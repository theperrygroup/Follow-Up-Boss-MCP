"""Typed MCP tool adapter layer."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from contextvars import ContextVar
from dataclasses import asdict
from typing import Any, cast

from pydantic import field_validator, model_validator

from followupboss_mcp.errors import FollowUpBossError, FollowUpBossRateLimitError
from followupboss_mcp.models.action_plans import (
    ActionPlanListRequest,
    ActionPlanPersonListRequest,
    CreateActionPlanPersonRequest,
    UpdateActionPlanPersonRequest,
)
from followupboss_mcp.models.appointment_metadata import (
    AppointmentOutcomeListRequest,
    AppointmentTypeListRequest,
    CreateAppointmentOutcomeRequest,
    CreateAppointmentTypeRequest,
    DeleteAppointmentOutcomeRequest,
    DeleteAppointmentTypeRequest,
    UpdateAppointmentOutcomeRequest,
    UpdateAppointmentTypeRequest,
)
from followupboss_mcp.models.appointments import (
    AppointmentListRequest,
    CreateAppointmentRequest,
    UpdateAppointmentRequest,
)
from followupboss_mcp.models.attachments import (
    CreateDealAttachmentRequest,
    CreatePersonAttachmentRequest,
    UpdateDealAttachmentRequest,
    UpdatePersonAttachmentRequest,
)
from followupboss_mcp.models.automations import (
    AutomationListRequest,
    AutomationPeopleListRequest,
    CreateAutomationPersonRequest,
    UpdateAutomationPersonRequest,
)
from followupboss_mcp.models.calls import (
    CallListRequest,
    CreateCallRequest,
    UpdateCallRequest,
)
from followupboss_mcp.models.common import RequestModel, ResponseModel
from followupboss_mcp.models.custom_fields import (
    CreateCustomFieldRequest,
    CustomFieldListRequest,
    UpdateCustomFieldRequest,
)
from followupboss_mcp.models.deals import (
    CreateDealCustomFieldRequest,
    CreateDealRequest,
    DealCustomFieldListRequest,
    DealListRequest,
    UpdateDealCustomFieldRequest,
    UpdateDealRequest,
)
from followupboss_mcp.models.email_marketing import (
    CreateEmailCampaignRequest,
    CreateEmailEventsBatchRequest,
    EmailCampaignListRequest,
    EmailEventListRequest,
    UpdateEmailCampaignRequest,
)
from followupboss_mcp.models.events import CreateEventRequest, EventSearchRequest
from followupboss_mcp.models.groups import (
    CreateGroupRequest,
    GroupListRequest,
    UpdateGroupRequest,
)
from followupboss_mcp.models.inbox_apps import (
    CreateInboxAppMessageRequest,
    CreateInboxAppNoteRequest,
    CreateInboxAppParticipantRequest,
    InstallInboxAppRequest,
    UpdateInboxAppConversationRequest,
    UpdateInboxAppMessageRequest,
)
from followupboss_mcp.models.notes import CreateNoteRequest, UpdateNoteRequest
from followupboss_mcp.models.people import (
    ClaimPersonRequest,
    CreatePersonRequest,
    IgnoreUnclaimedPersonRequest,
    PeopleSearchRequest,
    PersonDuplicateCheckRequest,
    PersonLookupRequest,
    PersonRecord,
    UnclaimedPeopleListRequest,
    UpdatePersonRequest,
)
from followupboss_mcp.models.people_relationships import (
    CreatePeopleRelationshipRequest,
    PeopleRelationshipListRequest,
    UpdatePeopleRelationshipRequest,
)
from followupboss_mcp.models.pipelines import (
    CreatePipelineRequest,
    PipelineListRequest,
    UpdatePipelineRequest,
)
from followupboss_mcp.models.ponds import (
    CreatePondRequest,
    DeletePondRequest,
    PondListRequest,
    UpdatePondRequest,
)
from followupboss_mcp.models.reactions import (
    CreateReactionRequest,
    DeleteReactionRequest,
    ReactionRefType,
)
from followupboss_mcp.models.smart_lists import SmartListListRequest, SmartListRecord
from followupboss_mcp.models.stages import (
    CreateStageRequest,
    DeleteStageRequest,
    StageListRequest,
    UpdateStageRequest,
)
from followupboss_mcp.models.tasks import (
    CreateTaskRequest,
    TaskListRequest,
    TaskRecord,
    UpdateTaskRequest,
)
from followupboss_mcp.models.team_inboxes import TeamInboxListRequest
from followupboss_mcp.models.teams import (
    CreateTeamRequest,
    DeleteTeamRequest,
    TeamListRequest,
    UpdateTeamRequest,
)
from followupboss_mcp.models.templates import (
    CreateTemplateRequest,
    MergeTemplateRequest,
    TemplateListRequest,
    TemplateLookupRequest,
    UpdateTemplateRequest,
)
from followupboss_mcp.models.text_messages import (
    CreateTextMessageRequest,
    CreateTextMessageTemplateRequest,
    MergeTextMessageTemplateRequest,
    TextMessageListRequest,
    TextMessageTemplateListRequest,
    UpdateTextMessageTemplateRequest,
)
from followupboss_mcp.models.timeframes import TimeframeListRequest
from followupboss_mcp.models.users import DeleteUserRequest, UserListRequest, UserRecord
from followupboss_mcp.models.webhooks import (
    CreateWebhookRequest,
    UpdateWebhookRequest,
    WebhookListRequest,
)
from followupboss_mcp.pagination import PageResult, PaginationMetadata
from followupboss_mcp.task_intents import upcoming_task_due_start as _upcoming_task_due_start
from followupboss_mcp.tenant_runtime import ServiceBundle, ServiceBundleResolver

_ACTIVE_SERVICE_BUNDLE: ContextVar[ServiceBundle | None] = ContextVar(
    "followupboss_active_service_bundle",
    default=None,
)
_LATEST_LEAD_RESPONSE_FIELDS = frozenset(
    {
        "id",
        "name",
        "firstName",
        "lastName",
        "created",
        "assignedUserId",
        "stage",
        "source",
        "lastActivity",
    }
)
_TASK_INTENT_RESPONSE_FIELDS = frozenset(
    {
        "id",
        "name",
        "dueDate",
        "assignedUserId",
        "personId",
        "isCompleted",
        "type",
    }
)
_UNCOMMUNICATED_LEAD_RESPONSE_FIELDS = frozenset(
    {
        "id",
        "name",
        "firstName",
        "lastName",
        "created",
        "assignedUserId",
        "assignedTo",
        "stage",
        "source",
        "lastActivity",
        "lastCommunication",
        "contacted",
        "emails",
        "phones",
    }
)
_UNCOMMUNICATED_LEAD_FILTER_FIELDS = frozenset({"id", "lastCommunication"})


class GetPersonToolInput(PersonLookupRequest):
    """Tool input for fetching a person by ID."""

    person_id: int


class GetLatestLeadToolInput(RequestModel):
    """Tool input for fetching the authenticated user's latest assigned lead."""

    fields: list[str] | None = None

    @field_validator("fields")
    @classmethod
    def _validate_fields(cls, value: list[str] | None) -> list[str] | None:
        """Validate person projection fields for the latest-lead helper.

        Args:
            value: Optional field names requested by the MCP caller.

        Returns:
            The original field list when every field is supported.

        Raises:
            ValueError: If any requested field is not supported by the narrow
                latest-lead helper.
        """
        if value is None:
            return None
        invalid_fields = sorted(set(value) - _LATEST_LEAD_RESPONSE_FIELDS)
        if invalid_fields:
            allowed_fields = ", ".join(sorted(_LATEST_LEAD_RESPONSE_FIELDS))
            invalid = ", ".join(invalid_fields)
            raise ValueError(
                f"Unsupported latest-lead fields: {invalid}. Allowed fields: {allowed_fields}."
            )
        return value


class SearchPeopleInSmartListToolInput(RequestModel):
    """Tool input for searching people inside one named smart list."""

    smart_list_name: str | None = None
    smart_list: str | None = None
    list_name: str | None = None
    assigned_user_id: int | None = None
    assigned_user_name: str | None = None
    owner_name: str | None = None
    agent_name: str | None = None
    fields: list[str] | None = None
    limit: int | None = None
    lead_source: str | None = None
    mine: bool = True
    next_token: str | None = None
    offset: int | None = None
    source: str | None = None
    source_name: str | None = None
    stage: str | None = None

    @field_validator("assigned_user_id")
    @classmethod
    def _validate_assigned_user_id(cls, value: int | None) -> int | None:
        """Require explicit owner IDs to be positive when supplied.

        Args:
            value: Candidate Follow Up Boss user ID.

        Returns:
            The validated user ID or `None`.

        Raises:
            ValueError: If the user ID is not positive.
        """
        if value is not None and value <= 0:
            raise ValueError("assigned_user_id must be a positive Follow Up Boss user ID.")
        return value

    @model_validator(mode="after")
    def _normalize_aliases(self) -> SearchPeopleInSmartListToolInput:
        """Normalize smart-list, source, and owner-name aliases.

        Returns:
            The validated helper input.

        Raises:
            ValueError: If no smart-list name is provided, or if aliases provide
                conflicting values.
        """
        self.smart_list_name = _coalesce_text_aliases(
            (
                ("smart_list_name", self.smart_list_name),
                ("smart_list", self.smart_list),
                ("list_name", self.list_name),
            ),
            required_name="smart_list_name",
        )
        self.source = _coalesce_text_aliases(
            (
                ("source", self.source),
                ("lead_source", self.lead_source),
                ("source_name", self.source_name),
            ),
            required_name=None,
        )
        self.assigned_user_name = _coalesce_text_aliases(
            (
                ("assigned_user_name", self.assigned_user_name),
                ("owner_name", self.owner_name),
                ("agent_name", self.agent_name),
            ),
            required_name=None,
        )
        return self

    async def resolved_assigned_user_id(
        self,
        services: ServiceBundle,
    ) -> int | None:
        """Return the assigned-user scope for this smart-list search.

        Args:
            services: Active service bundle used to resolve authenticated-user
                identity when `mine` is true.

        Returns:
            The explicit assigned user, authenticated user, or `None` for
            intentionally account-wide searches.

        Raises:
            RuntimeError: If `mine` is true but the authenticated identity does
                not include a Follow Up Boss user ID.
        """
        if self.assigned_user_id is not None:
            return self.assigned_user_id
        if self.assigned_user_name is not None:
            return await self._resolve_user_id_by_name(services, self.assigned_user_name)
        if not self.mine:
            return None
        identity = await services.identity.get_identity()
        if identity.id is None:
            raise RuntimeError("Authenticated Follow Up Boss user id is unavailable.")
        return identity.id

    async def _resolve_user_id_by_name(
        self,
        services: ServiceBundle,
        assigned_user_name: str,
    ) -> int:
        """Resolve a Follow Up Boss user name to one exact active user ID.

        Args:
            services: Active service bundle used to search users.
            assigned_user_name: User-provided owner or agent name.

        Returns:
            The unique matching Follow Up Boss user ID.

        Raises:
            RuntimeError: If no active user or more than one active user matches
                the normalized name.
        """
        users = await self._list_all_users_for_name(services, assigned_user_name)
        normalized_name = _normalize_user_name(assigned_user_name)
        matches = [
            user
            for user in users
            if _normalize_user_name(user.name or _user_full_name(user)) == normalized_name
            and _is_active_user(user)
        ]
        if not matches:
            raise RuntimeError(
                f"Active Follow Up Boss user named {assigned_user_name!r} was not found."
            )
        if len(matches) > 1:
            match_ids = [user.id for user in matches]
            raise RuntimeError(
                f"Active Follow Up Boss user named {assigned_user_name!r} is ambiguous; "
                f"matched IDs {match_ids!r}."
            )
        return matches[0].id

    async def _list_all_users_for_name(
        self,
        services: ServiceBundle,
        assigned_user_name: str,
    ) -> list[UserRecord]:
        """List all user-search pages for an owner-name lookup.

        Args:
            services: Active service bundle used to search users.
            assigned_user_name: Name query to send to Follow Up Boss.

        Returns:
            User records returned by the paginated users endpoint.
        """
        users: list[UserRecord] = []
        offset = 0
        while True:
            page = await services.users.list_users(
                UserListRequest(
                    include_deleted=False,
                    limit=100,
                    name=assigned_user_name,
                    offset=offset,
                )
            )
            users.extend(page.items)
            if not page.metadata.has_next() or page.metadata.count == 0:
                return users
            offset = page.metadata.offset + page.metadata.count

    def resolved_smart_list_name(self) -> str:
        """Return the normalized smart-list name after validation.

        Returns:
            The smart-list name used for helper resolution.

        Raises:
            RuntimeError: If the model was somehow used before validation
                normalized the smart-list name.
        """
        if self.smart_list_name is None:
            raise RuntimeError("smart_list_name must be normalized before helper execution.")
        return self.smart_list_name


class ListUncontactedLeadsToolInput(RequestModel):
    """Tool input for direct no-communication lead searches."""

    assigned_user_id: int | None = None
    assigned_user_name: str | None = None
    owner_name: str | None = None
    agent_name: str | None = None
    fields: list[str] | None = None
    lead_source: str | None = None
    mine: bool = True
    next_token: str | None = None
    offset: int | None = None
    limit: int | None = None
    source: str | None = None
    source_name: str | None = None
    stage: str | None = None

    @field_validator("assigned_user_id")
    @classmethod
    def _validate_assigned_user_id(cls, value: int | None) -> int | None:
        """Require explicit owner IDs to be positive when supplied.

        Args:
            value: Candidate Follow Up Boss owner user ID.

        Returns:
            The validated user ID or `None`.

        Raises:
            ValueError: If the owner user ID is not positive.
        """
        if value is not None and value <= 0:
            raise ValueError("assigned_user_id must be a positive Follow Up Boss user ID.")
        return value

    @field_validator("fields")
    @classmethod
    def _validate_fields(cls, value: list[str] | None) -> list[str] | None:
        """Validate person projection fields for no-communication helpers.

        Args:
            value: Optional field names requested by the MCP caller.

        Returns:
            The original field list when every field is supported.

        Raises:
            ValueError: If any requested field is not supported by the helper.
        """
        if value is None:
            return None
        invalid_fields = sorted(set(value) - _UNCOMMUNICATED_LEAD_RESPONSE_FIELDS)
        if invalid_fields:
            allowed_fields = ", ".join(sorted(_UNCOMMUNICATED_LEAD_RESPONSE_FIELDS))
            invalid = ", ".join(invalid_fields)
            raise ValueError(
                f"Unsupported no-communication lead fields: {invalid}. "
                f"Allowed fields: {allowed_fields}."
            )
        return value

    @model_validator(mode="after")
    def _normalize_aliases(self) -> ListUncontactedLeadsToolInput:
        """Normalize owner-name and source aliases.

        Returns:
            The validated helper input with canonical alias fields populated.

        Raises:
            ValueError: If aliases provide conflicting values.
        """
        self.assigned_user_name = _coalesce_text_aliases(
            (
                ("assigned_user_name", self.assigned_user_name),
                ("owner_name", self.owner_name),
                ("agent_name", self.agent_name),
            ),
            required_name=None,
        )
        self.source = _coalesce_text_aliases(
            (
                ("source", self.source),
                ("lead_source", self.lead_source),
                ("source_name", self.source_name),
            ),
            required_name=None,
        )
        return self

    async def resolved_assigned_user_id(self, services: ServiceBundle) -> int | None:
        """Return the owner scope for the uncontacted-leads search.

        Args:
            services: Active service bundle used for identity and owner-name
                resolution.

        Returns:
            The explicit owner ID, resolved owner-name ID, authenticated user ID,
            or `None` for an intentionally account-wide search.

        Raises:
            RuntimeError: If `mine` is true but the authenticated identity has no
                Follow Up Boss user ID, or if owner-name resolution fails.
        """
        if self.assigned_user_id is not None:
            return self.assigned_user_id
        if self.assigned_user_name is not None:
            return await self._resolve_user_id_by_name(services, self.assigned_user_name)
        if not self.mine:
            return None
        identity = await services.identity.get_identity()
        if identity.id is None:
            raise RuntimeError("Authenticated Follow Up Boss user id is unavailable.")
        return identity.id

    async def _resolve_user_id_by_name(
        self,
        services: ServiceBundle,
        assigned_user_name: str,
    ) -> int:
        """Resolve a Follow Up Boss owner name to one exact active user ID.

        Args:
            services: Active service bundle used to search users.
            assigned_user_name: User-provided owner or agent name.

        Returns:
            The unique matching Follow Up Boss user ID.

        Raises:
            RuntimeError: If no active user or more than one active user matches
                the normalized name.
        """
        users = await self._list_all_users_for_name(services, assigned_user_name)
        normalized_name = _normalize_user_name(assigned_user_name)
        matches = [
            user
            for user in users
            if _normalize_user_name(user.name or _user_full_name(user)) == normalized_name
            and _is_active_user(user)
        ]
        if not matches:
            raise RuntimeError(
                f"Active Follow Up Boss user named {assigned_user_name!r} was not found."
            )
        if len(matches) > 1:
            match_ids = [user.id for user in matches]
            raise RuntimeError(
                f"Active Follow Up Boss user named {assigned_user_name!r} is ambiguous; "
                f"matched IDs {match_ids!r}."
            )
        return matches[0].id

    async def _list_all_users_for_name(
        self,
        services: ServiceBundle,
        assigned_user_name: str,
    ) -> list[UserRecord]:
        """List all user-search pages for an owner-name lookup.

        Args:
            services: Active service bundle used to search users.
            assigned_user_name: Name query to send to Follow Up Boss.

        Returns:
            User records returned by the paginated users endpoint.
        """
        users: list[UserRecord] = []
        offset = 0
        while True:
            page = await services.users.list_users(
                UserListRequest(
                    include_deleted=False,
                    limit=100,
                    name=assigned_user_name,
                    offset=offset,
                )
            )
            users.extend(page.items)
            if not page.metadata.has_next() or page.metadata.count == 0:
                return users
            offset = page.metadata.offset + page.metadata.count


class ListMyTaskIntentToolInput(RequestModel):
    """Tool input for listing the authenticated user's intent-scoped tasks."""

    fields: list[str] | None = None
    limit: int | None = None
    next_token: str | None = None
    offset: int | None = None

    @field_validator("fields")
    @classmethod
    def _validate_fields(cls, value: list[str] | None) -> list[str] | None:
        """Validate task projection fields for owned task intent helpers.

        Args:
            value: Optional field names requested by the MCP caller.

        Returns:
            The original field list when every field is supported.

        Raises:
            ValueError: If any requested field is not supported by the narrow
                owned-task helpers.
        """
        if value is None:
            return None
        invalid_fields = sorted(set(value) - _TASK_INTENT_RESPONSE_FIELDS)
        if invalid_fields:
            allowed_fields = ", ".join(sorted(_TASK_INTENT_RESPONSE_FIELDS))
            invalid = ", ".join(invalid_fields)
            raise ValueError(
                f"Unsupported task fields for owned task helpers: {invalid}. "
                f"Allowed fields: {allowed_fields}."
            )
        return value


class ListActiveDealsForPersonToolInput(RequestModel):
    """Tool input for listing active deals tied to one person."""

    person_id: int


class ListPersonActivityToolInput(RequestModel):
    """Tool input for listing communication and activity records for one person."""

    person_id: int
    include_appointments: bool = True
    include_calls: bool = True
    include_email_events: bool = True
    include_events: bool = True
    include_text_messages: bool = True
    limit: int | None = None
    offset: int | None = None

    @model_validator(mode="after")
    def _require_one_activity_surface(self) -> ListPersonActivityToolInput:
        """Require at least one activity surface to be selected.

        Returns:
            The validated tool input.

        Raises:
            ValueError: If all activity surfaces are disabled.
        """
        if not any(
            (
                self.include_appointments,
                self.include_calls,
                self.include_email_events,
                self.include_events,
                self.include_text_messages,
            )
        ):
            raise ValueError("At least one person activity surface must be selected.")
        return self


class CheckDuplicatePersonToolInput(PersonDuplicateCheckRequest):
    """Tool input for checking whether a person already exists."""


class GetPersonAttachmentToolInput(RequestModel):
    """Tool input for fetching a person attachment by ID."""

    person_attachment_id: int


class GetReactionToolInput(RequestModel):
    """Tool input for fetching a reaction by ID."""

    reaction_id: int


class GetThreadedReplyToolInput(RequestModel):
    """Tool input for fetching a threaded reply by ID."""

    threaded_reply_id: int


class GetPeopleRelationshipToolInput(RequestModel):
    """Tool input for fetching a people relationship by ID."""

    people_relationship_id: int


class UpdatePersonToolInput(UpdatePersonRequest):
    """Tool input for updating a person."""

    person_id: int


class GetUserToolInput(RequestModel):
    """Tool input for fetching a user by ID."""

    user_id: int


class DeletePersonToolInput(RequestModel):
    """Tool input for deleting a person."""

    person_id: int


class DeleteUserToolInput(DeleteUserRequest):
    """Tool input for deleting a user."""

    user_id: int


class GetCustomFieldToolInput(RequestModel):
    """Tool input for fetching a custom field by ID."""

    custom_field_id: int


class GetNoteToolInput(RequestModel):
    """Tool input for fetching a note by ID."""

    note_id: int


class GetTaskToolInput(RequestModel):
    """Tool input for fetching a task by ID."""

    task_id: int


class GetCallToolInput(RequestModel):
    """Tool input for fetching a call by ID."""

    call_id: int


class GetAppointmentToolInput(RequestModel):
    """Tool input for fetching an appointment by ID."""

    appointment_id: int


class GetAutomationToolInput(RequestModel):
    """Tool input for fetching an automation by ID."""

    automation_id: int


class GetAutomationPersonToolInput(RequestModel):
    """Tool input for fetching an automation-person pairing by ID."""

    automation_person_id: int


class GetAppointmentOutcomeToolInput(RequestModel):
    """Tool input for fetching an appointment outcome by ID."""

    appointment_outcome_id: int


class GetAppointmentTypeToolInput(RequestModel):
    """Tool input for fetching an appointment type by ID."""

    appointment_type_id: int


class GetDealToolInput(RequestModel):
    """Tool input for fetching a deal by ID."""

    deal_id: int


class GetDealCustomFieldToolInput(RequestModel):
    """Tool input for fetching a deal custom field by ID."""

    deal_custom_field_id: int


class GetDealAttachmentToolInput(RequestModel):
    """Tool input for fetching a deal attachment by ID."""

    deal_attachment_id: int


class GetPipelineToolInput(RequestModel):
    """Tool input for fetching a pipeline by ID."""

    pipeline_id: int


class GetPondToolInput(RequestModel):
    """Tool input for fetching a pond by ID."""

    pond_id: int


class GetSmartListToolInput(RequestModel):
    """Tool input for fetching a smart list by ID."""

    smart_list_id: int


class GetStageToolInput(RequestModel):
    """Tool input for fetching a stage by ID."""

    stage_id: int


class GetTeamToolInput(RequestModel):
    """Tool input for fetching a team by ID."""

    team_id: int


class GetTextMessageToolInput(RequestModel):
    """Tool input for fetching a text message by ID."""

    text_message_id: int


class GetTextMessageTemplateToolInput(RequestModel):
    """Tool input for fetching a text message template by ID."""

    template_id: int


class GetTemplateToolInput(TemplateLookupRequest):
    """Tool input for fetching a template by ID."""

    template_id: int


class GetEventToolInput(RequestModel):
    """Tool input for fetching an event by ID."""

    event_id: int


class GetGroupToolInput(RequestModel):
    """Tool input for fetching a group by ID."""

    group_id: int


class ListInboxAppInstallationsToolInput(RequestModel):
    """Tool input for listing inbox app installations."""

    published_inbox_app_id: int


class ListInboxAppParticipantsToolInput(RequestModel):
    """Tool input for listing inbox app conversation participants."""

    ext_conversation_id: str
    inbox_app_id: int


class AddInboxAppMessageToolInput(CreateInboxAppMessageRequest):
    """Tool input for adding an inbox app message."""

    inbox_app_id: int


class ClaimPersonToolInput(ClaimPersonRequest):
    """Tool input for claiming an unclaimed person."""


class AddReactionToolInput(CreateReactionRequest):
    """Tool input for adding a reaction."""

    ref_id: int
    ref_type: ReactionRefType


class AddInboxAppNoteToolInput(CreateInboxAppNoteRequest):
    """Tool input for adding an inbox app note."""

    inbox_app_id: int


class GetWebhookToolInput(RequestModel):
    """Tool input for fetching a webhook by ID."""

    webhook_id: int


class GetWebhookEventToolInput(RequestModel):
    """Tool input for fetching a webhook event by ID."""

    webhook_event_id: str


class UpdateNoteToolInput(UpdateNoteRequest):
    """Tool input for updating a note."""

    note_id: int


class UpdateTaskToolInput(UpdateTaskRequest):
    """Tool input for updating a task."""

    task_id: int


class UpdateWebhookToolInput(UpdateWebhookRequest):
    """Tool input for updating a webhook."""

    webhook_id: int


class UpdateCallToolInput(UpdateCallRequest):
    """Tool input for updating a call."""

    call_id: int


class UpdateAppointmentToolInput(UpdateAppointmentRequest):
    """Tool input for updating an appointment."""

    appointment_id: int


class UpdateAppointmentOutcomeToolInput(UpdateAppointmentOutcomeRequest):
    """Tool input for updating an appointment outcome."""

    appointment_outcome_id: int


class UpdateAppointmentTypeToolInput(UpdateAppointmentTypeRequest):
    """Tool input for updating an appointment type."""

    appointment_type_id: int


class UpdateActionPlanPersonToolInput(UpdateActionPlanPersonRequest):
    """Tool input for updating an action-plan-person relationship."""

    action_plan_person_id: int


class UpdateAutomationPersonToolInput(UpdateAutomationPersonRequest):
    """Tool input for updating an automation-person pairing."""

    automation_person_id: int


class UpdateGroupToolInput(UpdateGroupRequest):
    """Tool input for updating a group."""

    group_id: int


class AddInboxAppParticipantToolInput(CreateInboxAppParticipantRequest):
    """Tool input for adding an inbox app conversation participant."""

    ext_conversation_id: str
    inbox_app_id: int


class UpdatePersonAttachmentToolInput(UpdatePersonAttachmentRequest):
    """Tool input for updating a person attachment."""

    person_attachment_id: int


class UpdatePeopleRelationshipToolInput(UpdatePeopleRelationshipRequest):
    """Tool input for updating a people relationship."""

    people_relationship_id: int


class UpdateDealAttachmentToolInput(UpdateDealAttachmentRequest):
    """Tool input for updating a deal attachment."""

    deal_attachment_id: int


class UpdateEmailCampaignToolInput(UpdateEmailCampaignRequest):
    """Tool input for updating an email marketing campaign."""

    email_campaign_id: int


class UpdateCustomFieldToolInput(UpdateCustomFieldRequest):
    """Tool input for updating a custom field."""

    custom_field_id: int


class UpdateInboxAppConversationToolInput(UpdateInboxAppConversationRequest):
    """Tool input for updating an inbox app conversation."""

    ext_conversation_id: str
    inbox_app_id: int


class UpdateInboxAppMessageToolInput(UpdateInboxAppMessageRequest):
    """Tool input for updating an inbox app message."""

    inbox_app_id: int


class UpdateDealToolInput(UpdateDealRequest):
    """Tool input for updating a deal."""

    deal_id: int


class UpdateDealCustomFieldToolInput(UpdateDealCustomFieldRequest):
    """Tool input for updating a deal custom field."""

    deal_custom_field_id: int


class UpdatePipelineToolInput(UpdatePipelineRequest):
    """Tool input for updating a pipeline."""

    pipeline_id: int


class UpdatePondToolInput(UpdatePondRequest):
    """Tool input for updating a pond."""

    pond_id: int


class UpdateStageToolInput(UpdateStageRequest):
    """Tool input for updating a stage."""

    stage_id: int


class UpdateTeamToolInput(UpdateTeamRequest):
    """Tool input for updating a team."""

    team_id: int


class UpdateTextMessageTemplateToolInput(UpdateTextMessageTemplateRequest):
    """Tool input for updating a text message template."""

    template_id: int


class UpdateTemplateToolInput(UpdateTemplateRequest):
    """Tool input for updating a template."""

    template_id: int


class DeleteNoteToolInput(RequestModel):
    """Tool input for deleting a note."""

    note_id: int


class DeleteTaskToolInput(RequestModel):
    """Tool input for deleting a task."""

    task_id: int


class DeleteTemplateToolInput(RequestModel):
    """Tool input for deleting a template."""

    template_id: int


class DeleteAppointmentToolInput(RequestModel):
    """Tool input for deleting an appointment."""

    appointment_id: int


class DeleteAppointmentOutcomeToolInput(DeleteAppointmentOutcomeRequest):
    """Tool input for deleting an appointment outcome."""

    appointment_outcome_id: int


class DeleteAppointmentTypeToolInput(DeleteAppointmentTypeRequest):
    """Tool input for deleting an appointment type."""

    appointment_type_id: int


class DeleteGroupToolInput(RequestModel):
    """Tool input for deleting a group."""

    group_id: int


class DeactivateInboxAppToolInput(RequestModel):
    """Tool input for deactivating an inbox app installation."""

    inbox_app_id: int


class DeleteDealToolInput(RequestModel):
    """Tool input for deleting a deal."""

    deal_id: int


class DeleteDealCustomFieldToolInput(RequestModel):
    """Tool input for deleting a deal custom field."""

    deal_custom_field_id: int


class DeletePipelineToolInput(RequestModel):
    """Tool input for deleting a pipeline."""

    pipeline_id: int


class DeletePondToolInput(DeletePondRequest):
    """Tool input for deleting a pond."""

    pond_id: int


class DeleteStageToolInput(DeleteStageRequest):
    """Tool input for deleting a stage."""

    stage_id: int


class DeleteTeamToolInput(DeleteTeamRequest):
    """Tool input for deleting a team."""

    team_id: int


class DeleteInboxAppParticipantToolInput(RequestModel):
    """Tool input for removing an inbox app participant."""

    ext_conversation_id: str
    inbox_app_id: int
    participant_id: int


class DeletePeopleRelationshipToolInput(RequestModel):
    """Tool input for deleting a people relationship."""

    people_relationship_id: int


class DeletePersonAttachmentToolInput(RequestModel):
    """Tool input for deleting a person attachment."""

    person_attachment_id: int


class IgnoreUnclaimedPersonToolInput(IgnoreUnclaimedPersonRequest):
    """Tool input for ignoring an unclaimed person offer."""


class DeleteReactionToolInput(DeleteReactionRequest):
    """Tool input for deleting a reaction."""

    ref_id: int
    ref_type: ReactionRefType


class DeleteCustomFieldToolInput(RequestModel):
    """Tool input for deleting a custom field."""

    custom_field_id: int


class DeleteDealAttachmentToolInput(RequestModel):
    """Tool input for deleting a deal attachment."""

    deal_attachment_id: int


class DeleteTextMessageTemplateToolInput(RequestModel):
    """Tool input for deleting a text message template."""

    template_id: int


class DeleteWebhookToolInput(RequestModel):
    """Tool input for deleting a webhook."""

    webhook_id: int


class FollowUpBossToolAdapter:
    """Thin MCP-safe adapter around typed domain services."""

    def __init__(self, services: ServiceBundle | ServiceBundleResolver) -> None:
        """Initialize the adapter.

        Args:
            services: Either one fixed service bundle or a resolver that creates
                a tenant-specific bundle for each call.
        """
        self._fixed_services: ServiceBundle | None
        self._service_bundle_resolver: ServiceBundleResolver | None
        if isinstance(services, ServiceBundle):
            self._fixed_services = services
            self._service_bundle_resolver = None
        else:
            self._fixed_services = None
            self._service_bundle_resolver = services

    @property
    def _services(self) -> ServiceBundle:
        """Return the active service bundle for the current tool call.

        Returns:
            The static service bundle for single-tenant flows or the request-
            scoped bundle resolved for the active hosted call.

        Raises:
            RuntimeError: If a tenant-scoped bundle is requested outside an
                active resolved runtime.
        """
        if self._fixed_services is not None:
            return self._fixed_services
        active_services = _ACTIVE_SERVICE_BUNDLE.get()
        if active_services is None:
            raise RuntimeError("Tenant runtime is unavailable.")
        return active_services

    async def get_identity(self) -> dict[str, Any]:
        """Return identity information."""
        return await self._single_result(lambda: self._services.identity.get_identity())

    async def list_action_plans(self, tool_input: ActionPlanListRequest) -> dict[str, Any]:
        """List action plans."""
        return await self._page_result(
            lambda: self._services.action_plans.list_action_plans(tool_input),
            key="actionPlans",
        )

    async def list_action_plan_people(
        self,
        tool_input: ActionPlanPersonListRequest,
    ) -> dict[str, Any]:
        """List action-plan-person relationships."""
        return await self._page_result(
            lambda: self._services.action_plans.list_action_plan_people(tool_input),
            key="actionPlansPeople",
        )

    async def apply_action_plan(
        self,
        tool_input: CreateActionPlanPersonRequest,
    ) -> dict[str, Any]:
        """Apply an action plan to a person."""
        return await self._single_result(
            lambda: self._services.action_plans.apply_action_plan(tool_input)
        )

    async def update_action_plan_person(
        self,
        tool_input: UpdateActionPlanPersonToolInput,
    ) -> dict[str, Any]:
        """Update an action-plan-person relationship."""
        request = UpdateActionPlanPersonRequest.model_validate(
            tool_input.model_dump(exclude={"action_plan_person_id"})
        )
        return await self._single_result(
            lambda: self._services.action_plans.update_action_plan_person(
                tool_input.action_plan_person_id,
                request,
            )
        )

    async def list_automations(self, tool_input: AutomationListRequest) -> dict[str, Any]:
        """List automations."""
        return await self._page_result(
            lambda: self._services.automations.list_automations(tool_input),
            key="automations",
        )

    async def get_automation(self, tool_input: GetAutomationToolInput) -> dict[str, Any]:
        """Get an automation."""
        return await self._single_result(
            lambda: self._services.automations.get_automation(tool_input.automation_id)
        )

    async def list_automation_people(
        self,
        tool_input: AutomationPeopleListRequest,
    ) -> dict[str, Any]:
        """List automation-person pairings."""
        return await self._page_result(
            lambda: self._services.automation_people.list_automation_people(tool_input),
            key="automationsPeople",
        )

    async def get_automation_person(
        self,
        tool_input: GetAutomationPersonToolInput,
    ) -> dict[str, Any]:
        """Get an automation-person pairing."""
        return await self._single_result(
            lambda: self._services.automation_people.get_automation_person(
                tool_input.automation_person_id
            )
        )

    async def trigger_automation(
        self,
        tool_input: CreateAutomationPersonRequest,
    ) -> dict[str, Any]:
        """Trigger an automation for a person."""
        return await self._single_result(
            lambda: self._services.automation_people.create_automation_person(tool_input)
        )

    async def update_automation_person(
        self,
        tool_input: UpdateAutomationPersonToolInput,
    ) -> dict[str, Any]:
        """Update an automation-person pairing."""
        request = UpdateAutomationPersonRequest.model_validate(
            tool_input.model_dump(exclude={"automation_person_id"})
        )
        return await self._single_result(
            lambda: self._services.automation_people.update_automation_person(
                tool_input.automation_person_id,
                request,
            )
        )

    async def list_appointment_outcomes(
        self,
        tool_input: AppointmentOutcomeListRequest,
    ) -> dict[str, Any]:
        """List appointment outcomes."""
        return await self._page_result(
            lambda: self._services.appointment_outcomes.list_appointment_outcomes(tool_input),
            key="appointmentoutcomes",
        )

    async def get_appointment_outcome(
        self,
        tool_input: GetAppointmentOutcomeToolInput,
    ) -> dict[str, Any]:
        """Get an appointment outcome."""
        return await self._single_result(
            lambda: self._services.appointment_outcomes.get_appointment_outcome(
                tool_input.appointment_outcome_id
            )
        )

    async def create_appointment_outcome(
        self,
        tool_input: CreateAppointmentOutcomeRequest,
    ) -> dict[str, Any]:
        """Create an appointment outcome."""
        return await self._single_result(
            lambda: self._services.appointment_outcomes.create_appointment_outcome(tool_input)
        )

    async def update_appointment_outcome(
        self,
        tool_input: UpdateAppointmentOutcomeToolInput,
    ) -> dict[str, Any]:
        """Update an appointment outcome."""
        request = UpdateAppointmentOutcomeRequest.model_validate(
            tool_input.model_dump(exclude={"appointment_outcome_id"})
        )
        return await self._single_result(
            lambda: self._services.appointment_outcomes.update_appointment_outcome(
                tool_input.appointment_outcome_id,
                request,
            )
        )

    async def delete_appointment_outcome(
        self,
        tool_input: DeleteAppointmentOutcomeToolInput,
    ) -> dict[str, Any]:
        """Delete an appointment outcome."""
        request = DeleteAppointmentOutcomeRequest.model_validate(
            tool_input.model_dump(exclude={"appointment_outcome_id"})
        )
        return await self._delete_result(
            lambda: self._services.appointment_outcomes.delete_appointment_outcome(
                tool_input.appointment_outcome_id,
                request,
            ),
            identifier_key="appointmentOutcomeId",
            identifier_value=tool_input.appointment_outcome_id,
        )

    async def list_appointment_types(
        self,
        tool_input: AppointmentTypeListRequest,
    ) -> dict[str, Any]:
        """List appointment types."""
        return await self._page_result(
            lambda: self._services.appointment_types.list_appointment_types(tool_input),
            key="appointmenttypes",
        )

    async def get_appointment_type(
        self,
        tool_input: GetAppointmentTypeToolInput,
    ) -> dict[str, Any]:
        """Get an appointment type."""
        return await self._single_result(
            lambda: self._services.appointment_types.get_appointment_type(
                tool_input.appointment_type_id
            )
        )

    async def create_appointment_type(
        self,
        tool_input: CreateAppointmentTypeRequest,
    ) -> dict[str, Any]:
        """Create an appointment type."""
        return await self._single_result(
            lambda: self._services.appointment_types.create_appointment_type(tool_input)
        )

    async def update_appointment_type(
        self,
        tool_input: UpdateAppointmentTypeToolInput,
    ) -> dict[str, Any]:
        """Update an appointment type."""
        request = UpdateAppointmentTypeRequest.model_validate(
            tool_input.model_dump(exclude={"appointment_type_id"})
        )
        return await self._single_result(
            lambda: self._services.appointment_types.update_appointment_type(
                tool_input.appointment_type_id,
                request,
            )
        )

    async def delete_appointment_type(
        self,
        tool_input: DeleteAppointmentTypeToolInput,
    ) -> dict[str, Any]:
        """Delete an appointment type."""
        request = DeleteAppointmentTypeRequest.model_validate(
            tool_input.model_dump(exclude={"appointment_type_id"})
        )
        return await self._delete_result(
            lambda: self._services.appointment_types.delete_appointment_type(
                tool_input.appointment_type_id,
                request,
            ),
            identifier_key="appointmentTypeId",
            identifier_value=tool_input.appointment_type_id,
        )

    async def search_people(self, tool_input: PeopleSearchRequest) -> dict[str, Any]:
        """Search people."""
        return await self._page_result(
            lambda: self._search_people_with_default_scope(tool_input),
            key="people",
        )

    async def list_uncontacted_leads(
        self,
        tool_input: ListUncontactedLeadsToolInput,
    ) -> dict[str, Any]:
        """List leads with no recorded last communication.

        Args:
            tool_input: Owner scope, optional source/stage filters, and
                pagination settings for the no-communication helper.

        Returns:
            A paginated people payload filtered to records whose
            `lastCommunication` is empty.
        """
        return await self._page_result(
            lambda: self._list_uncontacted_leads(tool_input),
            key="people",
        )

    async def _list_uncontacted_leads(
        self,
        tool_input: ListUncontactedLeadsToolInput,
    ) -> PageResult[PersonRecord]:
        """Build and run the direct no-last-communication people search.

        Args:
            tool_input: Validated uncontacted-leads helper input.

        Returns:
            A filtered page of people whose `lastCommunication` is empty.
        """
        assigned_user_id = await tool_input.resolved_assigned_user_id(self._services)
        requested_fields = _uncommunicated_lead_fields(tool_input.fields)
        matches: list[PersonRecord] = []
        fetch_offset = 0
        fetch_limit = 100
        while True:
            request = PeopleSearchRequest(
                assigned_user_id=assigned_user_id,
                fields=requested_fields,
                limit=fetch_limit,
                offset=fetch_offset,
                sort="-created",
                source=tool_input.source,
                stage=tool_input.stage,
            )
            page = await self._services.people.search_people(request)
            matches.extend(
                person
                for person in page.items
                if _is_empty_last_communication(person.last_communication)
            )
            if not page.metadata.has_next() or page.metadata.count == 0:
                break
            fetch_offset = page.metadata.offset + page.metadata.count

        page_offset = _pagination_offset(tool_input)
        page_limit = tool_input.limit or 25
        page_items = matches[page_offset : page_offset + page_limit]
        next_offset = page_offset + len(page_items)
        return PageResult(
            items=page_items,
            metadata=PaginationMetadata(
                count=len(page_items),
                limit=page_limit,
                next_token=str(next_offset) if next_offset < len(matches) else None,
                next_link=None,
                offset=page_offset,
                total=len(matches),
            ),
        )

    async def search_people_in_smart_list(
        self,
        tool_input: SearchPeopleInSmartListToolInput,
    ) -> dict[str, Any]:
        """Search people inside an exact named smart list.

        Args:
            tool_input: Named smart-list people-search input.

        Returns:
            A structured payload containing the resolved smart-list provenance,
            pagination metadata, and scoped people records.
        """
        try:
            smart_list = _resolve_smart_list_by_name(
                await self._list_all_smart_lists(),
                tool_input.resolved_smart_list_name(),
            )
            assigned_user_id = await self._execute_with_services(
                lambda: tool_input.resolved_assigned_user_id(self._services)
            )
            page = await self._execute_with_services(
                lambda: self._services.people.search_people(
                    PeopleSearchRequest(
                        assigned_user_id=assigned_user_id,
                        fields=tool_input.fields,
                        limit=tool_input.limit,
                        next_token=tool_input.next_token,
                        offset=tool_input.offset,
                        source=tool_input.source,
                        stage=tool_input.stage,
                        smart_list_id=smart_list.id,
                    )
                )
            )
        except FollowUpBossError as exc:
            raise RuntimeError(_mcp_safe_error(exc)) from exc
        return {
            "_metadata": asdict(page.metadata),
            "smartlist": smart_list.model_dump(
                mode="json",
                by_alias=True,
                exclude_defaults=True,
                exclude_none=True,
            ),
            "people": [item.model_dump(mode="json", by_alias=True) for item in page.items],
        }

    async def _list_all_smart_lists(self) -> list[SmartListRecord]:
        """List every visible smart list for exact-name helper resolution.

        Returns:
            Smart-list records across all available pages.
        """
        smart_lists: list[SmartListRecord] = []
        offset = 0
        while True:

            async def list_page(page_offset: int = offset) -> PageResult[SmartListRecord]:
                """List one smart-list page at the current offset."""
                return await self._services.smart_lists.list_smart_lists(
                    SmartListListRequest(include_all=True, limit=100, offset=page_offset)
                )

            page = cast(PageResult[SmartListRecord], await self._execute_with_services(list_page))
            smart_lists.extend(page.items)
            if not page.metadata.has_next() or page.metadata.count == 0:
                return smart_lists
            offset = page.metadata.offset + page.metadata.count

    async def get_latest_lead(self, tool_input: GetLatestLeadToolInput) -> dict[str, Any]:
        """Return the newest lead assigned to the authenticated user.

        Args:
            tool_input: Optional field selection for the returned person.

        Returns:
            A structured payload containing pagination metadata and the single newest
            assigned person, or ``None`` when no assigned leads are available.
        """
        request = PeopleSearchRequest(fields=tool_input.fields, limit=1, sort="-created")
        try:
            page = await self._execute_with_services(
                lambda: self._search_people_with_default_scope(request)
            )
        except FollowUpBossError as exc:
            raise RuntimeError(_mcp_safe_error(exc)) from exc

        person = page.items[0] if page.items else None
        return {
            "_metadata": asdict(page.metadata),
            "person": (
                person.model_dump(
                    mode="json",
                    by_alias=True,
                    exclude_defaults=True,
                    exclude_none=True,
                )
                if person is not None
                else None
            ),
        }

    async def _search_people_with_default_scope(
        self,
        tool_input: PeopleSearchRequest,
    ) -> PageResult[PersonRecord]:
        """Search people with an owned-leads default scope.

        Args:
            tool_input: Validated people-search tool input.

        Returns:
            The paginated people search result.
        """
        if (
            tool_input.assigned_to is not None
            or tool_input.assigned_user_id is not None
            or tool_input.assigned_pond_id is not None
            or tool_input.include_ponds is True
            or tool_input.include_unclaimed is True
        ):
            return await self._services.people.search_people(tool_input)
        identity = await self._services.identity.get_identity()
        if identity.id is None:
            raise RuntimeError("Authenticated Follow Up Boss user id is unavailable.")
        scoped_input = tool_input.model_copy(update={"assigned_user_id": identity.id})
        return await self._services.people.search_people(scoped_input)

    async def get_person(self, tool_input: GetPersonToolInput) -> dict[str, Any]:
        """Get a person."""
        return await self._single_result(
            lambda: self._services.people.get_person(
                tool_input.person_id,
                request=PersonLookupRequest(fields=tool_input.fields),
            )
        )

    async def create_person(self, tool_input: CreatePersonRequest) -> dict[str, Any]:
        """Create a person."""
        return await self._single_result(lambda: self._services.people.create_person(tool_input))

    async def update_person(self, tool_input: UpdatePersonToolInput) -> dict[str, Any]:
        """Update a person."""
        request = UpdatePersonRequest.model_validate(tool_input.model_dump(exclude={"person_id"}))
        return await self._single_result(
            lambda: self._services.people.update_person(tool_input.person_id, request)
        )

    async def check_duplicate_person(
        self,
        tool_input: CheckDuplicatePersonToolInput,
    ) -> dict[str, Any]:
        """Check whether a person already exists."""
        return await self._single_result(
            lambda: self._services.people.check_duplicate_person(tool_input)
        )

    async def list_unclaimed_people(
        self,
        tool_input: UnclaimedPeopleListRequest,
    ) -> dict[str, Any]:
        """List unclaimed people."""
        return await self._page_result(
            lambda: self._services.people.list_unclaimed_people(tool_input),
            key="people",
        )

    async def claim_person(self, tool_input: ClaimPersonToolInput) -> dict[str, Any]:
        """Claim a person."""
        return await self._single_result(lambda: self._services.people.claim_person(tool_input))

    async def ignore_unclaimed_person(
        self,
        tool_input: IgnoreUnclaimedPersonToolInput,
    ) -> dict[str, Any]:
        """Ignore an unclaimed person offer."""
        return await self._delete_result(
            lambda: self._services.people.ignore_unclaimed_person(tool_input),
            identifier_key="personId",
            identifier_value=tool_input.person_id,
        )

    async def delete_person(self, tool_input: DeletePersonToolInput) -> dict[str, Any]:
        """Delete a person."""
        return await self._delete_result(
            lambda: self._services.people.delete_person(tool_input.person_id),
            identifier_key="personId",
            identifier_value=tool_input.person_id,
        )

    async def get_person_attachment(
        self,
        tool_input: GetPersonAttachmentToolInput,
    ) -> dict[str, Any]:
        """Get a person attachment."""
        return await self._single_result(
            lambda: self._services.person_attachments.get_person_attachment(
                tool_input.person_attachment_id
            )
        )

    async def create_person_attachment(
        self,
        tool_input: CreatePersonAttachmentRequest,
    ) -> dict[str, Any]:
        """Create a person attachment."""
        return await self._single_result(
            lambda: self._services.person_attachments.create_person_attachment(tool_input)
        )

    async def update_person_attachment(
        self,
        tool_input: UpdatePersonAttachmentToolInput,
    ) -> dict[str, Any]:
        """Update a person attachment."""
        request = UpdatePersonAttachmentRequest.model_validate(
            tool_input.model_dump(exclude={"person_attachment_id"})
        )
        return await self._single_result(
            lambda: self._services.person_attachments.update_person_attachment(
                tool_input.person_attachment_id,
                request,
            )
        )

    async def delete_person_attachment(
        self,
        tool_input: DeletePersonAttachmentToolInput,
    ) -> dict[str, Any]:
        """Delete a person attachment."""
        return await self._delete_result(
            lambda: self._services.person_attachments.delete_person_attachment(
                tool_input.person_attachment_id
            ),
            identifier_key="personAttachmentId",
            identifier_value=tool_input.person_attachment_id,
        )

    async def get_reaction(self, tool_input: GetReactionToolInput) -> dict[str, Any]:
        """Get a reaction."""
        return await self._single_result(
            lambda: self._services.reactions.get_reaction(tool_input.reaction_id)
        )

    async def get_threaded_reply(
        self,
        tool_input: GetThreadedReplyToolInput,
    ) -> dict[str, Any]:
        """Get a threaded reply."""
        return await self._single_result(
            lambda: self._services.threaded_replies.get_threaded_reply(tool_input.threaded_reply_id)
        )

    async def add_reaction(self, tool_input: AddReactionToolInput) -> dict[str, Any]:
        """Add a reaction."""
        request = CreateReactionRequest.model_validate(
            tool_input.model_dump(exclude={"ref_type", "ref_id"})
        )
        return await self._single_result(
            lambda: self._services.reactions.add_reaction(
                tool_input.ref_type,
                tool_input.ref_id,
                request,
            )
        )

    async def delete_reaction(self, tool_input: DeleteReactionToolInput) -> dict[str, Any]:
        """Delete a reaction."""
        request = DeleteReactionRequest.model_validate(
            tool_input.model_dump(exclude={"ref_type", "ref_id"})
        )
        return await self._delete_result(
            lambda: self._services.reactions.delete_reaction(
                tool_input.ref_type,
                tool_input.ref_id,
                request,
            ),
            identifier_key="refId",
            identifier_value=tool_input.ref_id,
        )

    async def list_people_relationships(
        self,
        tool_input: PeopleRelationshipListRequest,
    ) -> dict[str, Any]:
        """List people relationships."""
        return await self._page_result(
            lambda: self._services.people_relationships.list_people_relationships(tool_input),
            key="peopleRelationships",
        )

    async def get_people_relationship(
        self,
        tool_input: GetPeopleRelationshipToolInput,
    ) -> dict[str, Any]:
        """Get a people relationship."""
        return await self._single_result(
            lambda: self._services.people_relationships.get_people_relationship(
                tool_input.people_relationship_id
            )
        )

    async def create_people_relationship(
        self,
        tool_input: CreatePeopleRelationshipRequest,
    ) -> dict[str, Any]:
        """Create a people relationship."""
        return await self._single_result(
            lambda: self._services.people_relationships.create_people_relationship(tool_input)
        )

    async def update_people_relationship(
        self,
        tool_input: UpdatePeopleRelationshipToolInput,
    ) -> dict[str, Any]:
        """Update a people relationship."""
        request = UpdatePeopleRelationshipRequest.model_validate(
            tool_input.model_dump(exclude={"people_relationship_id"})
        )
        return await self._single_result(
            lambda: self._services.people_relationships.update_people_relationship(
                tool_input.people_relationship_id,
                request,
            )
        )

    async def delete_people_relationship(
        self,
        tool_input: DeletePeopleRelationshipToolInput,
    ) -> dict[str, Any]:
        """Delete a people relationship."""
        return await self._delete_result(
            lambda: self._services.people_relationships.delete_people_relationship(
                tool_input.people_relationship_id
            ),
            identifier_key="peopleRelationshipId",
            identifier_value=tool_input.people_relationship_id,
        )

    async def search_events(self, tool_input: EventSearchRequest) -> dict[str, Any]:
        """Search events."""
        return await self._page_result(
            lambda: self._services.events.search_events(tool_input),
            key="events",
        )

    async def get_event(self, tool_input: GetEventToolInput) -> dict[str, Any]:
        """Get an event."""
        return await self._single_result(
            lambda: self._services.events.get_event(tool_input.event_id)
        )

    async def send_event(self, tool_input: CreateEventRequest) -> dict[str, Any]:
        """Send an event."""
        return await self._single_result(lambda: self._services.events.send_event(tool_input))

    async def list_groups(self, tool_input: GroupListRequest) -> dict[str, Any]:
        """List groups."""
        return await self._page_result(
            lambda: self._services.groups.list_groups(tool_input),
            key="groups",
        )

    async def list_round_robin_groups(self, tool_input: GroupListRequest) -> dict[str, Any]:
        """List groups with round-robin details."""
        return await self._page_result(
            lambda: self._services.groups.list_round_robin_groups(tool_input),
            key="groups",
        )

    async def get_group(self, tool_input: GetGroupToolInput) -> dict[str, Any]:
        """Get a group."""
        return await self._single_result(
            lambda: self._services.groups.get_group(tool_input.group_id)
        )

    async def create_group(self, tool_input: CreateGroupRequest) -> dict[str, Any]:
        """Create a group."""
        return await self._single_result(lambda: self._services.groups.create_group(tool_input))

    async def update_group(self, tool_input: UpdateGroupToolInput) -> dict[str, Any]:
        """Update a group."""
        request = UpdateGroupRequest.model_validate(tool_input.model_dump(exclude={"group_id"}))
        return await self._single_result(
            lambda: self._services.groups.update_group(tool_input.group_id, request)
        )

    async def delete_group(self, tool_input: DeleteGroupToolInput) -> dict[str, Any]:
        """Delete a group."""
        return await self._delete_result(
            lambda: self._services.groups.delete_group(tool_input.group_id),
            identifier_key="groupId",
            identifier_value=tool_input.group_id,
        )

    async def list_inbox_app_installations(
        self,
        tool_input: ListInboxAppInstallationsToolInput,
    ) -> dict[str, Any]:
        """List inbox app installations."""
        return await self._page_result(
            lambda: self._services.inbox_apps.list_inbox_app_installations(
                tool_input.published_inbox_app_id
            ),
            key="inboxApps",
        )

    async def install_inbox_app(self, tool_input: InstallInboxAppRequest) -> dict[str, Any]:
        """Install an inbox app."""
        return await self._single_result(
            lambda: self._services.inbox_apps.install_inbox_app(tool_input)
        )

    async def deactivate_inbox_app(self, tool_input: DeactivateInboxAppToolInput) -> dict[str, Any]:
        """Deactivate an inbox app."""
        return await self._delete_result(
            lambda: self._services.inbox_apps.deactivate_inbox_app(tool_input.inbox_app_id),
            identifier_key="inboxAppId",
            identifier_value=tool_input.inbox_app_id,
        )

    async def add_inbox_app_message(
        self,
        tool_input: AddInboxAppMessageToolInput,
    ) -> dict[str, Any]:
        """Add an inbox app message."""
        request = CreateInboxAppMessageRequest.model_validate(
            tool_input.model_dump(exclude={"inbox_app_id"})
        )
        return await self._single_result(
            lambda: self._services.inbox_apps.add_inbox_app_message(
                tool_input.inbox_app_id,
                request,
            )
        )

    async def add_inbox_app_note(
        self,
        tool_input: AddInboxAppNoteToolInput,
    ) -> dict[str, Any]:
        """Add an inbox app note."""
        request = CreateInboxAppNoteRequest.model_validate(
            tool_input.model_dump(exclude={"inbox_app_id"})
        )
        return await self._single_result(
            lambda: self._services.inbox_apps.add_inbox_app_note(
                tool_input.inbox_app_id,
                request,
            )
        )

    async def list_inbox_app_participants(
        self,
        tool_input: ListInboxAppParticipantsToolInput,
    ) -> dict[str, Any]:
        """List inbox app participants."""
        return await self._page_result(
            lambda: self._services.inbox_apps.list_inbox_app_participants(
                tool_input.inbox_app_id,
                tool_input.ext_conversation_id,
            ),
            key="participants",
        )

    async def add_inbox_app_participant(
        self,
        tool_input: AddInboxAppParticipantToolInput,
    ) -> dict[str, Any]:
        """Add an inbox app participant."""
        request = CreateInboxAppParticipantRequest.model_validate(
            tool_input.model_dump(exclude={"inbox_app_id", "ext_conversation_id"})
        )
        return await self._single_result(
            lambda: self._services.inbox_apps.add_inbox_app_participant(
                tool_input.inbox_app_id,
                tool_input.ext_conversation_id,
                request,
            )
        )

    async def update_inbox_app_conversation(
        self,
        tool_input: UpdateInboxAppConversationToolInput,
    ) -> dict[str, Any]:
        """Update an inbox app conversation."""
        request = UpdateInboxAppConversationRequest.model_validate(
            tool_input.model_dump(exclude={"inbox_app_id", "ext_conversation_id"})
        )
        return await self._single_result(
            lambda: self._services.inbox_apps.update_inbox_app_conversation(
                tool_input.inbox_app_id,
                tool_input.ext_conversation_id,
                request,
            )
        )

    async def update_inbox_app_message(
        self,
        tool_input: UpdateInboxAppMessageToolInput,
    ) -> dict[str, Any]:
        """Update an inbox app message."""
        request = UpdateInboxAppMessageRequest.model_validate(
            tool_input.model_dump(exclude={"inbox_app_id"})
        )
        return await self._single_result(
            lambda: self._services.inbox_apps.update_inbox_app_message(
                tool_input.inbox_app_id,
                request,
            )
        )

    async def remove_inbox_app_participant(
        self,
        tool_input: DeleteInboxAppParticipantToolInput,
    ) -> dict[str, Any]:
        """Remove an inbox app participant."""
        return await self._delete_result(
            lambda: self._services.inbox_apps.remove_inbox_app_participant(
                tool_input.inbox_app_id,
                tool_input.ext_conversation_id,
                tool_input.participant_id,
            ),
            identifier_key="participantId",
            identifier_value=tool_input.participant_id,
        )

    async def list_team_inboxes(self, tool_input: TeamInboxListRequest) -> dict[str, Any]:
        """List team inboxes."""
        return await self._page_result(
            lambda: self._services.team_inboxes.list_team_inboxes(tool_input),
            key="teamInboxes",
        )

    async def list_timeframes(self, tool_input: TimeframeListRequest) -> dict[str, Any]:
        """List timeframes."""
        return await self._page_result(
            lambda: self._services.timeframes.list_timeframes(tool_input),
            key="timeframes",
        )

    async def list_users(self, tool_input: UserListRequest) -> dict[str, Any]:
        """List users."""
        return await self._page_result(
            lambda: self._services.users.list_users(tool_input),
            key="users",
        )

    async def get_me(self) -> dict[str, Any]:
        """Get the currently authenticated user with sensitive fields redacted."""
        try:
            result = await self._execute_with_services(lambda: self._services.users.get_me())
        except FollowUpBossError as exc:
            raise RuntimeError(_mcp_safe_error(exc)) from exc
        safe_result = result.redacted_for_mcp()
        return cast(
            dict[str, Any],
            safe_result.model_dump(
                mode="json",
                by_alias=True,
                exclude_defaults=True,
                exclude_none=True,
            ),
        )

    async def get_user(self, tool_input: GetUserToolInput) -> dict[str, Any]:
        """Get a user."""
        return await self._single_result(lambda: self._services.users.get_user(tool_input.user_id))

    async def delete_user(self, tool_input: DeleteUserToolInput) -> dict[str, Any]:
        """Delete a user."""
        request = DeleteUserRequest.model_validate(tool_input.model_dump(exclude={"user_id"}))
        return await self._delete_result(
            lambda: self._services.users.delete_user(tool_input.user_id, request),
            identifier_key="userId",
            identifier_value=tool_input.user_id,
        )

    async def list_custom_fields(self, tool_input: CustomFieldListRequest) -> dict[str, Any]:
        """List custom fields."""
        return await self._page_result(
            lambda: self._services.custom_fields.list_custom_fields(tool_input),
            key="customfields",
        )

    async def get_custom_field(self, tool_input: GetCustomFieldToolInput) -> dict[str, Any]:
        """Get a custom field."""
        return await self._single_result(
            lambda: self._services.custom_fields.get_custom_field(tool_input.custom_field_id)
        )

    async def create_custom_field(self, tool_input: CreateCustomFieldRequest) -> dict[str, Any]:
        """Create a custom field."""
        return await self._single_result(
            lambda: self._services.custom_fields.create_custom_field(tool_input)
        )

    async def update_custom_field(self, tool_input: UpdateCustomFieldToolInput) -> dict[str, Any]:
        """Update a custom field."""
        request = UpdateCustomFieldRequest.model_validate(
            tool_input.model_dump(exclude={"custom_field_id"})
        )
        return await self._single_result(
            lambda: self._services.custom_fields.update_custom_field(
                tool_input.custom_field_id,
                request,
            )
        )

    async def delete_custom_field(self, tool_input: DeleteCustomFieldToolInput) -> dict[str, Any]:
        """Delete a custom field."""
        return await self._delete_result(
            lambda: self._services.custom_fields.delete_custom_field(tool_input.custom_field_id),
            identifier_key="customFieldId",
            identifier_value=tool_input.custom_field_id,
        )

    async def list_email_campaigns(self, tool_input: EmailCampaignListRequest) -> dict[str, Any]:
        """List email marketing campaigns."""
        return await self._page_result(
            lambda: self._services.email_marketing.list_email_campaigns(tool_input),
            key="emCampaigns",
        )

    async def create_email_campaign(self, tool_input: CreateEmailCampaignRequest) -> dict[str, Any]:
        """Create an email marketing campaign."""
        return await self._single_result(
            lambda: self._services.email_marketing.create_email_campaign(tool_input)
        )

    async def update_email_campaign(
        self,
        tool_input: UpdateEmailCampaignToolInput,
    ) -> dict[str, Any]:
        """Update an email marketing campaign."""
        request = UpdateEmailCampaignRequest.model_validate(
            tool_input.model_dump(exclude={"email_campaign_id"})
        )
        return await self._single_result(
            lambda: self._services.email_marketing.update_email_campaign(
                tool_input.email_campaign_id,
                request,
            )
        )

    async def list_email_events(self, tool_input: EmailEventListRequest) -> dict[str, Any]:
        """List email marketing events."""
        return await self._page_result(
            lambda: self._services.email_marketing.list_email_events(tool_input),
            key="emEvents",
        )

    async def send_email_events(self, tool_input: CreateEmailEventsBatchRequest) -> dict[str, Any]:
        """Send email marketing events."""
        return await self._single_result(
            lambda: self._services.email_marketing.send_email_events(tool_input)
        )

    async def list_deals(self, tool_input: DealListRequest) -> dict[str, Any]:
        """List deals."""
        return await self._page_result(
            lambda: self._services.deals.list_deals(tool_input),
            key="deals",
        )

    async def list_active_deals_for_person(
        self,
        tool_input: ListActiveDealsForPersonToolInput,
    ) -> dict[str, Any]:
        """Return active non-archived deals tied to a person.

        Args:
            tool_input: The person identifier to use when filtering deals.

        Returns:
            A paginated payload containing active deals associated with the person.
        """
        request = DealListRequest(
            include_archived=False,
            include_deleted=False,
            person_id=tool_input.person_id,
            status="Active",
        )
        return await self._page_result(
            lambda: self._services.deals.list_deals(request),
            key="deals",
        )

    async def list_person_activity(
        self,
        tool_input: ListPersonActivityToolInput,
    ) -> dict[str, Any]:
        """List communication and activity records for one explicit person.

        Args:
            tool_input: Person-scoped activity query controls.

        Returns:
            A structured payload containing person provenance, per-surface
            pagination metadata, and only activity records queried with the
            requested `person_id`.
        """
        try:
            person = await self._execute_with_services(
                lambda: self._services.people.get_person(tool_input.person_id)
            )
            metadata: dict[str, dict[str, Any]] = {}
            result: dict[str, Any] = {
                "person": person.model_dump(
                    mode="json",
                    by_alias=True,
                    exclude_defaults=True,
                    exclude_none=True,
                )
            }

            if tool_input.include_calls:
                calls = await self._execute_with_services(
                    lambda: self._services.calls.list_calls(
                        CallListRequest(
                            limit=tool_input.limit,
                            offset=tool_input.offset,
                            person_id=tool_input.person_id,
                        )
                    )
                )
                metadata["calls"] = asdict(calls.metadata)
                result["calls"] = [
                    item.model_dump(mode="json", by_alias=True) for item in calls.items
                ]

            if tool_input.include_text_messages:
                text_messages = await self._execute_with_services(
                    lambda: self._services.text_messages.list_text_messages(
                        TextMessageListRequest(person_id=tool_input.person_id)
                    )
                )
                metadata["textmessages"] = asdict(text_messages.metadata)
                result["textmessages"] = [
                    item.model_dump(mode="json", by_alias=True) for item in text_messages.items
                ]

            if tool_input.include_email_events:
                email_events = await self._execute_with_services(
                    lambda: self._services.email_marketing.list_email_events(
                        EmailEventListRequest(
                            limit=tool_input.limit,
                            offset=tool_input.offset,
                            person_id=tool_input.person_id,
                        )
                    )
                )
                metadata["emEvents"] = asdict(email_events.metadata)
                result["emEvents"] = [
                    item.model_dump(mode="json", by_alias=True) for item in email_events.items
                ]

            if tool_input.include_events:
                events = await self._execute_with_services(
                    lambda: self._services.events.search_events(
                        EventSearchRequest(
                            limit=tool_input.limit,
                            offset=tool_input.offset,
                            person_id=tool_input.person_id,
                        )
                    )
                )
                metadata["events"] = asdict(events.metadata)
                result["events"] = [
                    item.model_dump(mode="json", by_alias=True) for item in events.items
                ]

            if tool_input.include_appointments:
                appointments = await self._execute_with_services(
                    lambda: self._services.appointments.list_appointments(
                        AppointmentListRequest(
                            limit=tool_input.limit,
                            offset=tool_input.offset,
                            person_id=tool_input.person_id,
                        )
                    )
                )
                metadata["appointments"] = asdict(appointments.metadata)
                result["appointments"] = [
                    item.model_dump(mode="json", by_alias=True) for item in appointments.items
                ]
        except FollowUpBossError as exc:
            raise RuntimeError(_mcp_safe_error(exc)) from exc

        result["_metadata"] = metadata
        return result

    async def get_deal(self, tool_input: GetDealToolInput) -> dict[str, Any]:
        """Get a deal."""
        return await self._single_result(lambda: self._services.deals.get_deal(tool_input.deal_id))

    async def create_deal(self, tool_input: CreateDealRequest) -> dict[str, Any]:
        """Create a deal."""
        return await self._single_result(lambda: self._services.deals.create_deal(tool_input))

    async def update_deal(self, tool_input: UpdateDealToolInput) -> dict[str, Any]:
        """Update a deal."""
        request = UpdateDealRequest.model_validate(tool_input.model_dump(exclude={"deal_id"}))
        return await self._single_result(
            lambda: self._services.deals.update_deal(tool_input.deal_id, request)
        )

    async def delete_deal(self, tool_input: DeleteDealToolInput) -> dict[str, Any]:
        """Delete a deal."""
        return await self._delete_result(
            lambda: self._services.deals.delete_deal(tool_input.deal_id),
            identifier_key="dealId",
            identifier_value=tool_input.deal_id,
        )

    async def get_deal_attachment(self, tool_input: GetDealAttachmentToolInput) -> dict[str, Any]:
        """Get a deal attachment."""
        return await self._single_result(
            lambda: self._services.deal_attachments.get_deal_attachment(
                tool_input.deal_attachment_id
            )
        )

    async def create_deal_attachment(
        self,
        tool_input: CreateDealAttachmentRequest,
    ) -> dict[str, Any]:
        """Create a deal attachment."""
        return await self._single_result(
            lambda: self._services.deal_attachments.create_deal_attachment(tool_input)
        )

    async def update_deal_attachment(
        self,
        tool_input: UpdateDealAttachmentToolInput,
    ) -> dict[str, Any]:
        """Update a deal attachment."""
        request = UpdateDealAttachmentRequest.model_validate(
            tool_input.model_dump(exclude={"deal_attachment_id"})
        )
        return await self._single_result(
            lambda: self._services.deal_attachments.update_deal_attachment(
                tool_input.deal_attachment_id,
                request,
            )
        )

    async def delete_deal_attachment(
        self,
        tool_input: DeleteDealAttachmentToolInput,
    ) -> dict[str, Any]:
        """Delete a deal attachment."""
        return await self._delete_result(
            lambda: self._services.deal_attachments.delete_deal_attachment(
                tool_input.deal_attachment_id
            ),
            identifier_key="dealAttachmentId",
            identifier_value=tool_input.deal_attachment_id,
        )

    async def list_deal_custom_fields(
        self, tool_input: DealCustomFieldListRequest
    ) -> dict[str, Any]:
        """List deal custom fields."""
        return await self._page_result(
            lambda: self._services.deals.list_deal_custom_fields(tool_input),
            key="dealCustomfields",
        )

    async def get_deal_custom_field(
        self,
        tool_input: GetDealCustomFieldToolInput,
    ) -> dict[str, Any]:
        """Get a deal custom field."""
        return await self._single_result(
            lambda: self._services.deals.get_deal_custom_field(tool_input.deal_custom_field_id)
        )

    async def create_deal_custom_field(
        self,
        tool_input: CreateDealCustomFieldRequest,
    ) -> dict[str, Any]:
        """Create a deal custom field."""
        return await self._single_result(
            lambda: self._services.deals.create_deal_custom_field(tool_input)
        )

    async def update_deal_custom_field(
        self,
        tool_input: UpdateDealCustomFieldToolInput,
    ) -> dict[str, Any]:
        """Update a deal custom field."""
        request = UpdateDealCustomFieldRequest.model_validate(
            tool_input.model_dump(exclude={"deal_custom_field_id"})
        )
        return await self._single_result(
            lambda: self._services.deals.update_deal_custom_field(
                tool_input.deal_custom_field_id,
                request,
            )
        )

    async def delete_deal_custom_field(
        self,
        tool_input: DeleteDealCustomFieldToolInput,
    ) -> dict[str, Any]:
        """Delete a deal custom field."""
        return await self._delete_result(
            lambda: self._services.deals.delete_deal_custom_field(tool_input.deal_custom_field_id),
            identifier_key="dealCustomFieldId",
            identifier_value=tool_input.deal_custom_field_id,
        )

    async def list_pipelines(self, tool_input: PipelineListRequest) -> dict[str, Any]:
        """List pipelines."""
        return await self._page_result(
            lambda: self._services.pipelines.list_pipelines(tool_input),
            key="pipelines",
        )

    async def get_pipeline(self, tool_input: GetPipelineToolInput) -> dict[str, Any]:
        """Get a pipeline."""
        return await self._single_result(
            lambda: self._services.pipelines.get_pipeline(tool_input.pipeline_id)
        )

    async def create_pipeline(self, tool_input: CreatePipelineRequest) -> dict[str, Any]:
        """Create a pipeline."""
        return await self._single_result(
            lambda: self._services.pipelines.create_pipeline(tool_input)
        )

    async def update_pipeline(self, tool_input: UpdatePipelineToolInput) -> dict[str, Any]:
        """Update a pipeline."""
        request = UpdatePipelineRequest.model_validate(
            tool_input.model_dump(exclude={"pipeline_id"})
        )
        return await self._single_result(
            lambda: self._services.pipelines.update_pipeline(tool_input.pipeline_id, request)
        )

    async def delete_pipeline(self, tool_input: DeletePipelineToolInput) -> dict[str, Any]:
        """Delete a pipeline."""
        return await self._delete_result(
            lambda: self._services.pipelines.delete_pipeline(tool_input.pipeline_id),
            identifier_key="pipelineId",
            identifier_value=tool_input.pipeline_id,
        )

    async def list_ponds(self, tool_input: PondListRequest) -> dict[str, Any]:
        """List ponds."""
        return await self._page_result(
            lambda: self._services.ponds.list_ponds(tool_input),
            key="ponds",
        )

    async def get_pond(self, tool_input: GetPondToolInput) -> dict[str, Any]:
        """Get a pond."""
        return await self._single_result(lambda: self._services.ponds.get_pond(tool_input.pond_id))

    async def create_pond(self, tool_input: CreatePondRequest) -> dict[str, Any]:
        """Create a pond."""
        return await self._single_result(lambda: self._services.ponds.create_pond(tool_input))

    async def update_pond(self, tool_input: UpdatePondToolInput) -> dict[str, Any]:
        """Update a pond."""
        request = UpdatePondRequest.model_validate(tool_input.model_dump(exclude={"pond_id"}))
        return await self._single_result(
            lambda: self._services.ponds.update_pond(tool_input.pond_id, request)
        )

    async def delete_pond(self, tool_input: DeletePondToolInput) -> dict[str, Any]:
        """Delete a pond."""
        request = DeletePondRequest.model_validate(tool_input.model_dump(exclude={"pond_id"}))
        return await self._delete_result(
            lambda: self._services.ponds.delete_pond(tool_input.pond_id, request),
            identifier_key="pondId",
            identifier_value=tool_input.pond_id,
        )

    async def list_smart_lists(self, tool_input: SmartListListRequest) -> dict[str, Any]:
        """List smart lists."""
        return await self._page_result(
            lambda: self._services.smart_lists.list_smart_lists(tool_input),
            key="smartlists",
        )

    async def get_smart_list(self, tool_input: GetSmartListToolInput) -> dict[str, Any]:
        """Get a smart list."""
        return await self._single_result(
            lambda: self._services.smart_lists.get_smart_list(tool_input.smart_list_id)
        )

    async def list_stages(self, tool_input: StageListRequest) -> dict[str, Any]:
        """List stages."""
        return await self._page_result(
            lambda: self._services.stages.list_stages(tool_input),
            key="stages",
        )

    async def get_stage(self, tool_input: GetStageToolInput) -> dict[str, Any]:
        """Get a stage."""
        return await self._single_result(
            lambda: self._services.stages.get_stage(tool_input.stage_id)
        )

    async def create_stage(self, tool_input: CreateStageRequest) -> dict[str, Any]:
        """Create a stage."""
        return await self._single_result(lambda: self._services.stages.create_stage(tool_input))

    async def update_stage(self, tool_input: UpdateStageToolInput) -> dict[str, Any]:
        """Update a stage."""
        request = UpdateStageRequest.model_validate(tool_input.model_dump(exclude={"stage_id"}))
        return await self._single_result(
            lambda: self._services.stages.update_stage(tool_input.stage_id, request)
        )

    async def delete_stage(self, tool_input: DeleteStageToolInput) -> dict[str, Any]:
        """Delete a stage."""
        request = DeleteStageRequest.model_validate(tool_input.model_dump(exclude={"stage_id"}))
        return await self._delete_result(
            lambda: self._services.stages.delete_stage(tool_input.stage_id, request),
            identifier_key="stageId",
            identifier_value=tool_input.stage_id,
        )

    async def list_teams(self, tool_input: TeamListRequest) -> dict[str, Any]:
        """List teams."""
        return await self._page_result(
            lambda: self._services.teams.list_teams(tool_input),
            key="teams",
        )

    async def get_team(self, tool_input: GetTeamToolInput) -> dict[str, Any]:
        """Get a team."""
        return await self._single_result(lambda: self._services.teams.get_team(tool_input.team_id))

    async def create_team(self, tool_input: CreateTeamRequest) -> dict[str, Any]:
        """Create a team."""
        return await self._single_result(lambda: self._services.teams.create_team(tool_input))

    async def update_team(self, tool_input: UpdateTeamToolInput) -> dict[str, Any]:
        """Update a team."""
        request = UpdateTeamRequest.model_validate(tool_input.model_dump(exclude={"team_id"}))
        return await self._single_result(
            lambda: self._services.teams.update_team(tool_input.team_id, request)
        )

    async def delete_team(self, tool_input: DeleteTeamToolInput) -> dict[str, Any]:
        """Delete a team."""
        request = DeleteTeamRequest.model_validate(tool_input.model_dump(exclude={"team_id"}))
        return await self._delete_result(
            lambda: self._services.teams.delete_team(tool_input.team_id, request),
            identifier_key="teamId",
            identifier_value=tool_input.team_id,
        )

    async def list_appointments(self, tool_input: AppointmentListRequest) -> dict[str, Any]:
        """List appointments."""
        return await self._page_result(
            lambda: self._services.appointments.list_appointments(tool_input),
            key="appointments",
        )

    async def get_appointment(self, tool_input: GetAppointmentToolInput) -> dict[str, Any]:
        """Get an appointment."""
        return await self._single_result(
            lambda: self._services.appointments.get_appointment(tool_input.appointment_id)
        )

    async def create_appointment(self, tool_input: CreateAppointmentRequest) -> dict[str, Any]:
        """Create an appointment."""
        return await self._single_result(
            lambda: self._services.appointments.create_appointment(tool_input)
        )

    async def update_appointment(
        self,
        tool_input: UpdateAppointmentToolInput,
    ) -> dict[str, Any]:
        """Update an appointment."""
        request = UpdateAppointmentRequest.model_validate(
            tool_input.model_dump(exclude={"appointment_id"})
        )
        return await self._single_result(
            lambda: self._services.appointments.update_appointment(
                tool_input.appointment_id,
                request,
            )
        )

    async def delete_appointment(self, tool_input: DeleteAppointmentToolInput) -> dict[str, Any]:
        """Delete an appointment."""
        return await self._delete_result(
            lambda: self._services.appointments.delete_appointment(tool_input.appointment_id),
            identifier_key="appointmentId",
            identifier_value=tool_input.appointment_id,
        )

    async def list_calls(self, tool_input: CallListRequest) -> dict[str, Any]:
        """List calls."""
        return await self._page_result(
            lambda: self._services.calls.list_calls(tool_input),
            key="calls",
        )

    async def get_call(self, tool_input: GetCallToolInput) -> dict[str, Any]:
        """Get a call."""
        return await self._single_result(lambda: self._services.calls.get_call(tool_input.call_id))

    async def create_call(self, tool_input: CreateCallRequest) -> dict[str, Any]:
        """Create a call."""
        return await self._single_result(lambda: self._services.calls.create_call(tool_input))

    async def update_call(self, tool_input: UpdateCallToolInput) -> dict[str, Any]:
        """Update a call."""
        request = UpdateCallRequest.model_validate(tool_input.model_dump(exclude={"call_id"}))
        return await self._single_result(
            lambda: self._services.calls.update_call(tool_input.call_id, request)
        )

    async def list_tasks(self, tool_input: TaskListRequest) -> dict[str, Any]:
        """List tasks."""
        return await self._page_result(
            lambda: self._services.tasks.list_tasks(tool_input),
            key="tasks",
        )

    async def list_my_overdue_tasks(
        self,
        tool_input: ListMyTaskIntentToolInput,
    ) -> dict[str, Any]:
        """Return incomplete overdue tasks assigned to the authenticated user.

        Args:
            tool_input: Optional pagination and field-selection settings.

        Returns:
            A paginated payload containing overdue incomplete tasks assigned to the
            authenticated Follow Up Boss user.
        """
        return await self._page_result(
            lambda: self._list_my_tasks_by_due(tool_input, due="overdue"),
            key="tasks",
        )

    async def list_my_tasks_due_today(
        self,
        tool_input: ListMyTaskIntentToolInput,
    ) -> dict[str, Any]:
        """Return incomplete tasks due today and assigned to the authenticated user.

        Args:
            tool_input: Optional pagination and field-selection settings.

        Returns:
            A paginated payload containing today's incomplete tasks assigned to the
            authenticated Follow Up Boss user.
        """
        return await self._page_result(
            lambda: self._list_my_tasks_by_due(tool_input, due="today"),
            key="tasks",
        )

    async def list_my_upcoming_tasks(
        self,
        tool_input: ListMyTaskIntentToolInput,
    ) -> dict[str, Any]:
        """Return incomplete future tasks assigned to the authenticated user.

        Args:
            tool_input: Optional pagination and field-selection settings.

        Returns:
            A paginated payload containing incomplete tasks assigned to the
            authenticated Follow Up Boss user and due after today.
        """
        return await self._page_result(
            lambda: self._list_my_upcoming_tasks(tool_input),
            key="tasks",
        )

    async def _list_my_tasks_by_due(
        self,
        tool_input: ListMyTaskIntentToolInput,
        *,
        due: str,
    ) -> PageResult[TaskRecord]:
        """List authenticated-user tasks for a canonical due bucket.

        Args:
            tool_input: Optional pagination and field-selection settings.
            due: Follow Up Boss task due bucket to request.

        Returns:
            The paginated task result returned by Follow Up Boss.

        Raises:
            RuntimeError: If the authenticated user's Follow Up Boss ID is unavailable.
        """
        identity = await self._services.identity.get_identity()
        if identity.id is None:
            raise RuntimeError("Authenticated Follow Up Boss user id is unavailable.")
        request = TaskListRequest(
            assigned_user_id=identity.id,
            due=due,
            fields=tool_input.fields,
            is_completed=False,
            limit=tool_input.limit,
            next_token=tool_input.next_token,
            offset=tool_input.offset,
        )
        return await self._services.tasks.list_tasks(request)

    async def _list_my_upcoming_tasks(
        self,
        tool_input: ListMyTaskIntentToolInput,
    ) -> PageResult[TaskRecord]:
        """List authenticated-user incomplete tasks due after today.

        Args:
            tool_input: Optional pagination and field-selection settings.

        Returns:
            The paginated task result returned by Follow Up Boss.

        Raises:
            RuntimeError: If the authenticated user's Follow Up Boss ID is unavailable.
        """
        identity = await self._services.identity.get_identity()
        if identity.id is None:
            raise RuntimeError("Authenticated Follow Up Boss user id is unavailable.")
        request = TaskListRequest(
            assigned_user_id=identity.id,
            due_start=_upcoming_task_due_start(),
            fields=tool_input.fields,
            is_completed=False,
            limit=tool_input.limit,
            next_token=tool_input.next_token,
            offset=tool_input.offset,
        )
        return await self._services.tasks.list_tasks(request)

    async def get_task(self, tool_input: GetTaskToolInput) -> dict[str, Any]:
        """Get a task."""
        return await self._single_result(lambda: self._services.tasks.get_task(tool_input.task_id))

    async def create_task(self, tool_input: CreateTaskRequest) -> dict[str, Any]:
        """Create a task."""
        return await self._single_result(lambda: self._services.tasks.create_task(tool_input))

    async def update_task(self, tool_input: UpdateTaskToolInput) -> dict[str, Any]:
        """Update a task."""
        request = UpdateTaskRequest.model_validate(tool_input.model_dump(exclude={"task_id"}))
        return await self._single_result(
            lambda: self._services.tasks.update_task(tool_input.task_id, request)
        )

    async def delete_task(self, tool_input: DeleteTaskToolInput) -> dict[str, Any]:
        """Delete a task."""
        return await self._delete_result(
            lambda: self._services.tasks.delete_task(tool_input.task_id),
            identifier_key="taskId",
            identifier_value=tool_input.task_id,
        )

    async def list_templates(self, tool_input: TemplateListRequest) -> dict[str, Any]:
        """List templates."""
        return await self._page_result(
            lambda: self._services.templates.list_templates(tool_input),
            key="templates",
        )

    async def get_template(self, tool_input: GetTemplateToolInput) -> dict[str, Any]:
        """Get a template."""
        return await self._single_result(
            lambda: self._services.templates.get_template(
                tool_input.template_id,
                request=TemplateLookupRequest(merge_person_id=tool_input.merge_person_id),
            )
        )

    async def merge_template(self, tool_input: MergeTemplateRequest) -> dict[str, Any]:
        """Merge a template."""
        return await self._single_result(
            lambda: self._services.templates.merge_template(tool_input)
        )

    async def create_template(self, tool_input: CreateTemplateRequest) -> dict[str, Any]:
        """Create a template."""
        return await self._single_result(
            lambda: self._services.templates.create_template(tool_input)
        )

    async def update_template(self, tool_input: UpdateTemplateToolInput) -> dict[str, Any]:
        """Update a template."""
        request = UpdateTemplateRequest.model_validate(
            tool_input.model_dump(exclude={"template_id"})
        )
        return await self._single_result(
            lambda: self._services.templates.update_template(tool_input.template_id, request)
        )

    async def delete_template(self, tool_input: DeleteTemplateToolInput) -> dict[str, Any]:
        """Delete a template."""
        return await self._delete_result(
            lambda: self._services.templates.delete_template(tool_input.template_id),
            identifier_key="templateId",
            identifier_value=tool_input.template_id,
        )

    async def list_text_messages(self, tool_input: TextMessageListRequest) -> dict[str, Any]:
        """List text messages."""
        return await self._page_result(
            lambda: self._services.text_messages.list_text_messages(tool_input),
            key="textmessages",
        )

    async def get_text_message(self, tool_input: GetTextMessageToolInput) -> dict[str, Any]:
        """Get a text message."""
        return await self._single_result(
            lambda: self._services.text_messages.get_text_message(tool_input.text_message_id)
        )

    async def create_text_message(self, tool_input: CreateTextMessageRequest) -> dict[str, Any]:
        """Create a text message record."""
        return await self._single_result(
            lambda: self._services.text_messages.create_text_message(tool_input)
        )

    async def list_text_message_templates(
        self,
        tool_input: TextMessageTemplateListRequest,
    ) -> dict[str, Any]:
        """List text message templates."""
        return await self._page_result(
            lambda: self._services.text_message_templates.list_text_message_templates(tool_input),
            key="textmessagetemplates",
        )

    async def get_text_message_template(
        self,
        tool_input: GetTextMessageTemplateToolInput,
    ) -> dict[str, Any]:
        """Get a text message template."""
        return await self._single_result(
            lambda: self._services.text_message_templates.get_text_message_template(
                tool_input.template_id
            )
        )

    async def merge_text_message_template(
        self,
        tool_input: MergeTextMessageTemplateRequest,
    ) -> dict[str, Any]:
        """Merge a text message template."""
        return await self._single_result(
            lambda: self._services.text_message_templates.merge_text_message_template(tool_input)
        )

    async def create_text_message_template(
        self,
        tool_input: CreateTextMessageTemplateRequest,
    ) -> dict[str, Any]:
        """Create a text message template."""
        return await self._single_result(
            lambda: self._services.text_message_templates.create_text_message_template(tool_input)
        )

    async def update_text_message_template(
        self,
        tool_input: UpdateTextMessageTemplateToolInput,
    ) -> dict[str, Any]:
        """Update a text message template."""
        request = UpdateTextMessageTemplateRequest.model_validate(
            tool_input.model_dump(exclude={"template_id"})
        )
        return await self._single_result(
            lambda: self._services.text_message_templates.update_text_message_template(
                tool_input.template_id,
                request,
            )
        )

    async def delete_text_message_template(
        self,
        tool_input: DeleteTextMessageTemplateToolInput,
    ) -> dict[str, Any]:
        """Delete a text message template."""
        return await self._delete_result(
            lambda: self._services.text_message_templates.delete_text_message_template(
                tool_input.template_id
            ),
            identifier_key="textMessageTemplateId",
            identifier_value=tool_input.template_id,
        )

    async def add_note(
        self, tool_input: CreateNoteRequest, *, wait_for_person: bool = False
    ) -> dict[str, Any]:
        """Add a note."""
        return await self._single_result(
            lambda: self._services.notes.add_note(tool_input, wait_for_person=wait_for_person)
        )

    async def get_note(self, tool_input: GetNoteToolInput) -> dict[str, Any]:
        """Get a note."""
        return await self._single_result(lambda: self._services.notes.get_note(tool_input.note_id))

    async def update_note(self, tool_input: UpdateNoteToolInput) -> dict[str, Any]:
        """Update a note."""
        request = UpdateNoteRequest.model_validate(tool_input.model_dump(exclude={"note_id"}))
        return await self._single_result(
            lambda: self._services.notes.update_note(tool_input.note_id, request)
        )

    async def delete_note(self, tool_input: DeleteNoteToolInput) -> dict[str, Any]:
        """Delete a note."""
        return await self._delete_result(
            lambda: self._services.notes.delete_note(tool_input.note_id),
            identifier_key="noteId",
            identifier_value=tool_input.note_id,
        )

    async def list_webhooks(self, tool_input: WebhookListRequest) -> dict[str, Any]:
        """List webhooks."""
        return await self._page_result(
            lambda: self._services.webhooks.list_webhooks(tool_input),
            key="webhooks",
        )

    async def get_webhook(self, tool_input: GetWebhookToolInput) -> dict[str, Any]:
        """Get a webhook."""
        return await self._single_result(
            lambda: self._services.webhooks.get_webhook(tool_input.webhook_id)
        )

    async def get_webhook_event(self, tool_input: GetWebhookEventToolInput) -> dict[str, Any]:
        """Get a webhook event."""
        return await self._single_result(
            lambda: self._services.webhooks.get_webhook_event(tool_input.webhook_event_id)
        )

    async def create_webhook(self, tool_input: CreateWebhookRequest) -> dict[str, Any]:
        """Create a webhook."""
        return await self._single_result(lambda: self._services.webhooks.create_webhook(tool_input))

    async def update_webhook(self, tool_input: UpdateWebhookToolInput) -> dict[str, Any]:
        """Update a webhook."""
        request = UpdateWebhookRequest.model_validate(tool_input.model_dump(exclude={"webhook_id"}))
        return await self._single_result(
            lambda: self._services.webhooks.update_webhook(tool_input.webhook_id, request)
        )

    async def delete_webhook(self, tool_input: DeleteWebhookToolInput) -> dict[str, Any]:
        """Delete a webhook."""
        return await self._delete_result(
            lambda: self._services.webhooks.delete_webhook(tool_input.webhook_id),
            identifier_key="webhookId",
            identifier_value=tool_input.webhook_id,
        )

    async def _page_result(
        self,
        call: Callable[[], Awaitable[Any]],
        *,
        key: str,
    ) -> dict[str, Any]:
        """Run a paginated service call and normalize the result."""
        try:
            page = await self._execute_with_services(call)
        except FollowUpBossError as exc:
            raise RuntimeError(_mcp_safe_error(exc)) from exc
        return {
            "_metadata": asdict(page.metadata),
            key: [item.model_dump(mode="json", by_alias=True) for item in page.items],
        }

    async def _single_result(self, call: Callable[[], Awaitable[Any]]) -> dict[str, Any]:
        """Run a single-object service call and normalize errors."""
        try:
            result = cast(ResponseModel, await self._execute_with_services(call))
        except FollowUpBossError as exc:
            raise RuntimeError(_mcp_safe_error(exc)) from exc
        return result.model_dump(
            mode="json",
            by_alias=True,
            exclude_defaults=True,
            exclude_none=True,
        )

    async def _delete_result(
        self,
        call: Callable[[], Awaitable[None]],
        *,
        identifier_key: str,
        identifier_value: int,
    ) -> dict[str, Any]:
        """Run a delete operation and return a structured confirmation."""
        try:
            await self._execute_with_services(call)
        except FollowUpBossError as exc:
            raise RuntimeError(_mcp_safe_error(exc)) from exc
        return {"deleted": True, identifier_key: identifier_value}

    async def _execute_with_services(self, call: Callable[[], Awaitable[Any]]) -> Any:
        """Run one callable with the correct service bundle in scope.

        Args:
            call: The service-bound callable to invoke.

        Returns:
            The value returned by the callable.
        """
        if self._service_bundle_resolver is None or _ACTIVE_SERVICE_BUNDLE.get() is not None:
            return await call()

        async with self._service_bundle_resolver.service_bundle() as services:
            token = _ACTIVE_SERVICE_BUNDLE.set(services)
            try:
                return await call()
            finally:
                _ACTIVE_SERVICE_BUNDLE.reset(token)


def _mcp_safe_error(exc: FollowUpBossError) -> str:
    """Return an MCP-safe error message."""
    if isinstance(exc, FollowUpBossRateLimitError) and exc.retry_after_seconds is not None:
        return f"{exc} Retry after {exc.retry_after_seconds:.0f} seconds."
    return str(exc)


def _uncommunicated_lead_fields(fields: list[str] | None) -> list[str]:
    """Return fields required for no-communication filtering and display.

    Args:
        fields: Optional caller-requested projection fields.

    Returns:
        A deterministic field list that always includes `lastCommunication` so
        the helper can post-filter records correctly.
    """
    if fields is None:
        return sorted(_UNCOMMUNICATED_LEAD_RESPONSE_FIELDS)
    return sorted(set(fields) | _UNCOMMUNICATED_LEAD_FILTER_FIELDS)


def _is_empty_last_communication(value: object) -> bool:
    """Return whether a Follow Up Boss lastCommunication value is empty.

    Args:
        value: The raw `lastCommunication` response field, which is `None` for
            no communication and an object when communication exists.

    Returns:
        `True` only when no communication value is present.
    """
    return value in (None, "", 0, "0")


def _pagination_offset(tool_input: ListUncontactedLeadsToolInput) -> int:
    """Return the filtered-result offset requested by the MCP caller.

    Args:
        tool_input: Validated no-communication helper input.

    Returns:
        The explicit offset, numeric next token, or zero.

    Raises:
        RuntimeError: If the supplied next token is not a numeric filtered offset.
    """
    if tool_input.next_token is None:
        return tool_input.offset or 0
    if not tool_input.next_token.isdigit():
        raise RuntimeError("Uncontacted lead pagination token must be a numeric offset.")
    return int(tool_input.next_token)


def _coalesce_text_aliases(
    aliases: tuple[tuple[str, str | None], ...],
    *,
    required_name: str | None,
) -> str | None:
    """Return one normalized value from a set of text aliases.

    Args:
        aliases: Pairs of field names and candidate values.
        required_name: Public field name to report when no value is present.

    Returns:
        The unique normalized value, or `None` when the alias group is optional
        and absent.

    Raises:
        ValueError: If required text is missing or aliases conflict.
    """
    populated = [
        (name, value.strip()) for name, value in aliases if isinstance(value, str) and value.strip()
    ]
    if not populated:
        if required_name is None:
            return None
        raise ValueError(f"{required_name} must be non-empty.")
    normalized_values = {value.casefold() for _, value in populated}
    if len(normalized_values) > 1:
        names = ", ".join(name for name, _ in populated)
        raise ValueError(f"Conflicting values provided for {names}.")
    return populated[0][1]


def _resolve_smart_list_by_name(
    smart_lists: list[SmartListRecord],
    smart_list_name: str,
) -> SmartListRecord:
    """Resolve one smart list by exact normalized name.

    Args:
        smart_lists: Smart-list records available to the authenticated user.
        smart_list_name: User-provided smart-list name.

    Returns:
        The uniquely matching smart list.

    Raises:
        RuntimeError: If the normalized smart-list name is missing or ambiguous.
    """
    normalized_name = _normalize_smart_list_name(smart_list_name)
    matches = [
        smart_list
        for smart_list in smart_lists
        if _normalize_smart_list_name(smart_list.name or "") == normalized_name
    ]
    if not matches:
        raise RuntimeError(f"Smart list named {smart_list_name!r} was not found.")
    if len(matches) > 1:
        match_ids = [smart_list.id for smart_list in matches]
        raise RuntimeError(
            f"Smart list named {smart_list_name!r} is ambiguous; matched IDs {match_ids!r}."
        )
    return matches[0]


def _normalize_user_name(value: str) -> str:
    """Normalize a Follow Up Boss user name for exact matching.

    Args:
        value: Raw user name.

    Returns:
        Lowercased text with repeated whitespace removed.
    """
    return " ".join(value.casefold().strip().split())


def _user_full_name(user: UserRecord) -> str:
    """Return a display name assembled from first and last name fields.

    Args:
        user: Follow Up Boss user record.

    Returns:
        The user's first and last name joined with single spaces.
    """
    return " ".join(part for part in (user.first_name, user.last_name) if part)


def _is_active_user(user: UserRecord) -> bool:
    """Return whether a user record should be considered active for routing.

    Args:
        user: Follow Up Boss user record.

    Returns:
        `True` when the status is absent or does not describe a deleted/inactive
        user.
    """
    if user.status is None:
        return True
    return user.status.casefold() not in {"deleted", "disabled", "inactive", "archived"}


def _normalize_smart_list_name(value: str) -> str:
    """Normalize a smart-list name for exact matching.

    Args:
        value: Raw smart-list name.

    Returns:
        Lowercased text with decorative edge symbols and repeated whitespace removed.
    """
    collapsed = " ".join(value.casefold().strip().split())
    return _strip_decorative_name_edges(collapsed)


def _strip_decorative_name_edges(value: str) -> str:
    """Remove decorative symbols from the edges of a smart-list name.

    Args:
        value: Whitespace-normalized smart-list name.

    Returns:
        The value with leading and trailing non-alphanumeric decorations removed.
    """
    start = 0
    end = len(value)
    while start < end and not value[start].isalnum():
        start += 1
    while end > start and not value[end - 1].isalnum():
        end -= 1
    return value[start:end].strip()
