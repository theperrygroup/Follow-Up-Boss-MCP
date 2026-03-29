"""Tests for the typed service layer."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any

import pytest
from pydantic import ValidationError

from followupboss_mcp.errors import FollowUpBossNotFoundError, FollowUpBossValidationError
from followupboss_mcp.http_client import JsonPayload
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
    AppointmentInviteeInput,
    AppointmentListRequest,
    CreateAppointmentRequest,
    UpdateAppointmentRequest,
)
from followupboss_mcp.models.calls import CallListRequest, CreateCallRequest, UpdateCallRequest
from followupboss_mcp.models.common import EmailAddress
from followupboss_mcp.models.custom_fields import CustomFieldListRequest
from followupboss_mcp.models.deals import (
    CreateDealRequest,
    DealCustomFieldListRequest,
    DealListRequest,
    UpdateDealRequest,
)
from followupboss_mcp.models.events import CreateEventRequest, EventPersonInput, EventSearchRequest
from followupboss_mcp.models.identity import IdentityResponse
from followupboss_mcp.models.notes import CreateNoteRequest, UpdateNoteRequest
from followupboss_mcp.models.people import (
    CreatePersonRequest,
    PeopleSearchRequest,
    PersonLookupRequest,
    PersonRecord,
    UpdatePersonRequest,
)
from followupboss_mcp.models.pipelines import (
    CreatePipelineRequest,
    PipelineListRequest,
    PipelineStageInput,
    UpdatePipelineRequest,
)
from followupboss_mcp.models.ponds import (
    CreatePondRequest,
    DeletePondRequest,
    PondListRequest,
    UpdatePondRequest,
)
from followupboss_mcp.models.smart_lists import SmartListListRequest
from followupboss_mcp.models.stages import (
    CreateStageRequest,
    DeleteStageRequest,
    StageListRequest,
    UpdateStageRequest,
)
from followupboss_mcp.models.tasks import (
    CreateTaskRequest,
    TaskListRequest,
    UpdateTaskRequest,
)
from followupboss_mcp.models.teams import (
    CreateTeamRequest,
    DeleteTeamRequest,
    TeamListRequest,
    UpdateTeamRequest,
)
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
from followupboss_mcp.services.appointment_metadata import (
    AppointmentOutcomesService,
    AppointmentTypesService,
)
from followupboss_mcp.services.appointments import AppointmentsService
from followupboss_mcp.services.calls import CallsService
from followupboss_mcp.services.custom_fields import CustomFieldsService
from followupboss_mcp.services.deals import DealsService
from followupboss_mcp.services.events import EventsService
from followupboss_mcp.services.identity import IdentityService
from followupboss_mcp.services.notes import NotesService
from followupboss_mcp.services.people import PeopleService
from followupboss_mcp.services.pipelines import PipelinesService
from followupboss_mcp.services.ponds import PondsService
from followupboss_mcp.services.smart_lists import SmartListsService
from followupboss_mcp.services.stages import StagesService
from followupboss_mcp.services.tasks import TasksService
from followupboss_mcp.services.teams import TeamsService
from followupboss_mcp.services.templates import TemplatesService
from followupboss_mcp.services.text_messages import (
    TextMessagesService,
    TextMessageTemplatesService,
)
from followupboss_mcp.services.users import UsersService
from followupboss_mcp.services.webhooks import WebhooksService


@dataclass
class StubCall:
    """Recorded client call."""

    json_body: dict[str, object] | None
    method: str
    params: dict[str, str] | None
    path: str


class StubClient:
    """Very small async client stub."""

    def __init__(self, responses: list[JsonPayload | Exception]) -> None:
        self.calls: list[StubCall] = []
        self.responses = responses

    async def aclose(self) -> None:
        """Close the stub client."""

    async def request_json(
        self,
        method: str,
        path: str,
        *,
        headers: Mapping[str, str] | None = None,
        json_body: Mapping[str, object] | None = None,
        params: Mapping[str, str] | None = None,
    ) -> JsonPayload:
        del headers
        self.calls.append(
            StubCall(
                json_body=dict(json_body) if json_body is not None else None,
                method=method,
                params=dict(params) if params is not None else None,
                path=path,
            )
        )
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


@pytest.mark.asyncio
async def test_identity_service() -> None:
    """Identity service should fetch identity and expose health status."""
    client = StubClient([{"id": 1, "name": "Jean-Luc"}])
    service = IdentityService(client)
    identity = await service.get_identity()
    assert isinstance(identity, IdentityResponse)
    assert identity.id == 1

    client = StubClient([{"id": 2, "name": "Will"}])
    service = IdentityService(client)
    health = await service.health_check()
    assert health.ok is True
    assert health.identity.id == 2


@pytest.mark.asyncio
async def test_custom_fields_service() -> None:
    """Custom field listing should parse metadata and validate response shape."""
    client = StubClient(
        [
            {
                "_metadata": {"limit": 10, "offset": 0, "total": "1"},
                "customfields": [
                    {"id": 1, "label": "Birthday", "name": "customBirthday", "type": "date"}
                ],
            },
            [],
        ]
    )
    service = CustomFieldsService(client)
    page = await service.list_custom_fields(CustomFieldListRequest(label="Birthday"))
    assert page.items[0].name == "customBirthday"
    assert client.calls[0].params == {"label": "Birthday"}
    with pytest.raises(FollowUpBossValidationError):
        await service.list_custom_fields()


@pytest.mark.asyncio
async def test_appointment_outcomes_service() -> None:
    """Appointment outcomes service should map queries, bodies, and delete behavior correctly."""
    client = StubClient(
        [
            {
                "_metadata": {"limit": 10, "offset": 0, "total": 1},
                "appointmentoutcomes": [{"id": 1, "name": "Completed", "orderWeight": 1000}],
            },
            {"id": 2, "name": "Completed", "orderWeight": 1000},
            {"id": 3, "name": "No Show", "orderWeight": 2000},
            {"id": 4, "name": "Rescheduled", "orderWeight": 3000},
            {},
        ]
    )
    service = AppointmentOutcomesService(client)

    outcomes_page = await service.list_appointment_outcomes(
        AppointmentOutcomeListRequest(limit=5, offset=10, sort="-orderWeight")
    )
    assert outcomes_page.items[0].name == "Completed"
    assert client.calls[0].params == {
        "limit": "5",
        "offset": "10",
        "sort": "-orderWeight",
    }

    outcome = await service.get_appointment_outcome(2)
    assert outcome.id == 2

    created = await service.create_appointment_outcome(
        CreateAppointmentOutcomeRequest(name="No Show", order_weight=2000)
    )
    assert created.id == 3
    assert client.calls[2].json_body == {"name": "No Show", "orderWeight": 2000}

    updated = await service.update_appointment_outcome(
        4,
        UpdateAppointmentOutcomeRequest(name="Rescheduled", order_weight=3000),
    )
    assert updated.id == 4
    assert client.calls[3].json_body == {
        "name": "Rescheduled",
        "orderWeight": 3000,
    }

    await service.delete_appointment_outcome(
        5, DeleteAppointmentOutcomeRequest(assign_outcome_id=11)
    )
    assert client.calls[4].path == "/appointmentOutcomes/5"
    assert client.calls[4].params == {"assignOutcomeId": "11"}

    with pytest.raises(
        ValidationError,
        match="At least one appointment metadata field must be provided",
    ):
        UpdateAppointmentOutcomeRequest()


@pytest.mark.asyncio
async def test_appointment_types_service() -> None:
    """Appointment types service should map queries, bodies, and delete behavior correctly."""
    client = StubClient(
        [
            {
                "_metadata": {"limit": 10, "offset": 0, "total": 1},
                "appointmenttypes": [{"id": 1, "name": "Buyer Consult", "orderWeight": 1000}],
            },
            {"id": 2, "name": "Buyer Consult", "orderWeight": 1000},
            {"id": 3, "name": "Listing Consult", "orderWeight": 2000},
            {"id": 4, "name": "Showing", "orderWeight": 3000},
            {},
        ]
    )
    service = AppointmentTypesService(client)

    types_page = await service.list_appointment_types(
        AppointmentTypeListRequest(limit=5, offset=10, sort="-orderWeight")
    )
    assert types_page.items[0].name == "Buyer Consult"
    assert client.calls[0].params == {
        "limit": "5",
        "offset": "10",
        "sort": "-orderWeight",
    }

    appointment_type = await service.get_appointment_type(2)
    assert appointment_type.id == 2

    created = await service.create_appointment_type(
        CreateAppointmentTypeRequest(name="Listing Consult", order_weight=2000)
    )
    assert created.id == 3
    assert client.calls[2].json_body == {
        "name": "Listing Consult",
        "orderWeight": 2000,
    }

    updated = await service.update_appointment_type(
        4,
        UpdateAppointmentTypeRequest(name="Showing", order_weight=3000),
    )
    assert updated.id == 4
    assert client.calls[3].json_body == {
        "name": "Showing",
        "orderWeight": 3000,
    }

    await service.delete_appointment_type(5, DeleteAppointmentTypeRequest(assign_type_id=12))
    assert client.calls[4].path == "/appointmentTypes/5"
    assert client.calls[4].params == {"assignTypeId": "12"}

    with pytest.raises(
        ValidationError,
        match="At least one appointment metadata field must be provided",
    ):
        UpdateAppointmentTypeRequest()


@pytest.mark.asyncio
async def test_people_service_search_create_update_get_and_wait() -> None:
    """People service should shape queries, bodies, and eventual-consistency polling."""
    sleep_calls: list[float] = []

    async def sleep(delay: float) -> None:
        sleep_calls.append(delay)

    client = StubClient(
        [
            {
                "_metadata": {"limit": 10, "offset": 0, "total": 1, "next": "abc"},
                "people": [{"id": 7, "firstName": "Will"}],
            },
            {"id": 8, "firstName": "Tom"},
            {"id": 9, "firstName": "Tom"},
            {"id": 10, "firstName": "Bev"},
        ]
    )
    service = PeopleService(client, sleep=sleep)
    search = await service.search_people(
        PeopleSearchRequest(email="a@example.com", custom_field_filters={"customSource": "Zillow"})
    )
    assert search.items[0].id == 7
    assert client.calls[0].params == {"customSource": "Zillow", "email": "a@example.com"}

    created = await service.create_person(
        CreatePersonRequest(
            deduplicate=True,
            first_name="Tom",
            custom_fields={"customSource": "Portal"},
            emails=[EmailAddress(type="home", value="tom@example.com")],
        )
    )
    assert created.id == 8
    assert client.calls[1].params == {"deduplicate": "true"}
    assert client.calls[1].json_body == {
        "firstName": "Tom",
        "emails": [{"type": "home", "value": "tom@example.com"}],
        "customSource": "Portal",
    }

    updated = await service.update_person(
        9,
        UpdatePersonRequest(merge_tags=True, tags=["VIP"], custom_fields={"customTier": "Gold"}),
    )
    assert updated.id == 9
    assert client.calls[2].params == {"mergeTags": "true"}
    assert client.calls[2].json_body == {"tags": ["VIP"], "customTier": "Gold"}

    looked_up = await service.get_person(
        10, request=PersonLookupRequest(fields=["id", "firstName"])
    )
    assert looked_up.id == 10
    assert client.calls[3].params == {"fields": "id,firstName"}

    client = StubClient([])
    service = PeopleService(client, sleep=sleep)

    calls = {"count": 0}

    async def fake_get_person(
        person_id: int, request: PersonLookupRequest | None = None
    ) -> PersonRecord:
        del person_id, request
        calls["count"] += 1
        if calls["count"] < 2:
            raise FollowUpBossNotFoundError("missing", status_code=404)
        return PersonRecord(id=12)

    service.get_person = fake_get_person  # type: ignore[method-assign]
    person = await service.wait_for_person(12)
    assert person.id == 12
    assert sleep_calls == [1.0]

    with pytest.raises(ValueError):
        await service.wait_for_person(12, attempts=0)

    async def always_missing(
        person_id: int, request: PersonLookupRequest | None = None
    ) -> PersonRecord:
        del person_id, request
        raise FollowUpBossNotFoundError("missing", status_code=404)

    service.get_person = always_missing  # type: ignore[method-assign]
    with pytest.raises(FollowUpBossNotFoundError):
        await service.wait_for_person(12, attempts=1)


@pytest.mark.asyncio
async def test_people_service_optional_query_branches_and_invalid_collection_shape() -> None:
    """People service should omit optional query params and raise on bad list payloads."""
    client = StubClient([{"id": 11, "firstName": "Tom"}, []])
    service = PeopleService(client)
    created = await service.create_person(CreatePersonRequest(first_name="Tom"))
    assert created.id == 11
    assert client.calls[0].params is None
    assert client.calls[0].json_body == {"firstName": "Tom"}

    with pytest.raises(ValueError):
        await service.search_people()


@pytest.mark.asyncio
async def test_people_service_paginator_and_non_list_shape() -> None:
    """People paginator should carry pagination state and reject non-list payloads."""
    client = StubClient(
        [
            {
                "_metadata": {"limit": 1, "offset": 0, "total": 2, "next": "next-1"},
                "people": [{"id": 1}],
            },
            {
                "_metadata": {"limit": 1, "offset": 1, "total": 2},
                "people": [{"id": 2}],
            },
        ]
    )
    service = PeopleService(client)
    paginator = service.paginator(PeopleSearchRequest(limit=1, email="a@example.com"))
    items = [item async for item in paginator.items()]
    assert [item.id for item in items] == [1, 2]
    assert client.calls[0].params == {"email": "a@example.com", "limit": "1", "offset": "0"}
    assert client.calls[1].params == {
        "email": "a@example.com",
        "limit": "1",
        "next": "next-1",
        "offset": "0",
    }

    with pytest.raises(ValueError):
        await PeopleService(StubClient([{"people": {}}])).search_people()


@pytest.mark.asyncio
async def test_calls_service() -> None:
    """Calls service should map queries and bodies correctly."""
    client = StubClient(
        [
            {
                "_metadata": {"limit": 10, "offset": 0, "total": 1},
                "calls": [
                    {
                        "id": 1,
                        "personId": 99,
                        "phone": "555-0000",
                        "userId": 5,
                        "userName": "Data",
                        "isIncoming": True,
                    }
                ],
            },
            {
                "id": 2,
                "personId": 99,
                "phone": "555-0000",
                "userId": 5,
                "userName": "Data",
                "isIncoming": True,
            },
            {
                "id": 3,
                "personId": 99,
                "phone": "555-0000",
                "userId": 5,
                "userName": "Data",
                "isIncoming": True,
            },
            {
                "id": 4,
                "personId": 99,
                "phone": "555-0000",
                "userId": 5,
                "userName": "Data",
                "isIncoming": False,
            },
        ]
    )
    service = CallsService(client)

    calls_page = await service.list_calls(
        CallListRequest(
            person_id=99,
            phone="555-0000",
            to_number="555-1111",
            from_number="555-2222",
            limit=10,
            offset=5,
        )
    )
    assert calls_page.items[0].user_name == "Data"
    assert client.calls[0].params == {
        "personId": "99",
        "phone": "555-0000",
        "toNumber": "555-1111",
        "fromNumber": "555-2222",
        "limit": "10",
        "offset": "5",
    }

    call = await service.get_call(2)
    assert call.id == 2

    created = await service.create_call(
        CreateCallRequest(
            person_id=99,
            phone="555-0000",
            is_incoming=True,
            note="Incoming lead",
            outcome="Interested",
        )
    )
    assert created.id == 3
    assert client.calls[2].json_body == {
        "personId": 99,
        "phone": "555-0000",
        "isIncoming": True,
        "note": "Incoming lead",
        "outcome": "Interested",
    }

    updated = await service.update_call(
        4,
        UpdateCallRequest(
            note="Updated note",
            outcome="Left Message",
            is_incoming=False,
        ),
    )
    assert updated.id == 4
    assert client.calls[3].json_body == {
        "note": "Updated note",
        "outcome": "Left Message",
        "isIncoming": False,
    }


@pytest.mark.asyncio
async def test_appointments_service() -> None:
    """Appointments service should map queries, bodies, and delete behavior correctly."""
    start_time = datetime(2026, 3, 28, 10, 0, tzinfo=UTC)
    created_end_time = datetime(2026, 3, 28, 11, 0, tzinfo=UTC)
    end_time = datetime(2026, 3, 28, 12, 0, tzinfo=UTC)
    next_start_time = datetime(2026, 3, 29, 10, 0, tzinfo=UTC)
    next_end_time = datetime(2026, 3, 29, 11, 0, tzinfo=UTC)
    client = StubClient(
        [
            {
                "_metadata": {"limit": 10, "offset": 0, "total": 1},
                "appointments": [
                    {
                        "id": 1,
                        "title": "Buyer consult",
                        "start": "2026-03-28T10:00:00Z",
                        "end": "2026-03-28T11:00:00Z",
                        "allDay": False,
                    }
                ],
            },
            {
                "id": 2,
                "title": "Buyer consult",
                "start": "2026-03-28T10:00:00Z",
                "end": "2026-03-28T11:00:00Z",
                "allDay": False,
            },
            {
                "id": 3,
                "title": "Listing appointment",
                "start": "2026-03-28T10:00:00Z",
                "end": "2026-03-28T11:00:00Z",
                "allDay": False,
            },
            {
                "id": 4,
                "title": "Updated appointment",
                "start": "2026-03-29T10:00:00Z",
                "end": "2026-03-29T11:00:00Z",
                "allDay": False,
            },
            {},
        ]
    )
    service = AppointmentsService(client)

    appointments_page = await service.list_appointments(
        AppointmentListRequest(
            person_id=[99, 100],
            user_id=5,
            limit=10,
            offset=5,
            start=start_time,
            end=end_time,
        )
    )
    assert appointments_page.items[0].title == "Buyer consult"
    assert client.calls[0].params == {
        "personId": "99,100",
        "userId": "5",
        "limit": "10",
        "offset": "5",
        "start": "2026-03-28T10:00:00+00:00",
        "end": "2026-03-28T12:00:00+00:00",
    }

    appointment = await service.get_appointment(2)
    assert appointment.id == 2

    created = await service.create_appointment(
        CreateAppointmentRequest(
            title="Listing appointment",
            start=start_time,
            end=created_end_time,
            send_invitation=True,
            invitees=[AppointmentInviteeInput(person_id=99, name="Data")],
        )
    )
    assert created.id == 3
    assert client.calls[2].params == {"sendInvitation": "true"}
    assert client.calls[2].json_body == {
        "title": "Listing appointment",
        "start": "2026-03-28T10:00:00Z",
        "end": "2026-03-28T11:00:00Z",
        "invitees": [{"personId": 99, "name": "Data"}],
    }

    updated = await service.update_appointment(
        4,
        UpdateAppointmentRequest(
            title="Updated appointment",
            start=next_start_time,
            end=next_end_time,
            send_invitation=False,
            location="Office",
        ),
    )
    assert updated.id == 4
    assert client.calls[3].params == {"sendInvitation": "false"}
    assert client.calls[3].json_body == {
        "title": "Updated appointment",
        "start": "2026-03-29T10:00:00Z",
        "end": "2026-03-29T11:00:00Z",
        "location": "Office",
    }

    await service.delete_appointment(5)
    assert client.calls[4].path == "/appointments/5"

    with pytest.raises(ValidationError, match="start and end must be provided together"):
        AppointmentListRequest(start=start_time)


@pytest.mark.asyncio
async def test_deals_service() -> None:
    """Deals service should map queries, bodies, and delete behavior correctly."""
    client = StubClient(
        [
            {
                "_metadata": {"limit": 10, "offset": 0, "total": 1},
                "deals": [
                    {
                        "id": 1,
                        "name": "Buyer contract",
                        "pipelineId": 3,
                        "stageId": 7,
                        "people": [{"id": 99, "name": "Data"}],
                        "users": [{"id": 5, "name": "Picard"}],
                    }
                ],
            },
            {
                "id": 2,
                "name": "Buyer contract",
                "pipelineId": 3,
                "stageId": 7,
            },
            {
                "id": 3,
                "name": "New deal",
                "pipelineId": 3,
                "stageId": 7,
            },
            {
                "id": 4,
                "name": "Updated deal",
                "pipelineId": 3,
                "stageId": 8,
            },
            {},
            {
                "_metadata": {"limit": 10, "offset": 0, "total": 1},
                "dealCustomfields": [
                    {
                        "id": 6,
                        "label": "Close Price",
                        "name": "customClosePrice",
                        "type": "number",
                    }
                ],
            },
        ]
    )
    service = DealsService(client)

    deals_page = await service.list_deals(
        DealListRequest(
            pipeline_id=3,
            user_id=5,
            person_id=99,
            include_deleted=True,
            include_archived=False,
            status="Active",
        )
    )
    assert deals_page.items[0].name == "Buyer contract"
    assert client.calls[0].params == {
        "pipelineId": "3",
        "userId": "5",
        "personId": "99",
        "includeDeleted": "1",
        "includeArchived": "0",
        "status": "Active",
    }

    assert (await service.get_deal(2)).id == 2

    created = await service.create_deal(
        CreateDealRequest(
            name="New deal",
            stage_id=7,
            people_ids=[99],
            user_ids=[5],
            custom_fields={"customClosePrice": 450000},
        )
    )
    assert created.id == 3
    assert client.calls[2].json_body == {
        "name": "New deal",
        "stageId": 7,
        "peopleIds": [99],
        "userIds": [5],
        "customClosePrice": 450000,
    }

    updated = await service.update_deal(
        4,
        UpdateDealRequest(
            stage_id=8,
            user_ids=[5],
            custom_fields={"customClosePrice": 470000},
        ),
    )
    assert updated.id == 4
    assert client.calls[3].json_body == {
        "stageId": 8,
        "userIds": [5],
        "customClosePrice": 470000,
    }

    await service.delete_deal(5)
    assert client.calls[4].path == "/deals/5"

    custom_fields_page = await service.list_deal_custom_fields(
        DealCustomFieldListRequest(label="Close Price", limit=10, offset=0, sort="-id")
    )
    assert custom_fields_page.items[0].name == "customClosePrice"
    assert client.calls[5].params == {
        "label": "Close Price",
        "limit": "10",
        "offset": "0",
        "sort": "-id",
    }

    with pytest.raises(FollowUpBossValidationError, match="Deal custom field keys"):
        DealsService.validate_deal_custom_field_names({"ClosePrice": 1})

    invalid_service = DealsService(StubClient([[], {"dealCustomfields": {}}]))
    with pytest.raises(FollowUpBossValidationError, match="Unexpected deal custom fields"):
        await invalid_service.list_deal_custom_fields()
    with pytest.raises(FollowUpBossValidationError, match="Unexpected deal custom fields"):
        await invalid_service.list_deal_custom_fields()


@pytest.mark.asyncio
async def test_pipelines_service() -> None:
    """Pipelines service should map queries, bodies, and delete behavior correctly."""
    client = StubClient(
        [
            {
                "_metadata": {"limit": 10, "offset": 0, "total": 1},
                "pipelines": [
                    {
                        "id": 1,
                        "name": "Buyer pipeline",
                        "description": "Buyer flow",
                        "orderWeight": 1000,
                        "stages": [
                            {
                                "id": 10,
                                "name": "New lead",
                                "description": "Just created",
                                "orderWeight": 1000,
                                "color": "#00FF00",
                                "closedStage": False,
                            }
                        ],
                    }
                ],
            },
            {
                "id": 2,
                "name": "Buyer pipeline",
                "description": "Buyer flow",
                "orderWeight": 1000,
                "stages": [
                    {
                        "id": 10,
                        "name": "New lead",
                        "description": "Just created",
                        "orderWeight": 1000,
                        "color": "#00FF00",
                        "closedStage": False,
                    }
                ],
            },
            {
                "id": 3,
                "name": "New pipeline",
                "description": "New flow",
                "orderWeight": 2000,
                "stages": [{"id": 11, "name": "Warm", "closedStage": False}],
            },
            {
                "id": 4,
                "name": "Updated pipeline",
                "description": "Updated flow",
                "orderWeight": 3000,
                "stages": [{"id": 12, "name": "Closed won", "closedStage": True}],
            },
            {},
        ]
    )
    service = PipelinesService(client)

    pipelines_page = await service.list_pipelines(PipelineListRequest(name="Buyer pipeline"))
    assert pipelines_page.items[0].name == "Buyer pipeline"
    assert client.calls[0].params == {"name": "Buyer pipeline"}

    pipeline = await service.get_pipeline(2)
    assert pipeline.id == 2
    assert pipeline.stages[0].closed_stage is False

    created = await service.create_pipeline(
        CreatePipelineRequest(
            name="New pipeline",
            description="New flow",
            order_weight=2000,
            stages=[
                PipelineStageInput(
                    name="Warm",
                    description="Qualified",
                    order_weight=2000,
                    color="#00FF00",
                    closed_stage=False,
                )
            ],
        )
    )
    assert created.id == 3
    assert client.calls[2].json_body == {
        "name": "New pipeline",
        "description": "New flow",
        "orderWeight": 2000,
        "stages": [
            {
                "name": "Warm",
                "description": "Qualified",
                "orderWeight": 2000,
                "color": "#00FF00",
                "closedStage": False,
            }
        ],
    }

    updated = await service.update_pipeline(
        4,
        UpdatePipelineRequest(
            name="Updated pipeline",
            description="Updated flow",
            order_weight=3000,
            stages=[
                PipelineStageInput(
                    id=12,
                    name="Closed won",
                    description="Finished",
                    order_weight=4000,
                    color="#0000FF",
                    closed_stage=True,
                )
            ],
        ),
    )
    assert updated.id == 4
    assert client.calls[3].json_body == {
        "name": "Updated pipeline",
        "description": "Updated flow",
        "orderWeight": 3000,
        "stages": [
            {
                "id": 12,
                "name": "Closed won",
                "description": "Finished",
                "orderWeight": 4000,
                "color": "#0000FF",
                "closedStage": True,
            }
        ],
    }

    await service.delete_pipeline(5)
    assert client.calls[4].path == "/pipelines/5"

    with pytest.raises(ValidationError, match="At least one pipeline field must be provided"):
        UpdatePipelineRequest()


@pytest.mark.asyncio
async def test_ponds_service() -> None:
    """Ponds service should map queries, bodies, and delete behavior correctly."""
    client = StubClient(
        [
            {
                "_metadata": {"limit": 10, "offset": 0, "total": 1},
                "ponds": [
                    {
                        "id": 1,
                        "name": "Round Robin",
                        "userId": 5,
                        "userIds": [5, 6],
                    }
                ],
            },
            {
                "id": 2,
                "name": "Round Robin",
                "userId": 5,
                "userIds": [5, 6],
            },
            {
                "id": 3,
                "name": "Sphere Builders",
                "userId": 7,
                "userIds": [7, 8],
            },
            {
                "id": 4,
                "name": "Updated Pond",
                "userId": 9,
                "userIds": [9, 10],
            },
            {},
        ]
    )
    service = PondsService(client)

    ponds_page = await service.list_ponds(PondListRequest(limit=5, offset=10))
    assert ponds_page.items[0].name == "Round Robin"
    assert client.calls[0].params == {"limit": "5", "offset": "10"}

    pond = await service.get_pond(2)
    assert pond.id == 2
    assert pond.user_ids == [5, 6]

    created = await service.create_pond(
        CreatePondRequest(name="Sphere Builders", user_id=7, user_ids=[7, 8])
    )
    assert created.id == 3
    assert client.calls[2].json_body == {
        "name": "Sphere Builders",
        "userId": 7,
        "userIds": [7, 8],
    }

    updated = await service.update_pond(
        4,
        UpdatePondRequest(
            name="Updated Pond",
            user_id=9,
            user_ids=[9, 10],
        ),
    )
    assert updated.id == 4
    assert client.calls[3].json_body == {
        "name": "Updated Pond",
        "userId": 9,
        "userIds": [9, 10],
    }

    await service.delete_pond(5, DeletePondRequest(assign_to=11))
    assert client.calls[4].path == "/ponds/5"
    assert client.calls[4].params == {"assignTo": "11"}

    with pytest.raises(ValidationError, match="At least one pond field must be provided"):
        UpdatePondRequest()


@pytest.mark.asyncio
async def test_smart_lists_service() -> None:
    """Smart lists service should map queries and lookup behavior correctly."""
    client = StubClient(
        [
            {
                "_metadata": {"limit": 10, "offset": 0, "total": 1},
                "smartlists": [
                    {
                        "id": 1,
                        "name": "Active Buyers",
                        "description": "All active buyers",
                        "isFub2": True,
                        "defaultSmartListId": 7,
                    }
                ],
            },
            {
                "id": 2,
                "name": "Active Buyers",
                "description": "All active buyers",
                "isFub2": True,
                "defaultSmartListId": 7,
            },
        ]
    )
    service = SmartListsService(client)

    smart_lists_page = await service.list_smart_lists(
        SmartListListRequest(limit=5, offset=10, fub2=True, include_all=False)
    )
    assert smart_lists_page.items[0].name == "Active Buyers"
    assert client.calls[0].params == {
        "limit": "5",
        "offset": "10",
        "fub2": "true",
        "all": "false",
    }

    smart_list = await service.get_smart_list(2)
    assert smart_list.id == 2
    assert smart_list.is_fub2 is True


@pytest.mark.asyncio
async def test_stages_service() -> None:
    """Stages service should map queries, bodies, and delete behavior correctly."""
    client = StubClient(
        [
            {
                "_metadata": {"limit": 10, "offset": 0, "total": 1},
                "stages": [
                    {
                        "id": 1,
                        "name": "Prospect",
                        "orderWeight": 1000,
                        "isProtected": False,
                        "peopleCount": 12,
                    }
                ],
            },
            {
                "id": 2,
                "name": "Prospect",
                "orderWeight": 1000,
                "isProtected": False,
                "peopleCount": 12,
            },
            {
                "id": 3,
                "name": "Qualified",
                "orderWeight": 2000,
                "isProtected": False,
                "peopleCount": 8,
            },
            {
                "id": 4,
                "name": "Updated Stage",
                "orderWeight": 3000,
                "isProtected": False,
                "peopleCount": 5,
            },
            {},
        ]
    )
    service = StagesService(client)

    stages_page = await service.list_stages(StageListRequest(limit=5, offset=10, sort="-id"))
    assert stages_page.items[0].name == "Prospect"
    assert client.calls[0].params == {"limit": "5", "offset": "10", "sort": "-id"}

    stage = await service.get_stage(2)
    assert stage.id == 2
    assert stage.people_count == 12

    created = await service.create_stage(CreateStageRequest(name="Qualified", order_weight=2000))
    assert created.id == 3
    assert client.calls[2].json_body == {"name": "Qualified", "orderWeight": 2000}

    updated = await service.update_stage(
        4,
        UpdateStageRequest(name="Updated Stage", order_weight=3000),
    )
    assert updated.id == 4
    assert client.calls[3].json_body == {
        "name": "Updated Stage",
        "orderWeight": 3000,
    }

    await service.delete_stage(5, DeleteStageRequest(assign_stage_id=11))
    assert client.calls[4].path == "/stages/5"
    assert client.calls[4].params == {"assignStageId": "11"}

    with pytest.raises(ValidationError, match="At least one stage field must be provided"):
        UpdateStageRequest()


@pytest.mark.asyncio
async def test_teams_service() -> None:
    """Teams service should map queries, bodies, and delete behavior correctly."""
    client = StubClient(
        [
            {
                "_metadata": {"limit": 10, "offset": 0, "total": 1},
                "teams": [
                    {
                        "id": 1,
                        "name": "Listing Team",
                        "userIds": [5, 6],
                        "leaderIds": [5],
                    }
                ],
            },
            {
                "id": 2,
                "name": "Listing Team",
                "userIds": [5, 6],
                "leaderIds": [5],
            },
            {
                "id": 3,
                "name": "Buyer Team",
                "userIds": [7, 8],
                "leaderIds": [7],
            },
            {
                "id": 4,
                "name": "Updated Team",
                "userIds": [9, 10],
                "leaderIds": [9],
            },
            {},
        ]
    )
    service = TeamsService(client)

    teams_page = await service.list_teams(TeamListRequest(limit=5, offset=10))
    assert teams_page.items[0].name == "Listing Team"
    assert client.calls[0].params == {"limit": "5", "offset": "10"}

    team = await service.get_team(2)
    assert team.id == 2
    assert team.user_ids == [5, 6]

    created = await service.create_team(
        CreateTeamRequest(name="Buyer Team", user_ids=[7, 8], leader_ids=[7])
    )
    assert created.id == 3
    assert client.calls[2].json_body == {
        "name": "Buyer Team",
        "userIds": [7, 8],
        "leaderIds": [7],
    }

    updated = await service.update_team(
        4,
        UpdateTeamRequest(name="Updated Team", user_ids=[9, 10], leader_ids=[9]),
    )
    assert updated.id == 4
    assert client.calls[3].json_body == {
        "name": "Updated Team",
        "userIds": [9, 10],
        "leaderIds": [9],
    }

    await service.delete_team(5, DeleteTeamRequest(move_to_team_id=11))
    assert client.calls[4].path == "/teams/5"
    assert client.calls[4].params == {"moveToTeamId": "11"}

    with pytest.raises(ValidationError, match="At least one team field must be provided"):
        UpdateTeamRequest()


@pytest.mark.asyncio
async def test_text_messages_service() -> None:
    """Text messages service should map list and lookup behavior correctly."""
    client = StubClient(
        [
            {
                "_metadata": {"limit": 10, "offset": 0, "total": 1},
                "textmessages": [
                    {
                        "id": 1,
                        "personId": 99,
                        "message": "Hi there",
                        "fromNumber": "555-0001",
                        "toNumber": "555-0002",
                        "userName": "Data",
                    }
                ],
            },
            {
                "id": 2,
                "personId": 99,
                "message": "Hello again",
                "fromNumber": "555-0001",
                "toNumber": "555-0002",
                "userName": "Data",
            },
        ]
    )
    service = TextMessagesService(client)

    messages_page = await service.list_text_messages(
        TextMessageListRequest(
            person_id=99,
            to_number="555-0002",
            from_number="555-0001",
        )
    )
    assert messages_page.items[0].user_name == "Data"
    assert client.calls[0].params == {
        "personId": "99",
        "toNumber": "555-0002",
        "fromNumber": "555-0001",
    }

    assert (await service.get_text_message(2)).id == 2


@pytest.mark.asyncio
async def test_text_message_templates_service() -> None:
    """Text message templates service should map queries, bodies, and delete behavior correctly."""
    client = StubClient(
        [
            {
                "_metadata": {"limit": 10, "offset": 0, "total": 1},
                "textmessagetemplates": [
                    {
                        "id": 1,
                        "name": "Buyer intro text",
                        "message": "Hi there",
                        "isShared": True,
                    }
                ],
            },
            {
                "id": 2,
                "name": "Buyer intro text",
                "message": "Hi there",
                "isShared": True,
            },
            {
                "id": 3,
                "name": "New text template",
                "message": "Hello there",
                "isShared": True,
            },
            {
                "id": 4,
                "name": "Updated text template",
                "message": "Updated text",
                "isShared": False,
            },
            {},
        ]
    )
    service = TextMessageTemplatesService(client)

    templates_page = await service.list_text_message_templates(
        TextMessageTemplateListRequest(limit=5, offset=10)
    )
    assert templates_page.items[0].name == "Buyer intro text"
    assert client.calls[0].params == {"limit": "5", "offset": "10"}

    template = await service.get_text_message_template(2)
    assert template.id == 2

    created = await service.create_text_message_template(
        CreateTextMessageTemplateRequest(
            name="New text template",
            message="Hello there",
            is_shared=True,
        )
    )
    assert created.id == 3
    assert client.calls[2].json_body == {
        "name": "New text template",
        "message": "Hello there",
        "isShared": True,
    }

    updated = await service.update_text_message_template(
        4,
        UpdateTextMessageTemplateRequest(
            name="Updated text template",
            message="Updated text",
            is_shared=False,
        ),
    )
    assert updated.id == 4
    assert client.calls[3].json_body == {
        "name": "Updated text template",
        "message": "Updated text",
        "isShared": False,
    }

    await service.delete_text_message_template(5)
    assert client.calls[4].path == "/textMessageTemplates/5"


@pytest.mark.asyncio
async def test_tasks_service() -> None:
    """Tasks service should map queries, bodies, and delete behavior correctly."""
    client = StubClient(
        [
            {
                "_metadata": {"limit": 10, "offset": 0, "total": 1},
                "tasks": [
                    {
                        "id": 1,
                        "personId": 99,
                        "AssignedTo": "Data",
                        "assignedUserId": 5,
                        "name": "Call lead",
                        "type": "Call",
                        "isCompleted": False,
                    }
                ],
            },
            {
                "id": 2,
                "personId": 99,
                "assignedTo": "Data",
                "name": "Follow up",
                "type": "Follow Up",
                "isCompleted": False,
            },
            {
                "id": 3,
                "personId": 99,
                "assignedTo": "Data",
                "name": "Email lead",
                "type": "Email",
                "isCompleted": False,
            },
            {
                "id": 4,
                "personId": 99,
                "assignedTo": "Data",
                "name": "Updated task",
                "type": "Text",
                "isCompleted": True,
            },
            {},
        ]
    )
    service = TasksService(client)

    tasks_page = await service.list_tasks(
        TaskListRequest(
            person_id=99,
            assigned_user_id=5,
            is_completed=False,
            due="today",
            type=["Call", "Email"],
        )
    )
    assert tasks_page.items[0].assigned_to == "Data"
    assert client.calls[0].params == {
        "assignedUserId": "5",
        "due": "today",
        "isCompleted": "false",
        "personId": "99",
        "type": "Call,Email",
    }

    assert (await service.get_task(2)).id == 2
    created = await service.create_task(
        CreateTaskRequest(
            person_id=99,
            assigned_to="Data",
            name="Email lead",
            type="Email",
            due_date=date(2026, 3, 28),
        )
    )
    assert created.id == 3
    assert client.calls[2].json_body == {
        "personId": 99,
        "assignedTo": "Data",
        "name": "Email lead",
        "type": "Email",
        "dueDate": "2026-03-28",
    }

    updated = await service.update_task(
        4,
        UpdateTaskRequest(
            assigned_user_id=7,
            is_completed=True,
            type="Text",
        ),
    )
    assert updated.id == 4
    assert client.calls[3].json_body == {
        "assignedUserId": 7,
        "isCompleted": True,
        "type": "Text",
    }

    await service.delete_task(5)
    assert client.calls[4].path == "/tasks/5"

    with pytest.raises(ValidationError, match="Either assigned_to or assigned_user_id"):
        CreateTaskRequest(person_id=1)


@pytest.mark.asyncio
async def test_templates_service() -> None:
    """Templates service should map queries, bodies, and delete behavior correctly."""
    client = StubClient(
        [
            {
                "_metadata": {"limit": 10, "offset": 0, "total": 1},
                "templates": [
                    {
                        "id": 1,
                        "name": "Buyer intro",
                        "subject": "Hello",
                        "body": "<p>Hello</p>",
                        "isShared": True,
                    }
                ],
            },
            {
                "id": 2,
                "name": "Merged template",
                "subject": "Hello Tom",
                "body": "<p>Hello Tom</p>",
                "isShared": True,
            },
            {
                "id": 3,
                "name": "New template",
                "subject": "Hello",
                "body": "<p>Hello</p>",
                "isShared": True,
            },
            {
                "id": 4,
                "name": "Updated template",
                "subject": "Updated",
                "body": "<p>Updated</p>",
                "isShared": True,
            },
            {},
        ]
    )
    service = TemplatesService(client)

    templates_page = await service.list_templates(TemplateListRequest(limit=5, offset=10))
    assert templates_page.items[0].name == "Buyer intro"
    assert client.calls[0].params == {"limit": "5", "offset": "10"}

    template = await service.get_template(2, request=TemplateLookupRequest(merge_person_id=99))
    assert template.id == 2
    assert client.calls[1].params == {"mergePersonId": "99"}

    created = await service.create_template(
        CreateTemplateRequest(
            name="New template",
            subject="Hello",
            body="<p>Hello</p>",
            is_shared=True,
        )
    )
    assert created.id == 3
    assert client.calls[2].json_body == {
        "name": "New template",
        "subject": "Hello",
        "body": "<p>Hello</p>",
        "isShared": True,
    }

    updated = await service.update_template(
        4,
        UpdateTemplateRequest(
            name="Updated template",
            subject="Updated",
            body="<p>Updated</p>",
        ),
    )
    assert updated.id == 4
    assert client.calls[3].json_body == {
        "name": "Updated template",
        "subject": "Updated",
        "body": "<p>Updated</p>",
    }

    await service.delete_template(5)
    assert client.calls[4].path == "/templates/5"


@pytest.mark.asyncio
async def test_events_users_notes_and_webhooks_services() -> None:
    """Remaining services should map payloads and request shapes correctly."""
    client = StubClient(
        [
            {
                "_metadata": {"limit": 10, "offset": 0, "total": 1},
                "events": [{"id": 1, "personId": 99, "type": "Inquiry"}],
            },
            {"id": 2, "personId": 99, "type": "Inquiry"},
            {"id": 3, "personId": 99, "type": "Inquiry"},
            {
                "_metadata": {"limit": 10, "offset": 0, "total": 1},
                "users": [{"id": 5, "name": "Data"}],
            },
            {"id": 6, "name": "Geordi"},
            {"id": 7, "body": "created"},
            {"id": 8, "body": "loaded"},
            {"id": 9, "body": "updated"},
            {},
            {
                "_metadata": {"limit": 10, "offset": 0, "total": 1},
                "webhooks": [{"id": 10, "event": "peopleCreated", "url": "https://example.com"}],
            },
            {"id": 11, "event": "peopleCreated", "url": "https://example.com"},
            {"id": 12, "event": "peopleCreated", "url": "https://example.com"},
            {},
        ]
    )
    people_service = PeopleService(client)
    events_service = EventsService(client)
    users_service = UsersService(client)
    notes_service = NotesService(client, people_service=people_service)
    webhooks_service = WebhooksService(client)

    events_page = await events_service.search_events(
        EventSearchRequest(type=["Inquiry"], person_id=99)
    )
    assert events_page.items[0].person_id == 99
    assert client.calls[0].params == {"personId": "99", "type": "Inquiry"}

    sent = await events_service.send_event(
        CreateEventRequest(
            source="Portal",
            system="Portal",
            type="Inquiry",
            person=EventPersonInput(first_name="Bev", custom_fields={"customLeadType": "Buyer"}),
        )
    )
    assert sent.id == 2
    assert client.calls[1].json_body == {
        "source": "Portal",
        "system": "Portal",
        "type": "Inquiry",
        "person": {"firstName": "Bev", "customLeadType": "Buyer"},
    }
    assert (await events_service.get_event(3)).id == 3

    users_page = await users_service.list_users(UserListRequest(role="Agent"))
    assert users_page.items[0].id == 5
    assert client.calls[3].params == {"role": "Agent"}
    assert (await users_service.get_user(6)).id == 6

    wait_calls = {"count": 0}

    async def wait_for_person(
        person_id: int,
        *,
        attempts: int = 5,
        delay_seconds: float = 1.0,
        request: PersonLookupRequest | None = None,
    ) -> PersonRecord:
        del person_id, attempts, delay_seconds, request
        wait_calls["count"] += 1
        return PersonRecord(id=1)

    people_service.wait_for_person = wait_for_person  # type: ignore[method-assign]
    created_note = await notes_service.add_note(
        CreateNoteRequest(person_id=1, body="created"),
        wait_for_person=True,
    )
    assert created_note.id == 7
    assert wait_calls["count"] == 1
    assert client.calls[5].json_body == {"body": "created", "personId": 1}

    assert (await notes_service.get_note(8)).id == 8
    assert (await notes_service.update_note(9, UpdateNoteRequest(body="updated"))).id == 9
    await notes_service.delete_note(10)

    webhooks_page = await webhooks_service.list_webhooks(WebhookListRequest(event="peopleCreated"))
    assert webhooks_page.items[0].id == 10
    assert client.calls[9].params == {"event": "peopleCreated"}
    assert (
        await webhooks_service.create_webhook(
            CreateWebhookRequest(event="peopleCreated", url="https://example.com")
        )
    ).id == 11
    assert (await webhooks_service.get_webhook(12)).id == 12
    await webhooks_service.delete_webhook(13)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("service_factory", "payload", "exception_type"),
    [
        (
            lambda client: CustomFieldsService(client),
            {"customfields": {}},
            FollowUpBossValidationError,
        ),
        (lambda client: AppointmentOutcomesService(client), [], ValueError),
        (
            lambda client: AppointmentOutcomesService(client),
            {"appointmentoutcomes": {}},
            ValueError,
        ),
        (lambda client: AppointmentTypesService(client), [], ValueError),
        (
            lambda client: AppointmentTypesService(client),
            {"appointmenttypes": {}},
            ValueError,
        ),
        (lambda client: DealsService(client), [], ValueError),
        (lambda client: DealsService(client), {"deals": {}}, ValueError),
        (lambda client: PondsService(client), [], ValueError),
        (lambda client: PondsService(client), {"ponds": {}}, ValueError),
        (lambda client: PipelinesService(client), [], ValueError),
        (lambda client: PipelinesService(client), {"pipelines": {}}, ValueError),
        (lambda client: SmartListsService(client), [], ValueError),
        (lambda client: SmartListsService(client), {"smartlists": {}}, ValueError),
        (lambda client: StagesService(client), [], ValueError),
        (lambda client: StagesService(client), {"stages": {}}, ValueError),
        (lambda client: AppointmentsService(client), [], ValueError),
        (lambda client: AppointmentsService(client), {"appointments": {}}, ValueError),
        (lambda client: CallsService(client), [], ValueError),
        (lambda client: CallsService(client), {"calls": {}}, ValueError),
        (lambda client: TeamsService(client), [], ValueError),
        (lambda client: TeamsService(client), {"teams": {}}, ValueError),
        (lambda client: EventsService(client), [], ValueError),
        (lambda client: EventsService(client), {"events": {}}, ValueError),
        (lambda client: TasksService(client), [], ValueError),
        (lambda client: TasksService(client), {"tasks": {}}, ValueError),
        (lambda client: TextMessagesService(client), [], ValueError),
        (lambda client: TextMessagesService(client), {"textmessages": {}}, ValueError),
        (lambda client: TextMessageTemplatesService(client), [], ValueError),
        (
            lambda client: TextMessageTemplatesService(client),
            {"textmessagetemplates": {}},
            ValueError,
        ),
        (lambda client: TemplatesService(client), [], ValueError),
        (lambda client: TemplatesService(client), {"templates": {}}, ValueError),
        (lambda client: UsersService(client), [], ValueError),
        (lambda client: UsersService(client), {"users": {}}, ValueError),
        (lambda client: WebhooksService(client), [], ValueError),
        (lambda client: WebhooksService(client), {"webhooks": {}}, ValueError),
    ],
)
async def test_collection_services_raise_for_non_dict_payload(
    service_factory: Callable[[StubClient], Any],
    payload: JsonPayload,
    exception_type: type[Exception],
) -> None:
    """Collection services should reject unexpected collection payloads."""
    client = StubClient([payload])
    service = service_factory(client)
    if isinstance(service, CustomFieldsService):
        with pytest.raises(exception_type):
            await service.list_custom_fields()
    elif isinstance(service, AppointmentOutcomesService):
        with pytest.raises(exception_type):
            await service.list_appointment_outcomes()
    elif isinstance(service, AppointmentTypesService):
        with pytest.raises(exception_type):
            await service.list_appointment_types()
    elif isinstance(service, DealsService):
        with pytest.raises(exception_type):
            await service.list_deals()
    elif isinstance(service, PondsService):
        with pytest.raises(exception_type):
            await service.list_ponds()
    elif isinstance(service, PipelinesService):
        with pytest.raises(exception_type):
            await service.list_pipelines()
    elif isinstance(service, SmartListsService):
        with pytest.raises(exception_type):
            await service.list_smart_lists()
    elif isinstance(service, StagesService):
        with pytest.raises(exception_type):
            await service.list_stages()
    elif isinstance(service, AppointmentsService):
        with pytest.raises(exception_type):
            await service.list_appointments()
    elif isinstance(service, CallsService):
        with pytest.raises(exception_type):
            await service.list_calls()
    elif isinstance(service, TeamsService):
        with pytest.raises(exception_type):
            await service.list_teams()
    elif isinstance(service, EventsService):
        with pytest.raises(exception_type):
            await service.search_events()
    elif isinstance(service, TasksService):
        with pytest.raises(exception_type):
            await service.list_tasks()
    elif isinstance(service, TextMessagesService):
        with pytest.raises(exception_type):
            await service.list_text_messages()
    elif isinstance(service, TextMessageTemplatesService):
        with pytest.raises(exception_type):
            await service.list_text_message_templates()
    elif isinstance(service, TemplatesService):
        with pytest.raises(exception_type):
            await service.list_templates()
    elif isinstance(service, UsersService):
        with pytest.raises(exception_type):
            await service.list_users()
    else:
        with pytest.raises(exception_type):
            await service.list_webhooks()
