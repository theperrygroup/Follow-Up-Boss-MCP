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

_DEFAULT_TIMEZONE_ENV_KEYS = (
    "FOLLOWUPBOSS_DEFAULT_TIMEZONE",
    "FOLLOW_UP_BOSS_DEFAULT_TIMEZONE",
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


@pytest.fixture(autouse=True)
def clear_default_timezone_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prevent a developer's default-timezone setting from leaking into tests.

    Args:
        monkeypatch: Pytest monkeypatch fixture used to isolate process
            environment changes so naive datetimes are not silently localized
            unless a test opts in.
    """
    for key in _DEFAULT_TIMEZONE_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
