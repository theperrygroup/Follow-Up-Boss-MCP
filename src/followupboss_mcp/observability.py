"""Sentry observability helpers."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol, cast

from followupboss_mcp.config import SentrySettings, TransportMode
from followupboss_mcp.logging import redact_value

_REDACTED = "***redacted***"
_SENTRY_INITIALIZED = False
_SENTRY_REDACTED_KEYS = {
    "address",
    "addresses",
    "body",
    "cookie",
    "cookies",
    "data",
    "email",
    "emails",
    "form",
    "json",
    "note",
    "notes",
    "person",
    "people",
    "phone",
    "phones",
    "secretref",
    "task",
    "tasks",
    "tenantsecretref",
}

type SentryEvent = dict[str, object]
type SentryHint = Mapping[str, object]


class SentrySdkModule(Protocol):
    """Protocol for the subset of the Sentry SDK used by this project."""

    def init(self, **kwargs: object) -> object:
        """Initialize the Sentry SDK."""

    def set_tag(self, key: str, value: str) -> None:
        """Attach a global tag to future events."""


def _load_sentry_sdk() -> SentrySdkModule:
    """Import and return the Sentry SDK lazily.

    Returns:
        The imported Sentry SDK module.
    """
    import sentry_sdk

    return cast(SentrySdkModule, sentry_sdk)


def _normalize_sentry_key(key: object) -> str:
    """Normalize one event key for deny-list comparisons.

    Args:
        key: The raw event key.

    Returns:
        A lowercase key with punctuation removed for stable matching.
    """
    return str(key).replace("-", "").replace("_", "").lower()


def _redact_sentry_payload(value: object) -> object:
    """Return a Sentry payload copy with customer data fields redacted.

    Args:
        value: The event payload value to sanitize.

    Returns:
        A sanitized copy of the value with high-risk Follow Up Boss data fields
        replaced by a stable redaction marker.
    """
    if isinstance(value, dict):
        redacted_payload: dict[str, object] = {}
        for key, inner_value in value.items():
            normalized_key = _normalize_sentry_key(key)
            if normalized_key in _SENTRY_REDACTED_KEYS:
                redacted_payload[str(key)] = _REDACTED
            else:
                redacted_payload[str(key)] = _redact_sentry_payload(inner_value)
        return redacted_payload
    if isinstance(value, list):
        return [_redact_sentry_payload(item) for item in value]
    return value


def sanitize_sentry_event(event: Mapping[str, object]) -> SentryEvent:
    """Return a privacy-safe Sentry event copy.

    Args:
        event: The raw Sentry event.

    Returns:
        A sanitized event copy with known secret values and high-risk customer
        payload fields redacted.
    """
    secret_redacted_event = redact_value(dict(event))
    return cast(SentryEvent, _redact_sentry_payload(secret_redacted_event))


def before_send(event: SentryEvent, hint: SentryHint) -> SentryEvent | None:
    """Sanitize one Sentry event before submission.

    Args:
        event: The raw Sentry event.
        hint: Sentry hint metadata for the event. The current sanitizer does not
            need hint data, but the argument is part of the SDK hook contract.

    Returns:
        The sanitized Sentry event.
    """
    del hint
    return sanitize_sentry_event(event)


def configure_sentry(
    settings: SentrySettings | None = None,
    *,
    entrypoint: str,
    transport: TransportMode | None = None,
) -> bool:
    """Initialize Sentry when a DSN is configured.

    Args:
        settings: Optional Sentry settings. When omitted, settings are loaded
            from environment variables.
        entrypoint: Stable runtime entrypoint name to attach to events.
        transport: Optional MCP transport name to attach to events.

    Returns:
        `True` when Sentry is enabled or was already initialized, otherwise
        `False`.
    """
    global _SENTRY_INITIALIZED  # noqa: PLW0603

    resolved_settings = settings or SentrySettings()
    if not resolved_settings.enabled:
        return False
    if _SENTRY_INITIALIZED:
        return True

    sentry_sdk = _load_sentry_sdk()
    sentry_sdk.init(
        dsn=resolved_settings.dsn,
        environment=resolved_settings.environment,
        release=resolved_settings.release,
        sample_rate=resolved_settings.error_sample_rate,
        traces_sample_rate=resolved_settings.traces_sample_rate,
        profiles_sample_rate=resolved_settings.profiles_sample_rate,
        enable_logs=resolved_settings.enable_logs,
        debug=resolved_settings.debug,
        send_default_pii=False,
        include_local_variables=False,
        max_request_body_size="never",
        before_send=before_send,
        in_app_include=["followupboss_mcp"],
    )
    sentry_sdk.set_tag("entrypoint", entrypoint)
    if transport is not None:
        sentry_sdk.set_tag("transport", transport)
    _SENTRY_INITIALIZED = True
    return True
