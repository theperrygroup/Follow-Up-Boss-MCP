"""Structured logging helpers with secret redaction."""

from __future__ import annotations

import json
import logging
import re
import sys
from collections.abc import Mapping
from typing import Any

from followupboss_mcp.constants import HEADER_AUTHORIZATION, HEADER_SYSTEM_KEY
from followupboss_mcp.errors import (
    TenantCredentialNotFoundError,
    TenantCredentialRevokedError,
    TenantDisabledError,
    TenantNotFoundError,
    TenantSecretStoreUnavailableError,
    TenantStoreError,
    TenantStoreUnavailableError,
)

_REDACTED = "***redacted***"
_SENSITIVE_HEADERS = {HEADER_AUTHORIZATION.lower(), HEADER_SYSTEM_KEY.lower()}
_SENSITIVE_VALUE_KEYS = _SENSITIVE_HEADERS | {
    "access_token",
    "accesstoken",
    "algoliakey",
    "api_key",
    "apikey",
    "callingcapabilitytoken",
    "system_key",
    "systemkey",
    "token",
    "user_hash",
}
_SENSITIVE_ASSIGNMENT_PATTERN = re.compile(
    r"\b(?P<key>access[_-]?token|api[_-]?key|authorization|password|secret|system[_-]?key|token)"
    r"=(?P<value>[^\s,;&]+)",
    re.IGNORECASE,
)
_SENSITIVE_BEARER_PATTERN = re.compile(
    r"\b(?P<prefix>Bearer)\s+(?P<value>[A-Za-z0-9._~+/=-]+)",
    re.IGNORECASE,
)


def _is_sensitive_key(key: str, *, headers_only: bool = False) -> bool:
    """Return whether one key should be redacted.

    Args:
        key: The dictionary or header key being evaluated.
        headers_only: Whether only HTTP-header keys should be considered
            sensitive.

    Returns:
        `True` when the key should be redacted, otherwise `False`.
    """
    normalized_key = key.lower()
    if headers_only:
        return normalized_key in _SENSITIVE_HEADERS
    return normalized_key in _SENSITIVE_VALUE_KEYS


def redact_headers(headers: dict[str, str]) -> dict[str, str]:
    """Return headers with sensitive values redacted.

    Args:
        headers: The outbound or inbound HTTP headers to sanitize.

    Returns:
        A shallow copy of `headers` with sensitive header values replaced by a
        stable redaction marker.
    """
    redacted: dict[str, str] = {}
    for key, value in headers.items():
        redacted[key] = _REDACTED if _is_sensitive_key(key, headers_only=True) else value
    return redacted


def _redact_sensitive_text(value: str) -> str:
    """Redact secret-looking assignments embedded in free-form text.

    Args:
        value: The free-form string to sanitize.

    Returns:
        A sanitized string with known credential assignment and bearer-token
        patterns replaced by the stable redaction marker.
    """

    def redact_assignment(match: re.Match[str]) -> str:
        """Redact one `key=value` secret assignment while preserving the key."""
        return f"{match.group('key')}={_REDACTED}"

    def redact_bearer(match: re.Match[str]) -> str:
        """Redact one bearer credential while preserving the auth scheme."""
        return f"{match.group('prefix')} {_REDACTED}"

    return _SENSITIVE_BEARER_PATTERN.sub(
        redact_bearer,
        _SENSITIVE_ASSIGNMENT_PATTERN.sub(redact_assignment, value),
    )


def redact_value(value: Any) -> Any:
    """Redact known secret-looking values from arbitrary nested data.

    Args:
        value: The arbitrary nested value to sanitize for logs.

    Returns:
        A recursively redacted copy of the value when known secret-like keys are
        present.
    """
    if isinstance(value, dict):
        return {
            key: _REDACTED if _is_sensitive_key(key) else redact_value(inner)
            for key, inner in value.items()
        }
    if isinstance(value, list):
        return [redact_value(item) for item in value]
    if isinstance(value, str):
        return _redact_sensitive_text(value)
    return value


def _compact_audit_fields(fields: Mapping[str, object]) -> dict[str, object]:
    """Drop empty audit fields while preserving falsy-but-meaningful values.

    Args:
        fields: Candidate audit fields for one audit event.

    Returns:
        A dictionary containing only non-`None` audit fields.
    """
    return {key: value for key, value in fields.items() if value is not None}


def emit_audit_event(
    logger: logging.Logger | None,
    *,
    event: str,
    fields: Mapping[str, object] | None = None,
) -> None:
    """Emit one machine-readable audit event through the configured logger.

    Args:
        logger: The base logger used for application logging. When provided, the
            audit event is emitted through a child audit logger so handler
            configuration remains shared.
        event: A stable machine-readable audit event name.
        fields: Optional non-secret audit fields to include with the event.
    """
    payload: dict[str, object] = {"event": event}
    if fields is not None:
        payload.update(_compact_audit_fields(fields))

    resolved_logger = (
        logger.getChild("audit")
        if logger is not None
        else logging.getLogger("followupboss_mcp.audit")
    )
    resolved_logger.info(
        "AUDIT %s",
        json.dumps(redact_value(payload), sort_keys=True, default=str),
    )


def tenant_store_error_reason(error: TenantStoreError) -> str:
    """Return a stable machine-readable reason for one tenant-store error.

    Args:
        error: The tenant-store exception that should be summarized.

    Returns:
        A stable reason string suitable for audit logging.
    """
    reason_by_error_type: tuple[tuple[type[TenantStoreError], str], ...] = (
        (TenantStoreUnavailableError, "tenant_store_unavailable"),
        (TenantSecretStoreUnavailableError, "tenant_secret_store_unavailable"),
        (TenantNotFoundError, "tenant_not_found"),
        (TenantDisabledError, "tenant_disabled"),
        (TenantCredentialNotFoundError, "credential_not_found"),
        (TenantCredentialRevokedError, "credential_revoked"),
    )
    for error_type, reason in reason_by_error_type:
        if isinstance(error, error_type):
            return reason
    return "tenant_store_error"


def configure_logging(level: str) -> logging.Logger:
    """Configure and return the package logger.

    Args:
        level: The textual log level to configure for the package logger.

    Returns:
        The configured package logger.
    """
    logger = logging.getLogger("followupboss_mcp")
    logger.setLevel(level)
    logger.propagate = False
    if logger.handlers:
        return logger

    handler = logging.StreamHandler(stream=sys.stderr)
    handler.setFormatter(logging.Formatter("%(levelname)s %(name)s %(message)s"))
    logger.addHandler(handler)
    return logger
