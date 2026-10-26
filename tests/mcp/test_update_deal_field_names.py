"""Deal updates send commission fields under the names Follow Up Boss accepts."""

from __future__ import annotations

import json

import httpx
import pytest

from followupboss_mcp.config import FollowUpBossSettings
from followupboss_mcp.http_client import FollowUpBossAsyncClient
from followupboss_mcp.mcp_server import create_server
from followupboss_mcp.models.deals import CreateDealRequest, UpdateDealRequest


@pytest.mark.asyncio
async def test_update_deal_sends_correctly_spelled_commission_fields() -> None:
    """The PUT body names agentCommission and teamCommission, not the rejected typos."""
    requests: list[httpx.Request] = []

    def upstream(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path.endswith("/identity"):
            return httpx.Response(200, json={"id": 1})
        return httpx.Response(200, json={"id": 4321, "name": "Example deal"})

    settings = FollowUpBossSettings.model_validate({"api_key": "test-key", "max_retries": 0})
    async with httpx.AsyncClient(
        base_url=str(settings.base_url), transport=httpx.MockTransport(upstream)
    ) as http_client:
        client = FollowUpBossAsyncClient(settings, http_client=http_client)
        server = create_server(settings, client=client)
        await server.call_tool(
            "followupboss_update_deal",
            {"deal_id": 4321, "agent_commission": 7500, "team_commission": 2500},
        )

    writes = [request for request in requests if request.method == "PUT"]
    assert len(writes) == 1
    assert writes[0].url.path.endswith("/deals/4321")
    assert json.loads(writes[0].content) == {"agentCommission": 7500, "teamCommission": 2500}


def test_deal_create_and_update_send_shared_fields_under_one_name() -> None:
    """Every field the two deal write models share serializes under the same name."""
    create_fields = CreateDealRequest.model_fields
    update_fields = UpdateDealRequest.model_fields
    shared = sorted(create_fields.keys() & update_fields.keys())

    mismatched = {
        name: (create_fields[name].serialization_alias, update_fields[name].serialization_alias)
        for name in shared
        if create_fields[name].serialization_alias != update_fields[name].serialization_alias
    }

    assert {"agent_commission", "team_commission"} <= set(shared)
    assert mismatched == {}
