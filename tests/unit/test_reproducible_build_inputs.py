"""Regression checks for immutable production build inputs."""

from __future__ import annotations

from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_hosted_image_has_no_live_os_package_install() -> None:
    """The hosted runtime should not resolve Debian packages during its build."""
    dockerfile = (_PROJECT_ROOT / "Dockerfile").read_text()

    assert "apt-get" not in dockerfile
    assert "deb.debian.org" not in dockerfile


def test_migration_image_installs_psql_from_an_immutable_snapshot() -> None:
    """The migration-only psql client should resolve from one fixed Debian snapshot."""
    dockerfile = (_PROJECT_ROOT / "Dockerfile.migration").read_text()

    assert "https://snapshot.debian.org/archive/debian/20260824T000000Z" in dockerfile
    assert "https://snapshot.debian.org/archive/debian-security/20260824T000000Z" in dockerfile
    assert "postgresql-client-17=17.11-0+deb13u1" in dockerfile
    assert "apt-get install --yes --no-install-recommends postgresql-client " not in dockerfile


def test_build_backend_version_is_exact() -> None:
    """PEP 517 build isolation should use one reviewed Hatchling release."""
    pyproject = (_PROJECT_ROOT / "pyproject.toml").read_text()

    assert 'requires = ["hatchling==1.27.0"]' in pyproject
