"""Keep auth acceptance wired into CI, deployment, and installed-wheel validation."""

from __future__ import annotations

import os
import runpy
import subprocess
import venv
from pathlib import Path
from typing import Any

import pytest

_ROOT = Path(__file__).resolve().parents[2]


def test_deployment_checks_current_clients_before_mutation_and_after_rollout() -> None:
    workflow = (_ROOT / ".github/workflows/deploy-production.yml").read_text()
    validate, rest = workflow.split("  record-live-acceptance:", 1)
    assert "run: make auth-client-check" in validate
    assert (
        "inputs.operation == 'deploy'"
        in validate.split("- name: Verify current OAuth client compatibility", 1)[1]
    )
    deploy = rest.split("\n  deploy:\n", 1)[1]
    assert "      - validate\n" in deploy.split("    steps:", 1)[0]
    assert deploy.index("Verify the deployed ECS release") < deploy.index(
        "run: uv run --frozen python scripts/verify_public_oauth.py"
    )


def test_ci_cannot_build_without_current_client_compatibility() -> None:
    workflow = (_ROOT / ".github/workflows/ci.yml").read_text()
    client_job = workflow.split("  auth-client-compatibility:\n", 1)[1].split("\n  quality:", 1)[0]
    assert "run: make auth-client-check" in client_job
    assert "      - auth-client-compatibility\n" in workflow.split("\n  build:\n", 1)[1]


def test_wheel_validation_runs_auth_using_installed_code(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Observe dispatched commands: no source-path shortcut may satisfy wheel acceptance."""
    script = runpy.run_path(str(_ROOT / "scripts/validate_build_artifacts.py"))
    namespace = script["main"].__globals__
    project = tmp_path / "checkout"
    dist = project / "dist"
    dist.mkdir(parents=True)
    (dist / "example.whl").touch()
    (dist / "example.tar.gz").touch()
    monkeypatch.setitem(namespace, "PROJECT_ROOT", project)
    monkeypatch.setitem(namespace, "DIST_DIR", dist)
    monkeypatch.setattr(venv.EnvBuilder, "create", lambda self, path: None)
    monkeypatch.setenv("PYTHONPATH", str(project / "src"))
    monkeypatch.setenv("SENTRY_DSN", "must-not-reach-offline-test")
    monkeypatch.setenv("PYTEST_ADDOPTS", "-k skip-important-auth-cases")
    monkeypatch.setenv("PYTEST_PLUGINS", "unexpected_plugin")
    commands: list[tuple[list[str], dict[str, Any]]] = []

    def run(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        commands.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(subprocess, "run", run)
    script["main"]()
    test_runs = [(cmd, opts) for cmd, opts in commands if "pytest" in cmd]
    assert len(test_runs) == 1
    command, options = test_runs[0]
    assert command[-1] == str(project / "tests/integration/test_oauth_lifecycle.py")
    assert "--import-mode=importlib" in command
    assert command[command.index("-c") + 1] == os.devnull
    assert not Path(options["cwd"]).is_relative_to(project)
    assert "PYTHONPATH" not in options["env"]
    assert "SENTRY_DSN" not in options["env"]
    assert "PYTEST_ADDOPTS" not in options["env"]
    assert "PYTEST_PLUGINS" not in options["env"]
    assert any("install" in cmd and cmd[-1].endswith("[dev]") for cmd, _ in commands)
