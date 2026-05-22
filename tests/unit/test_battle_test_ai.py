"""Tests for AI-backed MCP battle-test selectors."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

import httpx
import pytest

from followupboss_mcp.battle_test_ai import (
    AnthropicBattleTestModelSelector,
    BattleTestAiToolSpec,
    BattleTestModelDecision,
    BattleTestModelSelector,
    OpenAiBattleTestModelSelector,
    _anthropic_decision_from_response,
    _conversation_prompt,
    _json_value,
    _openai_decision_from_response,
    battle_test_ai_selectors_from_env,
    battle_test_selection_instructions,
    capture_ai_selected_conversation_transcript,
    capture_ai_selected_multi_call_transcript,
    capture_ai_selected_transcript,
    load_env_file,
    read_only_battle_test_ai_tool_specs,
    run_ai_model_profile_battle_tests,
    run_ai_model_profile_conversation_battle_tests,
)
from followupboss_mcp.battle_tests import (
    BattleTestConversationKind,
    BattleTestModelProfile,
    BattleTestModelProvider,
    BattleTestScenario,
    BattleTestTranscript,
    ReadOnlyBattleTestOracle,
    battle_test_model_profile_by_id,
    mcp_tool_result_to_json,
    read_only_battle_test_conversations,
    scenario_by_id,
)
from followupboss_mcp.models.appointments import AppointmentListRequest, AppointmentRecord
from followupboss_mcp.models.calls import CallListRequest, CallRecord
from followupboss_mcp.models.common import JsonValue
from followupboss_mcp.models.email_marketing import EmailEventListRequest, EmailEventRecord
from followupboss_mcp.models.events import EventRecord, EventSearchRequest
from followupboss_mcp.models.identity import IdentityResponse
from followupboss_mcp.models.notes import NoteRecord
from followupboss_mcp.models.people import (
    PeopleSearchRequest,
    PersonDuplicateCheckRecord,
    PersonDuplicateCheckRequest,
    PersonRecord,
    UnclaimedPeopleListRequest,
)
from followupboss_mcp.models.smart_lists import SmartListListRequest, SmartListRecord
from followupboss_mcp.models.tasks import TaskListRequest, TaskRecord
from followupboss_mcp.models.templates import TemplateListRequest, TemplateRecord
from followupboss_mcp.models.text_messages import (
    TextMessageListRequest,
    TextMessageRecord,
    TextMessageTemplateListRequest,
    TextMessageTemplateRecord,
)
from followupboss_mcp.pagination import PageResult, PaginationMetadata


@dataclass
class StubAiSelector:
    """Selector test double returning queued decisions."""

    decisions: list[BattleTestModelDecision | Exception]

    async def select_tool(
        self,
        *,
        profile: BattleTestModelProfile,
        scenario: BattleTestScenario,
        prompt: str,
        tools: tuple[BattleTestAiToolSpec, ...],
    ) -> BattleTestModelDecision:
        """Return the next queued decision."""
        decision = self.decisions.pop(0)
        if isinstance(decision, Exception):
            raise decision
        return decision


@dataclass
class StubMultiAiSelector:
    """Selector test double returning queued decision batches."""

    decision_batches: list[tuple[BattleTestModelDecision, ...]]
    prompts: list[str] = field(default_factory=list)

    async def select_tool(
        self,
        *,
        profile: BattleTestModelProfile,
        scenario: BattleTestScenario,
        prompt: str,
        tools: tuple[BattleTestAiToolSpec, ...],
    ) -> BattleTestModelDecision:
        """Return the first decision from the next queued batch."""
        return (
            await self.select_tools(profile=profile, scenario=scenario, prompt=prompt, tools=tools)
        )[0]

    async def select_tools(
        self,
        *,
        profile: BattleTestModelProfile,
        scenario: BattleTestScenario,
        prompt: str,
        tools: tuple[BattleTestAiToolSpec, ...],
    ) -> tuple[BattleTestModelDecision, ...]:
        """Return the next queued decision batch."""
        self.prompts.append(prompt)
        return self.decision_batches.pop(0)


@dataclass
class StubMcpClient:
    """MCP client test double returning queued results."""

    results: list[object]
    calls: list[tuple[str, object]] = field(default_factory=list)

    async def call_tool(self, name: str, arguments: object | None = None) -> object:
        """Record the call and return the next queued result."""
        self.calls.append((name, arguments))
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


@dataclass
class StubIdentityService:
    """Identity service test double."""

    async def get_identity(self) -> IdentityResponse:
        """Return a stable authenticated user."""
        return IdentityResponse(id=7)


@dataclass
class StubPeopleService:
    """People service test double."""

    async def get_person(
        self,
        person_id: int,
        request: object | None = None,
    ) -> PersonRecord:
        """Return a person by ID."""
        del request
        return PersonRecord.model_validate({"id": person_id})

    async def search_people(
        self, request: PeopleSearchRequest | None = None
    ) -> PageResult[PersonRecord]:
        """Return one latest lead."""
        metadata = PaginationMetadata(
            count=1,
            limit=1,
            next_token=None,
            next_link=None,
            offset=0,
            total=1,
        )
        return PageResult(
            items=[PersonRecord.model_validate({"id": 42, "assignedUserId": 7})],
            metadata=metadata,
        )

    async def check_duplicate_person(
        self, request: PersonDuplicateCheckRequest
    ) -> PersonDuplicateCheckRecord:
        """Return a duplicate-check miss."""
        return PersonDuplicateCheckRecord(found=False)

    async def list_unclaimed_people(
        self, request: UnclaimedPeopleListRequest | None = None
    ) -> PageResult[PersonRecord]:
        """Return no unclaimed people."""
        return _empty_page()


@dataclass
class StubTasksService:
    """Tasks service test double."""

    async def list_tasks(self, request: TaskListRequest | None = None) -> PageResult[TaskRecord]:
        """Return no tasks."""
        metadata = PaginationMetadata(
            count=0,
            limit=0,
            next_token=None,
            next_link=None,
            offset=0,
            total=0,
        )
        return PageResult(items=[], metadata=metadata)


def _empty_page() -> PageResult[Any]:
    """Return an empty page result for expanded service doubles."""
    metadata = PaginationMetadata(
        count=0,
        limit=0,
        next_token=None,
        next_link=None,
        offset=0,
        total=0,
    )
    return PageResult(items=[], metadata=metadata)


@dataclass
class StubSmartListsService:
    """Smart-list service test double."""

    async def list_smart_lists(
        self, request: SmartListListRequest | None = None
    ) -> PageResult[SmartListRecord]:
        """Return no smart lists."""
        return _empty_page()


@dataclass
class StubAppointmentsService:
    """Appointments service test double."""

    async def list_appointments(
        self, request: AppointmentListRequest | None = None
    ) -> PageResult[AppointmentRecord]:
        """Return no appointments."""
        return _empty_page()


@dataclass
class StubCallsService:
    """Calls service test double."""

    async def list_calls(self, request: CallListRequest | None = None) -> PageResult[CallRecord]:
        """Return no calls."""
        return _empty_page()


@dataclass
class StubTextMessagesService:
    """Text-message service test double."""

    async def list_text_messages(
        self, request: TextMessageListRequest | None = None
    ) -> PageResult[TextMessageRecord]:
        """Return no text messages."""
        return _empty_page()


@dataclass
class StubEmailEventsService:
    """Email-event service test double."""

    async def list_email_events(
        self,
        request: EmailEventListRequest | None = None,
    ) -> PageResult[EmailEventRecord]:
        """Return no email events."""
        return _empty_page()


@dataclass
class StubEventsService:
    """Event service test double."""

    async def search_events(
        self,
        request: EventSearchRequest | None = None,
    ) -> PageResult[EventRecord]:
        """Return no events."""
        return _empty_page()


@dataclass
class StubTemplatesService:
    """Templates service test double."""

    async def list_templates(
        self, request: TemplateListRequest | None = None
    ) -> PageResult[TemplateRecord]:
        """Return no templates."""
        return _empty_page()


@dataclass
class StubTextMessageTemplatesService:
    """Text-message-template service test double."""

    async def list_text_message_templates(
        self, request: TextMessageTemplateListRequest | None = None
    ) -> PageResult[TextMessageTemplateRecord]:
        """Return no text-message templates."""
        return _empty_page()


@dataclass
class StubNotesService:
    """Notes service test double."""

    async def get_note(self, note_id: int) -> NoteRecord:
        """Return a note with the requested ID."""
        return NoteRecord.model_validate({"id": note_id})


@dataclass
class StubBattleTestServices:
    """Read-only battle-test service bundle test double."""

    identity: StubIdentityService = field(default_factory=StubIdentityService)
    people: StubPeopleService = field(default_factory=StubPeopleService)
    tasks: StubTasksService = field(default_factory=StubTasksService)
    smart_lists: StubSmartListsService = field(default_factory=StubSmartListsService)
    appointments: StubAppointmentsService = field(default_factory=StubAppointmentsService)
    calls: StubCallsService = field(default_factory=StubCallsService)
    text_messages: StubTextMessagesService = field(default_factory=StubTextMessagesService)
    email_marketing: StubEmailEventsService = field(default_factory=StubEmailEventsService)
    events: StubEventsService = field(default_factory=StubEventsService)
    templates: StubTemplatesService = field(default_factory=StubTemplatesService)
    text_message_templates: StubTextMessageTemplatesService = field(
        default_factory=StubTextMessageTemplatesService
    )
    notes: StubNotesService = field(default_factory=StubNotesService)


@pytest.mark.asyncio
async def test_openai_selector_sends_low_reasoning_and_parses_tool_call() -> None:
    requests: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer openai-key"
        payload = cast(dict[str, object], json.loads(request.content))
        requests.append(payload)
        return httpx.Response(
            200,
            json={
                "output_text": "Using the latest lead helper.",
                "output": [
                    {
                        "type": "function_call",
                        "name": "followupboss_get_latest_lead",
                        "arguments": '{"fields":["id"]}',
                    }
                ],
            },
        )

    selector = OpenAiBattleTestModelSelector(
        "openai-key",
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    scenario = scenario_by_id("BT-READ-001")

    decision = await selector.select_tool(
        profile=battle_test_model_profile_by_id("gpt-5.5-low-reasoning"),
        scenario=scenario,
        prompt=scenario.prompt_variants[0],
        tools=read_only_battle_test_ai_tool_specs(),
    )

    assert requests[0]["model"] == "gpt-5.5"
    assert requests[0]["reasoning"] == {"effort": "low"}
    assert requests[0]["tool_choice"] == "required"
    assert decision.selected_tool == "followupboss_get_latest_lead"
    assert decision.arguments == {"fields": ["id"]}
    assert decision.assistant_message == "Using the latest lead helper."
    await selector.aclose()


def test_read_only_tool_specs_constrain_owned_task_fields() -> None:
    specs = {tool.name: tool for tool in read_only_battle_test_ai_tool_specs()}
    overdue_schema = cast(
        dict[str, object],
        specs["followupboss_list_my_overdue_tasks"].input_schema["properties"],
    )
    today_schema = cast(
        dict[str, object],
        specs["followupboss_list_my_tasks_due_today"].input_schema["properties"],
    )
    upcoming_schema = cast(
        dict[str, object],
        specs["followupboss_list_my_upcoming_tasks"].input_schema["properties"],
    )

    overdue_fields = overdue_schema["fields"]
    today_fields = today_schema["fields"]
    upcoming_fields = upcoming_schema["fields"]

    assert overdue_fields == today_fields
    assert overdue_fields == upcoming_fields
    assert overdue_fields == {
        "type": "array",
        "description": "Optional task response fields to request.",
        "items": {
            "type": "string",
            "enum": [
                "id",
                "name",
                "dueDate",
                "assignedUserId",
                "personId",
                "isCompleted",
                "type",
            ],
        },
    }


def test_read_only_tool_specs_constrain_latest_lead_fields() -> None:
    specs = {tool.name: tool for tool in read_only_battle_test_ai_tool_specs()}
    latest_lead_schema = cast(
        dict[str, object],
        specs["followupboss_get_latest_lead"].input_schema["properties"],
    )

    assert latest_lead_schema["fields"] == {
        "type": "array",
        "description": "Optional latest-lead person response fields to request.",
        "items": {
            "type": "string",
            "enum": [
                "id",
                "name",
                "firstName",
                "lastName",
                "created",
                "assignedUserId",
                "stage",
                "source",
                "lastActivity",
            ],
        },
    }


def test_read_only_tool_specs_steer_notes_to_unsupported_sentinel() -> None:
    specs = {tool.name: tool for tool in read_only_battle_test_ai_tool_specs()}

    assert "notes by person" in specs["followupboss_search_events"].description
    assert "battle_test_explain_unsupported" in specs["followupboss_search_events"].description
    assert "notes by lead" in specs["followupboss_get_note"].description
    assert "battle_test_explain_unsupported" in specs["followupboss_get_note"].description
    assert (
        "notes by person, lead, or contact" in specs["battle_test_explain_unsupported"].description
    )
    assert "multi-action prompts" in specs["battle_test_explain_unsupported"].description
    assert "whether notes can be searched" in specs["battle_test_explain_unsupported"].description


def test_read_only_tool_specs_include_expanded_read_surfaces() -> None:
    specs = {tool.name: tool for tool in read_only_battle_test_ai_tool_specs()}

    for name in (
        "followupboss_search_people_in_smart_list",
        "followupboss_list_smart_lists",
        "followupboss_check_duplicate_person",
        "followupboss_list_unclaimed_people",
        "followupboss_list_person_activity",
        "followupboss_list_appointments",
        "followupboss_list_calls",
        "followupboss_list_text_messages",
        "followupboss_list_email_events",
        "followupboss_list_templates",
        "followupboss_list_text_message_templates",
    ):
        assert name in specs
        assert specs[name].input_schema["additionalProperties"] is False

    duplicate_properties = cast(
        dict[str, object],
        specs["followupboss_check_duplicate_person"].input_schema["properties"],
    )
    people_properties = cast(
        dict[str, object],
        specs["followupboss_search_people"].input_schema["properties"],
    )
    helper_properties = cast(
        dict[str, object],
        specs["followupboss_search_people_in_smart_list"].input_schema["properties"],
    )
    activity_properties = cast(
        dict[str, object],
        specs["followupboss_list_person_activity"].input_schema["properties"],
    )

    assert set(duplicate_properties) == {"email", "phone"}
    assert "smart_list_id" in people_properties
    assert "Do not use this for named smart-list" in (
        specs["followupboss_search_people"].description
    )
    assert {"smart_list_name", "source", "stage", "mine", "assigned_user_id"}.issubset(
        helper_properties
    )
    assert specs["followupboss_search_people_in_smart_list"].input_schema["required"] == [
        "smart_list_name",
        "source",
        "mine",
    ]
    assert "Zillow leads in Eligible For Transfer" in (
        specs["followupboss_search_people_in_smart_list"].description
    )
    assert "source='Zillow'" in specs["followupboss_search_people_in_smart_list"].description
    assert "defaults to mine=true" in specs["followupboss_search_people_in_smart_list"].description
    assert cast(
        dict[str, object],
        specs["followupboss_search_people_in_smart_list"].input_schema["properties"],
    )["mine"] == {
        "type": "boolean",
        "default": True,
        "description": (
            "True for I/me/my follow-up requests; false only when explicitly account-wide/everyone."
        ),
    }
    assert specs["followupboss_list_person_activity"].input_schema["required"] == ["person_id"]
    assert {"person_id", "include_calls", "include_text_messages"}.issubset(activity_properties)
    assert "clarify instead of using broad activity list tools" in (
        specs["followupboss_list_person_activity"].description
    )


def test_selection_instructions_explain_unsupported_note_search() -> None:
    instructions = battle_test_selection_instructions()

    assert "Do not answer with plain text only" in instructions
    assert "mixes supported actions with unsupported actions" in instructions
    assert (
        "followupboss_get_latest_lead followed by battle_test_explain_unsupported" in instructions
    )
    assert "notes by person, lead, or contact" in instructions
    assert "explicit note ID" in instructions
    assert "battle_test_explain_unsupported" in instructions
    assert "late, overdue, past due, behind" in instructions
    assert "followupboss_list_my_overdue_tasks" in instructions
    assert "today, due today, or not miss today" in instructions
    assert "followupboss_list_my_tasks_due_today" in instructions
    assert "coming up, upcoming, later, after today" in instructions
    assert "followupboss_list_my_upcoming_tasks" in instructions
    assert "followupboss_list_smart_lists" in instructions
    assert "Use followupboss_search_people_in_smart_list" in instructions
    assert "When the prompt says Zillow leads, include source='Zillow'" in instructions
    assert "set mine=true" in instructions
    assert "Set mine=false only when the prompt explicitly asks for everyone" in instructions
    assert "pass assigned_user_id only if the user ID is already known" in instructions
    assert "came from Zillow" in instructions
    assert "boundary for Zillow follow-ups" in instructions
    assert "absent from that smart-list-scoped tool result" in instructions
    assert "smart_list_name='Eligible For Transfer'" in instructions
    assert "call battle_test_clarify and ask which smart list" in instructions
    assert "Never default a bare Zillow-leads prompt" in instructions
    assert "Use followupboss_list_person_activity for communication history" in instructions
    assert "without a resolved person_id, call battle_test_clarify" in instructions
    assert "do not use broad calls, text messages, email events, events" in instructions
    assert (
        "followupboss_check_duplicate_person only when an email or phone is provided"
        in instructions
    )
    assert "route the current user turn independently" in instructions


def test_openai_text_only_unsupported_explanation_is_normalized() -> None:
    scenario = scenario_by_id("BT-READ-005")

    decision = _openai_decision_from_response(
        scenario=scenario,
        prompt=scenario.prompt_variants[0],
        payload={
            "output_text": "I can't search notes by lead because this MCP API does not expose it.",
            "output": [],
        },
    )

    assert decision.selected_tool is None
    assert decision.unsupported_explained is True
    assert "can't search notes" in (decision.assistant_message or "")


def test_anthropic_text_only_unsupported_explanation_is_normalized() -> None:
    scenario = scenario_by_id("BT-READ-005")

    decision = _anthropic_decision_from_response(
        scenario=scenario,
        prompt=scenario.prompt_variants[0],
        payload={
            "content": [
                {
                    "type": "text",
                    "text": (
                        "The Follow Up Boss API does not support searching note history by lead."
                    ),
                }
            ]
        },
    )

    assert decision.selected_tool is None
    assert decision.unsupported_explained is True
    assert "note history" in (decision.assistant_message or "")


@pytest.mark.asyncio
async def test_openai_selector_returns_text_when_no_tool_call() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"output_text": "I need more context.", "output": []})

    selector = OpenAiBattleTestModelSelector(
        "openai-key",
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    scenario = scenario_by_id("BT-READ-004")

    decision = await selector.select_tool(
        profile=BattleTestModelProfile(
            id="gpt-no-reasoning",
            provider=BattleTestModelProvider.OPENAI,
            model="gpt-5.5",
            display_name="GPT without reasoning setting",
        ),
        scenario=scenario,
        prompt=scenario.prompt_variants[0],
        tools=read_only_battle_test_ai_tool_specs(),
    )

    assert decision == BattleTestModelDecision(
        scenario_id="BT-READ-004",
        prompt=scenario.prompt_variants[0],
        assistant_message="I need more context.",
    )
    await selector.aclose()


@pytest.mark.asyncio
async def test_openai_selector_parses_clarification_sentinel_without_message() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "output_text": "Which lead do you mean?",
                "output": [
                    {
                        "type": "function_call",
                        "name": "battle_test_clarify",
                    }
                ],
            },
        )

    selector = OpenAiBattleTestModelSelector(
        "openai-key",
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    scenario = scenario_by_id("BT-READ-004")

    decision = await selector.select_tool(
        profile=battle_test_model_profile_by_id("gpt-5.5-low-reasoning"),
        scenario=scenario,
        prompt=scenario.prompt_variants[0],
        tools=read_only_battle_test_ai_tool_specs(),
    )

    assert decision.selected_tool is None
    assert decision.clarified is True
    assert decision.assistant_message == "Which lead do you mean?"
    await selector.aclose()


@pytest.mark.asyncio
async def test_openai_selector_parses_multiple_function_calls_in_order() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "output_text": "I'll check both.",
                "output": [
                    {
                        "type": "function_call",
                        "name": "followupboss_get_latest_lead",
                        "arguments": '{"fields":["id"]}',
                    },
                    {
                        "type": "function_call",
                        "name": "followupboss_list_my_overdue_tasks",
                        "arguments": '{"limit":5}',
                    },
                ],
            },
        )

    selector = OpenAiBattleTestModelSelector(
        "openai-key",
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    scenario = scenario_by_id("BT-READ-001")

    decisions = await selector.select_tools(
        profile=battle_test_model_profile_by_id("gpt-5.5-low-reasoning"),
        scenario=scenario,
        prompt="Show my latest lead and what I am late on.",
        tools=read_only_battle_test_ai_tool_specs(),
    )

    assert [decision.selected_tool for decision in decisions] == [
        "followupboss_get_latest_lead",
        "followupboss_list_my_overdue_tasks",
    ]
    assert decisions[0].arguments == {"fields": ["id"]}
    assert decisions[1].arguments == {"limit": 5}
    await selector.aclose()


def test_openai_single_decision_parser_preserves_existing_private_helper() -> None:
    scenario = scenario_by_id("BT-READ-001")

    decision = _openai_decision_from_response(
        scenario=scenario,
        prompt="Latest lead?",
        payload={
            "output": [
                {
                    "type": "function_call",
                    "name": "followupboss_get_latest_lead",
                    "arguments": "{}",
                }
            ]
        },
    )

    assert decision.selected_tool == "followupboss_get_latest_lead"


@pytest.mark.asyncio
async def test_openai_selector_handles_unstructured_payload_and_non_object_response() -> None:
    responses = [
        httpx.Response(200, json={"output": "not-a-list"}),
        httpx.Response(200, json=[]),
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        return responses.pop(0)

    selector = OpenAiBattleTestModelSelector(
        "openai-key",
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    scenario = scenario_by_id("BT-READ-004")

    decision = await selector.select_tool(
        profile=battle_test_model_profile_by_id("gpt-5.5-low-reasoning"),
        scenario=scenario,
        prompt=scenario.prompt_variants[0],
        tools=read_only_battle_test_ai_tool_specs(),
    )

    assert decision.assistant_message is None
    with pytest.raises(ValueError, match="OpenAI route-selection response"):
        await selector.select_tool(
            profile=battle_test_model_profile_by_id("gpt-5.5-low-reasoning"),
            scenario=scenario,
            prompt=scenario.prompt_variants[0],
            tools=read_only_battle_test_ai_tool_specs(),
        )
    await selector.aclose()


@pytest.mark.asyncio
async def test_openai_selector_ignores_non_tool_output_items() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "output": [
                    "not-an-object",
                    {"type": "message", "content": []},
                    {"type": "function_call", "name": 123},
                ]
            },
        )

    selector = OpenAiBattleTestModelSelector(
        "openai-key",
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    scenario = scenario_by_id("BT-READ-004")

    decision = await selector.select_tool(
        profile=battle_test_model_profile_by_id("gpt-5.5-low-reasoning"),
        scenario=scenario,
        prompt=scenario.prompt_variants[0],
        tools=read_only_battle_test_ai_tool_specs(),
    )

    assert decision.selected_tool is None
    assert decision.assistant_message is None
    await selector.aclose()


@pytest.mark.asyncio
async def test_anthropic_selector_parses_unsupported_tool_use() -> None:
    requests: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["x-api-key"] == "anthropic-key"
        payload = cast(dict[str, object], json.loads(request.content))
        requests.append(payload)
        return httpx.Response(
            200,
            json={
                "content": [
                    {"type": "text", "text": "Notes cannot be searched by person ID."},
                    {
                        "type": "tool_use",
                        "name": "battle_test_explain_unsupported",
                        "input": {"message": "Note search by person ID is unsupported."},
                    },
                ]
            },
        )

    selector = AnthropicBattleTestModelSelector(
        "anthropic-key",
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    scenario = scenario_by_id("BT-READ-005")

    decision = await selector.select_tool(
        profile=battle_test_model_profile_by_id("sonnet-4.6"),
        scenario=scenario,
        prompt=scenario.prompt_variants[0],
        tools=read_only_battle_test_ai_tool_specs(),
    )

    assert requests[0]["model"] == "claude-sonnet-4-6"
    assert requests[0]["tool_choice"] == {"type": "any"}
    assert "reasoning" not in requests[0]
    assert decision.selected_tool is None
    assert decision.unsupported_explained is True
    assert decision.assistant_message == "Note search by person ID is unsupported."
    await selector.aclose()


@pytest.mark.asyncio
async def test_anthropic_selector_parses_multiple_tool_uses_in_order() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "content": [
                    {"type": "text", "text": "I'll check both."},
                    {
                        "type": "tool_use",
                        "name": "followupboss_list_my_tasks_due_today",
                        "input": {"limit": 3},
                    },
                    {
                        "type": "tool_use",
                        "name": "followupboss_list_my_upcoming_tasks",
                        "input": {"fields": ["id", "dueDate"]},
                    },
                ]
            },
        )

    selector = AnthropicBattleTestModelSelector(
        "anthropic-key",
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    scenario = scenario_by_id("BT-READ-003")

    decisions = await selector.select_tools(
        profile=battle_test_model_profile_by_id("sonnet-4.6"),
        scenario=scenario,
        prompt="Show today's tasks and upcoming tasks.",
        tools=read_only_battle_test_ai_tool_specs(),
    )

    assert [decision.selected_tool for decision in decisions] == [
        "followupboss_list_my_tasks_due_today",
        "followupboss_list_my_upcoming_tasks",
    ]
    assert decisions[0].arguments == {"limit": 3}
    assert decisions[1].arguments == {"fields": ["id", "dueDate"]}
    await selector.aclose()


def test_anthropic_single_decision_parser_preserves_existing_private_helper() -> None:
    scenario = scenario_by_id("BT-READ-003")

    decision = _anthropic_decision_from_response(
        scenario=scenario,
        prompt="Today?",
        payload={
            "content": [
                {
                    "type": "tool_use",
                    "name": "followupboss_list_my_tasks_due_today",
                    "input": {},
                }
            ]
        },
    )

    assert decision.selected_tool == "followupboss_list_my_tasks_due_today"


@pytest.mark.asyncio
async def test_anthropic_selector_returns_text_without_tool_use() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"content": [{"type": "text", "text": "I can explain instead."}]},
        )

    selector = AnthropicBattleTestModelSelector(
        "anthropic-key",
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    scenario = scenario_by_id("BT-READ-005")

    decision = await selector.select_tool(
        profile=battle_test_model_profile_by_id("sonnet-4.6"),
        scenario=scenario,
        prompt=scenario.prompt_variants[0],
        tools=read_only_battle_test_ai_tool_specs(),
    )

    assert decision.selected_tool is None
    assert decision.assistant_message == "I can explain instead."
    await selector.aclose()


@pytest.mark.asyncio
async def test_anthropic_selector_handles_bad_payload_shapes() -> None:
    responses = [
        httpx.Response(200, json={"content": "not-a-list"}),
        httpx.Response(200, json=[]),
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        return responses.pop(0)

    selector = AnthropicBattleTestModelSelector(
        "anthropic-key",
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    scenario = scenario_by_id("BT-READ-005")

    decision = await selector.select_tool(
        profile=battle_test_model_profile_by_id("sonnet-4.6"),
        scenario=scenario,
        prompt=scenario.prompt_variants[0],
        tools=read_only_battle_test_ai_tool_specs(),
    )

    assert decision.assistant_message is None
    with pytest.raises(ValueError, match="Anthropic route-selection response"):
        await selector.select_tool(
            profile=battle_test_model_profile_by_id("sonnet-4.6"),
            scenario=scenario,
            prompt=scenario.prompt_variants[0],
            tools=read_only_battle_test_ai_tool_specs(),
        )
    await selector.aclose()


@pytest.mark.asyncio
async def test_anthropic_selector_ignores_non_tool_content_items() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "content": [
                    "not-an-object",
                    {"type": "text", "text": 123},
                    {"type": "tool_use", "name": 123},
                ]
            },
        )

    selector = AnthropicBattleTestModelSelector(
        "anthropic-key",
        http_client=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )
    scenario = scenario_by_id("BT-READ-005")

    decision = await selector.select_tool(
        profile=battle_test_model_profile_by_id("sonnet-4.6"),
        scenario=scenario,
        prompt=scenario.prompt_variants[0],
        tools=read_only_battle_test_ai_tool_specs(),
    )

    assert decision.selected_tool is None
    assert decision.assistant_message is None
    await selector.aclose()


@pytest.mark.asyncio
async def test_capture_ai_selected_transcript_executes_real_tool() -> None:
    scenario = scenario_by_id("BT-READ-001")
    selector = StubAiSelector(
        decisions=[
            BattleTestModelDecision(
                scenario_id=scenario.id,
                prompt=scenario.prompt_variants[0],
                selected_tool="followupboss_get_latest_lead",
                arguments={"fields": ["id"]},
                assistant_message="Using latest lead.",
            )
        ]
    )
    client = StubMcpClient(results=[{"person": {"id": 42}}])

    transcript = await capture_ai_selected_transcript(
        selector=selector,
        profile=battle_test_model_profile_by_id("gpt-5.5-low-reasoning"),
        scenario=scenario,
        prompt=scenario.prompt_variants[0],
        mcp_client=client,
    )

    assert transcript == BattleTestTranscript(
        scenario_id=scenario.id,
        prompt=scenario.prompt_variants[0],
        selected_tool="followupboss_get_latest_lead",
        arguments={"fields": ["id"]},
        response={"person": {"id": 42}},
        assistant_message="Using latest lead.",
    )
    assert client.calls == [("followupboss_get_latest_lead", {"fields": ["id"]})]


@pytest.mark.asyncio
async def test_capture_ai_selected_transcript_records_tool_errors() -> None:
    scenario = scenario_by_id("BT-READ-002")
    selector = StubAiSelector(
        decisions=[
            BattleTestModelDecision(
                scenario_id=scenario.id,
                prompt=scenario.prompt_variants[0],
                selected_tool="followupboss_list_my_overdue_tasks",
                arguments={"fields": ["personName"]},
            )
        ]
    )
    client = StubMcpClient(results=[RuntimeError("Invalid field personName")])

    transcript = await capture_ai_selected_transcript(
        selector=selector,
        profile=battle_test_model_profile_by_id("gpt-5.5-low-reasoning"),
        scenario=scenario,
        prompt=scenario.prompt_variants[0],
        mcp_client=client,
    )

    assert transcript.selected_tool == "followupboss_list_my_overdue_tasks"
    assert transcript.arguments == {"fields": ["personName"]}
    assert transcript.response == {"error": "Invalid field personName"}


@pytest.mark.asyncio
async def test_capture_ai_selected_transcript_records_model_selection_errors() -> None:
    scenario = scenario_by_id("BT-READ-002")
    selector = StubAiSelector(decisions=[TimeoutError("OpenAI timed out")])

    transcript = await capture_ai_selected_transcript(
        selector=selector,
        profile=battle_test_model_profile_by_id("gpt-5.5-low-reasoning"),
        scenario=scenario,
        prompt=scenario.prompt_variants[0],
        mcp_client=StubMcpClient(results=[]),
    )

    assert transcript.selected_tool is None
    assert transcript.response == {"error": "AI route selection failed: OpenAI timed out"}
    assert transcript.assistant_message == "OpenAI timed out"


@pytest.mark.asyncio
async def test_capture_ai_selected_multi_call_transcript_executes_ordered_calls() -> None:
    conversation = read_only_battle_test_conversations(BattleTestConversationKind.MULTI_ASK)[0]
    selector = StubMultiAiSelector(
        decision_batches=[
            (
                BattleTestModelDecision(
                    scenario_id=f"{conversation.id}-T01",
                    prompt=conversation.prompt or "",
                    selected_tool="followupboss_get_latest_lead",
                    arguments={"fields": ["id"]},
                ),
                BattleTestModelDecision(
                    scenario_id=f"{conversation.id}-T02",
                    prompt=conversation.prompt or "",
                    selected_tool="followupboss_list_my_tasks_due_today",
                    arguments={"limit": 5},
                ),
            )
        ]
    )
    client = StubMcpClient(results=[{"person": {"id": 42}}, {"tasks": []}])

    transcript = await capture_ai_selected_multi_call_transcript(
        selector=selector,
        profile=battle_test_model_profile_by_id("gpt-5.5-low-reasoning"),
        conversation=conversation,
        mcp_client=client,
    )

    assert transcript.scenario_id == conversation.id
    assert selector.prompts[0].startswith(conversation.prompt or "")
    assert "exactly 2 ordered tool or sentinel calls" in selector.prompts[0]
    assert [item.scenario_id for item in transcript.transcripts] == [
        f"{conversation.id}-T01",
        f"{conversation.id}-T02",
    ]
    assert client.calls == [
        ("followupboss_get_latest_lead", {"fields": ["id"]}),
        ("followupboss_list_my_tasks_due_today", {"limit": 5}),
    ]


@pytest.mark.asyncio
async def test_capture_ai_selected_multi_call_transcript_handles_missing_and_extra_calls() -> None:
    conversation = read_only_battle_test_conversations(BattleTestConversationKind.MULTI_ASK)[0]
    selector = StubMultiAiSelector(
        decision_batches=[
            (
                BattleTestModelDecision(
                    scenario_id=f"{conversation.id}-T01",
                    prompt=conversation.prompt or "",
                    assistant_message="I cannot search notes.",
                    unsupported_explained=True,
                ),
                BattleTestModelDecision(
                    scenario_id=f"{conversation.id}-EXTRA-01",
                    prompt=conversation.prompt or "",
                    selected_tool="followupboss_get_latest_lead",
                ),
                BattleTestModelDecision(
                    scenario_id=f"{conversation.id}-EXTRA-02",
                    prompt=conversation.prompt or "",
                    selected_tool="followupboss_list_my_overdue_tasks",
                ),
            )
        ]
    )
    client = StubMcpClient(results=[{"person": {"id": 42}}, RuntimeError("extra failed")])

    transcript = await capture_ai_selected_multi_call_transcript(
        selector=selector,
        profile=battle_test_model_profile_by_id("gpt-5.5-low-reasoning"),
        conversation=conversation,
        mcp_client=client,
    )

    assert transcript.transcripts[0].unsupported_explained is True
    assert transcript.transcripts[1].selected_tool == "followupboss_get_latest_lead"
    assert transcript.transcripts[2].scenario_id == f"{conversation.id}-EXTRA-01"
    assert transcript.transcripts[2].response == {"error": "extra failed"}


@pytest.mark.asyncio
async def test_capture_ai_selected_multi_call_transcript_records_missing_calls() -> None:
    conversation = read_only_battle_test_conversations(BattleTestConversationKind.MULTI_ASK)[0]
    selector = StubMultiAiSelector(
        decision_batches=[
            (
                BattleTestModelDecision(
                    scenario_id=f"{conversation.id}-T01",
                    prompt=conversation.prompt or "",
                    selected_tool="followupboss_get_latest_lead",
                ),
            )
        ]
    )

    transcript = await capture_ai_selected_multi_call_transcript(
        selector=selector,
        profile=battle_test_model_profile_by_id("gpt-5.5-low-reasoning"),
        conversation=conversation,
        mcp_client=StubMcpClient(results=[{"person": {"id": 42}}]),
    )

    assert transcript.transcripts[1].selected_tool is None
    assert transcript.transcripts[1].assistant_message is None


@pytest.mark.asyncio
async def test_capture_ai_selected_multi_call_transcript_reuses_unsupported_text() -> None:
    conversation = next(
        item
        for item in read_only_battle_test_conversations(BattleTestConversationKind.MULTI_ASK)
        if "notes" in (item.prompt or "")
    )
    prompt = conversation.prompt or ""
    selector = StubMultiAiSelector(
        decision_batches=[
            (
                BattleTestModelDecision(
                    scenario_id=f"{conversation.id}-T01",
                    prompt=prompt,
                    selected_tool="followupboss_get_latest_lead",
                    assistant_message=(
                        "I can pull the latest lead, but I can't search that lead's notes "
                        "because the MCP API does not expose note search by lead."
                    ),
                ),
            )
        ]
    )

    transcript = await capture_ai_selected_multi_call_transcript(
        selector=selector,
        profile=battle_test_model_profile_by_id("gpt-5.5-low-reasoning"),
        conversation=conversation,
        mcp_client=StubMcpClient(results=[{"person": {"id": 42}}]),
    )

    assert transcript.transcripts[0].selected_tool == "followupboss_get_latest_lead"
    assert transcript.transcripts[1].selected_tool is None
    assert transcript.transcripts[1].unsupported_explained is True
    assert "can't search" in (transcript.transcripts[1].assistant_message or "")


@pytest.mark.asyncio
async def test_capture_ai_selected_multi_call_transcript_rejects_multi_turn() -> None:
    conversation = read_only_battle_test_conversations(BattleTestConversationKind.MULTI_TURN)[0]

    with pytest.raises(ValueError, match="multi-ask conversation"):
        await capture_ai_selected_multi_call_transcript(
            selector=StubMultiAiSelector(decision_batches=[]),
            profile=battle_test_model_profile_by_id("gpt-5.5-low-reasoning"),
            conversation=conversation,
            mcp_client=StubMcpClient(results=[]),
        )


@pytest.mark.asyncio
async def test_capture_ai_selected_multi_call_transcript_records_selection_error() -> None:
    conversation = read_only_battle_test_conversations(BattleTestConversationKind.MULTI_ASK)[0]

    transcript = await capture_ai_selected_multi_call_transcript(
        selector=StubAiSelector(decisions=[TimeoutError("selector timed out")]),
        profile=battle_test_model_profile_by_id("gpt-5.5-low-reasoning"),
        conversation=conversation,
        mcp_client=StubMcpClient(results=[]),
    )

    assert [item.response for item in transcript.transcripts] == [
        {"error": "AI route selection failed: selector timed out"},
        {"error": "AI route selection failed: selector timed out"},
    ]
    assert transcript.assistant_message == "selector timed out"


@pytest.mark.asyncio
async def test_capture_ai_selected_conversation_transcript_passes_history() -> None:
    conversation = read_only_battle_test_conversations(BattleTestConversationKind.MULTI_TURN)[0]
    selector = StubMultiAiSelector(
        decision_batches=[
            (
                BattleTestModelDecision(
                    scenario_id="BT-CHAIN-001-T01",
                    prompt=conversation.turns[0].prompt,
                    selected_tool="followupboss_get_latest_lead",
                ),
            ),
            (
                BattleTestModelDecision(
                    scenario_id="BT-CHAIN-001-T02",
                    prompt=conversation.turns[1].prompt,
                    selected_tool="followupboss_list_my_tasks_due_today",
                ),
            ),
        ]
    )
    client = StubMcpClient(results=[{"person": {"id": 42}}, {"tasks": []}])

    transcript = await capture_ai_selected_conversation_transcript(
        selector=selector,
        profile=battle_test_model_profile_by_id("gpt-5.5-low-reasoning"),
        conversation=conversation,
        mcp_client=client,
    )

    assert transcript.conversation_id == "BT-CHAIN-001"
    assert [item.scenario_id for item in transcript.turn_transcripts] == [
        "BT-CHAIN-001-T01",
        "BT-CHAIN-001-T02",
    ]
    assert selector.prompts[0] == "Show my latest lead"
    assert "Previous conversation context:" in selector.prompts[1]
    assert "called followupboss_get_latest_lead" in selector.prompts[1]


@pytest.mark.asyncio
async def test_capture_ai_selected_conversation_transcript_records_selection_error() -> None:
    conversation = read_only_battle_test_conversations(BattleTestConversationKind.MULTI_TURN)[0]
    selector = StubAiSelector(decisions=[TimeoutError("selector timed out")])

    transcript = await capture_ai_selected_conversation_transcript(
        selector=selector,
        profile=battle_test_model_profile_by_id("gpt-5.5-low-reasoning"),
        conversation=conversation.model_copy(update={"turns": conversation.turns[:1]}),
        mcp_client=StubMcpClient(results=[]),
    )

    assert transcript.turn_transcripts[0].response == {
        "error": "AI route selection failed: selector timed out"
    }
    assert transcript.turn_transcripts[0].assistant_message == "selector timed out"


def test_conversation_prompt_renders_non_tool_history_branches() -> None:
    prompt = _conversation_prompt(
        "What next?",
        (
            BattleTestTranscript(
                scenario_id="A",
                prompt="Find notes",
                unsupported_explained=True,
            ),
            BattleTestTranscript(
                scenario_id="B",
                prompt="Do it",
                clarified=True,
            ),
            BattleTestTranscript(
                scenario_id="C",
                prompt="Hello",
                assistant_message="I can help.",
            ),
            BattleTestTranscript(
                scenario_id="D",
                prompt="No visible action",
            ),
            BattleTestTranscript(
                scenario_id="E",
                prompt="Resolve the list",
                selected_tool="followupboss_list_smart_lists",
                response={"smartlists": [{"id": 77, "name": "Eligible For Transfer"}]},
            ),
            BattleTestTranscript(
                scenario_id="F",
                prompt="Call a tool without a response",
                selected_tool="followupboss_search_people",
            ),
            BattleTestTranscript(
                scenario_id="G",
                prompt="Summarize a large response",
                selected_tool="followupboss_search_people",
                response={"people": [{"id": 1, "notes": "x" * 1300}]},
            ),
        ),
    )

    assert "explained unsupported capability" in prompt
    assert "asked for clarification" in prompt
    assert "Assistant: I can help." in prompt
    assert "Tool response:" in prompt
    assert "Eligible For Transfer" in prompt
    assert "..." in prompt


@pytest.mark.asyncio
async def test_run_ai_model_profile_battle_tests_writes_separate_artifacts(tmp_path: Path) -> None:
    scenario = scenario_by_id("BT-READ-005")
    gpt_profile = battle_test_model_profile_by_id("gpt-5.5-low-reasoning")
    sonnet_profile = battle_test_model_profile_by_id("sonnet-4.6")
    selectors: dict[BattleTestModelProvider, BattleTestModelSelector] = {
        BattleTestModelProvider.OPENAI: StubAiSelector(
            decisions=[
                BattleTestModelDecision(
                    scenario_id=scenario.id,
                    prompt=scenario.prompt_variants[0],
                    assistant_message="Unsupported.",
                    unsupported_explained=True,
                )
            ]
        ),
        BattleTestModelProvider.ANTHROPIC: StubAiSelector(
            decisions=[
                BattleTestModelDecision(
                    scenario_id=scenario.id,
                    prompt=scenario.prompt_variants[0],
                    assistant_message="Unsupported.",
                    unsupported_explained=True,
                )
            ]
        ),
    }

    artifacts = await run_ai_model_profile_battle_tests(
        mcp_client=StubMcpClient(results=[]),
        oracle=ReadOnlyBattleTestOracle(StubBattleTestServices()),
        selectors=selectors,
        run_id_prefix="read-only-unit",
        client="unit-ai",
        profiles=(gpt_profile, sonnet_profile),
        scenarios=(scenario,),
        artifact_directory=tmp_path,
        environment="test",
        started_at="2026-05-18T02:00:00Z",
    )

    assert [artifact.summary.overall_passed for artifact in artifacts] == [True, True]
    assert (tmp_path / "read-only-unit-gpt-5.5-low-reasoning.json").exists()
    assert (tmp_path / "read-only-unit-sonnet-4.6.json").exists()


@pytest.mark.asyncio
async def test_run_ai_model_profile_conversation_battle_tests_writes_chain_summary(
    tmp_path: Path,
) -> None:
    conversation = read_only_battle_test_conversations(BattleTestConversationKind.MULTI_ASK)[0]
    profile = battle_test_model_profile_by_id("gpt-5.5-low-reasoning")
    selector = StubMultiAiSelector(
        decision_batches=[
            (
                BattleTestModelDecision(
                    scenario_id=f"{conversation.id}-T01",
                    prompt=conversation.prompt or "",
                    selected_tool="followupboss_get_latest_lead",
                ),
                BattleTestModelDecision(
                    scenario_id=f"{conversation.id}-T02",
                    prompt=conversation.prompt or "",
                    selected_tool="followupboss_list_my_tasks_due_today",
                ),
            )
        ]
    )

    artifacts = await run_ai_model_profile_conversation_battle_tests(
        mcp_client=StubMcpClient(results=[{"person": {"id": 42}}, {"tasks": []}]),
        oracle=ReadOnlyBattleTestOracle(StubBattleTestServices()),
        selectors={BattleTestModelProvider.OPENAI: selector},
        run_id_prefix="chains-unit",
        client="unit",
        profiles=(profile,),
        conversations=(conversation,),
        artifact_directory=tmp_path,
        max_cases=1,
    )

    assert artifacts[0].summary.overall_passed is True
    assert artifacts[0].conversation_evaluations[0].passed is True
    assert (tmp_path / "chains-unit-gpt-5.5-low-reasoning.json").exists()


@pytest.mark.asyncio
async def test_run_ai_model_profile_conversation_battle_tests_supports_chain_depth() -> None:
    conversation = read_only_battle_test_conversations(BattleTestConversationKind.MULTI_TURN)[0]
    profile = battle_test_model_profile_by_id("gpt-5.5-low-reasoning")

    artifacts = await run_ai_model_profile_conversation_battle_tests(
        mcp_client=StubMcpClient(results=[{"person": {"id": 42}}]),
        oracle=ReadOnlyBattleTestOracle(StubBattleTestServices()),
        selectors={
            BattleTestModelProvider.OPENAI: StubAiSelector(
                decisions=[
                    BattleTestModelDecision(
                        scenario_id=f"{conversation.id}-T01",
                        prompt=conversation.turns[0].prompt,
                        selected_tool="followupboss_get_latest_lead",
                    )
                ]
            )
        },
        run_id_prefix="chains-depth",
        client="unit",
        profiles=(profile,),
        conversations=(conversation,),
        chain_depth=1,
    )

    assert artifacts[0].summary.total_scenarios == 1
    assert artifacts[0].summary.overall_passed is True


@pytest.mark.asyncio
async def test_run_ai_model_profile_conversation_battle_tests_requires_selector() -> None:
    profile = BattleTestModelProfile(
        id="missing-conversation-selector",
        provider=BattleTestModelProvider.OPENAI,
        model="gpt-5.5",
        display_name="Missing Selector",
    )

    with pytest.raises(RuntimeError, match="No battle-test selector"):
        await run_ai_model_profile_conversation_battle_tests(
            mcp_client=StubMcpClient(results=[]),
            oracle=ReadOnlyBattleTestOracle(StubBattleTestServices()),
            selectors={},
            run_id_prefix="missing-conversation-selector",
            client="unit",
            profiles=(profile,),
            conversations=(read_only_battle_test_conversations()[:1]),
        )


def test_load_env_file_preserves_existing_values_and_strips_quotes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text(
        "# comment\nOPENAI_API_KEY=file-value\nANTHROPIC_API_KEY='anthropic-file'\n"
        'FOLLOWUPBOSS_BATTLE_TEST_OPENAI_API_KEY="quoted"\n'
        "FOLLOWUPBOSS_BATTLE_TEST_ANTHROPIC_API_KEY=unquoted\nBAD\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("OPENAI_API_KEY", "existing")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    load_env_file(env_path)
    load_env_file(tmp_path / "missing.env")

    assert os.environ["OPENAI_API_KEY"] == "existing"
    assert os.environ["ANTHROPIC_API_KEY"] == "anthropic-file"
    assert os.environ["FOLLOWUPBOSS_BATTLE_TEST_OPENAI_API_KEY"] == "quoted"
    assert os.environ["FOLLOWUPBOSS_BATTLE_TEST_ANTHROPIC_API_KEY"] == "unquoted"


def test_battle_test_ai_selectors_from_env_uses_available_keys() -> None:
    selectors = battle_test_ai_selectors_from_env(
        env={
            "FOLLOWUPBOSS_BATTLE_TEST_OPENAI_API_KEY": "openai",
            "ANTHROPIC_API_KEY": "anthropic",
        }
    )

    assert set(selectors) == {BattleTestModelProvider.OPENAI, BattleTestModelProvider.ANTHROPIC}


def test_battle_test_ai_selectors_from_env_handles_partial_and_empty_env() -> None:
    openai_selectors = battle_test_ai_selectors_from_env(env={"OPENAI_API_KEY": "openai"})
    anthropic_selectors = battle_test_ai_selectors_from_env(env={"CLAUDE_API_KEY": "anthropic"})
    empty_selectors = battle_test_ai_selectors_from_env(env={})

    assert set(openai_selectors) == {BattleTestModelProvider.OPENAI}
    assert set(anthropic_selectors) == {BattleTestModelProvider.ANTHROPIC}
    assert empty_selectors == {}


def test_battle_test_ai_selectors_from_env_accepts_http_client_factory() -> None:
    created = 0

    def factory() -> httpx.AsyncClient:
        nonlocal created
        created += 1
        return httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(200)))

    selectors = battle_test_ai_selectors_from_env(
        env={"OPENAI_API_KEY": "openai", "ANTHROPIC_API_KEY": "anthropic"},
        http_client_factory=factory,
    )

    assert set(selectors) == {BattleTestModelProvider.OPENAI, BattleTestModelProvider.ANTHROPIC}
    assert created == 2


def test_mcp_tool_result_to_json_keeps_ai_test_json_values() -> None:
    assert mcp_tool_result_to_json({"ok": True}) == {"ok": True}


@pytest.mark.parametrize(
    "provider",
    [BattleTestModelProvider.OPENAI, BattleTestModelProvider.ANTHROPIC],
)
@pytest.mark.asyncio
async def test_missing_selector_for_profile_raises(provider: BattleTestModelProvider) -> None:
    profile = BattleTestModelProfile(
        id=f"{provider.value}-missing",
        provider=provider,
        model="missing-model",
        display_name="Missing Model",
    )

    with pytest.raises(RuntimeError, match="No battle-test selector"):
        await run_ai_model_profile_battle_tests(
            mcp_client=StubMcpClient(results=[]),
            oracle=ReadOnlyBattleTestOracle(StubBattleTestServices()),
            selectors={},
            run_id_prefix="missing",
            client="unit",
            profiles=(profile,),
            scenarios=(scenario_by_id("BT-READ-005"),),
        )


@pytest.mark.asyncio
async def test_run_ai_model_profile_battle_tests_can_skip_artifact_directory() -> None:
    scenario = scenario_by_id("BT-READ-005")
    profile = battle_test_model_profile_by_id("gpt-5.5-low-reasoning")
    selector = StubAiSelector(
        decisions=[
            BattleTestModelDecision(
                scenario_id=scenario.id,
                prompt=scenario.prompt_variants[1],
                assistant_message="Unsupported.",
                unsupported_explained=True,
            )
        ]
    )

    artifacts = await run_ai_model_profile_battle_tests(
        mcp_client=StubMcpClient(results=[]),
        oracle=ReadOnlyBattleTestOracle(StubBattleTestServices()),
        selectors={BattleTestModelProvider.OPENAI: selector},
        run_id_prefix="no-artifact",
        client="unit",
        profiles=(profile,),
        scenarios=(scenario,),
        prompt_variant_index=1,
    )

    assert len(artifacts) == 1
    assert artifacts[0].summary.overall_passed is True


@pytest.mark.asyncio
async def test_run_ai_model_profile_battle_tests_can_expand_all_prompt_variants() -> None:
    base = scenario_by_id("BT-READ-005").model_copy(
        update={"prompt_variants": ("Show notes for lead 123", "Find all notes for this lead")},
        deep=True,
    )
    profile = battle_test_model_profile_by_id("gpt-5.5-low-reasoning")
    selector = StubAiSelector(
        decisions=[
            BattleTestModelDecision(
                scenario_id="BT-READ-005-P01",
                prompt="Show notes for lead 123",
                assistant_message="Unsupported.",
                unsupported_explained=True,
            ),
            BattleTestModelDecision(
                scenario_id="BT-READ-005-P02",
                prompt="Find all notes for this lead",
                assistant_message="Unsupported.",
                unsupported_explained=True,
            ),
        ]
    )

    artifacts = await run_ai_model_profile_battle_tests(
        mcp_client=StubMcpClient(results=[]),
        oracle=ReadOnlyBattleTestOracle(StubBattleTestServices()),
        selectors={BattleTestModelProvider.OPENAI: selector},
        run_id_prefix="all-variants",
        client="unit",
        profiles=(profile,),
        scenarios=(base,),
        all_prompt_variants=True,
    )

    assert artifacts[0].summary.total_scenarios == 2
    assert artifacts[0].summary.passed_scenarios == 2
    assert [evaluation.scenario_id for evaluation in artifacts[0].evaluations] == [
        "BT-READ-005-P01",
        "BT-READ-005-P02",
    ]


@pytest.mark.asyncio
async def test_run_ai_model_profile_battle_tests_rejects_bad_prompt_index() -> None:
    with pytest.raises(IndexError, match="Prompt variant index"):
        await run_ai_model_profile_battle_tests(
            mcp_client=StubMcpClient(results=[]),
            oracle=ReadOnlyBattleTestOracle(StubBattleTestServices()),
            selectors={BattleTestModelProvider.OPENAI: StubAiSelector(decisions=[])},
            run_id_prefix="bad-index",
            client="unit",
            profiles=(battle_test_model_profile_by_id("gpt-5.5-low-reasoning"),),
            scenarios=(scenario_by_id("BT-READ-005"),),
            prompt_variant_index=999,
        )


def test_read_only_tool_specs_include_model_control_sentinels() -> None:
    names = [tool.name for tool in read_only_battle_test_ai_tool_specs()]

    assert "battle_test_clarify" in names
    assert "battle_test_explain_unsupported" in names
    assert "followupboss_get_latest_lead" in names


def test_json_value_type_alias_accepts_test_values() -> None:
    value: JsonValue = {"nested": [1, "two", True]}

    assert value == {"nested": [1, "two", True]}


def test_private_json_value_helper_normalizes_nested_and_unknown_values() -> None:
    value = _json_value({1: "ignored", "nested": [object()]})

    assert isinstance(value, dict)
    assert set(value) == {"nested"}
    nested = value["nested"]
    assert isinstance(nested, list)
    assert isinstance(nested[0], str)
    assert nested[0].startswith("<object object at")
