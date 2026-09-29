"""Behavior-based tool classifications must reach the public MCP catalog explicitly."""

from __future__ import annotations

import json

import httpx
import pytest

from followupboss_mcp.config import FollowUpBossSettings
from followupboss_mcp.http_client import FollowUpBossAsyncClient
from followupboss_mcp.mcp_server import create_server
from mcp.client._memory import InMemoryTransport
from mcp.client.session import ClientSession
from mcp.types import CallToolResult, Tool

# This is an independent, exhaustive behavior partition, not a name-prefix rule or
# an import of registration metadata. New tools require an explicit review here.
READ_ONLY_TOOLS = frozenset(
    {
        "followupboss_check_duplicate_person",
        "followupboss_get_appointment",
        "followupboss_get_appointment_outcome",
        "followupboss_get_appointment_type",
        "followupboss_get_automation",
        "followupboss_get_automation_person",
        "followupboss_get_call",
        "followupboss_get_custom_field",
        "followupboss_get_deal",
        "followupboss_get_deal_attachment",
        "followupboss_get_deal_custom_field",
        "followupboss_get_event",
        "followupboss_get_group",
        "followupboss_get_identity",
        "followupboss_get_latest_lead",
        "followupboss_get_me",
        "followupboss_get_note",
        "followupboss_get_people_relationship",
        "followupboss_get_person",
        "followupboss_get_person_attachment",
        "followupboss_get_pipeline",
        "followupboss_get_pond",
        "followupboss_get_reaction",
        "followupboss_get_smart_list",
        "followupboss_get_stage",
        "followupboss_get_task",
        "followupboss_get_team",
        "followupboss_get_template",
        "followupboss_get_text_message",
        "followupboss_get_text_message_template",
        "followupboss_get_threaded_reply",
        "followupboss_get_user",
        "followupboss_get_webhook",
        "followupboss_get_webhook_event",
        "followupboss_list_action_plan_people",
        "followupboss_list_action_plans",
        "followupboss_list_active_deals_for_person",
        "followupboss_list_appointment_outcomes",
        "followupboss_list_appointment_types",
        "followupboss_list_appointments",
        "followupboss_list_automation_people",
        "followupboss_list_automations",
        "followupboss_list_calls",
        "followupboss_list_custom_fields",
        "followupboss_list_deal_custom_fields",
        "followupboss_list_deals",
        "followupboss_list_email_campaigns",
        "followupboss_list_email_events",
        "followupboss_list_groups",
        "followupboss_list_inbox_app_installations",
        "followupboss_list_inbox_app_participants",
        "followupboss_list_my_overdue_tasks",
        "followupboss_list_my_tasks_due_today",
        "followupboss_list_my_upcoming_tasks",
        "followupboss_list_people_relationships",
        "followupboss_list_person_activity",
        "followupboss_list_pipelines",
        "followupboss_list_ponds",
        "followupboss_list_round_robin_groups",
        "followupboss_list_smart_lists",
        "followupboss_list_stages",
        "followupboss_list_tasks",
        "followupboss_list_team_inboxes",
        "followupboss_list_teams",
        "followupboss_list_templates",
        "followupboss_list_text_message_templates",
        "followupboss_list_text_messages",
        "followupboss_list_timeframes",
        "followupboss_list_unclaimed_people",
        "followupboss_list_uncontacted_leads",
        "followupboss_list_users",
        "followupboss_list_webhooks",
        "followupboss_merge_template",
        "followupboss_merge_text_message_template",
        "followupboss_search_events",
        "followupboss_search_people",
        "followupboss_search_people_in_smart_list",
    }
)

# These append CRM records or log already-performed communication. In particular,
# create_call does not dial, and send_email_events does not send an email.
ADDITIVE_TOOLS = frozenset(
    {
        "followupboss_add_inbox_app_note",
        "followupboss_add_inbox_app_participant",
        "followupboss_add_note",
        "followupboss_add_reaction",
        "followupboss_create_appointment_outcome",
        "followupboss_create_appointment_type",
        "followupboss_create_call",
        "followupboss_create_custom_field",
        "followupboss_create_deal",
        "followupboss_create_deal_attachment",
        "followupboss_create_deal_custom_field",
        "followupboss_create_email_campaign",
        "followupboss_create_group",
        "followupboss_create_people_relationship",
        "followupboss_create_person",
        "followupboss_create_person_attachment",
        "followupboss_create_pipeline",
        "followupboss_create_pond",
        "followupboss_create_stage",
        "followupboss_create_team",
        "followupboss_create_template",
        "followupboss_create_text_message_template",
        "followupboss_send_email_events",
    }
)

# The MCP destructive hint covers replacing existing state as well as deletion.
# Task creation can schedule reminder emails to bounded CRM assignees.
OVERWRITE_OR_DELETE_TOOLS = frozenset(
    {
        "followupboss_claim_person",
        "followupboss_create_task",
        "followupboss_delete_appointment",
        "followupboss_delete_appointment_outcome",
        "followupboss_delete_appointment_type",
        "followupboss_delete_custom_field",
        "followupboss_delete_deal",
        "followupboss_delete_deal_attachment",
        "followupboss_delete_deal_custom_field",
        "followupboss_delete_group",
        "followupboss_delete_note",
        "followupboss_delete_people_relationship",
        "followupboss_delete_person",
        "followupboss_delete_person_attachment",
        "followupboss_delete_pipeline",
        "followupboss_delete_pond",
        "followupboss_delete_reaction",
        "followupboss_delete_stage",
        "followupboss_delete_task",
        "followupboss_delete_team",
        "followupboss_delete_template",
        "followupboss_delete_text_message_template",
        "followupboss_delete_user",
        "followupboss_delete_webhook",
        "followupboss_ignore_unclaimed_person",
        "followupboss_remove_inbox_app_participant",
        "followupboss_update_appointment_outcome",
        "followupboss_update_appointment_type",
        "followupboss_update_call",
        "followupboss_update_custom_field",
        "followupboss_update_deal_attachment",
        "followupboss_update_deal_custom_field",
        "followupboss_update_email_campaign",
        "followupboss_update_group",
        "followupboss_update_inbox_app_message",
        "followupboss_update_note",
        "followupboss_update_people_relationship",
        "followupboss_update_person_attachment",
        "followupboss_update_pipeline",
        "followupboss_update_pond",
        "followupboss_update_stage",
        "followupboss_update_task",
        "followupboss_update_team",
        "followupboss_update_template",
        "followupboss_update_text_message_template",
    }
)

# Communication/workflow execution, calendar invitations, and external integration
# delivery can act outside the CRM. The hints cover every allowed input branch.
EXTERNAL_EFFECT_TOOLS = frozenset(
    {
        "followupboss_add_inbox_app_message",
        "followupboss_apply_action_plan",
        "followupboss_create_appointment",
        "followupboss_create_webhook",
        "followupboss_deactivate_inbox_app",
        "followupboss_install_inbox_app",
        "followupboss_send_event",
        "followupboss_trigger_automation",
        "followupboss_update_action_plan_person",
        "followupboss_update_appointment",
        "followupboss_update_automation_person",
        "followupboss_update_deal",
        "followupboss_update_inbox_app_conversation",
        "followupboss_update_person",
        "followupboss_update_webhook",
    }
)

EXPECTED_HINTS = {
    **{name: (True, False, False) for name in READ_ONLY_TOOLS},
    **{name: (False, False, False) for name in ADDITIVE_TOOLS},
    **{name: (False, True, False) for name in OVERWRITE_OR_DELETE_TOOLS},
    **{name: (False, True, True) for name in EXTERNAL_EFFECT_TOOLS},
}
HINT_NAMES = ("readOnlyHint", "destructiveHint", "openWorldHint")


def _assert_explicit_hints(tool: Tool, expected: tuple[bool, bool, bool]) -> None:
    # exclude_unset rejects annotations that merely rely on SDK/spec defaults.
    wire = tool.model_dump(mode="json", by_alias=True, exclude_unset=True)
    assert "annotations" in wire, tool.name
    annotations = wire["annotations"]
    assert isinstance(annotations, dict), tool.name
    for hint, expected_value in zip(HINT_NAMES, expected, strict=True):
        assert hint in annotations, (tool.name, hint)
        assert type(annotations[hint]) is bool, (tool.name, hint)
        assert annotations[hint] is expected_value, (tool.name, hint)


@pytest.mark.asyncio
async def test_tools_list_exposes_complete_explicit_behavior_partition() -> None:
    """The official client must receive the exact reviewed 160-tool catalog."""
    groups = (READ_ONLY_TOOLS, ADDITIVE_TOOLS, OVERWRITE_OR_DELETE_TOOLS, EXTERNAL_EFFECT_TOOLS)
    assert sum(map(len, groups)) == len(EXPECTED_HINTS) == 160
    requests: list[httpx.Request] = []

    def upstream(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        raise AssertionError("tools/list must not access Follow Up Boss")

    settings = FollowUpBossSettings.model_validate({"api_key": "test", "max_retries": 0})
    async with httpx.AsyncClient(
        base_url=str(settings.base_url), transport=httpx.MockTransport(upstream)
    ) as http_client:
        server = create_server(
            settings, client=FollowUpBossAsyncClient(settings, http_client=http_client)
        )
        async with InMemoryTransport(server) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                response = await session.list_tools()

    assert len(response.tools) == 160
    assert {tool.name for tool in response.tools} == EXPECTED_HINTS.keys()
    for tool in response.tools:
        _assert_explicit_hints(tool, EXPECTED_HINTS[tool.name])
    assert requests == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("tool_name", "arguments", "method", "path", "expected_body", "response"),
    [
        (
            "followupboss_get_person",
            {"person_id": 42},
            "GET",
            "/v1/people/42",
            None,
            {"id": 42},
        ),
        (
            "followupboss_merge_template",
            {"template_id": 4, "merge_person_id": 42},
            "POST",
            "/v1/templates/merge",
            {"templateId": 4, "mergePersonId": 42},
            {"id": 4, "body": "Hello Example"},
        ),
        (
            "followupboss_merge_text_message_template",
            {"template_id": 5, "person_id": 42},
            "POST",
            "/v1/textMessageTemplates/merge",
            {"templateId": 5, "personId": 42},
            {"mergedTemplate": "Hello Example"},
        ),
        (
            "followupboss_create_call",
            {"person_id": 42, "phone": "555-0100", "is_incoming": False},
            "POST",
            "/v1/calls",
            {"personId": 42, "phone": "555-0100", "isIncoming": False, "userId": 7},
            {"id": 10, "personId": 42, "userId": 7},
        ),
        (
            "followupboss_send_email_events",
            {
                "em_events": [
                    {
                        "campaign_id": 3,
                        "occurred": "2026-09-29T10:00:00",
                        "recipient": "example@example.invalid",
                        "type": "delivered",
                    }
                ]
            },
            "POST",
            "/v1/emEvents",
            {
                "emEvents": [
                    {
                        "campaignId": 3,
                        "occurred": "2026-09-29T10:00:00",
                        "recipient": "example@example.invalid",
                        "type": "delivered",
                    }
                ]
            },
            {"emEventIds": [12], "recipientsNotFound": []},
        ),
        (
            "followupboss_add_note",
            {"person_id": 42, "body": "Example note"},
            "POST",
            "/v1/notes",
            {"personId": 42, "body": "Example note"},
            {"id": 11, "personId": 42, "body": "Example note"},
        ),
        (
            "followupboss_update_note",
            {"note_id": 11, "body": "Revised example note"},
            "PUT",
            "/v1/notes/11",
            {"body": "Revised example note"},
            {"id": 11, "body": "Revised example note"},
        ),
        (
            "followupboss_delete_note",
            {"note_id": 11},
            "DELETE",
            "/v1/notes/11",
            None,
            {},
        ),
        (
            "followupboss_send_event",
            {
                "source": "Example portal",
                "system": "Example system",
                "type": "Inquiry",
                "person": {"emails": [{"value": "example@example.invalid"}]},
            },
            "POST",
            "/v1/events",
            {
                "source": "Example portal",
                "system": "Example system",
                "type": "Inquiry",
                "person": {"emails": [{"value": "example@example.invalid"}]},
            },
            {"id": 13, "personId": 42, "type": "Inquiry"},
        ),
    ],
)
async def test_annotations_follow_http_semantics_not_tool_name_or_method(
    tool_name: str,
    arguments: dict[str, object],
    method: str,
    path: str,
    expected_body: dict[str, object] | None,
    response: dict[str, object],
) -> None:
    """Exercise registered tools through the real adapter, services, and mock HTTP."""
    requests: list[httpx.Request] = []

    def upstream(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/v1/identity":
            assert request.method == "GET"
            return httpx.Response(200, json={"user": {"id": 7}})
        assert request.method == method
        assert request.url.path == path
        return httpx.Response(200, json=response)

    settings = FollowUpBossSettings.model_validate({"api_key": "test", "max_retries": 0})
    async with httpx.AsyncClient(
        base_url=str(settings.base_url), transport=httpx.MockTransport(upstream)
    ) as http_client:
        server = create_server(
            settings, client=FollowUpBossAsyncClient(settings, http_client=http_client)
        )
        tools = {tool.name: tool for tool in await server.list_tools()}
        _assert_explicit_hints(tools[tool_name], EXPECTED_HINTS[tool_name])
        result = await server.call_tool(tool_name, arguments)

    assert isinstance(result, CallToolResult)
    assert result.is_error is False
    assert result.structured_content is not None
    if tool_name == "followupboss_delete_note":
        expected_result: dict[str, object] = {"deleted": True, "noteId": 11}
    elif tool_name == "followupboss_send_email_events":
        # The adapter omits empty optional collections from its JSON output.
        expected_result = {"emEventIds": [12]}
    else:
        expected_result = response
    for key, value in expected_result.items():
        assert result.structured_content[key] == value

    actual_requests = [request for request in requests if request.url.path != "/v1/identity"]
    assert len(actual_requests) == 1
    identity_requests = [request for request in requests if request.url.path == "/v1/identity"]
    assert len(identity_requests) == (1 if tool_name == "followupboss_create_call" else 0)
    request = actual_requests[0]
    assert not request.url.query
    assert (json.loads(request.content) if request.content else None) == expected_body


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "tool_name", ["followupboss_create_appointment", "followupboss_update_appointment"]
)
@pytest.mark.parametrize("send_invitation", [None, False, True])
async def test_appointment_hints_cover_every_invitation_branch(
    tool_name: str, send_invitation: bool | None
) -> None:
    """Static catalog hints must cover the supported external invitation branch."""
    requests: list[httpx.Request] = []

    def upstream(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/v1/me":
            return httpx.Response(200, json={"id": 7, "timeZone": "UTC"})
        return httpx.Response(200, json={"id": 14, "title": "Example appointment"})

    arguments: dict[str, object] = {
        "title": "Example appointment",
        "start": "2026-10-01T10:00:00Z",
        "end": "2026-10-01T11:00:00Z",
        "invitees": [{"personId": 42, "email": "example@example.invalid"}],
    }
    if tool_name == "followupboss_update_appointment":
        arguments["appointment_id"] = 14
    if send_invitation is not None:
        arguments["send_invitation"] = send_invitation

    settings = FollowUpBossSettings.model_validate({"api_key": "test", "max_retries": 0})
    async with httpx.AsyncClient(
        base_url=str(settings.base_url), transport=httpx.MockTransport(upstream)
    ) as http_client:
        server = create_server(
            settings, client=FollowUpBossAsyncClient(settings, http_client=http_client)
        )
        tools = {tool.name: tool for tool in await server.list_tools()}
        _assert_explicit_hints(tools[tool_name], (False, True, True))
        result = await server.call_tool(tool_name, arguments)

    assert isinstance(result, CallToolResult)
    assert result.is_error is False
    assert result.structured_content is not None
    assert result.structured_content["id"] == 14
    assert result.structured_content["title"] == "Example appointment"

    writes = [request for request in requests if request.url.path != "/v1/me"]
    assert len(writes) == 1
    request = writes[0]
    if tool_name == "followupboss_create_appointment":
        assert (request.method, request.url.path) == ("POST", "/v1/appointments")
    else:
        assert (request.method, request.url.path) == ("PUT", "/v1/appointments/14")
    expected_query = (
        {} if send_invitation is None else {"sendInvitation": str(send_invitation).lower()}
    )
    assert dict(request.url.params) == expected_query
    body = json.loads(request.content)
    assert "sendInvitation" not in body
    assert body["invitees"] == [{"personId": 42, "email": "example@example.invalid"}]
    assert body["title"] == "Example appointment"
