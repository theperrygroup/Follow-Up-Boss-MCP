"""Tests for the typed service layer."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any, cast

import pytest
from pydantic import ValidationError

from followupboss_mcp.errors import (
    FollowUpBossHTTPError,
    FollowUpBossNotFoundError,
    FollowUpBossValidationError,
)
from followupboss_mcp.http_client import JsonPayload
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
    AppointmentInviteeInput,
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
from followupboss_mcp.models.calls import CallListRequest, CreateCallRequest, UpdateCallRequest
from followupboss_mcp.models.common import EmailAddress, PhoneNumber
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
from followupboss_mcp.models.events import CreateEventRequest, EventPersonInput, EventSearchRequest
from followupboss_mcp.models.groups import (
    CreateGroupRequest,
    GroupListRequest,
    UpdateGroupRequest,
)
from followupboss_mcp.models.identity import IdentityResponse
from followupboss_mcp.models.inbox_apps import (
    CreateInboxAppMessageRequest,
    CreateInboxAppNoteRequest,
    CreateInboxAppParticipantRequest,
    InboxAppAttachmentRequest,
    InboxAppConversationOwnerRequest,
    InboxAppConversationPersonRequest,
    InboxAppMessageSenderRequest,
    InboxAppNoteUserRequest,
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
    PipelineStageInput,
    UpdatePipelineRequest,
)
from followupboss_mcp.models.ponds import (
    CreatePondRequest,
    DeletePondRequest,
    PondListRequest,
    UpdatePondRequest,
)
from followupboss_mcp.models.reactions import CreateReactionRequest, DeleteReactionRequest
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
from followupboss_mcp.models.threaded_replies import ThreadedReplyRecord
from followupboss_mcp.models.timeframes import TimeframeListRequest
from followupboss_mcp.models.users import (
    CurrentUserRecord,
    DeleteUserRequest,
    IntercomSettingsRecord,
    UserListRequest,
)
from followupboss_mcp.models.webhooks import (
    CreateWebhookRequest,
    UpdateWebhookRequest,
    WebhookEventRecord,
    WebhookListRequest,
)
from followupboss_mcp.services.action_plans import ActionPlansService
from followupboss_mcp.services.appointment_metadata import (
    AppointmentOutcomesService,
    AppointmentTypesService,
)
from followupboss_mcp.services.appointments import AppointmentsService
from followupboss_mcp.services.attachments import (
    DealAttachmentsService,
    PersonAttachmentsService,
)
from followupboss_mcp.services.automations import (
    AutomationPeopleService,
    AutomationsService,
)
from followupboss_mcp.services.calls import CallsService
from followupboss_mcp.services.custom_fields import CustomFieldsService
from followupboss_mcp.services.deals import DealsService
from followupboss_mcp.services.email_marketing import EmailMarketingService
from followupboss_mcp.services.events import EventsService
from followupboss_mcp.services.groups import GroupsService
from followupboss_mcp.services.identity import IdentityService
from followupboss_mcp.services.inbox_apps import InboxAppsService
from followupboss_mcp.services.notes import NotesService
from followupboss_mcp.services.people import PeopleService
from followupboss_mcp.services.people_relationships import PeopleRelationshipsService
from followupboss_mcp.services.pipelines import PipelinesService
from followupboss_mcp.services.ponds import PondsService
from followupboss_mcp.services.reactions import ReactionsService
from followupboss_mcp.services.smart_lists import SmartListsService
from followupboss_mcp.services.stages import StagesService
from followupboss_mcp.services.tasks import TasksService
from followupboss_mcp.services.team_inboxes import TeamInboxesService
from followupboss_mcp.services.teams import TeamsService
from followupboss_mcp.services.templates import TemplatesService
from followupboss_mcp.services.text_messages import (
    TextMessagesService,
    TextMessageTemplatesService,
)
from followupboss_mcp.services.threaded_replies import ThreadedRepliesService
from followupboss_mcp.services.timeframes import TimeframesService
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

    client = StubClient(
        [
            {
                "account": {
                    "id": 17,
                    "name": "Enterprise",
                    "domain": "fleet",
                    "owner": {"email": "captain@example.com", "name": "Captain"},
                },
                "user": {
                    "id": 2,
                    "name": "Will",
                    "email": "will@example.com",
                    "isOwner": False,
                },
            }
        ]
    )
    service = IdentityService(client)
    health = await service.health_check()
    assert health.ok is True
    assert health.identity.id == 2
    assert health.identity.name == "Will"
    assert health.identity.email == "will@example.com"
    assert health.identity.account_id == 17

    identity = IdentityResponse.model_validate(
        {
            "account": {
                "id": 18,
                "name": "Voyager",
                "domain": "delta",
                "owner": {"email": "janeway@example.com"},
            }
        }
    )
    assert identity.id == 18
    assert identity.name == "Voyager"
    assert identity.email == "janeway@example.com"
    assert identity.system == "delta"

    empty_identity = IdentityResponse.model_validate({})
    assert empty_identity.id is None
    assert empty_identity.email is None

    preserved_identity = IdentityResponse.model_validate(
        {"id": 19, "email": "existing@example.com"}
    )
    assert preserved_identity.id == 19
    assert preserved_identity.email == "existing@example.com"


@pytest.mark.asyncio
async def test_custom_fields_service() -> None:
    """Custom fields service should map list and admin operations correctly."""
    client = StubClient(
        [
            {
                "_metadata": {"limit": 10, "offset": 0, "total": "1"},
                "customfields": [
                    {"id": 1, "label": "Birthday", "name": "customBirthday", "type": "date"}
                ],
            },
            {
                "id": 2,
                "label": "Close price",
                "name": "customClosePrice",
                "type": "number",
                "choices": [],
            },
            {
                "id": 3,
                "label": "Looking for",
                "name": "customLookingFor",
                "type": "dropdown",
                "choices": ["Apartment", "Townhouse"],
            },
            {
                "id": 4,
                "label": "Looking for",
                "name": "customLookingFor",
                "type": "dropdown",
                "isRecurring": False,
            },
            {},
            [],
            [],
            [],
            [],
        ]
    )
    service = CustomFieldsService(client)
    page = await service.list_custom_fields(CustomFieldListRequest(label="Birthday"))
    assert page.items[0].name == "customBirthday"
    assert client.calls[0].params == {"label": "Birthday"}

    field = await service.get_custom_field(2)
    assert field.id == 2
    assert client.calls[1].path == "/customFields/2"

    created = await service.create_custom_field(
        CreateCustomFieldRequest(
            label="Looking for",
            type="dropdown",
            choices=["Apartment", "Townhouse"],
            hide_if_empty=True,
        )
    )
    assert created.id == 3
    assert client.calls[2].json_body == {
        "label": "Looking for",
        "type": "dropdown",
        "choices": ["Apartment", "Townhouse"],
        "hideIfEmpty": True,
    }

    updated = await service.update_custom_field(
        4,
        UpdateCustomFieldRequest(
            label="Looking for",
            choices=["Detached House"],
            dropdown_choice_map={"Apartment": 0},
            order_weight=2000,
        ),
    )
    assert updated.id == 4
    assert client.calls[3].path == "/customFields/4"
    assert client.calls[3].json_body == {
        "label": "Looking for",
        "choices": ["Detached House"],
        "dropdownChoiceMap": {"Apartment": 0},
        "orderWeight": 2000,
    }

    await service.delete_custom_field(5)
    assert client.calls[4].path == "/customFields/5"

    with pytest.raises(FollowUpBossValidationError):
        await service.list_custom_fields()
    with pytest.raises(FollowUpBossValidationError):
        await service.get_custom_field(2)
    with pytest.raises(FollowUpBossValidationError):
        await service.create_custom_field(
            CreateCustomFieldRequest(label="Close price", type="number")
        )
    with pytest.raises(FollowUpBossValidationError):
        await service.update_custom_field(4, UpdateCustomFieldRequest(label="Updated"))

    with pytest.raises(
        ValidationError, match="Dropdown custom fields must provide at least one choice"
    ):
        CreateCustomFieldRequest(label="Looking for", type="dropdown")
    with pytest.raises(
        ValidationError,
        match="At least one custom field update field must be provided",
    ):
        UpdateCustomFieldRequest()


@pytest.mark.asyncio
async def test_email_marketing_service() -> None:
    """Email marketing service should map campaigns and event batches correctly."""
    updated_after = datetime(2026, 3, 28, 12, 0, tzinfo=UTC)
    occurred_at = datetime(2026, 3, 28, 13, 0, tzinfo=UTC)
    client = StubClient(
        [
            {
                "_metadata": {"limit": 10, "offset": 0, "total": 1},
                "emCampaigns": [
                    {
                        "id": 102,
                        "origin": "Curaytor",
                        "originId": "912",
                        "name": "Can I help",
                        "subject": "Can I help?",
                        "bodyHtml": "I saw you're browsing our website, can I help with...",
                    }
                ],
            },
            {
                "id": 103,
                "origin": "Curaytor",
                "originId": "913",
                "name": "New Campaign",
                "subject": "Hello",
                "bodyHtml": "<p>Hello</p>",
            },
            {
                "id": 104,
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
        ]
    )
    service = EmailMarketingService(client)

    campaigns_page = await service.list_email_campaigns(
        EmailCampaignListRequest(origin="Curaytor", origin_id="912")
    )
    assert campaigns_page.items[0].origin_id == "912"
    assert client.calls[0].params == {"origin": "Curaytor", "originId": "912"}

    created_campaign = await service.create_email_campaign(
        CreateEmailCampaignRequest(
            origin="Curaytor",
            origin_id="913",
            name="New Campaign",
            subject="Hello",
            body_html="<p>Hello</p>",
        )
    )
    assert created_campaign.id == 103
    assert client.calls[1].json_body == {
        "origin": "Curaytor",
        "originId": "913",
        "name": "New Campaign",
        "subject": "Hello",
        "bodyHtml": "<p>Hello</p>",
    }

    updated_campaign = await service.update_email_campaign(
        104,
        UpdateEmailCampaignRequest(
            name="Updated Campaign", subject="Updated", body_html="<p>Updated</p>"
        ),
    )
    assert updated_campaign.id == 104
    assert client.calls[2].path == "/emCampaigns/104"
    assert client.calls[2].json_body == {
        "name": "Updated Campaign",
        "subject": "Updated",
        "bodyHtml": "<p>Updated</p>",
    }

    events_page = await service.list_email_events(
        EmailEventListRequest(
            type="open",
            person_id=10911,
            updated_after=updated_after,
            limit=10,
            offset=0,
        )
    )
    assert events_page.items[0].campaign_id == 102
    assert client.calls[3].params == {
        "type": "open",
        "personId": "10911",
        "updatedAfter": updated_after.isoformat(),
        "limit": "10",
        "offset": "0",
    }

    batch_result = await service.send_email_events(
        CreateEmailEventsBatchRequest.model_validate(
            {
                "em_events": [
                    {
                        "type": "delivered",
                        "occurred": occurred_at.isoformat(),
                        "recipient": "john.smith@gmail.com",
                        "person_id": 1,
                        "campaign_id": 141,
                        "user_id": 3,
                    },
                    {
                        "type": "open",
                        "occurred": occurred_at.isoformat(),
                        "recipient": "jane@example.com",
                        "campaign_id": "141",
                    },
                ]
            }
        )
    )
    assert batch_result.em_event_ids == [193928, 193929]
    assert client.calls[4].json_body == {
        "emEvents": [
            {
                "type": "delivered",
                "occurred": "2026-03-28T13:00:00Z",
                "recipient": "john.smith@gmail.com",
                "personId": 1,
                "campaignId": 141,
                "userId": 3,
            },
            {
                "type": "open",
                "occurred": "2026-03-28T13:00:00Z",
                "recipient": "jane@example.com",
                "campaignId": "141",
            },
        ]
    }

    invalid_campaign_service = EmailMarketingService(StubClient([[], [], [], {"emCampaigns": {}}]))
    with pytest.raises(ValueError, match="Unexpected email campaigns response"):
        await invalid_campaign_service.list_email_campaigns()
    with pytest.raises(ValueError, match="Unexpected email campaigns response"):
        await invalid_campaign_service.create_email_campaign(
            CreateEmailCampaignRequest(origin="Curaytor", origin_id="913")
        )
    with pytest.raises(ValueError, match="Unexpected email campaigns response"):
        await invalid_campaign_service.update_email_campaign(
            104, UpdateEmailCampaignRequest(name="Updated")
        )
    with pytest.raises(ValueError, match="Unexpected email events response"):
        await EmailMarketingService(StubClient([[]])).list_email_events()
    with pytest.raises(ValueError, match="Unexpected email campaigns response"):
        await invalid_campaign_service.list_email_campaigns()
    with pytest.raises(ValueError, match="Unexpected email events response"):
        await EmailMarketingService(StubClient([{"emEvents": {}}])).list_email_events()
    with pytest.raises(ValueError, match="Unexpected email events response"):
        await EmailMarketingService(StubClient([[]])).send_email_events(
            CreateEmailEventsBatchRequest.model_validate(
                {
                    "em_events": [
                        {
                            "type": "delivered",
                            "occurred": occurred_at.isoformat(),
                            "recipient": "john.smith@gmail.com",
                            "campaign_id": 141,
                        }
                    ]
                }
            )
        )

    with pytest.raises(ValidationError, match="At least one email campaign field must be provided"):
        UpdateEmailCampaignRequest()
    with pytest.raises(
        ValidationError,
        match="At least one email marketing event must be provided",
    ):
        CreateEmailEventsBatchRequest(em_events=[])
    with pytest.raises(
        ValidationError,
        match="Email marketing event batches cannot exceed 1000 events",
    ):
        CreateEmailEventsBatchRequest.model_validate(
            {
                "em_events": [
                    {
                        "type": "delivered",
                        "occurred": occurred_at.isoformat(),
                        "recipient": f"user-{index}@example.com",
                        "campaign_id": 141,
                    }
                    for index in range(1001)
                ]
            }
        )


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
async def test_automations_service() -> None:
    """Automations services should map queries, bodies, and pairing updates correctly."""
    client = StubClient(
        [
            {
                "_metadata": {"limit": 10, "offset": 0, "total": 1},
                "automations": [{"id": 1, "name": "Test Automation", "status": "Active"}],
            },
            {"id": 2, "name": "Test Automation", "status": "Active"},
            {
                "_metadata": {"limit": 10, "offset": 0, "total": 1},
                "automationsPeople": [
                    {
                        "id": 3,
                        "created": "2023-08-09T21:36:05Z",
                        "updated": "2023-08-09T21:36:05Z",
                        "createdById": -1,
                        "updatedById": -1,
                        "createdBy": "Follow Up Boss",
                        "updatedBy": "Follow Up Boss",
                        "personId": 2,
                        "automationId": 1,
                        "status": "Completed",
                        "automationName": "Test Automation",
                    }
                ],
            },
            {
                "id": 4,
                "created": "2023-08-09T21:36:05Z",
                "updated": "2023-08-09T21:36:05Z",
                "createdById": -1,
                "updatedById": -1,
                "createdBy": "Follow Up Boss",
                "updatedBy": "Follow Up Boss",
                "personId": 2,
                "automationId": 1,
                "status": "Completed",
                "automationName": "Test Automation",
            },
            {
                "id": 5,
                "created": "2023-08-09T21:36:05Z",
                "updated": "2023-08-09T21:36:05Z",
                "createdById": -1,
                "updatedById": -1,
                "createdBy": "Follow Up Boss",
                "updatedBy": "Follow Up Boss",
                "personId": 3,
                "automationId": 1,
                "status": "Running",
                "automationName": "Test Automation",
            },
            {
                "id": 6,
                "created": "2023-08-09T21:36:05Z",
                "updated": "2023-08-09T21:36:05Z",
                "createdById": -1,
                "updatedById": -1,
                "createdBy": "Follow Up Boss",
                "updatedBy": "Follow Up Boss",
                "personId": 3,
                "automationId": 1,
                "status": "Paused",
                "automationName": "Test Automation",
            },
        ]
    )
    automations_service = AutomationsService(client)
    automation_people_service = AutomationPeopleService(client)

    automations_page = await automations_service.list_automations(
        AutomationListRequest(
            enabled_only=True,
            limit=5,
            manual_only=False,
            next_token="cursor-123",
            offset=10,
            status="Active",
        )
    )
    assert automations_page.items[0].name == "Test Automation"
    assert client.calls[0].params == {
        "enabledOnly": "true",
        "limit": "5",
        "manualOnly": "false",
        "next": "cursor-123",
        "offset": "10",
        "status": "Active",
    }

    automation = await automations_service.get_automation(2)
    assert automation.id == 2

    automation_people_page = await automation_people_service.list_automation_people(
        AutomationPeopleListRequest(automation_id=1, person_id=2, status="Completed")
    )
    assert automation_people_page.items[0].automation_name == "Test Automation"
    assert client.calls[2].params == {
        "automationId": "1",
        "personId": "2",
        "status": "Completed",
    }

    automation_person = await automation_people_service.get_automation_person(4)
    assert automation_person.id == 4

    created = await automation_people_service.create_automation_person(
        CreateAutomationPersonRequest(automation_id=1, person_id=3)
    )
    assert created.id == 5
    assert client.calls[4].json_body == {"automationId": 1, "personId": 3}

    updated = await automation_people_service.update_automation_person(
        6,
        UpdateAutomationPersonRequest(status="Paused"),
    )
    assert updated.id == 6
    assert client.calls[5].json_body == {"status": "Paused"}


@pytest.mark.asyncio
async def test_action_plans_service() -> None:
    """Action plans service should map queries, bodies, and relationship updates correctly."""
    client = StubClient(
        [
            {
                "_metadata": {"limit": 10, "offset": 0, "total": 1},
                "actionPlans": [
                    {
                        "id": 6,
                        "created": "2014-08-24T22:12:53Z",
                        "updated": "2014-08-24T22:12:53Z",
                        "name": "Qualify buyer leads",
                        "status": "Active",
                    }
                ],
            },
            {
                "_metadata": {"limit": 10, "offset": 0, "total": 1},
                "actionPlansPeople": [
                    {
                        "id": 2,
                        "created": "2014-08-19T18:31:43Z",
                        "updated": "2014-08-19T18:31:43Z",
                        "personId": 10810,
                        "actionPlanId": 2,
                        "status": "Running",
                    }
                ],
            },
            {},
            {
                "id": 3,
                "created": "2014-08-19T18:31:43Z",
                "updated": "2014-08-19T18:31:43Z",
                "personId": 10810,
                "actionPlanId": 2,
                "status": "Paused",
            },
        ]
    )
    service = ActionPlansService(client)

    action_plans_page = await service.list_action_plans(
        ActionPlanListRequest(
            ids=[6, 7],
            limit=5,
            names=["Qualify buyer leads", "Nurture seller leads"],
            offset=10,
            sort="-id",
            status="Active",
        )
    )
    assert action_plans_page.items[0].name == "Qualify buyer leads"
    assert client.calls[0].params == {
        "ids": "6,7",
        "limit": "5",
        "names[]": "Qualify buyer leads,Nurture seller leads",
        "offset": "10",
        "sort": "-id",
        "status": "Active",
    }

    action_plan_people_page = await service.list_action_plan_people(
        ActionPlanPersonListRequest(action_plan_id=2, limit=5, offset=10, person_id=10810)
    )
    assert action_plan_people_page.items[0].action_plan_id == 2
    assert client.calls[1].params == {
        "actionPlanId": "2",
        "limit": "5",
        "offset": "10",
        "personId": "10810",
    }

    applied = await service.apply_action_plan(
        CreateActionPlanPersonRequest(action_plan_id=2, person_id=10810)
    )
    assert applied.id is None
    assert client.calls[2].json_body == {"actionPlanId": 2, "personId": 10810}

    updated = await service.update_action_plan_person(
        3,
        UpdateActionPlanPersonRequest(status="Paused"),
    )
    assert updated.id == 3
    assert client.calls[3].json_body == {"status": "Paused"}

    invalid_service = ActionPlansService(StubClient([[], {"actionPlansPeople": {}}, [], []]))
    with pytest.raises(ValueError, match="Unexpected action plans response"):
        await invalid_service.list_action_plans()
    with pytest.raises(ValueError, match="Unexpected actionPlansPeople response"):
        await invalid_service.list_action_plan_people()
    with pytest.raises(ValueError, match="Unexpected actionPlansPeople response"):
        await invalid_service.apply_action_plan(
            CreateActionPlanPersonRequest(action_plan_id=2, person_id=10810)
        )
    with pytest.raises(ValueError, match="Unexpected actionPlansPeople response"):
        await invalid_service.update_action_plan_person(
            3,
            UpdateActionPlanPersonRequest(status="Paused"),
        )

    invalid_people_service = ActionPlansService(StubClient([[]]))
    with pytest.raises(ValueError, match="Unexpected actionPlansPeople response"):
        await invalid_people_service.list_action_plan_people()


@pytest.mark.asyncio
async def test_groups_service() -> None:
    """Groups service should map queries, bodies, and delete behavior correctly."""
    client = StubClient(
        [
            {
                "_metadata": {"limit": 10, "offset": 0, "total": 1},
                "groups": [
                    {
                        "id": 1,
                        "name": "Eastside",
                        "type": "Agent",
                        "distribution": "first-to-claim",
                        "defaultUserId": None,
                        "defaultPondId": None,
                        "defaultGroupId": None,
                        "claimWindow": 900,
                        "nextRoundRobinUser": None,
                        "isPrimary": False,
                        "users": [
                            {
                                "id": 199,
                                "name": "Daniel Corkill",
                                "firstName": "Daniel",
                                "lastName": "Corkill",
                                "role": "Broker",
                                "pauseLeadDistribution": True,
                            }
                        ],
                    }
                ],
            },
            {
                "_metadata": {"limit": 10, "offset": 0, "total": 1},
                "groups": [
                    {
                        "id": 2,
                        "name": "Round Robin",
                        "type": "Agent",
                        "distribution": "round-robin",
                        "nextRoundRobinUser": 334,
                    }
                ],
            },
            {
                "id": 3,
                "name": "Eastside",
                "type": "Agent",
                "distribution": "first-to-claim",
                "users": [{"id": 199, "name": "Daniel Corkill"}],
            },
            {
                "id": 4,
                "name": "Westside",
                "type": "Agent",
                "distribution": "round-robin",
                "users": [{"id": 200, "name": "Beverly Crusher"}],
            },
            {
                "id": 5,
                "name": "Westside Plus",
                "type": "Agent",
                "distribution": "first-to-claim",
                "claimWindow": 1800,
                "defaultUserId": 7,
                "users": [{"id": 200, "name": "Beverly Crusher"}],
            },
            {},
        ]
    )
    service = GroupsService(client)

    groups_page = await service.list_groups(GroupListRequest(type="Agent", sort="-name"))
    assert groups_page.items[0].name == "Eastside"
    assert groups_page.items[0].users[0].first_name == "Daniel"
    assert client.calls[0].params == {"type": "Agent", "sort": "-name"}

    round_robin_page = await service.list_round_robin_groups(
        GroupListRequest(type="Agent", sort="name")
    )
    assert round_robin_page.items[0].next_round_robin_user == 334
    assert client.calls[1].path == "/groups/roundRobin"
    assert client.calls[1].params == {"type": "Agent", "sort": "name"}

    group = await service.get_group(3)
    assert group.id == 3

    created = await service.create_group(
        CreateGroupRequest(
            name="Westside",
            users=[200, 201],
            distribution="round-robin",
            type="Agent",
        )
    )
    assert created.id == 4
    assert client.calls[3].json_body == {
        "name": "Westside",
        "users": [200, 201],
        "distribution": "round-robin",
        "type": "Agent",
    }

    updated = await service.update_group(
        5,
        UpdateGroupRequest(
            name="Westside Plus",
            users=[200, 201],
            distribution="first-to-claim",
            claim_window=1800,
            default_user_id=7,
        ),
    )
    assert updated.id == 5
    assert client.calls[4].json_body == {
        "name": "Westside Plus",
        "users": [200, 201],
        "distribution": "first-to-claim",
        "claimWindow": 1800,
        "defaultUserId": 7,
    }

    await service.delete_group(6)
    assert client.calls[5].path == "/groups/6"

    with pytest.raises(ValidationError, match="At least one group field must be provided"):
        UpdateGroupRequest()


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
async def test_people_service_admin_utility_endpoints() -> None:
    """People service should cover duplicate checks and unclaimed-lead utilities."""
    client = StubClient(
        [
            {
                "found": True,
                "matchedBy": "email",
                "assignedTo": "Agent Smith",
            },
            {
                "_metadata": {"limit": 10, "offset": 0, "total": 1},
                "people": [
                    {
                        "id": 13,
                        "firstName": "Unclaimed",
                        "source": "Zillow",
                        "sourceId": 730,
                        "claimed": False,
                        "delayed": False,
                        "picture": {"small": "https://example.com/avatar.jpg"},
                    }
                ],
            },
            {
                "id": 14,
                "firstName": "Claimed",
                "assignedTo": "Agent Smith",
                "claimed": False,
            },
            {},
        ]
    )
    service = PeopleService(client)

    duplicate = await service.check_duplicate_person(
        PersonDuplicateCheckRequest(email="agent@example.com")
    )
    assert duplicate.found is True
    assert duplicate.matched_by == "email"
    assert client.calls[0].path == "/people/checkDuplicate"
    assert client.calls[0].params == {"email": "agent@example.com"}

    unclaimed = await service.list_unclaimed_people(UnclaimedPeopleListRequest(limit=10, offset=0))
    assert unclaimed.items[0].source_id == 730
    assert unclaimed.items[0].picture is not None
    assert unclaimed.items[0].picture.small == "https://example.com/avatar.jpg"
    assert client.calls[1].path == "/people/unclaimed"
    assert client.calls[1].params == {"limit": "10", "offset": "0"}

    claimed = await service.claim_person(ClaimPersonRequest(person_id=14))
    assert claimed.id == 14
    assert client.calls[2].path == "/people/claim"
    assert client.calls[2].json_body == {"personId": 14}

    await service.ignore_unclaimed_person(IgnoreUnclaimedPersonRequest(person_id=14))
    assert client.calls[3].path == "/people/ignoreUnclaimed"
    assert client.calls[3].json_body == {"personId": 14}

    conflict_service = PeopleService(
        StubClient(
            [
                FollowUpBossHTTPError(
                    "Lead already claimed.",
                    status_code=409,
                    payload={
                        "id": 15,
                        "firstName": "Already",
                        "claimed": True,
                        "sourceId": 99,
                    },
                )
            ]
        )
    )
    conflict_result = await conflict_service.claim_person(ClaimPersonRequest(person_id=15))
    assert conflict_result.claimed is True
    assert conflict_result.source_id == 99

    with pytest.raises(
        ValidationError, match="Duplicate checks must include either email or phone"
    ):
        PersonDuplicateCheckRequest()

    invalid_collection_service = PeopleService(StubClient([[], {"people": {}}]))
    with pytest.raises(ValueError, match="Unexpected people duplicate-check response"):
        await invalid_collection_service.check_duplicate_person(
            PersonDuplicateCheckRequest(phone="5551112222")
        )
    with pytest.raises(ValueError, match="Unexpected unclaimed people response"):
        await invalid_collection_service.list_unclaimed_people()

    invalid_unclaimed_service = PeopleService(
        StubClient([cast(dict[str, object] | list[object] | Exception, "unexpected")])
    )
    with pytest.raises(ValueError, match="Unexpected unclaimed people response"):
        await invalid_unclaimed_service.list_unclaimed_people()

    invalid_claim_service = PeopleService(
        StubClient(
            [
                cast(dict[str, object] | list[object] | Exception, "unexpected"),
            ]
        )
    )
    with pytest.raises(ValueError, match="Unexpected people claim response"):
        await invalid_claim_service.claim_person(ClaimPersonRequest(person_id=16))

    invalid_conflict_service = PeopleService(
        StubClient([FollowUpBossHTTPError("Conflict", status_code=409)])
    )
    with pytest.raises(FollowUpBossHTTPError):
        await invalid_conflict_service.claim_person(ClaimPersonRequest(person_id=17))

    invalid_error_service = PeopleService(
        StubClient([FollowUpBossHTTPError("Internal", status_code=500)])
    )
    with pytest.raises(FollowUpBossHTTPError):
        await invalid_error_service.claim_person(ClaimPersonRequest(person_id=18))


@pytest.mark.asyncio
async def test_people_relationships_service() -> None:
    """People relationships service should map list/get/create/update/delete correctly."""
    client = StubClient(
        [
            {
                "_metadata": {"limit": 10, "offset": 0, "total": 1},
                "peoplerelationships": [
                    {
                        "id": 423,
                        "created": "2021-02-19T14:12:36Z",
                        "updated": "2021-02-19T14:12:41Z",
                        "createdById": 41,
                        "updatedById": 41,
                        "personId": 46977,
                        "name": "Billy Bob",
                        "firstName": "Billy",
                        "lastName": "Bob",
                        "type": "Husband",
                        "isPriority": True,
                        "emails": [],
                        "phones": [
                            {
                                "value": "5551113333",
                                "type": "mobile",
                                "status": "Valid",
                                "isPrimary": 1,
                                "normalized": "5551113333",
                            }
                        ],
                        "addresses": [],
                        "picture": None,
                        "socialData": [],
                    }
                ],
            },
            {
                "id": 423,
                "created": "2021-02-19T14:12:36Z",
                "updated": "2021-02-19T14:12:41Z",
                "createdById": 41,
                "updatedById": 41,
                "personId": 46977,
                "name": "Billy Bob",
                "firstName": "Billy",
                "lastName": "Bob",
                "type": "Husband",
                "isPriority": True,
                "emails": [],
                "phones": [],
                "addresses": [],
                "picture": None,
                "socialData": [],
            },
            {},
            {},
            {},
        ]
    )
    service = PeopleRelationshipsService(client)

    relationships_page = await service.list_people_relationships(
        PeopleRelationshipListRequest(
            person_id=46977,
            first_name="Billy",
            last_name="Bob",
            name="Billy Bob",
            sort="name",
        )
    )
    assert relationships_page.items[0].person_id == 46977
    assert client.calls[0].params == {
        "personId": "46977",
        "firstName": "Billy",
        "lastName": "Bob",
        "name": "Billy Bob",
        "sort": "name",
    }

    legacy_page = await PeopleRelationshipsService(
        StubClient([[{"id": 424, "personId": 46977, "name": "Legacy Shape"}]])
    ).list_people_relationships()
    assert legacy_page.items[0].id == 424

    camel_case_page = await PeopleRelationshipsService(
        StubClient(
            [
                {
                    "_metadata": {"limit": 10, "offset": 0, "total": 1},
                    "peopleRelationships": [{"id": 425, "personId": 46977, "name": "Camel Shape"}],
                }
            ]
        )
    ).list_people_relationships()
    assert camel_case_page.items[0].id == 425

    relationship = await service.get_people_relationship(423)
    assert relationship.id == 423
    assert client.calls[1].path == "/peopleRelationships/423"

    created = await service.create_people_relationship(
        CreatePeopleRelationshipRequest(
            person_id=46977,
            first_name="Billy",
            last_name="Bob",
            type="Husband",
            emails=[EmailAddress(value="billy@example.com", type="home")],
        )
    )
    assert created.id is None
    assert client.calls[2].json_body == {
        "personId": 46977,
        "firstName": "Billy",
        "lastName": "Bob",
        "type": "Husband",
        "emails": [{"value": "billy@example.com", "type": "home"}],
    }

    updated = await service.update_people_relationship(
        423,
        UpdatePeopleRelationshipRequest(
            type="Spouse",
            phones=[PhoneNumber(value="5551113333", type="mobile")],
        ),
    )
    assert updated.id is None
    assert client.calls[3].path == "/peopleRelationships/423"
    assert client.calls[3].json_body == {
        "type": "Spouse",
        "phones": [{"value": "5551113333", "type": "mobile"}],
    }

    await service.delete_people_relationship(423)
    assert client.calls[4].path == "/peopleRelationships/423"

    invalid_service = PeopleRelationshipsService(StubClient([{}, [], [], []]))
    with pytest.raises(ValueError, match="Unexpected people relationships response"):
        await invalid_service.list_people_relationships()
    with pytest.raises(ValueError, match="Unexpected people relationship response"):
        await invalid_service.get_people_relationship(423)
    with pytest.raises(ValueError, match="Unexpected people relationship response"):
        await invalid_service.create_people_relationship(
            CreatePeopleRelationshipRequest(person_id=46977)
        )
    with pytest.raises(ValueError, match="Unexpected people relationship response"):
        await invalid_service.update_people_relationship(
            423,
            UpdatePeopleRelationshipRequest(type="Spouse"),
        )

    with pytest.raises(
        ValidationError, match="At least one people relationship field must be provided"
    ):
        UpdatePeopleRelationshipRequest()

    scalar_payload_service = PeopleRelationshipsService(StubClient([cast(Any, "invalid payload")]))
    with pytest.raises(ValueError, match="Unexpected people relationships response"):
        await scalar_payload_service.list_people_relationships()


@pytest.mark.asyncio
async def test_attachment_services() -> None:
    """Attachment services should map get, create, update, and delete behavior correctly."""
    client = StubClient(
        [
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
        ]
    )
    person_service = PersonAttachmentsService(client)
    deal_service = DealAttachmentsService(client)

    person_attachment = await person_service.get_person_attachment(2)
    assert person_attachment.person_id == 1
    assert client.calls[0].path == "/personAttachments/2"

    created_person_attachment = await person_service.create_person_attachment(
        CreatePersonAttachmentRequest(
            person_id=1,
            uri="https://test.com/myfile",
            file_name="test.jpg",
        )
    )
    assert created_person_attachment.id == 3
    assert client.calls[1].json_body == {
        "personId": 1,
        "uri": "https://test.com/myfile",
        "fileName": "test.jpg",
    }

    updated_person_attachment = await person_service.update_person_attachment(
        4,
        UpdatePersonAttachmentRequest(
            person_id=1,
            uri="https://test.com/updated",
            file_name="updated.jpg",
            file_size=42,
        ),
    )
    assert updated_person_attachment.id == 4
    assert client.calls[2].path == "/personAttachments/4"
    assert client.calls[2].json_body == {
        "personId": 1,
        "uri": "https://test.com/updated",
        "fileName": "updated.jpg",
        "fileSize": 42,
    }

    await person_service.delete_person_attachment(5)
    assert client.calls[3].path == "/personAttachments/5"

    deal_attachment = await deal_service.get_deal_attachment(10)
    assert deal_attachment.deal_id == 8
    assert client.calls[4].path == "/dealAttachments/10"

    created_deal_attachment = await deal_service.create_deal_attachment(
        CreateDealAttachmentRequest(
            deal_id=8,
            uri="https://test.com/deal",
            file_name="deal.jpg",
        )
    )
    assert created_deal_attachment.id == 11
    assert client.calls[5].json_body == {
        "dealId": 8,
        "uri": "https://test.com/deal",
        "fileName": "deal.jpg",
    }

    updated_deal_attachment = await deal_service.update_deal_attachment(
        12,
        UpdateDealAttachmentRequest(
            deal_id=9,
            uri="https://test.com/deal-updated",
            file_name="deal-updated.jpg",
            file_size=24,
        ),
    )
    assert updated_deal_attachment.id == 12
    assert client.calls[6].path == "/dealAttachments/12"
    assert client.calls[6].json_body == {
        "dealId": 9,
        "uri": "https://test.com/deal-updated",
        "fileName": "deal-updated.jpg",
        "fileSize": 24,
    }

    await deal_service.delete_deal_attachment(13)
    assert client.calls[7].path == "/dealAttachments/13"

    invalid_person_service = PersonAttachmentsService(StubClient([[], [], []]))
    with pytest.raises(ValueError, match="Unexpected person attachment response"):
        await invalid_person_service.get_person_attachment(2)
    with pytest.raises(ValueError, match="Unexpected person attachment response"):
        await invalid_person_service.create_person_attachment(
            CreatePersonAttachmentRequest(
                person_id=1,
                uri="https://test.com/myfile",
                file_name="test.jpg",
            )
        )
    with pytest.raises(ValueError, match="Unexpected person attachment response"):
        await invalid_person_service.update_person_attachment(
            4,
            UpdatePersonAttachmentRequest(
                person_id=1,
                uri="https://test.com/updated",
                file_name="updated.jpg",
            ),
        )

    invalid_deal_service = DealAttachmentsService(StubClient([[], [], []]))
    with pytest.raises(ValueError, match="Unexpected deal attachment response"):
        await invalid_deal_service.get_deal_attachment(10)
    with pytest.raises(ValueError, match="Unexpected deal attachment response"):
        await invalid_deal_service.create_deal_attachment(
            CreateDealAttachmentRequest(
                deal_id=8,
                uri="https://test.com/deal",
                file_name="deal.jpg",
            )
        )
    with pytest.raises(ValueError, match="Unexpected deal attachment response"):
        await invalid_deal_service.update_deal_attachment(
            12,
            UpdateDealAttachmentRequest(
                deal_id=9,
                uri="https://test.com/deal-updated",
                file_name="deal-updated.jpg",
            ),
        )


@pytest.mark.asyncio
async def test_reactions_service() -> None:
    """Reactions service should map get, add, and delete behavior correctly."""
    client = StubClient(
        [
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
        ]
    )
    service = ReactionsService(client)

    reaction = await service.get_reaction(1363)
    assert reaction.ref_type == "Note"
    assert client.calls[0].path == "/reactions/1363"

    created = await service.add_reaction(
        "Note",
        2144705,
        CreateReactionRequest(body="🤣"),
    )
    assert created.model_dump(exclude_none=True) == {}
    assert client.calls[1].path == "/reactions/Note/2144705"
    assert client.calls[1].json_body == {"body": "🤣"}

    await service.delete_reaction("Note", 2144705, DeleteReactionRequest(emoji="👏"))
    assert client.calls[2].path == "/reactions/Note/2144705"
    assert client.calls[2].params == {"emoji": "👏"}

    invalid_reaction_service = ReactionsService(StubClient([[], ["unexpected"], []]))
    with pytest.raises(ValueError, match="Unexpected reactions response"):
        await invalid_reaction_service.get_reaction(1363)
    with pytest.raises(ValueError, match="Unexpected reactions response"):
        await invalid_reaction_service.add_reaction(
            "Note",
            2144705,
            CreateReactionRequest(body="🤣"),
        )

    ack_reaction_service = ReactionsService(StubClient([{}]))
    acknowledged = await ack_reaction_service.add_reaction(
        "Note",
        2144705,
        CreateReactionRequest(body="🤣"),
    )
    assert acknowledged.model_dump(exclude_none=True) == {}

    malformed_reaction_service = ReactionsService(
        StubClient(
            [
                cast(
                    dict[str, object] | list[object] | Exception,
                    "unexpected",
                )
            ]
        )
    )
    with pytest.raises(ValueError, match="Unexpected reactions response"):
        await malformed_reaction_service.add_reaction(
            "Note",
            2144705,
            CreateReactionRequest(body="🤣"),
        )


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

    created_from_camel_case = CreateAppointmentRequest.model_validate(
        {
            "title": "Camel appointment",
            "start": "2026-03-28T10:00:00Z",
            "end": "2026-03-28T11:00:00Z",
            "invitees": [{"personId": 99, "userId": 5, "name": "Data"}],
        }
    )
    assert created_from_camel_case.model_dump(by_alias=True, exclude_none=True)["invitees"] == [
        {"personId": 99, "userId": 5, "name": "Data"}
    ]

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
                        "type": 0,
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
                "type": 1,
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
            {
                "id": 7,
                "label": "Close Date",
                "name": "customCloseDate",
                "type": "date",
                "isRecurring": False,
                "hideIfEmpty": True,
                "readOnly": False,
            },
            {
                "id": 8,
                "label": "Priority",
                "name": "customPriority",
                "type": "dropdown",
                "choices": ["High", "Medium", "Low"],
                "hideIfEmpty": False,
                "readOnly": False,
            },
            {
                "id": 9,
                "label": "Priority",
                "name": "customPriority",
                "type": "dropdown",
                "choices": ["Critical", "High", "Medium"],
                "hideIfEmpty": True,
                "readOnly": True,
            },
            {},
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
    assert deals_page.items[0].type == 0
    assert client.calls[0].params == {
        "pipelineId": "3",
        "userId": "5",
        "personId": "99",
        "includeDeleted": "1",
        "includeArchived": "0",
        "status": "Active",
    }

    deal = await service.get_deal(2)
    assert deal.id == 2
    assert deal.type == 1

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

    custom_field = await service.get_deal_custom_field(7)
    assert custom_field.id == 7
    assert client.calls[6].path == "/dealCustomFields/7"

    created_custom_field = await service.create_deal_custom_field(
        CreateDealCustomFieldRequest(
            label="Priority",
            type="dropdown",
            choices=["High", "Medium", "Low"],
        )
    )
    assert created_custom_field.id == 8
    assert client.calls[7].json_body == {
        "label": "Priority",
        "type": "dropdown",
        "choices": ["High", "Medium", "Low"],
    }

    updated_custom_field = await service.update_deal_custom_field(
        9,
        UpdateDealCustomFieldRequest(
            label="Priority",
            choices=["Critical", "High", "Medium"],
            hide_if_empty=True,
            read_only=True,
        ),
    )
    assert updated_custom_field.id == 9
    assert client.calls[8].json_body == {
        "label": "Priority",
        "choices": ["Critical", "High", "Medium"],
        "hideIfEmpty": True,
        "readOnly": True,
    }

    await service.delete_deal_custom_field(9)
    assert client.calls[9].path == "/dealCustomFields/9"

    with pytest.raises(FollowUpBossValidationError, match="Deal custom field keys"):
        DealsService.validate_deal_custom_field_names({"ClosePrice": 1})

    with pytest.raises(ValidationError, match="Dropdown deal custom fields must provide"):
        CreateDealCustomFieldRequest(label="Priority", type="dropdown")

    with pytest.raises(ValidationError, match="Dropdown deal custom field updates must provide"):
        UpdateDealCustomFieldRequest(type="dropdown")

    with pytest.raises(
        ValidationError,
        match="At least one deal custom field update field must be provided",
    ):
        UpdateDealCustomFieldRequest()

    invalid_service = DealsService(StubClient([[], {"dealCustomfields": {}}, [], [], []]))
    with pytest.raises(FollowUpBossValidationError, match="Unexpected deal custom fields"):
        await invalid_service.list_deal_custom_fields()
    with pytest.raises(FollowUpBossValidationError, match="Unexpected deal custom fields"):
        await invalid_service.list_deal_custom_fields()
    with pytest.raises(FollowUpBossValidationError, match="Unexpected deal custom fields"):
        await invalid_service.get_deal_custom_field(7)
    with pytest.raises(FollowUpBossValidationError, match="Unexpected deal custom fields"):
        await invalid_service.create_deal_custom_field(
            CreateDealCustomFieldRequest(label="Priority", type="text")
        )
    with pytest.raises(FollowUpBossValidationError, match="Unexpected deal custom fields"):
        await invalid_service.update_deal_custom_field(
            9,
            UpdateDealCustomFieldRequest(label="Priority"),
        )


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
async def test_inbox_apps_service() -> None:
    """Inbox apps service should map installation and conversation flows correctly."""
    client = StubClient(
        [
            {
                "inboxApps": [
                    {
                        "inboxAppId": 1,
                        "userId": 0,
                        "created": "2025-01-01T12:12:12Z",
                    }
                ]
            },
            {
                "id": 2,
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
                    "id": 3,
                    "status": "active",
                    "userId": None,
                    "personId": None,
                    "name": "John Doe",
                    "phone": "+14075550123",
                    "email": "john@example.com",
                    "isAutomation": False,
                }
            ],
            {
                "id": 4,
                "status": "active",
                "userId": None,
                "personId": None,
                "name": "John Doe",
                "phone": "+14075550123",
                "email": "john@example.com",
                "isAutomation": False,
            },
            {},
            {
                "id": 5,
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
                "id": 6,
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
                "id": 7,
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
                "attachments": [],
                "conversationDeepLinkUrl": "https://app.followupboss.com/2/inbox-new/0/inbox/1",
            },
        ]
    )
    service = InboxAppsService(client)

    installations_page = await service.list_inbox_app_installations(9)
    assert installations_page.items[0].inbox_app_id == 1
    assert client.calls[0].path == "/inboxApps/installedApps/9"

    installed = await service.install_inbox_app(
        InstallInboxAppRequest(
            published_inbox_app_id=9,
            user_id=0,
            subscription_url="https://example.com/webhook",
        )
    )
    assert installed.id == 2
    assert client.calls[1].json_body == {
        "publishedInboxAppId": 9,
        "userId": 0,
        "subscriptionUrl": "https://example.com/webhook",
    }

    await service.deactivate_inbox_app(2)
    assert client.calls[2].path == "/inboxApps/2"

    participants_page = await service.list_inbox_app_participants(2, "conv-123")
    assert participants_page.items[0].name == "John Doe"
    assert client.calls[3].path == "/inboxApps/2/conversations/conv-123/participants"

    participant = await service.add_inbox_app_participant(
        2,
        "conv-123",
        CreateInboxAppParticipantRequest(name="John Doe", email="john@example.com"),
    )
    assert participant.id == 4
    assert client.calls[4].json_body == {"name": "John Doe", "email": "john@example.com"}

    await service.remove_inbox_app_participant(2, "conv-123", 4)
    assert client.calls[5].path == "/inboxApps/2/conversations/conv-123/participants/4"

    message = await service.add_inbox_app_message(
        2,
        CreateInboxAppMessageRequest(
            external_conversation_id="conv-123",
            external_message_id="msg-123",
            message="An example message.",
            is_incoming=True,
            sender=InboxAppMessageSenderRequest(personId=1),
            person=InboxAppConversationPersonRequest(id=1),
            owner=InboxAppConversationOwnerRequest(userId=5),
            attachments=[
                InboxAppAttachmentRequest(
                    filename="example-2.jpg",
                    url="https://followupboss.test/example-2.jpg",
                )
            ],
            rich_objects=["https://example.com/objects/1"],
        ),
    )
    assert message.id == 5
    assert client.calls[6].path == "/inboxApps/2/message"
    assert client.calls[6].json_body == {
        "externalConversationId": "conv-123",
        "externalMessageId": "msg-123",
        "message": "An example message.",
        "isIncoming": True,
        "sender": {"personId": 1},
        "person": {"id": 1},
        "owner": {"userId": 5},
        "attachments": [
            {
                "filename": "example-2.jpg",
                "url": "https://followupboss.test/example-2.jpg",
            }
        ],
        "richObjects": ["https://example.com/objects/1"],
    }

    note = await service.add_inbox_app_note(
        2,
        CreateInboxAppNoteRequest(
            external_conversation_id="conv-123",
            body="An example note.",
            user=InboxAppNoteUserRequest(id=1),
        ),
    )
    assert note.id == 6
    assert client.calls[7].path == "/inboxApps/2/note"
    assert client.calls[7].json_body == {
        "externalConversationId": "conv-123",
        "body": "An example note.",
        "user": {"id": 1},
    }

    conversation = await service.update_inbox_app_conversation(
        2,
        "conv-123",
        UpdateInboxAppConversationRequest(
            subject="A Conversation Subject",
            archived=False,
            person=InboxAppConversationPersonRequest(id=1),
        ),
    )
    assert conversation.external_conversation_id == "conv-123"
    assert client.calls[8].path == "/inboxApps/2/conversations/conv-123"
    assert client.calls[8].json_body == {
        "subject": "A Conversation Subject",
        "archived": False,
        "person": {"id": 1},
    }

    updated_message = await service.update_inbox_app_message(
        2,
        UpdateInboxAppMessageRequest(
            id=5,
            external_message_id="msg-124",
            delivery_status="Delivered",
        ),
    )
    assert updated_message.id == 7
    assert client.calls[9].path == "/inboxApps/2/message"
    assert client.calls[9].json_body == {
        "deliveryStatus": "Delivered",
        "externalMessageId": "msg-124",
        "id": 5,
    }

    invalid_service = InboxAppsService(StubClient([[], {"inboxApps": {}}, {}, [], [], [], []]))
    with pytest.raises(ValueError, match="Unexpected inbox app installations response"):
        await invalid_service.list_inbox_app_installations(9)
    with pytest.raises(ValueError, match="Unexpected inbox app installations response"):
        await invalid_service.list_inbox_app_installations(9)
    with pytest.raises(ValueError, match="Unexpected inbox app participants response"):
        await invalid_service.list_inbox_app_participants(2, "conv-123")
    with pytest.raises(ValueError, match="Unexpected inbox app message response"):
        await invalid_service.add_inbox_app_message(
            2,
            CreateInboxAppMessageRequest(
                external_conversation_id="conv-123",
                external_message_id="msg-123",
                message="An example message.",
                is_incoming=True,
                sender=InboxAppMessageSenderRequest(personId=1),
            ),
        )
    with pytest.raises(ValueError, match="Unexpected inbox app note response"):
        await invalid_service.add_inbox_app_note(
            2,
            CreateInboxAppNoteRequest(
                external_conversation_id="conv-123",
                body="An example note.",
                user=InboxAppNoteUserRequest(id=1),
            ),
        )
    with pytest.raises(ValueError, match="Unexpected inbox app conversation response"):
        await invalid_service.update_inbox_app_conversation(
            2,
            "conv-123",
            UpdateInboxAppConversationRequest(subject="A Conversation Subject"),
        )
    with pytest.raises(ValueError, match="Unexpected inbox app message response"):
        await invalid_service.update_inbox_app_message(
            2,
            UpdateInboxAppMessageRequest(id=5, external_message_id="msg-124"),
        )

    with pytest.raises(
        ValidationError,
        match="At least one inbox app participant identity field must be provided",
    ):
        CreateInboxAppParticipantRequest()
    with pytest.raises(
        ValidationError,
        match="At least one inbox app person reference field must be provided",
    ):
        InboxAppConversationPersonRequest()
    with pytest.raises(
        ValidationError,
        match="At least one inbox app owner field must be provided",
    ):
        InboxAppConversationOwnerRequest()
    with pytest.raises(
        ValidationError,
        match="At least one inbox app note user field must be provided",
    ):
        InboxAppNoteUserRequest()
    with pytest.raises(
        ValidationError,
        match="At least one inbox app sender field must be provided",
    ):
        InboxAppMessageSenderRequest()
    with pytest.raises(
        ValidationError,
        match="At least one inbox app conversation field must be provided",
    ):
        UpdateInboxAppConversationRequest()
    with pytest.raises(
        ValidationError,
        match="Either an inbox app message id or external_message_id must be provided",
    ):
        UpdateInboxAppMessageRequest(delivery_status="Delivered")
    with pytest.raises(
        ValidationError,
        match="Update inbox app message requests must include a mutation field",
    ):
        UpdateInboxAppMessageRequest(external_message_id="msg-124")


@pytest.mark.asyncio
async def test_team_inboxes_service() -> None:
    """Team inboxes service should map payloads correctly."""
    client = StubClient(
        [
            {
                "_metadata": {"limit": 10, "offset": 0, "total": 2},
                "teamInboxes": [
                    {
                        "id": 123,
                        "name": "My Team Inbox",
                        "users": [
                            {
                                "id": 111,
                                "name": "User Name",
                                "firstName": "User",
                                "lastName": "Name",
                            }
                        ],
                    }
                ],
            }
        ]
    )
    service = TeamInboxesService(client)

    team_inboxes_page = await service.list_team_inboxes(TeamInboxListRequest())
    assert team_inboxes_page.items[0].name == "My Team Inbox"
    assert team_inboxes_page.items[0].users[0].first_name == "User"
    assert client.calls[0].path == "/teamInboxes"


@pytest.mark.asyncio
async def test_timeframes_service() -> None:
    """Timeframes service should map payloads correctly."""
    client = StubClient(
        [
            {
                "_metadata": {"collection": "timeframes", "offset": 0, "limit": 10, "total": 5},
                "timeframes": [
                    {"id": 1, "timeframe": "0-3 Months"},
                    {"id": 2, "timeframe": "3-6 Months"},
                ],
            }
        ]
    )
    service = TimeframesService(client)

    timeframes_page = await service.list_timeframes(TimeframeListRequest())
    assert timeframes_page.items[0].timeframe == "0-3 Months"
    assert timeframes_page.items[1].id == 2
    assert client.calls[0].path == "/timeframes"

    invalid_service = TimeframesService(StubClient([[], {"timeframes": {}}]))
    with pytest.raises(ValueError, match="Unexpected timeframes response"):
        await invalid_service.list_timeframes()
    with pytest.raises(ValueError, match="Unexpected timeframes response"):
        await invalid_service.list_timeframes()


@pytest.mark.asyncio
async def test_threaded_replies_service() -> None:
    """Threaded replies service should map payloads correctly."""
    client = StubClient(
        [
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
            }
        ]
    )
    service = ThreadedRepliesService(client)

    threaded_reply = await service.get_threaded_reply(1)
    assert isinstance(threaded_reply, ThreadedReplyRecord)
    assert threaded_reply.body == "Hello world part 2"
    assert threaded_reply.created_by_id == 1
    assert threaded_reply.reactions is not None
    assert threaded_reply.model_dump(by_alias=True, exclude_none=True)["reactions"]["id"] == 1363
    assert client.calls[0].path == "/threadedReplies/1"

    with pytest.raises(ValueError, match="Unexpected threaded replies response"):
        await ThreadedRepliesService(StubClient([[]])).get_threaded_reply(1)


@pytest.mark.asyncio
async def test_text_messages_service() -> None:
    """Text messages service should map list, lookup, and create behavior correctly."""
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
            {
                "id": 3,
                "personId": 99,
                "message": "Logged externally",
                "fromNumber": "555-0001",
                "toNumber": "555-0002",
                "userName": "Data",
                "isIncoming": False,
                "externalLabel": "External SMS",
                "externalUrl": "https://example.com/sms/3",
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

    created = await service.create_text_message(
        CreateTextMessageRequest(
            person_id=99,
            message="Logged externally",
            to_number="555-0002",
            from_number="555-0001",
            is_incoming=False,
            external_label="External SMS",
            external_url="https://example.com/sms/3",
        )
    )
    assert created.id == 3
    assert client.calls[2].json_body == {
        "personId": 99,
        "message": "Logged externally",
        "toNumber": "555-0002",
        "fromNumber": "555-0001",
        "isIncoming": False,
        "externalLabel": "External SMS",
        "externalUrl": "https://example.com/sms/3",
    }


@pytest.mark.asyncio
async def test_text_message_templates_service() -> None:
    """Text message templates service should map queries, bodies, merge, and delete behavior."""
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
            {"mergedTemplate": "Hey Bob, Alice and Carol..."},
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

    merged = await service.merge_text_message_template(
        MergeTextMessageTemplateRequest.model_validate(
            {
                "template_id": 31,
                "person_id": 1213,
                "recipients": {
                    "to": [
                        {"name": "Bob Alvarez", "phone": "+14075558075"},
                        {"name": "Alice Alvarez", "phone": "+14075558710"},
                    ]
                },
            }
        )
    )
    assert merged.merged_template == "Hey Bob, Alice and Carol..."
    assert client.calls[5].path == "/textMessageTemplates/merge"
    assert client.calls[5].json_body == {
        "templateId": 31,
        "personId": 1213,
        "recipients": {
            "to": [
                {"name": "Bob Alvarez", "phone": "+14075558075"},
                {"name": "Alice Alvarez", "phone": "+14075558710"},
            ]
        },
    }


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
    """Templates service should map queries, bodies, merge, and delete behavior correctly."""
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
            {
                "id": 6,
                "name": "I am here to help",
                "subject": "Your property inquiry from Zillow",
                "body": "Hi Bob, I am here to help, ...",
                "isShared": True,
                "isEditable": True,
                "isDeletable": True,
            },
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

    merged = await service.merge_template(
        MergeTemplateRequest.model_validate(
            {
                "template_id": 31,
                "merge_person_id": 1213,
                "recipients": {
                    "to": [
                        {"name": "Bob Alvarez", "email": "bob@example.com"},
                        {"name": "Alice Alvarez", "email": "alice@example.com"},
                    ]
                },
            }
        )
    )
    assert merged.id == 6
    assert client.calls[5].path == "/templates/merge"
    assert client.calls[5].json_body == {
        "templateId": 31,
        "mergePersonId": 1213,
        "recipients": {
            "to": [
                {"name": "Bob Alvarez", "email": "bob@example.com"},
                {"name": "Alice Alvarez", "email": "alice@example.com"},
            ]
        },
    }


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
                "notifyBy": "Email only",
                "features": ["calling", "link-tracking"],
            },
            {},
            {"id": 7, "body": "created"},
            {"id": 8, "body": "loaded"},
            {"id": 9, "body": "updated"},
            {},
            {
                "_metadata": {"limit": 10, "offset": 0, "total": 1},
                "webhooks": [{"id": 10, "event": "peopleCreated", "url": "https://example.com"}],
            },
            {"id": 11, "event": "peopleCreated", "url": "https://example.com"},
            {
                "id": "db36048a6b06d80e7f9d3440233ae915",
                "eventId": "4b762cb3-d7b6-4cf4-b7fb-fbd8cb0dfe11",
                "eventCreated": "2016-12-12T18:36:26Z",
                "event": "peopleUpdated",
                "resourceIds": [99],
                "uri": "https://api.followupboss.com/v1/people/99",
                "data": {"changed": ["tags"]},
            },
            {
                "id": 12,
                "event": "peopleUpdated",
                "status": "Disabled",
                "url": "https://example.com",
            },
            {},
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
    current_user = await users_service.get_me()
    assert isinstance(current_user, CurrentUserRecord)
    assert current_user.api_key == "secret-api-key"
    assert current_user.algolia_key == "secret-algolia-key"
    assert current_user.intercom_settings is not None
    assert current_user.intercom_settings.user_hash == "secret-hash"
    assert current_user.connected_email is not None
    assert current_user.connected_email.oauth_provider == "google"
    sanitized_user = CurrentUserRecord(id=2, intercomSettings=IntercomSettingsRecord(app_id="abc"))
    sanitized_me = sanitized_user.redacted_for_mcp()
    assert sanitized_me.intercom_settings is not None
    assert sanitized_me.intercom_settings.user_hash is None

    await people_service.delete_person(77)
    assert client.calls[6].path == "/people/77"

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
    assert client.calls[7].json_body == {"body": "created", "personId": 1}

    assert (await notes_service.get_note(8)).id == 8
    assert (await notes_service.update_note(9, UpdateNoteRequest(body="updated"))).id == 9
    await notes_service.delete_note(10)

    webhooks_page = await webhooks_service.list_webhooks(WebhookListRequest(event="peopleCreated"))
    assert webhooks_page.items[0].id == 10
    assert client.calls[11].params == {"event": "peopleCreated"}
    assert (
        await webhooks_service.create_webhook(
            CreateWebhookRequest(event="peopleCreated", url="https://example.com")
        )
    ).id == 11
    webhook_event = await webhooks_service.get_webhook_event("db36048a6b06d80e7f9d3440233ae915")
    assert isinstance(webhook_event, WebhookEventRecord)
    assert webhook_event.event_id == "4b762cb3-d7b6-4cf4-b7fb-fbd8cb0dfe11"
    assert webhook_event.resource_ids == [99]
    assert webhook_event.data == {"changed": ["tags"]}
    updated_webhook = await webhooks_service.update_webhook(
        12,
        UpdateWebhookRequest(status="Disabled"),
    )
    assert updated_webhook.status == "Disabled"
    await webhooks_service.delete_webhook(13)
    await users_service.delete_user(14, DeleteUserRequest(assign_to=5))
    assert client.calls[16].path == "/users/14"
    assert client.calls[16].params == {"assignTo": "5"}

    with pytest.raises(ValueError, match="Unexpected current user response"):
        await UsersService(StubClient([[]])).get_me()

    with pytest.raises(ValueError, match="Unexpected webhook events response"):
        await WebhooksService(StubClient([[]])).get_webhook_event("event-1")


@pytest.mark.asyncio
async def test_send_event_accepts_camel_case_person_input() -> None:
    """Event creation should accept camelCase keys inside nested person payloads."""
    client = StubClient([{"id": 14, "personId": 99, "type": "Inquiry"}])
    service = EventsService(client)

    sent = await service.send_event(
        CreateEventRequest.model_validate(
            {
                "source": "Portal",
                "system": "Portal",
                "type": "Inquiry",
                "person": {
                    "firstName": "Deanna",
                    "lastName": "Troi",
                    "emails": [{"value": "deanna@example.com", "type": "work"}],
                },
            }
        )
    )

    assert sent.id == 14
    assert client.calls[0].json_body == {
        "source": "Portal",
        "system": "Portal",
        "type": "Inquiry",
        "person": {
            "firstName": "Deanna",
            "lastName": "Troi",
            "emails": [{"value": "deanna@example.com", "type": "work"}],
        },
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("service_factory", "payload", "exception_type"),
    [
        (
            lambda client: CustomFieldsService(client),
            {"customfields": {}},
            FollowUpBossValidationError,
        ),
        (lambda client: AutomationsService(client), [], ValueError),
        (lambda client: AutomationsService(client), {"automations": {}}, ValueError),
        (lambda client: AutomationPeopleService(client), [], ValueError),
        (
            lambda client: AutomationPeopleService(client),
            {"automationsPeople": {}},
            ValueError,
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
        (lambda client: ActionPlansService(client), [], ValueError),
        (lambda client: ActionPlansService(client), {"actionPlans": {}}, ValueError),
        (lambda client: GroupsService(client), [], ValueError),
        (lambda client: GroupsService(client), {"groups": {}}, ValueError),
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
        (lambda client: TeamInboxesService(client), [], ValueError),
        (lambda client: TeamInboxesService(client), {"teamInboxes": {}}, ValueError),
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
    elif isinstance(service, AutomationsService):
        with pytest.raises(exception_type):
            await service.list_automations()
    elif isinstance(service, AutomationPeopleService):
        with pytest.raises(exception_type):
            await service.list_automation_people()
    elif isinstance(service, AppointmentOutcomesService):
        with pytest.raises(exception_type):
            await service.list_appointment_outcomes()
    elif isinstance(service, AppointmentTypesService):
        with pytest.raises(exception_type):
            await service.list_appointment_types()
    elif isinstance(service, ActionPlansService):
        with pytest.raises(exception_type):
            await service.list_action_plans()
    elif isinstance(service, GroupsService):
        with pytest.raises(exception_type):
            await service.list_groups()
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
    elif isinstance(service, TeamInboxesService):
        with pytest.raises(exception_type):
            await service.list_team_inboxes()
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
