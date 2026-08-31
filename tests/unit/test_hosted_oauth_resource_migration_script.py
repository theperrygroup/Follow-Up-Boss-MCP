"""CLI safety tests for the hosted OAuth resource migration script."""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = _PROJECT_ROOT / "scripts" / "migrate_hosted_oauth_resource.py"
_RESOURCE = "https://mcp.example.com/mcp"


def _run_script(
    *args: str,
    configured_resource: str = _RESOURCE,
    database_url: str | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run the migration CLI without exposing a database URL."""
    environ = os.environ.copy()
    environ["FOLLOWUPBOSS_HOSTED_RESOURCE_SERVER_URL"] = configured_resource
    if database_url is None:
        environ.pop("FOLLOWUPBOSS_TENANT_DATABASE_URL", None)
    else:
        environ["FOLLOWUPBOSS_TENANT_DATABASE_URL"] = database_url
    return subprocess.run(
        [sys.executable, str(_SCRIPT), *args],
        cwd=_PROJECT_ROOT,
        env=environ,
        capture_output=True,
        check=False,
        text=True,
    )


def _receipt_payload(
    *,
    resource: str = _RESOURCE,
    phase: str = "status",
    unbound_rows: int = 1,
    foreign_rows: int = 0,
    is_nullable: str = "YES",
    has_canonical_default: bool = True,
) -> dict[str, object]:
    """Build one representative aggregate-only migration receipt."""
    total_rows = 3
    table = {
        "total_rows": total_rows,
        "unbound_rows": unbound_rows,
        "expected_resource_rows": total_rows - unbound_rows - foreign_rows,
        "foreign_resource_rows": foreign_rows,
        "is_nullable": is_nullable,
        "has_canonical_default": has_canonical_default,
    }
    return {
        "phase": phase,
        "resource": resource,
        "access": table,
        "refresh": table,
    }


def _fake_psql(
    tmp_path: Path,
    *output_lines: str,
    verify_private_service_file: bool = False,
) -> Path:
    """Create a cross-platform psql stand-in with controlled stdout."""
    stub = tmp_path / "fake_psql.py"
    stub.write_text(
        "\n".join(
            (
                "from __future__ import annotations",
                "",
                "import os",
                "import sys",
                "from pathlib import Path",
                "",
                f"OUTPUT_LINES = {output_lines!r}",
                f"VERIFY_PRIVATE_SERVICE_FILE = {verify_private_service_file!r}",
                "",
                "if VERIFY_PRIVATE_SERVICE_FILE:",
                '    if os.environ.get("PGSERVICE") != "followupboss_migration":',
                "        raise SystemExit(91)",
                '    service_file = os.environ.get("PGSERVICEFILE")',
                "    if service_file is None or not Path(service_file).is_file():",
                "        raise SystemExit(92)",
                '    if "PGDATABASE" in os.environ:',
                "        raise SystemExit(93)",
                '    service_lines = Path(service_file).read_text(encoding="utf-8").splitlines()',
                '    if "host=db.example.com" not in service_lines:',
                "        raise SystemExit(94)",
                '    if any("postgresql://" in argument for argument in sys.argv[1:]):',
                "        raise SystemExit(95)",
                '    if "port=5432" not in service_lines:',
                "        raise SystemExit(96)",
                "",
                "for output_line in OUTPUT_LINES:",
                "    print(output_line)",
                "",
            )
        ),
        encoding="utf-8",
    )
    if os.name == "nt":
        executable = tmp_path / "psql.cmd"
        command = subprocess.list2cmdline([sys.executable, str(stub)])
        executable.write_text(f"@echo off\n{command} %*\n", encoding="utf-8")
    else:
        executable = tmp_path / "psql"
        command = shlex.join([sys.executable, str(stub)])
        executable.write_text(f'#!/bin/sh\nexec {command} "$@"\n', encoding="utf-8")
        executable.chmod(0o755)
    return executable


def test_backfill_dry_run_prints_parameterized_plan_without_database_access() -> None:
    """The default write path should be a secret-free, non-executing plan."""
    result = _run_script("backfill", "--resource", _RESOURCE)

    assert result.returncode == 0
    assert "DRY RUN: backfill" in result.stdout
    assert "20260831_backfill_oauth_resource.sql" in result.stdout
    assert "psql variable: mcp_resource=<validated --resource>" in result.stdout
    assert "No database connection was opened" in result.stdout
    assert "FOLLOWUPBOSS_TENANT_DATABASE_URL must be set" not in result.stderr


def test_expand_and_finalize_plans_explain_the_temporary_default() -> None:
    """Dry-run output should make the rolling-deploy default lifecycle explicit."""
    expand = _run_script("expand", "--resource", _RESOURCE)
    finalize = _run_script("finalize", "--resource", _RESOURCE)
    rollback = _run_script("rollback-finalize", "--resource", _RESOURCE)

    assert "temporary canonical default" in expand.stdout
    assert "drops the temporary default" in finalize.stdout
    assert "restores the temporary canonical default" in rollback.stdout


def test_migration_script_requires_canonical_resource_and_configured_match() -> None:
    """A normalized variant or different configured audience must be rejected."""
    noncanonical = _run_script("expand", "--resource", f"{_RESOURCE}/")
    mismatch = _run_script(
        "expand",
        "--resource",
        "https://other.example.com/mcp",
    )

    assert noncanonical.returncode == 2
    assert "must already be canonical" in noncanonical.stderr
    assert mismatch.returncode == 2
    assert "does not exactly match" in mismatch.stderr


def test_migration_script_rejects_resource_url_credentials() -> None:
    """Plans and receipts must never echo URL userinfo that could contain a secret."""
    credentialed = "https://user:secret@mcp.example.com/mcp"
    result = _run_script(
        "expand",
        "--resource",
        credentialed,
        configured_resource=credentialed,
    )

    assert result.returncode == 2
    assert "must not contain URL credentials" in result.stderr
    assert "secret" not in result.stdout


def test_migration_script_requires_write_phase_acknowledgements_before_database_access() -> None:
    """Backfill and finalization should fail before connecting without acknowledgements."""
    backfill = _run_script("backfill", "--resource", _RESOURCE, "--apply")
    finalize = _run_script("finalize", "--resource", _RESOURCE, "--apply")

    assert backfill.returncode == 2
    assert "--acknowledge-unbound-token-audience" in backfill.stderr
    assert finalize.returncode == 2
    assert "--old-writers-retired" in finalize.stderr


def test_read_only_phases_require_database_environment_after_resource_validation() -> None:
    """Read-only gates should require the database URL without printing secrets."""
    status = _run_script("status", "--resource", _RESOURCE)
    verify_ready = _run_script("verify-ready", "--resource", _RESOURCE)

    for result in (status, verify_ready):
        assert result.returncode == 2
        assert "FOLLOWUPBOSS_TENANT_DATABASE_URL must be set" in result.stderr
        assert "postgresql://" not in result.stderr


def test_status_forwards_one_validated_receipt_using_the_workflow_contract(
    tmp_path: Path,
) -> None:
    """The task log should contain the exact prefix and shape consumed by Actions."""
    payload = _receipt_payload()
    raw_receipt = f"MIGRATION_RECEIPT={json.dumps(payload)}"
    psql = _fake_psql(tmp_path, "psql chatter stays private", raw_receipt)

    result = _run_script(
        "status",
        "--resource",
        _RESOURCE,
        "--psql-bin",
        str(psql),
        database_url="postgresql://private.invalid/database",
    )

    assert result.returncode == 0
    assert result.stderr == ""
    assert result.stdout.count("MIGRATION_RECEIPT=") == 1
    forwarded = json.loads(result.stdout.removeprefix("MIGRATION_RECEIPT="))
    assert forwarded == payload
    assert "psql chatter" not in result.stdout
    assert "postgresql://" not in result.stdout


def test_psql_uses_a_private_service_file_instead_of_a_connection_argv(
    tmp_path: Path,
) -> None:
    """A normal PostgreSQL URI should reach libpq without appearing in process arguments."""
    payload = _receipt_payload()
    psql = _fake_psql(
        tmp_path,
        f"MIGRATION_RECEIPT={json.dumps(payload)}",
        verify_private_service_file=True,
    )

    result = _run_script(
        "status",
        "--resource",
        _RESOURCE,
        "--psql-bin",
        str(psql),
        database_url="postgresql://user:secret@db.example.com:5432/database?sslmode=require",
    )

    assert result.returncode == 0
    assert "secret" not in result.stdout + result.stderr


def test_psql_service_file_rejects_values_libpq_cannot_represent(tmp_path: Path) -> None:
    """The private service file must fail closed on stripped or oversized values."""
    payload = _receipt_payload()
    psql = _fake_psql(tmp_path, f"MIGRATION_RECEIPT={json.dumps(payload)}")

    leading_space = _run_script(
        "status",
        "--resource",
        _RESOURCE,
        "--psql-bin",
        str(psql),
        database_url="postgresql://user:%20secret@db.example.com/database",
    )
    oversized = _run_script(
        "status",
        "--resource",
        _RESOURCE,
        "--psql-bin",
        str(psql),
        database_url=f"postgresql://user:{'s' * 1100}@db.example.com/database",
    )

    for result in (leading_space, oversized):
        assert result.returncode == 2
        assert "contained an invalid value" in result.stderr
        assert "secret" not in result.stdout + result.stderr


def test_status_rejects_a_receipt_for_a_different_resource(tmp_path: Path) -> None:
    """A task must fail closed if SQL reports a different resource audience."""
    payload = _receipt_payload(resource="https://other.example.com/mcp")
    psql = _fake_psql(tmp_path, f"MIGRATION_RECEIPT={json.dumps(payload)}")

    result = _run_script(
        "status",
        "--resource",
        _RESOURCE,
        "--psql-bin",
        str(psql),
        database_url="postgresql://private.invalid/database",
    )

    assert result.returncode == 2
    assert "receipt resource did not match" in result.stderr
    assert "MIGRATION_RECEIPT=" not in result.stdout


def test_verify_ready_rejects_unbound_rows_even_when_psql_exits_cleanly(
    tmp_path: Path,
) -> None:
    """The task must fail closed if a receipt violates phase postconditions."""
    payload = _receipt_payload(phase="verify-ready")
    psql = _fake_psql(tmp_path, f"MIGRATION_RECEIPT={json.dumps(payload)}")

    result = _run_script(
        "verify-ready",
        "--resource",
        _RESOURCE,
        "--psql-bin",
        str(psql),
        database_url="postgresql://private.invalid/database",
    )

    assert result.returncode == 2
    assert "violated the 'verify-ready' postconditions" in result.stderr
    assert "MIGRATION_RECEIPT=" not in result.stdout


def test_cutover_sql_is_parameterized_and_non_destructive() -> None:
    """SQL phases should update only unbound rows and retain data on rollback."""
    migrations = _PROJECT_ROOT / "deploy" / "postgres" / "migrations"
    expand = (migrations / "20260831_add_oauth_resource.sql").read_text()
    status = (migrations / "20260831_oauth_resource_status.sql").read_text()
    verify_ready = (migrations / "20260831_verify_oauth_resource_ready.sql").read_text()
    backfill = (migrations / "20260831_backfill_oauth_resource.sql").read_text()
    finalize = (migrations / "20260831_finalize_oauth_resource.sql").read_text()
    rollback = (migrations / "20260831_rollback_finalize_oauth_resource.sql").read_text()
    receipt = (migrations / "20260831_oauth_resource_receipt.sql").read_text()

    assert ":'mcp_resource'" in expand
    assert expand.count("ALTER COLUMN resource SET DEFAULT %L") == 2
    assert "resource expand rejected a partially applied schema" in expand
    assert "resource expand rejected an unexpected existing schema state" in expand
    assert "BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY" in status
    assert "deployment gate rejected unbound rows" in verify_ready
    assert "deployment gate rejected foreign resource rows" in verify_ready
    assert (
        "deployment gate requires either the rolling or finalized resource schema" in verify_ready
    )
    assert ":'mcp_resource'" in backfill
    assert "WHERE resource IS NULL" in backfill
    assert "unbound counts changed" in backfill
    assert "foreign resource rows found" in backfill
    assert finalize.count("ALTER COLUMN resource DROP DEFAULT") == 2
    assert "ALTER COLUMN resource SET NOT NULL" in finalize
    assert rollback.count("ALTER COLUMN resource SET DEFAULT %L") == 2
    assert "rollback-finalize rejected an unexpected schema state" in rollback
    assert "ALTER COLUMN resource DROP NOT NULL" in rollback
    phase_sql = expand + status + verify_ready + backfill + finalize + rollback
    assert phase_sql.count("\\ir 20260831_oauth_resource_receipt.sql") == 6
    assert "MIGRATION_RECEIPT=" in receipt
    assert "token_hash" not in receipt
    assert "DELETE FROM" not in phase_sql
    assert "fub.theperry.group" not in phase_sql + receipt


def test_production_workflow_uses_a_least_privilege_migration_task() -> None:
    """Production migration plumbing should stay gated and keep raw DB output private."""
    workflow = (_PROJECT_ROOT / ".github" / "workflows" / "deploy-production.yml").read_text()
    hosted_dockerfile = (_PROJECT_ROOT / "Dockerfile").read_text()
    dockerfile = (_PROJECT_ROOT / "Dockerfile.migration").read_text()
    task_template = (
        _PROJECT_ROOT / "deploy" / "ecs" / "task-definition.migration.template.json"
    ).read_text()

    assert "operation:" in workflow
    assert "authorize-production-ref" in workflow
    assert "refs/heads/main" in workflow
    assert "uses: actions/checkout@v" not in workflow
    assert workflow.count("id-token: write") == 3
    assert "REQUESTED_OPERATION" in workflow
    assert "verify-ready" in workflow
    assert "--acknowledge-unbound-token-audience" in workflow
    assert "old-writers-retired" in workflow
    assert "accepted_release_sha" in workflow
    assert "accepted_task_definition_arn" in workflow
    assert "record-acceptance" in workflow
    assert "production-live-acceptance-${{ github.run_id }}-${{ github.run_attempt }}" in workflow
    assert "modern_acceptance_evidence_sha256" in workflow
    assert "legacy_acceptance_evidence_sha256" in workflow
    assert "ACCEPTANCE_RUN_ID" in workflow
    assert '"${service_task_definition}" != "${accepted_task_definition}"' in workflow
    assert 'os.environ["REQUESTED_OPERATION"] != "expand"' in workflow
    assert "inputs.operation != 'record-acceptance'" in workflow
    assert "finalize-service-before.json" in workflow
    assert "finalize-service-after.json" in workflow
    assert "running_database_secret" in workflow
    assert "running_resource" in workflow
    assert "DATABASE_SECRET_METADATA=" in workflow
    assert '"secretsmanager",' in workflow
    assert 'region_name=os.environ["AWS_REGION"]' in workflow
    assert '.describe_secret(SecretId=os.environ["TENANT_DATABASE_URL_SECRET_ARN"])' in workflow
    assert '"SecretArnSha256": hashlib.sha256(' in workflow
    assert 'metadata["ARN"].encode("utf-8")' in workflow
    assert "version_id: sorted(stages)" in workflow
    assert 'if [ "${metadata_probe_required}" = "true" ]; then' in workflow
    assert 'registerable["family"] = "followupboss-mcp-database-secret-metadata"' in workflow
    assert 'probe_image = container.get("image", "")' in workflow
    assert 're.fullmatch(r".+@sha256:[0-9a-f]{64}", probe_image)' in workflow
    assert "from botocore.config import Config" in workflow
    assert '"ARN": metadata.get("ARN")' not in workflow
    assert "aws secretsmanager describe-secret" not in workflow
    assert (
        '"secrets":'
        not in workflow.split('registerable["containerDefinitions"] = [', 1)[1].split(
            '(temp / "metadata-probe-task-definition.json")', 1
        )[0]
    )
    assert 'pinned_secret_arn = f"{base_secret_arn}:::{current_versions[0]}"' in workflow
    assert '"PINNED_TENANT_DATABASE_URL_SECRET_ARN"' in workflow
    assert 'running_service["services"][0]["deployments"][0]["createdAt"]' in workflow
    assert "deployment_created < last_changed + 30" in workflow
    assert 'if "AWSPENDING" in stages' in workflow
    assert "database-secret-metadata-after-pin.json" in workflow
    assert "Database secret metadata changed during pinning" in workflow
    assert "aws ecs list-tasks" not in workflow
    assert workflow.count("aws ecs describe-tasks") == 2
    assert '--tasks "${metadata_probe_task_arn}"' in workflow
    assert '--tasks "${task_arn}"' in workflow
    assert 'select(.status == "PRIMARY" and .taskDefinition == $expected)' in workflow
    assert '[ "${deployment_status}" != "PRIMARY" ]' in workflow
    assert '[ "${deployment_running}" != "${desired}" ]' in workflow
    assert '[ "${deployment_pending}" != "0" ]' in workflow
    assert '[ "${deployment_strategy}" != "ROLLING" ]' in workflow
    assert "database-prepin-service.json" in workflow
    assert '--arg deployment_id "${initial_deployment_id}"' in workflow
    assert ".services[0].deployments[0].id == $deployment_id" in workflow
    assert '[ "${expected_deployment_id}" = "${initial_deployment_id}" ]' in workflow
    assert '[ "${deployment_id}" != "${expected_deployment_id}" ]' in workflow
    assert workflow.count("--force-new-deployment") == 2
    assert "deploymentCircuitBreaker={enable=true,rollback=true}" in workflow
    assert "task_definition=%s" in workflow
    assert 'issuer.path not in ("", "/")' in workflow
    assert 'issuer = f"{issuer_split.scheme}://{issuer_split.netloc}/"' in workflow
    assert "MIGRATION_RECEIPT=" in workflow
    assert "raw database output was suppressed" in workflow
    assert "postgresql-client" in dockerfile
    assert "uv.lock" in dockerfile
    assert "uv sync --frozen --no-dev --no-editable" in dockerfile
    assert "@sha256:" in dockerfile
    assert "uv.lock" in hosted_dockerfile
    assert "uv sync --frozen --no-dev --no-editable" in hosted_dockerfile
    assert "@sha256:" in hosted_dockerfile
    assert "migrate_hosted_oauth_resource.py" in dockerfile
    assert "FOLLOWUPBOSS_TENANT_DATABASE_URL" in task_template
    assert "FOLLOWUPBOSS_REDIS_URL" not in task_template
    assert "FOLLOWUPBOSS_FUB_OAUTH" not in task_template
