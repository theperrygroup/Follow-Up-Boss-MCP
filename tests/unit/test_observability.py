"""Tests for Sentry observability helpers."""

from __future__ import annotations

from typing import Any, cast

import pytest
from pydantic import ValidationError

from followupboss_mcp import observability
from followupboss_mcp.config import SentrySettings
from followupboss_mcp.observability import (
    before_send,
    capture_sentry_exception,
    capture_sentry_message,
    configure_sentry,
    flush_sentry,
    sanitize_sentry_event,
    set_sentry_tags,
)

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


def _event_tags(event: dict[str, object] | None) -> dict[str, object]:
    """Return one Sentry event's tags after asserting the event was kept."""
    assert event is not None
    tags = event.get("tags")
    assert isinstance(tags, dict)
    return cast(dict[str, object], tags)


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


def test_before_send_tags_expected_tool_validation_errors() -> None:
    """Handled FastMCP validation ToolErrors should be tagged but kept."""
    event: dict[str, object] = {
        "tags": {"entrypoint": "followupboss-mcp-hosted"},
        "exception": {
            "values": [
                {
                    "type": "ValidationError",
                    "value": "1 validation error for CreateTaskRequest",
                    "mechanism": {"handled": True},
                },
                {
                    "type": "ToolError",
                    "value": (
                        "Error executing tool followupboss_create_task: "
                        "1 validation error for CreateTaskRequest"
                    ),
                    "mechanism": {"handled": True},
                },
            ]
        },
    }

    tags = _event_tags(before_send(event, {"exc_info": object()}))

    assert tags["entrypoint"] == "followupboss-mcp-hosted"
    assert tags["mcp_tool_name"] == "followupboss_create_task"
    assert tags["mcp_error_expected"] == "true"
    assert tags["mcp_error_kind"] == "validation"


@pytest.mark.parametrize(
    ("error_type", "message", "expected_kind"),
    [
        (
            "FollowUpBossValidationError",
            "Deep pagination disabled, use 'nextLink' url.",
            "followupboss_validation",
        ),
        (
            "FollowUpBossForbiddenError",
            "You do not have access to delete pipelines.",
            "followupboss_forbidden",
        ),
        (
            "FollowUpBossNotFoundError",
            "Requested resource was not found.",
            "followupboss_not_found",
        ),
        (
            "RuntimeError",
            "Smart list named '0-3 Months' was not found.",
            "missing_smart_list",
        ),
    ],
)
def test_before_send_tags_expected_client_tool_errors(
    error_type: str,
    message: str,
    expected_kind: str,
) -> None:
    """Handled client/upstream ToolErrors should be tagged by kind and kept."""
    event: dict[str, object] = {
        "exception": {
            "values": [
                {
                    "type": error_type,
                    "value": message,
                    "mechanism": {"handled": True},
                },
                {
                    "type": "ToolError",
                    "value": f"Error executing tool followupboss_search_people: {message}",
                    "mechanism": {"handled": True},
                },
            ]
        },
    }

    tags = _event_tags(before_send(event, {"exc_info": object()}))

    assert tags["mcp_tool_name"] == "followupboss_search_people"
    assert tags["mcp_error_expected"] == "true"
    assert tags["mcp_error_kind"] == expected_kind


def test_before_send_tags_unknown_tool_errors_as_unexpected() -> None:
    """Unknown FastMCP ToolErrors should remain visible as unexpected."""
    event: dict[str, object] = {
        "exception": {
            "values": [
                {
                    "type": "RuntimeError",
                    "value": "Unexpected repo-owned failure",
                    "mechanism": {"handled": True},
                },
                {
                    "type": "ToolError",
                    "value": (
                        "Error executing tool followupboss_get_identity: "
                        "Unexpected repo-owned failure"
                    ),
                    "mechanism": {"handled": True},
                },
            ]
        },
    }

    tags = _event_tags(before_send(event, {"exc_info": object()}))

    assert tags["mcp_tool_name"] == "followupboss_get_identity"
    assert tags["mcp_error_expected"] == "false"
    assert tags["mcp_error_kind"] == "tool_error"


@pytest.mark.parametrize(
    ("error_type", "handled", "expected_kind"),
    [
        ("ClosedResourceError", True, "closed_resource"),
        ("AdminShutdown", False, "admin_shutdown"),
    ],
)
def test_before_send_tags_expected_infrastructure_noise(
    error_type: str,
    handled: bool,
    expected_kind: str,
) -> None:
    """Known staging infrastructure noise should be tagged and kept."""
    event: dict[str, object] = {
        "exception": {
            "values": [
                {
                    "type": error_type,
                    "value": "terminating connection due to administrator command",
                    "mechanism": {"handled": handled},
                }
            ]
        },
    }

    tags = _event_tags(before_send(event, {"exc_info": object()}))

    assert "mcp_tool_name" not in tags
    assert tags["mcp_error_expected"] == "true"
    assert tags["mcp_error_kind"] == expected_kind


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
        ("entrypoint", "ignored"),
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


def test_sentry_capture_helpers_noop_when_sentry_is_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Explicit Sentry helpers should avoid SDK imports until Sentry is initialized."""
    observability._SENTRY_INITIALIZED = False

    def fail_load_sentry_sdk() -> object:
        """Fail if disabled helper calls import the SDK."""
        raise AssertionError("Sentry SDK should not be imported while disabled.")

    monkeypatch.setattr(observability, "_load_sentry_sdk", fail_load_sentry_sdk)

    assert set_sentry_tags({"route": "/mcp"}) is False
    assert capture_sentry_exception(RuntimeError("boom")) is None
    assert capture_sentry_message("hosted runtime failed") is None
    assert flush_sentry() is False


def test_sentry_capture_helpers_attach_sanitized_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Explicit Sentry captures should use scoped, redacted metadata."""
    observability._SENTRY_INITIALIZED = True
    scopes: list[FakeScope] = []
    captured_exceptions: list[BaseException] = []
    captured_messages: list[tuple[str, str | None]] = []
    tag_calls: list[tuple[str, str]] = []
    flush_calls: list[float | None] = []

    class FakeScope:
        """Sentry event scope stand-in that records metadata."""

        def __init__(self) -> None:
            """Initialize empty scope metadata."""
            self.tags: list[tuple[str, str]] = []
            self.extras: list[tuple[str, object]] = []

        def set_tag(self, key: str, value: str) -> None:
            """Record one event-local tag."""
            self.tags.append((key, value))

        def set_extra(self, key: str, value: object) -> None:
            """Record one event-local extra field."""
            self.extras.append((key, value))

    class FakeScopeContext:
        """Context manager that yields a fake Sentry scope."""

        def __init__(self) -> None:
            """Create a scope for one capture."""
            self.scope = FakeScope()
            scopes.append(self.scope)

        def __enter__(self) -> FakeScope:
            """Return the event-local fake scope."""
            return self.scope

        def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
            """Accept context manager exit metadata."""
            del exc_type, exc, traceback

    class FakeSentrySdk:
        """Sentry SDK stand-in for explicit capture helpers."""

        def capture_exception(self, error: BaseException) -> str:
            """Record one captured exception."""
            captured_exceptions.append(error)
            return "exception-event-id"

        def capture_message(self, message: str, level: str | None = None) -> str:
            """Record one captured message."""
            captured_messages.append((message, level))
            return "message-event-id"

        def flush(self, timeout: float | None = None) -> None:
            """Record one flush call."""
            flush_calls.append(timeout)

        def init(self, **kwargs: object) -> object:
            """Accept initialization options."""
            return kwargs

        def new_scope(self) -> FakeScopeContext:
            """Return a fake scoped capture context."""
            return FakeScopeContext()

        def set_tag(self, key: str, value: str) -> None:
            """Record one global tag."""
            tag_calls.append((key, value))

    monkeypatch.setattr(observability, "_load_sentry_sdk", FakeSentrySdk)
    error = RuntimeError("Hosted runtime failed token=super-secret-token")

    assert (
        capture_sentry_exception(
            error,
            tags={"route": "/oauth/token", "retryable": True, "omitted": None},
            extras={
                "Authorization": "Bearer oauth-secret",
                "payload": {"email": "person@example.com"},
            },
        )
        == "exception-event-id"
    )
    assert (
        capture_sentry_message(
            "hosted_rate_limit_backend_failed",
            level="warning",
            tags={"failure_mode": "open"},
            extras={"api_key": "secret-key"},
        )
        == "message-event-id"
    )
    assert set_sentry_tags({"entrypoint": "hosted", "enabled": True, "omitted": None}) is True
    assert flush_sentry(timeout=0.5) is True

    assert captured_exceptions == [error]
    assert captured_messages == [("hosted_rate_limit_backend_failed", "warning")]
    assert scopes[0].tags == [("route", "/oauth/token"), ("retryable", "true")]
    assert scopes[0].extras == [
        ("Authorization", "***redacted***"),
        ("payload", {"email": "***redacted***"}),
    ]
    assert scopes[1].tags == [("failure_mode", "open")]
    assert scopes[1].extras == [("api_key", "***redacted***")]
    assert tag_calls == [("entrypoint", "hosted"), ("enabled", "true")]
    assert flush_calls == [0.5]


def test_sentry_scope_metadata_falls_back_to_value_redaction(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Scoped metadata should still redact values if event sanitization is unavailable."""

    class FakeScope:
        """Sentry scope stand-in for direct metadata helper coverage."""

        def __init__(self) -> None:
            """Initialize recorded extra fields."""
            self.extras: list[tuple[str, object]] = []

        def set_extra(self, key: str, value: object) -> None:
            """Record one extra field."""
            self.extras.append((key, value))

        def set_tag(self, key: str, value: str) -> None:
            """Accept unused tag metadata."""
            del key, value

    def sanitize_without_extra(event: dict[str, object]) -> dict[str, object]:
        """Return no sanitized extra payload to exercise fallback redaction."""
        del event
        return {}

    scope = FakeScope()
    monkeypatch.setattr(observability, "sanitize_sentry_event", sanitize_without_extra)

    observability._set_sentry_scope_metadata(scope, tags=None, extras=None)
    observability._set_sentry_scope_metadata(
        scope,
        tags=None,
        extras={"failure": "Runtime failed with Bearer oauth-secret"},
    )

    assert scope.extras == [("failure", "Runtime failed with Bearer ***redacted***")]


def test_load_sentry_sdk_imports_real_module() -> None:
    """The lazy loader should import the installed Sentry SDK."""
    loaded_sdk = observability._load_sentry_sdk()

    assert callable(loaded_sdk.init)
    assert callable(loaded_sdk.set_tag)
