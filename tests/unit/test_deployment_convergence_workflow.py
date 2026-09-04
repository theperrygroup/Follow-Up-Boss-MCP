"""Exercise the production workflow's actual ECS convergence shell gates."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import textwrap
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_WORKFLOW = _PROJECT_ROOT / ".github" / "workflows" / "deploy-production.yml"
_TASK_DEFINITION = "arn:aws:ecs:us-west-1:123456789012:task-definition/hosted:44"
_DEPLOYMENT_ID = "ecs-svc/expected"

pytestmark = pytest.mark.skipif(
    os.name == "nt" or shutil.which("bash") is None or shutil.which("jq") is None,
    reason="The production shell requires Bash and jq on a POSIX runner.",
)


def _service(rollout_state: str) -> dict[str, object]:
    """Build the minimum service response used by both real shell gates."""
    deployment = {
        "id": _DEPLOYMENT_ID,
        "status": "PRIMARY",
        "taskDefinition": _TASK_DEFINITION,
        "desiredCount": 1,
        "runningCount": 1,
        "pendingCount": 0,
        "rolloutState": rollout_state,
    }
    return {
        "status": "ACTIVE",
        "taskDefinition": _TASK_DEFINITION,
        "desiredCount": 1,
        "runningCount": 1,
        "pendingCount": 0,
        "deployments": [deployment],
        "deploymentController": {"type": "ECS"},
        "schedulingStrategy": "REPLICA",
        "deploymentConfiguration": {
            "strategy": "ROLLING",
            "deploymentCircuitBreaker": {"enable": True, "rollback": True},
        },
        "unrelatedPrivateValue": "DO_NOT_DISCLOSE_THIS_VALUE",
    }


def _convergence_script(phase: str) -> str:
    """Extract the executable post-wait acceptance path without duplicating it."""
    step_name = (
        "Verify or explicitly adopt one database secret version"
        if phase == "pin"
        else "Verify the deployed ECS release"
    )
    workflow = _WORKFLOW.read_text(encoding="utf-8")
    step = workflow.split(f"      - name: {step_name}\n", 1)[1].split("\n      - name:", 1)[0]
    script = textwrap.dedent(step.split("        run: |\n", 1)[1])
    if phase == "pin":
        script = script.split("aws ecs wait services-stable", 1)[1].split(
            '--region "${AWS_REGION}"\n', 1
        )[1]
        script = script.split("aws ecs describe-task-definition", 1)[0]
    return script


def _run_gate(
    tmp_path: Path,
    phase: str,
    services: list[dict[str, object]],
    *,
    elapsed_per_retry: int = 15,
) -> subprocess.CompletedProcess[str]:
    """Supply deterministic ECS snapshots and advance retries without wall-clock delay."""
    for index, service in enumerate(services):
        (tmp_path / f"service-{index}.json").write_text(
            json.dumps({"services": [service], "failures": []}), encoding="utf-8"
        )
    (tmp_path / "deployment-request.json").write_text(
        json.dumps({"service": _service("IN_PROGRESS")}), encoding="utf-8"
    )
    environ = os.environ.copy()
    environ.update(
        RUNNER_TEMP=str(tmp_path),
        AWS_REGION="us-west-1",
        ECS_CLUSTER="test-cluster",
        ECS_SERVICE="hosted",
        EXPECTED_TASK_DEFINITION=_TASK_DEFINITION,
        expected_task_definition=_TASK_DEFINITION,
        expected_deployment_id=_DEPLOYMENT_ID,
        pin_required="true",
        GITHUB_SHA="test-release",
    )
    stub = f"""\
        aws_calls=0
        aws() {{
          if [ "$1 $2" != "ecs describe-services" ]; then return 91; fi
          snapshot=$aws_calls
          if [ "$snapshot" -ge {len(services)} ]; then snapshot={len(services) - 1}; fi
          /bin/cat "$RUNNER_TEMP/service-$snapshot.json"
          aws_calls=$((aws_calls + 1))
          printf '%s' "$aws_calls" > "$RUNNER_TEMP/aws-calls.txt"
        }}
        sleep() {{ SECONDS=$((SECONDS + {elapsed_per_retry})); }}
    """
    return subprocess.run(
        ["bash", "-euo", "pipefail", "-c", textwrap.dedent(stub) + _convergence_script(phase)],
        env=environ,
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )


@pytest.mark.parametrize("phase", ["pin", "release"])
def test_convergence_waits_for_completed_after_running_counts_match(
    tmp_path: Path, phase: str
) -> None:
    """The AWS services-stable result may precede the deployment's COMPLETED state."""
    result = _run_gate(tmp_path, phase, [_service("IN_PROGRESS"), _service("COMPLETED")])

    assert result.returncode == 0, result.stderr
    assert (tmp_path / "aws-calls.txt").read_text() == "2"
    assert "DO_NOT_DISCLOSE_THIS_VALUE" not in result.stdout + result.stderr


@pytest.mark.parametrize("phase", ["pin", "release"])
def test_convergence_waits_for_deployment_counts_after_service_counts_match(
    tmp_path: Path, phase: str
) -> None:
    """A completed rollout still needs consistent deployment-level task counts."""
    service = _service("COMPLETED")
    deployments = service["deployments"]
    assert isinstance(deployments, list)
    deployments[0]["runningCount"] = 0
    deployments[0]["pendingCount"] = 1

    result = _run_gate(tmp_path, phase, [service, _service("COMPLETED")])

    assert result.returncode == 0, result.stderr
    assert (tmp_path / "aws-calls.txt").read_text() == "2"


@pytest.mark.parametrize("phase", ["pin", "release"])
@pytest.mark.parametrize("replacement", ["deployment", "task_definition", "strategy", "failed"])
def test_convergence_rejects_replacement_or_failed_rollout_without_retrying(
    tmp_path: Path, phase: str, replacement: str
) -> None:
    """Retries must never reinterpret another deployment as the requested release."""
    service = _service("IN_PROGRESS")
    deployments = service["deployments"]
    assert isinstance(deployments, list)
    if replacement == "deployment":
        deployments[0]["id"] = "ecs-svc/replacement"
    elif replacement == "task_definition":
        service["taskDefinition"] = f"{_TASK_DEFINITION}-replacement"
        deployments[0]["taskDefinition"] = f"{_TASK_DEFINITION}-replacement"
    elif replacement == "strategy":
        configuration = service["deploymentConfiguration"]
        assert isinstance(configuration, dict)
        configuration["strategy"] = "BLUE_GREEN"
    else:
        deployments[0]["rolloutState"] = "FAILED"

    result = _run_gate(tmp_path, phase, [service, _service("COMPLETED")])

    assert result.returncode == 1
    assert (tmp_path / "aws-calls.txt").read_text() == "1"
    assert "did not converge" in result.stderr
    assert "DO_NOT_DISCLOSE_THIS_VALUE" not in result.stdout + result.stderr


@pytest.mark.parametrize("phase", ["pin", "release"])
def test_convergence_deadline_fails_closed_with_allowlisted_diagnostics(
    tmp_path: Path, phase: str
) -> None:
    """An in-progress deployment cannot keep the workflow alive indefinitely."""
    result = _run_gate(tmp_path, phase, [_service("IN_PROGRESS")], elapsed_per_retry=300)

    assert result.returncode == 1
    assert (tmp_path / "aws-calls.txt").read_text() == "2"
    diagnostic = json.loads(result.stderr.splitlines()[0])
    assert diagnostic["rollout_in_progress"] is True
    assert diagnostic["rollout_completed"] is False
    assert diagnostic["deployment_id_matches"] is True
    assert diagnostic["deployment_task_definition_matches"] is True
    assert "DO_NOT_DISCLOSE_THIS_VALUE" not in result.stdout + result.stderr
