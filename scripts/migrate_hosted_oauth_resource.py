#!/usr/bin/env python3
"""Run the staged, psql-backed hosted OAuth resource transition safely."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Literal
from urllib.parse import urlsplit

from psycopg.conninfo import conninfo_to_dict
from pydantic import AnyHttpUrl

from followupboss_mcp.url_validation import normalize_public_http_url

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_DATABASE_URL_ENV = "FOLLOWUPBOSS_TENANT_DATABASE_URL"
_RESOURCE_ENV = "FOLLOWUPBOSS_HOSTED_RESOURCE_SERVER_URL"
_RECEIPT_PREFIX = "MIGRATION_RECEIPT="
_PGSERVICE_NAME = "followupboss_migration"

Phase = Literal[
    "expand",
    "status",
    "verify-ready",
    "backfill",
    "finalize",
    "rollback-finalize",
]

_PHASE_FILES: dict[Phase, Path] = {
    "expand": _PROJECT_ROOT / "deploy/postgres/migrations/20260831_add_oauth_resource.sql",
    "status": _PROJECT_ROOT / "deploy/postgres/migrations/20260831_oauth_resource_status.sql",
    "verify-ready": _PROJECT_ROOT
    / "deploy/postgres/migrations/20260831_verify_oauth_resource_ready.sql",
    "backfill": _PROJECT_ROOT / "deploy/postgres/migrations/20260831_backfill_oauth_resource.sql",
    "finalize": _PROJECT_ROOT / "deploy/postgres/migrations/20260831_finalize_oauth_resource.sql",
    "rollback-finalize": _PROJECT_ROOT
    / "deploy/postgres/migrations/20260831_rollback_finalize_oauth_resource.sql",
}


class MigrationSafetyError(RuntimeError):
    """Raised when operator input does not satisfy a cutover safety gate."""


def _canonical_resource(raw_resource: str, *, field_name: str) -> str:
    """Validate that an explicitly supplied resource is already canonical."""
    candidate = raw_resource.strip()
    try:
        normalized = normalize_public_http_url(candidate, field_name=field_name)
    except Exception as exc:
        raise MigrationSafetyError(f"{field_name} is not a valid MCP resource URL.") from exc
    if not isinstance(normalized, AnyHttpUrl):
        raise MigrationSafetyError(f"{field_name} is not a valid MCP resource URL.")
    parsed = urlsplit(candidate)
    if parsed.username is not None or parsed.password is not None:
        raise MigrationSafetyError(f"{field_name} must not contain URL credentials.")
    canonical = str(normalized)
    if candidate != canonical:
        raise MigrationSafetyError(f"{field_name} must already be canonical; use {canonical!r}.")
    return canonical


def _required_environment_value(environ: Mapping[str, str], name: str) -> str:
    """Return one non-empty environment value without logging its contents."""
    value = environ.get(name, "").strip()
    if not value:
        raise MigrationSafetyError(f"{name} must be set.")
    return value


def _nonnegative_integer(value: str) -> int:
    """Parse a non-negative operator-reviewed row count."""
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("row counts must be non-negative")
    return parsed


def _positive_integer(value: str) -> int:
    """Parse a positive timeout."""
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("timeouts must be greater than zero")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    """Build the staged OAuth resource-transition parser."""
    parser = argparse.ArgumentParser(
        description="Safely bind existing hosted OAuth rows to one canonical MCP resource."
    )
    parser.add_argument("phase", choices=tuple(_PHASE_FILES))
    parser.add_argument("--resource", required=True, help="Exact canonical MCP resource URL.")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Run psql for a write phase. Without it, print a non-connecting plan.",
    )
    parser.add_argument("--expect-access-unbound", type=_nonnegative_integer)
    parser.add_argument("--expect-refresh-unbound", type=_nonnegative_integer)
    parser.add_argument(
        "--acknowledge-unbound-token-audience",
        action="store_true",
        help="Confirm every NULL-resource token was issued only for --resource.",
    )
    parser.add_argument(
        "--old-writers-retired",
        action="store_true",
        help="Confirm no pre-resource application instance can insert NULL rows.",
    )
    parser.add_argument("--lock-timeout-seconds", type=_positive_integer, default=5)
    parser.add_argument("--statement-timeout-seconds", type=_positive_integer, default=60)
    parser.add_argument("--psql-bin", default="psql", help=argparse.SUPPRESS)
    return parser


def _validate_apply_safeguards(args: argparse.Namespace) -> None:
    """Require explicit acknowledgements before write phases."""
    if args.phase in {"status", "verify-ready"} and args.apply:
        raise MigrationSafetyError(f"{args.phase} is read-only; omit --apply.")
    if not args.apply:
        return
    if args.phase == "backfill":
        if not args.acknowledge_unbound_token_audience:
            raise MigrationSafetyError("Backfill requires --acknowledge-unbound-token-audience.")
        if args.expect_access_unbound is None or args.expect_refresh_unbound is None:
            raise MigrationSafetyError(
                "Backfill requires --expect-access-unbound and --expect-refresh-unbound "
                "from a fresh status run."
            )
    if args.phase == "finalize" and not args.old_writers_retired:
        raise MigrationSafetyError("Finalize requires --old-writers-retired.")


def _print_plan(phase: Phase, resource: str, args: argparse.Namespace) -> None:
    """Print a non-executing psql plan without connection secrets."""
    sql_path = _PHASE_FILES[phase].relative_to(_PROJECT_ROOT)
    print(f"DRY RUN: {phase} for canonical resource {resource}")
    print(f"- SQL: {sql_path}")
    print("- psql variable: mcp_resource=<validated --resource>")
    if phase == "expand":
        print("- installs a temporary canonical default for pre-resource writers")
    if phase == "backfill":
        print(
            "- reviewed counts: "
            f"access={args.expect_access_unbound!r} "
            f"refresh={args.expect_refresh_unbound!r}"
        )
    if phase == "finalize":
        print("- drops the temporary default before enforcing NOT NULL")
    if phase == "rollback-finalize":
        print("- restores the temporary canonical default before allowing NULL")
    print("- No database connection was opened. Add --apply only after reviewing status.")


def _psql_command(
    *,
    phase: Phase,
    resource: str,
    args: argparse.Namespace,
) -> list[str]:
    """Build a shell-free psql command with separately bound variables."""
    command = [
        args.psql_bin,
        "--no-psqlrc",
        "--quiet",
        "--tuples-only",
        "--no-align",
        "--set=ON_ERROR_STOP=1",
        f"--set=mcp_resource={resource}",
        f"--set=migration_phase={phase}",
        f"--set=lock_timeout_seconds={args.lock_timeout_seconds}",
        f"--set=statement_timeout_seconds={args.statement_timeout_seconds}",
    ]
    if phase == "backfill":
        command.extend(
            [
                f"--set=expected_access_unbound={args.expect_access_unbound}",
                f"--set=expected_refresh_unbound={args.expect_refresh_unbound}",
            ]
        )
    command.extend(["--file", str(_PHASE_FILES[phase])])
    return command


def _validated_receipt(phase: Phase, resource: str, raw_output: str) -> str:
    """Return one normalized, aggregate-only receipt from captured psql output."""
    receipt_lines = [line for line in raw_output.splitlines() if line.startswith(_RECEIPT_PREFIX)]
    if len(receipt_lines) != 1:
        raise MigrationSafetyError("The migration did not produce exactly one sanitized receipt.")
    try:
        payload = json.loads(receipt_lines[0][len(_RECEIPT_PREFIX) :])
    except (json.JSONDecodeError, TypeError) as exc:
        raise MigrationSafetyError("The sanitized migration receipt was invalid.") from exc
    if not isinstance(payload, dict) or set(payload) != {
        "phase",
        "resource",
        "access",
        "refresh",
    }:
        raise MigrationSafetyError("The sanitized migration receipt had an unexpected shape.")
    if payload["phase"] != phase:
        raise MigrationSafetyError("The sanitized migration receipt phase did not match.")
    if payload["resource"] != resource:
        raise MigrationSafetyError("The sanitized migration receipt resource did not match.")

    normalized: dict[str, object] = {"phase": phase, "resource": resource}
    validated_tables: dict[str, dict[str, object]] = {}
    expected_table_keys = {
        "total_rows",
        "unbound_rows",
        "expected_resource_rows",
        "foreign_resource_rows",
        "is_nullable",
        "has_canonical_default",
    }
    for table_name in ("access", "refresh"):
        table = payload[table_name]
        if not isinstance(table, dict) or set(table) != expected_table_keys:
            raise MigrationSafetyError("The sanitized migration receipt had an unexpected shape.")
        counts: dict[str, int] = {}
        for key in (
            "total_rows",
            "unbound_rows",
            "expected_resource_rows",
            "foreign_resource_rows",
        ):
            value = table[key]
            if type(value) is not int or value < 0:
                raise MigrationSafetyError(
                    "The sanitized migration receipt contained invalid counts."
                )
            counts[key] = value
        if (
            counts["unbound_rows"]
            + counts["expected_resource_rows"]
            + counts["foreign_resource_rows"]
            != counts["total_rows"]
        ):
            raise MigrationSafetyError("The sanitized migration receipt counts were inconsistent.")
        is_nullable = table["is_nullable"]
        has_canonical_default = table["has_canonical_default"]
        if is_nullable not in {"YES", "NO"} or type(has_canonical_default) is not bool:
            raise MigrationSafetyError("The sanitized migration receipt schema state was invalid.")
        validated_tables[table_name] = {
            **counts,
            "is_nullable": is_nullable,
            "has_canonical_default": has_canonical_default,
        }
        normalized[table_name] = validated_tables[table_name]

    tables = tuple(validated_tables.values())
    no_foreign = all(table["foreign_resource_rows"] == 0 for table in tables)
    fully_bound = no_foreign and all(table["unbound_rows"] == 0 for table in tables)
    rolling_schema = all(
        table["is_nullable"] == "YES" and table["has_canonical_default"] is True for table in tables
    )
    finalized_schema = all(
        table["is_nullable"] == "NO" and table["has_canonical_default"] is False for table in tables
    )

    phase_valid = True
    if phase == "expand":
        phase_valid = no_foreign and (rolling_schema or (fully_bound and finalized_schema))
    elif phase == "backfill":
        phase_valid = fully_bound and rolling_schema
    elif phase == "verify-ready":
        phase_valid = fully_bound and (rolling_schema or finalized_schema)
    elif phase == "finalize":
        phase_valid = fully_bound and finalized_schema
    elif phase == "rollback-finalize":
        phase_valid = fully_bound and rolling_schema
    if not phase_valid:
        raise MigrationSafetyError(
            f"The sanitized migration receipt violated the {phase!r} postconditions."
        )
    return json.dumps(normalized, separators=(",", ":"), sort_keys=True)


def _service_file_value(value: str) -> str:
    """Return one literal libpq service-file value without line injection."""
    if "\n" in value or "\r" in value or "\x00" in value:
        raise MigrationSafetyError("The database connection URL contained an invalid value.")
    if value != value.strip():
        raise MigrationSafetyError("The database connection URL contained an invalid value.")
    return value


def _write_libpq_service_file(database_url: str, directory: Path) -> Path:
    """Write a private libpq service file so the URL never appears in argv."""
    try:
        parameters = conninfo_to_dict(database_url)
    except Exception as exc:
        raise MigrationSafetyError("The database connection URL was invalid.") from exc
    if not parameters or any(key in parameters for key in ("service", "servicefile")):
        raise MigrationSafetyError("The database connection URL was invalid.")
    service_path = directory / "pg_service.conf"
    lines = [f"[{_PGSERVICE_NAME}]"]
    for key, value in sorted(parameters.items()):
        if value is not None:
            line = f"{key}={_service_file_value(str(value))}"
            if len(line.encode("utf-8")) >= 1023:
                raise MigrationSafetyError(
                    "The database connection URL contained an invalid value."
                )
            lines.append(line)
    service_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    service_path.chmod(0o600)
    return service_path


def _run_psql(
    *,
    phase: Phase,
    resource: str,
    database_url: str,
    args: argparse.Namespace,
    environ: Mapping[str, str],
) -> int:
    """Execute one checked SQL phase without putting the database URL in argv."""
    if shutil.which(args.psql_bin) is None:
        raise MigrationSafetyError(f"psql executable was not found: {args.psql_bin}")
    with TemporaryDirectory(prefix="followupboss-migration-") as temporary_directory:
        directory = Path(temporary_directory)
        directory.chmod(0o700)
        service_path = _write_libpq_service_file(database_url, directory)
        child_environment = dict(environ)
        child_environment.pop(_DATABASE_URL_ENV, None)
        child_environment.pop("PGDATABASE", None)
        child_environment["PGSERVICE"] = _PGSERVICE_NAME
        child_environment["PGSERVICEFILE"] = str(service_path)
        result = subprocess.run(
            _psql_command(phase=phase, resource=resource, args=args),
            cwd=_PROJECT_ROOT,
            env=child_environment,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    if result.returncode != 0:
        raise MigrationSafetyError(
            f"psql phase {phase!r} failed with exit code {result.returncode}; "
            "raw database output was suppressed. Verify state with status before retrying."
        )
    receipt = _validated_receipt(phase, resource, result.stdout)
    print(f"{_RECEIPT_PREFIX}{receipt}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Validate operator intent, print a plan, or run one psql phase."""
    args = build_parser().parse_args(argv)
    environ = os.environ
    try:
        resource = _canonical_resource(args.resource, field_name="--resource")
        configured_resource = _canonical_resource(
            _required_environment_value(environ, _RESOURCE_ENV),
            field_name=_RESOURCE_ENV,
        )
        if resource != configured_resource:
            raise MigrationSafetyError(
                "--resource does not exactly match FOLLOWUPBOSS_HOSTED_RESOURCE_SERVER_URL."
            )
        _validate_apply_safeguards(args)
        phase: Phase = args.phase
        if phase not in {"status", "verify-ready"} and not args.apply:
            _print_plan(phase, resource, args)
            return 0

        database_url = _required_environment_value(environ, _DATABASE_URL_ENV)
        return _run_psql(
            phase=phase,
            resource=resource,
            database_url=database_url,
            args=args,
            environ=environ,
        )
    except MigrationSafetyError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
