"""Typed MCP tool adapter layer."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import asdict, dataclass
from typing import Any, cast

from followupboss_mcp.errors import FollowUpBossError, FollowUpBossRateLimitError
from followupboss_mcp.models.appointments import (
    AppointmentListRequest,
    CreateAppointmentRequest,
    UpdateAppointmentRequest,
)
from followupboss_mcp.models.calls import (
    CallListRequest,
    CreateCallRequest,
    UpdateCallRequest,
)
from followupboss_mcp.models.common import RequestModel, ResponseModel
from followupboss_mcp.models.custom_fields import CustomFieldListRequest
from followupboss_mcp.models.deals import (
    CreateDealRequest,
    DealCustomFieldListRequest,
    DealListRequest,
    UpdateDealRequest,
)
from followupboss_mcp.models.events import CreateEventRequest, EventSearchRequest
from followupboss_mcp.models.notes import CreateNoteRequest, UpdateNoteRequest
from followupboss_mcp.models.people import (
    CreatePersonRequest,
    PeopleSearchRequest,
    PersonLookupRequest,
    UpdatePersonRequest,
)
from followupboss_mcp.models.tasks import CreateTaskRequest, TaskListRequest, UpdateTaskRequest
from followupboss_mcp.models.templates import (
    CreateTemplateRequest,
    TemplateListRequest,
    TemplateLookupRequest,
    UpdateTemplateRequest,
)
from followupboss_mcp.models.text_messages import (
    CreateTextMessageTemplateRequest,
    TextMessageListRequest,
    TextMessageTemplateListRequest,
    UpdateTextMessageTemplateRequest,
)
from followupboss_mcp.models.users import UserListRequest
from followupboss_mcp.models.webhooks import CreateWebhookRequest, WebhookListRequest
from followupboss_mcp.services.appointments import AppointmentsService
from followupboss_mcp.services.calls import CallsService
from followupboss_mcp.services.custom_fields import CustomFieldsService
from followupboss_mcp.services.deals import DealsService
from followupboss_mcp.services.events import EventsService
from followupboss_mcp.services.identity import IdentityService
from followupboss_mcp.services.notes import NotesService
from followupboss_mcp.services.people import PeopleService
from followupboss_mcp.services.tasks import TasksService
from followupboss_mcp.services.templates import TemplatesService
from followupboss_mcp.services.text_messages import (
    TextMessagesService,
    TextMessageTemplatesService,
)
from followupboss_mcp.services.users import UsersService
from followupboss_mcp.services.webhooks import WebhooksService


class GetPersonToolInput(PersonLookupRequest):
    """Tool input for fetching a person by ID."""

    person_id: int


class UpdatePersonToolInput(UpdatePersonRequest):
    """Tool input for updating a person."""

    person_id: int


class GetUserToolInput(RequestModel):
    """Tool input for fetching a user by ID."""

    user_id: int


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


class GetDealToolInput(RequestModel):
    """Tool input for fetching a deal by ID."""

    deal_id: int


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


class GetWebhookToolInput(RequestModel):
    """Tool input for fetching a webhook by ID."""

    webhook_id: int


class UpdateNoteToolInput(UpdateNoteRequest):
    """Tool input for updating a note."""

    note_id: int


class UpdateTaskToolInput(UpdateTaskRequest):
    """Tool input for updating a task."""

    task_id: int


class UpdateCallToolInput(UpdateCallRequest):
    """Tool input for updating a call."""

    call_id: int


class UpdateAppointmentToolInput(UpdateAppointmentRequest):
    """Tool input for updating an appointment."""

    appointment_id: int


class UpdateDealToolInput(UpdateDealRequest):
    """Tool input for updating a deal."""

    deal_id: int


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


class DeleteDealToolInput(RequestModel):
    """Tool input for deleting a deal."""

    deal_id: int


class DeleteTextMessageTemplateToolInput(RequestModel):
    """Tool input for deleting a text message template."""

    template_id: int


class DeleteWebhookToolInput(RequestModel):
    """Tool input for deleting a webhook."""

    webhook_id: int


@dataclass(frozen=True)
class ServiceBundle:
    """Service bundle used by the MCP tool adapter."""

    appointments: AppointmentsService
    calls: CallsService
    custom_fields: CustomFieldsService
    deals: DealsService
    events: EventsService
    identity: IdentityService
    notes: NotesService
    people: PeopleService
    tasks: TasksService
    text_message_templates: TextMessageTemplatesService
    text_messages: TextMessagesService
    templates: TemplatesService
    users: UsersService
    webhooks: WebhooksService


class FollowUpBossToolAdapter:
    """Thin MCP-safe adapter around typed domain services."""

    def __init__(self, services: ServiceBundle) -> None:
        """Initialize the adapter."""
        self._services = services

    async def get_identity(self) -> dict[str, Any]:
        """Return identity information."""
        return await self._single_result(self._services.identity.get_identity)

    async def search_people(self, tool_input: PeopleSearchRequest) -> dict[str, Any]:
        """Search people."""
        return await self._page_result(
            lambda: self._services.people.search_people(tool_input),
            key="people",
        )

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

    async def list_users(self, tool_input: UserListRequest) -> dict[str, Any]:
        """List users."""
        return await self._page_result(
            lambda: self._services.users.list_users(tool_input),
            key="users",
        )

    async def get_user(self, tool_input: GetUserToolInput) -> dict[str, Any]:
        """Get a user."""
        return await self._single_result(lambda: self._services.users.get_user(tool_input.user_id))

    async def list_custom_fields(self, tool_input: CustomFieldListRequest) -> dict[str, Any]:
        """List custom fields."""
        return await self._page_result(
            lambda: self._services.custom_fields.list_custom_fields(tool_input),
            key="customfields",
        )

    async def list_deals(self, tool_input: DealListRequest) -> dict[str, Any]:
        """List deals."""
        return await self._page_result(
            lambda: self._services.deals.list_deals(tool_input),
            key="deals",
        )

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

    async def list_deal_custom_fields(
        self, tool_input: DealCustomFieldListRequest
    ) -> dict[str, Any]:
        """List deal custom fields."""
        return await self._page_result(
            lambda: self._services.deals.list_deal_custom_fields(tool_input),
            key="dealCustomfields",
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

    async def create_webhook(self, tool_input: CreateWebhookRequest) -> dict[str, Any]:
        """Create a webhook."""
        return await self._single_result(lambda: self._services.webhooks.create_webhook(tool_input))

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
            page = await call()
        except FollowUpBossError as exc:
            raise RuntimeError(_mcp_safe_error(exc)) from exc
        return {
            "_metadata": asdict(page.metadata),
            key: [item.model_dump(mode="json", by_alias=True) for item in page.items],
        }

    async def _single_result(self, call: Callable[[], Awaitable[Any]]) -> dict[str, Any]:
        """Run a single-object service call and normalize errors."""
        try:
            result = cast(ResponseModel, await call())
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
            await call()
        except FollowUpBossError as exc:
            raise RuntimeError(_mcp_safe_error(exc)) from exc
        return {"deleted": True, identifier_key: identifier_value}


def _mcp_safe_error(exc: FollowUpBossError) -> str:
    """Return an MCP-safe error message."""
    if isinstance(exc, FollowUpBossRateLimitError) and exc.retry_after_seconds is not None:
        return f"{exc} Retry after {exc.retry_after_seconds:.0f} seconds."
    return str(exc)
