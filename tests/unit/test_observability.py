"""Tests for Sentry observability helpers."""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from followupboss_mcp import observability
from followupboss_mcp.config import SentrySettings
from followupboss_mcp.observability import before_send, configure_sentry, sanitize_sentry_event

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


def _clear_sentry_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove Sentry environment variables from one test case.

    Args:
        monkeypatch: Pytest monkeypatch fixture used to isolate process
            environment changes.
    """
    for key in _SENTRY_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


def test_sentry_settings_normalize_and_validate() -> None:
    """Sentry settings should normalize optional fields and validate sample rates."""
    settings = SentrySettings.model_validate(
        {
            "dsn": " https://public@example.com/1 ",
            "environment": " staging ",
            "release": " followupboss-mcp@0.1.0 ",
            "error_sample_rate": 0.75,
            "traces_sample_rate": 0.2,
            "profiles_sample_rate": 0.1,
            "enable_logs": True,
            "debug": True,
        }
    )

    assert settings.enabled is True
    assert settings.dsn == "https://public@example.com/1"
    assert settings.environment == "staging"
    assert settings.release == "followupboss-mcp@0.1.0"
    assert settings.error_sample_rate == 0.75
    assert settings.traces_sample_rate == 0.2
    assert settings.profiles_sample_rate == 0.1
    assert settings.enable_logs is True
    assert settings.debug is True

    disabled_settings = SentrySettings.model_validate(
        {
            "dsn": " ",
            "release": " ",
            "traces_sample_rate": " ",
            "profiles_sample_rate": "",
        }
    )
    assert disabled_settings.enabled is False
    assert disabled_settings.dsn is None
    assert disabled_settings.release is None
    assert disabled_settings.traces_sample_rate is None
    assert disabled_settings.profiles_sample_rate is None

    with pytest.raises(ValidationError, match="environment must not be empty"):
        SentrySettings.model_validate({"environment": " "})
    with pytest.raises(ValidationError, match="error_sample_rate must be between 0.0 and 1.0"):
        SentrySettings.model_validate({"error_sample_rate": 1.1})
    with pytest.raises(ValidationError, match="traces_sample_rate must be between 0.0 and 1.0"):
        SentrySettings.model_validate({"traces_sample_rate": -0.1})
    with pytest.raises(ValidationError, match="profiles_sample_rate must be between 0.0 and 1.0"):
        SentrySettings.model_validate({"profiles_sample_rate": 2.0})


def test_sanitize_sentry_event_redacts_secrets_and_customer_payloads() -> None:
    """Sentry event sanitization should remove secret and customer payload fields."""
    event: dict[str, object] = {
        "message": "safe top-level message",
        "request": {
            "headers": {
                "Authorization": "secret-token",
                "X-System-Key": "system-secret",
                "Accept": "application/json",
            },
            "data": {
                "email": "person@example.com",
                "phone": "555-0100",
            },
            "cookies": {"session": "secret-session"},
        },
        "extra": {
            "person": {"name": "Ada Lovelace"},
            "tasks": [{"subject": "Call lead"}],
            "tenant_secret_ref": "arn:aws:secretsmanager:secret",
            "apiKey": "follow-up-boss-secret",
            "exception_value": "Hosted runtime failed token=super-secret-token",
            "next_token": "pagination-token",
            "items": [{"note": "private note"}, "kept-scalar"],
        },
    }

    sanitized = sanitize_sentry_event(event)

    assert sanitized["message"] == "safe top-level message"
    request = sanitized["request"]
    assert isinstance(request, dict)
    assert request["headers"] == {
        "Authorization": "***redacted***",
        "X-System-Key": "***redacted***",
        "Accept": "application/json",
    }
    assert request["data"] == "***redacted***"
    assert request["cookies"] == "***redacted***"
    extra = sanitized["extra"]
    assert isinstance(extra, dict)
    assert extra["person"] == "***redacted***"
    assert extra["tasks"] == "***redacted***"
    assert extra["tenant_secret_ref"] == "***redacted***"
    assert extra["apiKey"] == "***redacted***"
    assert extra["exception_value"] == "Hosted runtime failed token=***redacted***"
    assert extra["next_token"] == "pagination-token"
    assert extra["items"] == [{"note": "***redacted***"}, "kept-scalar"]

    assert before_send(event, {"exc_info": object()}) == sanitized


def test_configure_sentry_skips_initialization_without_dsn(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Sentry initialization should be disabled when no DSN is configured."""
    observability._SENTRY_INITIALIZED = False
    _clear_sentry_env(monkeypatch)

    def fail_load_sentry_sdk() -> object:
        """Fail if disabled Sentry configuration imports the SDK."""
        raise AssertionError("Sentry SDK should not be imported without a DSN.")

    monkeypatch.setattr(observability, "_load_sentry_sdk", fail_load_sentry_sdk)

    enabled = configure_sentry(SentrySettings.model_validate({}), entrypoint="followupboss-mcp")

    assert enabled is False
    assert observability._SENTRY_INITIALIZED is False


def test_configure_sentry_ignores_blank_optional_rates_without_dsn(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Disabled Sentry startup should tolerate blank optional rate placeholders."""
    observability._SENTRY_INITIALIZED = False
    _clear_sentry_env(monkeypatch)
    monkeypatch.setenv("SENTRY_TRACES_SAMPLE_RATE", "")
    monkeypatch.setenv("SENTRY_PROFILES_SAMPLE_RATE", "")

    def fail_load_sentry_sdk() -> object:
        """Fail if disabled Sentry configuration imports the SDK."""
        raise AssertionError("Sentry SDK should not be imported without a DSN.")

    monkeypatch.setattr(observability, "_load_sentry_sdk", fail_load_sentry_sdk)

    enabled = configure_sentry(entrypoint="followupboss-mcp")

    assert enabled is False
    assert observability._SENTRY_INITIALIZED is False


def test_configure_sentry_initializes_once_and_sets_safe_options(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Configured Sentry should initialize once with privacy-safe options."""
    observability._SENTRY_INITIALIZED = False
    init_calls: list[dict[str, Any]] = []
    tag_calls: list[tuple[str, str]] = []

    class FakeSentrySdk:
        """Sentry SDK stand-in that records initialization calls."""

        def init(self, **kwargs: object) -> object:
            """Record one SDK initialization call."""
            init_calls.append(dict(kwargs))
            return None

        def set_tag(self, key: str, value: str) -> None:
            """Record one global tag call."""
            tag_calls.append((key, value))

    monkeypatch.setattr(observability, "_load_sentry_sdk", FakeSentrySdk)

    settings = SentrySettings.model_validate(
        {
            "dsn": "https://public@example.com/1",
            "environment": "staging",
            "release": "followupboss-mcp@0.1.0",
            "error_sample_rate": 0.5,
            "traces_sample_rate": 0.25,
            "profiles_sample_rate": 0.1,
            "enable_logs": True,
            "debug": True,
        }
    )

    assert (
        configure_sentry(
            settings,
            entrypoint="followupboss-mcp-hosted",
            transport="streamable-http",
        )
        is True
    )
    assert configure_sentry(settings, entrypoint="ignored") is True

    assert len(init_calls) == 1
    init_kwargs = init_calls[0]
    assert init_kwargs["dsn"] == "https://public@example.com/1"
    assert init_kwargs["environment"] == "staging"
    assert init_kwargs["release"] == "followupboss-mcp@0.1.0"
    assert init_kwargs["sample_rate"] == 0.5
    assert init_kwargs["traces_sample_rate"] == 0.25
    assert init_kwargs["profiles_sample_rate"] == 0.1
    assert init_kwargs["enable_logs"] is True
    assert init_kwargs["debug"] is True
    assert init_kwargs["send_default_pii"] is False
    assert init_kwargs["include_local_variables"] is False
    assert init_kwargs["max_request_body_size"] == "never"
    assert init_kwargs["before_send"] is before_send
    assert init_kwargs["in_app_include"] == ["followupboss_mcp"]
    assert tag_calls == [
        ("entrypoint", "followupboss-mcp-hosted"),
        ("transport", "streamable-http"),
    ]


def test_configure_sentry_allows_missing_transport_tag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Sentry initialization should allow callers without a transport tag."""
    observability._SENTRY_INITIALIZED = False
    tag_calls: list[tuple[str, str]] = []

    class FakeSentrySdk:
        """Sentry SDK stand-in for no-transport initialization."""

        def init(self, **kwargs: object) -> object:
            """Accept initialization options."""
            return kwargs

        def set_tag(self, key: str, value: str) -> None:
            """Record one global tag call."""
            tag_calls.append((key, value))

    monkeypatch.setattr(observability, "_load_sentry_sdk", FakeSentrySdk)

    assert (
        configure_sentry(
            SentrySettings.model_validate({"dsn": "https://public@example.com/1"}),
            entrypoint="custom-entrypoint",
        )
        is True
    )
    assert tag_calls == [("entrypoint", "custom-entrypoint")]


def test_load_sentry_sdk_imports_real_module() -> None:
    """The lazy loader should import the installed Sentry SDK."""
    loaded_sdk = observability._load_sentry_sdk()

    assert callable(loaded_sdk.init)
    assert callable(loaded_sdk.set_tag)
