"""Person and task updates that set no field fail locally before any request."""

from __future__ import annotations

import json
from collections.abc import Callable

import httpx
import pytest

from followupboss_mcp.config import FollowUpBossSettings
from followupboss_mcp.http_client import FollowUpBossAsyncClient
from followupboss_mcp.mcp_server import create_server
from mcp.server.mcpserver.exceptions import ToolError, UnexpectedToolError

type Upstream = Callable[[httpx.Request], httpx.Response]

_TASK_FIELDS = (
    "assigned_to, assigned_user_id, due_date, due_date_time, is_completed, name, person_id, type"
)
_PERSON_FIELDS = (
    "addresses, assigned_lender_id, assigned_lender_name, assigned_pond_id, assigned_to, "
    "assigned_user_id, background, contacted, custom_fields, emails, first_name, last_name, "
    "phones, price, stage, tags, timeframe_id"
)


async def _call_tool(tool_name: str, arguments: dict[str, object], upstream: Upstream) -> None:
    """Call one registered tool through the real adapter, service, and HTTP client.

    Args:
        tool_name: The registered MCP tool name.
        arguments: Tool arguments sent by the MCP caller.
        upstream: Fake Follow Up Boss HTTP handler.
    """
    settings = FollowUpBossSettings.model_validate({"api_key": "test-key", "max_retries": 0})
    async with httpx.AsyncClient(
        base_url=str(settings.base_url), transport=httpx.MockTransport(upstream)
    ) as http_client:
        client = FollowUpBossAsyncClient(settings, http_client=http_client)
        server = create_server(settings, client=client)
        await server.call_tool(tool_name, arguments)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("tool_name", "arguments", "expected_message"),
    [
        (
            "followupboss_update_task",
            {"task_id": 4321},
            f"followupboss_update_task needs at least one field to change. "
            f"Set one of: {_TASK_FIELDS}.",
        ),
        (
            "followupboss_update_person",
            {"person_id": 101},
            f"followupboss_update_person needs at least one field to change. "
            f"Set one of: {_PERSON_FIELDS}. merge_tags alone changes nothing.",
        ),
        (
            "followupboss_update_person",
            {"person_id": 101, "merge_tags": True},
            "merge_tags alone changes nothing.",
        ),
        (
            "followupboss_update_person",
            {"person_id": 101, "custom_fields": {}},
            "followupboss_update_person needs at least one field to change.",
        ),
    ],
    ids=["task", "person", "person-merge-tags-only", "person-empty-custom-fields"],
)
async def test_update_that_sets_no_field_fails_before_any_request(
    monkeypatch: pytest.MonkeyPatch,
    tool_name: str,
    arguments: dict[str, object],
    expected_message: str,
) -> None:
    """An update with nothing to change is a tool error and sends no request.

    The configured timezone stops the task tool's separate timezone priming from
    reading ``/me``, so the transport records only what the update itself sends.
    """
    monkeypatch.setenv("FOLLOWUPBOSS_DEFAULT_TIMEZONE", "America/Denver")
    requests: list[httpx.Request] = []

    def upstream(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        raise AssertionError(f"Unexpected request: {request.method} {request.url.path}")

    with pytest.raises(ToolError) as exc_info:
        await _call_tool(tool_name, arguments, upstream)

    assert not isinstance(exc_info.value, UnexpectedToolError)
    assert expected_message in str(exc_info.value)
    assert requests == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("tool_name", "arguments", "path_suffix", "expected_body", "expected_params"),
    [
        (
            "followupboss_update_task",
            {"task_id": 4321, "is_completed": True},
            "/tasks/4321",
            {"isCompleted": True},
            {},
        ),
        (
            "followupboss_update_person",
            {"person_id": 101, "stage": "Lead"},
            "/people/101",
            {"stage": "Lead"},
            {},
        ),
        (
            "followupboss_update_person",
            {"person_id": 101, "tags": ["Buyer"], "merge_tags": True},
            "/people/101",
            {"tags": ["Buyer"]},
            {"mergeTags": "true"},
        ),
    ],
    ids=["task", "person", "person-tags-with-merge-tags"],
)
async def test_update_that_sets_one_field_sends_that_field(
    monkeypatch: pytest.MonkeyPatch,
    tool_name: str,
    arguments: dict[str, object],
    path_suffix: str,
    expected_body: dict[str, object],
    expected_params: dict[str, str],
) -> None:
    """The check leaves real updates alone: one field set sends one PUT with it."""
    monkeypatch.setenv("FOLLOWUPBOSS_DEFAULT_TIMEZONE", "America/Denver")
    requests: list[httpx.Request] = []

    def upstream(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"id": 1})

    await _call_tool(tool_name, arguments, upstream)

    assert len(requests) == 1
    request = requests[0]
    assert request.method == "PUT"
    assert request.url.path.endswith(path_suffix)
    assert json.loads(request.content) == expected_body
    assert dict(request.url.params) == expected_params
