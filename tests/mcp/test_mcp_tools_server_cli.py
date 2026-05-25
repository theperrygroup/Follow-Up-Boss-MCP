"""Tests for the MCP adapter, FastMCP server wiring, and CLI."""

from __future__ import annotations

import asyncio
import os
import socket
import sys
import textwrap
from collections.abc import Mapping
from dataclasses import dataclass, replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest
from pydantic import AnyUrl, TypeAdapter, ValidationError

from followupboss_mcp.cli import build_parser, main
from followupboss_mcp.config import FollowUpBossSettings
from followupboss_mcp.errors import (
    FollowUpBossError,
    FollowUpBossRateLimitError,
    FollowUpBossValidationError,
)
from followupboss_mcp.mcp_server import create_server
from followupboss_mcp.mcp_tools import (
    AddInboxAppMessageToolInput,
    AddInboxAppNoteToolInput,
    AddInboxAppParticipantToolInput,
    AddReactionToolInput,
    CheckDuplicatePersonToolInput,
    ClaimPersonToolInput,
    DeactivateInboxAppToolInput,
    DeleteAppointmentOutcomeToolInput,
    DeleteAppointmentToolInput,
    DeleteAppointmentTypeToolInput,
    DeleteCustomFieldToolInput,
    DeleteDealAttachmentToolInput,
    DeleteDealCustomFieldToolInput,
    DeleteDealToolInput,
    DeleteGroupToolInput,
    DeleteInboxAppParticipantToolInput,
    DeleteNoteToolInput,
    DeletePeopleRelationshipToolInput,
    DeletePersonAttachmentToolInput,
    DeletePersonToolInput,
    DeletePipelineToolInput,
    DeletePondToolInput,
    DeleteReactionToolInput,
    DeleteStageToolInput,
    DeleteTaskToolInput,
    DeleteTeamToolInput,
    DeleteTemplateToolInput,
    DeleteTextMessageTemplateToolInput,
    DeleteUserToolInput,
    DeleteWebhookToolInput,
    FollowUpBossToolAdapter,
    GetAppointmentOutcomeToolInput,
    GetAppointmentToolInput,
    GetAppointmentTypeToolInput,
    GetAutomationPersonToolInput,
    GetAutomationToolInput,
    GetCallToolInput,
    GetCustomFieldToolInput,
    GetDealAttachmentToolInput,
    GetDealCustomFieldToolInput,
    GetDealToolInput,
    GetEventToolInput,
    GetGroupToolInput,
    GetLatestLeadToolInput,
    GetNoteToolInput,
    GetPeopleRelationshipToolInput,
    GetPersonAttachmentToolInput,
    GetPersonToolInput,
    GetPipelineToolInput,
    GetPondToolInput,
    GetReactionToolInput,
    GetSmartListToolInput,
    GetStageToolInput,
    GetTaskToolInput,
    GetTeamToolInput,
    GetTemplateToolInput,
    GetTextMessageTemplateToolInput,
    GetTextMessageToolInput,
    GetThreadedReplyToolInput,
    GetUserToolInput,
    GetWebhookEventToolInput,
    GetWebhookToolInput,
    IgnoreUnclaimedPersonToolInput,
    ListActiveDealsForPersonToolInput,
    ListInboxAppInstallationsToolInput,
    ListInboxAppParticipantsToolInput,
    ListMyTaskIntentToolInput,
    ListPersonActivityToolInput,
    ListUncontactedLeadsToolInput,
    SearchPeopleInSmartListToolInput,
    UpdateActionPlanPersonToolInput,
    UpdateAppointmentOutcomeToolInput,
    UpdateAppointmentToolInput,
    UpdateAppointmentTypeToolInput,
    UpdateAutomationPersonToolInput,
    UpdateCallToolInput,
    UpdateCustomFieldToolInput,
    UpdateDealAttachmentToolInput,
    UpdateDealCustomFieldToolInput,
    UpdateDealToolInput,
    UpdateEmailCampaignToolInput,
    UpdateGroupToolInput,
    UpdateInboxAppConversationToolInput,
    UpdateInboxAppMessageToolInput,
    UpdateNoteToolInput,
    UpdatePeopleRelationshipToolInput,
    UpdatePersonAttachmentToolInput,
    UpdatePersonToolInput,
    UpdatePipelineToolInput,
    UpdatePondToolInput,
    UpdateStageToolInput,
    UpdateTaskToolInput,
    UpdateTeamToolInput,
    UpdateTemplateToolInput,
    UpdateTextMessageTemplateToolInput,
    UpdateWebhookToolInput,
)
from followupboss_mcp.models.action_plans import (
    ActionPlanListRequest,
    ActionPlanPersonListRequest,
    ActionPlanPersonRecord,
    ActionPlanRecord,
    CreateActionPlanPersonRequest,
)
from followupboss_mcp.models.appointment_metadata import (
    AppointmentOutcomeListRequest,
    AppointmentOutcomeRecord,
    AppointmentTypeListRequest,
    AppointmentTypeRecord,
    CreateAppointmentOutcomeRequest,
    CreateAppointmentTypeRequest,
)
from followupboss_mcp.models.appointments import (
    AppointmentInvitee,
    AppointmentListRequest,
    AppointmentRecord,
    CreateAppointmentRequest,
)
from followupboss_mcp.models.attachments import (
    CreateDealAttachmentRequest,
    CreatePersonAttachmentRequest,
    DealAttachmentRecord,
    PersonAttachmentRecord,
)
from followupboss_mcp.models.automations import (
    AutomationListRequest,
    AutomationPeopleListRequest,
    AutomationPersonRecord,
    AutomationRecord,
    CreateAutomationPersonRequest,
)
from followupboss_mcp.models.calls import CallListRequest, CallRecord, CreateCallRequest
from followupboss_mcp.models.custom_fields import (
    CreateCustomFieldRequest,
    CustomFieldListRequest,
    CustomFieldRecord,
)
from followupboss_mcp.models.deals import (
    CreateDealCustomFieldRequest,
    CreateDealRequest,
    DealCustomFieldListRequest,
    DealCustomFieldRecord,
    DealListRequest,
    DealRecord,
)
from followupboss_mcp.models.email_marketing import (
    CreateEmailCampaignRequest,
    CreateEmailEventsBatchRequest,
    EmailCampaignListRequest,
    EmailCampaignRecord,
    EmailEventListRequest,
    EmailEventRecord,
    EmailEventsBatchResult,
)
from followupboss_mcp.models.events import (
    CreateEventRequest,
    EventPersonInput,
    EventRecord,
    EventSearchRequest,
)
from followupboss_mcp.models.groups import (
    CreateGroupRequest,
    GroupListRequest,
    GroupRecord,
    GroupUserSummary,
)
from followupboss_mcp.models.identity import IdentityResponse
from followupboss_mcp.models.inbox_apps import (
    InboxAppAttachmentRecord,
    InboxAppConversationPersonRecord,
    InboxAppConversationRecord,
    InboxAppInstallationRecord,
    InboxAppInstallationSummary,
    InboxAppMessageRecord,
    InboxAppMessageSenderRecord,
    InboxAppNoteRecord,
    InboxAppParticipantRecord,
    InstallInboxAppRequest,
)
from followupboss_mcp.models.notes import CreateNoteRequest, NoteRecord
from followupboss_mcp.models.people import (
    ClaimPersonRequest,
    CreatePersonRequest,
    IgnoreUnclaimedPersonRequest,
    PeopleSearchRequest,
    PersonDuplicateCheckRecord,
    PersonDuplicateCheckRequest,
    PersonRecord,
    UnclaimedPeopleListRequest,
)
from followupboss_mcp.models.people_relationships import (
    CreatePeopleRelationshipRequest,
    PeopleRelationshipListRequest,
    PeopleRelationshipRecord,
)
from followupboss_mcp.models.pipelines import (
    CreatePipelineRequest,
    PipelineListRequest,
    PipelineRecord,
    PipelineStageInput,
)
from followupboss_mcp.models.ponds import CreatePondRequest, PondListRequest, PondRecord
from followupboss_mcp.models.reactions import ReactionAckRecord, ReactionRecord
from followupboss_mcp.models.smart_lists import SmartListListRequest, SmartListRecord
from followupboss_mcp.models.stages import (
    CreateStageRequest,
    StageListRequest,
    StageRecord,
)
from followupboss_mcp.models.tasks import CreateTaskRequest, TaskListRequest, TaskRecord
from followupboss_mcp.models.team_inboxes import (
    TeamInboxListRequest,
    TeamInboxRecord,
    TeamInboxUserSummary,
)
from followupboss_mcp.models.teams import CreateTeamRequest, TeamListRequest, TeamRecord
from followupboss_mcp.models.templates import (
    CreateTemplateRequest,
    MergeTemplateRequest,
    TemplateListRequest,
    TemplateRecord,
)
from followupboss_mcp.models.text_messages import (
    CreateTextMessageRequest,
    CreateTextMessageTemplateRequest,
    MergedTextMessageTemplateRecord,
    MergeTextMessageTemplateRequest,
    TextMessageListRequest,
    TextMessageRecord,
    TextMessageTemplateListRequest,
    TextMessageTemplateRecord,
)
from followupboss_mcp.models.threaded_replies import ThreadedReplyRecord
from followupboss_mcp.models.timeframes import TimeframeListRequest, TimeframeRecord
from followupboss_mcp.models.users import (
    ConnectedEmailRecord,
    CurrentUserRecord,
    DeleteUserRequest,
    IntercomSettingsRecord,
    UserListRequest,
    UserRecord,
)
from followupboss_mcp.models.webhooks import (
    CreateWebhookRequest,
    WebhookEventRecord,
    WebhookListRequest,
    WebhookRecord,
)
from followupboss_mcp.pagination import PageResult, PaginationMetadata
from followupboss_mcp.tenant_runtime import ServiceBundle
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.client.streamable_http import streamable_http_client

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_SENTRY_ENV_KEYS = (
    "SENTRY_DSN",
    "SENTRY_ENVIRONMENT",
    "SENTRY_RELEASE",
    "SENTRY_SAMPLE_RATE",
    "SENTRY_TRACES_SAMPLE_RATE",
    "SENTRY_PROFILES_SAMPLE_RATE",
    "SENTRY_ENABLE_LOGS",
    "SENTRY_DEBUG",
)

EXPECTED_REGISTERED_TOOL_NAMES = [
    "followupboss_add_inbox_app_message",
    "followupboss_add_inbox_app_note",
    "followupboss_add_inbox_app_participant",
    "followupboss_add_note",
    "followupboss_add_reaction",
    "followupboss_apply_action_plan",
    "followupboss_check_duplicate_person",
    "followupboss_claim_person",
    "followupboss_create_appointment",
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
    "followupboss_create_task",
    "followupboss_create_team",
    "followupboss_create_template",
    "followupboss_create_text_message",
    "followupboss_create_text_message_template",
    "followupboss_create_webhook",
    "followupboss_deactivate_inbox_app",
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
    "followupboss_ignore_unclaimed_person",
    "followupboss_install_inbox_app",
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
    "followupboss_remove_inbox_app_participant",
    "followupboss_search_events",
    "followupboss_search_people",
    "followupboss_search_people_in_smart_list",
    "followupboss_send_email_events",
    "followupboss_send_event",
    "followupboss_trigger_automation",
    "followupboss_update_action_plan_person",
    "followupboss_update_appointment",
    "followupboss_update_appointment_outcome",
    "followupboss_update_appointment_type",
    "followupboss_update_automation_person",
    "followupboss_update_call",
    "followupboss_update_custom_field",
    "followupboss_update_deal",
    "followupboss_update_deal_attachment",
    "followupboss_update_deal_custom_field",
    "followupboss_update_email_campaign",
    "followupboss_update_group",
    "followupboss_update_inbox_app_conversation",
    "followupboss_update_inbox_app_message",
    "followupboss_update_note",
    "followupboss_update_people_relationship",
    "followupboss_update_person",
    "followupboss_update_person_attachment",
    "followupboss_update_pipeline",
    "followupboss_update_pond",
    "followupboss_update_stage",
    "followupboss_update_task",
    "followupboss_update_team",
    "followupboss_update_template",
    "followupboss_update_text_message_template",
    "followupboss_update_webhook",
]
EXPECTED_RESOURCE_URIS = ["followupboss://api-coverage-matrix"]
EXPECTED_PROMPT_NAMES = ["followupboss_compose_lead_event"]


def _page_metadata() -> PaginationMetadata:
    return PaginationMetadata(count=1, limit=10, next_token=None, next_link=None, offset=0, total=1)


def _reserve_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        sock.listen(1)
        return int(sock.getsockname()[1])


async def _wait_for_port(host: str, port: int, *, attempts: int = 300) -> None:
    for _ in range(attempts):
        try:
            reader, writer = await asyncio.open_connection(host, port)
        except OSError:
            await asyncio.sleep(0.1)
            continue
        writer.close()
        await writer.wait_closed()
        return
    raise AssertionError(f"Timed out waiting for {host}:{port} to accept connections.")


def _server_python_env() -> dict[str, str]:
    """Build the environment used by subprocess MCP server tests.

    Returns:
        An environment mapping that exposes the repository's `src/` layout to the
        subprocess-based MCP server tests.
    """
    server_env = dict(os.environ)
    for key in _SENTRY_ENV_KEYS:
        server_env.pop(key, None)
    existing_pythonpath = server_env.get("PYTHONPATH")
    pythonpath_entries = [str(PROJECT_ROOT / "src")]
    if existing_pythonpath:
        pythonpath_entries.append(existing_pythonpath)
    server_env["PYTHONPATH"] = os.pathsep.join(pythonpath_entries)
    return server_env


async def _call_public_tool(
    server: Any,
    tools: Mapping[str, Any],
    name: str,
    /,
    *args: object,
    **kwargs: object,
) -> dict[str, Any]:
    """Call one registered tool through the public FastMCP surface.

    Args:
        server: The FastMCP server under test.
        tools: Public tool metadata keyed by tool name from `await server.list_tools()`.
        name: The registered MCP tool name.
        *args: Positional arguments in the same order as the registered tool schema.
        **kwargs: Keyword arguments for the registered tool.

    Returns:
        The structured JSON payload returned by the public `server.call_tool()` helper.
    """
    properties = tools[name].inputSchema.get("properties", {})
    assert isinstance(properties, dict)
    arg_names = list(properties)
    assert len(args) <= len(arg_names)
    call_arguments = {arg_names[index]: value for index, value in enumerate(args)}
    assert not set(call_arguments).intersection(kwargs)
    call_arguments.update(kwargs)

    result = await server.call_tool(name, call_arguments)
    if isinstance(result, dict):
        return result
    if isinstance(result, tuple) and len(result) == 2 and isinstance(result[1], dict):
        return result[1]
    raise AssertionError(f"Unexpected public tool result for {name}: {result!r}")


def _service_stub(**methods: object) -> Any:
    """Return a tiny typed-as-Any service stub."""
    return SimpleNamespace(**methods)


@dataclass
class StubBundle:
    """Service bundle stub for adapter-only tests."""

    def __post_init__(self) -> None:
        self.appointment_list_requests: list[AppointmentListRequest] = []
        self.call_create_requests: list[CreateCallRequest] = []
        self.call_list_requests: list[CallListRequest] = []
        self.email_event_list_requests: list[EmailEventListRequest] = []
        self.event_search_requests: list[EventSearchRequest] = []
        self.deal_list_requests: list[DealListRequest] = []
        self.people_search_requests: list[PeopleSearchRequest] = []
        self.task_list_requests: list[TaskListRequest] = []
        self.text_message_create_requests: list[CreateTextMessageRequest] = []
        self.text_message_list_requests: list[TextMessageListRequest] = []
        self.user_list_requests: list[UserListRequest] = []

        async def identity_get() -> IdentityResponse:
            return IdentityResponse(id=1, name="Picard")

        async def people_search(request: PeopleSearchRequest) -> PageResult[PersonRecord]:
            self.people_search_requests.append(request)
            return PageResult(
                items=[PersonRecord(id=2, firstName="Will")], metadata=_page_metadata()
            )

        async def people_get(person_id: int, request: object | None = None) -> PersonRecord:
            del request
            return PersonRecord(id=person_id, firstName="Data")

        async def people_create(_: CreatePersonRequest) -> PersonRecord:
            return PersonRecord(id=3)

        async def people_update(person_id: int, request: object) -> PersonRecord:
            del request
            return PersonRecord(id=person_id)

        async def people_check_duplicate(
            _: PersonDuplicateCheckRequest,
        ) -> PersonDuplicateCheckRecord:
            return PersonDuplicateCheckRecord(
                found=True,
                matchedBy="email",
                assignedTo="Agent Smith",
            )

        async def people_list_unclaimed(
            _: UnclaimedPeopleListRequest,
        ) -> PageResult[PersonRecord]:
            return PageResult(
                items=[
                    PersonRecord(
                        id=6,
                        firstName="Unclaimed",
                        sourceId=730,
                        claimed=False,
                        delayed=False,
                    )
                ],
                metadata=_page_metadata(),
            )

        async def people_claim(_: ClaimPersonRequest) -> PersonRecord:
            return PersonRecord(id=7, firstName="Claimed", assignedTo="Agent Smith", claimed=False)

        async def people_ignore_unclaimed(_: IgnoreUnclaimedPersonRequest) -> None:
            return None

        async def people_delete(person_id: int) -> None:
            del person_id

        async def person_attachments_get(person_attachment_id: int) -> PersonAttachmentRecord:
            return PersonAttachmentRecord(
                id=person_attachment_id,
                personId=1,
                fileName="test.jpg",
                uri="https://test.com/myfile",
                mimeType="link",
                status="created",
                createdAt="2022-11-16T03:44:52Z",
                createdById=1,
                createdByName="Olivia Admin",
                is_external=1,
                system_id=123,
            )

        async def person_attachments_create(
            _: CreatePersonAttachmentRequest,
        ) -> PersonAttachmentRecord:
            return PersonAttachmentRecord(
                id=3,
                personId=1,
                fileName="test.jpg",
                uri="https://test.com/myfile",
                mimeType="link",
                status="created",
                createdAt="2022-11-16T03:44:52Z",
                createdById=1,
                createdByName="Olivia Admin",
            )

        async def person_attachments_update(
            person_attachment_id: int,
            request: object,
        ) -> PersonAttachmentRecord:
            del request
            return PersonAttachmentRecord(
                id=person_attachment_id,
                personId=1,
                fileName="updated.jpg",
                fileSize=42,
                uri="https://test.com/updated",
                mimeType="link",
                status="created",
                createdAt="2022-11-16T03:44:52Z",
                createdById=1,
                createdByName="Olivia Admin",
            )

        async def person_attachments_delete(person_attachment_id: int) -> None:
            del person_attachment_id

        async def deal_attachments_get(deal_attachment_id: int) -> DealAttachmentRecord:
            return DealAttachmentRecord(
                id=deal_attachment_id,
                dealId=8,
                fileName="deal.jpg",
                uri="https://test.com/deal",
                mimeType="link",
                status="created",
                createdAt="2022-11-16T19:09:45Z",
                createdById=1,
                createdByName="Olivia Admin",
            )

        async def deal_attachments_create(_: CreateDealAttachmentRequest) -> DealAttachmentRecord:
            return DealAttachmentRecord(
                id=11,
                dealId=8,
                fileName="deal.jpg",
                uri="https://test.com/deal",
                mimeType="link",
                status="created",
                createdAt="2022-11-16T19:09:45Z",
                createdById=1,
                createdByName="Olivia Admin",
            )

        async def deal_attachments_update(
            deal_attachment_id: int,
            request: object,
        ) -> DealAttachmentRecord:
            del request
            return DealAttachmentRecord(
                id=deal_attachment_id,
                dealId=9,
                fileName="deal-updated.jpg",
                fileSize=24,
                uri="https://test.com/deal-updated",
                mimeType="link",
                status="created",
                createdAt="2022-11-16T19:09:45Z",
                createdById=1,
                createdByName="Olivia Admin",
            )

        async def deal_attachments_delete(deal_attachment_id: int) -> None:
            del deal_attachment_id

        async def reactions_get(reaction_id: int) -> ReactionRecord:
            return ReactionRecord(
                id=reaction_id,
                created="2024-03-21T21:14:13Z",
                createdBy="Tom Minch",
                createdById=1,
                refType="Note",
                refId=2144705,
                body="🤯",
            )

        async def reactions_add(ref_type: str, ref_id: int, request: object) -> object:
            del ref_type, ref_id, request
            return ReactionAckRecord()

        async def reactions_delete(
            ref_type: str,
            ref_id: int,
            request: object | None = None,
        ) -> None:
            del ref_type, ref_id, request

        async def people_relationships_list(
            _: PeopleRelationshipListRequest,
        ) -> PageResult[PeopleRelationshipRecord]:
            return PageResult(
                items=[
                    PeopleRelationshipRecord(
                        id=423,
                        personId=46977,
                        name="Billy Bob",
                        firstName="Billy",
                        lastName="Bob",
                        type="Husband",
                        isPriority=True,
                    )
                ],
                metadata=_page_metadata(),
            )

        async def people_relationships_get(people_relationship_id: int) -> PeopleRelationshipRecord:
            return PeopleRelationshipRecord(
                id=people_relationship_id,
                personId=46977,
                name="Billy Bob",
                firstName="Billy",
                lastName="Bob",
                type="Husband",
                isPriority=True,
            )

        async def people_relationships_create(
            _: CreatePeopleRelationshipRequest,
        ) -> PeopleRelationshipRecord:
            return PeopleRelationshipRecord()

        async def people_relationships_update(
            people_relationship_id: int,
            request: object,
        ) -> PeopleRelationshipRecord:
            del people_relationship_id, request
            return PeopleRelationshipRecord()

        async def people_relationships_delete(people_relationship_id: int) -> None:
            del people_relationship_id

        async def events_search(request: EventSearchRequest) -> PageResult[EventRecord]:
            self.event_search_requests.append(request)
            return PageResult(
                items=[EventRecord(id=4, personId=request.person_id or 2, type="Inquiry")],
                metadata=_page_metadata(),
            )

        async def events_send(_: CreateEventRequest) -> EventRecord:
            return EventRecord(id=5, personId=2, type="Inquiry")

        async def events_get(event_id: int) -> EventRecord:
            return EventRecord(id=event_id, personId=2, type="Inquiry")

        async def action_plans_list(_: ActionPlanListRequest) -> PageResult[ActionPlanRecord]:
            return PageResult(
                items=[
                    ActionPlanRecord(
                        id=5,
                        name="Qualify buyer leads",
                        status="Active",
                    )
                ],
                metadata=_page_metadata(),
            )

        async def action_plan_people_list(
            _: ActionPlanPersonListRequest,
        ) -> PageResult[ActionPlanPersonRecord]:
            return PageResult(
                items=[
                    ActionPlanPersonRecord(
                        id=6,
                        actionPlanId=5,
                        personId=10810,
                        status="Running",
                    )
                ],
                metadata=_page_metadata(),
            )

        async def action_plans_apply(
            _: CreateActionPlanPersonRequest,
        ) -> ActionPlanPersonRecord:
            return ActionPlanPersonRecord(id=7, actionPlanId=5, personId=10810, status="Running")

        async def action_plan_people_update(
            action_plan_person_id: int,
            request: object,
        ) -> ActionPlanPersonRecord:
            del request
            return ActionPlanPersonRecord(
                id=action_plan_person_id,
                actionPlanId=5,
                personId=10810,
                status="Paused",
            )

        async def automations_list(_: AutomationListRequest) -> PageResult[AutomationRecord]:
            return PageResult(
                items=[AutomationRecord(id=50, name="Test Automation", status="Active")],
                metadata=_page_metadata(),
            )

        async def automations_get(automation_id: int) -> AutomationRecord:
            return AutomationRecord(id=automation_id, name="Test Automation", status="Active")

        async def automation_people_list(
            _: AutomationPeopleListRequest,
        ) -> PageResult[AutomationPersonRecord]:
            return PageResult(
                items=[
                    AutomationPersonRecord(
                        id=51,
                        automationId=50,
                        automationName="Test Automation",
                        personId=2,
                        status="Completed",
                    )
                ],
                metadata=_page_metadata(),
            )

        async def automation_people_get(automation_person_id: int) -> AutomationPersonRecord:
            return AutomationPersonRecord(
                id=automation_person_id,
                automationId=50,
                automationName="Test Automation",
                personId=2,
                status="Completed",
            )

        async def automation_people_create(
            _: CreateAutomationPersonRequest,
        ) -> AutomationPersonRecord:
            return AutomationPersonRecord(
                id=52,
                automationId=50,
                automationName="Test Automation",
                personId=3,
                status="Running",
            )

        async def automation_people_update(
            automation_person_id: int,
            request: object,
        ) -> AutomationPersonRecord:
            del request
            return AutomationPersonRecord(
                id=automation_person_id,
                automationId=50,
                automationName="Test Automation",
                personId=3,
                status="Paused",
            )

        async def groups_list(_: GroupListRequest) -> PageResult[GroupRecord]:
            return PageResult(
                items=[
                    GroupRecord(
                        id=6,
                        name="Eastside",
                        type="Agent",
                        distribution="round-robin",
                        users=[GroupUserSummary(id=199, name="Daniel Corkill")],
                    )
                ],
                metadata=_page_metadata(),
            )

        async def groups_round_robin_list(_: GroupListRequest) -> PageResult[GroupRecord]:
            return PageResult(
                items=[
                    GroupRecord(
                        id=7,
                        name="Round Robin",
                        type="Agent",
                        distribution="round-robin",
                        nextRoundRobinUser=334,
                        users=[GroupUserSummary(id=200, name="Beverly Crusher")],
                    )
                ],
                metadata=_page_metadata(),
            )

        async def groups_get(group_id: int) -> GroupRecord:
            return GroupRecord(id=group_id, name="Eastside", type="Agent")

        async def groups_create(_: CreateGroupRequest) -> GroupRecord:
            return GroupRecord(id=11, name="Westside", type="Agent")

        async def groups_update(group_id: int, request: object) -> GroupRecord:
            del request
            return GroupRecord(id=group_id, name="Westside Plus", type="Agent")

        async def groups_delete(group_id: int) -> None:
            del group_id

        async def inbox_apps_list_installations(
            published_inbox_app_id: int,
        ) -> PageResult[InboxAppInstallationSummary]:
            del published_inbox_app_id
            return PageResult(
                items=[
                    InboxAppInstallationSummary(
                        inboxAppId=130,
                        userId=0,
                        created="2025-01-01T12:12:12Z",
                    )
                ],
                metadata=_page_metadata(),
            )

        async def inbox_apps_install(_: InstallInboxAppRequest) -> InboxAppInstallationRecord:
            return InboxAppInstallationRecord(
                id=131,
                created="2024-01-01T12:00:00Z",
                updated="2024-01-01T12:00:00Z",
                createdById=1,
                updatedById=1,
                status=10,
                name="Example Inbox App",
                publishedInboxAppId=9,
                userId=0,
                canReply=True,
            )

        async def inbox_apps_deactivate(inbox_app_id: int) -> None:
            del inbox_app_id

        async def inbox_apps_list_participants(
            inbox_app_id: int,
            ext_conversation_id: str,
        ) -> PageResult[InboxAppParticipantRecord]:
            del inbox_app_id, ext_conversation_id
            return PageResult(
                items=[
                    InboxAppParticipantRecord(
                        id=132,
                        status="active",
                        name="John Doe",
                        phone="+14075550123",
                        email="john@example.com",
                        isAutomation=False,
                    )
                ],
                metadata=_page_metadata(),
            )

        async def inbox_apps_add_participant(
            inbox_app_id: int,
            ext_conversation_id: str,
            request: object,
        ) -> InboxAppParticipantRecord:
            del inbox_app_id, ext_conversation_id, request
            return InboxAppParticipantRecord(
                id=133,
                status="active",
                name="John Doe",
                phone="+14075550123",
                email="john@example.com",
                isAutomation=False,
            )

        async def inbox_apps_remove_participant(
            inbox_app_id: int,
            ext_conversation_id: str,
            participant_id: int,
        ) -> None:
            del inbox_app_id, ext_conversation_id, participant_id

        async def inbox_apps_add_message(
            inbox_app_id: int,
            request: object,
        ) -> InboxAppMessageRecord:
            del inbox_app_id, request
            return InboxAppMessageRecord(
                id=134,
                created="2024-01-01T12:00:00Z",
                updated="2024-01-01T12:00:00Z",
                sentAt="2024-01-01T12:00:00Z",
                deliveryStatus=None,
                deliveryStatusErrorMessage=None,
                createdById=1,
                updatedById=1,
                isIncoming=True,
                message="An example message.",
                userId=0,
                personId=1,
                sender=InboxAppMessageSenderRecord(
                    personId=1,
                    name="John Doe",
                    email=None,
                    phone=None,
                    avatar=None,
                ),
                attachments=[
                    InboxAppAttachmentRecord(
                        filename="example-2.jpg",
                        url="https://followupboss.test/example-2.jpg",
                    )
                ],
                conversationDeepLinkUrl="https://app.followupboss.com/2/inbox-new/0/inbox/1",
            )

        async def inbox_apps_add_note(
            inbox_app_id: int,
            request: object,
        ) -> InboxAppNoteRecord:
            del inbox_app_id, request
            return InboxAppNoteRecord(
                id=135,
                created="2024-01-01T12:00:00Z",
                updated="2024-01-01T12:00:00Z",
                createdById=1,
                updatedById=1,
                createdBy="John Doe",
                updatedBy="John Doe",
                conversationId=1,
                body="An example note.",
                isHtml=False,
                type="ConversationNote",
                conversationDeepLinkUrl="https://app.followupboss.com/2/inbox-new/0/inbox/1",
            )

        async def inbox_apps_update_conversation(
            inbox_app_id: int,
            ext_conversation_id: str,
            request: object,
        ) -> InboxAppConversationRecord:
            del inbox_app_id, request
            return InboxAppConversationRecord(
                externalConversationId=ext_conversation_id,
                created="2024-01-01T12:00:00Z",
                updated="2024-01-01T12:00:00Z",
                createdById="John Doe",
                updatedById="John Doe",
                ownerUserId=1,
                ownerSharedInboxId=0,
                assignedUserId=0,
                assignedSharedInboxId=1,
                subject="A Conversation Subject",
                archived=False,
                person=InboxAppConversationPersonRecord(
                    id=1,
                    name=None,
                    email=None,
                    phone=None,
                ),
                conversationDeepLinkUrl="https://app.followupboss.com/2/inbox-new/0/inbox/1",
            )

        async def inbox_apps_update_message(
            inbox_app_id: int,
            request: object,
        ) -> InboxAppMessageRecord:
            del inbox_app_id, request
            return InboxAppMessageRecord(
                id=136,
                created="2024-01-01T12:00:00Z",
                updated="2024-01-01T12:00:00Z",
                sentAt="2024-01-01T12:00:00Z",
                deliveryStatus="Delivered",
                deliveryStatusErrorMessage=None,
                createdById=1,
                updatedById=1,
                isIncoming=True,
                message="An example message.",
                userId=0,
                personId=1,
                sender=InboxAppMessageSenderRecord(
                    personId=1,
                    name="John Doe",
                    email=None,
                    phone=None,
                    avatar=None,
                ),
                conversationDeepLinkUrl="https://app.followupboss.com/2/inbox-new/0/inbox/1",
            )

        async def users_list(request: UserListRequest) -> PageResult[UserRecord]:
            self.user_list_requests.append(request)
            return PageResult(items=[UserRecord(id=6, name="Geordi")], metadata=_page_metadata())

        async def users_get(user_id: int) -> UserRecord:
            return UserRecord(id=user_id, name="Crusher")

        async def users_get_me() -> CurrentUserRecord:
            return CurrentUserRecord(
                id=1,
                name="Gerald Leenerts",
                role="admin",
                email="gerald@followupboss.com",
                phone="(123) 456-7890",
                timeZone="America/Chicago",
                signature="<div>Cheers,<br></div><div>-Gerald</div>",
                rawSignature="<div>Cheers,<br></div><div>-Gerald</div>",
                apiKey="secret-api-key",
                algoliaKey="secret-algolia-key",
                intercomSettings=IntercomSettingsRecord(
                    app_id="abc123",
                    created_at="1313236940",
                    user_hash="secret-hash",
                    user_id="1234-1",
                ),
                account=1234,
                teamMember=None,
                beta=True,
                betaOnly=False,
                connectedEmail=ConnectedEmailRecord(
                    email="gerald@followupboss.com",
                    oauthProvider="google",
                    shareEmails=False,
                    imapLeadProcessing=True,
                    hasSmtp=True,
                ),
                leadEmailAddress="gerald@followupboss.me",
                callingEnabled=True,
                voicemailEnabled=False,
                voicemailUrl=None,
                callingCapabilityToken="secret-calling-token",
                isOwner=True,
                unreadConversationCount=0,
                notifyBy=["email", "sms"],
                features=["calling", "link-tracking"],
            )

        async def users_delete(user_id: int, request: DeleteUserRequest) -> None:
            del user_id, request

        async def appointment_outcomes_list(
            _: AppointmentOutcomeListRequest,
        ) -> PageResult[AppointmentOutcomeRecord]:
            return PageResult(
                items=[AppointmentOutcomeRecord(id=7, name="Completed", orderWeight=1000)],
                metadata=_page_metadata(),
            )

        async def appointment_outcomes_get(
            appointment_outcome_id: int,
        ) -> AppointmentOutcomeRecord:
            return AppointmentOutcomeRecord(
                id=appointment_outcome_id,
                name="Completed",
                orderWeight=1000,
            )

        async def appointment_outcomes_create(
            _: CreateAppointmentOutcomeRequest,
        ) -> AppointmentOutcomeRecord:
            return AppointmentOutcomeRecord(id=8, name="No Show", orderWeight=2000)

        async def appointment_outcomes_update(
            appointment_outcome_id: int,
            request: object,
        ) -> AppointmentOutcomeRecord:
            del request
            return AppointmentOutcomeRecord(
                id=appointment_outcome_id,
                name="Rescheduled",
                orderWeight=3000,
            )

        async def appointment_outcomes_delete(
            appointment_outcome_id: int,
            request: object,
        ) -> None:
            del appointment_outcome_id, request

        async def appointment_types_list(
            _: AppointmentTypeListRequest,
        ) -> PageResult[AppointmentTypeRecord]:
            return PageResult(
                items=[AppointmentTypeRecord(id=9, name="Buyer Consult", orderWeight=1000)],
                metadata=_page_metadata(),
            )

        async def appointment_types_get(appointment_type_id: int) -> AppointmentTypeRecord:
            return AppointmentTypeRecord(
                id=appointment_type_id,
                name="Buyer Consult",
                orderWeight=1000,
            )

        async def appointment_types_create(
            _: CreateAppointmentTypeRequest,
        ) -> AppointmentTypeRecord:
            return AppointmentTypeRecord(id=10, name="Listing Consult", orderWeight=2000)

        async def appointment_types_update(
            appointment_type_id: int,
            request: object,
        ) -> AppointmentTypeRecord:
            del request
            return AppointmentTypeRecord(
                id=appointment_type_id,
                name="Showing",
                orderWeight=3000,
            )

        async def appointment_types_delete(
            appointment_type_id: int,
            request: object,
        ) -> None:
            del appointment_type_id, request

        async def custom_fields_list(_: CustomFieldListRequest) -> PageResult[CustomFieldRecord]:
            return PageResult(
                items=[
                    CustomFieldRecord(id=7, label="Birthday", name="customBirthday", type="date")
                ],
                metadata=_page_metadata(),
            )

        async def custom_fields_get(custom_field_id: int) -> CustomFieldRecord:
            return CustomFieldRecord(
                id=custom_field_id,
                label="Close price",
                name="customClosePrice",
                type="number",
            )

        async def custom_fields_create(_: CreateCustomFieldRequest) -> CustomFieldRecord:
            return CustomFieldRecord(
                id=12,
                label="Looking for",
                name="customLookingFor",
                type="dropdown",
                choices=["Apartment", "Townhouse"],
            )

        async def custom_fields_update(
            custom_field_id: int,
            request: object,
        ) -> CustomFieldRecord:
            del request
            return CustomFieldRecord(
                id=custom_field_id,
                label="Looking for",
                name="customLookingFor",
                type="dropdown",
            )

        async def custom_fields_delete(custom_field_id: int) -> None:
            del custom_field_id

        async def email_marketing_list_campaigns(
            _: EmailCampaignListRequest,
        ) -> PageResult[EmailCampaignRecord]:
            return PageResult(
                items=[
                    EmailCampaignRecord(
                        id=201,
                        origin="Curaytor",
                        originId="912",
                        name="Can I help",
                        subject="Can I help?",
                        bodyHtml="I saw you're browsing our website, can I help with...",
                    )
                ],
                metadata=_page_metadata(),
            )

        async def email_marketing_create_campaign(
            _: CreateEmailCampaignRequest,
        ) -> EmailCampaignRecord:
            return EmailCampaignRecord(
                id=202,
                origin="Curaytor",
                originId="913",
                name="New Campaign",
                subject="Hello",
                bodyHtml="<p>Hello</p>",
            )

        async def email_marketing_update_campaign(
            email_campaign_id: int,
            request: object,
        ) -> EmailCampaignRecord:
            del request
            return EmailCampaignRecord(
                id=email_campaign_id,
                origin="Curaytor",
                originId="913",
                name="Updated Campaign",
                subject="Updated",
                bodyHtml="<p>Updated</p>",
            )

        async def email_marketing_list_events(
            request: EmailEventListRequest,
        ) -> PageResult[EmailEventRecord]:
            self.email_event_list_requests.append(request)
            return PageResult(
                items=[
                    EmailEventRecord(
                        count=2,
                        type="open",
                        personId=request.person_id or 10911,
                        campaignId=102,
                        campaignName="Can I help",
                        created="2017-01-03T19:20:49Z",
                        updated="2017-01-03T19:20:49Z",
                    )
                ],
                metadata=_page_metadata(),
            )

        async def email_marketing_send_events(
            _: CreateEmailEventsBatchRequest,
        ) -> EmailEventsBatchResult:
            return EmailEventsBatchResult(
                emEventIds=[193928, 193929],
                recipientsNotFound=[
                    "email.not.in.fub@example.com",
                    "another.missing.email@example.com",
                ],
            )

        async def deals_list(request: DealListRequest) -> PageResult[DealRecord]:
            self.deal_list_requests.append(request)
            return PageResult(
                items=[DealRecord(id=8, name="Buyer contract", pipelineId=3, stageId=7)],
                metadata=_page_metadata(),
            )

        async def deals_get(deal_id: int) -> DealRecord:
            return DealRecord(id=deal_id, name="Buyer contract", pipelineId=3, stageId=7)

        async def deals_create(_: CreateDealRequest) -> DealRecord:
            return DealRecord(id=9, name="New deal", pipelineId=3, stageId=7)

        async def deals_update(deal_id: int, request: object) -> DealRecord:
            del request
            return DealRecord(id=deal_id, name="Updated deal", pipelineId=3, stageId=8)

        async def deals_delete(deal_id: int) -> None:
            del deal_id

        async def deal_custom_fields_list(
            _: DealCustomFieldListRequest,
        ) -> PageResult[DealCustomFieldRecord]:
            return PageResult(
                items=[
                    DealCustomFieldRecord(
                        id=10,
                        label="Close Price",
                        name="customClosePrice",
                        type="number",
                    )
                ],
                metadata=_page_metadata(),
            )

        async def deal_custom_fields_get(deal_custom_field_id: int) -> DealCustomFieldRecord:
            return DealCustomFieldRecord(
                id=deal_custom_field_id,
                label="Priority",
                name="customPriority",
                type="dropdown",
                choices=["High", "Medium", "Low"],
            )

        async def deal_custom_fields_create(
            _: CreateDealCustomFieldRequest,
        ) -> DealCustomFieldRecord:
            return DealCustomFieldRecord(
                id=45,
                label="Priority",
                name="customPriority",
                type="dropdown",
                choices=["High", "Medium", "Low"],
            )

        async def deal_custom_fields_update(
            deal_custom_field_id: int,
            request: object,
        ) -> DealCustomFieldRecord:
            del request
            return DealCustomFieldRecord(
                id=deal_custom_field_id,
                label="Priority",
                name="customPriority",
                type="dropdown",
                choices=["Critical", "High", "Medium"],
                hideIfEmpty=True,
                readOnly=True,
            )

        async def deal_custom_fields_delete(deal_custom_field_id: int) -> None:
            del deal_custom_field_id

        async def pipelines_list(_: PipelineListRequest) -> PageResult[PipelineRecord]:
            return PageResult(
                items=[PipelineRecord(id=11, name="Buyer pipeline", description="Buyer flow")],
                metadata=_page_metadata(),
            )

        async def pipelines_get(pipeline_id: int) -> PipelineRecord:
            return PipelineRecord(id=pipeline_id, name="Buyer pipeline", description="Buyer flow")

        async def pipelines_create(_: CreatePipelineRequest) -> PipelineRecord:
            return PipelineRecord(id=12, name="New pipeline", description="New flow")

        async def pipelines_update(pipeline_id: int, request: object) -> PipelineRecord:
            del request
            return PipelineRecord(
                id=pipeline_id, name="Updated pipeline", description="Updated flow"
            )

        async def pipelines_delete(pipeline_id: int) -> None:
            del pipeline_id

        async def ponds_list(_: PondListRequest) -> PageResult[PondRecord]:
            return PageResult(
                items=[PondRecord(id=70, name="Round Robin", userId=6, userIds=[6, 7])],
                metadata=_page_metadata(),
            )

        async def ponds_get(pond_id: int) -> PondRecord:
            return PondRecord(id=pond_id, name="Round Robin", userId=6, userIds=[6, 7])

        async def ponds_create(_: CreatePondRequest) -> PondRecord:
            return PondRecord(id=71, name="Sphere Builders", userId=8, userIds=[8, 9])

        async def ponds_update(pond_id: int, request: object) -> PondRecord:
            del request
            return PondRecord(id=pond_id, name="Updated Pond", userId=9, userIds=[9, 10])

        async def ponds_delete(pond_id: int, request: object) -> None:
            del pond_id, request

        async def smart_lists_list(_: SmartListListRequest) -> PageResult[SmartListRecord]:
            return PageResult(
                items=[
                    SmartListRecord(
                        id=74,
                        name="🚨 Active Buyers ✅",
                        description="All active buyers",
                        isFub2=True,
                    )
                ],
                metadata=_page_metadata(),
            )

        async def smart_lists_get(smart_list_id: int) -> SmartListRecord:
            return SmartListRecord(
                id=smart_list_id,
                name="Active Buyers",
                description="All active buyers",
                isFub2=True,
            )

        async def stages_list(_: StageListRequest) -> PageResult[StageRecord]:
            return PageResult(
                items=[
                    StageRecord(
                        id=78,
                        name="Prospect",
                        orderWeight=1000,
                        isProtected=False,
                        peopleCount=12,
                    )
                ],
                metadata=_page_metadata(),
            )

        async def stages_get(stage_id: int) -> StageRecord:
            return StageRecord(
                id=stage_id,
                name="Prospect",
                orderWeight=1000,
                isProtected=False,
                peopleCount=12,
            )

        async def stages_create(_: CreateStageRequest) -> StageRecord:
            return StageRecord(
                id=79,
                name="Qualified",
                orderWeight=2000,
                isProtected=False,
                peopleCount=8,
            )

        async def stages_update(stage_id: int, request: object) -> StageRecord:
            del request
            return StageRecord(
                id=stage_id,
                name="Updated Stage",
                orderWeight=3000,
                isProtected=False,
                peopleCount=5,
            )

        async def stages_delete(stage_id: int, request: object) -> None:
            del stage_id, request

        async def teams_list(_: TeamListRequest) -> PageResult[TeamRecord]:
            return PageResult(
                items=[
                    TeamRecord(
                        id=82,
                        name="Listing Team",
                        userIds=[5, 6],
                        leaderIds=[5],
                    )
                ],
                metadata=_page_metadata(),
            )

        async def teams_get(team_id: int) -> TeamRecord:
            return TeamRecord(
                id=team_id,
                name="Listing Team",
                userIds=[5, 6],
                leaderIds=[5],
            )

        async def teams_create(_: CreateTeamRequest) -> TeamRecord:
            return TeamRecord(id=83, name="Buyer Team", userIds=[7, 8], leaderIds=[7])

        async def teams_update(team_id: int, request: object) -> TeamRecord:
            del request
            return TeamRecord(id=team_id, name="Updated Team", userIds=[9, 10], leaderIds=[9])

        async def teams_delete(team_id: int, request: object) -> None:
            del team_id, request

        async def team_inboxes_list(_: TeamInboxListRequest) -> PageResult[TeamInboxRecord]:
            return PageResult(
                items=[
                    TeamInboxRecord(
                        id=121,
                        name="My Team Inbox",
                        users=[TeamInboxUserSummary(id=111, name="User Name", firstName="User")],
                    )
                ],
                metadata=_page_metadata(),
            )

        async def timeframes_list(_: TimeframeListRequest) -> PageResult[TimeframeRecord]:
            return PageResult(
                items=[
                    TimeframeRecord(id=1, timeframe="0-3 Months"),
                    TimeframeRecord(id=2, timeframe="3-6 Months"),
                ],
                metadata=_page_metadata(),
            )

        async def threaded_replies_get(threaded_reply_id: int) -> ThreadedReplyRecord:
            return ThreadedReplyRecord(
                id=threaded_reply_id,
                created="2024-01-11T18:50:12Z",
                updated="2024-01-26T19:13:27Z",
                createdById=1,
                refType="Note",
                refId=468,
                body="Hello world part 2",
                reactions=ReactionRecord(
                    id=1363,
                    created="2024-03-21T21:14:13Z",
                    createdBy="Tom Minch",
                    createdById=1,
                    refType="Note",
                    refId=2144705,
                    body="🤯",
                ),
            )

        async def appointments_list(
            request: AppointmentListRequest,
        ) -> PageResult[AppointmentRecord]:
            self.appointment_list_requests.append(request)
            return PageResult(
                items=[
                    AppointmentRecord(
                        id=8,
                        invitees=[
                            AppointmentInvitee.model_validate(
                                {"personId": request.person_id or 2, "name": "Data"}
                            )
                        ],
                        title="Buyer consult",
                        start="2026-03-28T10:00:00Z",
                        end="2026-03-28T11:00:00Z",
                    )
                ],
                metadata=_page_metadata(),
            )

        async def appointments_get(appointment_id: int) -> AppointmentRecord:
            return AppointmentRecord(
                id=appointment_id,
                title="Buyer consult",
                start="2026-03-28T10:00:00Z",
                end="2026-03-28T11:00:00Z",
            )

        async def appointments_create(_: CreateAppointmentRequest) -> AppointmentRecord:
            return AppointmentRecord(
                id=9,
                title="Listing appointment",
                start="2026-03-28T10:00:00Z",
                end="2026-03-28T11:00:00Z",
            )

        async def appointments_update(appointment_id: int, request: object) -> AppointmentRecord:
            del request
            return AppointmentRecord(
                id=appointment_id,
                title="Updated appointment",
                start="2026-03-29T10:00:00Z",
                end="2026-03-29T11:00:00Z",
            )

        async def appointments_delete(appointment_id: int) -> None:
            del appointment_id

        async def calls_list(request: CallListRequest) -> PageResult[CallRecord]:
            self.call_list_requests.append(request)
            return PageResult(
                items=[
                    CallRecord(
                        id=11,
                        personId=request.person_id or 2,
                        phone="555-0000",
                        userName="Data",
                    )
                ],
                metadata=_page_metadata(),
            )

        async def calls_get(call_id: int) -> CallRecord:
            return CallRecord(id=call_id, personId=2, phone="555-0000", userName="Data")

        async def calls_create(request: CreateCallRequest) -> CallRecord:
            self.call_create_requests.append(request)
            return CallRecord(
                id=12,
                personId=request.person_id,
                phone=request.phone,
                userId=request.user_id,
                userName="Picard",
            )

        async def calls_update(call_id: int, request: object) -> CallRecord:
            del request
            return CallRecord(id=call_id, personId=2, phone="555-0000", userName="Data")

        async def tasks_list(request: TaskListRequest) -> PageResult[TaskRecord]:
            self.task_list_requests.append(request)
            return PageResult(
                items=[TaskRecord(id=17, personId=2, assignedTo="Data", type="Call")],
                metadata=_page_metadata(),
            )

        async def tasks_get(task_id: int) -> TaskRecord:
            return TaskRecord(id=task_id, personId=2, assignedTo="Data", type="Call")

        async def tasks_create(_: CreateTaskRequest) -> TaskRecord:
            return TaskRecord(id=18, personId=2, assignedTo="Data", type="Email")

        async def tasks_update(task_id: int, request: object) -> TaskRecord:
            del request
            return TaskRecord(id=task_id, personId=2, assignedTo="Data", type="Text")

        async def tasks_delete(task_id: int) -> None:
            del task_id

        async def templates_list(_: TemplateListRequest) -> PageResult[TemplateRecord]:
            return PageResult(
                items=[TemplateRecord(id=19, name="Buyer intro", subject="Hello")],
                metadata=_page_metadata(),
            )

        async def templates_get(template_id: int, request: object | None = None) -> TemplateRecord:
            del request
            return TemplateRecord(id=template_id, name="Buyer intro", subject="Hello")

        async def templates_merge(_: MergeTemplateRequest) -> TemplateRecord:
            return TemplateRecord(
                id=20,
                name="I am here to help",
                subject="Your property inquiry from Zillow",
                body="Hi Bob, I am here to help, ...",
                isShared=True,
                isEditable=True,
                isDeletable=True,
            )

        async def templates_create(_: CreateTemplateRequest) -> TemplateRecord:
            return TemplateRecord(id=20, name="New template", subject="Hello")

        async def templates_update(template_id: int, request: object) -> TemplateRecord:
            del request
            return TemplateRecord(id=template_id, name="Updated template", subject="Updated")

        async def templates_delete(template_id: int) -> None:
            del template_id

        async def text_messages_list(
            request: TextMessageListRequest,
        ) -> PageResult[TextMessageRecord]:
            self.text_message_list_requests.append(request)
            return PageResult(
                items=[
                    TextMessageRecord(
                        id=31,
                        personId=request.person_id or 2,
                        message="Hi there",
                        userName="Data",
                    )
                ],
                metadata=_page_metadata(),
            )

        async def text_messages_get(text_message_id: int) -> TextMessageRecord:
            return TextMessageRecord(
                id=text_message_id,
                personId=2,
                message="Hi there",
                userName="Data",
            )

        async def text_messages_create(request: CreateTextMessageRequest) -> TextMessageRecord:
            self.text_message_create_requests.append(request)
            return TextMessageRecord(
                id=34,
                personId=request.person_id,
                message=request.message,
                fromNumber=request.from_number,
                toNumber=request.to_number,
                userName="Gerald Leenerts",
                isIncoming=request.is_incoming,
                externalLabel=request.external_label,
                externalUrl=request.external_url,
            )

        async def text_message_templates_list(
            _: TextMessageTemplateListRequest,
        ) -> PageResult[TextMessageTemplateRecord]:
            return PageResult(
                items=[
                    TextMessageTemplateRecord(
                        id=32,
                        name="Buyer intro text",
                        message="Hi there",
                    )
                ],
                metadata=_page_metadata(),
            )

        async def text_message_templates_get(template_id: int) -> TextMessageTemplateRecord:
            return TextMessageTemplateRecord(
                id=template_id, name="Buyer intro text", message="Hi there"
            )

        async def text_message_templates_merge(
            _: MergeTextMessageTemplateRequest,
        ) -> MergedTextMessageTemplateRecord:
            return MergedTextMessageTemplateRecord(mergedTemplate="Hey Bob, Alice and Carol...")

        async def text_message_templates_create(
            _: CreateTextMessageTemplateRequest,
        ) -> TextMessageTemplateRecord:
            return TextMessageTemplateRecord(id=33, name="New text template", message="Hello there")

        async def text_message_templates_update(
            template_id: int,
            request: object,
        ) -> TextMessageTemplateRecord:
            del request
            return TextMessageTemplateRecord(
                id=template_id,
                name="Updated text template",
                message="Updated text",
            )

        async def text_message_templates_delete(template_id: int) -> None:
            del template_id

        async def notes_add(_: CreateNoteRequest, wait_for_person: bool = False) -> NoteRecord:
            del wait_for_person
            return NoteRecord(id=8, body="created")

        async def notes_get(note_id: int) -> NoteRecord:
            return NoteRecord(id=note_id, body="loaded")

        async def notes_update(note_id: int, request: object) -> NoteRecord:
            del request
            return NoteRecord(id=note_id, body="updated")

        async def notes_delete(note_id: int) -> None:
            del note_id

        async def webhooks_list(_: WebhookListRequest) -> PageResult[WebhookRecord]:
            return PageResult(
                items=[WebhookRecord(id=9, event="peopleCreated", url="https://example.com")],
                metadata=_page_metadata(),
            )

        async def webhooks_create(_: CreateWebhookRequest) -> WebhookRecord:
            return WebhookRecord(id=10, event="peopleCreated", url="https://example.com")

        async def webhooks_get(webhook_id: int) -> WebhookRecord:
            return WebhookRecord(id=webhook_id, event="peopleCreated", url="https://example.com")

        async def webhooks_get_event(webhook_event_id: str) -> WebhookEventRecord:
            return WebhookEventRecord(
                id=webhook_event_id,
                eventId="4b762cb3-d7b6-4cf4-b7fb-fbd8cb0dfe11",
                eventCreated="2016-12-12T18:36:26Z",
                event="peopleUpdated",
                resourceIds=[99],
                uri="https://api.followupboss.com/v1/people/99",
                data={"changed": ["tags"]},
            )

        async def webhooks_update(webhook_id: int, request: object) -> WebhookRecord:
            del request
            return WebhookRecord(
                id=webhook_id,
                event="peopleUpdated",
                status="Disabled",
                url="https://example.com",
            )

        async def webhooks_delete(webhook_id: int) -> None:
            del webhook_id

        self.bundle = ServiceBundle(
            action_plans=_service_stub(
                list_action_plans=action_plans_list,
                list_action_plan_people=action_plan_people_list,
                apply_action_plan=action_plans_apply,
                update_action_plan_person=action_plan_people_update,
            ),
            appointments=_service_stub(
                list_appointments=appointments_list,
                get_appointment=appointments_get,
                create_appointment=appointments_create,
                update_appointment=appointments_update,
                delete_appointment=appointments_delete,
            ),
            appointment_outcomes=_service_stub(
                list_appointment_outcomes=appointment_outcomes_list,
                get_appointment_outcome=appointment_outcomes_get,
                create_appointment_outcome=appointment_outcomes_create,
                update_appointment_outcome=appointment_outcomes_update,
                delete_appointment_outcome=appointment_outcomes_delete,
            ),
            appointment_types=_service_stub(
                list_appointment_types=appointment_types_list,
                get_appointment_type=appointment_types_get,
                create_appointment_type=appointment_types_create,
                update_appointment_type=appointment_types_update,
                delete_appointment_type=appointment_types_delete,
            ),
            automation_people=_service_stub(
                list_automation_people=automation_people_list,
                get_automation_person=automation_people_get,
                create_automation_person=automation_people_create,
                update_automation_person=automation_people_update,
            ),
            automations=_service_stub(
                list_automations=automations_list,
                get_automation=automations_get,
            ),
            calls=_service_stub(
                list_calls=calls_list,
                get_call=calls_get,
                create_call=calls_create,
                update_call=calls_update,
            ),
            custom_fields=_service_stub(
                list_custom_fields=custom_fields_list,
                get_custom_field=custom_fields_get,
                create_custom_field=custom_fields_create,
                update_custom_field=custom_fields_update,
                delete_custom_field=custom_fields_delete,
            ),
            deal_attachments=_service_stub(
                get_deal_attachment=deal_attachments_get,
                create_deal_attachment=deal_attachments_create,
                update_deal_attachment=deal_attachments_update,
                delete_deal_attachment=deal_attachments_delete,
            ),
            deals=_service_stub(
                list_deals=deals_list,
                get_deal=deals_get,
                create_deal=deals_create,
                update_deal=deals_update,
                delete_deal=deals_delete,
                list_deal_custom_fields=deal_custom_fields_list,
                get_deal_custom_field=deal_custom_fields_get,
                create_deal_custom_field=deal_custom_fields_create,
                update_deal_custom_field=deal_custom_fields_update,
                delete_deal_custom_field=deal_custom_fields_delete,
            ),
            email_marketing=_service_stub(
                list_email_campaigns=email_marketing_list_campaigns,
                create_email_campaign=email_marketing_create_campaign,
                update_email_campaign=email_marketing_update_campaign,
                list_email_events=email_marketing_list_events,
                send_email_events=email_marketing_send_events,
            ),
            events=_service_stub(
                search_events=events_search,
                get_event=events_get,
                send_event=events_send,
            ),
            groups=_service_stub(
                list_groups=groups_list,
                list_round_robin_groups=groups_round_robin_list,
                get_group=groups_get,
                create_group=groups_create,
                update_group=groups_update,
                delete_group=groups_delete,
            ),
            identity=_service_stub(get_identity=identity_get),
            inbox_apps=_service_stub(
                list_inbox_app_installations=inbox_apps_list_installations,
                install_inbox_app=inbox_apps_install,
                deactivate_inbox_app=inbox_apps_deactivate,
                add_inbox_app_message=inbox_apps_add_message,
                add_inbox_app_note=inbox_apps_add_note,
                list_inbox_app_participants=inbox_apps_list_participants,
                add_inbox_app_participant=inbox_apps_add_participant,
                update_inbox_app_conversation=inbox_apps_update_conversation,
                update_inbox_app_message=inbox_apps_update_message,
                remove_inbox_app_participant=inbox_apps_remove_participant,
            ),
            notes=_service_stub(
                add_note=notes_add,
                get_note=notes_get,
                update_note=notes_update,
                delete_note=notes_delete,
            ),
            people=_service_stub(
                search_people=people_search,
                get_person=people_get,
                create_person=people_create,
                update_person=people_update,
                check_duplicate_person=people_check_duplicate,
                list_unclaimed_people=people_list_unclaimed,
                claim_person=people_claim,
                ignore_unclaimed_person=people_ignore_unclaimed,
                delete_person=people_delete,
            ),
            person_attachments=_service_stub(
                get_person_attachment=person_attachments_get,
                create_person_attachment=person_attachments_create,
                update_person_attachment=person_attachments_update,
                delete_person_attachment=person_attachments_delete,
            ),
            people_relationships=_service_stub(
                list_people_relationships=people_relationships_list,
                get_people_relationship=people_relationships_get,
                create_people_relationship=people_relationships_create,
                update_people_relationship=people_relationships_update,
                delete_people_relationship=people_relationships_delete,
            ),
            pipelines=_service_stub(
                list_pipelines=pipelines_list,
                get_pipeline=pipelines_get,
                create_pipeline=pipelines_create,
                update_pipeline=pipelines_update,
                delete_pipeline=pipelines_delete,
            ),
            ponds=_service_stub(
                list_ponds=ponds_list,
                get_pond=ponds_get,
                create_pond=ponds_create,
                update_pond=ponds_update,
                delete_pond=ponds_delete,
            ),
            reactions=_service_stub(
                get_reaction=reactions_get,
                add_reaction=reactions_add,
                delete_reaction=reactions_delete,
            ),
            smart_lists=_service_stub(
                list_smart_lists=smart_lists_list,
                get_smart_list=smart_lists_get,
            ),
            stages=_service_stub(
                list_stages=stages_list,
                get_stage=stages_get,
                create_stage=stages_create,
                update_stage=stages_update,
                delete_stage=stages_delete,
            ),
            tasks=_service_stub(
                list_tasks=tasks_list,
                get_task=tasks_get,
                create_task=tasks_create,
                update_task=tasks_update,
                delete_task=tasks_delete,
            ),
            team_inboxes=_service_stub(
                list_team_inboxes=team_inboxes_list,
            ),
            teams=_service_stub(
                list_teams=teams_list,
                get_team=teams_get,
                create_team=teams_create,
                update_team=teams_update,
                delete_team=teams_delete,
            ),
            threaded_replies=_service_stub(
                get_threaded_reply=threaded_replies_get,
            ),
            timeframes=_service_stub(
                list_timeframes=timeframes_list,
            ),
            text_message_templates=_service_stub(
                list_text_message_templates=text_message_templates_list,
                get_text_message_template=text_message_templates_get,
                merge_text_message_template=text_message_templates_merge,
                create_text_message_template=text_message_templates_create,
                update_text_message_template=text_message_templates_update,
                delete_text_message_template=text_message_templates_delete,
            ),
            text_messages=_service_stub(
                list_text_messages=text_messages_list,
                get_text_message=text_messages_get,
                create_text_message=text_messages_create,
            ),
            templates=_service_stub(
                list_templates=templates_list,
                get_template=templates_get,
                merge_template=templates_merge,
                create_template=templates_create,
                update_template=templates_update,
                delete_template=templates_delete,
            ),
            users=_service_stub(
                list_users=users_list,
                get_user=users_get,
                get_me=users_get_me,
                delete_user=users_delete,
            ),
            webhooks=_service_stub(
                list_webhooks=webhooks_list,
                get_webhook=webhooks_get,
                get_webhook_event=webhooks_get_event,
                create_webhook=webhooks_create,
                update_webhook=webhooks_update,
                delete_webhook=webhooks_delete,
            ),
        )


@pytest.mark.asyncio
async def test_tool_adapter_success_and_failure_paths() -> None:
    """The MCP adapter should normalize service results and safe errors."""
    stub = StubBundle()
    services = stub.bundle
    adapter = FollowUpBossToolAdapter(services)
    assert (await adapter.get_identity())["id"] == 1
    assert (await adapter.get_me())["id"] == 1
    assert (await adapter.get_me())["apiKey"] == "***redacted***"
    assert (await adapter.get_me())["algoliaKey"] == "***redacted***"
    assert (await adapter.get_me())["callingCapabilityToken"] == "***redacted***"
    assert (await adapter.get_me())["intercomSettings"]["user_hash"] == "***redacted***"
    assert (await adapter.search_people(PeopleSearchRequest()))["people"][0]["id"] == 2
    assert stub.people_search_requests[-1].assigned_user_id == 1
    assert stub.people_search_requests[-1].include_ponds is None
    assert (await adapter.get_latest_lead(GetLatestLeadToolInput()))["person"]["id"] == 2
    assert stub.people_search_requests[-1].assigned_user_id == 1
    assert stub.people_search_requests[-1].limit == 1
    assert stub.people_search_requests[-1].sort == "-created"
    assert GetLatestLeadToolInput(fields=["id", "name", "created"]).fields == [
        "id",
        "name",
        "created",
    ]
    with pytest.raises(ValidationError, match="Unsupported latest-lead fields"):
        GetLatestLeadToolInput(fields=["id", "createdAt"])
    assert (await adapter.search_people(PeopleSearchRequest(include_ponds=True)))["people"][0][
        "id"
    ] == 2
    assert stub.people_search_requests[-1].assigned_user_id is None
    assert stub.people_search_requests[-1].include_ponds is True
    assert (
        await adapter.search_people(
            PeopleSearchRequest(assigned_to="Scott Willey", contacted=False)
        )
    )["people"][0]["id"] == 2
    assert stub.people_search_requests[-1].assigned_to == "Scott Willey"
    assert stub.people_search_requests[-1].assigned_user_id is None
    assert stub.people_search_requests[-1].contacted is False
    my_uncontacted_leads = await adapter.list_uncontacted_leads(
        ListUncontactedLeadsToolInput(limit=25)
    )
    assert my_uncontacted_leads["people"][0]["id"] == 2
    assert stub.people_search_requests[-1].assigned_user_id == 1
    assert stub.people_search_requests[-1].contacted is None
    assert stub.people_search_requests[-1].sort == "-created"
    assert stub.people_search_requests[-1].fields is not None
    assert "lastCommunication" in stub.people_search_requests[-1].fields
    assert stub.people_search_requests[-1].smart_list_id is None
    assert stub.people_search_requests[-1].limit == 100
    assert my_uncontacted_leads["_metadata"]["limit"] == 25
    named_owner_uncontacted_leads = await adapter.list_uncontacted_leads(
        ListUncontactedLeadsToolInput(assigned_user_name="Geordi", source="Zillow")
    )
    assert named_owner_uncontacted_leads["people"][0]["id"] == 2
    assert stub.user_list_requests[-1].name == "Geordi"
    assert stub.user_list_requests[-1].include_deleted is False
    assert stub.people_search_requests[-1].assigned_user_id == 6
    assert stub.people_search_requests[-1].contacted is None
    assert stub.people_search_requests[-1].source == "Zillow"
    all_uncontacted_leads = await adapter.list_uncontacted_leads(
        ListUncontactedLeadsToolInput(mine=False)
    )
    assert all_uncontacted_leads["people"][0]["id"] == 2
    assert stub.people_search_requests[-1].assigned_user_id is None
    assert stub.people_search_requests[-1].contacted is None
    explicit_owner_uncontacted_leads = await adapter.list_uncontacted_leads(
        ListUncontactedLeadsToolInput(assigned_user_id=101)
    )
    assert explicit_owner_uncontacted_leads["people"][0]["id"] == 2
    assert stub.people_search_requests[-1].assigned_user_id == 101
    assert stub.people_search_requests[-1].contacted is None
    uncontacted_alias_input = ListUncontactedLeadsToolInput(
        owner_name="Geordi",
        lead_source="Zillow",
    )
    assert uncontacted_alias_input.assigned_user_name == "Geordi"
    assert uncontacted_alias_input.source == "Zillow"
    assert ListUncontactedLeadsToolInput(fields=["id", "name"]).fields == ["id", "name"]
    with pytest.raises(ValidationError, match="assigned_user_id must be a positive"):
        ListUncontactedLeadsToolInput(assigned_user_id=0)
    with pytest.raises(ValidationError, match="limit must be a positive integer"):
        ListUncontactedLeadsToolInput(limit=0)
    with pytest.raises(ValidationError, match="offset must be a non-negative integer"):
        ListUncontactedLeadsToolInput(offset=-1)
    with pytest.raises(ValidationError, match="Unsupported no-communication lead fields"):
        ListUncontactedLeadsToolInput(fields=["id", "createdAt"])
    with pytest.raises(ValidationError, match="Conflicting values"):
        ListUncontactedLeadsToolInput(owner_name="Geordi", agent_name="Worf")
    paginated_uncontacted_user_requests: list[UserListRequest] = []

    async def list_paginated_users(request: UserListRequest) -> PageResult[UserRecord]:
        paginated_uncontacted_user_requests.append(request)
        if len(paginated_uncontacted_user_requests) == 1:
            return PageResult(
                items=[UserRecord(id=5, name="Other Owner", status="Active")],
                metadata=PaginationMetadata(
                    count=1,
                    limit=1,
                    next_token=None,
                    next_link=None,
                    offset=0,
                    total=2,
                ),
            )
        return PageResult(
            items=[UserRecord(id=6, name="Geordi", status="Active")],
            metadata=PaginationMetadata(
                count=1,
                limit=1,
                next_token=None,
                next_link=None,
                offset=1,
                total=2,
            ),
        )

    paginated_user_adapter = FollowUpBossToolAdapter(
        replace(
            stub.bundle,
            users=_service_stub(
                list_users=list_paginated_users,
                get_user=stub.bundle.users.get_user,
                get_me=stub.bundle.users.get_me,
                delete_user=stub.bundle.users.delete_user,
            ),
        )
    )
    assert (
        await paginated_user_adapter.list_uncontacted_leads(
            ListUncontactedLeadsToolInput(assigned_user_name="Geordi")
        )
    )["people"][0]["id"] == 2
    assert [request.offset for request in paginated_uncontacted_user_requests] == [0, 1]
    paginated_no_communication_requests: list[PeopleSearchRequest] = []

    async def search_paginated_no_communication_people(
        request: PeopleSearchRequest,
    ) -> PageResult[PersonRecord]:
        paginated_no_communication_requests.append(request)
        if len(paginated_no_communication_requests) == 1:
            return PageResult(
                items=[
                    PersonRecord.model_validate(
                        {
                            "id": 10,
                            "name": "Quiet One",
                            "lastCommunication": None,
                        }
                    )
                ],
                metadata=PaginationMetadata(
                    count=1,
                    limit=1,
                    next_token=None,
                    next_link=None,
                    offset=0,
                    total=2,
                ),
            )
        return PageResult(
            items=[
                PersonRecord.model_validate(
                    {
                        "id": 11,
                        "name": "Recently Texted",
                        "lastCommunication": {"id": 99, "type": "Text"},
                    }
                ),
                PersonRecord.model_validate(
                    {
                        "id": 12,
                        "name": "Quiet Two",
                        "lastCommunication": "",
                    }
                ),
            ],
            metadata=PaginationMetadata(
                count=2,
                limit=2,
                next_token=None,
                next_link=None,
                offset=1,
                total=3,
            ),
        )

    paginated_no_communication_adapter = FollowUpBossToolAdapter(
        replace(
            stub.bundle,
            people=_service_stub(search_people=search_paginated_no_communication_people),
        )
    )
    paginated_no_communication = await paginated_no_communication_adapter.list_uncontacted_leads(
        ListUncontactedLeadsToolInput(fields=["id", "name"], limit=1, next_token="1")
    )
    assert paginated_no_communication["people"][0]["id"] == 12
    assert paginated_no_communication["_metadata"]["total"] == 2
    assert [request.offset for request in paginated_no_communication_requests] == [0, 1]
    assert paginated_no_communication_requests[0].fields == ["id", "lastCommunication", "name"]
    early_stop_no_communication_requests: list[PeopleSearchRequest] = []

    async def search_many_no_communication_people(
        request: PeopleSearchRequest,
    ) -> PageResult[PersonRecord]:
        early_stop_no_communication_requests.append(request)
        start = request.offset or 0
        return PageResult(
            items=[
                PersonRecord.model_validate(
                    {
                        "id": person_id,
                        "name": f"Quiet {person_id}",
                        "lastCommunication": None,
                    }
                )
                for person_id in range(start, start + 100)
            ],
            metadata=PaginationMetadata(
                count=100,
                limit=100,
                next_token=None,
                next_link=None,
                offset=start,
                total=200,
            ),
        )

    early_stop_no_communication_adapter = FollowUpBossToolAdapter(
        replace(
            stub.bundle,
            people=_service_stub(search_people=search_many_no_communication_people),
        )
    )
    early_stop_no_communication = await early_stop_no_communication_adapter.list_uncontacted_leads(
        ListUncontactedLeadsToolInput(limit=25)
    )
    assert [person["id"] for person in early_stop_no_communication["people"]] == list(range(25))
    early_stop_next_token = early_stop_no_communication["_metadata"]["next_token"]
    assert early_stop_next_token == "scan:25:25"
    assert early_stop_no_communication["_metadata"]["total"] is None
    assert [request.offset for request in early_stop_no_communication_requests] == [0]
    continued_no_communication = await early_stop_no_communication_adapter.list_uncontacted_leads(
        ListUncontactedLeadsToolInput(
            limit=25,
            next_token=cast(str, early_stop_next_token),
        )
    )
    assert [person["id"] for person in continued_no_communication["people"]] == list(range(25, 50))
    assert continued_no_communication["_metadata"]["next_token"] == "scan:50:50"
    assert continued_no_communication["_metadata"]["total"] is None
    assert [request.offset for request in early_stop_no_communication_requests] == [0, 25]
    boundary_no_communication_requests: list[PeopleSearchRequest] = []

    async def search_boundary_no_communication_people(
        request: PeopleSearchRequest,
    ) -> PageResult[PersonRecord]:
        boundary_no_communication_requests.append(request)
        start = request.offset or 0
        return PageResult(
            items=[
                PersonRecord.model_validate(
                    {
                        "id": person_id,
                        "name": f"Quiet {person_id}",
                        "lastCommunication": None,
                    }
                )
                for person_id in range(start, start + 100)
            ],
            metadata=PaginationMetadata(
                count=100,
                limit=100,
                next_token=None,
                next_link=None,
                offset=start,
                total=200,
            ),
        )

    boundary_no_communication_adapter = FollowUpBossToolAdapter(
        replace(
            stub.bundle,
            people=_service_stub(search_people=search_boundary_no_communication_people),
        )
    )
    boundary_no_communication = await boundary_no_communication_adapter.list_uncontacted_leads(
        ListUncontactedLeadsToolInput(limit=100)
    )
    assert [person["id"] for person in boundary_no_communication["people"]] == list(range(100))
    boundary_next_token = boundary_no_communication["_metadata"]["next_token"]
    assert boundary_next_token == "scan:100:100"
    boundary_continued_no_communication = (
        await boundary_no_communication_adapter.list_uncontacted_leads(
            ListUncontactedLeadsToolInput(
                limit=100,
                next_token=cast(str, boundary_next_token),
            )
        )
    )
    assert [person["id"] for person in boundary_continued_no_communication["people"]] == list(
        range(100, 200)
    )
    assert boundary_continued_no_communication["_metadata"]["next_token"] is None
    assert [request.offset for request in boundary_no_communication_requests] == [0, 100]
    with pytest.raises(RuntimeError, match="pagination token is invalid"):
        await paginated_no_communication_adapter.list_uncontacted_leads(
            ListUncontactedLeadsToolInput(next_token="not-a-number")
        )
    with pytest.raises(RuntimeError, match="pagination token is invalid"):
        await paginated_no_communication_adapter.list_uncontacted_leads(
            ListUncontactedLeadsToolInput(next_token="scan:1:not-a-number")
        )
    assert (await adapter.search_people(PeopleSearchRequest(smart_list_id=74)))["people"][0][
        "id"
    ] == 2
    assert stub.people_search_requests[-1].assigned_user_id == 1
    assert stub.people_search_requests[-1].include_ponds is None
    assert stub.people_search_requests[-1].smart_list_id == 74
    assert (await adapter.search_people(PeopleSearchRequest(include_ponds=True, smart_list_id=74)))[
        "people"
    ][0]["id"] == 2
    assert stub.people_search_requests[-1].assigned_user_id is None
    assert stub.people_search_requests[-1].smart_list_id == 74
    smart_list_people = await adapter.search_people_in_smart_list(
        SearchPeopleInSmartListToolInput(
            smart_list_name=" active   buyers ",
            source="Zillow",
            limit=5,
        )
    )
    assert smart_list_people["smartlist"] == {
        "id": 74,
        "description": "All active buyers",
        "isFub2": True,
        "name": "🚨 Active Buyers ✅",
    }
    assert smart_list_people["people"][0]["id"] == 2
    assert stub.people_search_requests[-1].assigned_user_id == 1
    assert stub.people_search_requests[-1].smart_list_id == 74
    assert stub.people_search_requests[-1].source == "Zillow"
    assert stub.people_search_requests[-1].limit == 5
    eligible_transfer_services = replace(
        stub.bundle,
        smart_lists=_service_stub(
            list_smart_lists=lambda _request: asyncio.sleep(
                0,
                result=PageResult(
                    items=[SmartListRecord(id=77, name="Eligible For Transfer")],
                    metadata=_page_metadata(),
                ),
            ),
            get_smart_list=stub.bundle.smart_lists.get_smart_list,
        ),
    )
    eligible_transfer_adapter = FollowUpBossToolAdapter(eligible_transfer_services)
    eligible_transfer_people = await eligible_transfer_adapter.search_people_in_smart_list(
        SearchPeopleInSmartListToolInput(
            smart_list_name="Eligible For Transfer",
            source="Zillow",
        )
    )
    assert eligible_transfer_people["people"][0]["id"] == 2
    assert stub.people_search_requests[-1].assigned_user_id == 1
    assert stub.people_search_requests[-1].smart_list_id == 77
    assert stub.people_search_requests[-1].source is None
    everyone_smart_list_people = await adapter.search_people_in_smart_list(
        SearchPeopleInSmartListToolInput(
            smart_list_name="Active Buyers",
            source="Zillow",
            mine=False,
        )
    )
    assert everyone_smart_list_people["people"][0]["id"] == 2
    assert stub.people_search_requests[-1].assigned_user_id is None
    mine_smart_list_people = await adapter.search_people_in_smart_list(
        SearchPeopleInSmartListToolInput(
            smart_list_name="Active Buyers",
            source="Zillow",
            mine=True,
        )
    )
    assert mine_smart_list_people["people"][0]["id"] == 2
    assert stub.people_search_requests[-1].assigned_user_id == 1
    explicit_owner_smart_list_people = await adapter.search_people_in_smart_list(
        SearchPeopleInSmartListToolInput(
            smart_list_name="Active Buyers",
            source="Zillow",
            assigned_user_id=101,
        )
    )
    assert explicit_owner_smart_list_people["people"][0]["id"] == 2
    assert stub.people_search_requests[-1].assigned_user_id == 101
    owner_name_smart_list_people = await adapter.search_people_in_smart_list(
        SearchPeopleInSmartListToolInput(
            smart_list_name="Active Buyers",
            source="Zillow",
            assigned_user_name="Geordi",
        )
    )
    assert owner_name_smart_list_people["people"][0]["id"] == 2
    assert stub.user_list_requests[-1].name == "Geordi"
    assert stub.user_list_requests[-1].include_deleted is False
    assert stub.people_search_requests[-1].assigned_user_id == 6
    assert stub.people_search_requests[-1].smart_list_id == 74
    user_lookup_count = len(stub.user_list_requests)
    explicit_owner_still_wins = await adapter.search_people_in_smart_list(
        SearchPeopleInSmartListToolInput(
            smart_list_name="Active Buyers",
            assigned_user_id=101,
            assigned_user_name="Geordi",
        )
    )
    assert explicit_owner_still_wins["people"][0]["id"] == 2
    assert len(stub.user_list_requests) == user_lookup_count
    assert stub.people_search_requests[-1].assigned_user_id == 101
    aliased_input = SearchPeopleInSmartListToolInput(
        list_name="Active Buyers",
        lead_source="Zillow",
        owner_name="Geordi",
    )
    assert aliased_input.resolved_smart_list_name() == "Active Buyers"
    assert aliased_input.source == "Zillow"
    assert aliased_input.assigned_user_name == "Geordi"
    with pytest.raises(RuntimeError, match="must be normalized"):
        SearchPeopleInSmartListToolInput.model_construct(
            smart_list_name=None,
        ).resolved_smart_list_name()
    with pytest.raises(ValidationError, match="smart_list_name must be non-empty"):
        SearchPeopleInSmartListToolInput(smart_list_name=" ")
    with pytest.raises(ValidationError, match="assigned_user_id must be a positive"):
        SearchPeopleInSmartListToolInput(smart_list_name="Active Buyers", assigned_user_id=0)
    with pytest.raises(ValidationError, match="Conflicting values"):
        SearchPeopleInSmartListToolInput(
            smart_list_name="Active Buyers",
            list_name="Seller Leads",
        )
    with pytest.raises(ValidationError, match="Conflicting values"):
        SearchPeopleInSmartListToolInput(
            smart_list_name="Active Buyers",
            owner_name="Geordi",
            agent_name="Worf",
        )
    with pytest.raises(RuntimeError, match="Smart list named 'Missing List' was not found"):
        await adapter.search_people_in_smart_list(
            SearchPeopleInSmartListToolInput(smart_list_name="Missing List")
        )
    person_activity = await adapter.list_person_activity(
        ListPersonActivityToolInput(person_id=42, limit=5)
    )
    assert person_activity["person"]["id"] == 42
    assert person_activity["calls"][0]["personId"] == 42
    assert person_activity["textmessages"][0]["personId"] == 42
    assert person_activity["emEvents"][0]["personId"] == 42
    assert person_activity["events"][0]["personId"] == 42
    assert person_activity["appointments"][0]["invitees"][0]["personId"] == 42
    assert stub.call_list_requests[-1].person_id == 42
    assert stub.call_list_requests[-1].limit == 5
    assert stub.text_message_list_requests[-1].person_id == 42
    assert stub.email_event_list_requests[-1].person_id == 42
    assert stub.event_search_requests[-1].person_id == 42
    assert stub.appointment_list_requests[-1].person_id == 42
    calls_only_activity = await adapter.list_person_activity(
        ListPersonActivityToolInput(
            person_id=42,
            include_appointments=False,
            include_email_events=False,
            include_events=False,
            include_text_messages=False,
        )
    )
    assert list(calls_only_activity["_metadata"]) == ["calls"]
    assert "textmessages" not in calls_only_activity
    no_calls_activity = await adapter.list_person_activity(
        ListPersonActivityToolInput(person_id=42, include_calls=False)
    )
    assert "calls" not in no_calls_activity
    assert "textmessages" in no_calls_activity
    with pytest.raises(ValidationError, match="At least one person activity surface"):
        ListPersonActivityToolInput(
            person_id=42,
            include_appointments=False,
            include_calls=False,
            include_email_events=False,
            include_events=False,
            include_text_messages=False,
        )
    ambiguous_services = replace(
        stub.bundle,
        smart_lists=_service_stub(
            list_smart_lists=lambda _request: asyncio.sleep(
                0,
                result=PageResult(
                    items=[
                        SmartListRecord(id=74, name="Active Buyers"),
                        SmartListRecord(id=75, name=" active buyers "),
                    ],
                    metadata=_page_metadata(),
                ),
            ),
            get_smart_list=stub.bundle.smart_lists.get_smart_list,
        ),
    )
    ambiguous_adapter = FollowUpBossToolAdapter(ambiguous_services)
    with pytest.raises(RuntimeError, match="ambiguous; matched IDs \\[74, 75\\]"):
        await ambiguous_adapter.search_people_in_smart_list(
            SearchPeopleInSmartListToolInput(smart_list_name="Active Buyers")
        )
    ambiguous_user_services = replace(
        stub.bundle,
        users=_service_stub(
            list_users=lambda _request: asyncio.sleep(
                0,
                result=PageResult(
                    items=[
                        UserRecord(id=6, name="Geordi"),
                        UserRecord(id=7, firstName="Geordi", lastName=""),
                    ],
                    metadata=_page_metadata(),
                ),
            ),
            get_user=stub.bundle.users.get_user,
            get_me=stub.bundle.users.get_me,
            delete_user=stub.bundle.users.delete_user,
        ),
    )
    ambiguous_user_adapter = FollowUpBossToolAdapter(ambiguous_user_services)
    with pytest.raises(RuntimeError, match="ambiguous; matched IDs \\[6, 7\\]"):
        await ambiguous_user_adapter.search_people_in_smart_list(
            SearchPeopleInSmartListToolInput(
                smart_list_name="Active Buyers",
                assigned_user_name="Geordi",
            )
        )
    with pytest.raises(RuntimeError, match="ambiguous; matched IDs \\[6, 7\\]"):
        await ambiguous_user_adapter.list_uncontacted_leads(
            ListUncontactedLeadsToolInput(assigned_user_name="Geordi")
        )
    missing_user_services = replace(
        stub.bundle,
        users=_service_stub(
            list_users=lambda _request: asyncio.sleep(
                0,
                result=PageResult(
                    items=[UserRecord(id=8, name="Geordi", status="Deleted")],
                    metadata=_page_metadata(),
                ),
            ),
            get_user=stub.bundle.users.get_user,
            get_me=stub.bundle.users.get_me,
            delete_user=stub.bundle.users.delete_user,
        ),
    )
    missing_user_adapter = FollowUpBossToolAdapter(missing_user_services)
    with pytest.raises(
        RuntimeError, match="Active Follow Up Boss user named 'Geordi' was not found"
    ):
        await missing_user_adapter.search_people_in_smart_list(
            SearchPeopleInSmartListToolInput(
                smart_list_name="Active Buyers",
                assigned_user_name="Geordi",
            )
        )
    with pytest.raises(
        RuntimeError, match="Active Follow Up Boss user named 'Geordi' was not found"
    ):
        await missing_user_adapter.list_uncontacted_leads(
            ListUncontactedLeadsToolInput(assigned_user_name="Geordi")
        )
    missing_identity_services = replace(
        stub.bundle,
        identity=_service_stub(
            get_identity=lambda: asyncio.sleep(0, result=IdentityResponse(id=None))
        ),
    )
    missing_identity_adapter = FollowUpBossToolAdapter(missing_identity_services)
    with pytest.raises(RuntimeError, match="Authenticated Follow Up Boss user id is unavailable"):
        await missing_identity_adapter.list_uncontacted_leads(ListUncontactedLeadsToolInput())
    paginated_smart_list_requests: list[SmartListListRequest] = []

    async def paginated_smart_lists_list(
        request: SmartListListRequest,
    ) -> PageResult[SmartListRecord]:
        paginated_smart_list_requests.append(request)
        if len(paginated_smart_list_requests) == 1:
            return PageResult(
                items=[SmartListRecord(id=73, name="First Page")],
                metadata=PaginationMetadata(
                    count=1,
                    limit=1,
                    next_token=None,
                    next_link=None,
                    offset=0,
                    total=2,
                ),
            )
        return PageResult(
            items=[SmartListRecord(id=74, name="Active Buyers")],
            metadata=PaginationMetadata(
                count=1,
                limit=1,
                next_token=None,
                next_link=None,
                offset=1,
                total=2,
            ),
        )

    paginated_services = replace(
        stub.bundle,
        smart_lists=_service_stub(
            list_smart_lists=paginated_smart_lists_list,
            get_smart_list=stub.bundle.smart_lists.get_smart_list,
        ),
    )
    paginated_adapter = FollowUpBossToolAdapter(paginated_services)
    assert (
        await paginated_adapter.search_people_in_smart_list(
            SearchPeopleInSmartListToolInput(smart_list_name="Active Buyers")
        )
    )["smartlist"]["id"] == 74
    assert [request.offset for request in paginated_smart_list_requests] == [0, 1]
    paginated_user_requests: list[UserListRequest] = []

    async def paginated_users_list(request: UserListRequest) -> PageResult[UserRecord]:
        paginated_user_requests.append(request)
        if len(paginated_user_requests) == 1:
            return PageResult(
                items=[UserRecord(id=5, name="Other Owner")],
                metadata=PaginationMetadata(
                    count=1,
                    limit=1,
                    next_token=None,
                    next_link=None,
                    offset=0,
                    total=2,
                ),
            )
        return PageResult(
            items=[UserRecord(id=6, name="Geordi")],
            metadata=PaginationMetadata(
                count=1,
                limit=1,
                next_token=None,
                next_link=None,
                offset=1,
                total=2,
            ),
        )

    paginated_user_services = replace(
        stub.bundle,
        users=_service_stub(
            list_users=paginated_users_list,
            get_user=stub.bundle.users.get_user,
            get_me=stub.bundle.users.get_me,
            delete_user=stub.bundle.users.delete_user,
        ),
    )
    paginated_user_adapter = FollowUpBossToolAdapter(paginated_user_services)
    assert (
        await paginated_user_adapter.search_people_in_smart_list(
            SearchPeopleInSmartListToolInput(
                smart_list_name="Active Buyers",
                assigned_user_name="Geordi",
            )
        )
    )["people"][0]["id"] == 2
    assert [request.offset for request in paginated_user_requests] == [0, 1]
    assert (await adapter.get_person(GetPersonToolInput(person_id=3)))["id"] == 3
    assert (await adapter.create_person(CreatePersonRequest(first_name="Tom")))["id"] == 3
    assert (await adapter.update_person(UpdatePersonToolInput(person_id=4)))["id"] == 4
    assert (
        await adapter.check_duplicate_person(
            CheckDuplicatePersonToolInput(email="agent@example.com")
        )
    ) == {
        "found": True,
        "matchedBy": "email",
        "assignedTo": "Agent Smith",
    }
    assert (await adapter.list_unclaimed_people(UnclaimedPeopleListRequest()))["people"][0][
        "id"
    ] == 6
    assert (await adapter.claim_person(ClaimPersonToolInput(person_id=7)))["id"] == 7
    assert (await adapter.ignore_unclaimed_person(IgnoreUnclaimedPersonToolInput(person_id=7))) == {
        "deleted": True,
        "personId": 7,
    }
    assert (await adapter.delete_person(DeletePersonToolInput(person_id=8))) == {
        "deleted": True,
        "personId": 8,
    }
    assert (
        await adapter.get_person_attachment(GetPersonAttachmentToolInput(person_attachment_id=2))
    )["id"] == 2
    assert (
        await adapter.create_person_attachment(
            CreatePersonAttachmentRequest(
                person_id=1,
                uri="https://test.com/myfile",
                file_name="test.jpg",
            )
        )
    )["id"] == 3
    assert (
        await adapter.update_person_attachment(
            UpdatePersonAttachmentToolInput(
                person_attachment_id=4,
                person_id=1,
                uri="https://test.com/updated",
                file_name="updated.jpg",
            )
        )
    )["id"] == 4
    assert (
        await adapter.delete_person_attachment(
            DeletePersonAttachmentToolInput(person_attachment_id=5)
        )
    ) == {
        "deleted": True,
        "personAttachmentId": 5,
    }
    assert (
        await adapter.list_people_relationships(PeopleRelationshipListRequest(person_id=46977))
    )["peopleRelationships"][0]["id"] == 423
    assert (
        await adapter.get_people_relationship(
            GetPeopleRelationshipToolInput(people_relationship_id=423)
        )
    )["id"] == 423
    assert (
        await adapter.create_people_relationship(CreatePeopleRelationshipRequest(person_id=46977))
    ) == {}
    assert (
        await adapter.update_people_relationship(
            UpdatePeopleRelationshipToolInput(people_relationship_id=423, type="Spouse")
        )
    ) == {}
    assert (
        await adapter.delete_people_relationship(
            DeletePeopleRelationshipToolInput(people_relationship_id=423)
        )
    ) == {
        "deleted": True,
        "peopleRelationshipId": 423,
    }
    assert (await adapter.get_reaction(GetReactionToolInput(reaction_id=1363)))["id"] == 1363
    assert (
        await adapter.add_reaction(AddReactionToolInput(ref_type="Note", ref_id=2144705, body="🤣"))
    ) == {}
    assert (
        await adapter.delete_reaction(
            DeleteReactionToolInput(ref_type="Note", ref_id=2144705, emoji="👏")
        )
    ) == {
        "deleted": True,
        "refId": 2144705,
    }
    assert (await adapter.get_threaded_reply(GetThreadedReplyToolInput(threaded_reply_id=1)))[
        "id"
    ] == 1
    assert (await adapter.search_events(EventSearchRequest()))["events"][0]["id"] == 4
    assert (await adapter.get_event(GetEventToolInput(event_id=6)))["id"] == 6
    assert (
        await adapter.send_event(
            CreateEventRequest(
                source="Portal", system="Portal", type="Inquiry", person=EventPersonInput()
            )
        )
    )["id"] == 5
    assert (await adapter.list_users(UserListRequest()))["users"][0]["id"] == 6
    assert (await adapter.get_user(GetUserToolInput(user_id=7)))["id"] == 7
    assert (await adapter.delete_user(DeleteUserToolInput(user_id=8, assign_to=5))) == {
        "deleted": True,
        "userId": 8,
    }
    assert (await adapter.list_appointment_outcomes(AppointmentOutcomeListRequest()))[
        "appointmentoutcomes"
    ][0]["id"] == 7
    assert (
        await adapter.get_appointment_outcome(
            GetAppointmentOutcomeToolInput(appointment_outcome_id=8)
        )
    )["id"] == 8
    assert (
        await adapter.create_appointment_outcome(
            CreateAppointmentOutcomeRequest(name="No Show", order_weight=2000)
        )
    )["id"] == 8
    assert (
        await adapter.update_appointment_outcome(
            UpdateAppointmentOutcomeToolInput(
                appointment_outcome_id=9,
                name="Rescheduled",
            )
        )
    )["id"] == 9
    assert (
        await adapter.delete_appointment_outcome(
            DeleteAppointmentOutcomeToolInput(
                appointment_outcome_id=10,
                assign_outcome_id=7,
            )
        )
    ) == {
        "deleted": True,
        "appointmentOutcomeId": 10,
    }
    assert (await adapter.list_appointment_types(AppointmentTypeListRequest()))["appointmenttypes"][
        0
    ]["id"] == 9
    assert (
        await adapter.get_appointment_type(GetAppointmentTypeToolInput(appointment_type_id=10))
    )["id"] == 10
    assert (
        await adapter.create_appointment_type(
            CreateAppointmentTypeRequest(name="Listing Consult", order_weight=2000)
        )
    )["id"] == 10
    assert (
        await adapter.update_appointment_type(
            UpdateAppointmentTypeToolInput(
                appointment_type_id=11,
                name="Showing",
            )
        )
    )["id"] == 11
    assert (
        await adapter.delete_appointment_type(
            DeleteAppointmentTypeToolInput(
                appointment_type_id=12,
                assign_type_id=9,
            )
        )
    ) == {
        "deleted": True,
        "appointmentTypeId": 12,
    }
    assert (await adapter.list_action_plans(ActionPlanListRequest()))["actionPlans"][0]["id"] == 5
    assert (await adapter.list_action_plan_people(ActionPlanPersonListRequest(action_plan_id=5)))[
        "actionPlansPeople"
    ][0]["id"] == 6
    assert (
        await adapter.apply_action_plan(
            CreateActionPlanPersonRequest(action_plan_id=5, person_id=10810)
        )
    )["id"] == 7
    assert (
        await adapter.update_action_plan_person(
            UpdateActionPlanPersonToolInput(action_plan_person_id=8, status="Paused")
        )
    )["id"] == 8
    assert (
        await adapter.list_inbox_app_installations(
            ListInboxAppInstallationsToolInput(published_inbox_app_id=9)
        )
    )["inboxApps"][0]["inboxAppId"] == 130
    assert (
        await adapter.install_inbox_app(
            InstallInboxAppRequest(
                published_inbox_app_id=9,
                user_id=0,
                subscription_url="https://example.com/webhook",
            )
        )
    )["id"] == 131
    assert (await adapter.deactivate_inbox_app(DeactivateInboxAppToolInput(inbox_app_id=131))) == {
        "deleted": True,
        "inboxAppId": 131,
    }
    assert (
        await adapter.list_inbox_app_participants(
            ListInboxAppParticipantsToolInput(inbox_app_id=131, ext_conversation_id="conv-123")
        )
    )["participants"][0]["id"] == 132
    assert (
        await adapter.add_inbox_app_participant(
            AddInboxAppParticipantToolInput(
                inbox_app_id=131,
                ext_conversation_id="conv-123",
                name="John Doe",
                email="john@example.com",
            )
        )
    )["id"] == 133
    assert (
        await adapter.remove_inbox_app_participant(
            DeleteInboxAppParticipantToolInput(
                inbox_app_id=131,
                ext_conversation_id="conv-123",
                participant_id=133,
            )
        )
    ) == {
        "deleted": True,
        "participantId": 133,
    }
    assert (
        await adapter.add_inbox_app_message(
            AddInboxAppMessageToolInput.model_validate(
                {
                    "inbox_app_id": 131,
                    "external_conversation_id": "conv-123",
                    "external_message_id": "msg-123",
                    "message": "An example message.",
                    "is_incoming": True,
                    "sender": {"personId": 1},
                }
            )
        )
    )["id"] == 134
    assert (
        await adapter.add_inbox_app_note(
            AddInboxAppNoteToolInput.model_validate(
                {
                    "inbox_app_id": 131,
                    "external_conversation_id": "conv-123",
                    "body": "An example note.",
                    "user": {"id": 1},
                }
            )
        )
    )["id"] == 135
    assert (
        await adapter.update_inbox_app_conversation(
            UpdateInboxAppConversationToolInput.model_validate(
                {
                    "inbox_app_id": 131,
                    "ext_conversation_id": "conv-123",
                    "subject": "A Conversation Subject",
                    "archived": False,
                }
            )
        )
    )["externalConversationId"] == "conv-123"
    assert (
        await adapter.update_inbox_app_message(
            UpdateInboxAppMessageToolInput(
                inbox_app_id=131,
                id=134,
                external_message_id="msg-124",
                delivery_status="Delivered",
            )
        )
    )["id"] == 136
    assert (await adapter.list_automations(AutomationListRequest()))["automations"][0]["id"] == 50
    assert (await adapter.get_automation(GetAutomationToolInput(automation_id=51)))["id"] == 51
    assert (await adapter.list_automation_people(AutomationPeopleListRequest(automation_id=50)))[
        "automationsPeople"
    ][0]["id"] == 51
    assert (
        await adapter.get_automation_person(GetAutomationPersonToolInput(automation_person_id=52))
    )["id"] == 52
    assert (
        await adapter.trigger_automation(
            CreateAutomationPersonRequest(automation_id=50, person_id=3)
        )
    )["id"] == 52
    assert (
        await adapter.update_automation_person(
            UpdateAutomationPersonToolInput(
                automation_person_id=53,
                status="Paused",
            )
        )
    )["id"] == 53
    assert (await adapter.list_groups(GroupListRequest(type="Agent")))["groups"][0]["id"] == 6
    assert (await adapter.list_round_robin_groups(GroupListRequest(type="Agent")))["groups"][0][
        "id"
    ] == 7
    assert (await adapter.get_group(GetGroupToolInput(group_id=11)))["id"] == 11
    assert (
        await adapter.create_group(
            CreateGroupRequest(name="Westside", users=[200, 201], distribution="round-robin")
        )
    )["id"] == 11
    assert (
        await adapter.update_group(
            UpdateGroupToolInput(group_id=12, name="Westside Plus", users=[200, 201])
        )
    )["id"] == 12
    assert (await adapter.delete_group(DeleteGroupToolInput(group_id=13))) == {
        "deleted": True,
        "groupId": 13,
    }
    assert (await adapter.list_team_inboxes(TeamInboxListRequest()))["teamInboxes"][0]["id"] == 121
    assert (await adapter.list_timeframes(TimeframeListRequest()))["timeframes"][0]["id"] == 1
    assert (await adapter.list_custom_fields(CustomFieldListRequest()))["customfields"][0][
        "id"
    ] == 7
    assert (await adapter.get_custom_field(GetCustomFieldToolInput(custom_field_id=12)))["id"] == 12
    assert (
        await adapter.create_custom_field(
            CreateCustomFieldRequest(label="Looking for", type="dropdown", choices=["Apartment"])
        )
    )["id"] == 12
    assert (
        await adapter.update_custom_field(
            UpdateCustomFieldToolInput(custom_field_id=13, label="Looking for")
        )
    )["id"] == 13
    assert (await adapter.delete_custom_field(DeleteCustomFieldToolInput(custom_field_id=14))) == {
        "deleted": True,
        "customFieldId": 14,
    }
    assert (await adapter.list_email_campaigns(EmailCampaignListRequest(origin="Curaytor")))[
        "emCampaigns"
    ][0]["id"] == 201
    assert (
        await adapter.create_email_campaign(
            CreateEmailCampaignRequest(origin="Curaytor", origin_id="913", name="New Campaign")
        )
    )["id"] == 202
    assert (
        await adapter.update_email_campaign(
            UpdateEmailCampaignToolInput(email_campaign_id=203, name="Updated Campaign")
        )
    )["id"] == 203
    assert (await adapter.list_email_events(EmailEventListRequest(type="open")))["emEvents"][0][
        "campaignId"
    ] == 102
    assert (
        await adapter.send_email_events(
            CreateEmailEventsBatchRequest.model_validate(
                {
                    "em_events": [
                        {
                            "type": "delivered",
                            "occurred": "2026-03-28T13:00:00Z",
                            "recipient": "john.smith@gmail.com",
                            "campaign_id": 141,
                        }
                    ]
                }
            )
        )
    )["emEventIds"] == [193928, 193929]
    assert (await adapter.list_deals(DealListRequest()))["deals"][0]["id"] == 8
    assert (
        await adapter.list_active_deals_for_person(ListActiveDealsForPersonToolInput(person_id=42))
    )["deals"][0]["id"] == 8
    assert stub.deal_list_requests[-1].person_id == 42
    assert stub.deal_list_requests[-1].status == "Active"
    assert stub.deal_list_requests[-1].include_archived is False
    assert stub.deal_list_requests[-1].include_deleted is False
    assert (await adapter.get_deal(GetDealToolInput(deal_id=9)))["id"] == 9
    assert (
        await adapter.create_deal(
            CreateDealRequest(name="New deal", stage_id=7, custom_fields={"customClosePrice": 1})
        )
    )["id"] == 9
    assert (
        await adapter.update_deal(
            UpdateDealToolInput(deal_id=10, stage_id=8, custom_fields={"customClosePrice": 2})
        )
    )["id"] == 10
    assert (await adapter.delete_deal(DeleteDealToolInput(deal_id=11))) == {
        "deleted": True,
        "dealId": 11,
    }
    assert (await adapter.get_deal_attachment(GetDealAttachmentToolInput(deal_attachment_id=10)))[
        "id"
    ] == 10
    assert (
        await adapter.create_deal_attachment(
            CreateDealAttachmentRequest(
                deal_id=8,
                uri="https://test.com/deal",
                file_name="deal.jpg",
            )
        )
    )["id"] == 11
    assert (
        await adapter.update_deal_attachment(
            UpdateDealAttachmentToolInput(
                deal_attachment_id=12,
                deal_id=9,
                uri="https://test.com/deal-updated",
                file_name="deal-updated.jpg",
            )
        )
    )["id"] == 12
    assert (
        await adapter.delete_deal_attachment(DeleteDealAttachmentToolInput(deal_attachment_id=13))
    ) == {
        "deleted": True,
        "dealAttachmentId": 13,
    }
    assert (await adapter.list_deal_custom_fields(DealCustomFieldListRequest()))[
        "dealCustomfields"
    ][0]["id"] == 10
    assert (
        await adapter.get_deal_custom_field(GetDealCustomFieldToolInput(deal_custom_field_id=45))
    )["id"] == 45
    assert (
        await adapter.create_deal_custom_field(
            CreateDealCustomFieldRequest(
                label="Priority",
                type="dropdown",
                choices=["High", "Medium", "Low"],
            )
        )
    )["id"] == 45
    assert (
        await adapter.update_deal_custom_field(
            UpdateDealCustomFieldToolInput(
                deal_custom_field_id=46,
                label="Priority",
                choices=["Critical", "High", "Medium"],
                read_only=True,
            )
        )
    )["id"] == 46
    assert (
        await adapter.delete_deal_custom_field(
            DeleteDealCustomFieldToolInput(deal_custom_field_id=47)
        )
    ) == {
        "deleted": True,
        "dealCustomFieldId": 47,
    }
    assert (await adapter.list_pipelines(PipelineListRequest()))["pipelines"][0]["id"] == 11
    assert (await adapter.get_pipeline(GetPipelineToolInput(pipeline_id=12)))["id"] == 12
    assert (
        await adapter.create_pipeline(
            CreatePipelineRequest(
                name="New pipeline",
                description="New flow",
                stages=[PipelineStageInput(name="Warm", closed_stage=False)],
            )
        )
    )["id"] == 12
    assert (
        await adapter.update_pipeline(
            UpdatePipelineToolInput(
                pipeline_id=13,
                name="Updated pipeline",
                stages=[PipelineStageInput(id=21, name="Closed won", closed_stage=True)],
            )
        )
    )["id"] == 13
    assert (await adapter.delete_pipeline(DeletePipelineToolInput(pipeline_id=14))) == {
        "deleted": True,
        "pipelineId": 14,
    }
    assert (await adapter.list_ponds(PondListRequest()))["ponds"][0]["id"] == 70
    assert (await adapter.get_pond(GetPondToolInput(pond_id=71)))["id"] == 71
    assert (
        await adapter.create_pond(
            CreatePondRequest(name="Sphere Builders", user_id=8, user_ids=[8, 9])
        )
    )["id"] == 71
    assert (
        await adapter.update_pond(
            UpdatePondToolInput(pond_id=72, name="Updated Pond", user_ids=[9, 10])
        )
    )["id"] == 72
    assert (await adapter.delete_pond(DeletePondToolInput(pond_id=73, assign_to=6))) == {
        "deleted": True,
        "pondId": 73,
    }
    assert (await adapter.list_smart_lists(SmartListListRequest()))["smartlists"][0]["id"] == 74
    assert (await adapter.get_smart_list(GetSmartListToolInput(smart_list_id=75)))["id"] == 75
    assert (await adapter.list_stages(StageListRequest()))["stages"][0]["id"] == 78
    assert (await adapter.get_stage(GetStageToolInput(stage_id=79)))["id"] == 79
    assert (await adapter.create_stage(CreateStageRequest(name="Qualified", order_weight=2000)))[
        "id"
    ] == 79
    assert (
        await adapter.update_stage(
            UpdateStageToolInput(stage_id=80, name="Updated Stage", order_weight=3000)
        )
    )["id"] == 80
    assert (await adapter.delete_stage(DeleteStageToolInput(stage_id=81, assign_stage_id=11))) == {
        "deleted": True,
        "stageId": 81,
    }
    assert (await adapter.list_teams(TeamListRequest()))["teams"][0]["id"] == 82
    assert (await adapter.get_team(GetTeamToolInput(team_id=83)))["id"] == 83
    assert (
        await adapter.create_team(
            CreateTeamRequest(name="Buyer Team", user_ids=[7, 8], leader_ids=[7])
        )
    )["id"] == 83
    assert (
        await adapter.update_team(
            UpdateTeamToolInput(
                team_id=84,
                name="Updated Team",
                user_ids=[9, 10],
                leader_ids=[9],
            )
        )
    )["id"] == 84
    assert (await adapter.delete_team(DeleteTeamToolInput(team_id=85, move_to_team_id=82))) == {
        "deleted": True,
        "teamId": 85,
    }
    assert (await adapter.list_appointments(AppointmentListRequest()))["appointments"][0]["id"] == 8
    assert (await adapter.get_appointment(GetAppointmentToolInput(appointment_id=9)))["id"] == 9
    assert (
        await adapter.create_appointment(
            CreateAppointmentRequest.model_validate(
                {
                    "title": "Listing appointment",
                    "start": "2026-03-28T10:00:00Z",
                    "end": "2026-03-28T11:00:00Z",
                }
            )
        )
    )["id"] == 9
    assert (
        await adapter.update_appointment(
            UpdateAppointmentToolInput.model_validate(
                {
                    "appointment_id": 10,
                    "title": "Updated appointment",
                    "start": "2026-03-29T10:00:00Z",
                    "end": "2026-03-29T11:00:00Z",
                }
            )
        )
    )["id"] == 10
    assert (await adapter.delete_appointment(DeleteAppointmentToolInput(appointment_id=11))) == {
        "deleted": True,
        "appointmentId": 11,
    }
    assert (await adapter.list_calls(CallListRequest()))["calls"][0]["id"] == 11
    assert (await adapter.get_call(GetCallToolInput(call_id=12)))["id"] == 12
    assert (
        await adapter.create_call(
            CreateCallRequest(person_id=1, phone="555-0000", is_incoming=True)
        )
    )["id"] == 12
    assert stub.call_create_requests[-1].user_id == 1
    assert (await adapter.update_call(UpdateCallToolInput(call_id=13, note="Updated note")))[
        "id"
    ] == 13
    assert (await adapter.list_tasks(TaskListRequest()))["tasks"][0]["id"] == 17
    assert (await adapter.list_my_overdue_tasks(ListMyTaskIntentToolInput(limit=25)))["tasks"][0][
        "id"
    ] == 17
    assert stub.task_list_requests[-1].assigned_user_id == 1
    assert stub.task_list_requests[-1].due == "overdue"
    assert stub.task_list_requests[-1].is_completed is False
    assert stub.task_list_requests[-1].limit == 25
    assert (await adapter.list_my_tasks_due_today(ListMyTaskIntentToolInput()))["tasks"][0][
        "id"
    ] == 17
    assert stub.task_list_requests[-1].assigned_user_id == 1
    assert stub.task_list_requests[-1].due == "today"
    assert stub.task_list_requests[-1].is_completed is False
    assert (await adapter.list_my_upcoming_tasks(ListMyTaskIntentToolInput(limit=10)))["tasks"][0][
        "id"
    ] == 17
    assert stub.task_list_requests[-1].assigned_user_id == 1
    assert stub.task_list_requests[-1].due is None
    assert stub.task_list_requests[-1].due_start is not None
    assert stub.task_list_requests[-1].is_completed is False
    assert stub.task_list_requests[-1].limit == 10
    assert ListMyTaskIntentToolInput(fields=["id", "name", "dueDate"]).fields == [
        "id",
        "name",
        "dueDate",
    ]
    with pytest.raises(ValidationError, match="Unsupported task fields"):
        ListMyTaskIntentToolInput(fields=["id", "personName"])
    assert (await adapter.get_task(GetTaskToolInput(task_id=18)))["id"] == 18
    assert (
        await adapter.create_task(CreateTaskRequest(person_id=1, assigned_to="Data", type="Email"))
    )["id"] == 18
    assert (await adapter.update_task(UpdateTaskToolInput(task_id=19, type="Text")))["id"] == 19
    assert (await adapter.delete_task(DeleteTaskToolInput(task_id=20))) == {
        "deleted": True,
        "taskId": 20,
    }
    assert (await adapter.list_templates(TemplateListRequest()))["templates"][0]["id"] == 19
    assert (await adapter.get_template(GetTemplateToolInput(template_id=20)))["id"] == 20
    assert (
        await adapter.merge_template(
            MergeTemplateRequest.model_validate(
                {
                    "template_id": 31,
                    "merge_person_id": 1213,
                    "recipients": {"to": [{"name": "Bob Alvarez", "email": "bob@example.com"}]},
                }
            )
        )
    )["id"] == 20
    assert (
        await adapter.create_template(
            CreateTemplateRequest(name="New template", subject="Hello", body="<p>Hello</p>")
        )
    )["id"] == 20
    assert (
        await adapter.update_template(
            UpdateTemplateToolInput(
                template_id=21,
                name="Updated template",
                subject="Updated",
                body="<p>Updated</p>",
            )
        )
    )["id"] == 21
    assert (await adapter.delete_template(DeleteTemplateToolInput(template_id=22))) == {
        "deleted": True,
        "templateId": 22,
    }
    assert (await adapter.list_text_messages(TextMessageListRequest()))["textmessages"][0][
        "id"
    ] == 31
    assert (await adapter.get_text_message(GetTextMessageToolInput(text_message_id=32)))["id"] == 32
    assert (
        await adapter.create_text_message(
            CreateTextMessageRequest(
                person_id=2,
                message="Logged externally",
                to_number="555-0002",
                from_number="1234567890",
                is_incoming=False,
                external_label="External SMS",
                external_url="https://example.com/sms/3",
            )
        )
    )["id"] == 34
    assert stub.text_message_create_requests[-1].from_number == "(123) 456-7890"
    assert (await adapter.list_text_message_templates(TextMessageTemplateListRequest()))[
        "textmessagetemplates"
    ][0]["id"] == 32
    assert (
        await adapter.get_text_message_template(GetTextMessageTemplateToolInput(template_id=33))
    )["id"] == 33
    assert (
        await adapter.merge_text_message_template(
            MergeTextMessageTemplateRequest.model_validate(
                {
                    "template_id": 31,
                    "person_id": 1213,
                    "recipients": {"to": [{"name": "Bob Alvarez", "phone": "+14075558075"}]},
                }
            )
        )
    )["mergedTemplate"] == "Hey Bob, Alice and Carol..."
    assert (
        await adapter.create_text_message_template(
            CreateTextMessageTemplateRequest(
                name="New text template",
                message="Hello there",
            )
        )
    )["id"] == 33
    assert (
        await adapter.update_text_message_template(
            UpdateTextMessageTemplateToolInput(
                template_id=34,
                name="Updated text template",
                message="Updated text",
            )
        )
    )["id"] == 34
    assert (
        await adapter.delete_text_message_template(
            DeleteTextMessageTemplateToolInput(template_id=35)
        )
    ) == {
        "deleted": True,
        "textMessageTemplateId": 35,
    }
    assert (await adapter.add_note(CreateNoteRequest(person_id=1)))["id"] == 8
    assert (await adapter.get_note(GetNoteToolInput(note_id=9)))["id"] == 9
    assert (await adapter.update_note(UpdateNoteToolInput(note_id=10)))["id"] == 10
    assert (await adapter.delete_note(DeleteNoteToolInput(note_id=11))) == {
        "deleted": True,
        "noteId": 11,
    }
    assert (await adapter.list_webhooks(WebhookListRequest()))["webhooks"][0]["id"] == 9
    assert (await adapter.get_webhook(GetWebhookToolInput(webhook_id=11)))["id"] == 11
    assert (
        await adapter.get_webhook_event(
            GetWebhookEventToolInput(webhook_event_id="db36048a6b06d80e7f9d3440233ae915")
        )
    )["id"] == "db36048a6b06d80e7f9d3440233ae915"
    assert (
        await adapter.create_webhook(
            CreateWebhookRequest(event="peopleCreated", url="https://example.com")
        )
    )["id"] == 10
    assert (await adapter.update_webhook(UpdateWebhookToolInput(webhook_id=12, status="Disabled")))[
        "status"
    ] == "Disabled"
    assert (await adapter.delete_webhook(DeleteWebhookToolInput(webhook_id=12))) == {
        "deleted": True,
        "webhookId": 12,
    }

    async def boom() -> IdentityResponse:
        raise FollowUpBossRateLimitError(
            "slow down",
            status_code=429,
            retry_after_seconds=9.0,
        )

    failing = ServiceBundle(
        action_plans=services.action_plans,
        appointments=services.appointments,
        appointment_outcomes=services.appointment_outcomes,
        appointment_types=services.appointment_types,
        automation_people=services.automation_people,
        automations=services.automations,
        calls=services.calls,
        custom_fields=services.custom_fields,
        deal_attachments=services.deal_attachments,
        deals=services.deals,
        email_marketing=services.email_marketing,
        events=services.events,
        groups=services.groups,
        identity=_service_stub(get_identity=boom),
        inbox_apps=services.inbox_apps,
        notes=_service_stub(
            add_note=services.notes.add_note,
            get_note=services.notes.get_note,
            update_note=services.notes.update_note,
            delete_note=lambda note_id: (_ for _ in ()).throw(
                FollowUpBossValidationError("bad delete", status_code=400)
            ),
        ),
        people=_service_stub(
            search_people=lambda request: (_ for _ in ()).throw(
                FollowUpBossValidationError("bad people", status_code=400)
            ),
            get_person=services.people.get_person,
            create_person=services.people.create_person,
            update_person=services.people.update_person,
        ),
        person_attachments=services.person_attachments,
        people_relationships=services.people_relationships,
        ponds=services.ponds,
        pipelines=services.pipelines,
        reactions=services.reactions,
        smart_lists=services.smart_lists,
        stages=services.stages,
        tasks=services.tasks,
        team_inboxes=services.team_inboxes,
        teams=services.teams,
        threaded_replies=services.threaded_replies,
        timeframes=services.timeframes,
        text_message_templates=services.text_message_templates,
        text_messages=services.text_messages,
        templates=services.templates,
        users=_service_stub(
            list_users=services.users.list_users,
            get_user=services.users.get_user,
            get_me=lambda: (_ for _ in ()).throw(
                FollowUpBossValidationError("bad me", status_code=400)
            ),
        ),
        webhooks=services.webhooks,
    )
    adapter = FollowUpBossToolAdapter(failing)
    with pytest.raises(RuntimeError, match="Retry after 9 seconds"):
        await adapter.get_identity()
    with pytest.raises(RuntimeError, match="bad me"):
        await adapter.get_me()
    with pytest.raises(RuntimeError, match="bad people"):
        await adapter.search_people(PeopleSearchRequest(include_ponds=True))
    with pytest.raises(RuntimeError, match="bad delete"):
        await adapter.delete_note(DeleteNoteToolInput(note_id=1))


@pytest.mark.asyncio
async def test_communication_mutations_require_authenticated_attribution() -> None:
    """Call and outbound text logs should be bound to the authenticated user."""
    stub = StubBundle()
    adapter = FollowUpBossToolAdapter(stub.bundle)

    call = await adapter.create_call(
        CreateCallRequest(person_id=99, phone="555-2222", is_incoming=False)
    )
    text = await adapter.create_text_message(
        CreateTextMessageRequest(
            person_id=99,
            message="Logged externally",
            to_number="555-2222",
            from_number="1234567890",
            is_incoming=False,
        )
    )

    assert call["userId"] == 1
    assert stub.call_create_requests[-1].user_id == 1
    assert text["fromNumber"] == "(123) 456-7890"
    assert stub.text_message_create_requests[-1].from_number == "(123) 456-7890"


@pytest.mark.asyncio
async def test_communication_mutations_reject_mismatched_attribution() -> None:
    """The adapter should fail before logging under another user or sender."""
    stub = StubBundle()
    adapter = FollowUpBossToolAdapter(stub.bundle)

    with pytest.raises(RuntimeError, match="attributed to the authenticated"):
        await adapter.create_call(
            CreateCallRequest(person_id=99, phone="555-2222", is_incoming=False, user_id=999)
        )
    with pytest.raises(RuntimeError, match="authenticated Follow Up Boss user's sender phone"):
        await adapter.create_text_message(
            CreateTextMessageRequest(
                person_id=99,
                message="Logged externally",
                to_number="555-2222",
                from_number="555-0001",
                is_incoming=False,
            )
        )

    assert stub.call_create_requests == []
    assert stub.text_message_create_requests == []


@pytest.mark.asyncio
async def test_outbound_text_logs_fail_without_authenticated_user_phone() -> None:
    """Outbound text logs should not fall back to team/default sender numbers."""
    stub = StubBundle()

    async def users_get_me_without_phone() -> CurrentUserRecord:
        """Return a current user with no configured sender phone."""
        return CurrentUserRecord(id=1, name="Scott Willey")

    services = replace(
        stub.bundle,
        users=_service_stub(
            list_users=stub.bundle.users.list_users,
            get_user=stub.bundle.users.get_user,
            get_me=users_get_me_without_phone,
            delete_user=stub.bundle.users.delete_user,
        ),
    )
    adapter = FollowUpBossToolAdapter(services)

    with pytest.raises(RuntimeError, match="user phone is unavailable"):
        await adapter.create_text_message(
            CreateTextMessageRequest(
                person_id=99,
                message="Logged externally",
                to_number="555-2222",
                from_number="555-0001",
                is_incoming=False,
            )
        )

    assert stub.text_message_create_requests == []


@pytest.mark.asyncio
async def test_uncontacted_leads_reports_exact_total_after_local_filtering() -> None:
    """The no-communication helper should report the exact filtered total."""
    stub = StubBundle()
    requests: list[PeopleSearchRequest] = []

    async def search_people(request: PeopleSearchRequest) -> PageResult[PersonRecord]:
        """Return a final raw page whose first record satisfies the local filter."""
        requests.append(request)
        if len(requests) > 1:
            raise AssertionError("Only one final raw page is expected.")
        return PageResult(
            items=[
                PersonRecord.model_validate({"id": 11, "lastCommunication": None}),
                PersonRecord.model_validate(
                    {"id": 12, "lastCommunication": {"type": "Call", "created": "2024-01-01"}}
                ),
            ],
            metadata=PaginationMetadata(
                count=2,
                limit=100,
                next_token=None,
                next_link=None,
                offset=0,
                total=2,
            ),
        )

    adapter = FollowUpBossToolAdapter(
        replace(stub.bundle, people=_service_stub(search_people=search_people))
    )

    result = await adapter.list_uncontacted_leads(ListUncontactedLeadsToolInput(limit=1))

    assert [person["id"] for person in result["people"]] == [11]
    assert len(requests) == 1
    assert result["_metadata"]["total"] == 1
    assert result["_metadata"]["next_token"] is None


@pytest.mark.asyncio
async def test_uncontacted_leads_scans_raw_pages_before_reporting_zero_total() -> None:
    """The no-communication helper should scan raw pages before returning zero."""
    stub = StubBundle()
    requests: list[PeopleSearchRequest] = []

    async def search_people(request: PeopleSearchRequest) -> PageResult[PersonRecord]:
        """Return communicated people so the helper must advance by raw pages."""
        requests.append(request)
        offset = request.offset or 0
        people = [
            PersonRecord.model_validate(
                {
                    "id": offset + index + 1,
                    "lastCommunication": {"type": "Email", "created": "2024-01-01"},
                }
            )
            for index in range(100)
        ]
        return PageResult(
            items=people,
            metadata=PaginationMetadata(
                count=100,
                limit=100,
                next_token=None,
                next_link=None,
                offset=offset,
                total=5_000,
            ),
        )

    adapter = FollowUpBossToolAdapter(
        replace(stub.bundle, people=_service_stub(search_people=search_people))
    )

    result = await adapter.list_uncontacted_leads(ListUncontactedLeadsToolInput(limit=25))

    assert result["people"] == []
    assert len(requests) == 10
    assert [request.offset for request in requests] == [index * 100 for index in range(10)]
    assert result["_metadata"]["total"] is None
    assert cast("str", result["_metadata"]["next_token"]).startswith("scan:")


@pytest.mark.asyncio
async def test_search_people_requires_identity_id_for_default_scope() -> None:
    """People search should fail before querying when default scoping has no user id."""
    stub = StubBundle()

    async def identity_get_without_id() -> IdentityResponse:
        """Return an identity payload that cannot scope owned leads."""
        return IdentityResponse(name="Picard")

    services = replace(stub.bundle, identity=_service_stub(get_identity=identity_get_without_id))
    adapter = FollowUpBossToolAdapter(services)

    with pytest.raises(RuntimeError, match="Authenticated Follow Up Boss user id is unavailable"):
        await adapter.search_people(PeopleSearchRequest())
    with pytest.raises(RuntimeError, match="Authenticated Follow Up Boss user id is unavailable"):
        await adapter.search_people(PeopleSearchRequest(smart_list_id=74, source="Zillow"))
    with pytest.raises(ValidationError, match="People search IDs must be positive"):
        PeopleSearchRequest(smart_list_id=0)
    with pytest.raises(ValidationError, match="People search IDs must be positive"):
        PeopleSearchRequest(assigned_user_id=0)
    with pytest.raises(RuntimeError, match="Authenticated Follow Up Boss user id is unavailable"):
        await adapter.get_latest_lead(GetLatestLeadToolInput())
    with pytest.raises(RuntimeError, match="Authenticated Follow Up Boss user id is unavailable"):
        await adapter.list_my_overdue_tasks(ListMyTaskIntentToolInput())
    with pytest.raises(RuntimeError, match="Authenticated Follow Up Boss user id is unavailable"):
        await adapter.list_my_tasks_due_today(ListMyTaskIntentToolInput())
    with pytest.raises(RuntimeError, match="Authenticated Follow Up Boss user id is unavailable"):
        await adapter.list_my_upcoming_tasks(ListMyTaskIntentToolInput())
    with pytest.raises(RuntimeError, match="Authenticated Follow Up Boss user id is unavailable"):
        await adapter.search_people_in_smart_list(
            SearchPeopleInSmartListToolInput(smart_list_name="Active Buyers", mine=True)
        )

    assert stub.people_search_requests == []
    assert stub.task_list_requests == []


@pytest.mark.asyncio
async def test_latest_lead_returns_none_when_owned_scope_is_empty() -> None:
    """Latest-lead helper should return an explicit null person for empty owned results."""
    stub = StubBundle()

    async def empty_people_search(request: PeopleSearchRequest) -> PageResult[PersonRecord]:
        """Record the scoped request and return an empty people page."""
        stub.people_search_requests.append(request)
        return PageResult(
            items=[],
            metadata=PaginationMetadata(
                count=0,
                limit=1,
                next_token=None,
                next_link=None,
                offset=0,
                total=0,
            ),
        )

    services = replace(stub.bundle, people=_service_stub(search_people=empty_people_search))
    adapter = FollowUpBossToolAdapter(services)

    result = await adapter.get_latest_lead(GetLatestLeadToolInput())

    assert result["person"] is None
    assert stub.people_search_requests[-1].assigned_user_id == 1
    assert stub.people_search_requests[-1].limit == 1
    assert stub.people_search_requests[-1].sort == "-created"


@pytest.mark.asyncio
async def test_latest_lead_returns_safe_runtime_error_for_follow_up_boss_failures() -> None:
    """Latest-lead helper should surface Follow Up Boss failures as safe runtime errors."""
    stub = StubBundle()

    async def failing_people_search(_: PeopleSearchRequest) -> PageResult[PersonRecord]:
        """Raise a representative Follow Up Boss service failure."""
        raise FollowUpBossError("upstream exploded")

    services = replace(stub.bundle, people=_service_stub(search_people=failing_people_search))
    adapter = FollowUpBossToolAdapter(services)

    with pytest.raises(RuntimeError, match="upstream exploded"):
        await adapter.get_latest_lead(GetLatestLeadToolInput())


@pytest.mark.asyncio
async def test_smart_list_helper_returns_safe_runtime_error_for_follow_up_boss_failures() -> None:
    """Smart-list helper should surface Follow Up Boss failures as safe runtime errors."""
    stub = StubBundle()

    async def failing_people_search(_: PeopleSearchRequest) -> PageResult[PersonRecord]:
        """Raise a representative Follow Up Boss service failure."""
        raise FollowUpBossError("upstream exploded")

    services = replace(stub.bundle, people=_service_stub(search_people=failing_people_search))
    adapter = FollowUpBossToolAdapter(services)

    with pytest.raises(RuntimeError, match="upstream exploded"):
        await adapter.search_people_in_smart_list(
            SearchPeopleInSmartListToolInput(smart_list_name="Active Buyers")
        )


@pytest.mark.asyncio
async def test_person_activity_returns_safe_runtime_error_for_follow_up_boss_failures() -> None:
    """Person-activity helper should surface Follow Up Boss failures as safe runtime errors."""
    stub = StubBundle()

    async def failing_people_get(
        person_id: int,
        request: object | None = None,
    ) -> PersonRecord:
        """Raise a representative Follow Up Boss service failure."""
        del person_id, request
        raise FollowUpBossError("upstream exploded")

    services = replace(stub.bundle, people=_service_stub(get_person=failing_people_get))
    adapter = FollowUpBossToolAdapter(services)

    with pytest.raises(RuntimeError, match="upstream exploded"):
        await adapter.list_person_activity(ListPersonActivityToolInput(person_id=42))


class QueueClient:
    """Queue-backed client for FastMCP server tests."""

    def __init__(self, responses: list[dict[str, object] | list[object]]) -> None:
        self.responses = responses

    async def aclose(self) -> None:
        return None

    async def request_json(
        self,
        method: str,
        path: str,
        *,
        headers: Mapping[str, str] | None = None,
        json_body: Mapping[str, object] | None = None,
        params: Mapping[str, str] | None = None,
    ) -> dict[str, object] | list[object]:
        del method, path, headers, json_body, params
        return self.responses.pop(0)


@pytest.mark.asyncio
async def test_create_server_registers_tools_resource_and_prompt() -> None:
    """The FastMCP server should register the complete tool/resource/prompt surface."""
    server = create_server(
        FollowUpBossSettings.model_validate({"api_key": "key"}),
        client=QueueClient(
            [
                {"id": 1},
                {
                    "id": 1,
                    "name": "Gerald Leenerts",
                    "role": "admin",
                    "email": "gerald@followupboss.com",
                    "phone": "(123) 456-7890",
                    "timeZone": "America/Chicago",
                    "signature": "<div>Cheers,<br></div><div>-Gerald</div>",
                    "rawSignature": "<div>Cheers,<br></div><div>-Gerald</div>",
                    "apiKey": "secret-api-key",
                    "algoliaKey": "secret-algolia-key",
                    "intercomSettings": {
                        "app_id": "abc123",
                        "created_at": "1313236940",
                        "user_hash": "secret-hash",
                        "user_id": "1234-1",
                    },
                    "account": 1234,
                    "teamMember": None,
                    "beta": True,
                    "betaOnly": False,
                    "connectedEmail": {
                        "email": "gerald@followupboss.com",
                        "oauthProvider": "google",
                        "shareEmails": False,
                        "imapLeadProcessing": True,
                        "hasSmtp": True,
                    },
                    "leadEmailAddress": "gerald@followupboss.me",
                    "callingEnabled": True,
                    "voicemailEnabled": False,
                    "voicemailUrl": None,
                    "callingCapabilityToken": "secret-calling-token",
                    "isOwner": True,
                    "unreadConversationCount": 0,
                    "notifyBy": ["email", "sms"],
                    "features": ["calling", "link-tracking"],
                },
                {"_metadata": {"limit": 10, "offset": 0, "total": 1}, "people": [{"id": 2}]},
                {"id": 1},
                {"_metadata": {"limit": 1, "offset": 0, "total": 1}, "people": [{"id": 2}]},
                {"id": 3},
                {"id": 4},
                {"id": 5},
                {
                    "found": True,
                    "matchedBy": "email",
                    "assignedTo": "Agent Smith",
                },
                {
                    "_metadata": {"limit": 10, "offset": 0, "total": 1},
                    "people": [
                        {
                            "id": 6,
                            "firstName": "Unclaimed",
                            "sourceId": 730,
                            "claimed": False,
                            "delayed": False,
                        }
                    ],
                },
                {
                    "id": 7,
                    "firstName": "Claimed",
                    "assignedTo": "Agent Smith",
                    "claimed": False,
                },
                {},
                {},
                {
                    "personId": 1,
                    "fileName": "test.jpg",
                    "fileSize": None,
                    "id": 2,
                    "mimeType": "link",
                    "uri": "https://test.com/myfile",
                    "thumbnailUri": None,
                    "status": "created",
                    "createdAt": "2022-11-16T03:44:52Z",
                    "createdById": 1,
                    "createdByName": "Olivia Admin",
                    "is_external": 1,
                    "system_id": 123,
                },
                {
                    "personId": 1,
                    "fileName": "test.jpg",
                    "fileSize": None,
                    "id": 3,
                    "mimeType": "link",
                    "uri": "https://test.com/myfile",
                    "thumbnailUri": None,
                    "status": "created",
                    "createdAt": "2022-11-16T03:44:52Z",
                    "createdById": 1,
                    "createdByName": "Olivia Admin",
                },
                {
                    "personId": 1,
                    "fileName": "updated.jpg",
                    "fileSize": 42,
                    "id": 4,
                    "mimeType": "link",
                    "uri": "https://test.com/updated",
                    "thumbnailUri": None,
                    "status": "created",
                    "createdAt": "2022-11-16T03:44:52Z",
                    "createdById": 1,
                    "createdByName": "Olivia Admin",
                },
                {},
                [
                    {
                        "id": 423,
                        "personId": 46977,
                        "name": "Billy Bob",
                        "firstName": "Billy",
                        "lastName": "Bob",
                        "type": "Husband",
                        "isPriority": True,
                    }
                ],
                {
                    "id": 423,
                    "personId": 46977,
                    "name": "Billy Bob",
                    "firstName": "Billy",
                    "lastName": "Bob",
                    "type": "Husband",
                    "isPriority": True,
                },
                {},
                {},
                {},
                {
                    "id": 1363,
                    "created": "2024-03-21T21:14:13Z",
                    "createdBy": "Tom Minch",
                    "createdById": 1,
                    "refType": "Note",
                    "refId": 2144705,
                    "body": "🤯",
                },
                [],
                {},
                {
                    "id": 1,
                    "created": "2024-01-11T18:50:12Z",
                    "updated": "2024-01-26T19:13:27Z",
                    "createdById": 1,
                    "refType": "Note",
                    "refId": 468,
                    "body": "Hello world part 2",
                    "reactions": {
                        "id": 1363,
                        "created": "2024-03-21T21:14:13Z",
                        "createdBy": "Tom Minch",
                        "createdById": 1,
                        "refType": "Note",
                        "refId": 2144705,
                        "body": "🤯",
                    },
                },
                {"_metadata": {"limit": 10, "offset": 0, "total": 1}, "events": [{"id": 6}]},
                {"id": 7},
                {"id": 8},
                {"_metadata": {"limit": 10, "offset": 0, "total": 1}, "users": [{"id": 9}]},
                {"id": 10},
                {},
                {
                    "_metadata": {"limit": 10, "offset": 0, "total": 1},
                    "actionPlans": [{"id": 11, "name": "Qualify buyer leads"}],
                },
                {
                    "_metadata": {"limit": 10, "offset": 0, "total": 1},
                    "actionPlansPeople": [{"id": 12, "personId": 10810, "actionPlanId": 11}],
                },
                {},
                {"id": 13, "personId": 10810, "actionPlanId": 11, "status": "Paused"},
                {
                    "_metadata": {"limit": 10, "offset": 0, "total": 1},
                    "automations": [{"id": 87, "name": "Test Automation"}],
                },
                {"id": 88, "name": "Test Automation", "status": "Active"},
                {
                    "_metadata": {"limit": 10, "offset": 0, "total": 1},
                    "automationsPeople": [{"id": 89, "automationId": 87, "personId": 2}],
                },
                {
                    "id": 90,
                    "automationId": 87,
                    "personId": 2,
                    "status": "Completed",
                    "automationName": "Test Automation",
                },
                {
                    "id": 91,
                    "automationId": 87,
                    "personId": 3,
                    "status": "Running",
                    "automationName": "Test Automation",
                },
                {
                    "id": 92,
                    "automationId": 87,
                    "personId": 3,
                    "status": "Paused",
                    "automationName": "Test Automation",
                },
                {
                    "_metadata": {"limit": 10, "offset": 0, "total": 1},
                    "appointmentoutcomes": [{"id": 90, "name": "Completed"}],
                },
                {"id": 91, "name": "Completed", "orderWeight": 1000},
                {"id": 92, "name": "No Show", "orderWeight": 2000},
                {"id": 93, "name": "Rescheduled", "orderWeight": 3000},
                {},
                {
                    "_metadata": {"limit": 10, "offset": 0, "total": 1},
                    "appointmenttypes": [{"id": 94, "name": "Buyer Consult"}],
                },
                {"id": 95, "name": "Buyer Consult", "orderWeight": 1000},
                {"id": 96, "name": "Listing Consult", "orderWeight": 2000},
                {"id": 97, "name": "Showing", "orderWeight": 3000},
                {},
                {"_metadata": {"limit": 10, "offset": 0, "total": 1}, "groups": [{"id": 99}]},
                {"_metadata": {"limit": 10, "offset": 0, "total": 1}, "groups": [{"id": 100}]},
                {"id": 101, "name": "Eastside", "type": "Agent"},
                {"id": 102, "name": "Westside", "type": "Agent"},
                {"id": 103, "name": "Westside Plus", "type": "Agent"},
                {},
                {
                    "inboxApps": [
                        {"inboxAppId": 130, "userId": 0, "created": "2025-01-01T12:12:12Z"}
                    ]
                },
                {
                    "id": 131,
                    "created": "2024-01-01T12:00:00Z",
                    "updated": "2024-01-01T12:00:00Z",
                    "createdById": 1,
                    "updatedById": 1,
                    "status": 10,
                    "name": "Example Inbox App",
                    "publishedInboxAppId": 9,
                    "userId": 0,
                    "canReply": True,
                },
                {},
                [
                    {
                        "id": 132,
                        "status": "active",
                        "name": "John Doe",
                        "phone": "+14075550123",
                        "email": "john@example.com",
                        "isAutomation": False,
                    }
                ],
                {
                    "id": 133,
                    "status": "active",
                    "name": "John Doe",
                    "phone": "+14075550123",
                    "email": "john@example.com",
                    "isAutomation": False,
                },
                {},
                {
                    "id": 134,
                    "created": "2024-01-01T12:00:00Z",
                    "updated": "2024-01-01T12:00:00Z",
                    "sentAt": "2024-01-01T12:00:00Z",
                    "deliveryStatus": None,
                    "deliveryStatusErrorMessage": None,
                    "createdById": 1,
                    "updatedById": 1,
                    "isIncoming": True,
                    "message": "An example message.",
                    "userId": 0,
                    "personId": 1,
                    "sender": {
                        "personId": 1,
                        "name": "John Doe",
                        "email": None,
                        "phone": None,
                        "avatar": None,
                    },
                    "attachments": [
                        {
                            "filename": "example-2.jpg",
                            "url": "https://followupboss.test/example-2.jpg",
                        }
                    ],
                    "conversationDeepLinkUrl": "https://app.followupboss.com/2/inbox-new/0/inbox/1",
                },
                {
                    "id": 135,
                    "created": "2024-01-01T12:00:00Z",
                    "updated": "2024-01-01T12:00:00Z",
                    "createdById": 1,
                    "updatedById": 1,
                    "createdBy": "John Doe",
                    "updatedBy": "John Doe",
                    "conversationId": 1,
                    "body": "An example note.",
                    "isHtml": False,
                    "type": "ConversationNote",
                    "conversationDeepLinkUrl": "https://app.followupboss.com/2/inbox-new/0/inbox/1",
                },
                {
                    "externalConversationId": "conv-123",
                    "created": "2024-01-01T12:00:00Z",
                    "updated": "2024-01-01T12:00:00Z",
                    "createdById": "John Doe",
                    "updatedById": "John Doe",
                    "ownerUserId": 1,
                    "ownerSharedInboxId": 0,
                    "assignedUserId": 0,
                    "assignedSharedInboxId": 1,
                    "subject": "A Conversation Subject",
                    "archived": False,
                    "person": {"id": 1, "name": None, "email": None, "phone": None},
                    "conversationDeepLinkUrl": "https://app.followupboss.com/2/inbox-new/0/inbox/1",
                },
                {
                    "id": 136,
                    "created": "2024-01-01T12:00:00Z",
                    "updated": "2024-01-01T12:00:00Z",
                    "sentAt": "2024-01-01T12:00:00Z",
                    "deliveryStatus": "Delivered",
                    "deliveryStatusErrorMessage": None,
                    "createdById": 1,
                    "updatedById": 1,
                    "isIncoming": True,
                    "message": "An example message.",
                    "userId": 0,
                    "personId": 1,
                    "sender": {
                        "personId": 1,
                        "name": "John Doe",
                        "email": None,
                        "phone": None,
                        "avatar": None,
                    },
                    "conversationDeepLinkUrl": "https://app.followupboss.com/2/inbox-new/0/inbox/1",
                },
                {
                    "_metadata": {"limit": 10, "offset": 0, "total": 1},
                    "customfields": [
                        {"id": 11, "label": "Birthday", "name": "customBirthday", "type": "date"}
                    ],
                },
                {"id": 12, "label": "Close price", "name": "customClosePrice", "type": "number"},
                {
                    "id": 13,
                    "label": "Looking for",
                    "name": "customLookingFor",
                    "type": "dropdown",
                    "choices": ["Apartment", "Townhouse"],
                },
                {
                    "id": 14,
                    "label": "Looking for",
                    "name": "customLookingFor",
                    "type": "dropdown",
                },
                {},
                {
                    "_metadata": {"limit": 10, "offset": 0, "total": 1},
                    "emCampaigns": [
                        {
                            "id": 201,
                            "origin": "Curaytor",
                            "originId": "912",
                            "name": "Can I help",
                            "subject": "Can I help?",
                            "bodyHtml": "I saw you're browsing our website, can I help with...",
                        }
                    ],
                },
                {
                    "id": 202,
                    "origin": "Curaytor",
                    "originId": "913",
                    "name": "New Campaign",
                    "subject": "Hello",
                    "bodyHtml": "<p>Hello</p>",
                },
                {
                    "id": 203,
                    "origin": "Curaytor",
                    "originId": "913",
                    "name": "Updated Campaign",
                    "subject": "Updated",
                    "bodyHtml": "<p>Updated</p>",
                },
                {
                    "_metadata": {"limit": 10, "offset": 0, "total": 1},
                    "emEvents": [
                        {
                            "count": 2,
                            "type": "open",
                            "personId": 10911,
                            "campaignId": 102,
                            "campaignName": "Can I help",
                            "created": "2017-01-03T19:20:49Z",
                            "updated": "2017-01-03T19:20:49Z",
                        }
                    ],
                },
                {
                    "emEventIds": [193928, 193929],
                    "recipientsNotFound": [
                        "email.not.in.fub@example.com",
                        "another.missing.email@example.com",
                    ],
                },
                {"_metadata": {"limit": 10, "offset": 0, "total": 1}, "deals": [{"id": 40}]},
                {"_metadata": {"limit": 10, "offset": 0, "total": 1}, "deals": [{"id": 40}]},
                {"id": 41, "name": "Buyer contract"},
                {"id": 42, "name": "New deal"},
                {"id": 43, "name": "Updated deal"},
                {},
                {
                    "dealId": 8,
                    "fileName": "deal.jpg",
                    "fileSize": None,
                    "id": 10,
                    "mimeType": "link",
                    "uri": "https://test.com/deal",
                    "thumbnailUri": None,
                    "status": "created",
                    "createdAt": "2022-11-16T19:09:45Z",
                    "createdById": 1,
                    "createdByName": "Olivia Admin",
                },
                {
                    "dealId": 8,
                    "fileName": "deal.jpg",
                    "fileSize": None,
                    "id": 11,
                    "mimeType": "link",
                    "uri": "https://test.com/deal",
                    "thumbnailUri": None,
                    "status": "created",
                    "createdAt": "2022-11-16T19:09:45Z",
                    "createdById": 1,
                    "createdByName": "Olivia Admin",
                },
                {
                    "dealId": 9,
                    "fileName": "deal-updated.jpg",
                    "fileSize": 24,
                    "id": 12,
                    "mimeType": "link",
                    "uri": "https://test.com/deal-updated",
                    "thumbnailUri": None,
                    "status": "created",
                    "createdAt": "2022-11-16T19:09:45Z",
                    "createdById": 1,
                    "createdByName": "Olivia Admin",
                },
                {},
                {
                    "_metadata": {"limit": 10, "offset": 0, "total": 1},
                    "dealCustomfields": [
                        {
                            "id": 44,
                            "label": "Close Price",
                            "name": "customClosePrice",
                            "type": "number",
                        }
                    ],
                },
                {
                    "id": 45,
                    "label": "Priority",
                    "name": "customPriority",
                    "type": "dropdown",
                    "choices": ["High", "Medium", "Low"],
                },
                {
                    "id": 46,
                    "label": "Priority",
                    "name": "customPriority",
                    "type": "dropdown",
                    "choices": ["High", "Medium", "Low"],
                },
                {
                    "id": 47,
                    "label": "Priority",
                    "name": "customPriority",
                    "type": "dropdown",
                    "choices": ["Critical", "High", "Medium"],
                    "readOnly": True,
                },
                {},
                {"_metadata": {"limit": 10, "offset": 0, "total": 1}, "pipelines": [{"id": 60}]},
                {"id": 61, "name": "Buyer pipeline", "description": "Buyer flow"},
                {"id": 62, "name": "New pipeline", "description": "New flow"},
                {"id": 63, "name": "Updated pipeline", "description": "Updated flow"},
                {},
                {"_metadata": {"limit": 10, "offset": 0, "total": 1}, "ponds": [{"id": 65}]},
                {"id": 66, "name": "Round Robin", "userId": 9, "userIds": [9, 10]},
                {"id": 67, "name": "Sphere Builders", "userId": 8, "userIds": [8, 9]},
                {"id": 68, "name": "Updated Pond", "userId": 9, "userIds": [9, 10]},
                {},
                {
                    "_metadata": {"limit": 10, "offset": 0, "total": 1},
                    "smartlists": [{"id": 76, "name": "Active Buyers"}],
                },
                {"id": 77, "name": "Active Buyers", "isFub2": True},
                {
                    "_metadata": {"limit": 10, "offset": 0, "total": 1},
                    "smartlists": [{"id": 76, "name": "Active Buyers"}],
                },
                {
                    "_metadata": {"limit": 1, "offset": 0, "total": 1},
                    "people": [{"id": 2, "firstName": "Will"}],
                },
                {"_metadata": {"limit": 10, "offset": 0, "total": 1}, "stages": [{"id": 78}]},
                {"id": 79, "name": "Prospect", "orderWeight": 1000, "isProtected": False},
                {"id": 80, "name": "Qualified", "orderWeight": 2000, "isProtected": False},
                {"id": 81, "name": "Updated Stage", "orderWeight": 3000, "isProtected": False},
                {},
                {"_metadata": {"limit": 10, "offset": 0, "total": 1}, "teams": [{"id": 83}]},
                {"id": 84, "name": "Listing Team", "userIds": [5, 6], "leaderIds": [5]},
                {"id": 85, "name": "Buyer Team", "userIds": [7, 8], "leaderIds": [7]},
                {"id": 86, "name": "Updated Team", "userIds": [9, 10], "leaderIds": [9]},
                {},
                {"_metadata": {"limit": 10, "offset": 0, "total": 1}, "calls": [{"id": 12}]},
                {"id": 13, "personId": 2, "phone": "555-0000", "userName": "Data"},
                {"id": 1},
                {"id": 14, "personId": 2, "phone": "555-0000", "userName": "Data"},
                {"id": 15, "personId": 2, "phone": "555-0000", "userName": "Data"},
                {"_metadata": {"limit": 10, "offset": 0, "total": 1}, "tasks": [{"id": 16}]},
                {"id": 1},
                {"_metadata": {"limit": 10, "offset": 0, "total": 1}, "tasks": [{"id": 16}]},
                {"id": 1},
                {"_metadata": {"limit": 10, "offset": 0, "total": 1}, "tasks": [{"id": 16}]},
                {"id": 1},
                {"_metadata": {"limit": 10, "offset": 0, "total": 1}, "tasks": [{"id": 16}]},
                {"id": 17, "personId": 2, "assignedTo": "Data", "type": "Call"},
                {"id": 18, "personId": 2, "assignedTo": "Data", "type": "Email"},
                {"id": 19, "personId": 2, "assignedTo": "Data", "type": "Text"},
                {},
                {
                    "_metadata": {"limit": 10, "offset": 0, "total": 1},
                    "templates": [{"id": 20, "name": "Buyer intro", "subject": "Hello"}],
                },
                {"id": 21, "name": "Buyer intro", "subject": "Hello"},
                {
                    "id": 57,
                    "name": "I am here to help",
                    "subject": "Your property inquiry from Zillow",
                    "body": "Hi Bob, I am here to help, ...",
                    "isShared": True,
                    "isEditable": True,
                    "isDeletable": True,
                },
                {"id": 22, "name": "New template", "subject": "Hello", "body": "<p>Hello</p>"},
                {
                    "id": 23,
                    "name": "Updated template",
                    "subject": "Updated",
                    "body": "<p>Updated</p>",
                },
                {},
                {"_metadata": {"limit": 10, "offset": 0, "total": 1}, "textmessages": [{"id": 50}]},
                {"id": 51, "message": "Hi there"},
                {
                    "id": 1,
                    "name": "Gerald Leenerts",
                    "email": "gerald@followupboss.com",
                    "phone": "(123) 456-7890",
                },
                {
                    "id": 58,
                    "personId": 2,
                    "message": "Logged externally",
                    "fromNumber": "(123) 456-7890",
                    "toNumber": "555-0002",
                    "userName": "Data",
                    "isIncoming": False,
                    "externalLabel": "External SMS",
                    "externalUrl": "https://example.com/sms/3",
                },
                {
                    "_metadata": {"limit": 10, "offset": 0, "total": 1},
                    "textmessagetemplates": [{"id": 52, "name": "Buyer intro text"}],
                },
                {"id": 53, "name": "Buyer intro text", "message": "Hi there"},
                {"mergedTemplate": "Hey Bob, Alice and Carol..."},
                {"id": 54, "name": "New text template", "message": "Hello there"},
                {"id": 55, "name": "Updated text template", "message": "Updated text"},
                {},
                {"_metadata": {"limit": 10, "offset": 0, "total": 1}, "teamInboxes": [{"id": 120}]},
                {"id": 24, "body": "created"},
                {"id": 25, "body": "loaded"},
                {"id": 26, "body": "updated"},
                {},
                {
                    "_metadata": {"limit": 10, "offset": 0, "total": 1},
                    "webhooks": [
                        {"id": 27, "event": "peopleCreated", "url": "https://example.com"}
                    ],
                },
                {"id": 28, "event": "peopleCreated", "url": "https://example.com"},
                {
                    "id": "db36048a6b06d80e7f9d3440233ae915",
                    "eventId": "4b762cb3-d7b6-4cf4-b7fb-fbd8cb0dfe11",
                    "eventCreated": "2016-12-12T18:36:26Z",
                    "event": "peopleUpdated",
                    "resourceIds": [99],
                    "uri": "https://api.followupboss.com/v1/people/99",
                    "data": {"changed": ["tags"]},
                },
                {"id": 29, "event": "peopleCreated", "url": "https://example.com"},
                {
                    "id": 29,
                    "event": "peopleUpdated",
                    "status": "Disabled",
                    "url": "https://example.com",
                },
                {},
                {
                    "_metadata": {"limit": 10, "offset": 0, "total": 1},
                    "appointments": [{"id": 30, "title": "Buyer consult"}],
                },
                {"id": 31, "title": "Buyer consult"},
                {"id": 32, "title": "Listing appointment"},
                {"id": 33, "title": "Updated appointment"},
                {},
                {
                    "_metadata": {"collection": "timeframes", "offset": 0, "limit": 10, "total": 5},
                    "timeframes": [
                        {"id": 1, "timeframe": "0-3 Months"},
                        {"id": 2, "timeframe": "3-6 Months"},
                    ],
                },
            ]
        ),
    )
    listed_tools = await server.list_tools()
    tool_names = sorted(tool.name for tool in listed_tools)
    tools = {tool.name: tool for tool in listed_tools}
    search_people_properties = tools["followupboss_search_people"].inputSchema.get("properties", {})
    assert isinstance(search_people_properties, dict)
    assert "smart_list_id" in search_people_properties
    search_people_description = cast("str", tools["followupboss_search_people"].description)
    assert "Do not use this broad search for 'my latest lead'" in search_people_description
    assert "use followupboss_get_latest_lead" in search_people_description
    assert "use followupboss_list_uncontacted_leads" in search_people_description
    assert "including after a smart-list-scoped result is empty" in search_people_description
    uncontacted_description = cast(
        "str",
        tools["followupboss_list_uncontacted_leads"].description,
    )
    assert "no recorded lastCommunication" in uncontacted_description
    assert "never smart-list lookup" in uncontacted_description
    assert "contacted=false only when the user explicitly asks" in uncontacted_description
    assert "assigned_user_name/owner_name/agent_name" in uncontacted_description
    assert "Do not use this as a fallback after an Eligible For Transfer" in (
        uncontacted_description
    )
    search_events_description = cast("str", tools["followupboss_search_events"].description)
    assert "Do not use this to answer requests for notes associated with a person" in (
        search_events_description
    )
    assert "support@followupboss.com" in search_events_description
    get_note_description = cast("str", tools["followupboss_get_note"].description)
    assert "by note ID only" in get_note_description
    assert "FUB person ID" in get_note_description
    latest_lead_description = cast("str", tools["followupboss_get_latest_lead"].description)
    assert "Resolves the authenticated user internally" in latest_lead_description
    list_tasks_description = cast("str", tools["followupboss_list_tasks"].description)
    assert "Use this broad list only when the request provides explicit task filters" in (
        list_tasks_description
    )
    helper_description = cast(
        "str",
        tools["followupboss_search_people_in_smart_list"].description,
    )
    assert "named Follow Up Boss smart list" in helper_description
    assert "Do not use this for uncontacted" in helper_description
    assert "assigned_user_name" in helper_description
    assert "provenance" in helper_description
    assert "do not run a broad Zillow or uncontacted-leads fallback" in helper_description
    smart_lists_description = cast("str", tools["followupboss_list_smart_lists"].description)
    assert "use followupboss_list_uncontacted_leads" in smart_lists_description
    assert "unless the user explicitly asks to list saved lists" in smart_lists_description
    person_activity_description = cast(
        "str",
        tools["followupboss_list_person_activity"].description,
    )
    assert "one explicit Follow Up Boss person_id" in person_activity_description
    assert "applies person_id to calls" in person_activity_description
    create_call_description = cast("str", tools["followupboss_create_call"].description)
    assert "attributed to the authenticated user" in create_call_description
    assert "rejects mismatched user IDs" in create_call_description
    create_text_description = cast("str", tools["followupboss_create_text_message"].description)
    assert "exactly one resolved prior lead/contact/person" in create_text_description
    assert "sticky recipient context" in create_text_description
    assert "Do not ask who to log the text with" in create_text_description
    assert "sender/from_number" in create_text_description
    assert "authenticated user's own Follow Up Boss phone" in create_text_description
    assert "never a team, group, account" in create_text_description
    assert "rejects mismatched sender numbers" in create_text_description
    assert "followupboss_list_my_overdue_tasks" in list_tasks_description
    assert "followupboss_list_my_tasks_due_today" in list_tasks_description
    assert "followupboss_list_my_upcoming_tasks" in list_tasks_description
    overdue_tasks_description = cast("str", tools["followupboss_list_my_overdue_tasks"].description)
    assert "forces incomplete overdue task scope" in overdue_tasks_description
    today_tasks_description = cast("str", tools["followupboss_list_my_tasks_due_today"].description)
    assert "forces incomplete due-today task scope" in today_tasks_description
    upcoming_tasks_description = cast(
        "str", tools["followupboss_list_my_upcoming_tasks"].description
    )
    assert "forces incomplete future task scope" in upcoming_tasks_description
    assert "explicit person_id" in cast("str", tools["followupboss_update_person"].description)
    assert "explicit person_id" in cast("str", tools["followupboss_delete_person"].description)
    assert "explicit task_id" in cast("str", tools["followupboss_update_task"].description)
    assert "explicit task_id" in cast("str", tools["followupboss_delete_task"].description)
    assert tool_names == [
        "followupboss_add_inbox_app_message",
        "followupboss_add_inbox_app_note",
        "followupboss_add_inbox_app_participant",
        "followupboss_add_note",
        "followupboss_add_reaction",
        "followupboss_apply_action_plan",
        "followupboss_check_duplicate_person",
        "followupboss_claim_person",
        "followupboss_create_appointment",
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
        "followupboss_create_task",
        "followupboss_create_team",
        "followupboss_create_template",
        "followupboss_create_text_message",
        "followupboss_create_text_message_template",
        "followupboss_create_webhook",
        "followupboss_deactivate_inbox_app",
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
        "followupboss_ignore_unclaimed_person",
        "followupboss_install_inbox_app",
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
        "followupboss_remove_inbox_app_participant",
        "followupboss_search_events",
        "followupboss_search_people",
        "followupboss_search_people_in_smart_list",
        "followupboss_send_email_events",
        "followupboss_send_event",
        "followupboss_trigger_automation",
        "followupboss_update_action_plan_person",
        "followupboss_update_appointment",
        "followupboss_update_appointment_outcome",
        "followupboss_update_appointment_type",
        "followupboss_update_automation_person",
        "followupboss_update_call",
        "followupboss_update_custom_field",
        "followupboss_update_deal",
        "followupboss_update_deal_attachment",
        "followupboss_update_deal_custom_field",
        "followupboss_update_email_campaign",
        "followupboss_update_group",
        "followupboss_update_inbox_app_conversation",
        "followupboss_update_inbox_app_message",
        "followupboss_update_note",
        "followupboss_update_people_relationship",
        "followupboss_update_person",
        "followupboss_update_person_attachment",
        "followupboss_update_pipeline",
        "followupboss_update_pond",
        "followupboss_update_stage",
        "followupboss_update_task",
        "followupboss_update_team",
        "followupboss_update_template",
        "followupboss_update_text_message_template",
        "followupboss_update_webhook",
    ]

    assert await _call_public_tool(
        server,
        tools,
        "followupboss_get_identity",
    ) == {"id": 1}
    assert (
        await _call_public_tool(
            server,
            tools,
            "followupboss_get_me",
        )
    )["apiKey"] == "***redacted***"
    assert (
        await _call_public_tool(
            server,
            tools,
            "followupboss_search_people",
            email="a@example.com",
            include_ponds=True,
            smart_list_id=74,
        )
    )["people"][0]["id"] == 2
    assert (
        await _call_public_tool(
            server,
            tools,
            "followupboss_get_latest_lead",
        )
    )["person"]["id"] == 2
    assert await _call_public_tool(server, tools, "followupboss_get_person", 3) == {"id": 3}
    assert (await _call_public_tool(server, tools, "followupboss_create_person", first_name="Tom"))[
        "id"
    ] == 4
    assert (
        await _call_public_tool(server, tools, "followupboss_update_person", 5, first_name="Will")
    )["id"] == 5
    assert await _call_public_tool(
        server, tools, "followupboss_check_duplicate_person", email="agent@example.com"
    ) == {
        "found": True,
        "matchedBy": "email",
        "assignedTo": "Agent Smith",
    }
    assert (
        await _call_public_tool(
            server,
            tools,
            "followupboss_list_unclaimed_people",
        )
    )["people"][0]["id"] == 6
    assert (await _call_public_tool(server, tools, "followupboss_claim_person", 7))["id"] == 7
    assert await _call_public_tool(server, tools, "followupboss_ignore_unclaimed_person", 7) == {
        "deleted": True,
        "personId": 7,
    }
    assert await _call_public_tool(server, tools, "followupboss_delete_person", 8) == {
        "deleted": True,
        "personId": 8,
    }
    assert (await _call_public_tool(server, tools, "followupboss_get_person_attachment", 2))[
        "id"
    ] == 2
    assert (
        await _call_public_tool(
            server,
            tools,
            "followupboss_create_person_attachment",
            1,
            "https://test.com/myfile",
            "test.jpg",
        )
    )["id"] == 3
    assert (
        await _call_public_tool(
            server,
            tools,
            "followupboss_update_person_attachment",
            4,
            1,
            "https://test.com/updated",
            "updated.jpg",
        )
    )["id"] == 4
    assert await _call_public_tool(server, tools, "followupboss_delete_person_attachment", 5) == {
        "deleted": True,
        "personAttachmentId": 5,
    }
    assert (
        await _call_public_tool(
            server, tools, "followupboss_list_people_relationships", person_id=46977
        )
    )["peopleRelationships"][0]["id"] == 423
    assert (await _call_public_tool(server, tools, "followupboss_get_people_relationship", 423))[
        "id"
    ] == 423
    assert (
        await _call_public_tool(server, tools, "followupboss_create_people_relationship", 46977)
        == {}
    )
    assert (
        await _call_public_tool(
            server, tools, "followupboss_update_people_relationship", 423, type="Spouse"
        )
        == {}
    )
    assert await _call_public_tool(
        server, tools, "followupboss_delete_people_relationship", 423
    ) == {
        "deleted": True,
        "peopleRelationshipId": 423,
    }
    assert (await _call_public_tool(server, tools, "followupboss_get_reaction", 1363))["id"] == 1363
    assert (
        await _call_public_tool(server, tools, "followupboss_add_reaction", "Note", 2144705, "🤣")
        == {}
    )
    assert await _call_public_tool(
        server, tools, "followupboss_delete_reaction", "Note", 2144705, emoji="👏"
    ) == {
        "deleted": True,
        "refId": 2144705,
    }
    assert (await _call_public_tool(server, tools, "followupboss_get_threaded_reply", 1))["id"] == 1
    assert (await _call_public_tool(server, tools, "followupboss_search_events", person_id=1))[
        "events"
    ][0]["id"] == 6
    assert (await _call_public_tool(server, tools, "followupboss_get_event", 7))["id"] == 7
    assert (
        await _call_public_tool(
            server,
            tools,
            "followupboss_send_event",
            source="Portal",
            system="Portal",
            type="Inquiry",
            person={},
        )
    )["id"] == 8
    assert (
        await _call_public_tool(
            server,
            tools,
            "followupboss_list_users",
        )
    )["users"][0]["id"] == 9
    assert (await _call_public_tool(server, tools, "followupboss_get_user", 10))["id"] == 10
    assert await _call_public_tool(server, tools, "followupboss_delete_user", 10, 5) == {
        "deleted": True,
        "userId": 10,
    }
    assert (
        await _call_public_tool(
            server,
            tools,
            "followupboss_list_action_plans",
        )
    )["actionPlans"][0]["id"] == 11
    assert (
        await _call_public_tool(
            server,
            tools,
            "followupboss_list_action_plan_people",
        )
    )["actionPlansPeople"][0]["id"] == 12
    assert await _call_public_tool(server, tools, "followupboss_apply_action_plan", 11, 10810) == {}
    assert (
        await _call_public_tool(
            server, tools, "followupboss_update_action_plan_person", 13, status="Paused"
        )
    )["id"] == 13
    assert (
        await _call_public_tool(
            server,
            tools,
            "followupboss_list_automations",
        )
    )["automations"][0]["id"] == 87
    assert (await _call_public_tool(server, tools, "followupboss_get_automation", 88))["id"] == 88
    assert (
        await _call_public_tool(
            server,
            tools,
            "followupboss_list_automation_people",
        )
    )["automationsPeople"][0]["id"] == 89
    assert (await _call_public_tool(server, tools, "followupboss_get_automation_person", 90))[
        "id"
    ] == 90
    assert (await _call_public_tool(server, tools, "followupboss_trigger_automation", 87, 3))[
        "id"
    ] == 91
    assert (
        await _call_public_tool(
            server, tools, "followupboss_update_automation_person", 92, status="Paused"
        )
    )["id"] == 92
    assert (
        await _call_public_tool(
            server,
            tools,
            "followupboss_list_appointment_outcomes",
        )
    )["appointmentoutcomes"][0]["id"] == 90
    assert (await _call_public_tool(server, tools, "followupboss_get_appointment_outcome", 91))[
        "id"
    ] == 91
    assert (
        await _call_public_tool(
            server, tools, "followupboss_create_appointment_outcome", name="No Show"
        )
    )["id"] == 92
    assert (
        await _call_public_tool(
            server,
            tools,
            "followupboss_update_appointment_outcome",
            93,
            name="Rescheduled",
        )
    )["id"] == 93
    assert await _call_public_tool(
        server, tools, "followupboss_delete_appointment_outcome", 94, 91
    ) == {
        "deleted": True,
        "appointmentOutcomeId": 94,
    }
    assert (
        await _call_public_tool(
            server,
            tools,
            "followupboss_list_appointment_types",
        )
    )["appointmenttypes"][0]["id"] == 94
    assert (await _call_public_tool(server, tools, "followupboss_get_appointment_type", 95))[
        "id"
    ] == 95
    assert (
        await _call_public_tool(
            server, tools, "followupboss_create_appointment_type", name="Listing Consult"
        )
    )["id"] == 96
    assert (
        await _call_public_tool(
            server,
            tools,
            "followupboss_update_appointment_type",
            97,
            name="Showing",
        )
    )["id"] == 97
    assert await _call_public_tool(
        server, tools, "followupboss_delete_appointment_type", 98, 95
    ) == {
        "deleted": True,
        "appointmentTypeId": 98,
    }
    assert (await _call_public_tool(server, tools, "followupboss_list_groups", type="Agent"))[
        "groups"
    ][0]["id"] == 99
    assert (
        await _call_public_tool(server, tools, "followupboss_list_round_robin_groups", type="Agent")
    )["groups"][0]["id"] == 100
    assert (await _call_public_tool(server, tools, "followupboss_get_group", 101))["id"] == 101
    assert (
        await _call_public_tool(server, tools, "followupboss_create_group", "Westside", [200, 201])
    )["id"] == 102
    assert (
        await _call_public_tool(
            server, tools, "followupboss_update_group", 103, name="Westside Plus"
        )
    )["id"] == 103
    assert await _call_public_tool(server, tools, "followupboss_delete_group", 104) == {
        "deleted": True,
        "groupId": 104,
    }
    assert (await _call_public_tool(server, tools, "followupboss_list_inbox_app_installations", 9))[
        "inboxApps"
    ][0]["inboxAppId"] == 130
    assert (
        await _call_public_tool(
            server,
            tools,
            "followupboss_install_inbox_app",
            9,
            0,
            "https://example.com/webhook",
        )
    )["id"] == 131
    assert await _call_public_tool(server, tools, "followupboss_deactivate_inbox_app", 131) == {
        "deleted": True,
        "inboxAppId": 131,
    }
    assert (
        await _call_public_tool(
            server, tools, "followupboss_list_inbox_app_participants", 131, "conv-123"
        )
    )["participants"][0]["id"] == 132
    assert (
        await _call_public_tool(
            server,
            tools,
            "followupboss_add_inbox_app_participant",
            131,
            "conv-123",
            name="John Doe",
            email="john@example.com",
        )
    )["id"] == 133
    assert await _call_public_tool(
        server, tools, "followupboss_remove_inbox_app_participant", 131, "conv-123", 133
    ) == {
        "deleted": True,
        "participantId": 133,
    }
    assert (
        await _call_public_tool(
            server,
            tools,
            "followupboss_add_inbox_app_message",
            131,
            "conv-123",
            "msg-123",
            "An example message.",
            True,
            {"personId": 1},
        )
    )["id"] == 134
    assert (
        await _call_public_tool(
            server,
            tools,
            "followupboss_add_inbox_app_note",
            131,
            "conv-123",
            "An example note.",
            {"id": 1},
        )
    )["id"] == 135
    assert (
        await _call_public_tool(
            server,
            tools,
            "followupboss_update_inbox_app_conversation",
            131,
            "conv-123",
            subject="A Conversation Subject",
            archived=False,
        )
    )["externalConversationId"] == "conv-123"
    assert (
        await _call_public_tool(
            server,
            tools,
            "followupboss_update_inbox_app_message",
            131,
            id=134,
            external_message_id="msg-124",
            delivery_status="Delivered",
        )
    )["id"] == 136
    assert (
        await _call_public_tool(
            server,
            tools,
            "followupboss_list_custom_fields",
        )
    )["customfields"][0]["id"] == 11
    assert (await _call_public_tool(server, tools, "followupboss_get_custom_field", 12))["id"] == 12
    assert (
        await _call_public_tool(
            server,
            tools,
            "followupboss_create_custom_field",
            "Looking for",
            "dropdown",
            choices=["Apartment"],
        )
    )["id"] == 13
    assert (
        await _call_public_tool(
            server, tools, "followupboss_update_custom_field", 14, label="Looking for"
        )
    )["id"] == 14
    assert await _call_public_tool(server, tools, "followupboss_delete_custom_field", 15) == {
        "deleted": True,
        "customFieldId": 15,
    }
    assert (
        await _call_public_tool(
            server, tools, "followupboss_list_email_campaigns", origin="Curaytor"
        )
    )["emCampaigns"][0]["id"] == 201
    assert (
        await _call_public_tool(
            server,
            tools,
            "followupboss_create_email_campaign",
            "Curaytor",
            "913",
            name="New Campaign",
            subject="Hello",
            body_html="<p>Hello</p>",
        )
    )["id"] == 202
    assert (
        await _call_public_tool(
            server,
            tools,
            "followupboss_update_email_campaign",
            203,
            name="Updated Campaign",
            subject="Updated",
            body_html="<p>Updated</p>",
        )
    )["id"] == 203
    assert (await _call_public_tool(server, tools, "followupboss_list_email_events", type="open"))[
        "emEvents"
    ][0]["campaignId"] == 102
    assert (
        await _call_public_tool(
            server,
            tools,
            "followupboss_send_email_events",
            [
                {
                    "type": "delivered",
                    "occurred": "2026-03-28T13:00:00Z",
                    "recipient": "john.smith@gmail.com",
                    "campaign_id": 141,
                }
            ],
        )
    )["emEventIds"] == [193928, 193929]
    assert (
        await _call_public_tool(
            server,
            tools,
            "followupboss_list_deals",
        )
    )["deals"][0]["id"] == 40
    assert (
        await _call_public_tool(
            server,
            tools,
            "followupboss_list_active_deals_for_person",
            2,
        )
    )["deals"][0]["id"] == 40
    assert (await _call_public_tool(server, tools, "followupboss_get_deal", 41))["id"] == 41
    assert (
        await _call_public_tool(
            server, tools, "followupboss_create_deal", name="New deal", stage_id=7
        )
    )["id"] == 42
    assert (await _call_public_tool(server, tools, "followupboss_update_deal", 43, stage_id=8))[
        "id"
    ] == 43
    assert await _call_public_tool(server, tools, "followupboss_delete_deal", 44) == {
        "deleted": True,
        "dealId": 44,
    }
    assert (await _call_public_tool(server, tools, "followupboss_get_deal_attachment", 10))[
        "id"
    ] == 10
    assert (
        await _call_public_tool(
            server,
            tools,
            "followupboss_create_deal_attachment",
            8,
            "https://test.com/deal",
            "deal.jpg",
        )
    )["id"] == 11
    assert (
        await _call_public_tool(
            server,
            tools,
            "followupboss_update_deal_attachment",
            12,
            9,
            "https://test.com/deal-updated",
            "deal-updated.jpg",
        )
    )["id"] == 12
    assert await _call_public_tool(server, tools, "followupboss_delete_deal_attachment", 13) == {
        "deleted": True,
        "dealAttachmentId": 13,
    }
    assert (
        await _call_public_tool(
            server,
            tools,
            "followupboss_list_deal_custom_fields",
        )
    )["dealCustomfields"][0]["id"] == 44
    assert (await _call_public_tool(server, tools, "followupboss_get_deal_custom_field", 45))[
        "id"
    ] == 45
    assert (
        await _call_public_tool(
            server,
            tools,
            "followupboss_create_deal_custom_field",
            "Priority",
            "dropdown",
            choices=["High", "Medium", "Low"],
        )
    )["id"] == 46
    assert (
        await _call_public_tool(
            server,
            tools,
            "followupboss_update_deal_custom_field",
            47,
            label="Priority",
            choices=["Critical", "High", "Medium"],
            read_only=True,
        )
    )["id"] == 47
    assert await _call_public_tool(server, tools, "followupboss_delete_deal_custom_field", 47) == {
        "deleted": True,
        "dealCustomFieldId": 47,
    }
    assert (
        await _call_public_tool(
            server,
            tools,
            "followupboss_list_pipelines",
        )
    )["pipelines"][0]["id"] == 60
    assert (await _call_public_tool(server, tools, "followupboss_get_pipeline", 61))["id"] == 61
    assert (
        await _call_public_tool(server, tools, "followupboss_create_pipeline", name="New pipeline")
    )["id"] == 62
    assert (
        await _call_public_tool(
            server, tools, "followupboss_update_pipeline", 63, name="Updated pipeline"
        )
    )["id"] == 63
    assert await _call_public_tool(server, tools, "followupboss_delete_pipeline", 64) == {
        "deleted": True,
        "pipelineId": 64,
    }
    assert (
        await _call_public_tool(
            server,
            tools,
            "followupboss_list_ponds",
        )
    )["ponds"][0]["id"] == 65
    assert (await _call_public_tool(server, tools, "followupboss_get_pond", 66))["id"] == 66
    assert (
        await _call_public_tool(
            server, tools, "followupboss_create_pond", "Sphere Builders", 8, [8, 9]
        )
    )["id"] == 67
    assert (
        await _call_public_tool(server, tools, "followupboss_update_pond", 68, name="Updated Pond")
    )["id"] == 68
    assert await _call_public_tool(server, tools, "followupboss_delete_pond", 69, 9) == {
        "deleted": True,
        "pondId": 69,
    }
    assert (
        await _call_public_tool(
            server,
            tools,
            "followupboss_list_smart_lists",
        )
    )["smartlists"][0]["id"] == 76
    assert (await _call_public_tool(server, tools, "followupboss_get_smart_list", 77))["id"] == 77
    smart_list_people = await _call_public_tool(
        server,
        tools,
        "followupboss_search_people_in_smart_list",
        "Active Buyers",
        limit=1,
        mine=False,
    )
    assert smart_list_people["smartlist"]["id"] == 76
    assert smart_list_people["people"][0]["id"] == 2
    assert (
        await _call_public_tool(
            server,
            tools,
            "followupboss_list_stages",
        )
    )["stages"][0]["id"] == 78
    assert (await _call_public_tool(server, tools, "followupboss_get_stage", 79))["id"] == 79
    assert (await _call_public_tool(server, tools, "followupboss_create_stage", "Qualified"))[
        "id"
    ] == 80
    assert (
        await _call_public_tool(
            server, tools, "followupboss_update_stage", 81, name="Updated Stage"
        )
    )["id"] == 81
    assert await _call_public_tool(server, tools, "followupboss_delete_stage", 82, 11) == {
        "deleted": True,
        "stageId": 82,
    }
    assert (
        await _call_public_tool(
            server,
            tools,
            "followupboss_list_teams",
        )
    )["teams"][0]["id"] == 83
    assert (await _call_public_tool(server, tools, "followupboss_get_team", 84))["id"] == 84
    assert (
        await _call_public_tool(server, tools, "followupboss_create_team", "Buyer Team", [7, 8])
    )["id"] == 85
    assert (
        await _call_public_tool(server, tools, "followupboss_update_team", 86, name="Updated Team")
    )["id"] == 86
    assert await _call_public_tool(server, tools, "followupboss_delete_team", 87) == {
        "deleted": True,
        "teamId": 87,
    }
    assert (
        await _call_public_tool(
            server,
            tools,
            "followupboss_list_calls",
        )
    )["calls"][0]["id"] == 12
    assert (await _call_public_tool(server, tools, "followupboss_get_call", 13))["id"] == 13
    assert (
        await _call_public_tool(server, tools, "followupboss_create_call", 1, "555-0000", True)
    )["id"] == 14
    assert (
        await _call_public_tool(server, tools, "followupboss_update_call", 15, note="Updated note")
    )["id"] == 15
    assert (
        await _call_public_tool(
            server,
            tools,
            "followupboss_list_tasks",
        )
    )["tasks"][0]["id"] == 16
    assert (
        await _call_public_tool(
            server,
            tools,
            "followupboss_list_my_overdue_tasks",
        )
    )["tasks"][0]["id"] == 16
    assert (
        await _call_public_tool(
            server,
            tools,
            "followupboss_list_my_tasks_due_today",
        )
    )["tasks"][0]["id"] == 16
    assert (
        await _call_public_tool(
            server,
            tools,
            "followupboss_list_my_upcoming_tasks",
        )
    )["tasks"][0]["id"] == 16
    assert (await _call_public_tool(server, tools, "followupboss_get_task", 17))["id"] == 17
    assert (
        await _call_public_tool(
            server, tools, "followupboss_create_task", 1, assigned_to="Data", type="Email"
        )
    )["id"] == 18
    assert (await _call_public_tool(server, tools, "followupboss_update_task", 19, type="Text"))[
        "id"
    ] == 19
    assert await _call_public_tool(server, tools, "followupboss_delete_task", 20) == {
        "deleted": True,
        "taskId": 20,
    }
    assert (
        await _call_public_tool(
            server,
            tools,
            "followupboss_list_templates",
        )
    )["templates"][0]["id"] == 20
    assert (await _call_public_tool(server, tools, "followupboss_get_template", 21))["id"] == 21
    assert (
        await _call_public_tool(
            server,
            tools,
            "followupboss_merge_template",
            31,
            merge_person_id=1213,
            recipients={"to": [{"name": "Bob Alvarez", "email": "bob@example.com"}]},
        )
    )["id"] == 57
    assert (
        await _call_public_tool(
            server,
            tools,
            "followupboss_create_template",
            name="New template",
            subject="Hello",
            body="<p>Hello</p>",
        )
    )["id"] == 22
    assert (
        await _call_public_tool(
            server,
            tools,
            "followupboss_update_template",
            23,
            name="Updated template",
            subject="Updated",
            body="<p>Updated</p>",
        )
    )["id"] == 23
    assert await _call_public_tool(server, tools, "followupboss_delete_template", 24) == {
        "deleted": True,
        "templateId": 24,
    }
    assert (
        await _call_public_tool(
            server,
            tools,
            "followupboss_list_text_messages",
        )
    )["textmessages"][0]["id"] == 50
    assert (await _call_public_tool(server, tools, "followupboss_get_text_message", 51))["id"] == 51
    assert (
        await _call_public_tool(
            server,
            tools,
            "followupboss_create_text_message",
            2,
            "Logged externally",
            "555-0002",
            "1234567890",
            is_incoming=False,
            external_label="External SMS",
            external_url="https://example.com/sms/3",
        )
    )["id"] == 58
    assert (
        await _call_public_tool(
            server,
            tools,
            "followupboss_list_text_message_templates",
        )
    )["textmessagetemplates"][0]["id"] == 52
    assert (await _call_public_tool(server, tools, "followupboss_get_text_message_template", 53))[
        "id"
    ] == 53
    assert (
        await _call_public_tool(
            server,
            tools,
            "followupboss_merge_text_message_template",
            31,
            person_id=1213,
            recipients={"to": [{"name": "Bob Alvarez", "phone": "+14075558075"}]},
        )
    )["mergedTemplate"] == "Hey Bob, Alice and Carol..."
    assert (
        await _call_public_tool(
            server,
            tools,
            "followupboss_create_text_message_template",
            name="New text template",
            message="Hello there",
        )
    )["id"] == 54
    assert (
        await _call_public_tool(
            server,
            tools,
            "followupboss_update_text_message_template",
            55,
            name="Updated text template",
            message="Updated text",
        )
    )["id"] == 55
    assert await _call_public_tool(
        server, tools, "followupboss_delete_text_message_template", 56
    ) == {
        "deleted": True,
        "textMessageTemplateId": 56,
    }
    assert (
        await _call_public_tool(
            server,
            tools,
            "followupboss_list_team_inboxes",
        )
    )["teamInboxes"][0]["id"] == 120
    assert (await _call_public_tool(server, tools, "followupboss_add_note", 1, body="hi"))[
        "id"
    ] == 24
    assert (await _call_public_tool(server, tools, "followupboss_get_note", 25))["id"] == 25
    assert (await _call_public_tool(server, tools, "followupboss_update_note", 26, body="updated"))[
        "id"
    ] == 26
    assert await _call_public_tool(server, tools, "followupboss_delete_note", 27) == {
        "deleted": True,
        "noteId": 27,
    }
    assert (
        await _call_public_tool(
            server,
            tools,
            "followupboss_list_webhooks",
        )
    )["webhooks"][0]["id"] == 27
    assert (await _call_public_tool(server, tools, "followupboss_get_webhook", 28))["id"] == 28
    assert (
        await _call_public_tool(
            server, tools, "followupboss_get_webhook_event", "db36048a6b06d80e7f9d3440233ae915"
        )
    )["id"] == "db36048a6b06d80e7f9d3440233ae915"
    assert (
        await _call_public_tool(
            server, tools, "followupboss_create_webhook", "peopleCreated", "https://example.com"
        )
    )["id"] == 29
    assert (
        await _call_public_tool(server, tools, "followupboss_update_webhook", 29, status="Disabled")
    )["status"] == "Disabled"
    assert await _call_public_tool(server, tools, "followupboss_delete_webhook", 30) == {
        "deleted": True,
        "webhookId": 30,
    }
    assert (
        await _call_public_tool(
            server,
            tools,
            "followupboss_list_appointments",
        )
    )["appointments"][0]["id"] == 30
    assert (await _call_public_tool(server, tools, "followupboss_get_appointment", 31))["id"] == 31
    assert (
        await _call_public_tool(
            server,
            tools,
            "followupboss_create_appointment",
            title="Listing appointment",
            start="2026-03-28T10:00:00Z",
            end="2026-03-28T11:00:00Z",
        )
    )["id"] == 32
    assert (
        await _call_public_tool(
            server,
            tools,
            "followupboss_update_appointment",
            33,
            title="Updated appointment",
            start="2026-03-29T10:00:00Z",
            end="2026-03-29T11:00:00Z",
        )
    )["id"] == 33
    assert await _call_public_tool(server, tools, "followupboss_delete_appointment", 34) == {
        "deleted": True,
        "appointmentId": 34,
    }
    assert (
        await _call_public_tool(
            server,
            tools,
            "followupboss_list_timeframes",
        )
    )["timeframes"][0]["id"] == 1

    resources = await server.list_resources()
    assert [str(resource.uri) for resource in resources] == EXPECTED_RESOURCE_URIS
    resource_contents = list(await server.read_resource(EXPECTED_RESOURCE_URIS[0]))
    assert "API Coverage Matrix" in resource_contents[0].content

    prompts = await server.list_prompts()
    assert [prompt.name for prompt in prompts] == EXPECTED_PROMPT_NAMES
    prompt_result = await server.get_prompt(
        "followupboss_compose_lead_event",
        {
            "source": "Portal",
            "type": "Inquiry",
            "message": "Hi",
            "email": "a@example.com",
        },
    )
    content_text = getattr(prompt_result.messages[0].content, "text", None)
    assert isinstance(content_text, str)
    assert content_text.startswith("Create a Follow Up Boss POST /events payload")


@pytest.mark.asyncio
async def test_public_person_activity_tool_returns_scoped_activity() -> None:
    """The registered public helper should enforce person activity scope."""
    server = create_server(
        FollowUpBossSettings.model_validate({"api_key": "key"}),
        client=QueueClient(
            [
                {"id": 42, "firstName": "Data"},
                {
                    "_metadata": {"count": 1, "limit": 2, "offset": 0, "total": 1},
                    "calls": [{"id": 1, "personId": 42}],
                },
                {
                    "_metadata": {"count": 1, "limit": 0, "offset": 0, "total": 1},
                    "textmessages": [{"id": 2, "personId": 42}],
                },
                {
                    "_metadata": {"count": 1, "limit": 2, "offset": 0, "total": 1},
                    "emEvents": [{"count": 1, "personId": 42, "type": "open"}],
                },
                {
                    "_metadata": {"count": 1, "limit": 2, "offset": 0, "total": 1},
                    "events": [{"id": 4, "personId": 42}],
                },
                {
                    "_metadata": {"count": 1, "limit": 2, "offset": 0, "total": 1},
                    "appointments": [{"id": 5, "invitees": [{"personId": 42}]}],
                },
            ]
        ),
    )
    tools = {tool.name: tool for tool in await server.list_tools()}

    result = await _call_public_tool(
        server,
        tools,
        "followupboss_list_person_activity",
        42,
        limit=2,
    )

    assert result["person"]["id"] == 42
    assert result["calls"][0]["personId"] == 42
    assert result["textmessages"][0]["personId"] == 42
    assert result["emEvents"][0]["personId"] == 42
    assert result["events"][0]["personId"] == 42
    assert result["appointments"][0]["invitees"][0]["personId"] == 42


@pytest.mark.asyncio
async def test_public_uncontacted_leads_tool_filters_missing_last_communication() -> None:
    """The registered helper should request lastCommunication and filter locally."""

    @dataclass
    class CapturingQueueClient:
        """Queue-backed client that records outgoing request params."""

        responses: list[dict[str, object] | list[object]]
        params_seen: list[Mapping[str, str] | None] | None = None

        def __post_init__(self) -> None:
            """Initialize request capture storage."""
            self.params_seen = []

        async def aclose(self) -> None:
            """Close the test client."""
            return None

        async def request_json(
            self,
            method: str,
            path: str,
            *,
            headers: Mapping[str, str] | None = None,
            json_body: Mapping[str, object] | None = None,
            params: Mapping[str, str] | None = None,
        ) -> dict[str, object] | list[object]:
            """Record request params and return the next queued response."""
            del method, path, headers, json_body
            if self.params_seen is None:
                raise AssertionError("params_seen was not initialized.")
            self.params_seen.append(params)
            return self.responses.pop(0)

    client = CapturingQueueClient(
        responses=[
            {"id": 7, "name": "Picard"},
            {
                "_metadata": {"limit": 100, "offset": 0, "total": 1},
                "people": [
                    {
                        "id": 724,
                        "name": "Wesley Binks",
                        "contacted": True,
                        "lastCommunication": None,
                    }
                ],
            },
        ]
    )
    server = create_server(
        FollowUpBossSettings.model_validate({"api_key": "key"}),
        client=client,
    )
    tools = {tool.name: tool for tool in await server.list_tools()}

    result = await _call_public_tool(
        server,
        tools,
        "followupboss_list_uncontacted_leads",
        limit=25,
    )

    assert result["people"][0]["id"] == 724
    assert client.params_seen is not None
    assert client.params_seen[-1] == {
        "assignedUserId": "7",
        "fields": (
            "assignedTo,assignedUserId,contacted,created,emails,firstName,id,"
            "lastActivity,lastCommunication,lastName,name,phones,source,stage"
        ),
        "limit": "100",
        "offset": "0",
        "sort": "-created",
    }


@pytest.mark.asyncio
async def test_stdio_client_interoperates_with_server_surface() -> None:
    """The official stdio client should interoperate with tools, resources, and prompts."""
    server_script = textwrap.dedent(
        """
        from collections.abc import Mapping

        from followupboss_mcp.config import FollowUpBossSettings
        from followupboss_mcp.mcp_server import create_server


        class QueueClient:
            def __init__(self) -> None:
                self.responses = [
                    {"id": 1, "name": "Picard"},
                    {
                        "id": 1,
                        "name": "Gerald Leenerts",
                        "apiKey": "secret-api-key",
                        "algoliaKey": "secret-algolia-key",
                        "callingCapabilityToken": "secret-calling-token",
                        "notifyBy": ["email", "sms"],
                        "intercomSettings": {"user_hash": "secret-hash"},
                    },
                    {"_metadata": {"limit": 10, "offset": 0, "total": 1}, "people": [{"id": 2}]},
                    {"id": 3, "firstName": "Tom"},
                    {},
                    {
                        "_metadata": {"limit": 10, "offset": 0, "total": 2},
                        "timeframes": [{"id": 10, "timeframe": "0-3 Months"}],
                    },
                    {"id": 3, "personId": 2, "type": "Inquiry"},
                    {"_metadata": {"limit": 10, "offset": 0, "total": 1}, "tasks": [{"id": 4}]},
                    {"id": 5, "personId": 2, "assignedTo": "Data", "type": "Call"},
                    {"_metadata": {"limit": 10, "offset": 0, "total": 1}, "calls": [{"id": 6}]},
                    {"id": 7, "personId": 2, "phone": "555-0000", "userName": "Data"},
                    {"_metadata": {"limit": 10, "offset": 0, "total": 1}, "templates": [{"id": 8}]},
                    {"id": 9, "name": "Buyer intro", "subject": "Hello"},
                    {
                        "_metadata": {"limit": 10, "offset": 0, "total": 1},
                        "appointments": [{"id": 10}],
                    },
                    {"id": 11, "title": "Buyer consult"},
                ]

            async def aclose(self) -> None:
                return None

            async def request_json(
                self,
                method: str,
                path: str,
                *,
                headers: Mapping[str, str] | None = None,
                json_body: Mapping[str, object] | None = None,
                params: Mapping[str, str] | None = None,
            ) -> dict[str, object] | list[object]:
                del method, path, headers, json_body, params
                return self.responses.pop(0)


        create_server(
            FollowUpBossSettings.model_validate({"api_key": "key"}),
            client=QueueClient(),
        ).run(transport="stdio")
        """
    )
    server = StdioServerParameters(
        command=sys.executable,
        args=["-c", server_script],
        cwd=str(PROJECT_ROOT),
        env=_server_python_env(),
    )
    resource_uri = TypeAdapter(AnyUrl).validate_python(EXPECTED_RESOURCE_URIS[0])

    async with stdio_client(server) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            tools = await session.list_tools()
            tool_names = sorted(tool.name for tool in tools.tools)
            assert tool_names == EXPECTED_REGISTERED_TOOL_NAMES

            identity_result = await session.call_tool("followupboss_get_identity")
            assert identity_result.isError is False
            assert identity_result.structuredContent == {"id": 1, "name": "Picard"}

            me_result = await session.call_tool("followupboss_get_me")
            assert me_result.isError is False
            assert me_result.structuredContent is not None
            assert me_result.structuredContent["id"] == 1
            assert me_result.structuredContent["apiKey"] == "***redacted***"
            assert me_result.structuredContent["algoliaKey"] == "***redacted***"
            assert me_result.structuredContent["callingCapabilityToken"] == "***redacted***"
            assert me_result.structuredContent["notifyBy"] == ["email", "sms"]
            assert me_result.structuredContent["intercomSettings"]["user_hash"] == "***redacted***"

            people_result = await session.call_tool(
                "followupboss_search_people",
                {"email": "a@example.com", "include_ponds": True},
            )
            assert people_result.isError is False
            assert people_result.structuredContent is not None
            assert people_result.structuredContent["_metadata"] == {
                "count": 1,
                "limit": 10,
                "next_token": None,
                "next_link": None,
                "offset": 0,
                "total": 1,
            }
            people = people_result.structuredContent["people"]
            assert isinstance(people, list)
            assert people[0]["id"] == 2

            create_person_result = await session.call_tool(
                "followupboss_create_person",
                {"first_name": "Tom"},
            )
            assert create_person_result.isError is False
            assert create_person_result.structuredContent == {"id": 3, "firstName": "Tom"}

            delete_person_result = await session.call_tool(
                "followupboss_delete_person",
                {"person_id": 4},
            )
            assert delete_person_result.isError is False
            assert delete_person_result.structuredContent == {"deleted": True, "personId": 4}

            timeframes_result = await session.call_tool("followupboss_list_timeframes")
            assert timeframes_result.isError is False
            assert timeframes_result.structuredContent is not None
            assert timeframes_result.structuredContent["_metadata"] == {
                "count": 1,
                "limit": 10,
                "next_token": None,
                "next_link": None,
                "offset": 0,
                "total": 2,
            }
            timeframes = timeframes_result.structuredContent["timeframes"]
            assert isinstance(timeframes, list)
            assert timeframes[0]["id"] == 10

            event_result = await session.call_tool("followupboss_get_event", {"event_id": 3})
            assert event_result.isError is False
            assert event_result.structuredContent is not None
            assert event_result.structuredContent["id"] == 3

            tasks_result = await session.call_tool("followupboss_list_tasks", {"person_id": 2})
            assert tasks_result.isError is False
            assert tasks_result.structuredContent is not None
            tasks = tasks_result.structuredContent["tasks"]
            assert isinstance(tasks, list)
            assert tasks[0]["id"] == 4

            task_result = await session.call_tool("followupboss_get_task", {"task_id": 5})
            assert task_result.isError is False
            assert task_result.structuredContent is not None
            assert task_result.structuredContent["id"] == 5

            calls_result = await session.call_tool("followupboss_list_calls", {"person_id": 2})
            assert calls_result.isError is False
            assert calls_result.structuredContent is not None
            calls = calls_result.structuredContent["calls"]
            assert isinstance(calls, list)
            assert calls[0]["id"] == 6

            call_result = await session.call_tool("followupboss_get_call", {"call_id": 7})
            assert call_result.isError is False
            assert call_result.structuredContent is not None
            assert call_result.structuredContent["id"] == 7

            templates_result = await session.call_tool("followupboss_list_templates")
            assert templates_result.isError is False
            assert templates_result.structuredContent is not None
            templates = templates_result.structuredContent["templates"]
            assert isinstance(templates, list)
            assert templates[0]["id"] == 8

            template_result = await session.call_tool(
                "followupboss_get_template", {"template_id": 9}
            )
            assert template_result.isError is False
            assert template_result.structuredContent is not None
            assert template_result.structuredContent["id"] == 9

            appointments_result = await session.call_tool("followupboss_list_appointments")
            assert appointments_result.isError is False
            assert appointments_result.structuredContent is not None
            appointments = appointments_result.structuredContent["appointments"]
            assert isinstance(appointments, list)
            assert appointments[0]["id"] == 10

            appointment_result = await session.call_tool(
                "followupboss_get_appointment",
                {"appointment_id": 11},
            )
            assert appointment_result.isError is False
            assert appointment_result.structuredContent is not None
            assert appointment_result.structuredContent["id"] == 11

            resources = await session.list_resources()
            assert [str(resource.uri) for resource in resources.resources] == EXPECTED_RESOURCE_URIS
            resource_result = await session.read_resource(resource_uri)
            resource_text = getattr(resource_result.contents[0], "text", None)
            assert isinstance(resource_text, str)
            assert "API Coverage Matrix" in resource_text

            prompts = await session.list_prompts()
            assert [prompt.name for prompt in prompts.prompts] == EXPECTED_PROMPT_NAMES
            prompt_result = await session.get_prompt(
                EXPECTED_PROMPT_NAMES[0],
                {
                    "source": "Portal",
                    "type": "Inquiry",
                    "message": "Hi",
                    "email": "a@example.com",
                },
            )
            prompt_text = getattr(prompt_result.messages[0].content, "text", None)
            assert isinstance(prompt_text, str)
            assert prompt_text.startswith("Create a Follow Up Boss POST /events payload")


@pytest.mark.asyncio
async def test_streamable_http_client_interoperates_with_server_surface() -> None:
    """The official streamable HTTP client should interoperate with the server surface."""
    port = _reserve_port()
    server_script = textwrap.dedent(
        f"""
        from collections.abc import Mapping

        from followupboss_mcp.config import FollowUpBossSettings
        from followupboss_mcp.mcp_server import create_server


        class QueueClient:
            def __init__(self) -> None:
                self.responses = [
                    {{"id": 1, "name": "Picard"}},
                    {{
                        "id": 1,
                        "name": "Gerald Leenerts",
                        "apiKey": "secret-api-key",
                        "algoliaKey": "secret-algolia-key",
                        "callingCapabilityToken": "secret-calling-token",
                        "notifyBy": ["email", "sms"],
                        "intercomSettings": {{"user_hash": "secret-hash"}},
                    }},
                    {{
                        "_metadata": {{"limit": 10, "offset": 0, "total": 1}},
                        "people": [{{"id": 2}}],
                    }},
                    {{}},
                    {{
                        "_metadata": {{"limit": 10, "offset": 0, "total": 2}},
                        "timeframes": [{{"id": 10, "timeframe": "0-3 Months"}}],
                    }},
                    {{"id": 3, "personId": 2, "type": "Inquiry"}},
                    {{
                        "_metadata": {{"limit": 10, "offset": 0, "total": 1}},
                        "tasks": [{{"id": 4}}],
                    }},
                    {{"id": 5, "personId": 2, "assignedTo": "Data", "type": "Call"}},
                    {{
                        "_metadata": {{"limit": 10, "offset": 0, "total": 1}},
                        "calls": [{{"id": 6}}],
                    }},
                    {{"id": 7, "personId": 2, "phone": "555-0000", "userName": "Data"}},
                    {{
                        "_metadata": {{"limit": 10, "offset": 0, "total": 1}},
                        "templates": [{{"id": 8}}],
                    }},
                    {{"id": 9, "name": "Buyer intro", "subject": "Hello"}},
                    {{
                        "_metadata": {{"limit": 10, "offset": 0, "total": 1}},
                        "appointments": [{{"id": 10}}],
                    }},
                    {{"id": 11, "title": "Buyer consult"}},
                ]

            async def aclose(self) -> None:
                return None

            async def request_json(
                self,
                method: str,
                path: str,
                *,
                headers: Mapping[str, str] | None = None,
                json_body: Mapping[str, object] | None = None,
                params: Mapping[str, str] | None = None,
            ) -> dict[str, object] | list[object]:
                del method, path, headers, json_body, params
                return self.responses.pop(0)


        create_server(
            FollowUpBossSettings.model_validate({{"api_key": "key"}}),
            client=QueueClient(),
            host="127.0.0.1",
            port={port},
            streamable_http_path="/mcp",
        ).run(transport="streamable-http")
        """
    )
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        "-c",
        server_script,
        cwd=str(PROJECT_ROOT),
        env=_server_python_env(),
    )
    try:
        await _wait_for_port("127.0.0.1", port)
        resource_uri = TypeAdapter(AnyUrl).validate_python(EXPECTED_RESOURCE_URIS[0])
        async with streamable_http_client(f"http://127.0.0.1:{port}/mcp") as (
            read_stream,
            write_stream,
            _,
        ):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()

                tools = await session.list_tools()
                tool_names = sorted(tool.name for tool in tools.tools)
                assert tool_names == EXPECTED_REGISTERED_TOOL_NAMES

                identity_result = await session.call_tool("followupboss_get_identity")
                assert identity_result.isError is False
                assert identity_result.structuredContent == {"id": 1, "name": "Picard"}

                me_result = await session.call_tool("followupboss_get_me")
                assert me_result.isError is False
                assert me_result.structuredContent is not None
                assert me_result.structuredContent["id"] == 1
                assert me_result.structuredContent["apiKey"] == "***redacted***"
                assert me_result.structuredContent["algoliaKey"] == "***redacted***"
                assert me_result.structuredContent["callingCapabilityToken"] == "***redacted***"
                assert me_result.structuredContent["notifyBy"] == ["email", "sms"]
                assert (
                    me_result.structuredContent["intercomSettings"]["user_hash"] == "***redacted***"
                )

                people_result = await session.call_tool(
                    "followupboss_search_people",
                    {"email": "a@example.com", "include_ponds": True},
                )
                assert people_result.isError is False
                assert people_result.structuredContent is not None
                assert people_result.structuredContent["_metadata"] == {
                    "count": 1,
                    "limit": 10,
                    "next_token": None,
                    "next_link": None,
                    "offset": 0,
                    "total": 1,
                }
                people = people_result.structuredContent["people"]
                assert isinstance(people, list)
                assert people[0]["id"] == 2

                delete_person_result = await session.call_tool(
                    "followupboss_delete_person",
                    {"person_id": 4},
                )
                assert delete_person_result.isError is False
                assert delete_person_result.structuredContent == {"deleted": True, "personId": 4}

                timeframes_result = await session.call_tool("followupboss_list_timeframes")
                assert timeframes_result.isError is False
                assert timeframes_result.structuredContent is not None
                assert timeframes_result.structuredContent["_metadata"] == {
                    "count": 1,
                    "limit": 10,
                    "next_token": None,
                    "next_link": None,
                    "offset": 0,
                    "total": 2,
                }
                timeframes = timeframes_result.structuredContent["timeframes"]
                assert isinstance(timeframes, list)
                assert timeframes[0]["id"] == 10

                event_result = await session.call_tool("followupboss_get_event", {"event_id": 3})
                assert event_result.isError is False
                assert event_result.structuredContent is not None
                assert event_result.structuredContent["id"] == 3

                tasks_result = await session.call_tool("followupboss_list_tasks", {"person_id": 2})
                assert tasks_result.isError is False
                assert tasks_result.structuredContent is not None
                tasks = tasks_result.structuredContent["tasks"]
                assert isinstance(tasks, list)
                assert tasks[0]["id"] == 4

                task_result = await session.call_tool("followupboss_get_task", {"task_id": 5})
                assert task_result.isError is False
                assert task_result.structuredContent is not None
                assert task_result.structuredContent["id"] == 5

                calls_result = await session.call_tool("followupboss_list_calls", {"person_id": 2})
                assert calls_result.isError is False
                assert calls_result.structuredContent is not None
                calls = calls_result.structuredContent["calls"]
                assert isinstance(calls, list)
                assert calls[0]["id"] == 6

                call_result = await session.call_tool("followupboss_get_call", {"call_id": 7})
                assert call_result.isError is False
                assert call_result.structuredContent is not None
                assert call_result.structuredContent["id"] == 7

                templates_result = await session.call_tool("followupboss_list_templates")
                assert templates_result.isError is False
                assert templates_result.structuredContent is not None
                templates = templates_result.structuredContent["templates"]
                assert isinstance(templates, list)
                assert templates[0]["id"] == 8

                template_result = await session.call_tool(
                    "followupboss_get_template", {"template_id": 9}
                )
                assert template_result.isError is False
                assert template_result.structuredContent is not None
                assert template_result.structuredContent["id"] == 9

                appointments_result = await session.call_tool("followupboss_list_appointments")
                assert appointments_result.isError is False
                assert appointments_result.structuredContent is not None
                appointments = appointments_result.structuredContent["appointments"]
                assert isinstance(appointments, list)
                assert appointments[0]["id"] == 10

                appointment_result = await session.call_tool(
                    "followupboss_get_appointment",
                    {"appointment_id": 11},
                )
                assert appointment_result.isError is False
                assert appointment_result.structuredContent is not None
                assert appointment_result.structuredContent["id"] == 11

                resources = await session.list_resources()
                assert [
                    str(resource.uri) for resource in resources.resources
                ] == EXPECTED_RESOURCE_URIS
                resource_result = await session.read_resource(resource_uri)
                resource_text = getattr(resource_result.contents[0], "text", None)
                assert isinstance(resource_text, str)
                assert "API Coverage Matrix" in resource_text

                prompts = await session.list_prompts()
                assert [prompt.name for prompt in prompts.prompts] == EXPECTED_PROMPT_NAMES
                prompt_result = await session.get_prompt(
                    EXPECTED_PROMPT_NAMES[0],
                    {
                        "source": "Portal",
                        "type": "Inquiry",
                        "message": "Hi",
                        "email": "a@example.com",
                    },
                )
                prompt_text = getattr(prompt_result.messages[0].content, "text", None)
                assert isinstance(prompt_text, str)
                assert prompt_text.startswith("Create a Follow Up Boss POST /events payload")
    finally:
        process.terminate()
        await process.wait()


def test_cli_parser_and_main(monkeypatch: pytest.MonkeyPatch) -> None:
    """The CLI should build both transports and pass through the selected mode."""
    parser = build_parser()
    assert parser.prog == "followupboss-mcp"

    runs: list[tuple[str, Any]] = []

    @dataclass
    class FakeServerSettings:
        """Tiny server-settings stand-in for CLI tests."""

        transport: str = "stdio"
        host: str = "127.0.0.1"
        port: int = 8000
        streamable_http_path: str = "/mcp"

        def model_copy(self, *, update: dict[str, Any]) -> FakeServerSettings:
            """Return a copied settings object with updates applied."""
            return FakeServerSettings(
                transport=update.get("transport", self.transport),
                host=update.get("host", self.host),
                port=update.get("port", self.port),
                streamable_http_path=update.get(
                    "streamable_http_path",
                    self.streamable_http_path,
                ),
            )

    class FakeServer:
        def run(self, transport: str) -> None:
            runs.append((transport, {}))

    def fake_create_server(settings: object, **kwargs: object) -> FakeServer:
        runs.append(("create", {"settings": settings, "kwargs": kwargs}))
        return FakeServer()

    monkeypatch.setattr(
        "followupboss_mcp.cli.FollowUpBossSettings",
        lambda: _service_stub(),
    )
    monkeypatch.setattr(
        "followupboss_mcp.cli.FollowUpBossServerSettings",
        lambda: FakeServerSettings(),
    )
    monkeypatch.setattr("followupboss_mcp.cli.create_server", fake_create_server)

    assert main(["stdio"]) == 0
    assert main(["streamable-http", "--host", "0.0.0.0", "--port", "9000", "--path", "/alt"]) == 0
    assert runs[0][0] == "create"
    assert runs[0][1]["kwargs"]["server_settings"].transport == "stdio"
    assert runs[1] == ("stdio", {})
    assert runs[2][0] == "create"
    assert runs[2][1]["kwargs"]["server_settings"].transport == "streamable-http"
    assert runs[2][1]["kwargs"]["server_settings"].host == "0.0.0.0"
    assert runs[2][1]["kwargs"]["server_settings"].port == 9000
    assert runs[2][1]["kwargs"]["server_settings"].streamable_http_path == "/alt"
    assert runs[3] == ("streamable-http", {})
