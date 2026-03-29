"""Tests for the MCP adapter, FastMCP server wiring, and CLI."""

from __future__ import annotations

import asyncio
import os
import socket
import sys
import textwrap
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import AnyUrl, TypeAdapter

from followupboss_mcp.cli import build_parser, main
from followupboss_mcp.config import FollowUpBossSettings
from followupboss_mcp.errors import FollowUpBossRateLimitError, FollowUpBossValidationError
from followupboss_mcp.mcp_server import create_server
from followupboss_mcp.mcp_tools import (
    DeleteAppointmentOutcomeToolInput,
    DeleteAppointmentToolInput,
    DeleteAppointmentTypeToolInput,
    DeleteDealToolInput,
    DeleteNoteToolInput,
    DeletePipelineToolInput,
    DeletePondToolInput,
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
    GetCallToolInput,
    GetDealToolInput,
    GetEventToolInput,
    GetNoteToolInput,
    GetPersonToolInput,
    GetPipelineToolInput,
    GetPondToolInput,
    GetSmartListToolInput,
    GetStageToolInput,
    GetTaskToolInput,
    GetTeamToolInput,
    GetTemplateToolInput,
    GetTextMessageTemplateToolInput,
    GetTextMessageToolInput,
    GetUserToolInput,
    GetWebhookToolInput,
    ServiceBundle,
    UpdateAppointmentOutcomeToolInput,
    UpdateAppointmentToolInput,
    UpdateAppointmentTypeToolInput,
    UpdateCallToolInput,
    UpdateDealToolInput,
    UpdateNoteToolInput,
    UpdatePersonToolInput,
    UpdatePipelineToolInput,
    UpdatePondToolInput,
    UpdateStageToolInput,
    UpdateTaskToolInput,
    UpdateTeamToolInput,
    UpdateTemplateToolInput,
    UpdateTextMessageTemplateToolInput,
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
    AppointmentListRequest,
    AppointmentRecord,
    CreateAppointmentRequest,
)
from followupboss_mcp.models.calls import CallListRequest, CallRecord, CreateCallRequest
from followupboss_mcp.models.custom_fields import CustomFieldListRequest, CustomFieldRecord
from followupboss_mcp.models.deals import (
    CreateDealRequest,
    DealCustomFieldListRequest,
    DealCustomFieldRecord,
    DealListRequest,
    DealRecord,
)
from followupboss_mcp.models.events import (
    CreateEventRequest,
    EventPersonInput,
    EventRecord,
    EventSearchRequest,
)
from followupboss_mcp.models.identity import IdentityResponse
from followupboss_mcp.models.notes import CreateNoteRequest, NoteRecord
from followupboss_mcp.models.people import CreatePersonRequest, PeopleSearchRequest, PersonRecord
from followupboss_mcp.models.pipelines import (
    CreatePipelineRequest,
    PipelineListRequest,
    PipelineRecord,
    PipelineStageInput,
)
from followupboss_mcp.models.ponds import CreatePondRequest, PondListRequest, PondRecord
from followupboss_mcp.models.smart_lists import SmartListListRequest, SmartListRecord
from followupboss_mcp.models.stages import (
    CreateStageRequest,
    StageListRequest,
    StageRecord,
)
from followupboss_mcp.models.tasks import CreateTaskRequest, TaskListRequest, TaskRecord
from followupboss_mcp.models.teams import CreateTeamRequest, TeamListRequest, TeamRecord
from followupboss_mcp.models.templates import (
    CreateTemplateRequest,
    TemplateListRequest,
    TemplateRecord,
)
from followupboss_mcp.models.text_messages import (
    CreateTextMessageTemplateRequest,
    TextMessageListRequest,
    TextMessageRecord,
    TextMessageTemplateListRequest,
    TextMessageTemplateRecord,
)
from followupboss_mcp.models.users import UserListRequest, UserRecord
from followupboss_mcp.models.webhooks import CreateWebhookRequest, WebhookListRequest, WebhookRecord
from followupboss_mcp.pagination import PageResult, PaginationMetadata
from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.client.streamable_http import streamable_http_client

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _page_metadata() -> PaginationMetadata:
    return PaginationMetadata(count=1, limit=10, next_token=None, next_link=None, offset=0, total=1)


def _reserve_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        sock.listen(1)
        return int(sock.getsockname()[1])


async def _wait_for_port(host: str, port: int, *, attempts: int = 50) -> None:
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


def _service_stub(**methods: object) -> Any:
    """Return a tiny typed-as-Any service stub."""
    return SimpleNamespace(**methods)


@dataclass
class StubBundle:
    """Service bundle stub for adapter-only tests."""

    def __post_init__(self) -> None:
        async def identity_get() -> IdentityResponse:
            return IdentityResponse(id=1, name="Picard")

        async def people_search(_: PeopleSearchRequest) -> PageResult[PersonRecord]:
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

        async def events_search(_: EventSearchRequest) -> PageResult[EventRecord]:
            return PageResult(
                items=[EventRecord(id=4, personId=2, type="Inquiry")], metadata=_page_metadata()
            )

        async def events_send(_: CreateEventRequest) -> EventRecord:
            return EventRecord(id=5, personId=2, type="Inquiry")

        async def events_get(event_id: int) -> EventRecord:
            return EventRecord(id=event_id, personId=2, type="Inquiry")

        async def users_list(_: UserListRequest) -> PageResult[UserRecord]:
            return PageResult(items=[UserRecord(id=6, name="Geordi")], metadata=_page_metadata())

        async def users_get(user_id: int) -> UserRecord:
            return UserRecord(id=user_id, name="Crusher")

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

        async def deals_list(_: DealListRequest) -> PageResult[DealRecord]:
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
                        name="Active Buyers",
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

        async def appointments_list(_: AppointmentListRequest) -> PageResult[AppointmentRecord]:
            return PageResult(
                items=[
                    AppointmentRecord(
                        id=8,
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

        async def calls_list(_: CallListRequest) -> PageResult[CallRecord]:
            return PageResult(
                items=[CallRecord(id=11, personId=2, phone="555-0000", userName="Data")],
                metadata=_page_metadata(),
            )

        async def calls_get(call_id: int) -> CallRecord:
            return CallRecord(id=call_id, personId=2, phone="555-0000", userName="Data")

        async def calls_create(_: CreateCallRequest) -> CallRecord:
            return CallRecord(id=12, personId=2, phone="555-0000", userName="Data")

        async def calls_update(call_id: int, request: object) -> CallRecord:
            del request
            return CallRecord(id=call_id, personId=2, phone="555-0000", userName="Data")

        async def tasks_list(_: TaskListRequest) -> PageResult[TaskRecord]:
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

        async def templates_create(_: CreateTemplateRequest) -> TemplateRecord:
            return TemplateRecord(id=20, name="New template", subject="Hello")

        async def templates_update(template_id: int, request: object) -> TemplateRecord:
            del request
            return TemplateRecord(id=template_id, name="Updated template", subject="Updated")

        async def templates_delete(template_id: int) -> None:
            del template_id

        async def text_messages_list(_: TextMessageListRequest) -> PageResult[TextMessageRecord]:
            return PageResult(
                items=[TextMessageRecord(id=31, personId=2, message="Hi there", userName="Data")],
                metadata=_page_metadata(),
            )

        async def text_messages_get(text_message_id: int) -> TextMessageRecord:
            return TextMessageRecord(
                id=text_message_id,
                personId=2,
                message="Hi there",
                userName="Data",
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

        async def webhooks_delete(webhook_id: int) -> None:
            del webhook_id

        self.bundle = ServiceBundle(
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
            calls=_service_stub(
                list_calls=calls_list,
                get_call=calls_get,
                create_call=calls_create,
                update_call=calls_update,
            ),
            custom_fields=_service_stub(list_custom_fields=custom_fields_list),
            deals=_service_stub(
                list_deals=deals_list,
                get_deal=deals_get,
                create_deal=deals_create,
                update_deal=deals_update,
                delete_deal=deals_delete,
                list_deal_custom_fields=deal_custom_fields_list,
            ),
            events=_service_stub(
                search_events=events_search,
                get_event=events_get,
                send_event=events_send,
            ),
            identity=_service_stub(get_identity=identity_get),
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
            teams=_service_stub(
                list_teams=teams_list,
                get_team=teams_get,
                create_team=teams_create,
                update_team=teams_update,
                delete_team=teams_delete,
            ),
            text_message_templates=_service_stub(
                list_text_message_templates=text_message_templates_list,
                get_text_message_template=text_message_templates_get,
                create_text_message_template=text_message_templates_create,
                update_text_message_template=text_message_templates_update,
                delete_text_message_template=text_message_templates_delete,
            ),
            text_messages=_service_stub(
                list_text_messages=text_messages_list,
                get_text_message=text_messages_get,
            ),
            templates=_service_stub(
                list_templates=templates_list,
                get_template=templates_get,
                create_template=templates_create,
                update_template=templates_update,
                delete_template=templates_delete,
            ),
            users=_service_stub(list_users=users_list, get_user=users_get),
            webhooks=_service_stub(
                list_webhooks=webhooks_list,
                get_webhook=webhooks_get,
                create_webhook=webhooks_create,
                delete_webhook=webhooks_delete,
            ),
        )


@pytest.mark.asyncio
async def test_tool_adapter_success_and_failure_paths() -> None:
    """The MCP adapter should normalize service results and safe errors."""
    services = StubBundle().bundle
    adapter = FollowUpBossToolAdapter(services)
    assert (await adapter.get_identity())["id"] == 1
    assert (await adapter.search_people(PeopleSearchRequest()))["people"][0]["id"] == 2
    assert (await adapter.get_person(GetPersonToolInput(person_id=3)))["id"] == 3
    assert (await adapter.create_person(CreatePersonRequest(first_name="Tom")))["id"] == 3
    assert (await adapter.update_person(UpdatePersonToolInput(person_id=4)))["id"] == 4
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
    assert (await adapter.list_custom_fields(CustomFieldListRequest()))["customfields"][0][
        "id"
    ] == 7
    assert (await adapter.list_deals(DealListRequest()))["deals"][0]["id"] == 8
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
    assert (await adapter.list_deal_custom_fields(DealCustomFieldListRequest()))[
        "dealCustomfields"
    ][0]["id"] == 10
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
    assert (
        await adapter.delete_team(DeleteTeamToolInput(team_id=85, move_to_team_id=82))
    ) == {
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
    assert (await adapter.update_call(UpdateCallToolInput(call_id=13, note="Updated note")))[
        "id"
    ] == 13
    assert (await adapter.list_tasks(TaskListRequest()))["tasks"][0]["id"] == 17
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
    assert (await adapter.list_text_message_templates(TextMessageTemplateListRequest()))[
        "textmessagetemplates"
    ][0]["id"] == 32
    assert (
        await adapter.get_text_message_template(GetTextMessageTemplateToolInput(template_id=33))
    )["id"] == 33
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
        await adapter.create_webhook(
            CreateWebhookRequest(event="peopleCreated", url="https://example.com")
        )
    )["id"] == 10
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
        appointments=services.appointments,
        appointment_outcomes=services.appointment_outcomes,
        appointment_types=services.appointment_types,
        calls=services.calls,
        custom_fields=services.custom_fields,
        deals=services.deals,
        events=services.events,
        identity=_service_stub(get_identity=boom),
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
        ponds=services.ponds,
        pipelines=services.pipelines,
        smart_lists=services.smart_lists,
        stages=services.stages,
        tasks=services.tasks,
        teams=services.teams,
        text_message_templates=services.text_message_templates,
        text_messages=services.text_messages,
        templates=services.templates,
        users=services.users,
        webhooks=services.webhooks,
    )
    adapter = FollowUpBossToolAdapter(failing)
    with pytest.raises(RuntimeError, match="Retry after 9 seconds"):
        await adapter.get_identity()
    with pytest.raises(RuntimeError, match="bad people"):
        await adapter.search_people(PeopleSearchRequest())
    with pytest.raises(RuntimeError, match="bad delete"):
        await adapter.delete_note(DeleteNoteToolInput(note_id=1))


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
                {"_metadata": {"limit": 10, "offset": 0, "total": 1}, "people": [{"id": 2}]},
                {"id": 3},
                {"id": 4},
                {"id": 5},
                {"_metadata": {"limit": 10, "offset": 0, "total": 1}, "events": [{"id": 6}]},
                {"id": 7},
                {"id": 8},
                {"_metadata": {"limit": 10, "offset": 0, "total": 1}, "users": [{"id": 9}]},
                {"id": 10},
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
                {
                    "_metadata": {"limit": 10, "offset": 0, "total": 1},
                    "customfields": [
                        {"id": 11, "label": "Birthday", "name": "customBirthday", "type": "date"}
                    ],
                },
                {"_metadata": {"limit": 10, "offset": 0, "total": 1}, "deals": [{"id": 40}]},
                {"id": 41, "name": "Buyer contract"},
                {"id": 42, "name": "New deal"},
                {"id": 43, "name": "Updated deal"},
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
                {"id": 14, "personId": 2, "phone": "555-0000", "userName": "Data"},
                {"id": 15, "personId": 2, "phone": "555-0000", "userName": "Data"},
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
                    "_metadata": {"limit": 10, "offset": 0, "total": 1},
                    "textmessagetemplates": [{"id": 52, "name": "Buyer intro text"}],
                },
                {"id": 53, "name": "Buyer intro text", "message": "Hi there"},
                {"id": 54, "name": "New text template", "message": "Hello there"},
                {"id": 55, "name": "Updated text template", "message": "Updated text"},
                {},
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
                {"id": 29, "event": "peopleCreated", "url": "https://example.com"},
                {},
                {
                    "_metadata": {"limit": 10, "offset": 0, "total": 1},
                    "appointments": [{"id": 30, "title": "Buyer consult"}],
                },
                {"id": 31, "title": "Buyer consult"},
                {"id": 32, "title": "Listing appointment"},
                {"id": 33, "title": "Updated appointment"},
                {},
            ]
        ),
    )
    tools = server._tool_manager._tools
    assert sorted(tools) == [
        "followupboss_add_note",
        "followupboss_create_appointment",
        "followupboss_create_appointment_outcome",
        "followupboss_create_appointment_type",
        "followupboss_create_call",
        "followupboss_create_deal",
        "followupboss_create_person",
        "followupboss_create_pipeline",
        "followupboss_create_pond",
        "followupboss_create_stage",
        "followupboss_create_task",
        "followupboss_create_team",
        "followupboss_create_template",
        "followupboss_create_text_message_template",
        "followupboss_create_webhook",
        "followupboss_delete_appointment",
        "followupboss_delete_appointment_outcome",
        "followupboss_delete_appointment_type",
        "followupboss_delete_deal",
        "followupboss_delete_note",
        "followupboss_delete_pipeline",
        "followupboss_delete_pond",
        "followupboss_delete_stage",
        "followupboss_delete_task",
        "followupboss_delete_team",
        "followupboss_delete_template",
        "followupboss_delete_text_message_template",
        "followupboss_delete_webhook",
        "followupboss_get_appointment",
        "followupboss_get_appointment_outcome",
        "followupboss_get_appointment_type",
        "followupboss_get_call",
        "followupboss_get_deal",
        "followupboss_get_event",
        "followupboss_get_identity",
        "followupboss_get_note",
        "followupboss_get_person",
        "followupboss_get_pipeline",
        "followupboss_get_pond",
        "followupboss_get_smart_list",
        "followupboss_get_stage",
        "followupboss_get_task",
        "followupboss_get_team",
        "followupboss_get_template",
        "followupboss_get_text_message",
        "followupboss_get_text_message_template",
        "followupboss_get_user",
        "followupboss_get_webhook",
        "followupboss_list_appointment_outcomes",
        "followupboss_list_appointment_types",
        "followupboss_list_appointments",
        "followupboss_list_calls",
        "followupboss_list_custom_fields",
        "followupboss_list_deal_custom_fields",
        "followupboss_list_deals",
        "followupboss_list_pipelines",
        "followupboss_list_ponds",
        "followupboss_list_smart_lists",
        "followupboss_list_stages",
        "followupboss_list_tasks",
        "followupboss_list_teams",
        "followupboss_list_templates",
        "followupboss_list_text_message_templates",
        "followupboss_list_text_messages",
        "followupboss_list_users",
        "followupboss_list_webhooks",
        "followupboss_search_events",
        "followupboss_search_people",
        "followupboss_send_event",
        "followupboss_update_appointment",
        "followupboss_update_appointment_outcome",
        "followupboss_update_appointment_type",
        "followupboss_update_call",
        "followupboss_update_deal",
        "followupboss_update_note",
        "followupboss_update_person",
        "followupboss_update_pipeline",
        "followupboss_update_pond",
        "followupboss_update_stage",
        "followupboss_update_task",
        "followupboss_update_team",
        "followupboss_update_template",
        "followupboss_update_text_message_template",
    ]

    assert await tools["followupboss_get_identity"].fn() == {"id": 1}
    assert (await tools["followupboss_search_people"].fn(email="a@example.com"))["people"][0][
        "id"
    ] == 2
    assert await tools["followupboss_get_person"].fn(3) == {"id": 3}
    assert (await tools["followupboss_create_person"].fn(first_name="Tom"))["id"] == 4
    assert (await tools["followupboss_update_person"].fn(5, first_name="Will"))["id"] == 5
    assert (await tools["followupboss_search_events"].fn(person_id=1))["events"][0]["id"] == 6
    assert (await tools["followupboss_get_event"].fn(7))["id"] == 7
    assert (
        await tools["followupboss_send_event"].fn(
            source="Portal",
            system="Portal",
            type="Inquiry",
            person={},
        )
    )["id"] == 8
    assert (await tools["followupboss_list_users"].fn())["users"][0]["id"] == 9
    assert (await tools["followupboss_get_user"].fn(10))["id"] == 10
    assert (await tools["followupboss_list_appointment_outcomes"].fn())["appointmentoutcomes"][0][
        "id"
    ] == 90
    assert (await tools["followupboss_get_appointment_outcome"].fn(91))["id"] == 91
    assert (await tools["followupboss_create_appointment_outcome"].fn(name="No Show"))["id"] == 92
    assert (
        await tools["followupboss_update_appointment_outcome"].fn(
            93,
            name="Rescheduled",
        )
    )["id"] == 93
    assert await tools["followupboss_delete_appointment_outcome"].fn(94, 91) == {
        "deleted": True,
        "appointmentOutcomeId": 94,
    }
    assert (await tools["followupboss_list_appointment_types"].fn())["appointmenttypes"][0][
        "id"
    ] == 94
    assert (await tools["followupboss_get_appointment_type"].fn(95))["id"] == 95
    assert (await tools["followupboss_create_appointment_type"].fn(name="Listing Consult"))[
        "id"
    ] == 96
    assert (
        await tools["followupboss_update_appointment_type"].fn(
            97,
            name="Showing",
        )
    )["id"] == 97
    assert await tools["followupboss_delete_appointment_type"].fn(98, 95) == {
        "deleted": True,
        "appointmentTypeId": 98,
    }
    assert (await tools["followupboss_list_custom_fields"].fn())["customfields"][0]["id"] == 11
    assert (await tools["followupboss_list_deals"].fn())["deals"][0]["id"] == 40
    assert (await tools["followupboss_get_deal"].fn(41))["id"] == 41
    assert (await tools["followupboss_create_deal"].fn(name="New deal", stage_id=7))["id"] == 42
    assert (await tools["followupboss_update_deal"].fn(43, stage_id=8))["id"] == 43
    assert await tools["followupboss_delete_deal"].fn(44) == {"deleted": True, "dealId": 44}
    assert (await tools["followupboss_list_deal_custom_fields"].fn())["dealCustomfields"][0][
        "id"
    ] == 44
    assert (await tools["followupboss_list_pipelines"].fn())["pipelines"][0]["id"] == 60
    assert (await tools["followupboss_get_pipeline"].fn(61))["id"] == 61
    assert (await tools["followupboss_create_pipeline"].fn(name="New pipeline"))["id"] == 62
    assert (await tools["followupboss_update_pipeline"].fn(63, name="Updated pipeline"))["id"] == 63
    assert await tools["followupboss_delete_pipeline"].fn(64) == {
        "deleted": True,
        "pipelineId": 64,
    }
    assert (await tools["followupboss_list_ponds"].fn())["ponds"][0]["id"] == 65
    assert (await tools["followupboss_get_pond"].fn(66))["id"] == 66
    assert (await tools["followupboss_create_pond"].fn("Sphere Builders", 8, [8, 9]))["id"] == 67
    assert (await tools["followupboss_update_pond"].fn(68, name="Updated Pond"))["id"] == 68
    assert await tools["followupboss_delete_pond"].fn(69, 9) == {
        "deleted": True,
        "pondId": 69,
    }
    assert (await tools["followupboss_list_smart_lists"].fn())["smartlists"][0]["id"] == 76
    assert (await tools["followupboss_get_smart_list"].fn(77))["id"] == 77
    assert (await tools["followupboss_list_stages"].fn())["stages"][0]["id"] == 78
    assert (await tools["followupboss_get_stage"].fn(79))["id"] == 79
    assert (await tools["followupboss_create_stage"].fn("Qualified"))["id"] == 80
    assert (await tools["followupboss_update_stage"].fn(81, name="Updated Stage"))["id"] == 81
    assert await tools["followupboss_delete_stage"].fn(82, 11) == {
        "deleted": True,
        "stageId": 82,
    }
    assert (await tools["followupboss_list_teams"].fn())["teams"][0]["id"] == 83
    assert (await tools["followupboss_get_team"].fn(84))["id"] == 84
    assert (await tools["followupboss_create_team"].fn("Buyer Team", [7, 8]))["id"] == 85
    assert (await tools["followupboss_update_team"].fn(86, name="Updated Team"))["id"] == 86
    assert await tools["followupboss_delete_team"].fn(87) == {
        "deleted": True,
        "teamId": 87,
    }
    assert (await tools["followupboss_list_calls"].fn())["calls"][0]["id"] == 12
    assert (await tools["followupboss_get_call"].fn(13))["id"] == 13
    assert (await tools["followupboss_create_call"].fn(1, "555-0000", True))["id"] == 14
    assert (await tools["followupboss_update_call"].fn(15, note="Updated note"))["id"] == 15
    assert (await tools["followupboss_list_tasks"].fn())["tasks"][0]["id"] == 16
    assert (await tools["followupboss_get_task"].fn(17))["id"] == 17
    assert (await tools["followupboss_create_task"].fn(1, assigned_to="Data", type="Email"))[
        "id"
    ] == 18
    assert (await tools["followupboss_update_task"].fn(19, type="Text"))["id"] == 19
    assert await tools["followupboss_delete_task"].fn(20) == {"deleted": True, "taskId": 20}
    assert (await tools["followupboss_list_templates"].fn())["templates"][0]["id"] == 20
    assert (await tools["followupboss_get_template"].fn(21))["id"] == 21
    assert (
        await tools["followupboss_create_template"].fn(
            name="New template",
            subject="Hello",
            body="<p>Hello</p>",
        )
    )["id"] == 22
    assert (
        await tools["followupboss_update_template"].fn(
            23,
            name="Updated template",
            subject="Updated",
            body="<p>Updated</p>",
        )
    )["id"] == 23
    assert await tools["followupboss_delete_template"].fn(24) == {
        "deleted": True,
        "templateId": 24,
    }
    assert (await tools["followupboss_list_text_messages"].fn())["textmessages"][0]["id"] == 50
    assert (await tools["followupboss_get_text_message"].fn(51))["id"] == 51
    assert (await tools["followupboss_list_text_message_templates"].fn())["textmessagetemplates"][
        0
    ]["id"] == 52
    assert (await tools["followupboss_get_text_message_template"].fn(53))["id"] == 53
    assert (
        await tools["followupboss_create_text_message_template"].fn(
            name="New text template",
            message="Hello there",
        )
    )["id"] == 54
    assert (
        await tools["followupboss_update_text_message_template"].fn(
            55,
            name="Updated text template",
            message="Updated text",
        )
    )["id"] == 55
    assert await tools["followupboss_delete_text_message_template"].fn(56) == {
        "deleted": True,
        "textMessageTemplateId": 56,
    }
    assert (await tools["followupboss_add_note"].fn(1, body="hi"))["id"] == 24
    assert (await tools["followupboss_get_note"].fn(25))["id"] == 25
    assert (await tools["followupboss_update_note"].fn(26, body="updated"))["id"] == 26
    assert await tools["followupboss_delete_note"].fn(27) == {"deleted": True, "noteId": 27}
    assert (await tools["followupboss_list_webhooks"].fn())["webhooks"][0]["id"] == 27
    assert (await tools["followupboss_get_webhook"].fn(28))["id"] == 28
    assert (await tools["followupboss_create_webhook"].fn("peopleCreated", "https://example.com"))[
        "id"
    ] == 29
    assert await tools["followupboss_delete_webhook"].fn(30) == {"deleted": True, "webhookId": 30}
    assert (await tools["followupboss_list_appointments"].fn())["appointments"][0]["id"] == 30
    assert (await tools["followupboss_get_appointment"].fn(31))["id"] == 31
    assert (
        await tools["followupboss_create_appointment"].fn(
            title="Listing appointment",
            start="2026-03-28T10:00:00Z",
            end="2026-03-28T11:00:00Z",
        )
    )["id"] == 32
    assert (
        await tools["followupboss_update_appointment"].fn(
            33,
            title="Updated appointment",
            start="2026-03-29T10:00:00Z",
            end="2026-03-29T11:00:00Z",
        )
    )["id"] == 33
    assert await tools["followupboss_delete_appointment"].fn(34) == {
        "deleted": True,
        "appointmentId": 34,
    }

    resource = server._resource_manager._resources["followupboss://api-coverage-matrix"]
    resource_text = await resource.read()
    assert "API Coverage Matrix" in resource_text

    prompt = server._prompt_manager._prompts["followupboss_compose_lead_event"]
    messages = await prompt.render(
        arguments={
            "source": "Portal",
            "type": "Inquiry",
            "message": "Hi",
            "email": "a@example.com",
        }
    )
    content_text = getattr(messages[0].content, "text", None)
    assert isinstance(content_text, str)
    assert content_text.startswith("Create a Follow Up Boss POST /events payload")


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
                    {"_metadata": {"limit": 10, "offset": 0, "total": 1}, "people": [{"id": 2}]},
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
    server_env = dict(os.environ)
    existing_pythonpath = server_env.get("PYTHONPATH")
    pythonpath_entries = [str(PROJECT_ROOT / "src")]
    if existing_pythonpath:
        pythonpath_entries.append(existing_pythonpath)
    server_env["PYTHONPATH"] = os.pathsep.join(pythonpath_entries)
    server = StdioServerParameters(
        command=sys.executable,
        args=["-c", server_script],
        cwd=str(PROJECT_ROOT),
        env=server_env,
    )
    resource_uri = TypeAdapter(AnyUrl).validate_python("followupboss://api-coverage-matrix")

    async with stdio_client(server) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()

            tools = await session.list_tools()
            tool_names = sorted(tool.name for tool in tools.tools)
            assert "followupboss_get_appointment" in tool_names
            assert "followupboss_get_call" in tool_names
            assert "followupboss_get_event" in tool_names
            assert "followupboss_get_identity" in tool_names
            assert "followupboss_get_task" in tool_names
            assert "followupboss_get_template" in tool_names
            assert "followupboss_list_appointments" in tool_names
            assert "followupboss_list_calls" in tool_names
            assert "followupboss_list_tasks" in tool_names
            assert "followupboss_list_templates" in tool_names
            assert "followupboss_search_people" in tool_names

            identity_result = await session.call_tool("followupboss_get_identity")
            assert identity_result.isError is False
            assert identity_result.structuredContent == {"id": 1, "name": "Picard"}

            people_result = await session.call_tool(
                "followupboss_search_people",
                {"email": "a@example.com"},
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
            assert [str(resource.uri) for resource in resources.resources] == [
                "followupboss://api-coverage-matrix"
            ]
            resource_result = await session.read_resource(resource_uri)
            resource_text = getattr(resource_result.contents[0], "text", None)
            assert isinstance(resource_text, str)
            assert "API Coverage Matrix" in resource_text

            prompts = await session.list_prompts()
            assert [prompt.name for prompt in prompts.prompts] == [
                "followupboss_compose_lead_event"
            ]
            prompt_result = await session.get_prompt(
                "followupboss_compose_lead_event",
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
    server_env = dict(os.environ)
    existing_pythonpath = server_env.get("PYTHONPATH")
    pythonpath_entries = [str(PROJECT_ROOT / "src")]
    if existing_pythonpath:
        pythonpath_entries.append(existing_pythonpath)
    server_env["PYTHONPATH"] = os.pathsep.join(pythonpath_entries)

    process = await asyncio.create_subprocess_exec(
        sys.executable,
        "-c",
        server_script,
        cwd=str(PROJECT_ROOT),
        env=server_env,
    )
    try:
        await _wait_for_port("127.0.0.1", port)
        resource_uri = TypeAdapter(AnyUrl).validate_python("followupboss://api-coverage-matrix")
        async with streamable_http_client(f"http://127.0.0.1:{port}/mcp") as (
            read_stream,
            write_stream,
            _,
        ):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()

                tools = await session.list_tools()
                tool_names = sorted(tool.name for tool in tools.tools)
                assert "followupboss_get_identity" in tool_names

                identity_result = await session.call_tool("followupboss_get_identity")
                assert identity_result.isError is False
                assert identity_result.structuredContent == {"id": 1, "name": "Picard"}

                resources = await session.list_resources()
                assert [str(resource.uri) for resource in resources.resources] == [
                    "followupboss://api-coverage-matrix"
                ]
                resource_result = await session.read_resource(resource_uri)
                resource_text = getattr(resource_result.contents[0], "text", None)
                assert isinstance(resource_text, str)
                assert "API Coverage Matrix" in resource_text

                prompts = await session.list_prompts()
                assert [prompt.name for prompt in prompts.prompts] == [
                    "followupboss_compose_lead_event"
                ]
                prompt_result = await session.get_prompt(
                    "followupboss_compose_lead_event",
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

    runs: list[tuple[str, dict[str, Any]]] = []

    class FakeServer:
        def run(self, transport: str) -> None:
            runs.append((transport, {}))

    def fake_create_server(settings: object, **kwargs: object) -> FakeServer:
        runs.append(("create", kwargs))
        return FakeServer()

    monkeypatch.setattr(
        "followupboss_mcp.cli.FollowUpBossSettings",
        lambda: _service_stub(),
    )
    monkeypatch.setattr("followupboss_mcp.cli.create_server", fake_create_server)

    assert main(["stdio"]) == 0
    assert main(["streamable-http", "--host", "0.0.0.0", "--port", "9000", "--path", "/alt"]) == 0
    assert runs == [
        ("create", {}),
        ("stdio", {}),
        ("create", {"host": "0.0.0.0", "port": 9000, "streamable_http_path": "/alt"}),
        ("streamable-http", {}),
    ]
