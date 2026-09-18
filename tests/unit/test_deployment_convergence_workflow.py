"""Exercise the production workflow's actual ECS convergence shell gates."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
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


def _task_definition(
    *,
    sentry_dsn: str = "https://public@example.ingest.sentry.io/123",
    sentry_environment: str = "production",
    sentry_release: str = "followupboss-mcp@test-release",
) -> dict[str, object]:
    """Build the hosted container metadata checked after ECS convergence."""
    return {
        "taskDefinition": {
            "containerDefinitions": [
                {
                    "name": "followupboss-mcp-hosted",
                    "environment": [
                        {"name": "SENTRY_DSN", "value": sentry_dsn},
                        {"name": "SENTRY_ENVIRONMENT", "value": sentry_environment},
                        {"name": "SENTRY_RELEASE", "value": sentry_release},
                    ],
                }
            ]
        }
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
    sentry_dsn: str = "https://public@example.ingest.sentry.io/123",
    expected_sentry_dsn: str = "https://public@example.ingest.sentry.io/123",
    sentry_environment: str = "production",
    sentry_release: str = "followupboss-mcp@test-release",
) -> subprocess.CompletedProcess[str]:
    """Supply deterministic ECS snapshots and advance retries without wall-clock delay."""
    for index, service in enumerate(services):
        (tmp_path / f"service-{index}.json").write_text(
            json.dumps({"services": [service], "failures": []}), encoding="utf-8"
        )
    (tmp_path / "deployment-request.json").write_text(
        json.dumps({"service": _service("IN_PROGRESS")}), encoding="utf-8"
    )
    (tmp_path / "task-definition.json").write_text(
        json.dumps(
            _task_definition(
                sentry_dsn=sentry_dsn,
                sentry_environment=sentry_environment,
                sentry_release=sentry_release,
            )
        ),
        encoding="utf-8",
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
        PYTHON_EXECUTABLE=sys.executable,
        SENTRY_DSN=expected_sentry_dsn,
    )
    stub = f"""\
        aws_calls=0
        aws() {{
          if [ "$1 $2" = "ecs describe-services" ]; then
            snapshot=$aws_calls
            if [ "$snapshot" -ge {len(services)} ]; then snapshot={len(services) - 1}; fi
            /bin/cat "$RUNNER_TEMP/service-$snapshot.json"
            aws_calls=$((aws_calls + 1))
            printf '%s' "$aws_calls" > "$RUNNER_TEMP/aws-calls.txt"
          elif [ "$1 $2" = "ecs describe-task-definition" ]; then
            /bin/cat "$RUNNER_TEMP/task-definition.json"
          else
            return 91
          fi
        }}
        sleep() {{ SECONDS=$((SECONDS + {elapsed_per_retry})); }}
        python() {{ "${{PYTHON_EXECUTABLE}}" "$@"; }}
    """
    return subprocess.run(
        ["bash", "-euo", "pipefail", "-c", textwrap.dedent(stub) + _convergence_script(phase)],
        env=environ,
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )


def _run_validate_configuration_gate(
    *,
    sentry_dsn: str = "https://public@example.ingest.sentry.io/123",
    sentry_environment: str = "production",
) -> subprocess.CompletedProcess[str]:
    """Run the workflow's preflight shell gate up to its URL-validation Python block."""
    workflow = _WORKFLOW.read_text(encoding="utf-8")
    step = workflow.split("      - name: Verify production workflow configuration\n", 1)[1].split(
        "\n      - name:", 1
    )[0]
    script = textwrap.dedent(step.split("        run: |\n", 1)[1]).split("python - <<'PY'\n", 1)[0]
    environ = os.environ.copy()
    environ.update(
        AWS_REGION="us-west-1",
        DEPLOYMENT_ENVIRONMENT="production",
        ECR_REPOSITORY="followupboss-mcp",
        ECS_CLUSTER="test-cluster",
        ECS_SERVICE="hosted",
        HOSTED_ISSUER_URL="https://issuer.example.test",
        HOSTED_RESOURCE_SERVER_URL="https://resource.example.test/mcp",
        LOG_GROUP_NAME="/ecs/followupboss-mcp",
        SENTRY_DSN=sentry_dsn,
        SENTRY_ENVIRONMENT=sentry_environment,
        SENTRY_RELEASE="followupboss-mcp@test-release",
        TENANT_SECRET_PREFIX="followupboss-mcp/tenants/",
        TENANT_SECRET_REGION="us-west-1",
        AWS_ROLE_TO_ASSUME="arn:aws:iam::123456789012:role/deploy",
        REDIS_URL_SECRET_ARN="arn:aws:secretsmanager:us-west-1:123456789012:secret:redis",
        TENANT_DATABASE_URL_SECRET_ARN=(
            "arn:aws:secretsmanager:us-west-1:123456789012:secret:database"
        ),
        TASK_EXECUTION_ROLE_ARN="arn:aws:iam::123456789012:role/execution",
        TASK_ROLE_ARN="arn:aws:iam::123456789012:role/task",
    )
    return subprocess.run(
        ["bash", "-euo", "pipefail", "-c", script],
        env=environ,
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )


def _run_rendered_sentry_configuration_gate(
    tmp_path: Path,
    *,
    expected_sentry_dsn: str = "https://public@example.ingest.sentry.io/123",
    expected_sentry_environment: str = "production",
    expected_sentry_release: str = "followupboss-mcp@test-release",
    rendered_sentry_dsn: str = "https://public@example.ingest.sentry.io/123",
    rendered_sentry_environment: str = "production",
    rendered_sentry_release: str = "followupboss-mcp@test-release",
) -> subprocess.CompletedProcess[str]:
    """Run the actual pre-registration Sentry check against a rendered task definition."""
    workflow = _WORKFLOW.read_text(encoding="utf-8")
    step = workflow.split("      - name: Verify rendered Sentry release configuration\n", 1)[
        1
    ].split("\n      - name:", 1)[0]
    script = textwrap.dedent(step.split("        run: |\n", 1)[1])
    rendered_path = tmp_path / "deploy" / "ecs" / "task-definition.rendered.json"
    rendered_path.parent.mkdir(parents=True)
    rendered_path.write_text(
        json.dumps(
            {
                "containerDefinitions": [
                    {
                        "name": "followupboss-mcp-hosted",
                        "environment": [
                            {"name": "SENTRY_DSN", "value": rendered_sentry_dsn},
                            {
                                "name": "SENTRY_ENVIRONMENT",
                                "value": rendered_sentry_environment,
                            },
                            {"name": "SENTRY_RELEASE", "value": rendered_sentry_release},
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    environ = os.environ.copy()
    environ.update(
        GITHUB_SHA="test-release",
        PYTHON_EXECUTABLE=sys.executable,
        SENTRY_DSN=expected_sentry_dsn,
        SENTRY_ENVIRONMENT=expected_sentry_environment,
        SENTRY_RELEASE=expected_sentry_release,
    )
    script = 'python() { "${PYTHON_EXECUTABLE}" "$@"; }\n' + script
    return subprocess.run(
        ["bash", "-euo", "pipefail", "-c", script],
        cwd=tmp_path,
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


@pytest.mark.parametrize(
    ("sentry_dsn", "sentry_environment", "sentry_release"),
    [
        ("", "production", "followupboss-mcp@test-release"),
        ("https://public@example.ingest.sentry.io/123", "staging", "followupboss-mcp@test-release"),
        ("https://public@example.ingest.sentry.io/123", "production", "wrong-release"),
    ],
)
def test_release_requires_deployed_sentry_configuration(
    tmp_path: Path,
    sentry_dsn: str,
    sentry_environment: str,
    sentry_release: str,
) -> None:
    """A stable ECS rollout is insufficient when observability metadata drifts."""
    result = _run_gate(
        tmp_path,
        "release",
        [_service("COMPLETED")],
        sentry_dsn=sentry_dsn,
        sentry_environment=sentry_environment,
        sentry_release=sentry_release,
    )

    assert result.returncode == 1
    assert "required Sentry configuration" in result.stderr
    assert "DO_NOT_DISCLOSE_THIS_VALUE" not in result.stdout + result.stderr


def test_release_rejects_a_wrong_nonempty_sentry_dsn(tmp_path: Path) -> None:
    """A task definition cannot silently route production events to another project."""
    expected_sentry_dsn = "https://public@example.ingest.sentry.io/123"
    deployed_sentry_dsn = "https://public@other-project.ingest.sentry.io/456"

    result = _run_gate(
        tmp_path,
        "release",
        [_service("COMPLETED")],
        sentry_dsn=deployed_sentry_dsn,
        expected_sentry_dsn=expected_sentry_dsn,
    )

    assert result.returncode == 1
    assert "required Sentry configuration" in result.stderr
    assert expected_sentry_dsn not in result.stdout + result.stderr
    assert deployed_sentry_dsn not in result.stdout + result.stderr


def test_validate_gate_requires_a_nonempty_sentry_dsn() -> None:
    """Release validation must fail before a deployment can silently disable Sentry."""
    workflow = _WORKFLOW.read_text(encoding="utf-8")
    validate_step = workflow.split("      - name: Verify production workflow configuration\n", 1)[
        1
    ].split("\n      - name:", 1)[0]
    required_values = validate_step.split("          required_values=(\n", 1)[1].split(
        "          )\n", 1
    )[0]

    assert "SENTRY_DSN" in required_values
    assert "SENTRY_DSN must be non-empty." in validate_step
    result = _run_validate_configuration_gate(sentry_dsn=" \t")

    assert result.returncode == 1
    assert "SENTRY_DSN must be non-empty." in result.stderr


def test_validate_gate_accepts_only_lowercase_production_sentry_environment() -> None:
    """Preflight must reject a value that would later differ in the task definition."""
    canonical = _run_validate_configuration_gate()
    mixed_case = _run_validate_configuration_gate(sentry_environment="Production")

    assert canonical.returncode == 0, canonical.stderr
    assert mixed_case.returncode == 1
    assert "SENTRY_ENVIRONMENT must be production" in mixed_case.stderr


@pytest.mark.parametrize(
    ("expected_sentry_dsn", "expected_sentry_environment", "rendered_sentry_dsn"),
    [
        ("", "production", "https://public@example.ingest.sentry.io/123"),
        (
            "https://public@example.ingest.sentry.io/123",
            "staging",
            "https://public@example.ingest.sentry.io/123",
        ),
        (
            "https://public@example.ingest.sentry.io/123",
            "production",
            "https://public@other-project.ingest.sentry.io/456",
        ),
    ],
)
def test_rendered_sentry_gate_rejects_deploy_time_drift(
    tmp_path: Path,
    expected_sentry_dsn: str,
    expected_sentry_environment: str,
    rendered_sentry_dsn: str,
) -> None:
    """Mutable deploy-job values cannot register a misconfigured task definition."""
    result = _run_rendered_sentry_configuration_gate(
        tmp_path,
        expected_sentry_dsn=expected_sentry_dsn,
        expected_sentry_environment=expected_sentry_environment,
        rendered_sentry_dsn=rendered_sentry_dsn,
    )

    assert result.returncode == 1
    assert "Rendered task definition did not retain required Sentry configuration." in result.stderr
    assert "https://public@example.ingest.sentry.io/123" not in result.stdout + result.stderr
    assert "https://public@other-project.ingest.sentry.io/456" not in result.stdout + result.stderr


def test_rendered_sentry_gate_accepts_the_current_production_values(tmp_path: Path) -> None:
    """The pre-registration guard accepts the exact production configuration it renders."""
    result = _run_rendered_sentry_configuration_gate(tmp_path)

    assert result.returncode == 0, result.stderr
