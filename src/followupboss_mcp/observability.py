"""Sentry observability helpers."""

from __future__ import annotations

from collections.abc import Mapping
from contextlib import AbstractContextManager
from typing import Literal, Protocol, cast

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
type SentryExtra = Mapping[str, object]
type SentryHint = Mapping[str, object]
type SentryMessageLevel = Literal["fatal", "critical", "error", "warning", "info", "debug"]
type SentryTags = Mapping[str, str | int | float | bool | None]


class SentryScope(Protocol):
    """Protocol for the Sentry scope methods used by scoped captures."""

    def set_extra(self, key: str, value: object) -> None:
        """Attach sanitized extra data to the scoped event."""

    def set_tag(self, key: str, value: str) -> None:
        """Attach a tag to the scoped event."""


class SentrySdkModule(Protocol):
    """Protocol for the subset of the Sentry SDK used by this project."""

    def capture_exception(self, error: BaseException) -> str | None:
        """Capture one exception event."""

    def capture_message(self, message: str, level: SentryMessageLevel | None = None) -> str | None:
        """Capture one message event."""

    def flush(self, timeout: float | None = None) -> None:
        """Flush queued Sentry events."""

    def init(self, **kwargs: object) -> object:
        """Initialize the Sentry SDK."""

    def new_scope(self) -> AbstractContextManager[SentryScope]:
        """Return an isolated scope for one explicit event capture."""

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


def _stringify_sentry_tag(value: str | int | float | bool | None) -> str | None:
    """Return a stable Sentry tag value, or `None` when the tag should be skipped.

    Args:
        value: Raw tag value supplied by an instrumentation call.

    Returns:
        String tag value accepted by Sentry, or `None` for omitted tags.
    """
    if value is None:
        return None
    if isinstance(value, bool):
        return str(value).lower()
    return str(value)


def _set_sentry_tags(sentry_sdk: SentrySdkModule, tags: SentryTags) -> None:
    """Attach global Sentry tags when Sentry is enabled.

    Args:
        sentry_sdk: Imported Sentry SDK module.
        tags: Tag names and values to attach.
    """
    for key, value in tags.items():
        tag_value = _stringify_sentry_tag(value)
        if tag_value is not None:
            sentry_sdk.set_tag(key, tag_value)


def _set_sentry_scope_metadata(
    scope: SentryScope,
    *,
    tags: SentryTags | None,
    extras: SentryExtra | None,
) -> None:
    """Attach sanitized metadata to one Sentry event scope.

    Args:
        scope: The event-local Sentry scope.
        tags: Optional event tags.
        extras: Optional extra event fields.
    """
    if tags is not None:
        for key, value in tags.items():
            tag_value = _stringify_sentry_tag(value)
            if tag_value is not None:
                scope.set_tag(key, tag_value)
    if extras is not None:
        sanitized_extras = sanitize_sentry_event({"extra": dict(extras)}).get("extra", {})
        for key, extra_value in extras.items():
            if isinstance(sanitized_extras, dict) and key in sanitized_extras:
                scope.set_extra(key, sanitized_extras[key])
            else:
                scope.set_extra(key, redact_value(extra_value))


def set_sentry_tags(tags: SentryTags) -> bool:
    """Attach global Sentry tags if Sentry has been initialized.

    Args:
        tags: Tag names and values to attach to future events.

    Returns:
        `True` when tags were attached, otherwise `False` because Sentry is
        disabled in the current process.
    """
    if not _SENTRY_INITIALIZED:
        return False
    _set_sentry_tags(_load_sentry_sdk(), tags)
    return True


def capture_sentry_exception(
    exc: BaseException,
    *,
    tags: SentryTags | None = None,
    extras: SentryExtra | None = None,
) -> str | None:
    """Capture a handled exception with sanitized, event-local metadata.

    Args:
        exc: The handled exception to report.
        tags: Optional safe tags for grouping and filtering.
        extras: Optional extra metadata. Values are redacted before capture.

    Returns:
        The Sentry event identifier when Sentry accepted the event, otherwise
        `None` when Sentry is disabled.
    """
    if not _SENTRY_INITIALIZED:
        return None
    sentry_sdk = _load_sentry_sdk()
    with sentry_sdk.new_scope() as scope:
        _set_sentry_scope_metadata(scope, tags=tags, extras=extras)
        return sentry_sdk.capture_exception(exc)


def capture_sentry_message(
    message: str,
    *,
    level: SentryMessageLevel = "error",
    tags: SentryTags | None = None,
    extras: SentryExtra | None = None,
) -> str | None:
    """Capture an operational Sentry message with sanitized metadata.

    Args:
        message: Stable message text for the event.
        level: Sentry severity level.
        tags: Optional safe tags for grouping and filtering.
        extras: Optional extra metadata. Values are redacted before capture.

    Returns:
        The Sentry event identifier when Sentry accepted the event, otherwise
        `None` when Sentry is disabled.
    """
    if not _SENTRY_INITIALIZED:
        return None
    sentry_sdk = _load_sentry_sdk()
    with sentry_sdk.new_scope() as scope:
        _set_sentry_scope_metadata(scope, tags=tags, extras=extras)
        return sentry_sdk.capture_message(message, level)


def flush_sentry(*, timeout: float | None = 2.0) -> bool:
    """Flush queued Sentry events if Sentry has been initialized.

    Args:
        timeout: Optional maximum seconds to wait for queued events.

    Returns:
        `True` when Sentry was initialized and flushed, otherwise `False`.
    """
    if not _SENTRY_INITIALIZED:
        return False
    _load_sentry_sdk().flush(timeout=timeout)
    return True


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
    sentry_tags: dict[str, str] = {"entrypoint": entrypoint}
    if transport is not None:
        sentry_tags["transport"] = transport
    if _SENTRY_INITIALIZED:
        _set_sentry_tags(_load_sentry_sdk(), sentry_tags)
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
    _set_sentry_tags(sentry_sdk, sentry_tags)
    _SENTRY_INITIALIZED = True
    return True
