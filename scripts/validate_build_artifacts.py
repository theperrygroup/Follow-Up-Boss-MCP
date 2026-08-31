#!/usr/bin/env python3
"""Validate built distribution artifacts in an isolated virtual environment."""

from __future__ import annotations

import os
import subprocess
import tempfile
import venv
from collections.abc import Sequence
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DIST_DIR = PROJECT_ROOT / "dist"


def _latest_artifact(directory: Path, pattern: str) -> Path:
    """Return the newest matching artifact in a directory.

    Args:
        directory: The directory that contains built artifacts.
        pattern: The glob pattern used to match candidate artifacts.

    Returns:
        The newest matching artifact path.

    Raises:
        FileNotFoundError: If no matching artifact exists.
    """
    artifacts = sorted(directory.glob(pattern), key=lambda path: path.stat().st_mtime)
    if not artifacts:
        raise FileNotFoundError(f"No build artifact matched {pattern!r} in {directory}.")
    return artifacts[-1]


def _python_command(bin_dir: Path, command: str) -> Path:
    """Return a platform-specific executable path from a virtual environment.

    Args:
        bin_dir: The virtual environment scripts directory.
        command: The command name without an extension.

    Returns:
        The platform-specific executable path.
    """
    suffix = ".exe" if os.name == "nt" else ""
    return bin_dir / f"{command}{suffix}"


def _run(command: Sequence[str], *, cwd: Path | None = None) -> None:
    """Run a command and raise if it fails.

    Args:
        command: The full command to execute.
        cwd: An optional working directory.
    """
    subprocess.run(
        command,
        check=True,
        cwd=str(cwd) if cwd is not None else None,
    )


def main() -> None:
    """Validate that built artifacts can be installed and exercised.

    Raises:
        SystemExit: If the expected build artifacts are missing.
    """
    if not DIST_DIR.exists():
        raise SystemExit("dist/ does not exist. Run `uv build --clear` first.")

    sdist_path = _latest_artifact(DIST_DIR, "*.tar.gz")
    wheel_path = _latest_artifact(DIST_DIR, "*.whl")

    with tempfile.TemporaryDirectory(prefix="followupboss-mcp-build-") as temp_dir:
        venv_dir = Path(temp_dir) / "venv"
        venv.EnvBuilder(with_pip=True, clear=True).create(venv_dir)
        bin_dir = venv_dir / ("Scripts" if os.name == "nt" else "bin")
        python_path = _python_command(bin_dir, "python")
        cli_path = _python_command(bin_dir, "followupboss-mcp")

        _run([str(python_path), "-m", "pip", "install", str(wheel_path)])
        _run([str(cli_path), "--help"])
        _run(
            [
                str(python_path),
                "-c",
                (
                    "from importlib import resources; "
                    "import followupboss_mcp; "
                    "assert followupboss_mcp.__version__; "
                    "coverage = resources.files('followupboss_mcp.assets')"
                    ".joinpath('api-coverage-matrix.md').read_text(encoding='utf-8'); "
                    "assert '# API Coverage Matrix' in coverage; "
                    "print(followupboss_mcp.__version__)"
                ),
            ]
        )

    print(
        "Validated build artifacts:",
        sdist_path.name,
        wheel_path.name,
    )


if __name__ == "__main__":
    main()
