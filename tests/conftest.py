"""Shared pytest fixtures for deterministic test isolation."""

from __future__ import annotations

import pytest

_SENTRY_ENV_KEYS = (
    "SENTRY_DSN",
    "SENTRY_ENVIRONMENT",
    "SENTRY_RELEASE",
    "SENTRY_SAMPLE_RATE",
    "SENTRY_TRACES_SAMPLE_RATE",
    "SENTRY_PROFILES_SAMPLE_RATE",
    "SENTRY_ENABLE_LOGS",
    "SENTRY_DEBUG",
)


@pytest.fixture(autouse=True)
def clear_sentry_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prevent external Sentry settings from leaking into offline tests.

    Args:
        monkeypatch: Pytest monkeypatch fixture used to isolate process
            environment changes.
    """
    for key in _SENTRY_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
