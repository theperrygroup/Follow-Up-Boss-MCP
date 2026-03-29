"""Structured logging helpers with secret redaction."""

from __future__ import annotations

import logging
import sys
from typing import Any

from followupboss_mcp.constants import HEADER_AUTHORIZATION, HEADER_SYSTEM_KEY

_REDACTED = "***redacted***"
_SENSITIVE_HEADERS = {HEADER_AUTHORIZATION.lower(), HEADER_SYSTEM_KEY.lower()}


def redact_headers(headers: dict[str, str]) -> dict[str, str]:
    """Return a copy of headers with sensitive values redacted."""
    redacted: dict[str, str] = {}
    for key, value in headers.items():
        redacted[key] = _REDACTED if key.lower() in _SENSITIVE_HEADERS else value
    return redacted


def redact_value(value: Any) -> Any:
    """Redact known secret-looking values from arbitrary data."""
    if isinstance(value, dict):
        return {
            key: _REDACTED if key.lower() in _SENSITIVE_HEADERS else redact_value(inner)
            for key, inner in value.items()
        }
    if isinstance(value, list):
        return [redact_value(item) for item in value]
    return value


def configure_logging(level: str) -> logging.Logger:
    """Configure and return the package logger."""
    logger = logging.getLogger("followupboss_mcp")
    logger.setLevel(level)
    logger.propagate = False
    if logger.handlers:
        return logger

    handler = logging.StreamHandler(stream=sys.stderr)
    handler.setFormatter(logging.Formatter("%(levelname)s %(name)s %(message)s"))
    logger.addHandler(handler)
    return logger
