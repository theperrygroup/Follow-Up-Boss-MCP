"""Exercise the production workflow's interrupted database-adoption retry gates."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

_WORKFLOW = Path(__file__).resolve().parents[2] / ".github/workflows/deploy-production.yml"
_SECRET = "arn:aws:secretsmanager:us-west-1:123456789012:secret:database-example"
_VERSION = "version-one"
_PINNED = f"{_SECRET}:::{_VERSION}"
_RESOURCE = "https://mcp.example.com/mcp"


def _workflow_step() -> str:
    text = _WORKFLOW.read_text(encoding="utf-8")
    return text.split("- name: Verify or explicitly adopt one database secret version", 1)[1].split(
        "- name: Set up Docker Buildx", 1
    )[0]


@pytest.mark.parametrize("operation", ["expand", "status", "deploy", "backfill", "finalize"])
@pytest.mark.parametrize("pinned", [False, True])
@pytest.mark.skipif(
    os.name == "nt" or shutil.which("bash") is None,
    reason="The production selector requires Bash on a POSIX runner.",
)
def test_metadata_probe_is_required_for_explicit_expand(operation: str, pinned: bool) -> None:
    step = _workflow_step()
    selector = step.split('          database_version_prefix="', 1)[1].split(
        '          if [ "${metadata_probe_required}" = "true" ]; then', 1
    )[0]
    result = subprocess.run(
        [
            "bash",
            "-c",
            'database_version_prefix="' + selector + '\nprintf "%s" "$metadata_probe_required"',
        ],
        env={
            **os.environ,
            "TENANT_DATABASE_URL_SECRET_ARN": _SECRET,
            "running_database_secret": _PINNED if pinned else _SECRET,
            "REQUESTED_OPERATION": operation,
        },
        capture_output=True,
        check=False,
        text=True,
    )
    if not pinned and operation != "expand":
        assert result.returncode != 0
        assert "explicit expand operation" in result.stderr
    else:
        assert result.returncode == 0, result.stderr
        assert result.stdout == ("true" if operation == "expand" else "false")


def _run_target_proof(
    tmp_path: Path,
    *,
    operation: str = "expand",
    current_version: str = _VERSION,
    pending_version: str | None = None,
    last_changed: float = 100,
    deployment_created: float = 200,
    include_metadata: bool = True,
) -> subprocess.CompletedProcess[str]:
    blocks = re.findall(r"          python - <<'PY'\n(.*?)\n          PY", _workflow_step(), re.S)
    proof = next(
        block for block in blocks if 'pin_path = temp / "pinned-database-secret-arn.txt"' in block
    )
    payloads: dict[str, object] = {
        "service-task-definition.json": {
            "taskDefinition": {
                "containerDefinitions": [
                    {
                        "name": "followupboss-mcp-hosted",
                        "environment": [
                            {"name": "FOLLOWUPBOSS_HOSTED_RESOURCE_SERVER_URL", "value": _RESOURCE}
                        ],
                        "secrets": [
                            {"name": "FOLLOWUPBOSS_TENANT_DATABASE_URL", "valueFrom": _PINNED}
                        ],
                    }
                ]
            }
        },
        "production-service.json": {
            "services": [{"deployments": [{"createdAt": deployment_created}]}]
        },
    }
    if include_metadata:
        versions = {current_version: ["AWSCURRENT"]}
        if pending_version is not None:
            versions.setdefault(pending_version, []).append("AWSPENDING")
        payloads["database-secret-metadata.json"] = {
            "ARN": _SECRET,
            "LastChangedDate": last_changed,
            "VersionIdsToStages": versions,
        }
    for filename, payload in payloads.items():
        (tmp_path / filename).write_text(json.dumps(payload), encoding="utf-8")
    return subprocess.run(
        [sys.executable, "-c", textwrap.dedent(proof)],
        env={
            **os.environ,
            "RUNNER_TEMP": str(tmp_path),
            "TENANT_DATABASE_URL_SECRET_ARN": _SECRET,
            "HOSTED_RESOURCE_SERVER_URL": _RESOURCE,
            "REQUESTED_OPERATION": operation,
        },
        capture_output=True,
        check=False,
        text=True,
    )


def test_pinned_expand_retry_reproves_target_without_registering_another_pin(
    tmp_path: Path,
) -> None:
    result = _run_target_proof(tmp_path)
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "pinned-database-secret-arn.txt").read_text() == _PINNED
    assert (tmp_path / "database-pin-required.txt").read_text() == "false"
    assert not (tmp_path / "pinned-service-task-definition.json").exists()


def test_pinned_expand_retry_rejects_rotated_current_version(tmp_path: Path) -> None:
    result = _run_target_proof(tmp_path, current_version="version-two")
    assert result.returncode != 0
    assert "did not match the running pinned database version" in result.stderr


def test_pinned_expand_retry_rejects_distinct_pending_version(tmp_path: Path) -> None:
    result = _run_target_proof(tmp_path, pending_version="version-two")
    assert result.returncode != 0
    assert "rotation is in progress" in result.stderr


def test_pinned_expand_retry_allows_current_version_also_pending(tmp_path: Path) -> None:
    result = _run_target_proof(tmp_path, pending_version=_VERSION)
    assert result.returncode == 0, result.stderr


def test_pinned_expand_retry_requires_metadata_to_predate_deployment_safety_window(
    tmp_path: Path,
) -> None:
    result = _run_target_proof(tmp_path, last_changed=171)
    assert result.returncode != 0
    assert "predates the current version safety window" in result.stderr


def test_pinned_expand_retry_requires_metadata_receipt(tmp_path: Path) -> None:
    result = _run_target_proof(tmp_path, include_metadata=False)
    assert result.returncode != 0
    assert not (tmp_path / "pinned-database-secret-arn.txt").exists()


@pytest.mark.parametrize("operation", ["status", "deploy", "backfill", "finalize"])
def test_later_pinned_phases_do_not_advance_to_rotated_current_version(
    tmp_path: Path, operation: str
) -> None:
    result = _run_target_proof(tmp_path, operation=operation, include_metadata=False)
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "pinned-database-secret-arn.txt").read_text() == _PINNED


@pytest.mark.parametrize("changed", [False, True])
@pytest.mark.skipif(
    os.name == "nt" or shutil.which("bash") is None,
    reason="The production metadata comparison requires Bash on a POSIX runner.",
)
def test_pinned_expand_retry_compares_metadata_after_final_convergence(
    tmp_path: Path, changed: bool
) -> None:
    step = _workflow_step()
    comparison = step.split(
        '          if [ "${metadata_probe_required}" = "true" ]; then\n'
        "            run_metadata_probe \\\n",
        1,
    )[1].split("          jq -e", 1)[0]
    before = {"LastChangedDate": 100, "VersionIdsToStages": {_VERSION: ["AWSCURRENT"]}}
    after = {**before, "LastChangedDate": 101 if changed else 100}
    (tmp_path / "database-secret-metadata-receipt.json").write_text(json.dumps(before))
    source = tmp_path / "probe-result.json"
    source.write_text(json.dumps(after))
    result = subprocess.run(
        [
            "bash",
            "-c",
            'run_metadata_probe() { cp "$SOURCE_RECEIPT" "$1"; }\n'
            'if [ "${metadata_probe_required}" = "true" ]; then\n'
            "  run_metadata_probe \\\n" + comparison,
        ],
        env={
            **os.environ,
            "RUNNER_TEMP": str(tmp_path),
            "SOURCE_RECEIPT": str(source),
            "metadata_probe_required": "true",
            "pin_required": "false",
        },
        capture_output=True,
        check=False,
        text=True,
    )
    assert (result.returncode != 0) == changed
    if changed:
        assert "Database secret metadata changed during pinning" in result.stderr
