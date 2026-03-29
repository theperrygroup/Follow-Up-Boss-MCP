"""Contract tests for edge-case behavior in shared production utilities."""

from __future__ import annotations

from datetime import UTC, datetime

import httpx
import pytest
from pydantic import ValidationError

from followupboss_mcp.config import FollowUpBossSettings
from followupboss_mcp.http_client import FollowUpBossAsyncClient
from followupboss_mcp.pagination import PaginationMetadata, parse_pagination_metadata
from followupboss_mcp.rate_limits import parse_retry_after


def test_settings_invalid_log_levels_raise_clear_errors() -> None:
    """Settings validation should reject invalid log-level values."""
    with pytest.raises(ValidationError, match="log_level must be one of DEBUG"):
        FollowUpBossSettings.model_validate({"api_key": "key", "log_level": "verbose"})
    with pytest.raises(TypeError, match="log_level must be a string"):
        FollowUpBossSettings.model_validate({"api_key": "key", "log_level": 1})


def test_pagination_and_retry_after_edge_contracts() -> None:
    """Shared pagination and rate-limit helpers should cover sparse edge shapes."""
    metadata = parse_pagination_metadata(
        {"_metadata": {"limit": 10, "offset": 4, "total": "not-a-number"}},
        item_count=2,
    )
    assert metadata == PaginationMetadata(
        count=2,
        limit=10,
        next_token=None,
        next_link=None,
        offset=4,
        total=None,
    )
    assert metadata.has_next() is False

    now = datetime(2026, 3, 28, tzinfo=UTC)
    assert parse_retry_after("Sun, 29 Mar 2026 00:00:00", now=now) == 86400.0


@pytest.mark.asyncio
async def test_http_client_private_helpers_cover_error_and_header_branches() -> None:
    """Private client helpers should preserve documented header and error behavior."""
    client = FollowUpBossAsyncClient(FollowUpBossSettings.model_validate({"api_key": "key"}))

    headers = client._build_headers(headers={"X-Test": "value"}, has_json_body=True)
    assert headers["Content-Type"] == "application/json"
    assert headers["X-Test"] == "value"
    with pytest.raises(ValueError, match="Authorization"):
        client._build_headers(headers={"Authorization": "Bearer bad"}, has_json_body=False)

    assert client._error_payload(httpx.Response(500, content=b"")) is None
    assert client._error_payload(httpx.Response(500, content=b"not-json")) is None
    assert (
        client._error_message(httpx.Response(400, json={"detail": "bad"}), {"detail": "bad"})
        == "Follow Up Boss returned HTTP 400."
    )

    await client.aclose()
