"""Malformed person updates must fail locally without hiding provider failures."""

from __future__ import annotations

import json

import httpx
import pytest

from followupboss_mcp.config import FollowUpBossSettings
from followupboss_mcp.http_client import FollowUpBossAsyncClient
from followupboss_mcp.mcp_server import create_server
from mcp.server.mcpserver.exceptions import ToolError, UnexpectedToolError


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("arguments", "guidance"),
    [
        ({"addresses": [{"0": "invalid"}]}, "named fields"),
        ({"emails": [{"value": "test@example.com", "0": "invalid"}]}, "named fields"),
        ({"phones": [{"value": "555-0100", "1": "invalid"}]}, "named fields"),
        ({"custom_fields": {"0": "invalid"}}, "followupboss_list_custom_fields"),
        ({"custom_fields": {"Closing Date": "2026-10-01"}}, "followupboss_list_custom_fields"),
    ],
)
async def test_update_person_rejects_malformed_fields_before_http(
    arguments: dict[str, object], guidance: str
) -> None:
    """Reach the real registered tool, adapter, service, and HTTP boundary."""
    requests: list[httpx.Request] = []

    def upstream(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(400, json={"errorMessage": "Invalid fields in the request body: 0."})

    settings = FollowUpBossSettings.model_validate({"api_key": "test-key", "max_retries": 0})
    async with httpx.AsyncClient(
        base_url=str(settings.base_url), transport=httpx.MockTransport(upstream)
    ) as http_client:
        client = FollowUpBossAsyncClient(settings, http_client=http_client)
        server = create_server(settings, client=client)

        with pytest.raises(ToolError, match=guidance) as exc_info:
            await server.call_tool("followupboss_update_person", {"person_id": 42, **arguments})

    assert not isinstance(exc_info.value, UnexpectedToolError)
    assert requests == []


@pytest.mark.asyncio
async def test_update_person_preserves_supported_fields_and_provider_errors() -> None:
    """Do not turn a provider rejecting a valid-looking request into hidden noise."""
    bodies: list[dict[str, object]] = []

    def upstream(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
        return httpx.Response(400, json={"errorMessage": "Invalid fields in the request body: 0."})

    settings = FollowUpBossSettings.model_validate({"api_key": "test-key", "max_retries": 0})
    async with httpx.AsyncClient(
        base_url=str(settings.base_url), transport=httpx.MockTransport(upstream)
    ) as http_client:
        client = FollowUpBossAsyncClient(settings, http_client=http_client)
        server = create_server(settings, client=client)

        with pytest.raises(UnexpectedToolError):
            await server.call_tool(
                "followupboss_update_person",
                {
                    "person_id": 42,
                    "addresses": [{"street": "Example", "country": "US", "type": "home"}],
                    "emails": [{"value": "test@example.com", "id": 7}],
                    "phones": [{"value": "555-0100", "type": "mobile"}],
                    "custom_fields": {"customClosingDate": None},
                },
            )

    assert bodies == [
        {
            "addresses": [{"street": "Example", "country": "US", "type": "home"}],
            "emails": [{"value": "test@example.com", "id": 7}],
            "phones": [{"value": "555-0100", "type": "mobile"}],
            "customClosingDate": None,
        }
    ]
