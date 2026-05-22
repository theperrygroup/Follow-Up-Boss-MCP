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
from followupboss_mcp.models.common import RequestModel
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
from followupboss_mcp.models.webhooks import (
    CreateWebhookRequest,
    WebhookListRequest,
)
from followupboss_mcp.observability import capture_sentry_exception
from followupboss_mcp.tenant_runtime import TenantRuntime, TenantRuntimeFactory
from mcp.server.fastmcp import FastMCP

_API_COVERAGE_RESOURCE_URI = "followupboss://api-coverage-matrix"
_COMPOSE_LEAD_EVENT_PROMPT_NAME = "followupboss_compose_lead_event"
_HOSTED_PUBLIC_RESOURCE_URIS: frozenset[str] = frozenset()
_HOSTED_PUBLIC_PROMPT_NAMES: frozenset[str] = frozenset()


def _validated_request[ModelT: RequestModel](
    model_type: type[ModelT],
    values: dict[str, object],
    /,
    *,
    exclude: set[str] | None = None,
) -> ModelT:
    """Build a typed request model from function-local values.

    Args:
        model_type: The strict request model type to validate.
        values: The raw function-local values to validate.
        exclude: Optional local variable names to skip.

    Returns:
        The validated request-model instance.
    """
    payload = {
        key: value
        for key, value in values.items()
        if key in model_type.model_fields and (exclude is None or key not in exclude)
    }
    return model_type.model_validate(payload)


def register_server_surface(
    mcp: FastMCP,
    adapter: FollowUpBossToolAdapter,
    *,
    project_root: Path,
    tenant_runtime_factory: TenantRuntimeFactory | None = None,
) -> None:
    """Register the complete Follow Up Boss MCP surface.

    Args:
        mcp: The FastMCP server instance to extend.
        adapter: The typed MCP adapter that delegates to domain services.
        project_root: The repository root used for resource-backed content.
        tenant_runtime_factory: Optional hosted runtime factory used to resolve
            tenant context for non-tool MCP surfaces.
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
    _register_resources_and_prompts(
        mcp,
        project_root=project_root,
        tenant_runtime_factory=tenant_runtime_factory,
    )


def _format_hosted_surface_context(runtime: TenantRuntime) -> str:
    """Return a compact, non-secret hosted tenant context block.

    Args:
        runtime: The resolved hosted tenant runtime for the active MCP call.

    Returns:
        A stable text block that surfaces the authenticated tenant identity
        without exposing credential material.
    """
    display_name = runtime.tenant.display_name or runtime.tenant.tenant_slug
    return (
        "Hosted tenant context:\n"
        f"tenant_slug: {runtime.tenant.tenant_slug}\n"
        f"display_name: {display_name}"
    )


def _surface_runtime_resolution_error() -> RuntimeError:
    """Return a stable MCP-safe runtime-resolution error.

    Returns:
        A runtime error with a non-secret message suitable for MCP transport
        surfaces.
    """
    return RuntimeError("Hosted tenant runtime is unavailable.")


async def _resolve_surface_runtime(
    *,
    surface_name: str,
    public_surface_names: frozenset[str],
    tenant_runtime_factory: TenantRuntimeFactory | None,
) -> TenantRuntime | None:
    """Resolve hosted tenant runtime for one non-tool MCP surface.

    Args:
        surface_name: The resource URI or prompt name being handled.
        public_surface_names: The set of hosted surfaces intentionally left
            public.
        tenant_runtime_factory: Optional hosted runtime factory.

    Returns:
        The tenant runtime for the active hosted call, or `None` when hosted
        runtime resolution is disabled or the surface is intentionally public.
    """
    if tenant_runtime_factory is None or surface_name in public_surface_names:
        return None
    try:
        return await tenant_runtime_factory.runtime_for_current_tenant()
    except Exception as exc:
        capture_sentry_exception(
            exc,
            tags={
                "component": "mcp_registration",
                "surface_runtime_phase": "resolve_surface_runtime",
            },
            extras={"surface_name": surface_name},
        )
        raise _surface_runtime_resolution_error() from None


def _render_api_coverage_matrix_resource(
    *,
    resource_text: str,
    runtime: TenantRuntime | None,
) -> str:
    """Render the API-coverage resource with optional hosted tenant context.

    Args:
        resource_text: The base repository-backed markdown content.
        runtime: Optional hosted tenant runtime for the active call.

    Returns:
        The resource content with hosted tenant context appended when available.
    """
    if runtime is None:
        return resource_text
    return f"{resource_text.rstrip()}\n\n---\n\n{_format_hosted_surface_context(runtime)}\n"


def _render_compose_lead_event_prompt(
    *,
    source: str,
    type: str,
    message: str,
    email: str,
    first_name: str,
    last_name: str,
    runtime: TenantRuntime | None,
) -> str:
    """Render the lead-event prompt with optional hosted tenant context.

    Args:
        source: The Follow Up Boss lead source.
        type: The Follow Up Boss event type.
        message: The lead or activity message.
        email: The lead email address.
        first_name: Optional lead first name.
        last_name: Optional lead last name.
        runtime: Optional hosted tenant runtime for the active call.

    Returns:
        The prompt text with hosted tenant context included when available.
    """
    tenant_context = ""
    if runtime is not None:
        tenant_context = (
            "Use the authenticated hosted tenant context below for any "
            "account-scoped assumptions.\n"
            f"{_format_hosted_surface_context(runtime)}\n\n"
        )
    return (
        "Create a Follow Up Boss POST /events payload using the canonical "
        "lead-ingestion path.\n\n"
        f"{tenant_context}"
        f"source: {source}\n"
        f"type: {type}\n"
        f"message: {message}\n"
        f"email: {email}\n"
        f"first_name: {first_name}\n"
        f"last_name: {last_name}\n\n"
        "Return JSON with top-level source, system, type, message, and a nested person object."
    )


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
            "Search Follow Up Boss people with documented query parameters "
            "and pagination metadata. By default this searches the authenticated "
            "user's assigned leads; set include_ponds=true to include pond/shared "
            "leads visible to the authenticated user. Use this broad search for "
            "explicit person filters or known smart_list_id searches. Do not use "
            "this broad search for named smart-list people prompts; use "
            "followupboss_search_people_in_smart_list so the list name is resolved "
            "inside the MCP boundary. Do not use this broad search for "
            "'my latest lead', 'newest lead', or 'most recent lead I received'; "
            "use followupboss_get_latest_lead so the authenticated user is resolved "
            "internally."
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
        include_ponds: bool | None = None,
        last_name: str | None = None,
        name: str | None = None,
        phone: str | None = None,
        smart_list_id: int | None = None,
        source: str | None = None,
        stage: str | None = None,
        custom_field_filters: dict[str, str] | None = None,
    ) -> dict[str, object]:
        tool_input = _validated_request(PeopleSearchRequest, locals())
        return await adapter.search_people(tool_input)

    @mcp.tool(
        name="followupboss_search_people_in_smart_list",
        description=(
            "Search people inside an exact named Follow Up Boss smart list. Use this "
            "for prompts such as 'Zillow leads in Eligible For Transfer' or any "
            "request where the user names a smart list instead of providing a numeric "
            "smart_list_id. The tool resolves the smart-list name with "
            "include_all=true, fails on missing or ambiguous names, then searches "
            "people only with the resolved smart_list_id and returns smart-list "
            "provenance. Set mine=true for I/me/my follow-up requests so the "
            "helper also scopes by the authenticated user. Use assigned_user_id "
            "for an explicit owner. Do not include people outside the returned "
            "people list in the answer."
        ),
    )
    async def followupboss_search_people_in_smart_list(
        smart_list_name: str | None = None,
        *,
        assigned_user_id: int | None = None,
        fields: list[str] | None = None,
        smart_list: str | None = None,
        list_name: str | None = None,
        limit: int | None = None,
        lead_source: str | None = None,
        mine: bool = False,
        next_token: str | None = None,
        offset: int | None = None,
        source: str | None = None,
        source_name: str | None = None,
        stage: str | None = None,
    ) -> dict[str, object]:
        tool_input = _validated_request(SearchPeopleInSmartListToolInput, locals())
        return await adapter.search_people_in_smart_list(tool_input)

    @mcp.tool(
        name="followupboss_get_latest_lead",
        description=(
            "Return the single most recently created Follow Up Boss lead assigned "
            "to the authenticated user. Use this for requests like 'my latest lead', "
            "'newest lead', or 'most recent lead I received'. Resolves the "
            "authenticated user internally; do not ask the caller for an "
            "assigned_user_id."
        ),
    )
    async def followupboss_get_latest_lead(
        *,
        fields: list[str] | None = None,
    ) -> dict[str, object]:
        return await adapter.get_latest_lead(_validated_request(GetLatestLeadToolInput, locals()))

    @mcp.tool(
        name="followupboss_get_person",
        description="Fetch a single Follow Up Boss person by ID.",
    )
    async def followupboss_get_person(
        person_id: int,
        *,
        fields: list[str] | None = None,
    ) -> dict[str, object]:
        return await adapter.get_person(_validated_request(GetPersonToolInput, locals()))

    @mcp.tool(
        name="followupboss_list_person_activity",
        description=(
            "List communication and activity records for one explicit Follow Up Boss "
            "person_id. Use this for prompts like 'history for person 123', 'calls, "
            "texts, and events for this lead', or 'what have we sent contact 123'. "
            "This helper applies person_id to calls, text messages, email events, "
            "events, and appointments inside the MCP boundary. Do not use broad "
            "activity list tools for lead/contact history unless the user supplies "
            "the exact required person or phone filter."
        ),
    )
    async def followupboss_list_person_activity(
        person_id: int,
        *,
        include_appointments: bool = True,
        include_calls: bool = True,
        include_email_events: bool = True,
        include_events: bool = True,
        include_text_messages: bool = True,
        limit: int | None = None,
        offset: int | None = None,
    ) -> dict[str, object]:
        return await adapter.list_person_activity(
            _validated_request(ListPersonActivityToolInput, locals())
        )

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
        tool_input = _validated_request(CreatePersonRequest, locals())
        return await adapter.create_person(tool_input)

    @mcp.tool(
        name="followupboss_update_person",
        description=(
            "Update a single Follow Up Boss person by explicit person_id. Do not "
            "infer the person_id from vague natural-language intent."
        ),
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
        tool_input = _validated_request(UpdatePersonToolInput, locals())
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
            _validated_request(CheckDuplicatePersonToolInput, locals())
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
            _validated_request(UnclaimedPeopleListRequest, locals())
        )

    @mcp.tool(
        name="followupboss_claim_person",
        description="Claim an unclaimed Follow Up Boss lead by person ID.",
    )
    async def followupboss_claim_person(person_id: int) -> dict[str, object]:
        return await adapter.claim_person(_validated_request(ClaimPersonToolInput, locals()))

    @mcp.tool(
        name="followupboss_ignore_unclaimed_person",
        description="Ignore an unclaimed Follow Up Boss lead offer by person ID.",
    )
    async def followupboss_ignore_unclaimed_person(person_id: int) -> dict[str, object]:
        return await adapter.ignore_unclaimed_person(
            _validated_request(IgnoreUnclaimedPersonToolInput, locals())
        )

    @mcp.tool(
        name="followupboss_delete_person",
        description=(
            "Delete a Follow Up Boss person by explicit person_id. Do not infer the "
            "person_id from vague natural-language intent."
        ),
    )
    async def followupboss_delete_person(person_id: int) -> dict[str, object]:
        return await adapter.delete_person(_validated_request(DeletePersonToolInput, locals()))


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
            _validated_request(PeopleRelationshipListRequest, locals())
        )

    @mcp.tool(
        name="followupboss_get_people_relationship",
        description="Fetch a single Follow Up Boss people relationship by ID.",
    )
    async def followupboss_get_people_relationship(
        people_relationship_id: int,
    ) -> dict[str, object]:
        return await adapter.get_people_relationship(
            _validated_request(GetPeopleRelationshipToolInput, locals())
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
            _validated_request(CreatePeopleRelationshipRequest, locals())
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
            _validated_request(UpdatePeopleRelationshipToolInput, locals())
        )

    @mcp.tool(
        name="followupboss_delete_people_relationship",
        description="Delete a Follow Up Boss people relationship by ID.",
    )
    async def followupboss_delete_people_relationship(
        people_relationship_id: int,
    ) -> dict[str, object]:
        return await adapter.delete_people_relationship(
            _validated_request(DeletePeopleRelationshipToolInput, locals())
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
        return await adapter.list_timeframes(_validated_request(TimeframeListRequest, locals()))


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
            _validated_request(GetPersonAttachmentToolInput, locals())
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
            _validated_request(CreatePersonAttachmentRequest, locals())
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
            _validated_request(UpdatePersonAttachmentToolInput, locals())
        )

    @mcp.tool(
        name="followupboss_delete_person_attachment",
        description="Delete a Follow Up Boss person attachment by ID.",
    )
    async def followupboss_delete_person_attachment(person_attachment_id: int) -> dict[str, object]:
        return await adapter.delete_person_attachment(
            _validated_request(DeletePersonAttachmentToolInput, locals())
        )

    @mcp.tool(
        name="followupboss_get_deal_attachment",
        description="Fetch a single Follow Up Boss deal attachment by ID.",
    )
    async def followupboss_get_deal_attachment(deal_attachment_id: int) -> dict[str, object]:
        return await adapter.get_deal_attachment(
            _validated_request(GetDealAttachmentToolInput, locals())
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
            _validated_request(CreateDealAttachmentRequest, locals())
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
            _validated_request(UpdateDealAttachmentToolInput, locals())
        )

    @mcp.tool(
        name="followupboss_delete_deal_attachment",
        description="Delete a Follow Up Boss deal attachment by ID.",
    )
    async def followupboss_delete_deal_attachment(deal_attachment_id: int) -> dict[str, object]:
        return await adapter.delete_deal_attachment(
            _validated_request(DeleteDealAttachmentToolInput, locals())
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
        return await adapter.get_reaction(_validated_request(GetReactionToolInput, locals()))

    @mcp.tool(
        name="followupboss_add_reaction",
        description="Add a Follow Up Boss reaction to a note, call, or threaded reply.",
    )
    async def followupboss_add_reaction(
        ref_type: ReactionRefType,
        ref_id: int,
        body: str,
    ) -> dict[str, object]:
        return await adapter.add_reaction(_validated_request(AddReactionToolInput, locals()))

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
        return await adapter.delete_reaction(_validated_request(DeleteReactionToolInput, locals()))


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
            _validated_request(GetThreadedReplyToolInput, locals())
        )


def _register_event_tools(mcp: FastMCP, adapter: FollowUpBossToolAdapter) -> None:
    """Register event-related MCP tools.

    Args:
        mcp: The FastMCP server instance.
        adapter: The typed Follow Up Boss tool adapter.
    """

    @mcp.tool(
        name="followupboss_search_events",
        description=(
            "Search Follow Up Boss events with pagination metadata. Do not use this to "
            "answer requests for notes associated with a person or lead ID; Follow Up Boss "
            "has not made note search by FUB person ID available via the API. Tell the "
            "user this and suggest asking support@followupboss.com to make that search "
            "possible."
        ),
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
        return await adapter.search_events(_validated_request(EventSearchRequest, locals()))

    @mcp.tool(
        name="followupboss_get_event",
        description="Fetch a single Follow Up Boss event by ID.",
    )
    async def followupboss_get_event(event_id: int) -> dict[str, object]:
        return await adapter.get_event(_validated_request(GetEventToolInput, locals()))

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
        tool_input = _validated_request(CreateEventRequest, locals())
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
            _validated_request(EmailCampaignListRequest, locals())
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
            _validated_request(CreateEmailCampaignRequest, locals())
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
            _validated_request(UpdateEmailCampaignToolInput, locals())
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
        return await adapter.list_email_events(_validated_request(EmailEventListRequest, locals()))

    @mcp.tool(
        name="followupboss_send_email_events",
        description="Post batched Follow Up Boss email marketing events.",
    )
    async def followupboss_send_email_events(
        em_events: list[dict[str, object]],
    ) -> dict[str, object]:
        return await adapter.send_email_events(
            _validated_request(CreateEmailEventsBatchRequest, locals())
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
        return await adapter.list_action_plans(_validated_request(ActionPlanListRequest, locals()))

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
            _validated_request(ActionPlanPersonListRequest, locals())
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
            _validated_request(CreateActionPlanPersonRequest, locals())
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
            _validated_request(UpdateActionPlanPersonToolInput, locals())
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
        return await adapter.list_automations(_validated_request(AutomationListRequest, locals()))

    @mcp.tool(
        name="followupboss_get_automation",
        description="Fetch a single Follow Up Boss automation by ID.",
    )
    async def followupboss_get_automation(automation_id: int) -> dict[str, object]:
        return await adapter.get_automation(_validated_request(GetAutomationToolInput, locals()))

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
            _validated_request(AutomationPeopleListRequest, locals())
        )

    @mcp.tool(
        name="followupboss_get_automation_person",
        description="Fetch a single Follow Up Boss automation-person pairing by ID.",
    )
    async def followupboss_get_automation_person(automation_person_id: int) -> dict[str, object]:
        return await adapter.get_automation_person(
            _validated_request(GetAutomationPersonToolInput, locals())
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
            _validated_request(CreateAutomationPersonRequest, locals())
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
            _validated_request(UpdateAutomationPersonToolInput, locals())
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
        return await adapter.list_groups(_validated_request(GroupListRequest, locals()))

    @mcp.tool(
        name="followupboss_list_round_robin_groups",
        description="List Follow Up Boss groups including round-robin assignment details.",
    )
    async def followupboss_list_round_robin_groups(
        *,
        sort: str | None = None,
        type: str | None = None,
    ) -> dict[str, object]:
        return await adapter.list_round_robin_groups(_validated_request(GroupListRequest, locals()))

    @mcp.tool(
        name="followupboss_get_group",
        description="Fetch a single Follow Up Boss group by ID.",
    )
    async def followupboss_get_group(group_id: int) -> dict[str, object]:
        return await adapter.get_group(_validated_request(GetGroupToolInput, locals()))

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
        return await adapter.create_group(_validated_request(CreateGroupRequest, locals()))

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
        return await adapter.update_group(_validated_request(UpdateGroupToolInput, locals()))

    @mcp.tool(
        name="followupboss_delete_group",
        description="Delete a Follow Up Boss group by ID.",
    )
    async def followupboss_delete_group(group_id: int) -> dict[str, object]:
        return await adapter.delete_group(_validated_request(DeleteGroupToolInput, locals()))


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
            _validated_request(ListInboxAppInstallationsToolInput, locals())
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
        return await adapter.install_inbox_app(_validated_request(InstallInboxAppRequest, locals()))

    @mcp.tool(
        name="followupboss_deactivate_inbox_app",
        description="Deactivate a Follow Up Boss inbox app installation by ID.",
    )
    async def followupboss_deactivate_inbox_app(inbox_app_id: int) -> dict[str, object]:
        return await adapter.deactivate_inbox_app(
            _validated_request(DeactivateInboxAppToolInput, locals())
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
            _validated_request(AddInboxAppMessageToolInput, locals())
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
            _validated_request(AddInboxAppNoteToolInput, locals())
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
            _validated_request(ListInboxAppParticipantsToolInput, locals())
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
            _validated_request(AddInboxAppParticipantToolInput, locals())
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
            _validated_request(UpdateInboxAppConversationToolInput, locals())
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
            _validated_request(UpdateInboxAppMessageToolInput, locals())
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
            _validated_request(DeleteInboxAppParticipantToolInput, locals())
        )


def _register_user_tools(mcp: FastMCP, adapter: FollowUpBossToolAdapter) -> None:
    """Register user-related MCP tools.

    Args:
        mcp: The FastMCP server instance.
        adapter: The typed Follow Up Boss tool adapter.
    """

    @mcp.tool(
        name="followupboss_get_me",
        description=(
            "Retrieve the current Follow Up Boss user profile with sensitive keys redacted."
        ),
    )
    async def followupboss_get_me() -> dict[str, object]:
        return await adapter.get_me()

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
        return await adapter.list_users(_validated_request(UserListRequest, locals()))

    @mcp.tool(
        name="followupboss_get_user",
        description="Fetch a single Follow Up Boss user by ID.",
    )
    async def followupboss_get_user(user_id: int) -> dict[str, object]:
        return await adapter.get_user(_validated_request(GetUserToolInput, locals()))

    @mcp.tool(
        name="followupboss_delete_user",
        description="Delete a Follow Up Boss user by ID and reassign their leads.",
    )
    async def followupboss_delete_user(user_id: int, assign_to: int) -> dict[str, object]:
        return await adapter.delete_user(_validated_request(DeleteUserToolInput, locals()))


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
            _validated_request(AppointmentOutcomeListRequest, locals())
        )

    @mcp.tool(
        name="followupboss_get_appointment_outcome",
        description="Fetch a single Follow Up Boss appointment outcome by ID.",
    )
    async def followupboss_get_appointment_outcome(
        appointment_outcome_id: int,
    ) -> dict[str, object]:
        return await adapter.get_appointment_outcome(
            _validated_request(GetAppointmentOutcomeToolInput, locals())
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
            _validated_request(CreateAppointmentOutcomeRequest, locals())
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
            _validated_request(UpdateAppointmentOutcomeToolInput, locals())
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
            _validated_request(DeleteAppointmentOutcomeToolInput, locals())
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
            _validated_request(AppointmentTypeListRequest, locals())
        )

    @mcp.tool(
        name="followupboss_get_appointment_type",
        description="Fetch a single Follow Up Boss appointment type by ID.",
    )
    async def followupboss_get_appointment_type(
        appointment_type_id: int,
    ) -> dict[str, object]:
        return await adapter.get_appointment_type(
            _validated_request(GetAppointmentTypeToolInput, locals())
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
            _validated_request(CreateAppointmentTypeRequest, locals())
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
            _validated_request(UpdateAppointmentTypeToolInput, locals())
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
            _validated_request(DeleteAppointmentTypeToolInput, locals())
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
            _validated_request(CustomFieldListRequest, locals())
        )

    @mcp.tool(
        name="followupboss_get_custom_field",
        description="Fetch a single Follow Up Boss custom field by ID.",
    )
    async def followupboss_get_custom_field(custom_field_id: int) -> dict[str, object]:
        return await adapter.get_custom_field(_validated_request(GetCustomFieldToolInput, locals()))

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
            _validated_request(CreateCustomFieldRequest, locals())
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
            _validated_request(UpdateCustomFieldToolInput, locals())
        )

    @mcp.tool(
        name="followupboss_delete_custom_field",
        description="Delete a Follow Up Boss custom field by ID.",
    )
    async def followupboss_delete_custom_field(custom_field_id: int) -> dict[str, object]:
        return await adapter.delete_custom_field(
            _validated_request(DeleteCustomFieldToolInput, locals())
        )


def _register_deal_tools(mcp: FastMCP, adapter: FollowUpBossToolAdapter) -> None:
    """Register deal-related MCP tools.

    Args:
        mcp: The FastMCP server instance.
        adapter: The typed Follow Up Boss tool adapter.
    """

    @mcp.tool(
        name="followupboss_list_deals",
        description=(
            "List Follow Up Boss deals with documented filters and pagination metadata. "
            "For active deals tied to a specific lead/person, use "
            "followupboss_list_active_deals_for_person."
        ),
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
        return await adapter.list_deals(_validated_request(DealListRequest, locals()))

    @mcp.tool(
        name="followupboss_list_active_deals_for_person",
        description=(
            "List active, non-archived Follow Up Boss deals for a specific person/lead. "
            "Use this for requests like 'open deals for this lead' or "
            "'active deals for person 123'."
        ),
    )
    async def followupboss_list_active_deals_for_person(person_id: int) -> dict[str, object]:
        return await adapter.list_active_deals_for_person(
            _validated_request(ListActiveDealsForPersonToolInput, locals())
        )

    @mcp.tool(
        name="followupboss_get_deal",
        description="Fetch a single Follow Up Boss deal by ID.",
    )
    async def followupboss_get_deal(deal_id: int) -> dict[str, object]:
        return await adapter.get_deal(_validated_request(GetDealToolInput, locals()))

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
        return await adapter.create_deal(_validated_request(CreateDealRequest, locals()))

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
        return await adapter.update_deal(_validated_request(UpdateDealToolInput, locals()))

    @mcp.tool(
        name="followupboss_delete_deal",
        description="Delete a Follow Up Boss deal by ID.",
    )
    async def followupboss_delete_deal(deal_id: int) -> dict[str, object]:
        return await adapter.delete_deal(_validated_request(DeleteDealToolInput, locals()))

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
            _validated_request(DealCustomFieldListRequest, locals())
        )

    @mcp.tool(
        name="followupboss_get_deal_custom_field",
        description="Fetch a single Follow Up Boss deal custom field by ID.",
    )
    async def followupboss_get_deal_custom_field(deal_custom_field_id: int) -> dict[str, object]:
        return await adapter.get_deal_custom_field(
            _validated_request(GetDealCustomFieldToolInput, locals())
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
            _validated_request(CreateDealCustomFieldRequest, locals())
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
            _validated_request(UpdateDealCustomFieldToolInput, locals())
        )

    @mcp.tool(
        name="followupboss_delete_deal_custom_field",
        description="Delete a Follow Up Boss deal custom field by ID.",
    )
    async def followupboss_delete_deal_custom_field(deal_custom_field_id: int) -> dict[str, object]:
        return await adapter.delete_deal_custom_field(
            _validated_request(DeleteDealCustomFieldToolInput, locals())
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
        return await adapter.list_appointments(_validated_request(AppointmentListRequest, locals()))

    @mcp.tool(
        name="followupboss_get_appointment",
        description="Fetch a single Follow Up Boss appointment by ID.",
    )
    async def followupboss_get_appointment(appointment_id: int) -> dict[str, object]:
        return await adapter.get_appointment(_validated_request(GetAppointmentToolInput, locals()))

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
            _validated_request(CreateAppointmentRequest, locals())
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
            _validated_request(UpdateAppointmentToolInput, locals())
        )

    @mcp.tool(
        name="followupboss_delete_appointment",
        description="Delete a Follow Up Boss appointment by ID.",
    )
    async def followupboss_delete_appointment(appointment_id: int) -> dict[str, object]:
        return await adapter.delete_appointment(
            _validated_request(DeleteAppointmentToolInput, locals())
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
        return await adapter.list_calls(_validated_request(CallListRequest, locals()))

    @mcp.tool(
        name="followupboss_get_call",
        description="Fetch a single Follow Up Boss call by ID.",
    )
    async def followupboss_get_call(call_id: int) -> dict[str, object]:
        return await adapter.get_call(_validated_request(GetCallToolInput, locals()))

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
        return await adapter.create_call(_validated_request(CreateCallRequest, locals()))

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
        return await adapter.update_call(_validated_request(UpdateCallToolInput, locals()))


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
        return await adapter.list_pipelines(_validated_request(PipelineListRequest, locals()))

    @mcp.tool(
        name="followupboss_get_pipeline",
        description="Fetch a single Follow Up Boss pipeline by ID.",
    )
    async def followupboss_get_pipeline(pipeline_id: int) -> dict[str, object]:
        return await adapter.get_pipeline(_validated_request(GetPipelineToolInput, locals()))

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
            _validated_request(
                CreatePipelineRequest,
                {**locals(), "stages": stage_inputs},
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
            _validated_request(
                UpdatePipelineToolInput,
                {**locals(), "stages": stage_inputs},
            )
        )

    @mcp.tool(
        name="followupboss_delete_pipeline",
        description=(
            "Delete a Follow Up Boss pipeline by ID. Owner permissions are required upstream."
        ),
    )
    async def followupboss_delete_pipeline(pipeline_id: int) -> dict[str, object]:
        return await adapter.delete_pipeline(_validated_request(DeletePipelineToolInput, locals()))


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
        return await adapter.list_ponds(_validated_request(PondListRequest, locals()))

    @mcp.tool(
        name="followupboss_get_pond",
        description="Fetch a single Follow Up Boss pond by ID.",
    )
    async def followupboss_get_pond(pond_id: int) -> dict[str, object]:
        return await adapter.get_pond(_validated_request(GetPondToolInput, locals()))

    @mcp.tool(
        name="followupboss_create_pond",
        description="Create a Follow Up Boss pond.",
    )
    async def followupboss_create_pond(
        name: str,
        user_id: int,
        user_ids: list[int],
    ) -> dict[str, object]:
        return await adapter.create_pond(_validated_request(CreatePondRequest, locals()))

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
        return await adapter.update_pond(_validated_request(UpdatePondToolInput, locals()))

    @mcp.tool(
        name="followupboss_delete_pond",
        description="Delete a Follow Up Boss pond by ID and reassign its contacts.",
    )
    async def followupboss_delete_pond(pond_id: int, assign_to: int) -> dict[str, object]:
        return await adapter.delete_pond(_validated_request(DeletePondToolInput, locals()))


def _register_smart_list_tools(mcp: FastMCP, adapter: FollowUpBossToolAdapter) -> None:
    """Register smart-list-related MCP tools.

    Args:
        mcp: The FastMCP server instance.
        adapter: The typed Follow Up Boss tool adapter.
    """

    @mcp.tool(
        name="followupboss_list_smart_lists",
        description=(
            "List Follow Up Boss smart lists with documented filters and pagination metadata. "
            "When resolving a user-provided smart list name, set include_all=true so both "
            "classic and current Follow Up Boss smart lists are considered."
        ),
    )
    async def followupboss_list_smart_lists(
        *,
        fub2: bool | None = None,
        include_all: bool | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ) -> dict[str, object]:
        return await adapter.list_smart_lists(_validated_request(SmartListListRequest, locals()))

    @mcp.tool(
        name="followupboss_get_smart_list",
        description="Fetch a single Follow Up Boss smart list by ID.",
    )
    async def followupboss_get_smart_list(smart_list_id: int) -> dict[str, object]:
        return await adapter.get_smart_list(_validated_request(GetSmartListToolInput, locals()))


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
        return await adapter.list_stages(_validated_request(StageListRequest, locals()))

    @mcp.tool(
        name="followupboss_get_stage",
        description="Fetch a single Follow Up Boss stage by ID.",
    )
    async def followupboss_get_stage(stage_id: int) -> dict[str, object]:
        return await adapter.get_stage(_validated_request(GetStageToolInput, locals()))

    @mcp.tool(
        name="followupboss_create_stage",
        description="Create a Follow Up Boss stage.",
    )
    async def followupboss_create_stage(
        name: str,
        *,
        order_weight: int | None = None,
    ) -> dict[str, object]:
        return await adapter.create_stage(_validated_request(CreateStageRequest, locals()))

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
        return await adapter.update_stage(_validated_request(UpdateStageToolInput, locals()))

    @mcp.tool(
        name="followupboss_delete_stage",
        description="Delete a Follow Up Boss stage by ID and reassign linked action plans.",
    )
    async def followupboss_delete_stage(
        stage_id: int,
        assign_stage_id: int,
    ) -> dict[str, object]:
        return await adapter.delete_stage(_validated_request(DeleteStageToolInput, locals()))


def _register_task_tools(mcp: FastMCP, adapter: FollowUpBossToolAdapter) -> None:
    """Register task-related MCP tools.

    Args:
        mcp: The FastMCP server instance.
        adapter: The typed Follow Up Boss tool adapter.
    """

    @mcp.tool(
        name="followupboss_list_tasks",
        description=(
            "List Follow Up Boss tasks with documented filters and pagination metadata. "
            "Use this broad list only when the request provides explicit task filters "
            "or needs non-owned task discovery. For your overdue tasks, use "
            "followupboss_list_my_overdue_tasks. For your tasks due today, use "
            "followupboss_list_my_tasks_due_today. For your upcoming tasks after "
            "today, use followupboss_list_my_upcoming_tasks."
        ),
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
        return await adapter.list_tasks(_validated_request(TaskListRequest, locals()))

    @mcp.tool(
        name="followupboss_list_my_overdue_tasks",
        description=(
            "List incomplete overdue Follow Up Boss tasks assigned to the authenticated user. "
            "Use this for requests like 'my overdue tasks' or 'what am I late on?'. "
            "Resolves the authenticated user internally and forces incomplete overdue "
            "task scope."
        ),
    )
    async def followupboss_list_my_overdue_tasks(
        *,
        fields: list[str] | None = None,
        limit: int | None = None,
        next_token: str | None = None,
        offset: int | None = None,
    ) -> dict[str, object]:
        return await adapter.list_my_overdue_tasks(
            _validated_request(ListMyTaskIntentToolInput, locals())
        )

    @mcp.tool(
        name="followupboss_list_my_tasks_due_today",
        description=(
            "List incomplete Follow Up Boss tasks due today and assigned to the "
            "authenticated user. Use this for requests like 'my tasks today' or "
            "'what do I need to do today?'. Resolves the authenticated user "
            "internally and forces incomplete due-today task scope."
        ),
    )
    async def followupboss_list_my_tasks_due_today(
        *,
        fields: list[str] | None = None,
        limit: int | None = None,
        next_token: str | None = None,
        offset: int | None = None,
    ) -> dict[str, object]:
        return await adapter.list_my_tasks_due_today(
            _validated_request(ListMyTaskIntentToolInput, locals())
        )

    @mcp.tool(
        name="followupboss_list_my_upcoming_tasks",
        description=(
            "List incomplete Follow Up Boss tasks due after today and assigned to "
            "the authenticated user. Use this for requests like 'my upcoming tasks', "
            "'what do I have coming up?', or 'what is due after today?'. Resolves "
            "the authenticated user internally and forces incomplete future task scope."
        ),
    )
    async def followupboss_list_my_upcoming_tasks(
        *,
        fields: list[str] | None = None,
        limit: int | None = None,
        next_token: str | None = None,
        offset: int | None = None,
    ) -> dict[str, object]:
        return await adapter.list_my_upcoming_tasks(
            _validated_request(ListMyTaskIntentToolInput, locals())
        )

    @mcp.tool(
        name="followupboss_get_task",
        description="Fetch a single Follow Up Boss task by ID.",
    )
    async def followupboss_get_task(task_id: int) -> dict[str, object]:
        return await adapter.get_task(_validated_request(GetTaskToolInput, locals()))

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
        tool_input = _validated_request(CreateTaskRequest, locals())
        return await adapter.create_task(tool_input)

    @mcp.tool(
        name="followupboss_update_task",
        description=(
            "Update a Follow Up Boss task by explicit task_id. Do not infer the "
            "task_id from vague natural-language intent."
        ),
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
        return await adapter.update_task(_validated_request(UpdateTaskToolInput, locals()))

    @mcp.tool(
        name="followupboss_delete_task",
        description=(
            "Delete a Follow Up Boss task by explicit task_id. Do not infer the "
            "task_id from vague natural-language intent."
        ),
    )
    async def followupboss_delete_task(task_id: int) -> dict[str, object]:
        return await adapter.delete_task(_validated_request(DeleteTaskToolInput, locals()))


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
        return await adapter.list_team_inboxes(_validated_request(TeamInboxListRequest, locals()))


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
        return await adapter.list_teams(_validated_request(TeamListRequest, locals()))

    @mcp.tool(
        name="followupboss_get_team",
        description="Fetch a single Follow Up Boss team by ID.",
    )
    async def followupboss_get_team(team_id: int) -> dict[str, object]:
        return await adapter.get_team(_validated_request(GetTeamToolInput, locals()))

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
        return await adapter.create_team(_validated_request(CreateTeamRequest, locals()))

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
        return await adapter.update_team(_validated_request(UpdateTeamToolInput, locals()))

    @mcp.tool(
        name="followupboss_delete_team",
        description="Delete a Follow Up Boss team by ID, optionally moving members first.",
    )
    async def followupboss_delete_team(
        team_id: int,
        move_to_team_id: int | None = None,
    ) -> dict[str, object]:
        return await adapter.delete_team(_validated_request(DeleteTeamToolInput, locals()))


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
        return await adapter.list_templates(_validated_request(TemplateListRequest, locals()))

    @mcp.tool(
        name="followupboss_get_template",
        description="Fetch a single Follow Up Boss email template by ID.",
    )
    async def followupboss_get_template(
        template_id: int,
        *,
        merge_person_id: int | None = None,
    ) -> dict[str, object]:
        return await adapter.get_template(_validated_request(GetTemplateToolInput, locals()))

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
        return await adapter.merge_template(_validated_request(MergeTemplateRequest, locals()))

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
        return await adapter.create_template(_validated_request(CreateTemplateRequest, locals()))

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
        return await adapter.update_template(_validated_request(UpdateTemplateToolInput, locals()))

    @mcp.tool(
        name="followupboss_delete_template",
        description="Delete a Follow Up Boss email template by ID.",
    )
    async def followupboss_delete_template(template_id: int) -> dict[str, object]:
        return await adapter.delete_template(_validated_request(DeleteTemplateToolInput, locals()))


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
            _validated_request(TextMessageListRequest, locals())
        )

    @mcp.tool(
        name="followupboss_get_text_message",
        description="Fetch a single Follow Up Boss text message by ID.",
    )
    async def followupboss_get_text_message(text_message_id: int) -> dict[str, object]:
        return await adapter.get_text_message(_validated_request(GetTextMessageToolInput, locals()))

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
            _validated_request(CreateTextMessageRequest, locals())
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
            _validated_request(TextMessageTemplateListRequest, locals())
        )

    @mcp.tool(
        name="followupboss_get_text_message_template",
        description="Fetch a single Follow Up Boss text message template by ID.",
    )
    async def followupboss_get_text_message_template(template_id: int) -> dict[str, object]:
        return await adapter.get_text_message_template(
            _validated_request(GetTextMessageTemplateToolInput, locals())
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
            _validated_request(MergeTextMessageTemplateRequest, locals())
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
            _validated_request(CreateTextMessageTemplateRequest, locals())
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
            _validated_request(UpdateTextMessageTemplateToolInput, locals())
        )

    @mcp.tool(
        name="followupboss_delete_text_message_template",
        description="Delete a Follow Up Boss text message template by ID.",
    )
    async def followupboss_delete_text_message_template(template_id: int) -> dict[str, object]:
        return await adapter.delete_text_message_template(
            _validated_request(DeleteTextMessageTemplateToolInput, locals())
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
            _validated_request(CreateNoteRequest, locals(), exclude={"wait_for_person"}),
            wait_for_person=wait_for_person,
        )

    @mcp.tool(
        name="followupboss_get_note",
        description=(
            "Fetch a Follow Up Boss note by note ID only. Follow Up Boss has not made "
            "searching for notes associated with a FUB person ID available via the API; "
            "when users ask for notes by lead/person ID, explain that limitation and "
            "suggest asking support@followupboss.com to make that search possible."
        ),
    )
    async def followupboss_get_note(note_id: int) -> dict[str, object]:
        return await adapter.get_note(_validated_request(GetNoteToolInput, locals()))

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
        return await adapter.update_note(_validated_request(UpdateNoteToolInput, locals()))

    @mcp.tool(
        name="followupboss_delete_note",
        description="Delete a Follow Up Boss note by ID.",
    )
    async def followupboss_delete_note(note_id: int) -> dict[str, object]:
        return await adapter.delete_note(_validated_request(DeleteNoteToolInput, locals()))


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
        return await adapter.list_webhooks(_validated_request(WebhookListRequest, locals()))

    @mcp.tool(
        name="followupboss_get_webhook",
        description="Fetch a single Follow Up Boss webhook by ID.",
    )
    async def followupboss_get_webhook(webhook_id: int) -> dict[str, object]:
        return await adapter.get_webhook(_validated_request(GetWebhookToolInput, locals()))

    @mcp.tool(
        name="followupboss_get_webhook_event",
        description="Fetch a single Follow Up Boss webhook event by ID.",
    )
    async def followupboss_get_webhook_event(webhook_event_id: str) -> dict[str, object]:
        return await adapter.get_webhook_event(
            _validated_request(GetWebhookEventToolInput, locals())
        )

    @mcp.tool(
        name="followupboss_create_webhook",
        description="Create a Follow Up Boss webhook for a documented event name.",
    )
    async def followupboss_create_webhook(event: str, url: str) -> dict[str, object]:
        return await adapter.create_webhook(_validated_request(CreateWebhookRequest, locals()))

    @mcp.tool(
        name="followupboss_update_webhook",
        description="Update a Follow Up Boss webhook by ID.",
    )
    async def followupboss_update_webhook(
        webhook_id: int,
        *,
        event: str | None = None,
        status: str | None = None,
        url: str | None = None,
    ) -> dict[str, object]:
        return await adapter.update_webhook(_validated_request(UpdateWebhookToolInput, locals()))

    @mcp.tool(
        name="followupboss_delete_webhook",
        description="Delete a Follow Up Boss webhook by ID.",
    )
    async def followupboss_delete_webhook(webhook_id: int) -> dict[str, object]:
        return await adapter.delete_webhook(_validated_request(DeleteWebhookToolInput, locals()))


def _register_resources_and_prompts(
    mcp: FastMCP,
    *,
    project_root: Path,
    tenant_runtime_factory: TenantRuntimeFactory | None,
) -> None:
    """Register MCP resources and prompts.

    Args:
        mcp: The FastMCP server instance.
        project_root: The repository root used for file-backed resources.
        tenant_runtime_factory: Optional hosted runtime factory used to resolve
            tenant context for resource and prompt handlers.
    """

    @mcp.resource(
        _API_COVERAGE_RESOURCE_URI,
        title="Follow Up Boss API Coverage Matrix",
        description="Repository API coverage matrix for Follow Up Boss endpoints.",
        mime_type="text/markdown",
    )
    async def followupboss_api_coverage_matrix() -> str:
        resource_text = (project_root / "docs" / "api-coverage-matrix.md").read_text(
            encoding="utf-8"
        )
        runtime = await _resolve_surface_runtime(
            surface_name=_API_COVERAGE_RESOURCE_URI,
            public_surface_names=_HOSTED_PUBLIC_RESOURCE_URIS,
            tenant_runtime_factory=tenant_runtime_factory,
        )
        return _render_api_coverage_matrix_resource(
            resource_text=resource_text,
            runtime=runtime,
        )

    @mcp.prompt(
        name=_COMPOSE_LEAD_EVENT_PROMPT_NAME,
        description="Compose a canonical POST /events payload for a new lead or lead activity.",
    )
    async def followupboss_compose_lead_event(
        source: str,
        type: str,
        message: str,
        email: str,
        *,
        first_name: str = "",
        last_name: str = "",
    ) -> str:
        runtime = await _resolve_surface_runtime(
            surface_name=_COMPOSE_LEAD_EVENT_PROMPT_NAME,
            public_surface_names=_HOSTED_PUBLIC_PROMPT_NAMES,
            tenant_runtime_factory=tenant_runtime_factory,
        )
        return _render_compose_lead_event_prompt(
            source=source,
            type=type,
            message=message,
            email=email,
            first_name=first_name,
            last_name=last_name,
            runtime=runtime,
        )
