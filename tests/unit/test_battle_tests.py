"""Tests for MCP battle-test scenario and oracle helpers."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from pathlib import Path
from typing import Any, cast

import pytest

import followupboss_mcp.battle_tests as battle_tests_module
import followupboss_mcp.mcp_tools as mcp_tools_module
from followupboss_mcp.battle_tests import (
    ApiOracleSpec,
    BattleTestConversationKind,
    BattleTestConversationScenario,
    BattleTestConversationTranscript,
    BattleTestConversationTurn,
    BattleTestEvaluation,
    BattleTestFailureCategory,
    BattleTestFixtureKind,
    BattleTestGrade,
    BattleTestModelProfile,
    BattleTestModelProvider,
    BattleTestOracleKind,
    BattleTestOracleSnapshot,
    BattleTestRunArtifact,
    BattleTestRunMetadata,
    BattleTestScenario,
    BattleTestToolCall,
    BattleTestTranscript,
    ExpectedMcpRoute,
    ReadOnlyBattleTestOracle,
    battle_test_model_profile_by_id,
    battle_test_model_profiles,
    build_battle_test_run_artifact,
    build_disposable_fixture_plan,
    build_model_profile_run_metadata,
    capture_mcp_tool_transcript,
    capture_mcp_tool_transcripts,
    categorize_battle_test_failure,
    categorize_battle_test_failures,
    conversation_turn_to_scenario,
    evaluate_battle_test_conversation,
    evaluate_battle_test_conversations,
    evaluate_battle_test_run,
    evaluate_model_profile_battle_test_runs,
    evaluate_transcript_route,
    expand_battle_test_prompt_variants,
    expanded_battle_test_conversations,
    expanded_read_only_battle_test_scenarios,
    flatten_battle_test_conversations,
    mcp_tool_result_to_json,
    read_only_battle_test_conversations,
    read_only_battle_test_scenarios,
    run_battle_test_tool_calls,
    sample_battle_test_conversations,
    sample_battle_test_scenarios,
    scenario_by_id,
    smart_list_grounding_battle_test_conversations,
    smart_list_grounding_battle_test_scenarios,
    write_battle_test_run_artifact,
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


def _metadata(count: int) -> PaginationMetadata:
    return PaginationMetadata(
        count=count,
        limit=count,
        next_token=None,
        next_link=None,
        offset=0,
        total=count,
    )


def _people_page(*people: PersonRecord) -> PageResult[PersonRecord]:
    return PageResult(items=list(people), metadata=_metadata(len(people)))


def _tasks_page(*tasks: TaskRecord) -> PageResult[TaskRecord]:
    return PageResult(items=list(tasks), metadata=_metadata(len(tasks)))


def _smart_lists_page(*smart_lists: SmartListRecord) -> PageResult[SmartListRecord]:
    return PageResult(items=list(smart_lists), metadata=_metadata(len(smart_lists)))


def _appointments_page(*appointments: AppointmentRecord) -> PageResult[AppointmentRecord]:
    return PageResult(items=list(appointments), metadata=_metadata(len(appointments)))


def _calls_page(*calls: CallRecord) -> PageResult[CallRecord]:
    return PageResult(items=list(calls), metadata=_metadata(len(calls)))


def _text_messages_page(*messages: TextMessageRecord) -> PageResult[TextMessageRecord]:
    return PageResult(items=list(messages), metadata=_metadata(len(messages)))


def _email_events_page(*events: EmailEventRecord) -> PageResult[EmailEventRecord]:
    return PageResult(items=list(events), metadata=_metadata(len(events)))


def _events_page(*events: EventRecord) -> PageResult[EventRecord]:
    return PageResult(items=list(events), metadata=_metadata(len(events)))


def _templates_page(*templates: TemplateRecord) -> PageResult[TemplateRecord]:
    return PageResult(items=list(templates), metadata=_metadata(len(templates)))


def _text_templates_page(
    *templates: TextMessageTemplateRecord,
) -> PageResult[TextMessageTemplateRecord]:
    return PageResult(items=list(templates), metadata=_metadata(len(templates)))


def test_upcoming_task_due_start_is_shared_by_oracle_and_tool_adapter() -> None:
    battle_due_start = cast(
        "Callable[[], datetime]",
        getattr(battle_tests_module, "_upcoming_task_due_start"),  # noqa: B009
    )
    tool_due_start = cast(
        "Callable[[], datetime]",
        getattr(mcp_tools_module, "_upcoming_task_due_start"),  # noqa: B009
    )
    due_start = battle_due_start()

    assert battle_due_start is tool_due_start
    assert due_start.utcoffset() == timedelta(0)
    assert due_start.time() == time.min


@dataclass
class StubIdentityService:
    user_id: int | None

    async def get_identity(self) -> IdentityResponse:
        return IdentityResponse(id=self.user_id)


@dataclass
class StubPeopleService:
    page: PageResult[PersonRecord]
    duplicate: PersonDuplicateCheckRecord = field(
        default_factory=lambda: PersonDuplicateCheckRecord(found=False)
    )
    unclaimed_page: PageResult[PersonRecord] = field(default_factory=_people_page)
    requests: list[PeopleSearchRequest] = field(default_factory=list)
    duplicate_requests: list[PersonDuplicateCheckRequest] = field(default_factory=list)
    unclaimed_requests: list[UnclaimedPeopleListRequest] = field(default_factory=list)

    async def get_person(
        self,
        person_id: int,
        request: object | None = None,
    ) -> PersonRecord:
        del request
        return PersonRecord(id=person_id, firstName="Alex")

    async def search_people(
        self, request: PeopleSearchRequest | None = None
    ) -> PageResult[PersonRecord]:
        self.requests.append(request or PeopleSearchRequest())
        return self.page

    async def check_duplicate_person(
        self, request: PersonDuplicateCheckRequest
    ) -> PersonDuplicateCheckRecord:
        self.duplicate_requests.append(request)
        return self.duplicate

    async def list_unclaimed_people(
        self, request: UnclaimedPeopleListRequest | None = None
    ) -> PageResult[PersonRecord]:
        self.unclaimed_requests.append(request or UnclaimedPeopleListRequest())
        return self.unclaimed_page


@dataclass
class StubTasksService:
    page: PageResult[TaskRecord]
    requests: list[TaskListRequest] = field(default_factory=list)

    async def list_tasks(self, request: TaskListRequest | None = None) -> PageResult[TaskRecord]:
        self.requests.append(request or TaskListRequest())
        return self.page


@dataclass
class StubSmartListsService:
    page: PageResult[SmartListRecord] = field(default_factory=_smart_lists_page)
    requests: list[SmartListListRequest] = field(default_factory=list)

    async def list_smart_lists(
        self, request: SmartListListRequest | None = None
    ) -> PageResult[SmartListRecord]:
        self.requests.append(request or SmartListListRequest())
        return self.page


@dataclass
class PaginatedStubSmartListsService(StubSmartListsService):
    pages: list[PageResult[SmartListRecord]] = field(default_factory=list)

    async def list_smart_lists(
        self, request: SmartListListRequest | None = None
    ) -> PageResult[SmartListRecord]:
        self.requests.append(request or SmartListListRequest())
        page_index = min(len(self.requests) - 1, len(self.pages) - 1)
        return self.pages[page_index]


@dataclass
class StubAppointmentsService:
    page: PageResult[AppointmentRecord] = field(default_factory=_appointments_page)
    requests: list[AppointmentListRequest] = field(default_factory=list)

    async def list_appointments(
        self, request: AppointmentListRequest | None = None
    ) -> PageResult[AppointmentRecord]:
        self.requests.append(request or AppointmentListRequest())
        return self.page


@dataclass
class StubCallsService:
    page: PageResult[CallRecord] = field(default_factory=_calls_page)
    requests: list[CallListRequest] = field(default_factory=list)

    async def list_calls(self, request: CallListRequest | None = None) -> PageResult[CallRecord]:
        self.requests.append(request or CallListRequest())
        return self.page


@dataclass
class StubTextMessagesService:
    page: PageResult[TextMessageRecord] = field(default_factory=_text_messages_page)
    requests: list[TextMessageListRequest] = field(default_factory=list)

    async def list_text_messages(
        self, request: TextMessageListRequest | None = None
    ) -> PageResult[TextMessageRecord]:
        self.requests.append(request or TextMessageListRequest())
        return self.page


@dataclass
class StubEmailEventsService:
    page: PageResult[EmailEventRecord] = field(default_factory=_email_events_page)
    requests: list[EmailEventListRequest] = field(default_factory=list)

    async def list_email_events(
        self, request: EmailEventListRequest | None = None
    ) -> PageResult[EmailEventRecord]:
        self.requests.append(request or EmailEventListRequest())
        return self.page


@dataclass
class StubEventsService:
    page: PageResult[EventRecord] = field(default_factory=_events_page)
    requests: list[EventSearchRequest] = field(default_factory=list)

    async def search_events(
        self, request: EventSearchRequest | None = None
    ) -> PageResult[EventRecord]:
        self.requests.append(request or EventSearchRequest())
        return self.page


@dataclass
class StubTemplatesService:
    page: PageResult[TemplateRecord] = field(default_factory=_templates_page)
    requests: list[TemplateListRequest] = field(default_factory=list)

    async def list_templates(
        self, request: TemplateListRequest | None = None
    ) -> PageResult[TemplateRecord]:
        self.requests.append(request or TemplateListRequest())
        return self.page


@dataclass
class StubTextMessageTemplatesService:
    page: PageResult[TextMessageTemplateRecord] = field(default_factory=_text_templates_page)
    requests: list[TextMessageTemplateListRequest] = field(default_factory=list)

    async def list_text_message_templates(
        self, request: TextMessageTemplateListRequest | None = None
    ) -> PageResult[TextMessageTemplateRecord]:
        self.requests.append(request or TextMessageTemplateListRequest())
        return self.page


@dataclass
class StubNotesService:
    note: NoteRecord = field(default_factory=lambda: NoteRecord.model_validate({"id": 1}))
    requests: list[int] = field(default_factory=list)

    async def get_note(self, note_id: int) -> NoteRecord:
        self.requests.append(note_id)
        return self.note


@dataclass
class FailingTasksService:
    async def list_tasks(self, request: TaskListRequest | None = None) -> PageResult[TaskRecord]:
        """Raise a stable failure for oracle exception tests."""
        raise RuntimeError("invalid task oracle request")


@dataclass
class StubBattleTestServices:
    identity: StubIdentityService
    people: StubPeopleService
    tasks: StubTasksService
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


@dataclass
class FailingTaskBattleTestServices:
    identity: StubIdentityService
    people: StubPeopleService
    tasks: FailingTasksService
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


@dataclass
class StubMcpToolResult:
    structured_content: object | None = None
    content: tuple[object, ...] = ()

    def __post_init__(self) -> None:
        """Expose the client-library shaped structured content attribute."""
        if self.structured_content is not None:
            self.structuredContent = self.structured_content


@dataclass
class StubMcpTextContent:
    text: str


@dataclass
class StubMcpClient:
    results: list[object]
    calls: list[tuple[str, object]] = field(default_factory=list)

    async def call_tool(self, name: str, arguments: object | None = None) -> object:
        self.calls.append((name, arguments))
        return self.results.pop(0)


def _services(
    *,
    user_id: int | None = 7,
    people: PageResult[PersonRecord] | None = None,
    tasks: PageResult[TaskRecord] | None = None,
    smart_lists: PageResult[SmartListRecord] | None = None,
    appointments: PageResult[AppointmentRecord] | None = None,
    calls: PageResult[CallRecord] | None = None,
    text_messages: PageResult[TextMessageRecord] | None = None,
    email_events: PageResult[EmailEventRecord] | None = None,
    events: PageResult[EventRecord] | None = None,
    templates: PageResult[TemplateRecord] | None = None,
    text_templates: PageResult[TextMessageTemplateRecord] | None = None,
) -> StubBattleTestServices:
    return StubBattleTestServices(
        identity=StubIdentityService(user_id),
        people=StubPeopleService(people or _people_page()),
        tasks=StubTasksService(tasks or _tasks_page()),
        smart_lists=StubSmartListsService(smart_lists or _smart_lists_page()),
        appointments=StubAppointmentsService(appointments or _appointments_page()),
        calls=StubCallsService(calls or _calls_page()),
        text_messages=StubTextMessagesService(text_messages or _text_messages_page()),
        email_marketing=StubEmailEventsService(email_events or _email_events_page()),
        events=StubEventsService(events or _events_page()),
        templates=StubTemplatesService(templates or _templates_page()),
        text_message_templates=StubTextMessageTemplatesService(
            text_templates or _text_templates_page()
        ),
    )


def _scenario(grade: BattleTestGrade) -> BattleTestScenario:
    return BattleTestScenario(
        id=f"TEST-{grade.value}",
        grade=grade,
        prompt_variants=("Do the thing",),
        expected_mcp=ExpectedMcpRoute(
            allowed_tools=("safe_tool",),
            forbidden_tools=("unsafe_tool",),
            required_argument_keys=("record_id",),
        ),
        api_oracle=ApiOracleSpec(
            kind=BattleTestOracleKind.UNSUPPORTED_NOTE_SEARCH,
            description="Test-only oracle.",
        ),
    )


def test_read_only_scenario_corpus_is_stable() -> None:
    scenarios = read_only_battle_test_scenarios()

    assert [scenario.id for scenario in scenarios] == [
        "BT-READ-001",
        "BT-READ-002",
        "BT-READ-003",
        "BT-READ-004",
        "BT-READ-005",
    ]
    assert all(len(scenario.prompt_variants) == 100 for scenario in scenarios)
    assert scenario_by_id("BT-READ-001").expected_mcp.allowed_tools == (
        "followupboss_get_latest_lead",
    )
    assert scenario_by_id("BT-READ-004").grade is BattleTestGrade.MUST_ROUTE
    assert scenario_by_id("BT-READ-004").expected_mcp.allowed_tools == (
        "followupboss_list_my_upcoming_tasks",
    )
    assert scenario_by_id("BT-READ-004").api_oracle.kind is BattleTestOracleKind.MY_UPCOMING_TASKS
    with pytest.raises(KeyError):
        scenario_by_id("BT-READ-999")


def test_expanded_read_only_scenario_corpus_adds_api_surfaces() -> None:
    scenarios = expanded_read_only_battle_test_scenarios()
    expanded_ids = [scenario.id for scenario in scenarios if scenario.id >= "BT-READ-006"]

    assert expanded_ids == [
        "BT-READ-006",
        "BT-READ-007",
        "BT-READ-008",
        "BT-READ-009",
        "BT-READ-010",
        "BT-READ-011",
        "BT-READ-012",
        "BT-READ-013",
        "BT-READ-014",
        "BT-READ-015",
        "BT-READ-016",
        "BT-READ-017",
    ]
    assert all(len(scenario.prompt_variants) == 50 for scenario in scenarios[5:])
    assert scenario_by_id("BT-READ-008").expected_mcp.required_argument_keys == ("email",)
    assert scenario_by_id("BT-READ-015").api_oracle.kind is BattleTestOracleKind.EXPLICIT_NOTE
    assert scenario_by_id("BT-READ-016").api_oracle.kind is BattleTestOracleKind.PERSON_ACTIVITY
    assert scenario_by_id("BT-READ-016").expected_mcp.forbidden_tools == (
        "followupboss_list_calls",
        "followupboss_list_text_messages",
        "followupboss_list_email_events",
        "followupboss_search_events",
        "followupboss_list_appointments",
    )


def test_expanded_conversation_corpus_adds_cross_surface_prompts() -> None:
    conversations = expanded_battle_test_conversations()
    multi_ask = expanded_battle_test_conversations(BattleTestConversationKind.MULTI_ASK)

    assert len(conversations) > len(read_only_battle_test_conversations())
    assert all(
        conversation.kind is BattleTestConversationKind.MULTI_ASK for conversation in multi_ask
    )
    assert any(conversation.id.startswith("BT-CHAIN-X") for conversation in conversations)
    assert any(
        turn.api_oracle.kind is BattleTestOracleKind.TEXT_MESSAGES
        for conversation in conversations
        for turn in conversation.turns
    )


def test_smart_list_grounding_corpus_targets_zillow_regression() -> None:
    scenarios = smart_list_grounding_battle_test_scenarios()
    conversations = smart_list_grounding_battle_test_conversations()

    assert [scenario.id for scenario in scenarios] == [
        "BT-SMARTLIST-001",
        "BT-SMARTLIST-002",
        "BT-SMARTLIST-003",
        "BT-SMARTLIST-004",
    ]
    assert not any("Zillow" in prompt for prompt in scenarios[0].prompt_variants)
    assert not any("lead" in prompt.casefold() for prompt in scenarios[0].prompt_variants)
    assert scenario_by_id("BT-SMARTLIST-002").api_oracle.kind is (
        BattleTestOracleKind.NAMED_SMART_LIST_PEOPLE
    )
    assert scenario_by_id("BT-SMARTLIST-002").api_oracle.smart_list_name == (
        "Eligible For Transfer"
    )
    assert scenario_by_id("BT-SMARTLIST-002").expected_mcp.allowed_tools == (
        "followupboss_search_people_in_smart_list",
    )
    assert scenario_by_id("BT-SMARTLIST-002").expected_mcp.required_argument_keys == (
        "smart_list_name",
        "source",
    )
    assert len(scenario_by_id("BT-SMARTLIST-002").prompt_variants) == 20
    assert scenario_by_id("BT-SMARTLIST-003").grade is BattleTestGrade.MUST_CLARIFY
    assert [conversation.kind for conversation in conversations] == [
        BattleTestConversationKind.MULTI_ASK,
        BattleTestConversationKind.MULTI_TURN,
        BattleTestConversationKind.MULTI_TURN,
        BattleTestConversationKind.MULTI_TURN,
    ]
    assert (
        smart_list_grounding_battle_test_conversations(BattleTestConversationKind.MULTI_ASK)[0]
        .turns[1]
        .api_oracle.kind
        is BattleTestOracleKind.NAMED_SMART_LIST_PEOPLE
    )


def test_disposable_fixture_plan_orders_cleanup_safely() -> None:
    plan = build_disposable_fixture_plan(run_prefix="MCP Battle Test 20260519")

    assert plan.fixture_kinds == (
        BattleTestFixtureKind.PERSON,
        BattleTestFixtureKind.TASK,
        BattleTestFixtureKind.NOTE,
        BattleTestFixtureKind.APPOINTMENT,
    )
    assert [action.fixture_kind for action in plan.cleanup_actions] == [
        BattleTestFixtureKind.APPOINTMENT,
        BattleTestFixtureKind.NOTE,
        BattleTestFixtureKind.TASK,
        BattleTestFixtureKind.PERSON,
    ]
    assert plan.cleanup_actions[-1].tool_name == "followupboss_delete_person"
    with pytest.raises(ValueError, match="non-empty run prefix"):
        build_disposable_fixture_plan(run_prefix=" ")


def test_read_only_conversation_corpus_has_stable_ids_and_turns() -> None:
    conversations = read_only_battle_test_conversations()

    assert len(conversations) == 50
    assert conversations[0].id == "BT-CHAIN-001"
    assert conversations[0].kind is BattleTestConversationKind.MULTI_TURN
    assert conversations[-1].kind is BattleTestConversationKind.MULTI_ASK
    flattened = flatten_battle_test_conversations((conversations[0],))

    assert [scenario.id for scenario in flattened] == ["BT-CHAIN-001-T01", "BT-CHAIN-001-T02"]
    assert flattened[0].expected_mcp.allowed_tools == ("followupboss_get_latest_lead",)


def test_conversation_turn_conversion_preserves_oracle_contract() -> None:
    conversation = read_only_battle_test_conversations()[0]

    scenario = conversation_turn_to_scenario(conversation, conversation.turns[0])

    assert scenario.id == "BT-CHAIN-001-T01"
    assert scenario.prompt_variants == ("Show my latest lead",)
    assert scenario.api_oracle.kind is BattleTestOracleKind.LATEST_ASSIGNED_LEAD


def test_sampling_helpers_are_deterministic_and_keep_order() -> None:
    scenarios = expand_battle_test_prompt_variants((scenario_by_id("BT-READ-005"),))
    conversations = read_only_battle_test_conversations()

    first_scenario_sample = sample_battle_test_scenarios(scenarios, max_cases=5, sample_seed=17)
    second_scenario_sample = sample_battle_test_scenarios(scenarios, max_cases=5, sample_seed=17)
    conversation_sample = sample_battle_test_conversations(
        conversations, max_cases=3, sample_seed=7
    )

    assert [scenario.id for scenario in first_scenario_sample] == [
        scenario.id for scenario in second_scenario_sample
    ]
    assert [scenario.id for scenario in first_scenario_sample] == sorted(
        scenario.id for scenario in first_scenario_sample
    )
    assert len(conversation_sample) == 3
    assert sample_battle_test_scenarios(scenarios, max_cases=0) == ()
    assert sample_battle_test_conversations(conversations, max_cases=0) == ()


def test_prompt_variant_expansion_creates_stable_cases() -> None:
    scenario = BattleTestScenario(
        id="BT-READ-TEST",
        grade=BattleTestGrade.MUST_ROUTE,
        prompt_variants=("First wording", "Second wording"),
        expected_mcp=ExpectedMcpRoute(allowed_tools=("safe_tool",)),
        api_oracle=ApiOracleSpec(
            kind=BattleTestOracleKind.UNSUPPORTED_NOTE_SEARCH,
            description="Test-only oracle.",
        ),
    )

    expanded = expand_battle_test_prompt_variants((scenario,))

    assert [item.id for item in expanded] == ["BT-READ-TEST-P01", "BT-READ-TEST-P02"]
    assert [item.prompt_variants for item in expanded] == [("First wording",), ("Second wording",)]
    assert all(item.expected_mcp == scenario.expected_mcp for item in expanded)


def test_scenario_requires_non_empty_prompt_variants() -> None:
    with pytest.raises(ValueError, match="non-empty prompt"):
        BattleTestScenario(
            id="BAD",
            grade=BattleTestGrade.MUST_ROUTE,
            prompt_variants=(" ",),
            expected_mcp=ExpectedMcpRoute(allowed_tools=("safe_tool",)),
            api_oracle=ApiOracleSpec(
                kind=BattleTestOracleKind.UNSUPPORTED_NOTE_SEARCH,
                description="Test-only oracle.",
            ),
        )


def test_conversation_scenario_validates_turn_shape() -> None:
    turn = BattleTestConversationTurn(
        id="T01",
        prompt="Show my latest lead",
        grade=BattleTestGrade.MUST_ROUTE,
        expected_mcp=ExpectedMcpRoute(allowed_tools=("followupboss_get_latest_lead",)),
        api_oracle=ApiOracleSpec(
            kind=BattleTestOracleKind.LATEST_ASSIGNED_LEAD,
            description="Latest lead.",
        ),
    )

    with pytest.raises(ValueError, match="conversation turns"):
        BattleTestConversationTurn(
            id=" ",
            prompt="Show my latest lead",
            grade=BattleTestGrade.MUST_ROUTE,
            expected_mcp=ExpectedMcpRoute(allowed_tools=("followupboss_get_latest_lead",)),
            api_oracle=ApiOracleSpec(
                kind=BattleTestOracleKind.LATEST_ASSIGNED_LEAD,
                description="Latest lead.",
            ),
        )

    with pytest.raises(ValueError, match="conversation scenarios"):
        BattleTestConversationScenario(
            id=" ",
            kind=BattleTestConversationKind.MULTI_TURN,
            turns=(turn,),
        )

    with pytest.raises(ValueError, match="at least one turn"):
        BattleTestConversationScenario(
            id="BT-CHAIN-EMPTY",
            kind=BattleTestConversationKind.MULTI_TURN,
            turns=(),
        )

    with pytest.raises(ValueError, match="turn IDs"):
        BattleTestConversationScenario(
            id="BT-CHAIN-DUP",
            kind=BattleTestConversationKind.MULTI_TURN,
            turns=(turn, turn),
        )

    with pytest.raises(ValueError, match="Multi-ask"):
        BattleTestConversationScenario(
            id="BT-CHAIN-NO-PROMPT",
            kind=BattleTestConversationKind.MULTI_ASK,
            turns=(turn,),
        )


def test_default_model_profiles_are_separate_run_targets() -> None:
    profiles = battle_test_model_profiles()

    assert [profile.id for profile in profiles] == ["gpt-5.5-low-reasoning", "sonnet-4.6"]
    assert profiles[0].provider is BattleTestModelProvider.OPENAI
    assert profiles[0].model == "gpt-5.5"
    assert profiles[0].reasoning_effort == "low"
    assert profiles[1].provider is BattleTestModelProvider.ANTHROPIC
    assert profiles[1].model == "claude-sonnet-4-6"
    assert profiles[1].reasoning_effort is None
    assert battle_test_model_profile_by_id("sonnet-4.6") == profiles[1]
    with pytest.raises(KeyError):
        battle_test_model_profile_by_id("missing")


def test_model_profile_requires_non_empty_strings() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        BattleTestModelProfile(
            id=" ",
            provider=BattleTestModelProvider.OPENAI,
            model="gpt-5.5",
            display_name="GPT-5.5",
        )
    with pytest.raises(ValueError, match="reasoning_effort"):
        BattleTestModelProfile(
            id="bad-reasoning",
            provider=BattleTestModelProvider.OPENAI,
            model="gpt-5.5",
            display_name="GPT-5.5",
            reasoning_effort=" ",
        )


def test_build_model_profile_run_metadata_suffixes_run_id() -> None:
    profile = battle_test_model_profile_by_id("gpt-5.5-low-reasoning")

    metadata = build_model_profile_run_metadata(
        run_id_prefix="read-only-20260518",
        client="cursor",
        model_profile=profile,
        environment="staging",
        started_at="2026-05-18T02:00:00Z",
        notes=("read-only",),
    )

    assert metadata.run_id == "read-only-20260518-gpt-5.5-low-reasoning"
    assert metadata.client == "cursor"
    assert metadata.model_profile == profile
    assert metadata.environment == "staging"
    assert metadata.started_at == "2026-05-18T02:00:00Z"
    assert metadata.notes == ("read-only",)


@pytest.mark.parametrize(
    ("grade", "transcript", "passed", "failure_substring"),
    [
        (
            BattleTestGrade.MUST_ROUTE,
            BattleTestTranscript(
                scenario_id="TEST-MUST_ROUTE",
                prompt="Do the thing",
                selected_tool="safe_tool",
            ),
            True,
            "",
        ),
        (
            BattleTestGrade.MUST_ROUTE,
            BattleTestTranscript(scenario_id="WRONG", prompt="Do the thing", selected_tool=None),
            False,
            "does not match",
        ),
        (
            BattleTestGrade.MUST_ROUTE,
            BattleTestTranscript(
                scenario_id="TEST-MUST_ROUTE",
                prompt="Do the thing",
                selected_tool="unsafe_tool",
            ),
            False,
            "forbidden tool",
        ),
        (
            BattleTestGrade.MAY_ROUTE,
            BattleTestTranscript(
                scenario_id="TEST-MAY_ROUTE",
                prompt="Do the thing",
                selected_tool="safe_tool",
            ),
            True,
            "",
        ),
        (
            BattleTestGrade.MAY_ROUTE,
            BattleTestTranscript(
                scenario_id="TEST-MAY_ROUTE",
                prompt="Do the thing",
                clarified=True,
            ),
            True,
            "",
        ),
        (
            BattleTestGrade.MAY_ROUTE,
            BattleTestTranscript(
                scenario_id="TEST-MAY_ROUTE",
                prompt="Do the thing",
                selected_tool="other_tool",
            ),
            False,
            "allowed safe route",
        ),
        (
            BattleTestGrade.MAY_ROUTE,
            BattleTestTranscript(scenario_id="TEST-MAY_ROUTE", prompt="Do the thing"),
            False,
            "safe tool route or a clarifying response",
        ),
        (
            BattleTestGrade.MUST_CLARIFY,
            BattleTestTranscript(
                scenario_id="TEST-MUST_CLARIFY",
                prompt="Do the thing",
                clarified=True,
            ),
            True,
            "",
        ),
        (
            BattleTestGrade.MUST_CLARIFY,
            BattleTestTranscript(
                scenario_id="TEST-MUST_CLARIFY",
                prompt="Do the thing",
                selected_tool="safe_tool",
            ),
            False,
            "clarifying question",
        ),
        (
            BattleTestGrade.MUST_REQUIRE_ID,
            BattleTestTranscript(
                scenario_id="TEST-MUST_REQUIRE_ID",
                prompt="Do the thing",
                arguments={"record_id": 123},
                selected_tool="safe_tool",
            ),
            True,
            "",
        ),
        (
            BattleTestGrade.MUST_REQUIRE_ID,
            BattleTestTranscript(
                scenario_id="TEST-MUST_REQUIRE_ID",
                prompt="Do the thing",
                selected_tool="safe_tool",
            ),
            False,
            "without required arguments",
        ),
        (
            BattleTestGrade.MUST_REQUIRE_ID,
            BattleTestTranscript(
                scenario_id="TEST-MUST_REQUIRE_ID",
                prompt="Do the thing",
                arguments={"record_id": 123},
                selected_tool="other_tool",
            ),
            False,
            "Expected one of",
        ),
        (
            BattleTestGrade.MUST_REQUIRE_ID,
            BattleTestTranscript(
                scenario_id="TEST-MUST_REQUIRE_ID",
                prompt="Do the thing",
                clarified=True,
            ),
            True,
            "",
        ),
        (
            BattleTestGrade.MUST_EXPLAIN_UNSUPPORTED,
            BattleTestTranscript(
                scenario_id="TEST-MUST_EXPLAIN_UNSUPPORTED",
                prompt="Do the thing",
                unsupported_explained=True,
            ),
            True,
            "",
        ),
        (
            BattleTestGrade.MUST_EXPLAIN_UNSUPPORTED,
            BattleTestTranscript(
                scenario_id="TEST-MUST_EXPLAIN_UNSUPPORTED",
                prompt="Do the thing",
                selected_tool="safe_tool",
            ),
            False,
            "unsupported API capability",
        ),
    ],
)
def test_route_evaluation_grades(
    grade: BattleTestGrade,
    transcript: BattleTestTranscript,
    passed: bool,
    failure_substring: str,
) -> None:
    route_result = evaluate_transcript_route(_scenario(grade), transcript)

    assert route_result.passed is passed
    if failure_substring:
        assert any(failure_substring in failure for failure in route_result.failures)


@pytest.mark.asyncio
async def test_latest_lead_oracle_matches_person_id_and_mirrors_fields() -> None:
    scenario = scenario_by_id("BT-READ-001")
    services = _services(
        people=_people_page(PersonRecord.model_validate({"id": 42, "assignedUserId": 7}))
    )
    transcript = BattleTestTranscript(
        scenario_id=scenario.id,
        prompt=scenario.prompt_variants[0],
        selected_tool="followupboss_get_latest_lead",
        arguments={"fields": ["id", "name"]},
        response={"person": {"id": 42}, "_metadata": {"count": 1}},
    )

    evaluation = await ReadOnlyBattleTestOracle(services).evaluate(scenario, transcript)

    assert evaluation.passed is True
    assert evaluation.oracle_snapshot is not None
    assert evaluation.oracle_snapshot.expected["person_id"] == 42
    assert services.people.requests == [
        PeopleSearchRequest(assigned_user_id=7, fields=["id", "name"], limit=1, sort="-created")
    ]


@pytest.mark.asyncio
async def test_latest_lead_oracle_handles_empty_result_and_mismatches() -> None:
    scenario = scenario_by_id("BT-READ-001")
    empty_transcript = BattleTestTranscript(
        scenario_id=scenario.id,
        prompt=scenario.prompt_variants[0],
        selected_tool="followupboss_get_latest_lead",
        response={"person": None},
    )

    empty_evaluation = await ReadOnlyBattleTestOracle(_services()).evaluate(
        scenario,
        empty_transcript,
    )

    assert empty_evaluation.passed is True

    unexpected_person = await ReadOnlyBattleTestOracle(_services()).evaluate(
        scenario,
        empty_transcript.model_copy(update={"response": {"person": {"id": 99}}}),
    )
    assert unexpected_person.passed is False
    assert "Expected no latest assigned lead" in unexpected_person.failures[0]

    missing_person_object = await ReadOnlyBattleTestOracle(
        _services(people=_people_page(PersonRecord.model_validate({"id": 42})))
    ).evaluate(scenario, empty_transcript.model_copy(update={"response": {"person": None}}))
    assert missing_person_object.passed is False
    assert "person object" in missing_person_object.failures[0]

    wrong_id = await ReadOnlyBattleTestOracle(
        _services(people=_people_page(PersonRecord.model_validate({"id": 42})))
    ).evaluate(scenario, empty_transcript.model_copy(update={"response": {"person": {"id": 41}}}))
    assert wrong_id.passed is False
    assert "Expected latest lead person id" in wrong_id.failures[0]

    not_an_object = await ReadOnlyBattleTestOracle(_services()).evaluate(
        scenario,
        empty_transcript.model_copy(update={"response": "not-json-object"}),
    )
    assert not_an_object.passed is False
    assert "response to be an object" in not_an_object.failures[0]


@pytest.mark.asyncio
async def test_owned_task_oracle_matches_task_ids_and_mirrors_arguments() -> None:
    scenario = scenario_by_id("BT-READ-002")
    services = _services(tasks=_tasks_page(TaskRecord.model_validate({"id": 1})))
    transcript = BattleTestTranscript(
        scenario_id=scenario.id,
        prompt=scenario.prompt_variants[0],
        selected_tool="followupboss_list_my_overdue_tasks",
        arguments={
            "fields": ["id", "name"],
            "limit": 1,
            "next_token": "next-page",
            "offset": 3,
        },
        response={"tasks": [{"id": 1}]},
    )

    evaluation = await ReadOnlyBattleTestOracle(services).evaluate(scenario, transcript)

    assert evaluation.passed is True
    assert services.tasks.requests == [
        TaskListRequest(
            assigned_user_id=7,
            due="overdue",
            fields=["id", "name"],
            is_completed=False,
            limit=1,
            next_token="next-page",
            offset=3,
        )
    ]


@pytest.mark.asyncio
async def test_owned_task_oracle_ignores_invalid_optional_arguments() -> None:
    scenario = scenario_by_id("BT-READ-003")
    services = _services(tasks=_tasks_page(TaskRecord.model_validate({"id": 5})))
    transcript = BattleTestTranscript(
        scenario_id=scenario.id,
        prompt=scenario.prompt_variants[0],
        selected_tool="followupboss_list_my_tasks_due_today",
        arguments={
            "fields": ["id", 123],
            "limit": "large",
            "next_token": 99,
            "offset": "zero",
        },
        response={"tasks": [{"id": 5}]},
    )

    evaluation = await ReadOnlyBattleTestOracle(services).evaluate(scenario, transcript)

    assert evaluation.passed is True
    assert services.tasks.requests == [
        TaskListRequest(assigned_user_id=7, due="today", is_completed=False)
    ]


@pytest.mark.asyncio
async def test_owned_task_oracle_rejects_boolean_limit_and_offset() -> None:
    """JSON booleans should not be mirrored as integer pagination arguments."""
    scenario = scenario_by_id("BT-READ-003")
    services = _services(tasks=_tasks_page(TaskRecord.model_validate({"id": 5})))
    transcript = BattleTestTranscript(
        scenario_id=scenario.id,
        prompt=scenario.prompt_variants[0],
        selected_tool="followupboss_list_my_tasks_due_today",
        arguments={"limit": True, "offset": False},
        response={"tasks": [{"id": 5}]},
    )

    evaluation = await ReadOnlyBattleTestOracle(services).evaluate(scenario, transcript)

    assert evaluation.passed is True
    assert services.tasks.requests == [
        TaskListRequest(assigned_user_id=7, due="today", is_completed=False)
    ]


@pytest.mark.asyncio
async def test_owned_task_oracle_reports_response_shape_and_id_mismatches() -> None:
    scenario = scenario_by_id("BT-READ-002")
    services = _services(tasks=_tasks_page(TaskRecord.model_validate({"id": 1})))
    base = BattleTestTranscript(
        scenario_id=scenario.id,
        prompt=scenario.prompt_variants[0],
        selected_tool="followupboss_list_my_overdue_tasks",
        response={"tasks": [{"id": 1}]},
    )

    missing_tasks = await ReadOnlyBattleTestOracle(services).evaluate(
        scenario,
        base.model_copy(update={"response": {}}),
    )
    assert missing_tasks.passed is False
    assert "tasks list" in missing_tasks.failures[0]

    not_an_object = await ReadOnlyBattleTestOracle(services).evaluate(
        scenario,
        base.model_copy(update={"response": None}),
    )
    assert not_an_object.passed is False
    assert "response to be an object" in not_an_object.failures[0]

    wrong_ids = await ReadOnlyBattleTestOracle(services).evaluate(
        scenario,
        base.model_copy(update={"response": {"tasks": [{"id": 2}, "ignored"]}}),
    )
    assert wrong_ids.passed is False
    assert "Expected task ids" in wrong_ids.failures[0]


@pytest.mark.asyncio
async def test_oracle_exception_is_recorded_as_evaluation_failure() -> None:
    scenario = scenario_by_id("BT-READ-002")
    transcript = BattleTestTranscript(
        scenario_id=scenario.id,
        prompt=scenario.prompt_variants[0],
        selected_tool="followupboss_list_my_overdue_tasks",
        response={"error": "tool failed"},
    )
    services = FailingTaskBattleTestServices(
        identity=StubIdentityService(7),
        people=StubPeopleService(_people_page()),
        tasks=FailingTasksService(),
    )

    evaluation = await ReadOnlyBattleTestOracle(services).evaluate(scenario, transcript)

    assert evaluation.route_passed is True
    assert evaluation.oracle_passed is False
    assert evaluation.passed is False
    assert evaluation.oracle_snapshot is None
    assert evaluation.failures == ["API oracle failed: invalid task oracle request"]


@pytest.mark.asyncio
async def test_unsupported_note_search_evaluates_without_api_call() -> None:
    scenario = scenario_by_id("BT-READ-005")
    services = _services()
    transcript = BattleTestTranscript(
        scenario_id=scenario.id,
        prompt=scenario.prompt_variants[0],
        unsupported_explained=True,
    )

    evaluation = await ReadOnlyBattleTestOracle(services).evaluate(scenario, transcript)

    assert evaluation.passed is True
    assert evaluation.oracle_snapshot is not None
    assert evaluation.oracle_snapshot.expected == {"unsupported": True, "selected_tool": None}
    assert services.people.requests == []
    assert services.tasks.requests == []


@pytest.mark.asyncio
async def test_upcoming_task_oracle_matches_future_task_ids() -> None:
    scenario = scenario_by_id("BT-READ-004")
    services = _services(tasks=_tasks_page(TaskRecord.model_validate({"id": 8})))
    transcript = BattleTestTranscript(
        scenario_id=scenario.id,
        prompt=scenario.prompt_variants[0],
        selected_tool="followupboss_list_my_upcoming_tasks",
        arguments={"fields": ["id", "dueDate"], "limit": 2},
        response={"tasks": [{"id": 8}]},
    )

    evaluation = await ReadOnlyBattleTestOracle(services).evaluate(scenario, transcript)

    assert evaluation.route_passed is True
    assert evaluation.oracle_passed is True
    assert evaluation.passed is True
    assert services.tasks.requests[0].assigned_user_id == 7
    assert services.tasks.requests[0].due is None
    assert services.tasks.requests[0].due_start is not None
    assert services.tasks.requests[0].fields == ["id", "dueDate"]
    assert services.tasks.requests[0].is_completed is False
    assert services.tasks.requests[0].limit == 2


@pytest.mark.asyncio
async def test_expanded_page_oracles_compare_response_ids() -> None:
    scenario = scenario_by_id("BT-READ-006")
    services = _services(
        smart_lists=_smart_lists_page(SmartListRecord.model_validate({"id": 3, "name": "Hot"}))
    )
    transcript = BattleTestTranscript(
        scenario_id=scenario.id,
        prompt=scenario.prompt_variants[0],
        selected_tool="followupboss_list_smart_lists",
        arguments={"include_all": True},
        response={"smartlists": [{"id": 3, "name": "Hot"}]},
    )

    evaluation = await ReadOnlyBattleTestOracle(services).evaluate(scenario, transcript)

    assert evaluation.passed is True
    assert evaluation.oracle_snapshot is not None
    assert evaluation.oracle_snapshot.expected["smart_list_ids"] == [3]
    assert services.smart_lists.requests[0].include_all is True


@pytest.mark.asyncio
async def test_people_search_oracle_uses_required_smart_list_id() -> None:
    scenario = scenario_by_id("BT-READ-007")
    services = _services(
        people=_people_page(PersonRecord.model_validate({"id": 8, "assignedUserId": 7}))
    )
    transcript = BattleTestTranscript(
        scenario_id=scenario.id,
        prompt=scenario.prompt_variants[0],
        selected_tool="followupboss_search_people",
        arguments={"smart_list_id": 1},
        response={"people": [{"id": 8}]},
    )

    evaluation = await ReadOnlyBattleTestOracle(services).evaluate(scenario, transcript)

    assert evaluation.passed is True
    assert services.people.requests[0].smart_list_id == 1


@pytest.mark.asyncio
async def test_person_activity_oracle_scopes_every_surface_by_person_id() -> None:
    scenario = scenario_by_id("BT-READ-016")
    services = _services(
        appointments=_appointments_page(AppointmentRecord.model_validate({"id": 51})),
        calls=_calls_page(CallRecord.model_validate({"id": 52, "personId": 42})),
        text_messages=_text_messages_page(
            TextMessageRecord.model_validate({"id": 53, "personId": 42})
        ),
        email_events=_email_events_page(
            EmailEventRecord.model_validate({"count": 1, "personId": 42, "type": "open"})
        ),
        events=_events_page(EventRecord.model_validate({"id": 55, "personId": 42})),
    )
    transcript = BattleTestTranscript(
        scenario_id=scenario.id,
        prompt=scenario.prompt_variants[0],
        selected_tool="followupboss_list_person_activity",
        arguments={"person_id": 42, "limit": 5, "offset": 2},
        response={
            "person": {"id": 42},
            "calls": [{"id": 52, "personId": 42}],
            "textmessages": [{"id": 53, "personId": 42}],
            "emEvents": [{"id": None, "personId": 42}],
            "events": [{"id": 55, "personId": 42}],
            "appointments": [{"id": 51}],
        },
    )

    evaluation = await ReadOnlyBattleTestOracle(services).evaluate(scenario, transcript)

    assert evaluation.passed is True
    assert services.calls.requests[0] == CallListRequest(limit=5, offset=2, person_id=42)
    assert services.text_messages.requests[0] == TextMessageListRequest(person_id=42)
    assert services.email_marketing.requests[0] == EmailEventListRequest(
        limit=5,
        offset=2,
        person_id=42,
    )
    assert services.events.requests[0] == EventSearchRequest(limit=5, offset=2, person_id=42)
    assert services.appointments.requests[0] == AppointmentListRequest(
        limit=5,
        offset=2,
        person_id=42,
    )


@pytest.mark.asyncio
async def test_person_activity_oracle_honors_include_flags_and_requires_person_id() -> None:
    scenario = scenario_by_id("BT-READ-016")
    services = _services(
        appointments=_appointments_page(AppointmentRecord.model_validate({"id": 9}))
    )
    transcript = BattleTestTranscript(
        scenario_id=scenario.id,
        prompt=scenario.prompt_variants[0],
        selected_tool="followupboss_list_person_activity",
        arguments={
            "person_id": 42,
            "include_calls": False,
            "include_text_messages": False,
            "include_email_events": False,
            "include_events": False,
            "include_appointments": True,
        },
        response={"person": {"id": 42}, "appointments": [{"id": 9}]},
    )

    evaluation = await ReadOnlyBattleTestOracle(services).evaluate(scenario, transcript)

    assert evaluation.passed is True
    assert services.calls.requests == []
    assert services.text_messages.requests == []
    assert services.email_marketing.requests == []
    assert services.events.requests == []
    assert services.appointments.requests == [AppointmentListRequest(person_id=42)]

    skip_appointments = await ReadOnlyBattleTestOracle(services).evaluate(
        scenario,
        transcript.model_copy(
            update={
                "arguments": {"person_id": 42, "include_appointments": False},
                "response": {
                    "person": {"id": 42},
                    "calls": [],
                    "textmessages": [],
                    "emEvents": [],
                    "events": [],
                },
            }
        ),
    )
    assert skip_appointments.passed is True
    assert services.appointments.requests == [AppointmentListRequest(person_id=42)]

    with pytest.raises(RuntimeError, match="requires a person_id argument"):
        await ReadOnlyBattleTestOracle(_services()).snapshot(
            scenario,
            transcript.model_copy(update={"arguments": {}}),
        )


@pytest.mark.asyncio
async def test_person_activity_oracle_catches_off_scope_activity() -> None:
    scenario = scenario_by_id("BT-READ-016")
    transcript = BattleTestTranscript(
        scenario_id=scenario.id,
        prompt=scenario.prompt_variants[0],
        selected_tool="followupboss_list_person_activity",
        arguments={"person_id": 42},
        response={
            "person": {"id": 42},
            "calls": [{"id": 52, "personId": 43}],
            "textmessages": [],
            "emEvents": [],
            "events": [],
            "appointments": [],
        },
    )

    evaluation = await ReadOnlyBattleTestOracle(
        _services(calls=_calls_page(CallRecord.model_validate({"id": 52, "personId": 42})))
    ).evaluate(scenario, transcript)

    assert evaluation.passed is False
    assert any("off-scope IDs: [52]" in failure for failure in evaluation.failures)


def test_person_activity_private_compare_failure_edges() -> None:
    compare_activity = cast(
        "Callable[[BattleTestTranscript, BattleTestOracleSnapshot], list[str]]",
        getattr(battle_tests_module, "_compare_person_activity_response"),  # noqa: B009
    )
    snapshot = BattleTestOracleSnapshot(
        scenario_id="BT-READ-016",
        kind=BattleTestOracleKind.PERSON_ACTIVITY,
        automated=True,
        expected={"person_id": 42, "resolved_person_id": 42, "call_ids": [1]},
    )

    not_an_object = compare_activity(
        BattleTestTranscript(scenario_id="BT-READ-016", prompt="history", response=None),
        snapshot,
    )
    wrong_shape = compare_activity(
        BattleTestTranscript(
            scenario_id="BT-READ-016",
            prompt="history",
            response={"person": None},
        ),
        snapshot,
    )
    wrong_id_and_missing_calls = compare_activity(
        BattleTestTranscript(
            scenario_id="BT-READ-016",
            prompt="history",
            response={"person": {"id": 43}},
        ),
        snapshot,
    )
    mismatched_call_ids = compare_activity(
        BattleTestTranscript(
            scenario_id="BT-READ-016",
            prompt="history",
            response={"person": {"id": 42}, "calls": [{"id": 2, "personId": 42}]},
        ),
        snapshot,
    )

    assert not_an_object == ["Expected person-activity MCP response to be an object."]
    assert wrong_shape == [
        "Expected person-activity MCP response to include a person object.",
        "Expected person-activity response to include 'calls'.",
    ]
    assert wrong_id_and_missing_calls == [
        "Expected person-activity person id 42, got 43.",
        "Expected person-activity response to include 'calls'.",
    ]
    assert mismatched_call_ids == ["Expected calls ids [1], got [2]."]


@pytest.mark.asyncio
async def test_named_smart_list_grounding_resolves_exact_list_and_people() -> None:
    scenario = scenario_by_id("BT-SMARTLIST-002")
    services = _services(
        smart_lists=_smart_lists_page(
            SmartListRecord.model_validate({"id": 77, "name": "🚨 Eligible For Transfer ✅"})
        ),
        people=_people_page(
            PersonRecord.model_validate(
                {
                    "id": 21,
                    "name": "Jane Zillow",
                    "phones": [{"value": "(555) 000-1111"}],
                }
            )
        ),
    )
    transcript = BattleTestTranscript(
        scenario_id=scenario.id,
        prompt=scenario.prompt_variants[0],
        selected_tool="followupboss_search_people_in_smart_list",
        arguments={"smart_list_name": "Eligible For Transfer", "source": "Zillow", "limit": 10},
        response={
            "smartlist": {"id": 77, "name": "🚨 Eligible For Transfer ✅"},
            "people": [{"id": 21, "name": "Jane Zillow"}],
        },
        assistant_message="Jane Zillow | (555) 000-1111",
    )

    evaluation = await ReadOnlyBattleTestOracle(services).evaluate(scenario, transcript)

    assert evaluation.passed is True
    assert services.smart_lists.requests[0].include_all is True
    assert services.people.requests[0].smart_list_id == 77
    assert services.people.requests[0].source == "Zillow"
    assert services.people.requests[0].limit == 10
    assert evaluation.oracle_snapshot is not None
    assert evaluation.oracle_snapshot.expected["allowed_answer_phones"] == ["5550001111"]


@pytest.mark.asyncio
async def test_named_smart_list_grounding_resolves_list_from_later_page() -> None:
    scenario = scenario_by_id("BT-SMARTLIST-002")
    paginated_smart_lists = PaginatedStubSmartListsService(
        pages=[
            PageResult(
                items=[SmartListRecord.model_validate({"id": 1, "name": "First Page"})],
                metadata=PaginationMetadata(
                    count=1,
                    limit=1,
                    next_token=None,
                    next_link=None,
                    offset=0,
                    total=2,
                ),
            ),
            PageResult(
                items=[SmartListRecord.model_validate({"id": 77, "name": "Eligible For Transfer"})],
                metadata=PaginationMetadata(
                    count=1,
                    limit=1,
                    next_token=None,
                    next_link=None,
                    offset=1,
                    total=2,
                ),
            ),
        ]
    )
    services = StubBattleTestServices(
        identity=StubIdentityService(7),
        people=StubPeopleService(
            _people_page(PersonRecord.model_validate({"id": 21, "name": "Jane Zillow"}))
        ),
        tasks=StubTasksService(_tasks_page()),
        smart_lists=paginated_smart_lists,
    )
    transcript = BattleTestTranscript(
        scenario_id=scenario.id,
        prompt=scenario.prompt_variants[0],
        selected_tool="followupboss_search_people_in_smart_list",
        arguments={"smart_list_name": "Eligible For Transfer", "source": "Zillow"},
        response={
            "smartlist": {"id": 77, "name": "Eligible For Transfer"},
            "people": [{"id": 21, "name": "Jane Zillow"}],
        },
    )

    evaluation = await ReadOnlyBattleTestOracle(services).evaluate(scenario, transcript)

    assert evaluation.passed is True
    assert [request.offset for request in paginated_smart_lists.requests] == [0, 1]


@pytest.mark.asyncio
async def test_named_smart_list_grounding_rejects_off_list_response() -> None:
    scenario = scenario_by_id("BT-SMARTLIST-002")
    services = _services(
        smart_lists=_smart_lists_page(
            SmartListRecord.model_validate({"id": 77, "name": " Eligible   For Transfer "})
        ),
        people=_people_page(PersonRecord.model_validate({"id": 21, "name": "Jane Zillow"})),
    )
    transcript = BattleTestTranscript(
        scenario_id=scenario.id,
        prompt=scenario.prompt_variants[0],
        selected_tool="followupboss_search_people_in_smart_list",
        arguments={"smart_list_name": "Eligible For Transfer", "source": "Zillow"},
        response={
            "smartlist": {"id": 77, "name": "Eligible For Transfer"},
            "people": [{"id": 999, "name": "Off List"}],
        },
    )

    evaluation = await ReadOnlyBattleTestOracle(services).evaluate(scenario, transcript)

    assert evaluation.passed is False
    assert "Expected people ids [21], got [999]." in evaluation.failures


@pytest.mark.asyncio
async def test_named_smart_list_grounding_rejects_answer_leakage() -> None:
    scenario = scenario_by_id("BT-SMARTLIST-002")
    services = _services(
        smart_lists=_smart_lists_page(
            SmartListRecord.model_validate({"id": 77, "name": "Eligible For Transfer"})
        ),
        people=_people_page(
            PersonRecord.model_validate(
                {
                    "id": 21,
                    "name": "Jane Zillow",
                    "phones": [{"value": "555-000-1111"}],
                }
            )
        ),
    )
    transcript = BattleTestTranscript(
        scenario_id=scenario.id,
        prompt=scenario.prompt_variants[0],
        selected_tool="followupboss_search_people_in_smart_list",
        arguments={"smart_list_name": "Eligible For Transfer", "source": "Zillow"},
        response={
            "smartlist": {"id": 77, "name": "Eligible For Transfer"},
            "people": [{"id": 21, "name": "Jane Zillow"}],
        },
        assistant_message="Jane Zillow | 555-000-1111\nOff List Lead | 555-999-0000",
    )

    evaluation = await ReadOnlyBattleTestOracle(services).evaluate(scenario, transcript)

    assert evaluation.passed is False
    assert any("off-list phone" in failure for failure in evaluation.failures)
    assert any("off-list name" in failure for failure in evaluation.failures)


@pytest.mark.asyncio
async def test_named_smart_list_grounding_reports_wrong_helper_provenance() -> None:
    base_scenario = scenario_by_id("BT-SMARTLIST-002")
    scenario = base_scenario.model_copy(
        update={
            "api_oracle": ApiOracleSpec(
                kind=BattleTestOracleKind.NAMED_SMART_LIST_PEOPLE,
                description="No final-answer grounding for this shape.",
                smart_list_name="Eligible For Transfer",
                answer_must_be_grounded=False,
            )
        }
    )
    services = _services(
        smart_lists=_smart_lists_page(
            SmartListRecord.model_validate({"id": 77, "name": "Eligible For Transfer"})
        ),
        people=_people_page(PersonRecord.model_validate({"id": 21, "name": "Jane Zillow"})),
    )
    transcript = BattleTestTranscript(
        scenario_id=scenario.id,
        prompt=scenario.prompt_variants[0],
        selected_tool="followupboss_search_people_in_smart_list",
        arguments={"smart_list_name": "Eligible For Transfer", "source": "Zillow"},
        response={
            "smartlist": {"id": 78, "name": "Wrong List"},
            "people": [{"id": 21, "name": "Jane Zillow"}],
        },
        assistant_message="Off List Lead | 555-999-0000",
    )

    evaluation = await ReadOnlyBattleTestOracle(services).evaluate(scenario, transcript)

    assert evaluation.passed is False
    assert evaluation.failures == ["Expected helper smartlist id 77, got 78."]


@pytest.mark.asyncio
async def test_named_smart_list_grounding_still_catches_broad_wrong_id_path() -> None:
    base_scenario = scenario_by_id("BT-SMARTLIST-002")
    scenario = base_scenario.model_copy(
        update={
            "expected_mcp": ExpectedMcpRoute(
                allowed_tools=("followupboss_search_people",),
                required_argument_keys=("smart_list_id",),
            )
        }
    )
    services = _services(
        smart_lists=_smart_lists_page(
            SmartListRecord.model_validate({"id": 77, "name": "Eligible For Transfer"})
        ),
        people=_people_page(PersonRecord.model_validate({"id": 21, "name": "Jane Zillow"})),
    )
    transcript = BattleTestTranscript(
        scenario_id=scenario.id,
        prompt=scenario.prompt_variants[0],
        selected_tool="followupboss_search_people",
        arguments={"smart_list_id": 78},
        response={"people": [{"id": 21, "name": "Jane Zillow"}]},
    )

    evaluation = await ReadOnlyBattleTestOracle(services).evaluate(scenario, transcript)

    assert evaluation.passed is False
    assert evaluation.failures == [
        "Expected named smart-list search to use smart_list_id 77, got 78."
    ]


@pytest.mark.asyncio
async def test_named_smart_list_grounding_accepts_exact_id_fallback_path() -> None:
    base_scenario = scenario_by_id("BT-SMARTLIST-002")
    scenario = base_scenario.model_copy(
        update={
            "expected_mcp": ExpectedMcpRoute(
                allowed_tools=("followupboss_search_people",),
                required_argument_keys=("smart_list_id",),
            )
        }
    )
    services = _services(
        smart_lists=_smart_lists_page(
            SmartListRecord.model_validate({"id": 77, "name": "Eligible For Transfer"})
        ),
        people=_people_page(PersonRecord.model_validate({"id": 21, "name": "Jane Zillow"})),
    )
    transcript = BattleTestTranscript(
        scenario_id=scenario.id,
        prompt=scenario.prompt_variants[0],
        selected_tool="followupboss_search_people",
        arguments={"smart_list_id": 77},
        response={"people": [{"id": 21, "name": "Jane Zillow"}]},
    )

    evaluation = await ReadOnlyBattleTestOracle(services).evaluate(scenario, transcript)

    assert evaluation.passed is True


@pytest.mark.asyncio
async def test_named_smart_list_grounding_rejects_unexpected_tool_after_custom_route() -> None:
    base_scenario = scenario_by_id("BT-SMARTLIST-002")
    scenario = base_scenario.model_copy(
        update={"expected_mcp": ExpectedMcpRoute(allowed_tools=("unexpected_tool",))}
    )
    services = _services(
        smart_lists=_smart_lists_page(
            SmartListRecord.model_validate({"id": 77, "name": "Eligible For Transfer"})
        ),
        people=_people_page(PersonRecord.model_validate({"id": 21, "name": "Jane Zillow"})),
    )
    transcript = BattleTestTranscript(
        scenario_id=scenario.id,
        prompt=scenario.prompt_variants[0],
        selected_tool="unexpected_tool",
        arguments={},
        response={"people": [{"id": 21, "name": "Jane Zillow"}]},
    )

    evaluation = await ReadOnlyBattleTestOracle(services).evaluate(scenario, transcript)

    assert evaluation.passed is False
    assert (
        "Expected named smart-list people scenario to use "
        "followupboss_search_people_in_smart_list or followupboss_search_people."
    ) in evaluation.failures


def test_named_smart_list_helper_route_private_compare_failure_edges() -> None:
    compare_helper = cast(
        "Callable[..., list[str]]",
        getattr(battle_tests_module, "_compare_named_smart_list_helper_route"),  # noqa: B009
    )
    transcript = BattleTestTranscript(
        scenario_id="BT-SMARTLIST-PRIVATE",
        prompt="Show Zillow leads in Eligible For Transfer",
        selected_tool="followupboss_search_people_in_smart_list",
        arguments={"smart_list_name": "Wrong List"},
        response={},
    )

    wrong_name_failures = compare_helper(
        transcript,
        expected_smart_list_id=77,
        expected_smart_list_name="Eligible For Transfer",
    )
    missing_expected_name_failures = compare_helper(
        transcript,
        expected_smart_list_id=77,
        expected_smart_list_name=None,
    )

    assert "Expected helper smart_list_name 'Eligible For Transfer', got 'Wrong List'." in (
        wrong_name_failures
    )
    assert "Expected helper response to include a smartlist object." in wrong_name_failures
    assert (
        "Expected named smart-list oracle snapshot to include a list name."
        in missing_expected_name_failures
    )


@pytest.mark.asyncio
async def test_named_smart_list_grounding_requires_configured_list_name() -> None:
    base_scenario = scenario_by_id("BT-SMARTLIST-002")
    scenario = base_scenario.model_copy(
        update={
            "api_oracle": ApiOracleSpec(
                kind=BattleTestOracleKind.NAMED_SMART_LIST_PEOPLE,
                description="Missing list name.",
            )
        }
    )
    transcript = BattleTestTranscript(
        scenario_id=scenario.id,
        prompt=scenario.prompt_variants[0],
        selected_tool="followupboss_search_people_in_smart_list",
        arguments={"smart_list_name": "Eligible For Transfer", "source": "Zillow"},
        response={"smartlist": {"id": 77}, "people": []},
    )

    evaluation = await ReadOnlyBattleTestOracle(_services()).evaluate(scenario, transcript)

    assert evaluation.passed is False
    assert evaluation.failures == [
        "API oracle failed: Named smart-list oracle requires a smart_list_name."
    ]


@pytest.mark.asyncio
async def test_named_smart_list_grounding_fails_missing_or_ambiguous_list() -> None:
    scenario = scenario_by_id("BT-SMARTLIST-002")
    transcript = BattleTestTranscript(
        scenario_id=scenario.id,
        prompt=scenario.prompt_variants[0],
        selected_tool="followupboss_search_people_in_smart_list",
        arguments={"smart_list_name": "Eligible For Transfer", "source": "Zillow"},
        response={"smartlist": {"id": 77}, "people": []},
    )
    missing_services = _services()
    ambiguous_services = _services(
        smart_lists=_smart_lists_page(
            SmartListRecord.model_validate({"id": 77, "name": "Eligible For Transfer"}),
            SmartListRecord.model_validate({"id": 78, "name": "eligible for transfer"}),
        ),
    )

    missing = await ReadOnlyBattleTestOracle(missing_services).evaluate(scenario, transcript)
    ambiguous = await ReadOnlyBattleTestOracle(ambiguous_services).evaluate(
        scenario,
        transcript,
    )

    assert missing.passed is False
    assert missing.failures == [
        "API oracle failed: Smart list named 'Eligible For Transfer' was not found."
    ]
    assert ambiguous.passed is False
    assert ambiguous.failures == [
        "API oracle failed: Smart list named 'Eligible For Transfer' is ambiguous; "
        "matched IDs [77, 78]."
    ]


def test_named_smart_list_answer_private_extractors_cover_edge_shapes() -> None:
    phone_tokens = cast(
        "Callable[[str], tuple[str, ...]]",
        getattr(battle_tests_module, "_phone_like_tokens"),  # noqa: B009
    )
    table_names = cast(
        "Callable[[str], tuple[str, ...]]",
        getattr(battle_tests_module, "_table_like_answer_names"),  # noqa: B009
    )
    person_phones = cast(
        "Callable[[Sequence[PersonRecord]], list[JsonValue]]",
        getattr(battle_tests_module, "_person_answer_phones"),  # noqa: B009
    )
    people = [
        PersonRecord.model_validate(
            {
                "id": 1,
                "phones": [
                    {"value": "123"},
                    {"value": "555-000-1111"},
                    {"value": "(555) 000-1111"},
                ],
            }
        )
    ]

    assert phone_tokens("Call abc 123 x 555-111-2222 and 999") == ("555-111-2222",)
    assert table_names(
        "\nName | Phone\n--- | ---\nNo pipe\n555 | Phone\nValid Person | 555-111-2222"
    ) == ("Valid Person",)
    assert person_phones(people) == ["5550001111"]


@pytest.mark.asyncio
async def test_duplicate_and_explicit_note_oracles_compare_single_responses() -> None:
    duplicate_scenario = scenario_by_id("BT-READ-008")
    duplicate_services = _services()
    duplicate_services.people.duplicate = PersonDuplicateCheckRecord(
        found=True,
        matchedBy="email",
    )
    duplicate_transcript = BattleTestTranscript(
        scenario_id=duplicate_scenario.id,
        prompt=duplicate_scenario.prompt_variants[0],
        selected_tool="followupboss_check_duplicate_person",
        arguments={"email": "alex@example.com"},
        response={"found": True, "matchedBy": "email"},
    )

    duplicate_evaluation = await ReadOnlyBattleTestOracle(duplicate_services).evaluate(
        duplicate_scenario,
        duplicate_transcript,
    )

    assert duplicate_evaluation.passed is True
    assert duplicate_services.people.duplicate_requests[0].email == "alex@example.com"

    note_scenario = scenario_by_id("BT-READ-015")
    note_services = _services()
    note_services.notes.note = NoteRecord.model_validate({"id": 12, "body": "ok"})
    note_transcript = BattleTestTranscript(
        scenario_id=note_scenario.id,
        prompt=note_scenario.prompt_variants[0],
        selected_tool="followupboss_get_note",
        arguments={"note_id": 12},
        response={"id": 12, "body": "ok"},
    )

    note_evaluation = await ReadOnlyBattleTestOracle(note_services).evaluate(
        note_scenario,
        note_transcript,
    )

    assert note_evaluation.passed is True
    assert note_services.notes.requests == [12]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("scenario_id", "selected_tool", "response_key", "record_id"),
    [
        ("BT-READ-009", "followupboss_list_unclaimed_people", "people", 9),
        ("BT-READ-010", "followupboss_list_appointments", "appointments", 10),
        ("BT-READ-011", "followupboss_list_calls", "calls", 11),
        ("BT-READ-012", "followupboss_list_text_messages", "textmessages", 12),
        ("BT-READ-013", "followupboss_list_templates", "templates", 13),
        (
            "BT-READ-014",
            "followupboss_list_text_message_templates",
            "textmessagetemplates",
            14,
        ),
    ],
)
async def test_expanded_list_oracles_cover_all_page_surfaces(
    scenario_id: str,
    selected_tool: str,
    response_key: str,
    record_id: int,
) -> None:
    services = _services()
    services.people.unclaimed_page = _people_page(PersonRecord.model_validate({"id": 9}))
    services.appointments.page = _appointments_page(AppointmentRecord.model_validate({"id": 10}))
    services.calls.page = _calls_page(CallRecord.model_validate({"id": 11}))
    services.text_messages.page = _text_messages_page(TextMessageRecord.model_validate({"id": 12}))
    services.templates.page = _templates_page(TemplateRecord.model_validate({"id": 13}))
    services.text_message_templates.page = _text_templates_page(
        TextMessageTemplateRecord.model_validate({"id": 14})
    )
    scenario = scenario_by_id(scenario_id)
    transcript = BattleTestTranscript(
        scenario_id=scenario.id,
        prompt=scenario.prompt_variants[0],
        selected_tool=selected_tool,
        response={response_key: [{"id": record_id}]},
    )

    evaluation = await ReadOnlyBattleTestOracle(services).evaluate(scenario, transcript)

    assert evaluation.passed is True


def test_expanded_page_comparison_reports_shape_mismatches() -> None:
    compare_page = cast(
        "Callable[[BattleTestTranscript, BattleTestOracleSnapshot], list[str]]",
        getattr(battle_tests_module, "_compare_page_response"),  # noqa: B009
    )
    snapshot = BattleTestOracleSnapshot(
        scenario_id="TEST",
        kind=BattleTestOracleKind.SMART_LISTS,
        automated=True,
        expected={"response_key": "smartlists", "smart_list_ids": [1]},
    )

    assert compare_page(
        BattleTestTranscript(scenario_id="TEST", prompt="p", response=[]),
        snapshot,
    ) == ["Expected paginated MCP response to be an object."]
    assert compare_page(
        BattleTestTranscript(scenario_id="TEST", prompt="p", response={"smartlists": []}),
        snapshot.model_copy(update={"expected": {}}),
    ) == ["Expected page oracle snapshot to include a response key."]
    assert compare_page(
        BattleTestTranscript(scenario_id="TEST", prompt="p", response={"smartlists": {}}),
        snapshot,
    ) == ["Expected MCP response to include a 'smartlists' list."]
    assert compare_page(
        BattleTestTranscript(scenario_id="TEST", prompt="p", response={"smartlists": [{"id": 2}]}),
        snapshot,
    ) == ["Expected smartlists ids [1], got [2]."]
    assert compare_page(
        BattleTestTranscript(scenario_id="TEST", prompt="p", response={"smartlists": []}),
        snapshot.model_copy(update={"expected": {"response_key": "smartlists"}}),
    ) == ["Expected smartlists ids None, got []."]


def test_expanded_single_response_comparisons_report_mismatches() -> None:
    compare_duplicate = cast(
        "Callable[[BattleTestTranscript, BattleTestOracleSnapshot], list[str]]",
        getattr(battle_tests_module, "_compare_duplicate_response"),  # noqa: B009
    )
    compare_single = cast(
        Any,
        getattr(battle_tests_module, "_compare_single_id_response"),  # noqa: B009
    )
    duplicate_snapshot = BattleTestOracleSnapshot(
        scenario_id="TEST",
        kind=BattleTestOracleKind.PERSON_DUPLICATE_CHECK,
        automated=True,
        expected={"found": True, "matched_by": "email"},
    )
    note_snapshot = BattleTestOracleSnapshot(
        scenario_id="TEST",
        kind=BattleTestOracleKind.EXPLICIT_NOTE,
        automated=True,
        expected={"note_id": 5},
    )

    assert compare_duplicate(
        BattleTestTranscript(scenario_id="TEST", prompt="p", response=[]),
        duplicate_snapshot,
    ) == ["Expected duplicate-check MCP response to be an object."]
    assert compare_duplicate(
        BattleTestTranscript(
            scenario_id="TEST",
            prompt="p",
            response={"found": False, "matchedBy": "phone"},
        ),
        duplicate_snapshot,
    ) == [
        "Expected duplicate found=True, got False.",
        "Expected duplicate matchedBy='email', got 'phone'.",
    ]
    assert compare_single(
        BattleTestTranscript(scenario_id="TEST", prompt="p", response=[]),
        note_snapshot,
        expected_key="note_id",
    ) == ["Expected single-object MCP response to be an object."]
    assert compare_single(
        BattleTestTranscript(scenario_id="TEST", prompt="p", response={"id": 6}),
        note_snapshot,
        expected_key="note_id",
    ) == ["Expected response id 5, got 6."]


def test_expanded_oracle_private_coercion_helpers_cover_edge_shapes() -> None:
    optional_bool = cast(
        "Callable[[JsonValue], bool | None]",
        getattr(battle_tests_module, "_optional_bool"),  # noqa: B009
    )
    record_id = cast(
        "Callable[[object], JsonValue]",
        getattr(battle_tests_module, "_record_id"),  # noqa: B009
    )

    assert optional_bool("true") is None
    assert record_id({"id": 99}) == 99


@pytest.mark.asyncio
async def test_explicit_note_oracle_requires_note_id_argument() -> None:
    scenario = scenario_by_id("BT-READ-015")
    transcript = BattleTestTranscript(
        scenario_id=scenario.id,
        prompt=scenario.prompt_variants[0],
        selected_tool="followupboss_get_note",
        response={"id": 1},
    )

    evaluation = await ReadOnlyBattleTestOracle(_services()).evaluate(scenario, transcript)

    assert evaluation.passed is False
    assert any("without required arguments" in failure for failure in evaluation.failures)
    with pytest.raises(RuntimeError, match="requires a note_id argument"):
        await ReadOnlyBattleTestOracle(_services()).snapshot(scenario, transcript)


@pytest.mark.asyncio
async def test_route_only_pending_oracle_still_reports_incomplete_custom_scenario() -> None:
    scenario = BattleTestScenario(
        id="BT-READ-CUSTOM",
        grade=BattleTestGrade.MUST_ROUTE,
        prompt_variants=("Use a placeholder route",),
        expected_mcp=ExpectedMcpRoute(allowed_tools=("safe_tool",)),
        api_oracle=ApiOracleSpec(
            kind=BattleTestOracleKind.ROUTE_ONLY_PENDING,
            description="Custom pending oracle for fallback coverage.",
        ),
    )
    transcript = BattleTestTranscript(
        scenario_id=scenario.id,
        prompt=scenario.prompt_variants[0],
        selected_tool="safe_tool",
        response={"ok": True},
    )

    evaluation = await ReadOnlyBattleTestOracle(_services()).evaluate(scenario, transcript)

    assert evaluation.route_passed is True
    assert evaluation.oracle_passed is False
    assert evaluation.passed is False
    assert "does not have an automated API oracle yet" in evaluation.failures[0]


@pytest.mark.asyncio
async def test_route_only_pending_oracle_passes_safety_grades() -> None:
    scenario = BattleTestScenario(
        id="BT-READ-CLARIFY",
        grade=BattleTestGrade.MUST_CLARIFY,
        prompt_variants=("Which one?",),
        expected_mcp=ExpectedMcpRoute(),
        api_oracle=ApiOracleSpec(
            kind=BattleTestOracleKind.ROUTE_ONLY_PENDING,
            description="Route-only safety check.",
        ),
    )
    transcript = BattleTestTranscript(
        scenario_id=scenario.id,
        prompt=scenario.prompt_variants[0],
        clarified=True,
    )

    evaluation = await ReadOnlyBattleTestOracle(_services()).evaluate(scenario, transcript)

    assert evaluation.passed is True
    assert evaluation.oracle_snapshot is not None
    assert evaluation.oracle_snapshot.expected == {"route_only": True}


@pytest.mark.asyncio
async def test_conversation_evaluation_summarizes_per_turn_failures() -> None:
    conversation = read_only_battle_test_conversations(BattleTestConversationKind.MULTI_TURN)[0]
    services = _services(
        people=_people_page(PersonRecord.model_validate({"id": 42, "assignedUserId": 7})),
        tasks=_tasks_page(TaskRecord.model_validate({"id": 5})),
    )
    transcript = BattleTestConversationTranscript(
        conversation_id=conversation.id,
        kind=conversation.kind,
        turn_transcripts=(
            BattleTestTranscript(
                scenario_id="BT-CHAIN-001-T01",
                prompt="Show my latest lead",
                selected_tool="followupboss_get_latest_lead",
                response={"person": {"id": 42}},
            ),
            BattleTestTranscript(
                scenario_id="BT-CHAIN-001-T02",
                prompt="Now show what I need to do today",
                selected_tool="followupboss_list_my_tasks_due_today",
                response={"tasks": [{"id": 999}]},
            ),
        ),
    )

    evaluation = await evaluate_battle_test_conversation(
        ReadOnlyBattleTestOracle(services),
        conversation,
        transcript,
    )

    assert evaluation.passed is False
    assert [turn.scenario_id for turn in evaluation.turn_evaluations] == [
        "BT-CHAIN-001-T01",
        "BT-CHAIN-001-T02",
    ]
    assert any("Expected task ids" in failure for failure in evaluation.failures)


@pytest.mark.asyncio
async def test_conversation_evaluation_reports_bundle_mismatches() -> None:
    conversation = read_only_battle_test_conversations(BattleTestConversationKind.MULTI_TURN)[0]
    transcript = BattleTestConversationTranscript(
        conversation_id="BT-CHAIN-WRONG",
        kind=BattleTestConversationKind.MULTI_ASK,
        turn_transcripts=(
            BattleTestTranscript(
                scenario_id="BT-CHAIN-999-T01",
                prompt="Unexpected turn",
                selected_tool="followupboss_get_latest_lead",
                response={"person": None},
            ),
        ),
    )

    evaluation = await evaluate_battle_test_conversation(
        ReadOnlyBattleTestOracle(_services()),
        conversation,
        transcript,
    )

    assert evaluation.passed is False
    assert any("does not match" in failure for failure in evaluation.failures)
    assert any("kind" in failure for failure in evaluation.failures)
    assert any("Missing transcript" in failure for failure in evaluation.failures)
    assert any("Unexpected transcript" in failure for failure in evaluation.failures)


@pytest.mark.asyncio
async def test_evaluate_battle_test_conversations_filters_to_captured_items() -> None:
    conversation = read_only_battle_test_conversations(BattleTestConversationKind.MULTI_ASK)[0]
    transcript = BattleTestConversationTranscript(
        conversation_id=conversation.id,
        kind=conversation.kind,
        turn_transcripts=(
            BattleTestTranscript(
                scenario_id=f"{conversation.id}-T01",
                prompt=conversation.prompt or "",
                selected_tool="followupboss_get_latest_lead",
                response={"person": {"id": 42}},
            ),
            BattleTestTranscript(
                scenario_id=f"{conversation.id}-T02",
                prompt=conversation.prompt or "",
                selected_tool="followupboss_list_my_tasks_due_today",
                response={"tasks": []},
            ),
        ),
    )

    evaluations = await evaluate_battle_test_conversations(
        ReadOnlyBattleTestOracle(
            _services(people=_people_page(PersonRecord.model_validate({"id": 42})))
        ),
        (transcript,),
        conversations=(conversation,),
    )

    assert len(evaluations) == 1
    assert evaluations[0].conversation_id == conversation.id


@pytest.mark.asyncio
async def test_route_failure_skips_oracle_snapshot() -> None:
    scenario = scenario_by_id("BT-READ-001")
    transcript = BattleTestTranscript(
        scenario_id=scenario.id,
        prompt=scenario.prompt_variants[0],
        selected_tool="followupboss_search_people",
        response={"people": []},
    )

    evaluation = await ReadOnlyBattleTestOracle(_services()).evaluate(scenario, transcript)

    assert evaluation.route_passed is False
    assert evaluation.oracle_snapshot is None
    assert "forbidden tool" in evaluation.failures[0]


@pytest.mark.asyncio
async def test_oracle_requires_authenticated_user_id() -> None:
    scenario = scenario_by_id("BT-READ-001")
    transcript = BattleTestTranscript(
        scenario_id=scenario.id,
        prompt=scenario.prompt_variants[0],
        selected_tool="followupboss_get_latest_lead",
        response={"person": None},
    )

    evaluation = await ReadOnlyBattleTestOracle(_services(user_id=None)).evaluate(
        scenario,
        transcript,
    )

    assert evaluation.route_passed is True
    assert evaluation.oracle_passed is False
    assert evaluation.passed is False
    assert evaluation.failures == [
        "API oracle failed: Authenticated Follow Up Boss user id is unavailable."
    ]


def test_failure_category_derivation_covers_common_drift_modes() -> None:
    assert (
        categorize_battle_test_failure(
            "Expected one of ('followupboss_list_my_upcoming_tasks',), got None."
        )
        is BattleTestFailureCategory.ROUTE_NO_CALL
    )
    assert (
        categorize_battle_test_failure(
            "Expected one of ('followupboss_list_my_upcoming_tasks',), "
            "got 'followupboss_list_my_tasks_due_today'."
        )
        is BattleTestFailureCategory.ROUTE_WRONG_TOOL
    )
    assert (
        categorize_battle_test_failure(
            "Expected the assistant to explain the unsupported API capability."
        )
        is BattleTestFailureCategory.UNSUPPORTED_NOT_EXPLAINED
    )
    assert (
        categorize_battle_test_failure(
            "API oracle failed: Transport error while calling Follow Up Boss."
        )
        is BattleTestFailureCategory.ORACLE_TRANSPORT_ERROR
    )
    assert (
        categorize_battle_test_failure("Expected task ids [1], got [2].")
        is BattleTestFailureCategory.ORACLE_RESPONSE_MISMATCH
    )
    assert categorize_battle_test_failure("surprising failure") is BattleTestFailureCategory.UNKNOWN
    assert categorize_battle_test_failures(
        (
            "Expected one of ('safe',), got None.",
            "Expected one of ('safe',), got None.",
        )
    ) == (BattleTestFailureCategory.ROUTE_NO_CALL,)


def test_build_battle_test_run_artifact_summarizes_results() -> None:
    metadata = BattleTestRunMetadata(run_id="run-1", client="unit")
    artifact = build_battle_test_run_artifact(
        metadata=metadata,
        evaluations=(
            BattleTestEvaluation(
                scenario_id="BT-READ-001",
                grade=BattleTestGrade.MUST_ROUTE,
                route_passed=True,
                oracle_passed=True,
                passed=True,
            ),
            BattleTestEvaluation(
                scenario_id="BT-READ-002",
                grade=BattleTestGrade.MUST_ROUTE,
                route_passed=True,
                oracle_passed=False,
                passed=False,
                failures=["Expected task ids [1], got [2]."],
            ),
        ),
        total_scenarios=4,
        missing_scenario_ids=("BT-READ-003",),
        unknown_transcript_scenario_ids=("BT-READ-999",),
    )

    assert artifact.metadata == metadata
    assert artifact.summary.total_scenarios == 4
    assert artifact.summary.evaluated_scenarios == 2
    assert artifact.summary.passed_scenarios == 1
    assert artifact.summary.failed_scenarios == 1
    assert artifact.summary.missing_scenarios == 1
    assert artifact.summary.unknown_transcripts == 1
    assert artifact.summary.failure_category_counts == {"oracle_response_mismatch": 1}
    assert artifact.summary.overall_passed is False


def test_battle_test_run_artifact_loads_without_failure_summary() -> None:
    artifact = BattleTestRunArtifact.model_validate(
        {
            "metadata": {"run_id": "legacy-run", "client": "unit"},
            "summary": {
                "total_scenarios": 1,
                "evaluated_scenarios": 1,
                "passed_scenarios": 1,
                "failed_scenarios": 0,
                "missing_scenarios": 0,
                "unknown_transcripts": 0,
                "overall_passed": True,
            },
            "evaluations": [
                {
                    "scenario_id": "BT-READ-001",
                    "grade": "MUST_ROUTE",
                    "route_passed": True,
                    "oracle_passed": True,
                    "passed": True,
                }
            ],
        }
    )

    assert artifact.summary.failure_category_counts == {}
    assert artifact.evaluations[0].failure_categories == ()


def test_write_battle_test_run_artifact_creates_parent_directories(tmp_path: Path) -> None:
    artifact = build_battle_test_run_artifact(
        metadata=BattleTestRunMetadata(
            run_id="run-1",
            client="unit",
            environment="test",
            started_at="2026-05-18T01:00:00Z",
            notes=("read-only",),
        ),
        evaluations=(),
        total_scenarios=0,
    )
    output_path = tmp_path / "nested" / "battle-test-run.json"

    write_battle_test_run_artifact(artifact, output_path)

    assert output_path.read_text(encoding="utf-8").endswith("\n")
    assert '"run_id": "run-1"' in output_path.read_text(encoding="utf-8")
    assert '"overall_passed": true' in output_path.read_text(encoding="utf-8")


def test_mcp_tool_result_to_json_extracts_structured_content() -> None:
    result = StubMcpToolResult(structured_content={"person": {"id": 42}, "ok": True})

    assert mcp_tool_result_to_json(result) == {"person": {"id": 42}, "ok": True}


def test_mcp_tool_result_to_json_extracts_text_content() -> None:
    result = StubMcpToolResult(content=(StubMcpTextContent("hello"), object()))

    assert mcp_tool_result_to_json(result) == {"content": [{"type": "text", "text": "hello"}]}


def test_mcp_tool_result_to_json_coerces_model_dump_result() -> None:
    transcript = BattleTestTranscript(
        scenario_id="BT-READ-005",
        prompt="Show notes",
        unsupported_explained=True,
    )

    result = mcp_tool_result_to_json(transcript)

    assert isinstance(result, dict)
    assert result["scenario_id"] == "BT-READ-005"


def test_mcp_tool_result_to_json_rejects_content_without_text_items() -> None:
    result = StubMcpToolResult(content=(object(),))

    with pytest.raises(TypeError, match="not JSON serializable"):
        mcp_tool_result_to_json(result)


def test_mcp_tool_result_to_json_rejects_unstructured_objects() -> None:
    with pytest.raises(TypeError, match="not JSON serializable"):
        mcp_tool_result_to_json(object())


@pytest.mark.asyncio
async def test_capture_mcp_tool_transcript_executes_selected_tool() -> None:
    client = StubMcpClient(results=[StubMcpToolResult(structured_content={"person": {"id": 42}})])
    tool_call = BattleTestToolCall(
        scenario_id="BT-READ-001",
        prompt="What is my latest lead?",
        tool_name="followupboss_get_latest_lead",
        arguments={"fields": ["id"]},
        assistant_message="Using the latest lead helper.",
    )

    transcript = await capture_mcp_tool_transcript(client, tool_call)

    assert client.calls == [("followupboss_get_latest_lead", {"fields": ["id"]})]
    assert transcript == BattleTestTranscript(
        scenario_id="BT-READ-001",
        prompt="What is my latest lead?",
        selected_tool="followupboss_get_latest_lead",
        arguments={"fields": ["id"]},
        response={"person": {"id": 42}},
        assistant_message="Using the latest lead helper.",
    )


@pytest.mark.asyncio
async def test_capture_mcp_tool_transcript_sends_none_for_empty_arguments() -> None:
    client = StubMcpClient(results=[{"person": None}])
    tool_call = BattleTestToolCall(
        scenario_id="BT-READ-001",
        prompt="Anything new for me?",
        tool_name="followupboss_get_latest_lead",
    )

    transcript = await capture_mcp_tool_transcript(client, tool_call)

    assert client.calls == [("followupboss_get_latest_lead", None)]
    assert transcript.response == {"person": None}


@pytest.mark.asyncio
async def test_capture_mcp_tool_transcripts_preserves_order() -> None:
    client = StubMcpClient(results=[{"person": None}, {"tasks": []}])
    transcripts = await capture_mcp_tool_transcripts(
        client,
        (
            BattleTestToolCall(
                scenario_id="BT-READ-001",
                prompt="Anything new for me?",
                tool_name="followupboss_get_latest_lead",
            ),
            BattleTestToolCall(
                scenario_id="BT-READ-002",
                prompt="What am I late on?",
                tool_name="followupboss_list_my_overdue_tasks",
            ),
        ),
    )

    assert [transcript.scenario_id for transcript in transcripts] == ["BT-READ-001", "BT-READ-002"]
    assert [call[0] for call in client.calls] == [
        "followupboss_get_latest_lead",
        "followupboss_list_my_overdue_tasks",
    ]


@pytest.mark.asyncio
async def test_run_battle_test_tool_calls_writes_artifact(tmp_path: Path) -> None:
    scenario = scenario_by_id("BT-READ-001")
    client = StubMcpClient(results=[StubMcpToolResult(structured_content={"person": {"id": 42}})])
    services = _services(
        people=_people_page(PersonRecord.model_validate({"id": 42, "assignedUserId": 7}))
    )
    output_path = tmp_path / "runs" / "run.json"

    artifact = await run_battle_test_tool_calls(
        client,
        ReadOnlyBattleTestOracle(services),
        (
            BattleTestToolCall(
                scenario_id=scenario.id,
                prompt=scenario.prompt_variants[0],
                tool_name="followupboss_get_latest_lead",
            ),
        ),
        metadata=BattleTestRunMetadata(run_id="run-3", client="unit"),
        scenarios=(scenario,),
        artifact_path=output_path,
    )

    assert artifact.summary.overall_passed is True
    assert output_path.exists()
    assert '"run_id": "run-3"' in output_path.read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_run_battle_test_tool_calls_can_skip_artifact_writing() -> None:
    scenario = scenario_by_id("BT-READ-005")
    client = StubMcpClient(results=[{"content": [{"type": "text", "text": "Unsupported."}]}])

    artifact = await run_battle_test_tool_calls(
        client,
        ReadOnlyBattleTestOracle(_services()),
        (
            BattleTestToolCall(
                scenario_id=scenario.id,
                prompt=scenario.prompt_variants[0],
                tool_name="followupboss_search_notes",
                assistant_message="That note search is unsupported.",
            ),
        ),
        metadata=BattleTestRunMetadata(run_id="run-4", client="unit"),
        scenarios=(scenario,),
    )

    assert artifact.summary.overall_passed is False
    assert client.calls == [("followupboss_search_notes", None)]


@pytest.mark.asyncio
async def test_evaluate_battle_test_run_builds_artifact_with_missing_and_unknown_transcripts() -> (
    None
):
    scenario = scenario_by_id("BT-READ-001")
    transcript = BattleTestTranscript(
        scenario_id=scenario.id,
        prompt=scenario.prompt_variants[0],
        selected_tool="followupboss_get_latest_lead",
        response={"person": {"id": 42}},
    )
    unknown = BattleTestTranscript(
        scenario_id="BT-READ-999",
        prompt="Unknown",
        selected_tool="followupboss_get_identity",
        response={"id": 7},
    )
    services = _services(
        people=_people_page(PersonRecord.model_validate({"id": 42, "assignedUserId": 7}))
    )

    artifact = await evaluate_battle_test_run(
        ReadOnlyBattleTestOracle(services),
        (transcript, unknown),
        metadata=BattleTestRunMetadata(run_id="run-1", client="unit"),
        scenarios=(scenario, scenario_by_id("BT-READ-005")),
    )

    assert artifact.summary.total_scenarios == 2
    assert artifact.summary.evaluated_scenarios == 1
    assert artifact.summary.passed_scenarios == 1
    assert artifact.summary.failed_scenarios == 0
    assert artifact.summary.missing_scenarios == 1
    assert artifact.summary.unknown_transcripts == 1
    assert artifact.summary.overall_passed is False
    assert artifact.missing_scenario_ids == ("BT-READ-005",)
    assert artifact.unknown_transcript_scenario_ids == ("BT-READ-999",)


@pytest.mark.asyncio
async def test_evaluate_battle_test_run_passes_when_all_scenarios_pass() -> None:
    scenario = scenario_by_id("BT-READ-005")
    transcript = BattleTestTranscript(
        scenario_id=scenario.id,
        prompt=scenario.prompt_variants[0],
        unsupported_explained=True,
    )

    artifact = await evaluate_battle_test_run(
        ReadOnlyBattleTestOracle(_services()),
        (transcript,),
        metadata=BattleTestRunMetadata(run_id="run-2", client="unit"),
        scenarios=(scenario,),
    )

    assert artifact.summary.evaluated_scenarios == 1
    assert artifact.summary.passed_scenarios == 1
    assert artifact.summary.overall_passed is True


@pytest.mark.asyncio
async def test_evaluate_model_profile_battle_test_runs_keeps_profiles_separate(
    tmp_path: Path,
) -> None:
    scenario = scenario_by_id("BT-READ-005")
    gpt_transcript = BattleTestTranscript(
        scenario_id=scenario.id,
        prompt=scenario.prompt_variants[0],
        unsupported_explained=True,
    )

    artifacts = await evaluate_model_profile_battle_test_runs(
        ReadOnlyBattleTestOracle(_services()),
        {"gpt-5.5-low-reasoning": (gpt_transcript,)},
        run_id_prefix="read-only-20260518",
        client="cursor",
        environment="staging",
        started_at="2026-05-18T02:00:00Z",
        notes=("model comparison",),
        scenarios=(scenario,),
        artifact_directory=tmp_path,
    )

    assert [
        artifact.metadata.model_profile.id
        for artifact in artifacts
        if artifact.metadata.model_profile
    ] == [
        "gpt-5.5-low-reasoning",
        "sonnet-4.6",
    ]
    assert artifacts[0].summary.overall_passed is True
    assert artifacts[1].summary.overall_passed is False
    assert artifacts[1].missing_scenario_ids == ("BT-READ-005",)
    gpt_artifact = tmp_path / "read-only-20260518-gpt-5.5-low-reasoning.json"
    sonnet_artifact = tmp_path / "read-only-20260518-sonnet-4.6.json"
    assert gpt_artifact.exists()
    assert sonnet_artifact.exists()
    assert '"reasoning_effort": "low"' in gpt_artifact.read_text(encoding="utf-8")
    assert '"model": "claude-sonnet-4-6"' in sonnet_artifact.read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_evaluate_model_profile_battle_test_runs_can_skip_artifact_directory() -> None:
    scenario = scenario_by_id("BT-READ-005")
    profile = battle_test_model_profile_by_id("sonnet-4.6")
    transcript = BattleTestTranscript(
        scenario_id=scenario.id,
        prompt=scenario.prompt_variants[0],
        unsupported_explained=True,
    )

    artifacts = await evaluate_model_profile_battle_test_runs(
        ReadOnlyBattleTestOracle(_services()),
        {"sonnet-4.6": (transcript,)},
        run_id_prefix="read-only-20260518",
        client="cursor",
        profiles=(profile,),
        scenarios=(scenario,),
    )

    assert len(artifacts) == 1
    assert artifacts[0].metadata.run_id == "read-only-20260518-sonnet-4.6"
    assert artifacts[0].summary.overall_passed is True
