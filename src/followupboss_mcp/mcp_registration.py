"""Grouped FastMCP registration helpers for the Follow Up Boss server."""

from __future__ import annotations

from pathlib import Path

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
    DeletePipelineToolInput,
    DeletePondToolInput,
    DeleteReactionToolInput,
    DeleteStageToolInput,
    DeleteTaskToolInput,
    DeleteTeamToolInput,
    DeleteTemplateToolInput,
    DeleteTextMessageTemplateToolInput,
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
    GetWebhookToolInput,
    IgnoreUnclaimedPersonToolInput,
    ListInboxAppInstallationsToolInput,
    ListInboxAppParticipantsToolInput,
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
)
from followupboss_mcp.models.action_plans import (
    ActionPlanListRequest,
    ActionPlanPersonListRequest,
    ActionPlanPersonStatus,
    CreateActionPlanPersonRequest,
)
from followupboss_mcp.models.appointment_metadata import (
    AppointmentOutcomeListRequest,
    AppointmentTypeListRequest,
    CreateAppointmentOutcomeRequest,
    CreateAppointmentTypeRequest,
)
from followupboss_mcp.models.appointments import AppointmentListRequest, CreateAppointmentRequest
from followupboss_mcp.models.attachments import (
    CreateDealAttachmentRequest,
    CreatePersonAttachmentRequest,
)
from followupboss_mcp.models.automations import (
    AutomationListRequest,
    AutomationPauseStatus,
    AutomationPeopleListRequest,
    AutomationRunStatus,
    CreateAutomationPersonRequest,
)
from followupboss_mcp.models.calls import CallListRequest, CreateCallRequest
from followupboss_mcp.models.custom_fields import (
    CreateCustomFieldRequest,
    CustomFieldListRequest,
    CustomFieldType,
)
from followupboss_mcp.models.deals import (
    CreateDealCustomFieldRequest,
    CreateDealRequest,
    DealCustomFieldListRequest,
    DealListRequest,
)
from followupboss_mcp.models.email_marketing import (
    CreateEmailCampaignRequest,
    CreateEmailEventsBatchRequest,
    EmailCampaignListRequest,
    EmailEventListRequest,
    EmailEventType,
)
from followupboss_mcp.models.events import CreateEventRequest, EventSearchRequest
from followupboss_mcp.models.groups import CreateGroupRequest, GroupListRequest
from followupboss_mcp.models.inbox_apps import (
    InboxAppMessageDeliveryStatus,
    InstallInboxAppRequest,
)
from followupboss_mcp.models.notes import CreateNoteRequest
from followupboss_mcp.models.people import (
    CreatePersonRequest,
    PeopleSearchRequest,
    UnclaimedPeopleListRequest,
)
from followupboss_mcp.models.people_relationships import (
    CreatePeopleRelationshipRequest,
    PeopleRelationshipListRequest,
)
from followupboss_mcp.models.pipelines import (
    CreatePipelineRequest,
    PipelineListRequest,
    PipelineStageInput,
)
from followupboss_mcp.models.ponds import CreatePondRequest, PondListRequest
from followupboss_mcp.models.reactions import ReactionRefType
from followupboss_mcp.models.smart_lists import SmartListListRequest
from followupboss_mcp.models.stages import CreateStageRequest, StageListRequest
from followupboss_mcp.models.tasks import CreateTaskRequest, TaskListRequest
from followupboss_mcp.models.team_inboxes import TeamInboxListRequest
from followupboss_mcp.models.teams import CreateTeamRequest, TeamListRequest
from followupboss_mcp.models.templates import (
    CreateTemplateRequest,
    MergeTemplateRequest,
    TemplateListRequest,
)
from followupboss_mcp.models.text_messages import (
    CreateTextMessageRequest,
    CreateTextMessageTemplateRequest,
    MergeTextMessageTemplateRequest,
    TextMessageListRequest,
    TextMessageTemplateListRequest,
)
from followupboss_mcp.models.timeframes import TimeframeListRequest
from followupboss_mcp.models.users import UserListRequest
from followupboss_mcp.models.webhooks import CreateWebhookRequest, WebhookListRequest
from mcp.server.fastmcp import FastMCP


def register_server_surface(
    mcp: FastMCP,
    adapter: FollowUpBossToolAdapter,
    *,
    project_root: Path,
) -> None:
    """Register the complete Follow Up Boss MCP surface.

    Args:
        mcp: The FastMCP server instance to extend.
        adapter: The typed MCP adapter that delegates to domain services.
        project_root: The repository root used for resource-backed content.
    """
    _register_identity_tools(mcp, adapter)
    _register_people_tools(mcp, adapter)
    _register_people_relationship_tools(mcp, adapter)
    _register_timeframe_tools(mcp, adapter)
    _register_attachment_tools(mcp, adapter)
    _register_reaction_tools(mcp, adapter)
    _register_threaded_reply_tools(mcp, adapter)
    _register_event_tools(mcp, adapter)
    _register_email_marketing_tools(mcp, adapter)
    _register_action_plan_tools(mcp, adapter)
    _register_automation_tools(mcp, adapter)
    _register_group_tools(mcp, adapter)
    _register_inbox_app_tools(mcp, adapter)
    _register_user_tools(mcp, adapter)
    _register_custom_field_tools(mcp, adapter)
    _register_deal_tools(mcp, adapter)
    _register_appointment_metadata_tools(mcp, adapter)
    _register_appointment_tools(mcp, adapter)
    _register_call_tools(mcp, adapter)
    _register_pipeline_tools(mcp, adapter)
    _register_pond_tools(mcp, adapter)
    _register_smart_list_tools(mcp, adapter)
    _register_stage_tools(mcp, adapter)
    _register_task_tools(mcp, adapter)
    _register_team_inbox_tools(mcp, adapter)
    _register_team_tools(mcp, adapter)
    _register_template_tools(mcp, adapter)
    _register_text_message_tools(mcp, adapter)
    _register_note_tools(mcp, adapter)
    _register_webhook_tools(mcp, adapter)
    _register_resources_and_prompts(mcp, project_root=project_root)


def _register_identity_tools(mcp: FastMCP, adapter: FollowUpBossToolAdapter) -> None:
    """Register identity-related MCP tools.

    Args:
        mcp: The FastMCP server instance.
        adapter: The typed Follow Up Boss tool adapter.
    """

    @mcp.tool(
        name="followupboss_get_identity",
        description=(
            "Return identity information for the authenticated Follow Up Boss user and account."
        ),
    )
    async def followupboss_get_identity() -> dict[str, object]:
        return await adapter.get_identity()


def _register_people_tools(mcp: FastMCP, adapter: FollowUpBossToolAdapter) -> None:
    """Register people-related MCP tools.

    Args:
        mcp: The FastMCP server instance.
        adapter: The typed Follow Up Boss tool adapter.
    """

    @mcp.tool(
        name="followupboss_search_people",
        description=(
            "Search Follow Up Boss people with documented query parameters and pagination metadata."
        ),
    )
    async def followupboss_search_people(
        *,
        fields: list[str] | None = None,
        id: int | None = None,
        ids: list[int] | None = None,
        id_greater_than: int | None = None,
        id_less_than: int | None = None,
        limit: int | None = None,
        next_token: str | None = None,
        offset: int | None = None,
        sort: str | None = None,
        assigned_user_id: int | None = None,
        email: str | None = None,
        first_name: str | None = None,
        include_trash: bool | None = None,
        last_name: str | None = None,
        name: str | None = None,
        phone: str | None = None,
        source: str | None = None,
        stage: str | None = None,
        custom_field_filters: dict[str, str] | None = None,
    ) -> dict[str, object]:
        tool_input = PeopleSearchRequest(
            fields=fields,
            id=id,
            ids=ids,
            id_greater_than=id_greater_than,
            id_less_than=id_less_than,
            limit=limit,
            next_token=next_token,
            offset=offset,
            sort=sort,
            assigned_user_id=assigned_user_id,
            email=email,
            first_name=first_name,
            include_trash=include_trash,
            last_name=last_name,
            name=name,
            phone=phone,
            source=source,
            stage=stage,
            custom_field_filters=custom_field_filters,
        )
        return await adapter.search_people(tool_input)

    @mcp.tool(
        name="followupboss_get_person",
        description="Fetch a single Follow Up Boss person by ID.",
    )
    async def followupboss_get_person(
        person_id: int,
        *,
        fields: list[str] | None = None,
    ) -> dict[str, object]:
        return await adapter.get_person(GetPersonToolInput(person_id=person_id, fields=fields))

    @mcp.tool(
        name="followupboss_create_person",
        description=(
            "Create a Follow Up Boss person directly. "
            "Use followupboss_send_event for canonical lead ingestion."
        ),
    )
    async def followupboss_create_person(
        *,
        addresses: list[dict[str, object]] | None = None,
        assigned_lender_id: int | None = None,
        assigned_lender_name: str | None = None,
        assigned_pond_id: int | None = None,
        assigned_to: str | None = None,
        assigned_user_id: int | None = None,
        background: str | None = None,
        collaborators: list[int] | None = None,
        contacted: bool | None = None,
        created_at: str | None = None,
        custom_fields: dict[str, object] | None = None,
        deduplicate: bool | None = None,
        emails: list[dict[str, object]] | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        phones: list[dict[str, object]] | None = None,
        price: int | None = None,
        source: str | None = None,
        source_url: str | None = None,
        stage: str | None = None,
        tags: list[str] | None = None,
        timeframe_id: int | None = None,
    ) -> dict[str, object]:
        tool_input = CreatePersonRequest.model_validate(
            {
                "addresses": addresses,
                "assigned_lender_id": assigned_lender_id,
                "assigned_lender_name": assigned_lender_name,
                "assigned_pond_id": assigned_pond_id,
                "assigned_to": assigned_to,
                "assigned_user_id": assigned_user_id,
                "background": background,
                "collaborators": collaborators,
                "contacted": contacted,
                "created_at": created_at,
                "custom_fields": custom_fields,
                "deduplicate": deduplicate,
                "emails": emails,
                "first_name": first_name,
                "last_name": last_name,
                "phones": phones,
                "price": price,
                "source": source,
                "source_url": source_url,
                "stage": stage,
                "tags": tags,
                "timeframe_id": timeframe_id,
            }
        )
        return await adapter.create_person(tool_input)

    @mcp.tool(
        name="followupboss_update_person",
        description="Update a single Follow Up Boss person by ID.",
    )
    async def followupboss_update_person(
        person_id: int,
        *,
        addresses: list[dict[str, object]] | None = None,
        assigned_lender_id: int | None = None,
        assigned_lender_name: str | None = None,
        assigned_pond_id: int | None = None,
        assigned_to: str | None = None,
        assigned_user_id: int | None = None,
        background: str | None = None,
        contacted: bool | None = None,
        custom_fields: dict[str, object] | None = None,
        emails: list[dict[str, object]] | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        merge_tags: bool | None = None,
        phones: list[dict[str, object]] | None = None,
        price: int | None = None,
        stage: str | None = None,
        tags: list[str] | None = None,
        timeframe_id: int | None = None,
    ) -> dict[str, object]:
        tool_input = UpdatePersonToolInput.model_validate(
            {
                "person_id": person_id,
                "addresses": addresses,
                "assigned_lender_id": assigned_lender_id,
                "assigned_lender_name": assigned_lender_name,
                "assigned_pond_id": assigned_pond_id,
                "assigned_to": assigned_to,
                "assigned_user_id": assigned_user_id,
                "background": background,
                "contacted": contacted,
                "custom_fields": custom_fields,
                "emails": emails,
                "first_name": first_name,
                "last_name": last_name,
                "merge_tags": merge_tags,
                "phones": phones,
                "price": price,
                "stage": stage,
                "tags": tags,
                "timeframe_id": timeframe_id,
            }
        )
        return await adapter.update_person(tool_input)

    @mcp.tool(
        name="followupboss_check_duplicate_person",
        description="Check whether a person already exists in Follow Up Boss by email or phone.",
    )
    async def followupboss_check_duplicate_person(
        *,
        email: str | None = None,
        phone: str | None = None,
    ) -> dict[str, object]:
        return await adapter.check_duplicate_person(
            CheckDuplicatePersonToolInput.model_validate(
                {
                    "email": email,
                    "phone": phone,
                }
            )
        )

    @mcp.tool(
        name="followupboss_list_unclaimed_people",
        description="List unclaimed Follow Up Boss leads available to the authenticated user.",
    )
    async def followupboss_list_unclaimed_people(
        *,
        limit: int | None = None,
        offset: int | None = None,
    ) -> dict[str, object]:
        return await adapter.list_unclaimed_people(
            UnclaimedPeopleListRequest(limit=limit, offset=offset)
        )

    @mcp.tool(
        name="followupboss_claim_person",
        description="Claim an unclaimed Follow Up Boss lead by person ID.",
    )
    async def followupboss_claim_person(person_id: int) -> dict[str, object]:
        return await adapter.claim_person(ClaimPersonToolInput(person_id=person_id))

    @mcp.tool(
        name="followupboss_ignore_unclaimed_person",
        description="Ignore an unclaimed Follow Up Boss lead offer by person ID.",
    )
    async def followupboss_ignore_unclaimed_person(person_id: int) -> dict[str, object]:
        return await adapter.ignore_unclaimed_person(
            IgnoreUnclaimedPersonToolInput(person_id=person_id)
        )


def _register_people_relationship_tools(
    mcp: FastMCP,
    adapter: FollowUpBossToolAdapter,
) -> None:
    """Register people-relationship-related MCP tools.

    Args:
        mcp: The FastMCP server instance.
        adapter: The typed Follow Up Boss tool adapter.
    """

    @mcp.tool(
        name="followupboss_list_people_relationships",
        description="List Follow Up Boss people relationships.",
    )
    async def followupboss_list_people_relationships(
        *,
        first_name: str | None = None,
        last_name: str | None = None,
        name: str | None = None,
        person_id: int | None = None,
        sort: str | None = None,
    ) -> dict[str, object]:
        return await adapter.list_people_relationships(
            PeopleRelationshipListRequest(
                first_name=first_name,
                last_name=last_name,
                name=name,
                person_id=person_id,
                sort=sort,
            )
        )

    @mcp.tool(
        name="followupboss_get_people_relationship",
        description="Fetch a single Follow Up Boss people relationship by ID.",
    )
    async def followupboss_get_people_relationship(
        people_relationship_id: int,
    ) -> dict[str, object]:
        return await adapter.get_people_relationship(
            GetPeopleRelationshipToolInput(people_relationship_id=people_relationship_id)
        )

    @mcp.tool(
        name="followupboss_create_people_relationship",
        description="Create a Follow Up Boss people relationship for a person.",
    )
    async def followupboss_create_people_relationship(
        person_id: int,
        *,
        addresses: list[dict[str, object]] | None = None,
        emails: list[dict[str, object]] | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        phones: list[dict[str, object]] | None = None,
        type: str | None = None,
    ) -> dict[str, object]:
        return await adapter.create_people_relationship(
            CreatePeopleRelationshipRequest.model_validate(
                {
                    "person_id": person_id,
                    "addresses": addresses,
                    "emails": emails,
                    "first_name": first_name,
                    "last_name": last_name,
                    "phones": phones,
                    "type": type,
                }
            )
        )

    @mcp.tool(
        name="followupboss_update_people_relationship",
        description="Update a Follow Up Boss people relationship by ID.",
    )
    async def followupboss_update_people_relationship(
        people_relationship_id: int,
        *,
        addresses: list[dict[str, object]] | None = None,
        emails: list[dict[str, object]] | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        phones: list[dict[str, object]] | None = None,
        type: str | None = None,
    ) -> dict[str, object]:
        return await adapter.update_people_relationship(
            UpdatePeopleRelationshipToolInput.model_validate(
                {
                    "people_relationship_id": people_relationship_id,
                    "addresses": addresses,
                    "emails": emails,
                    "first_name": first_name,
                    "last_name": last_name,
                    "phones": phones,
                    "type": type,
                }
            )
        )

    @mcp.tool(
        name="followupboss_delete_people_relationship",
        description="Delete a Follow Up Boss people relationship by ID.",
    )
    async def followupboss_delete_people_relationship(
        people_relationship_id: int,
    ) -> dict[str, object]:
        return await adapter.delete_people_relationship(
            DeletePeopleRelationshipToolInput(people_relationship_id=people_relationship_id)
        )


def _register_timeframe_tools(mcp: FastMCP, adapter: FollowUpBossToolAdapter) -> None:
    """Register timeframe-related MCP tools.

    Args:
        mcp: The FastMCP server instance.
        adapter: The typed Follow Up Boss tool adapter.
    """

    @mcp.tool(
        name="followupboss_list_timeframes",
        description="List Follow Up Boss timeframes with pagination metadata.",
    )
    async def followupboss_list_timeframes() -> dict[str, object]:
        return await adapter.list_timeframes(TimeframeListRequest())


def _register_attachment_tools(mcp: FastMCP, adapter: FollowUpBossToolAdapter) -> None:
    """Register deal and person attachment MCP tools.

    Args:
        mcp: The FastMCP server instance.
        adapter: The typed Follow Up Boss tool adapter.
    """

    @mcp.tool(
        name="followupboss_get_person_attachment",
        description="Fetch a single Follow Up Boss person attachment by ID.",
    )
    async def followupboss_get_person_attachment(person_attachment_id: int) -> dict[str, object]:
        return await adapter.get_person_attachment(
            GetPersonAttachmentToolInput(person_attachment_id=person_attachment_id)
        )

    @mcp.tool(
        name="followupboss_create_person_attachment",
        description="Create a Follow Up Boss person attachment record.",
    )
    async def followupboss_create_person_attachment(
        person_id: int,
        uri: str,
        file_name: str,
        *,
        file_size: int | None = None,
    ) -> dict[str, object]:
        return await adapter.create_person_attachment(
            CreatePersonAttachmentRequest(
                person_id=person_id,
                uri=uri,
                file_name=file_name,
                file_size=file_size,
            )
        )

    @mcp.tool(
        name="followupboss_update_person_attachment",
        description="Update a Follow Up Boss person attachment by ID.",
    )
    async def followupboss_update_person_attachment(
        person_attachment_id: int,
        person_id: int,
        uri: str,
        file_name: str,
        *,
        file_size: int | None = None,
    ) -> dict[str, object]:
        return await adapter.update_person_attachment(
            UpdatePersonAttachmentToolInput(
                person_attachment_id=person_attachment_id,
                person_id=person_id,
                uri=uri,
                file_name=file_name,
                file_size=file_size,
            )
        )

    @mcp.tool(
        name="followupboss_delete_person_attachment",
        description="Delete a Follow Up Boss person attachment by ID.",
    )
    async def followupboss_delete_person_attachment(person_attachment_id: int) -> dict[str, object]:
        return await adapter.delete_person_attachment(
            DeletePersonAttachmentToolInput(person_attachment_id=person_attachment_id)
        )

    @mcp.tool(
        name="followupboss_get_deal_attachment",
        description="Fetch a single Follow Up Boss deal attachment by ID.",
    )
    async def followupboss_get_deal_attachment(deal_attachment_id: int) -> dict[str, object]:
        return await adapter.get_deal_attachment(
            GetDealAttachmentToolInput(deal_attachment_id=deal_attachment_id)
        )

    @mcp.tool(
        name="followupboss_create_deal_attachment",
        description="Create a Follow Up Boss deal attachment record.",
    )
    async def followupboss_create_deal_attachment(
        deal_id: int,
        uri: str,
        file_name: str,
        *,
        file_size: int | None = None,
    ) -> dict[str, object]:
        return await adapter.create_deal_attachment(
            CreateDealAttachmentRequest(
                deal_id=deal_id,
                uri=uri,
                file_name=file_name,
                file_size=file_size,
            )
        )

    @mcp.tool(
        name="followupboss_update_deal_attachment",
        description="Update a Follow Up Boss deal attachment by ID.",
    )
    async def followupboss_update_deal_attachment(
        deal_attachment_id: int,
        deal_id: int,
        uri: str,
        file_name: str,
        *,
        file_size: int | None = None,
    ) -> dict[str, object]:
        return await adapter.update_deal_attachment(
            UpdateDealAttachmentToolInput(
                deal_attachment_id=deal_attachment_id,
                deal_id=deal_id,
                uri=uri,
                file_name=file_name,
                file_size=file_size,
            )
        )

    @mcp.tool(
        name="followupboss_delete_deal_attachment",
        description="Delete a Follow Up Boss deal attachment by ID.",
    )
    async def followupboss_delete_deal_attachment(deal_attachment_id: int) -> dict[str, object]:
        return await adapter.delete_deal_attachment(
            DeleteDealAttachmentToolInput(deal_attachment_id=deal_attachment_id)
        )


def _register_reaction_tools(mcp: FastMCP, adapter: FollowUpBossToolAdapter) -> None:
    """Register reaction-related MCP tools.

    Args:
        mcp: The FastMCP server instance.
        adapter: The typed Follow Up Boss tool adapter.
    """

    @mcp.tool(
        name="followupboss_get_reaction",
        description="Fetch a single Follow Up Boss reaction by ID.",
    )
    async def followupboss_get_reaction(reaction_id: int) -> dict[str, object]:
        return await adapter.get_reaction(GetReactionToolInput(reaction_id=reaction_id))

    @mcp.tool(
        name="followupboss_add_reaction",
        description="Add a Follow Up Boss reaction to a note, call, or threaded reply.",
    )
    async def followupboss_add_reaction(
        ref_type: ReactionRefType,
        ref_id: int,
        body: str,
    ) -> dict[str, object]:
        return await adapter.add_reaction(
            AddReactionToolInput(ref_type=ref_type, ref_id=ref_id, body=body)
        )

    @mcp.tool(
        name="followupboss_delete_reaction",
        description="Delete a Follow Up Boss reaction from a note, call, or threaded reply.",
    )
    async def followupboss_delete_reaction(
        ref_type: ReactionRefType,
        ref_id: int,
        *,
        emoji: str | None = None,
    ) -> dict[str, object]:
        return await adapter.delete_reaction(
            DeleteReactionToolInput(ref_type=ref_type, ref_id=ref_id, emoji=emoji)
        )


def _register_threaded_reply_tools(mcp: FastMCP, adapter: FollowUpBossToolAdapter) -> None:
    """Register threaded-reply-related MCP tools.

    Args:
        mcp: The FastMCP server instance.
        adapter: The typed Follow Up Boss tool adapter.
    """

    @mcp.tool(
        name="followupboss_get_threaded_reply",
        description="Fetch a single Follow Up Boss threaded reply by ID.",
    )
    async def followupboss_get_threaded_reply(threaded_reply_id: int) -> dict[str, object]:
        return await adapter.get_threaded_reply(
            GetThreadedReplyToolInput(threaded_reply_id=threaded_reply_id)
        )


def _register_event_tools(mcp: FastMCP, adapter: FollowUpBossToolAdapter) -> None:
    """Register event-related MCP tools.

    Args:
        mcp: The FastMCP server instance.
        adapter: The typed Follow Up Boss tool adapter.
    """

    @mcp.tool(
        name="followupboss_search_events",
        description="Search Follow Up Boss events with pagination metadata.",
    )
    async def followupboss_search_events(
        *,
        limit: int | None = None,
        next_token: str | None = None,
        offset: int | None = None,
        person_id: int | None = None,
        type: list[str] | None = None,
        has_property: bool | None = None,
        property_address: str | None = None,
    ) -> dict[str, object]:
        return await adapter.search_events(
            EventSearchRequest(
                limit=limit,
                next_token=next_token,
                offset=offset,
                person_id=person_id,
                type=type,
                has_property=has_property,
                property_address=property_address,
            )
        )

    @mcp.tool(
        name="followupboss_get_event",
        description="Fetch a single Follow Up Boss event by ID.",
    )
    async def followupboss_get_event(event_id: int) -> dict[str, object]:
        return await adapter.get_event(GetEventToolInput(event_id=event_id))

    @mcp.tool(
        name="followupboss_send_event",
        description=(
            "Send a canonical Follow Up Boss lead or lead-activity event through POST /events."
        ),
    )
    async def followupboss_send_event(
        source: str,
        system: str,
        type: str,
        person: dict[str, object],
        *,
        campaign: dict[str, object] | None = None,
        description: str | None = None,
        message: str | None = None,
        occurred_at: str | None = None,
        page_duration: int | None = None,
        page_referrer: str | None = None,
        page_title: str | None = None,
        page_url: str | None = None,
        property: dict[str, object] | None = None,
        property_search: dict[str, object] | None = None,
    ) -> dict[str, object]:
        tool_input = CreateEventRequest.model_validate(
            {
                "source": source,
                "system": system,
                "type": type,
                "person": person,
                "campaign": campaign,
                "description": description,
                "message": message,
                "occurred_at": occurred_at,
                "page_duration": page_duration,
                "page_referrer": page_referrer,
                "page_title": page_title,
                "page_url": page_url,
                "property": property,
                "property_search": property_search,
            }
        )
        return await adapter.send_event(tool_input)


def _register_email_marketing_tools(
    mcp: FastMCP,
    adapter: FollowUpBossToolAdapter,
) -> None:
    """Register email-marketing-related MCP tools.

    Args:
        mcp: The FastMCP server instance.
        adapter: The typed Follow Up Boss tool adapter.
    """

    @mcp.tool(
        name="followupboss_list_email_campaigns",
        description="List Follow Up Boss email marketing campaigns.",
    )
    async def followupboss_list_email_campaigns(
        *,
        origin: str | None = None,
        origin_id: str | None = None,
    ) -> dict[str, object]:
        return await adapter.list_email_campaigns(
            EmailCampaignListRequest(origin=origin, origin_id=origin_id)
        )

    @mcp.tool(
        name="followupboss_create_email_campaign",
        description="Create a Follow Up Boss email marketing campaign.",
    )
    async def followupboss_create_email_campaign(
        origin: str,
        origin_id: str,
        *,
        name: str | None = None,
        subject: str | None = None,
        body_html: str | None = None,
    ) -> dict[str, object]:
        return await adapter.create_email_campaign(
            CreateEmailCampaignRequest(
                origin=origin,
                origin_id=origin_id,
                name=name,
                subject=subject,
                body_html=body_html,
            )
        )

    @mcp.tool(
        name="followupboss_update_email_campaign",
        description="Update a Follow Up Boss email marketing campaign by ID.",
    )
    async def followupboss_update_email_campaign(
        email_campaign_id: int,
        *,
        name: str | None = None,
        subject: str | None = None,
        body_html: str | None = None,
    ) -> dict[str, object]:
        return await adapter.update_email_campaign(
            UpdateEmailCampaignToolInput(
                email_campaign_id=email_campaign_id,
                name=name,
                subject=subject,
                body_html=body_html,
            )
        )

    @mcp.tool(
        name="followupboss_list_email_events",
        description="List Follow Up Boss email marketing events.",
    )
    async def followupboss_list_email_events(
        *,
        type: EmailEventType | None = None,
        person_id: int | None = None,
        updated_after: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> dict[str, object]:
        return await adapter.list_email_events(
            EmailEventListRequest.model_validate(
                {
                    "type": type,
                    "person_id": person_id,
                    "updated_after": updated_after,
                    "limit": limit,
                    "offset": offset,
                }
            )
        )

    @mcp.tool(
        name="followupboss_send_email_events",
        description="Post batched Follow Up Boss email marketing events.",
    )
    async def followupboss_send_email_events(
        em_events: list[dict[str, object]],
    ) -> dict[str, object]:
        return await adapter.send_email_events(
            CreateEmailEventsBatchRequest.model_validate({"em_events": em_events})
        )


def _register_action_plan_tools(mcp: FastMCP, adapter: FollowUpBossToolAdapter) -> None:
    """Register action-plan-related MCP tools.

    Args:
        mcp: The FastMCP server instance.
        adapter: The typed Follow Up Boss tool adapter.
    """

    @mcp.tool(
        name="followupboss_list_action_plans",
        description=(
            "List Follow Up Boss action plans with documented filters and pagination metadata."
        ),
    )
    async def followupboss_list_action_plans(
        *,
        ids: list[int] | None = None,
        limit: int | None = None,
        names: list[str] | None = None,
        offset: int | None = None,
        sort: str | None = None,
        status: str | None = None,
    ) -> dict[str, object]:
        return await adapter.list_action_plans(
            ActionPlanListRequest(
                ids=ids,
                limit=limit,
                names=names,
                offset=offset,
                sort=sort,
                status=status,
            )
        )

    @mcp.tool(
        name="followupboss_list_action_plan_people",
        description="List Follow Up Boss action-plan-person relationships with documented filters.",
    )
    async def followupboss_list_action_plan_people(
        *,
        action_plan_id: int | None = None,
        limit: int | None = None,
        offset: int | None = None,
        person_id: int | None = None,
    ) -> dict[str, object]:
        return await adapter.list_action_plan_people(
            ActionPlanPersonListRequest(
                action_plan_id=action_plan_id,
                limit=limit,
                offset=offset,
                person_id=person_id,
            )
        )

    @mcp.tool(
        name="followupboss_apply_action_plan",
        description="Apply a Follow Up Boss action plan to a specific person.",
    )
    async def followupboss_apply_action_plan(
        action_plan_id: int,
        person_id: int,
    ) -> dict[str, object]:
        return await adapter.apply_action_plan(
            CreateActionPlanPersonRequest(
                action_plan_id=action_plan_id,
                person_id=person_id,
            )
        )

    @mcp.tool(
        name="followupboss_update_action_plan_person",
        description="Pause or resume a Follow Up Boss action-plan-person relationship by ID.",
    )
    async def followupboss_update_action_plan_person(
        action_plan_person_id: int,
        *,
        status: ActionPlanPersonStatus,
    ) -> dict[str, object]:
        return await adapter.update_action_plan_person(
            UpdateActionPlanPersonToolInput(
                action_plan_person_id=action_plan_person_id,
                status=status,
            )
        )


def _register_automation_tools(mcp: FastMCP, adapter: FollowUpBossToolAdapter) -> None:
    """Register automation-related MCP tools.

    Args:
        mcp: The FastMCP server instance.
        adapter: The typed Follow Up Boss tool adapter.
    """

    @mcp.tool(
        name="followupboss_list_automations",
        description=(
            "List Follow Up Boss automations with documented filters and pagination metadata."
        ),
    )
    async def followupboss_list_automations(
        *,
        enabled_only: bool | None = None,
        limit: int | None = None,
        manual_only: bool | None = None,
        next_token: str | None = None,
        offset: int | None = None,
        status: str | None = None,
    ) -> dict[str, object]:
        return await adapter.list_automations(
            AutomationListRequest(
                enabled_only=enabled_only,
                limit=limit,
                manual_only=manual_only,
                next_token=next_token,
                offset=offset,
                status=status,
            )
        )

    @mcp.tool(
        name="followupboss_get_automation",
        description="Fetch a single Follow Up Boss automation by ID.",
    )
    async def followupboss_get_automation(automation_id: int) -> dict[str, object]:
        return await adapter.get_automation(GetAutomationToolInput(automation_id=automation_id))

    @mcp.tool(
        name="followupboss_list_automation_people",
        description="List Follow Up Boss automation-person pairings with documented filters.",
    )
    async def followupboss_list_automation_people(
        *,
        automation_id: int | None = None,
        person_id: int | None = None,
        status: AutomationRunStatus | None = None,
    ) -> dict[str, object]:
        return await adapter.list_automation_people(
            AutomationPeopleListRequest(
                automation_id=automation_id,
                person_id=person_id,
                status=status,
            )
        )

    @mcp.tool(
        name="followupboss_get_automation_person",
        description="Fetch a single Follow Up Boss automation-person pairing by ID.",
    )
    async def followupboss_get_automation_person(automation_person_id: int) -> dict[str, object]:
        return await adapter.get_automation_person(
            GetAutomationPersonToolInput(automation_person_id=automation_person_id)
        )

    @mcp.tool(
        name="followupboss_trigger_automation",
        description="Trigger a Follow Up Boss automation for a specific person.",
    )
    async def followupboss_trigger_automation(
        automation_id: int,
        person_id: int,
    ) -> dict[str, object]:
        return await adapter.trigger_automation(
            CreateAutomationPersonRequest(
                automation_id=automation_id,
                person_id=person_id,
            )
        )

    @mcp.tool(
        name="followupboss_update_automation_person",
        description="Pause or resume a Follow Up Boss automation-person pairing by ID.",
    )
    async def followupboss_update_automation_person(
        automation_person_id: int,
        *,
        status: AutomationPauseStatus,
    ) -> dict[str, object]:
        return await adapter.update_automation_person(
            UpdateAutomationPersonToolInput(
                automation_person_id=automation_person_id,
                status=status,
            )
        )


def _register_group_tools(mcp: FastMCP, adapter: FollowUpBossToolAdapter) -> None:
    """Register group-related MCP tools.

    Args:
        mcp: The FastMCP server instance.
        adapter: The typed Follow Up Boss tool adapter.
    """

    @mcp.tool(
        name="followupboss_list_groups",
        description="List Follow Up Boss groups with documented filters and pagination metadata.",
    )
    async def followupboss_list_groups(
        *,
        sort: str | None = None,
        type: str | None = None,
    ) -> dict[str, object]:
        return await adapter.list_groups(GroupListRequest(sort=sort, type=type))

    @mcp.tool(
        name="followupboss_list_round_robin_groups",
        description="List Follow Up Boss groups including round-robin assignment details.",
    )
    async def followupboss_list_round_robin_groups(
        *,
        sort: str | None = None,
        type: str | None = None,
    ) -> dict[str, object]:
        return await adapter.list_round_robin_groups(GroupListRequest(sort=sort, type=type))

    @mcp.tool(
        name="followupboss_get_group",
        description="Fetch a single Follow Up Boss group by ID.",
    )
    async def followupboss_get_group(group_id: int) -> dict[str, object]:
        return await adapter.get_group(GetGroupToolInput(group_id=group_id))

    @mcp.tool(
        name="followupboss_create_group",
        description="Create a Follow Up Boss group.",
    )
    async def followupboss_create_group(
        name: str,
        users: list[int],
        *,
        claim_window: int | None = None,
        default_group_id: int | None = None,
        default_pond_id: int | None = None,
        default_user_id: int | None = None,
        distribution: str | None = None,
        type: str | None = None,
    ) -> dict[str, object]:
        return await adapter.create_group(
            CreateGroupRequest(
                name=name,
                users=users,
                claim_window=claim_window,
                default_group_id=default_group_id,
                default_pond_id=default_pond_id,
                default_user_id=default_user_id,
                distribution=distribution,
                type=type,
            )
        )

    @mcp.tool(
        name="followupboss_update_group",
        description="Update a Follow Up Boss group by ID.",
    )
    async def followupboss_update_group(
        group_id: int,
        *,
        claim_window: int | None = None,
        default_group_id: int | None = None,
        default_pond_id: int | None = None,
        default_user_id: int | None = None,
        distribution: str | None = None,
        name: str | None = None,
        type: str | None = None,
        users: list[int] | None = None,
    ) -> dict[str, object]:
        return await adapter.update_group(
            UpdateGroupToolInput(
                group_id=group_id,
                claim_window=claim_window,
                default_group_id=default_group_id,
                default_pond_id=default_pond_id,
                default_user_id=default_user_id,
                distribution=distribution,
                name=name,
                type=type,
                users=users,
            )
        )

    @mcp.tool(
        name="followupboss_delete_group",
        description="Delete a Follow Up Boss group by ID.",
    )
    async def followupboss_delete_group(group_id: int) -> dict[str, object]:
        return await adapter.delete_group(DeleteGroupToolInput(group_id=group_id))


def _register_inbox_app_tools(mcp: FastMCP, adapter: FollowUpBossToolAdapter) -> None:
    """Register inbox-app-related MCP tools.

    Args:
        mcp: The FastMCP server instance.
        adapter: The typed Follow Up Boss tool adapter.
    """

    @mcp.tool(
        name="followupboss_list_inbox_app_installations",
        description=(
            "List installed Follow Up Boss inbox app installations for a published inbox app."
        ),
    )
    async def followupboss_list_inbox_app_installations(
        published_inbox_app_id: int,
    ) -> dict[str, object]:
        return await adapter.list_inbox_app_installations(
            ListInboxAppInstallationsToolInput(published_inbox_app_id=published_inbox_app_id)
        )

    @mcp.tool(
        name="followupboss_install_inbox_app",
        description="Install a Follow Up Boss inbox app for an account or user scope.",
    )
    async def followupboss_install_inbox_app(
        published_inbox_app_id: int,
        user_id: int,
        subscription_url: str,
    ) -> dict[str, object]:
        return await adapter.install_inbox_app(
            InstallInboxAppRequest(
                published_inbox_app_id=published_inbox_app_id,
                user_id=user_id,
                subscription_url=subscription_url,
            )
        )

    @mcp.tool(
        name="followupboss_deactivate_inbox_app",
        description="Deactivate a Follow Up Boss inbox app installation by ID.",
    )
    async def followupboss_deactivate_inbox_app(inbox_app_id: int) -> dict[str, object]:
        return await adapter.deactivate_inbox_app(
            DeactivateInboxAppToolInput(inbox_app_id=inbox_app_id)
        )

    @mcp.tool(
        name="followupboss_add_inbox_app_message",
        description="Add a message to a Follow Up Boss inbox app conversation.",
    )
    async def followupboss_add_inbox_app_message(
        inbox_app_id: int,
        external_conversation_id: str,
        external_message_id: str,
        message: str,
        is_incoming: bool,
        sender: dict[str, object],
        *,
        attachments: list[dict[str, object]] | None = None,
        delivery_status: InboxAppMessageDeliveryStatus | None = None,
        delivery_status_error_message: str | None = None,
        is_automation: bool | None = None,
        owner: dict[str, object] | None = None,
        person: dict[str, object] | None = None,
        rich_objects: list[str] | None = None,
        sent_at: str | None = None,
        subject: str | None = None,
    ) -> dict[str, object]:
        return await adapter.add_inbox_app_message(
            AddInboxAppMessageToolInput.model_validate(
                {
                    "inbox_app_id": inbox_app_id,
                    "external_conversation_id": external_conversation_id,
                    "external_message_id": external_message_id,
                    "message": message,
                    "is_incoming": is_incoming,
                    "sender": sender,
                    "attachments": attachments,
                    "delivery_status": delivery_status,
                    "delivery_status_error_message": delivery_status_error_message,
                    "is_automation": is_automation,
                    "owner": owner,
                    "person": person,
                    "rich_objects": rich_objects,
                    "sent_at": sent_at,
                    "subject": subject,
                }
            )
        )

    @mcp.tool(
        name="followupboss_add_inbox_app_note",
        description="Add a note to a Follow Up Boss inbox app conversation.",
    )
    async def followupboss_add_inbox_app_note(
        inbox_app_id: int,
        external_conversation_id: str,
        body: str,
        user: dict[str, object],
    ) -> dict[str, object]:
        return await adapter.add_inbox_app_note(
            AddInboxAppNoteToolInput.model_validate(
                {
                    "inbox_app_id": inbox_app_id,
                    "external_conversation_id": external_conversation_id,
                    "body": body,
                    "user": user,
                }
            )
        )

    @mcp.tool(
        name="followupboss_list_inbox_app_participants",
        description="List participants in a Follow Up Boss inbox app conversation.",
    )
    async def followupboss_list_inbox_app_participants(
        inbox_app_id: int,
        ext_conversation_id: str,
    ) -> dict[str, object]:
        return await adapter.list_inbox_app_participants(
            ListInboxAppParticipantsToolInput(
                inbox_app_id=inbox_app_id,
                ext_conversation_id=ext_conversation_id,
            )
        )

    @mcp.tool(
        name="followupboss_add_inbox_app_participant",
        description="Add a participant to a Follow Up Boss inbox app conversation.",
    )
    async def followupboss_add_inbox_app_participant(
        inbox_app_id: int,
        ext_conversation_id: str,
        *,
        person_id: int | None = None,
        user_id: int | None = None,
        relationship_id: int | None = None,
        name: str | None = None,
        email: str | None = None,
        phone: str | None = None,
        is_automation: bool | None = None,
    ) -> dict[str, object]:
        return await adapter.add_inbox_app_participant(
            AddInboxAppParticipantToolInput(
                inbox_app_id=inbox_app_id,
                ext_conversation_id=ext_conversation_id,
                person_id=person_id,
                user_id=user_id,
                relationship_id=relationship_id,
                name=name,
                email=email,
                phone=phone,
                is_automation=is_automation,
            )
        )

    @mcp.tool(
        name="followupboss_update_inbox_app_conversation",
        description="Update a Follow Up Boss inbox app conversation by external conversation ID.",
    )
    async def followupboss_update_inbox_app_conversation(
        inbox_app_id: int,
        ext_conversation_id: str,
        *,
        archived: bool | None = None,
        assigned_inbox_id: int | None = None,
        assigned_user_id: int | None = None,
        permanently_archived: bool | None = None,
        person: dict[str, object] | None = None,
        subject: str | None = None,
    ) -> dict[str, object]:
        return await adapter.update_inbox_app_conversation(
            UpdateInboxAppConversationToolInput.model_validate(
                {
                    "inbox_app_id": inbox_app_id,
                    "ext_conversation_id": ext_conversation_id,
                    "archived": archived,
                    "assigned_inbox_id": assigned_inbox_id,
                    "assigned_user_id": assigned_user_id,
                    "permanently_archived": permanently_archived,
                    "person": person,
                    "subject": subject,
                }
            )
        )

    @mcp.tool(
        name="followupboss_update_inbox_app_message",
        description="Update a Follow Up Boss inbox app message by ID or external message ID.",
    )
    async def followupboss_update_inbox_app_message(
        inbox_app_id: int,
        *,
        id: int | None = None,
        external_message_id: str | None = None,
        delivery_status: InboxAppMessageDeliveryStatus | None = None,
        delivery_status_error_message: str | None = None,
    ) -> dict[str, object]:
        return await adapter.update_inbox_app_message(
            UpdateInboxAppMessageToolInput.model_validate(
                {
                    "inbox_app_id": inbox_app_id,
                    "id": id,
                    "external_message_id": external_message_id,
                    "delivery_status": delivery_status,
                    "delivery_status_error_message": delivery_status_error_message,
                }
            )
        )

    @mcp.tool(
        name="followupboss_remove_inbox_app_participant",
        description="Remove a participant from a Follow Up Boss inbox app conversation.",
    )
    async def followupboss_remove_inbox_app_participant(
        inbox_app_id: int,
        ext_conversation_id: str,
        participant_id: int,
    ) -> dict[str, object]:
        return await adapter.remove_inbox_app_participant(
            DeleteInboxAppParticipantToolInput(
                inbox_app_id=inbox_app_id,
                ext_conversation_id=ext_conversation_id,
                participant_id=participant_id,
            )
        )


def _register_user_tools(mcp: FastMCP, adapter: FollowUpBossToolAdapter) -> None:
    """Register user-related MCP tools.

    Args:
        mcp: The FastMCP server instance.
        adapter: The typed Follow Up Boss tool adapter.
    """

    @mcp.tool(
        name="followupboss_list_users",
        description="List Follow Up Boss users with pagination metadata.",
    )
    async def followupboss_list_users(
        *,
        fields: list[str] | None = None,
        id: int | None = None,
        ids: list[int] | None = None,
        id_greater_than: int | None = None,
        id_less_than: int | None = None,
        limit: int | None = None,
        next_token: str | None = None,
        offset: int | None = None,
        sort: str | None = None,
        email: str | None = None,
        include_deleted: bool | None = None,
        name: str | None = None,
        role: str | None = None,
    ) -> dict[str, object]:
        return await adapter.list_users(
            UserListRequest(
                fields=fields,
                id=id,
                ids=ids,
                id_greater_than=id_greater_than,
                id_less_than=id_less_than,
                limit=limit,
                next_token=next_token,
                offset=offset,
                sort=sort,
                email=email,
                include_deleted=include_deleted,
                name=name,
                role=role,
            )
        )

    @mcp.tool(
        name="followupboss_get_user",
        description="Fetch a single Follow Up Boss user by ID.",
    )
    async def followupboss_get_user(user_id: int) -> dict[str, object]:
        return await adapter.get_user(GetUserToolInput(user_id=user_id))


def _register_appointment_metadata_tools(
    mcp: FastMCP,
    adapter: FollowUpBossToolAdapter,
) -> None:
    """Register appointment outcome and appointment type MCP tools.

    Args:
        mcp: The FastMCP server instance.
        adapter: The typed Follow Up Boss tool adapter.
    """

    @mcp.tool(
        name="followupboss_list_appointment_outcomes",
        description="List Follow Up Boss appointment outcomes with pagination metadata.",
    )
    async def followupboss_list_appointment_outcomes(
        *,
        limit: int | None = None,
        offset: int | None = None,
        sort: str | None = None,
    ) -> dict[str, object]:
        return await adapter.list_appointment_outcomes(
            AppointmentOutcomeListRequest(limit=limit, offset=offset, sort=sort)
        )

    @mcp.tool(
        name="followupboss_get_appointment_outcome",
        description="Fetch a single Follow Up Boss appointment outcome by ID.",
    )
    async def followupboss_get_appointment_outcome(
        appointment_outcome_id: int,
    ) -> dict[str, object]:
        return await adapter.get_appointment_outcome(
            GetAppointmentOutcomeToolInput(appointment_outcome_id=appointment_outcome_id)
        )

    @mcp.tool(
        name="followupboss_create_appointment_outcome",
        description="Create a Follow Up Boss appointment outcome.",
    )
    async def followupboss_create_appointment_outcome(
        name: str,
        *,
        order_weight: int | None = None,
    ) -> dict[str, object]:
        return await adapter.create_appointment_outcome(
            CreateAppointmentOutcomeRequest(name=name, order_weight=order_weight)
        )

    @mcp.tool(
        name="followupboss_update_appointment_outcome",
        description="Update a Follow Up Boss appointment outcome by ID.",
    )
    async def followupboss_update_appointment_outcome(
        appointment_outcome_id: int,
        *,
        name: str | None = None,
        order_weight: int | None = None,
    ) -> dict[str, object]:
        return await adapter.update_appointment_outcome(
            UpdateAppointmentOutcomeToolInput(
                appointment_outcome_id=appointment_outcome_id,
                name=name,
                order_weight=order_weight,
            )
        )

    @mcp.tool(
        name="followupboss_delete_appointment_outcome",
        description="Delete a Follow Up Boss appointment outcome by ID and reassign appointments.",
    )
    async def followupboss_delete_appointment_outcome(
        appointment_outcome_id: int,
        assign_outcome_id: int,
    ) -> dict[str, object]:
        return await adapter.delete_appointment_outcome(
            DeleteAppointmentOutcomeToolInput(
                appointment_outcome_id=appointment_outcome_id,
                assign_outcome_id=assign_outcome_id,
            )
        )

    @mcp.tool(
        name="followupboss_list_appointment_types",
        description="List Follow Up Boss appointment types with pagination metadata.",
    )
    async def followupboss_list_appointment_types(
        *,
        limit: int | None = None,
        offset: int | None = None,
        sort: str | None = None,
    ) -> dict[str, object]:
        return await adapter.list_appointment_types(
            AppointmentTypeListRequest(limit=limit, offset=offset, sort=sort)
        )

    @mcp.tool(
        name="followupboss_get_appointment_type",
        description="Fetch a single Follow Up Boss appointment type by ID.",
    )
    async def followupboss_get_appointment_type(
        appointment_type_id: int,
    ) -> dict[str, object]:
        return await adapter.get_appointment_type(
            GetAppointmentTypeToolInput(appointment_type_id=appointment_type_id)
        )

    @mcp.tool(
        name="followupboss_create_appointment_type",
        description="Create a Follow Up Boss appointment type.",
    )
    async def followupboss_create_appointment_type(
        name: str,
        *,
        order_weight: int | None = None,
    ) -> dict[str, object]:
        return await adapter.create_appointment_type(
            CreateAppointmentTypeRequest(name=name, order_weight=order_weight)
        )

    @mcp.tool(
        name="followupboss_update_appointment_type",
        description="Update a Follow Up Boss appointment type by ID.",
    )
    async def followupboss_update_appointment_type(
        appointment_type_id: int,
        *,
        name: str | None = None,
        order_weight: int | None = None,
    ) -> dict[str, object]:
        return await adapter.update_appointment_type(
            UpdateAppointmentTypeToolInput(
                appointment_type_id=appointment_type_id,
                name=name,
                order_weight=order_weight,
            )
        )

    @mcp.tool(
        name="followupboss_delete_appointment_type",
        description="Delete a Follow Up Boss appointment type by ID and reassign appointments.",
    )
    async def followupboss_delete_appointment_type(
        appointment_type_id: int,
        assign_type_id: int,
    ) -> dict[str, object]:
        return await adapter.delete_appointment_type(
            DeleteAppointmentTypeToolInput(
                appointment_type_id=appointment_type_id,
                assign_type_id=assign_type_id,
            )
        )


def _register_custom_field_tools(mcp: FastMCP, adapter: FollowUpBossToolAdapter) -> None:
    """Register custom-field-related MCP tools.

    Args:
        mcp: The FastMCP server instance.
        adapter: The typed Follow Up Boss tool adapter.
    """

    @mcp.tool(
        name="followupboss_list_custom_fields",
        description="List custom fields for the authenticated Follow Up Boss account.",
    )
    async def followupboss_list_custom_fields(
        *,
        fields: list[str] | None = None,
        id: int | None = None,
        ids: list[int] | None = None,
        id_greater_than: int | None = None,
        id_less_than: int | None = None,
        label: str | None = None,
        limit: int | None = None,
        next_token: str | None = None,
        offset: int | None = None,
        sort: str | None = None,
    ) -> dict[str, object]:
        return await adapter.list_custom_fields(
            CustomFieldListRequest(
                fields=fields,
                id=id,
                ids=ids,
                id_greater_than=id_greater_than,
                id_less_than=id_less_than,
                label=label,
                limit=limit,
                next_token=next_token,
                offset=offset,
                sort=sort,
            )
        )

    @mcp.tool(
        name="followupboss_get_custom_field",
        description="Fetch a single Follow Up Boss custom field by ID.",
    )
    async def followupboss_get_custom_field(custom_field_id: int) -> dict[str, object]:
        return await adapter.get_custom_field(
            GetCustomFieldToolInput(custom_field_id=custom_field_id)
        )

    @mcp.tool(
        name="followupboss_create_custom_field",
        description="Create a Follow Up Boss custom field.",
    )
    async def followupboss_create_custom_field(
        label: str,
        type: CustomFieldType,
        *,
        choices: list[str] | None = None,
        hide_if_empty: bool | None = None,
        is_recurring: bool | None = None,
        order_weight: int | None = None,
    ) -> dict[str, object]:
        return await adapter.create_custom_field(
            CreateCustomFieldRequest(
                label=label,
                type=type,
                choices=choices,
                hide_if_empty=hide_if_empty,
                is_recurring=is_recurring,
                order_weight=order_weight,
            )
        )

    @mcp.tool(
        name="followupboss_update_custom_field",
        description="Update a Follow Up Boss custom field by ID.",
    )
    async def followupboss_update_custom_field(
        custom_field_id: int,
        *,
        choices: list[str] | None = None,
        dropdown_choice_map: dict[str, int] | list[int] | None = None,
        hide_if_empty: bool | None = None,
        is_recurring: bool | None = None,
        label: str | None = None,
        order_weight: int | None = None,
    ) -> dict[str, object]:
        return await adapter.update_custom_field(
            UpdateCustomFieldToolInput.model_validate(
                {
                    "custom_field_id": custom_field_id,
                    "choices": choices,
                    "dropdown_choice_map": dropdown_choice_map,
                    "hide_if_empty": hide_if_empty,
                    "is_recurring": is_recurring,
                    "label": label,
                    "order_weight": order_weight,
                }
            )
        )

    @mcp.tool(
        name="followupboss_delete_custom_field",
        description="Delete a Follow Up Boss custom field by ID.",
    )
    async def followupboss_delete_custom_field(custom_field_id: int) -> dict[str, object]:
        return await adapter.delete_custom_field(
            DeleteCustomFieldToolInput(custom_field_id=custom_field_id)
        )


def _register_deal_tools(mcp: FastMCP, adapter: FollowUpBossToolAdapter) -> None:
    """Register deal-related MCP tools.

    Args:
        mcp: The FastMCP server instance.
        adapter: The typed Follow Up Boss tool adapter.
    """

    @mcp.tool(
        name="followupboss_list_deals",
        description="List Follow Up Boss deals with documented filters and pagination metadata.",
    )
    async def followupboss_list_deals(
        *,
        include_archived: bool | None = None,
        include_deleted: bool | None = None,
        person_id: int | None = None,
        pipeline_id: int | None = None,
        status: str | None = None,
        user_id: int | None = None,
    ) -> dict[str, object]:
        return await adapter.list_deals(
            DealListRequest(
                include_archived=include_archived,
                include_deleted=include_deleted,
                person_id=person_id,
                pipeline_id=pipeline_id,
                status=status,
                user_id=user_id,
            )
        )

    @mcp.tool(
        name="followupboss_get_deal",
        description="Fetch a single Follow Up Boss deal by ID.",
    )
    async def followupboss_get_deal(deal_id: int) -> dict[str, object]:
        return await adapter.get_deal(GetDealToolInput(deal_id=deal_id))

    @mcp.tool(
        name="followupboss_create_deal",
        description="Create a Follow Up Boss deal.",
    )
    async def followupboss_create_deal(
        name: str,
        stage_id: int,
        *,
        agent_commission: int | None = None,
        commission_value: int | None = None,
        custom_fields: dict[str, object] | None = None,
        description: str | None = None,
        due_diligence_date: str | None = None,
        earnest_money_due_date: str | None = None,
        final_walk_through_date: str | None = None,
        mutual_acceptance_date: str | None = None,
        order_weight: int | None = None,
        people_ids: list[int] | None = None,
        possession_date: str | None = None,
        price: int | None = None,
        projected_close_date: str | None = None,
        team_commission: int | None = None,
        user_ids: list[int] | None = None,
    ) -> dict[str, object]:
        return await adapter.create_deal(
            CreateDealRequest.model_validate(
                {
                    "name": name,
                    "stage_id": stage_id,
                    "agent_commission": agent_commission,
                    "commission_value": commission_value,
                    "custom_fields": custom_fields,
                    "description": description,
                    "due_diligence_date": due_diligence_date,
                    "earnest_money_due_date": earnest_money_due_date,
                    "final_walk_through_date": final_walk_through_date,
                    "mutual_acceptance_date": mutual_acceptance_date,
                    "order_weight": order_weight,
                    "people_ids": people_ids,
                    "possession_date": possession_date,
                    "price": price,
                    "projected_close_date": projected_close_date,
                    "team_commission": team_commission,
                    "user_ids": user_ids,
                }
            )
        )

    @mcp.tool(
        name="followupboss_update_deal",
        description="Update a Follow Up Boss deal by ID.",
    )
    async def followupboss_update_deal(
        deal_id: int,
        *,
        agent_commission: int | None = None,
        commission_value: int | None = None,
        custom_fields: dict[str, object] | None = None,
        description: str | None = None,
        due_diligence_date: str | None = None,
        earnest_money_due_date: str | None = None,
        final_walk_through_date: str | None = None,
        mutual_acceptance_date: str | None = None,
        name: str | None = None,
        people_ids: list[int] | None = None,
        possession_date: str | None = None,
        price: int | None = None,
        projected_close_date: str | None = None,
        stage_id: int | None = None,
        team_commission: int | None = None,
        user_ids: list[int] | None = None,
    ) -> dict[str, object]:
        return await adapter.update_deal(
            UpdateDealToolInput.model_validate(
                {
                    "deal_id": deal_id,
                    "agent_commission": agent_commission,
                    "commission_value": commission_value,
                    "custom_fields": custom_fields,
                    "description": description,
                    "due_diligence_date": due_diligence_date,
                    "earnest_money_due_date": earnest_money_due_date,
                    "final_walk_through_date": final_walk_through_date,
                    "mutual_acceptance_date": mutual_acceptance_date,
                    "name": name,
                    "people_ids": people_ids,
                    "possession_date": possession_date,
                    "price": price,
                    "projected_close_date": projected_close_date,
                    "stage_id": stage_id,
                    "team_commission": team_commission,
                    "user_ids": user_ids,
                }
            )
        )

    @mcp.tool(
        name="followupboss_delete_deal",
        description="Delete a Follow Up Boss deal by ID.",
    )
    async def followupboss_delete_deal(deal_id: int) -> dict[str, object]:
        return await adapter.delete_deal(DeleteDealToolInput(deal_id=deal_id))

    @mcp.tool(
        name="followupboss_list_deal_custom_fields",
        description="List Follow Up Boss deal custom fields with pagination metadata.",
    )
    async def followupboss_list_deal_custom_fields(
        *,
        label: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
        sort: str | None = None,
    ) -> dict[str, object]:
        return await adapter.list_deal_custom_fields(
            DealCustomFieldListRequest(
                label=label,
                limit=limit,
                offset=offset,
                sort=sort,
            )
        )

    @mcp.tool(
        name="followupboss_get_deal_custom_field",
        description="Fetch a single Follow Up Boss deal custom field by ID.",
    )
    async def followupboss_get_deal_custom_field(deal_custom_field_id: int) -> dict[str, object]:
        return await adapter.get_deal_custom_field(
            GetDealCustomFieldToolInput(deal_custom_field_id=deal_custom_field_id)
        )

    @mcp.tool(
        name="followupboss_create_deal_custom_field",
        description="Create a Follow Up Boss deal custom field.",
    )
    async def followupboss_create_deal_custom_field(
        label: str,
        type: CustomFieldType,
        *,
        choices: list[str] | None = None,
        hide_if_empty: bool | None = None,
        is_recurring: bool | None = None,
        order_weight: int | None = None,
        read_only: bool | None = None,
    ) -> dict[str, object]:
        return await adapter.create_deal_custom_field(
            CreateDealCustomFieldRequest.model_validate(
                {
                    "label": label,
                    "type": type,
                    "choices": choices,
                    "hide_if_empty": hide_if_empty,
                    "is_recurring": is_recurring,
                    "order_weight": order_weight,
                    "read_only": read_only,
                }
            )
        )

    @mcp.tool(
        name="followupboss_update_deal_custom_field",
        description="Update a Follow Up Boss deal custom field by ID.",
    )
    async def followupboss_update_deal_custom_field(
        deal_custom_field_id: int,
        *,
        choices: list[str] | None = None,
        dropdown_choice_map: dict[str, int] | list[int] | None = None,
        hide_if_empty: bool | None = None,
        is_recurring: bool | None = None,
        label: str | None = None,
        order_weight: int | None = None,
        read_only: bool | None = None,
        type: CustomFieldType | None = None,
    ) -> dict[str, object]:
        return await adapter.update_deal_custom_field(
            UpdateDealCustomFieldToolInput.model_validate(
                {
                    "deal_custom_field_id": deal_custom_field_id,
                    "choices": choices,
                    "dropdown_choice_map": dropdown_choice_map,
                    "hide_if_empty": hide_if_empty,
                    "is_recurring": is_recurring,
                    "label": label,
                    "order_weight": order_weight,
                    "read_only": read_only,
                    "type": type,
                }
            )
        )

    @mcp.tool(
        name="followupboss_delete_deal_custom_field",
        description="Delete a Follow Up Boss deal custom field by ID.",
    )
    async def followupboss_delete_deal_custom_field(deal_custom_field_id: int) -> dict[str, object]:
        return await adapter.delete_deal_custom_field(
            DeleteDealCustomFieldToolInput(deal_custom_field_id=deal_custom_field_id)
        )


def _register_appointment_tools(mcp: FastMCP, adapter: FollowUpBossToolAdapter) -> None:
    """Register appointment-related MCP tools.

    Args:
        mcp: The FastMCP server instance.
        adapter: The typed Follow Up Boss tool adapter.
    """

    @mcp.tool(
        name="followupboss_list_appointments",
        description=(
            "List Follow Up Boss appointments with documented filters and pagination metadata."
        ),
    )
    async def followupboss_list_appointments(
        *,
        end: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
        person_id: int | list[int] | None = None,
        start: str | None = None,
        user_id: int | None = None,
    ) -> dict[str, object]:
        return await adapter.list_appointments(
            AppointmentListRequest.model_validate(
                {
                    "end": end,
                    "limit": limit,
                    "offset": offset,
                    "person_id": person_id,
                    "start": start,
                    "user_id": user_id,
                }
            )
        )

    @mcp.tool(
        name="followupboss_get_appointment",
        description="Fetch a single Follow Up Boss appointment by ID.",
    )
    async def followupboss_get_appointment(appointment_id: int) -> dict[str, object]:
        return await adapter.get_appointment(GetAppointmentToolInput(appointment_id=appointment_id))

    @mcp.tool(
        name="followupboss_create_appointment",
        description="Create a Follow Up Boss appointment.",
    )
    async def followupboss_create_appointment(
        title: str,
        start: str,
        end: str,
        *,
        all_day: bool | None = None,
        created_by_id: int | None = None,
        description: str | None = None,
        invitees: list[dict[str, object]] | None = None,
        location: str | None = None,
        outcome_id: int | None = None,
        send_invitation: bool | None = None,
        type_id: int | None = None,
    ) -> dict[str, object]:
        return await adapter.create_appointment(
            CreateAppointmentRequest.model_validate(
                {
                    "title": title,
                    "start": start,
                    "end": end,
                    "all_day": all_day,
                    "created_by_id": created_by_id,
                    "description": description,
                    "invitees": invitees,
                    "location": location,
                    "outcome_id": outcome_id,
                    "send_invitation": send_invitation,
                    "type_id": type_id,
                }
            )
        )

    @mcp.tool(
        name="followupboss_update_appointment",
        description="Update a Follow Up Boss appointment by ID.",
    )
    async def followupboss_update_appointment(
        appointment_id: int,
        *,
        title: str,
        start: str,
        end: str,
        all_day: bool | None = None,
        description: str | None = None,
        invitees: list[dict[str, object]] | None = None,
        location: str | None = None,
        outcome_id: int | None = None,
        send_invitation: bool | None = None,
        type_id: int | None = None,
    ) -> dict[str, object]:
        return await adapter.update_appointment(
            UpdateAppointmentToolInput.model_validate(
                {
                    "appointment_id": appointment_id,
                    "title": title,
                    "start": start,
                    "end": end,
                    "all_day": all_day,
                    "description": description,
                    "invitees": invitees,
                    "location": location,
                    "outcome_id": outcome_id,
                    "send_invitation": send_invitation,
                    "type_id": type_id,
                }
            )
        )

    @mcp.tool(
        name="followupboss_delete_appointment",
        description="Delete a Follow Up Boss appointment by ID.",
    )
    async def followupboss_delete_appointment(appointment_id: int) -> dict[str, object]:
        return await adapter.delete_appointment(
            DeleteAppointmentToolInput(appointment_id=appointment_id)
        )


def _register_call_tools(mcp: FastMCP, adapter: FollowUpBossToolAdapter) -> None:
    """Register call-related MCP tools.

    Args:
        mcp: The FastMCP server instance.
        adapter: The typed Follow Up Boss tool adapter.
    """

    @mcp.tool(
        name="followupboss_list_calls",
        description="List Follow Up Boss calls with documented filters and pagination metadata.",
    )
    async def followupboss_list_calls(
        *,
        from_number: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
        person_id: int | None = None,
        phone: str | None = None,
        to_number: str | None = None,
    ) -> dict[str, object]:
        return await adapter.list_calls(
            CallListRequest(
                from_number=from_number,
                limit=limit,
                offset=offset,
                person_id=person_id,
                phone=phone,
                to_number=to_number,
            )
        )

    @mcp.tool(
        name="followupboss_get_call",
        description="Fetch a single Follow Up Boss call by ID.",
    )
    async def followupboss_get_call(call_id: int) -> dict[str, object]:
        return await adapter.get_call(GetCallToolInput(call_id=call_id))

    @mcp.tool(
        name="followupboss_create_call",
        description="Create a Follow Up Boss call log entry.",
    )
    async def followupboss_create_call(
        person_id: int,
        phone: str,
        is_incoming: bool,
        *,
        duration: int | None = None,
        from_number: str | None = None,
        note: str | None = None,
        outcome: str | None = None,
        recording_url: str | None = None,
        to_number: str | None = None,
        user_id: int | None = None,
    ) -> dict[str, object]:
        return await adapter.create_call(
            CreateCallRequest(
                person_id=person_id,
                phone=phone,
                is_incoming=is_incoming,
                duration=duration,
                from_number=from_number,
                note=note,
                outcome=outcome,
                recording_url=recording_url,
                to_number=to_number,
                user_id=user_id,
            )
        )

    @mcp.tool(
        name="followupboss_update_call",
        description="Update a Follow Up Boss call log entry by ID.",
    )
    async def followupboss_update_call(
        call_id: int,
        *,
        duration: int | None = None,
        from_number: str | None = None,
        is_incoming: bool | None = None,
        note: str | None = None,
        outcome: str | None = None,
        person_id: int | None = None,
        phone: str | None = None,
        recording_url: str | None = None,
        to_number: str | None = None,
        user_id: int | None = None,
    ) -> dict[str, object]:
        return await adapter.update_call(
            UpdateCallToolInput(
                call_id=call_id,
                duration=duration,
                from_number=from_number,
                is_incoming=is_incoming,
                note=note,
                outcome=outcome,
                person_id=person_id,
                phone=phone,
                recording_url=recording_url,
                to_number=to_number,
                user_id=user_id,
            )
        )


def _register_pipeline_tools(mcp: FastMCP, adapter: FollowUpBossToolAdapter) -> None:
    """Register pipeline-related MCP tools.

    Args:
        mcp: The FastMCP server instance.
        adapter: The typed Follow Up Boss tool adapter.
    """

    @mcp.tool(
        name="followupboss_list_pipelines",
        description=(
            "List Follow Up Boss pipelines with exact-name filtering and pagination metadata."
        ),
    )
    async def followupboss_list_pipelines(*, name: str | None = None) -> dict[str, object]:
        return await adapter.list_pipelines(PipelineListRequest(name=name))

    @mcp.tool(
        name="followupboss_get_pipeline",
        description="Fetch a single Follow Up Boss pipeline by ID.",
    )
    async def followupboss_get_pipeline(pipeline_id: int) -> dict[str, object]:
        return await adapter.get_pipeline(GetPipelineToolInput(pipeline_id=pipeline_id))

    @mcp.tool(
        name="followupboss_create_pipeline",
        description="Create a Follow Up Boss pipeline. Owner permissions are required upstream.",
    )
    async def followupboss_create_pipeline(
        name: str,
        *,
        description: str | None = None,
        order_weight: int | None = None,
        stages: list[dict[str, object]] | None = None,
    ) -> dict[str, object]:
        stage_inputs = (
            [PipelineStageInput.model_validate(stage) for stage in stages]
            if stages is not None
            else None
        )
        return await adapter.create_pipeline(
            CreatePipelineRequest(
                name=name,
                description=description,
                order_weight=order_weight,
                stages=stage_inputs,
            )
        )

    @mcp.tool(
        name="followupboss_update_pipeline",
        description=(
            "Update a Follow Up Boss pipeline by ID. Owner permissions are required upstream."
        ),
    )
    async def followupboss_update_pipeline(
        pipeline_id: int,
        *,
        description: str | None = None,
        name: str | None = None,
        order_weight: int | None = None,
        stages: list[dict[str, object]] | None = None,
    ) -> dict[str, object]:
        stage_inputs = (
            [PipelineStageInput.model_validate(stage) for stage in stages]
            if stages is not None
            else None
        )
        return await adapter.update_pipeline(
            UpdatePipelineToolInput(
                pipeline_id=pipeline_id,
                name=name,
                description=description,
                order_weight=order_weight,
                stages=stage_inputs,
            )
        )

    @mcp.tool(
        name="followupboss_delete_pipeline",
        description=(
            "Delete a Follow Up Boss pipeline by ID. Owner permissions are required upstream."
        ),
    )
    async def followupboss_delete_pipeline(pipeline_id: int) -> dict[str, object]:
        return await adapter.delete_pipeline(DeletePipelineToolInput(pipeline_id=pipeline_id))


def _register_pond_tools(mcp: FastMCP, adapter: FollowUpBossToolAdapter) -> None:
    """Register pond-related MCP tools.

    Args:
        mcp: The FastMCP server instance.
        adapter: The typed Follow Up Boss tool adapter.
    """

    @mcp.tool(
        name="followupboss_list_ponds",
        description="List Follow Up Boss ponds with pagination metadata.",
    )
    async def followupboss_list_ponds(
        *,
        limit: int | None = None,
        offset: int | None = None,
    ) -> dict[str, object]:
        return await adapter.list_ponds(PondListRequest(limit=limit, offset=offset))

    @mcp.tool(
        name="followupboss_get_pond",
        description="Fetch a single Follow Up Boss pond by ID.",
    )
    async def followupboss_get_pond(pond_id: int) -> dict[str, object]:
        return await adapter.get_pond(GetPondToolInput(pond_id=pond_id))

    @mcp.tool(
        name="followupboss_create_pond",
        description="Create a Follow Up Boss pond.",
    )
    async def followupboss_create_pond(
        name: str,
        user_id: int,
        user_ids: list[int],
    ) -> dict[str, object]:
        return await adapter.create_pond(
            CreatePondRequest(
                name=name,
                user_id=user_id,
                user_ids=user_ids,
            )
        )

    @mcp.tool(
        name="followupboss_update_pond",
        description="Update a Follow Up Boss pond by ID.",
    )
    async def followupboss_update_pond(
        pond_id: int,
        *,
        name: str | None = None,
        user_id: int | None = None,
        user_ids: list[int] | None = None,
    ) -> dict[str, object]:
        return await adapter.update_pond(
            UpdatePondToolInput(
                pond_id=pond_id,
                name=name,
                user_id=user_id,
                user_ids=user_ids,
            )
        )

    @mcp.tool(
        name="followupboss_delete_pond",
        description="Delete a Follow Up Boss pond by ID and reassign its contacts.",
    )
    async def followupboss_delete_pond(pond_id: int, assign_to: int) -> dict[str, object]:
        return await adapter.delete_pond(
            DeletePondToolInput(
                pond_id=pond_id,
                assign_to=assign_to,
            )
        )


def _register_smart_list_tools(mcp: FastMCP, adapter: FollowUpBossToolAdapter) -> None:
    """Register smart-list-related MCP tools.

    Args:
        mcp: The FastMCP server instance.
        adapter: The typed Follow Up Boss tool adapter.
    """

    @mcp.tool(
        name="followupboss_list_smart_lists",
        description=(
            "List Follow Up Boss smart lists with documented filters and pagination metadata."
        ),
    )
    async def followupboss_list_smart_lists(
        *,
        fub2: bool | None = None,
        include_all: bool | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> dict[str, object]:
        return await adapter.list_smart_lists(
            SmartListListRequest(
                fub2=fub2,
                include_all=include_all,
                limit=limit,
                offset=offset,
            )
        )

    @mcp.tool(
        name="followupboss_get_smart_list",
        description="Fetch a single Follow Up Boss smart list by ID.",
    )
    async def followupboss_get_smart_list(smart_list_id: int) -> dict[str, object]:
        return await adapter.get_smart_list(GetSmartListToolInput(smart_list_id=smart_list_id))


def _register_stage_tools(mcp: FastMCP, adapter: FollowUpBossToolAdapter) -> None:
    """Register stage-related MCP tools.

    Args:
        mcp: The FastMCP server instance.
        adapter: The typed Follow Up Boss tool adapter.
    """

    @mcp.tool(
        name="followupboss_list_stages",
        description="List Follow Up Boss stages with documented filters and pagination metadata.",
    )
    async def followupboss_list_stages(
        *,
        limit: int | None = None,
        offset: int | None = None,
        sort: str | None = None,
    ) -> dict[str, object]:
        return await adapter.list_stages(StageListRequest(limit=limit, offset=offset, sort=sort))

    @mcp.tool(
        name="followupboss_get_stage",
        description="Fetch a single Follow Up Boss stage by ID.",
    )
    async def followupboss_get_stage(stage_id: int) -> dict[str, object]:
        return await adapter.get_stage(GetStageToolInput(stage_id=stage_id))

    @mcp.tool(
        name="followupboss_create_stage",
        description="Create a Follow Up Boss stage.",
    )
    async def followupboss_create_stage(
        name: str,
        *,
        order_weight: int | None = None,
    ) -> dict[str, object]:
        return await adapter.create_stage(CreateStageRequest(name=name, order_weight=order_weight))

    @mcp.tool(
        name="followupboss_update_stage",
        description="Update a Follow Up Boss stage by ID.",
    )
    async def followupboss_update_stage(
        stage_id: int,
        *,
        name: str | None = None,
        order_weight: int | None = None,
    ) -> dict[str, object]:
        return await adapter.update_stage(
            UpdateStageToolInput(
                stage_id=stage_id,
                name=name,
                order_weight=order_weight,
            )
        )

    @mcp.tool(
        name="followupboss_delete_stage",
        description="Delete a Follow Up Boss stage by ID and reassign linked action plans.",
    )
    async def followupboss_delete_stage(
        stage_id: int,
        assign_stage_id: int,
    ) -> dict[str, object]:
        return await adapter.delete_stage(
            DeleteStageToolInput(
                stage_id=stage_id,
                assign_stage_id=assign_stage_id,
            )
        )


def _register_task_tools(mcp: FastMCP, adapter: FollowUpBossToolAdapter) -> None:
    """Register task-related MCP tools.

    Args:
        mcp: The FastMCP server instance.
        adapter: The typed Follow Up Boss tool adapter.
    """

    @mcp.tool(
        name="followupboss_list_tasks",
        description="List Follow Up Boss tasks with documented filters and pagination metadata.",
    )
    async def followupboss_list_tasks(
        *,
        fields: list[str] | None = None,
        id: int | None = None,
        ids: list[int] | None = None,
        id_greater_than: int | None = None,
        id_less_than: int | None = None,
        limit: int | None = None,
        next_token: str | None = None,
        offset: int | None = None,
        sort: str | None = None,
        assigned_to: str | None = None,
        assigned_user_id: int | None = None,
        due: str | None = None,
        due_end: str | None = None,
        due_start: str | None = None,
        is_completed: bool | None = None,
        name: str | None = None,
        person_id: int | None = None,
        type: list[str] | None = None,
    ) -> dict[str, object]:
        return await adapter.list_tasks(
            TaskListRequest.model_validate(
                {
                    "fields": fields,
                    "id": id,
                    "ids": ids,
                    "id_greater_than": id_greater_than,
                    "id_less_than": id_less_than,
                    "limit": limit,
                    "next_token": next_token,
                    "offset": offset,
                    "sort": sort,
                    "assigned_to": assigned_to,
                    "assigned_user_id": assigned_user_id,
                    "due": due,
                    "due_end": due_end,
                    "due_start": due_start,
                    "is_completed": is_completed,
                    "name": name,
                    "person_id": person_id,
                    "type": type,
                }
            )
        )

    @mcp.tool(
        name="followupboss_get_task",
        description="Fetch a single Follow Up Boss task by ID.",
    )
    async def followupboss_get_task(task_id: int) -> dict[str, object]:
        return await adapter.get_task(GetTaskToolInput(task_id=task_id))

    @mcp.tool(
        name="followupboss_create_task",
        description="Create a Follow Up Boss task.",
    )
    async def followupboss_create_task(
        person_id: int,
        *,
        assigned_to: str | None = None,
        assigned_user_id: int | None = None,
        due_date: str | None = None,
        due_date_time: str | None = None,
        is_completed: bool | None = None,
        name: str | None = None,
        remind_seconds_before: int | None = None,
        type: str | None = None,
    ) -> dict[str, object]:
        tool_input = CreateTaskRequest.model_validate(
            {
                "person_id": person_id,
                "assigned_to": assigned_to,
                "assigned_user_id": assigned_user_id,
                "due_date": due_date,
                "due_date_time": due_date_time,
                "is_completed": is_completed,
                "name": name,
                "remind_seconds_before": remind_seconds_before,
                "type": type,
            }
        )
        return await adapter.create_task(tool_input)

    @mcp.tool(
        name="followupboss_update_task",
        description="Update a Follow Up Boss task by ID.",
    )
    async def followupboss_update_task(
        task_id: int,
        *,
        assigned_to: str | None = None,
        assigned_user_id: int | None = None,
        due_date: str | None = None,
        due_date_time: str | None = None,
        is_completed: bool | None = None,
        name: str | None = None,
        person_id: int | None = None,
        type: str | None = None,
    ) -> dict[str, object]:
        return await adapter.update_task(
            UpdateTaskToolInput.model_validate(
                {
                    "task_id": task_id,
                    "assigned_to": assigned_to,
                    "assigned_user_id": assigned_user_id,
                    "due_date": due_date,
                    "due_date_time": due_date_time,
                    "is_completed": is_completed,
                    "name": name,
                    "person_id": person_id,
                    "type": type,
                }
            )
        )

    @mcp.tool(
        name="followupboss_delete_task",
        description="Delete a Follow Up Boss task by ID.",
    )
    async def followupboss_delete_task(task_id: int) -> dict[str, object]:
        return await adapter.delete_task(DeleteTaskToolInput(task_id=task_id))


def _register_team_inbox_tools(mcp: FastMCP, adapter: FollowUpBossToolAdapter) -> None:
    """Register team inbox related MCP tools.

    Args:
        mcp: The FastMCP server instance.
        adapter: The typed Follow Up Boss tool adapter.
    """

    @mcp.tool(
        name="followupboss_list_team_inboxes",
        description="List Follow Up Boss team inboxes with pagination metadata.",
    )
    async def followupboss_list_team_inboxes() -> dict[str, object]:
        return await adapter.list_team_inboxes(TeamInboxListRequest())


def _register_team_tools(mcp: FastMCP, adapter: FollowUpBossToolAdapter) -> None:
    """Register team-related MCP tools.

    Args:
        mcp: The FastMCP server instance.
        adapter: The typed Follow Up Boss tool adapter.
    """

    @mcp.tool(
        name="followupboss_list_teams",
        description="List Follow Up Boss teams with pagination metadata.",
    )
    async def followupboss_list_teams(
        *,
        limit: int | None = None,
        offset: int | None = None,
    ) -> dict[str, object]:
        return await adapter.list_teams(TeamListRequest(limit=limit, offset=offset))

    @mcp.tool(
        name="followupboss_get_team",
        description="Fetch a single Follow Up Boss team by ID.",
    )
    async def followupboss_get_team(team_id: int) -> dict[str, object]:
        return await adapter.get_team(GetTeamToolInput(team_id=team_id))

    @mcp.tool(
        name="followupboss_create_team",
        description="Create a Follow Up Boss team.",
    )
    async def followupboss_create_team(
        name: str,
        user_ids: list[int],
        *,
        leader_ids: list[int] | None = None,
    ) -> dict[str, object]:
        return await adapter.create_team(
            CreateTeamRequest(
                name=name,
                user_ids=user_ids,
                leader_ids=leader_ids,
            )
        )

    @mcp.tool(
        name="followupboss_update_team",
        description="Update a Follow Up Boss team by ID.",
    )
    async def followupboss_update_team(
        team_id: int,
        *,
        leader_ids: list[int] | None = None,
        name: str | None = None,
        user_ids: list[int] | None = None,
    ) -> dict[str, object]:
        return await adapter.update_team(
            UpdateTeamToolInput(
                team_id=team_id,
                leader_ids=leader_ids,
                name=name,
                user_ids=user_ids,
            )
        )

    @mcp.tool(
        name="followupboss_delete_team",
        description="Delete a Follow Up Boss team by ID, optionally moving members first.",
    )
    async def followupboss_delete_team(
        team_id: int,
        move_to_team_id: int | None = None,
    ) -> dict[str, object]:
        return await adapter.delete_team(
            DeleteTeamToolInput(
                team_id=team_id,
                move_to_team_id=move_to_team_id,
            )
        )


def _register_template_tools(mcp: FastMCP, adapter: FollowUpBossToolAdapter) -> None:
    """Register template-related MCP tools.

    Args:
        mcp: The FastMCP server instance.
        adapter: The typed Follow Up Boss tool adapter.
    """

    @mcp.tool(
        name="followupboss_list_templates",
        description="List Follow Up Boss email templates with pagination metadata.",
    )
    async def followupboss_list_templates(
        *,
        limit: int | None = None,
        offset: int | None = None,
    ) -> dict[str, object]:
        return await adapter.list_templates(
            TemplateListRequest(
                limit=limit,
                offset=offset,
            )
        )

    @mcp.tool(
        name="followupboss_get_template",
        description="Fetch a single Follow Up Boss email template by ID.",
    )
    async def followupboss_get_template(
        template_id: int,
        *,
        merge_person_id: int | None = None,
    ) -> dict[str, object]:
        return await adapter.get_template(
            GetTemplateToolInput(template_id=template_id, merge_person_id=merge_person_id)
        )

    @mcp.tool(
        name="followupboss_merge_template",
        description="Merge a Follow Up Boss email template with recipients.",
    )
    async def followupboss_merge_template(
        template_id: int,
        *,
        merge_person_id: int | None = None,
        recipients: dict[str, object] | None = None,
    ) -> dict[str, object]:
        return await adapter.merge_template(
            MergeTemplateRequest.model_validate(
                {
                    "template_id": template_id,
                    "merge_person_id": merge_person_id,
                    "recipients": recipients,
                }
            )
        )

    @mcp.tool(
        name="followupboss_create_template",
        description="Create a Follow Up Boss email template.",
    )
    async def followupboss_create_template(
        name: str,
        subject: str,
        body: str,
        *,
        is_shared: bool | None = None,
    ) -> dict[str, object]:
        return await adapter.create_template(
            CreateTemplateRequest(
                name=name,
                subject=subject,
                body=body,
                is_shared=is_shared,
            )
        )

    @mcp.tool(
        name="followupboss_update_template",
        description="Update a Follow Up Boss email template by ID.",
    )
    async def followupboss_update_template(
        template_id: int,
        *,
        name: str,
        subject: str,
        body: str,
    ) -> dict[str, object]:
        return await adapter.update_template(
            UpdateTemplateToolInput(
                template_id=template_id,
                name=name,
                subject=subject,
                body=body,
            )
        )

    @mcp.tool(
        name="followupboss_delete_template",
        description="Delete a Follow Up Boss email template by ID.",
    )
    async def followupboss_delete_template(template_id: int) -> dict[str, object]:
        return await adapter.delete_template(DeleteTemplateToolInput(template_id=template_id))


def _register_text_message_tools(mcp: FastMCP, adapter: FollowUpBossToolAdapter) -> None:
    """Register text message and text message template MCP tools.

    Args:
        mcp: The FastMCP server instance.
        adapter: The typed Follow Up Boss tool adapter.
    """

    @mcp.tool(
        name="followupboss_list_text_messages",
        description=(
            "List Follow Up Boss text messages with documented filters and pagination metadata."
        ),
    )
    async def followupboss_list_text_messages(
        *,
        from_number: str | None = None,
        person_id: int | None = None,
        to_number: str | None = None,
    ) -> dict[str, object]:
        return await adapter.list_text_messages(
            TextMessageListRequest(
                from_number=from_number,
                person_id=person_id,
                to_number=to_number,
            )
        )

    @mcp.tool(
        name="followupboss_get_text_message",
        description="Fetch a single Follow Up Boss text message by ID.",
    )
    async def followupboss_get_text_message(text_message_id: int) -> dict[str, object]:
        return await adapter.get_text_message(
            GetTextMessageToolInput(text_message_id=text_message_id)
        )

    @mcp.tool(
        name="followupboss_create_text_message",
        description="Record an externally sent Follow Up Boss text message log entry.",
    )
    async def followupboss_create_text_message(
        person_id: int,
        message: str,
        to_number: str,
        from_number: str,
        *,
        external_label: str | None = None,
        external_url: str | None = None,
        is_incoming: bool | None = None,
    ) -> dict[str, object]:
        return await adapter.create_text_message(
            CreateTextMessageRequest(
                person_id=person_id,
                message=message,
                to_number=to_number,
                from_number=from_number,
                external_label=external_label,
                external_url=external_url,
                is_incoming=is_incoming,
            )
        )

    @mcp.tool(
        name="followupboss_list_text_message_templates",
        description="List Follow Up Boss text message templates with pagination metadata.",
    )
    async def followupboss_list_text_message_templates(
        *,
        limit: int | None = None,
        offset: int | None = None,
    ) -> dict[str, object]:
        return await adapter.list_text_message_templates(
            TextMessageTemplateListRequest(limit=limit, offset=offset)
        )

    @mcp.tool(
        name="followupboss_get_text_message_template",
        description="Fetch a single Follow Up Boss text message template by ID.",
    )
    async def followupboss_get_text_message_template(template_id: int) -> dict[str, object]:
        return await adapter.get_text_message_template(
            GetTextMessageTemplateToolInput(template_id=template_id)
        )

    @mcp.tool(
        name="followupboss_merge_text_message_template",
        description="Merge a Follow Up Boss text message template with recipients.",
    )
    async def followupboss_merge_text_message_template(
        template_id: int,
        *,
        person_id: int | None = None,
        recipients: dict[str, object] | None = None,
    ) -> dict[str, object]:
        return await adapter.merge_text_message_template(
            MergeTextMessageTemplateRequest.model_validate(
                {
                    "template_id": template_id,
                    "person_id": person_id,
                    "recipients": recipients,
                }
            )
        )

    @mcp.tool(
        name="followupboss_create_text_message_template",
        description="Create a Follow Up Boss text message template.",
    )
    async def followupboss_create_text_message_template(
        name: str,
        message: str,
        *,
        is_shared: bool | None = None,
    ) -> dict[str, object]:
        return await adapter.create_text_message_template(
            CreateTextMessageTemplateRequest(
                name=name,
                message=message,
                is_shared=is_shared,
            )
        )

    @mcp.tool(
        name="followupboss_update_text_message_template",
        description="Update a Follow Up Boss text message template by ID.",
    )
    async def followupboss_update_text_message_template(
        template_id: int,
        *,
        name: str,
        message: str,
        is_shared: bool | None = None,
    ) -> dict[str, object]:
        return await adapter.update_text_message_template(
            UpdateTextMessageTemplateToolInput(
                template_id=template_id,
                name=name,
                message=message,
                is_shared=is_shared,
            )
        )

    @mcp.tool(
        name="followupboss_delete_text_message_template",
        description="Delete a Follow Up Boss text message template by ID.",
    )
    async def followupboss_delete_text_message_template(template_id: int) -> dict[str, object]:
        return await adapter.delete_text_message_template(
            DeleteTextMessageTemplateToolInput(template_id=template_id)
        )


def _register_note_tools(mcp: FastMCP, adapter: FollowUpBossToolAdapter) -> None:
    """Register note-related MCP tools.

    Args:
        mcp: The FastMCP server instance.
        adapter: The typed Follow Up Boss tool adapter.
    """

    @mcp.tool(
        name="followupboss_add_note",
        description=(
            "Create a Follow Up Boss note for a person, optionally waiting "
            "for person visibility first."
        ),
    )
    async def followupboss_add_note(
        person_id: int,
        *,
        body: str | None = None,
        is_html: bool | None = None,
        subject: str | None = None,
        wait_for_person: bool = False,
    ) -> dict[str, object]:
        return await adapter.add_note(
            CreateNoteRequest(
                body=body,
                is_html=is_html,
                person_id=person_id,
                subject=subject,
            ),
            wait_for_person=wait_for_person,
        )

    @mcp.tool(
        name="followupboss_get_note",
        description="Fetch a Follow Up Boss note by ID.",
    )
    async def followupboss_get_note(note_id: int) -> dict[str, object]:
        return await adapter.get_note(GetNoteToolInput(note_id=note_id))

    @mcp.tool(
        name="followupboss_update_note",
        description="Update a Follow Up Boss note by ID.",
    )
    async def followupboss_update_note(
        note_id: int,
        *,
        body: str | None = None,
        is_html: bool | None = None,
        subject: str | None = None,
    ) -> dict[str, object]:
        return await adapter.update_note(
            UpdateNoteToolInput(
                note_id=note_id,
                body=body,
                is_html=is_html,
                subject=subject,
            )
        )

    @mcp.tool(
        name="followupboss_delete_note",
        description="Delete a Follow Up Boss note by ID.",
    )
    async def followupboss_delete_note(note_id: int) -> dict[str, object]:
        return await adapter.delete_note(DeleteNoteToolInput(note_id=note_id))


def _register_webhook_tools(mcp: FastMCP, adapter: FollowUpBossToolAdapter) -> None:
    """Register webhook-related MCP tools.

    Args:
        mcp: The FastMCP server instance.
        adapter: The typed Follow Up Boss tool adapter.
    """

    @mcp.tool(
        name="followupboss_list_webhooks",
        description="List registered Follow Up Boss webhooks with pagination metadata.",
    )
    async def followupboss_list_webhooks(
        *,
        fields: list[str] | None = None,
        id: int | None = None,
        ids: list[int] | None = None,
        id_greater_than: int | None = None,
        id_less_than: int | None = None,
        limit: int | None = None,
        next_token: str | None = None,
        offset: int | None = None,
        sort: str | None = None,
        event: str | None = None,
        status: str | None = None,
    ) -> dict[str, object]:
        return await adapter.list_webhooks(
            WebhookListRequest(
                fields=fields,
                id=id,
                ids=ids,
                id_greater_than=id_greater_than,
                id_less_than=id_less_than,
                limit=limit,
                next_token=next_token,
                offset=offset,
                sort=sort,
                event=event,
                status=status,
            )
        )

    @mcp.tool(
        name="followupboss_get_webhook",
        description="Fetch a single Follow Up Boss webhook by ID.",
    )
    async def followupboss_get_webhook(webhook_id: int) -> dict[str, object]:
        return await adapter.get_webhook(GetWebhookToolInput(webhook_id=webhook_id))

    @mcp.tool(
        name="followupboss_create_webhook",
        description="Create a Follow Up Boss webhook for a documented event name.",
    )
    async def followupboss_create_webhook(event: str, url: str) -> dict[str, object]:
        return await adapter.create_webhook(CreateWebhookRequest(event=event, url=url))

    @mcp.tool(
        name="followupboss_delete_webhook",
        description="Delete a Follow Up Boss webhook by ID.",
    )
    async def followupboss_delete_webhook(webhook_id: int) -> dict[str, object]:
        return await adapter.delete_webhook(DeleteWebhookToolInput(webhook_id=webhook_id))


def _register_resources_and_prompts(mcp: FastMCP, *, project_root: Path) -> None:
    """Register MCP resources and prompts.

    Args:
        mcp: The FastMCP server instance.
        project_root: The repository root used for file-backed resources.
    """

    @mcp.resource(
        "followupboss://api-coverage-matrix",
        title="Follow Up Boss API Coverage Matrix",
        description="Repository API coverage matrix for Follow Up Boss endpoints.",
        mime_type="text/markdown",
    )
    def followupboss_api_coverage_matrix() -> str:
        return (project_root / "docs" / "api-coverage-matrix.md").read_text(encoding="utf-8")

    @mcp.prompt(
        name="followupboss_compose_lead_event",
        description="Compose a canonical POST /events payload for a new lead or lead activity.",
    )
    def followupboss_compose_lead_event(
        source: str,
        type: str,
        message: str,
        email: str,
        *,
        first_name: str = "",
        last_name: str = "",
    ) -> str:
        return (
            "Create a Follow Up Boss POST /events payload using the canonical "
            "lead-ingestion path.\n\n"
            f"source: {source}\n"
            f"type: {type}\n"
            f"message: {message}\n"
            f"email: {email}\n"
            f"first_name: {first_name}\n"
            f"last_name: {last_name}\n\n"
            "Return JSON with top-level source, system, type, message, and a nested person object."
        )
