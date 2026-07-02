"""Unit tests for hosted public URL validation helpers."""

from __future__ import annotations

from typing import cast

import pytest

import followupboss_mcp.url_validation as url_validation
from followupboss_mcp.url_validation import normalize_public_http_url, validated_public_http_url


def test_normalize_public_http_url_covers_hostlike_variants() -> None:
    """Normalize scheme-relative, IPv6 loopback, and trailing-slash variants."""
    assert str(normalize_public_http_url("//mcp.example.com/mcp", field_name="resource")) == (
        "https://mcp.example.com/mcp"
    )
    assert str(normalize_public_http_url("[::1]:8000/mcp", field_name="resource")) == (
        "http://[::1]:8000/mcp"
    )
    assert (
        str(
            normalize_public_http_url(
                "mcp.example.com/mcp/",
                field_name="resource",
                strip_trailing_slash=False,
            )
        )
        == "https://mcp.example.com/mcp/"
    )


def test_normalize_public_http_url_rejects_blank_and_preserves_non_strings() -> None:
    """Handle blank and non-string inputs on the Pydantic validator path."""
    raw_value = object()
    assert normalize_public_http_url(raw_value, field_name="resource") is raw_value
    assert url_validation._host_looks_loopback(None) is False
    assert url_validation._host_from_authority("[::1") == "["

    with pytest.raises(ValueError, match="must not be empty"):
        normalize_public_http_url(" ", field_name="resource")
    with pytest.raises(ValueError, match="template placeholders"):
        normalize_public_http_url("https://mcp.example.com/{tenant}", field_name="resource")
    with pytest.raises(ValueError, match="must use HTTPS"):
        normalize_public_http_url("http://mcp.example.com/mcp", field_name="resource")


def test_validated_public_http_url_requires_url_string() -> None:
    """Raise a type error if a non-string value reaches the strict helper."""
    with pytest.raises(TypeError, match="URL string"):
        validated_public_http_url(cast(str, object()), field_name="resource")
