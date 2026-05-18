"""Tests for MCP battle-test scenario and oracle helpers."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from pathlib import Path
from typing import cast

import pytest

import followupboss_mcp.battle_tests as battle_tests_module
import followupboss_mcp.mcp_tools as mcp_tools_module
from followupboss_mcp.battle_tests import (
    ApiOracleSpec,
    BattleTestEvaluation,
    BattleTestGrade,
    BattleTestModelProfile,
    BattleTestModelProvider,
    BattleTestOracleKind,
    BattleTestRunMetadata,
    BattleTestScenario,
    BattleTestToolCall,
    BattleTestTranscript,
    ExpectedMcpRoute,
    ReadOnlyBattleTestOracle,
    battle_test_model_profile_by_id,
    battle_test_model_profiles,
    build_battle_test_run_artifact,
    build_model_profile_run_metadata,
    capture_mcp_tool_transcript,
    capture_mcp_tool_transcripts,
    evaluate_battle_test_run,
    evaluate_model_profile_battle_test_runs,
    evaluate_transcript_route,
    expand_battle_test_prompt_variants,
    mcp_tool_result_to_json,
    read_only_battle_test_scenarios,
    run_battle_test_tool_calls,
    scenario_by_id,
    write_battle_test_run_artifact,
)
from followupboss_mcp.models.identity import IdentityResponse
from followupboss_mcp.models.people import PeopleSearchRequest, PersonRecord
from followupboss_mcp.models.tasks import TaskListRequest, TaskRecord
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
    requests: list[PeopleSearchRequest] = field(default_factory=list)

    async def search_people(
        self, request: PeopleSearchRequest | None = None
    ) -> PageResult[PersonRecord]:
        self.requests.append(request or PeopleSearchRequest())
        return self.page


@dataclass
class StubTasksService:
    page: PageResult[TaskRecord]
    requests: list[TaskListRequest] = field(default_factory=list)

    async def list_tasks(self, request: TaskListRequest | None = None) -> PageResult[TaskRecord]:
        self.requests.append(request or TaskListRequest())
        return self.page


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


@dataclass
class FailingTaskBattleTestServices:
    identity: StubIdentityService
    people: StubPeopleService
    tasks: FailingTasksService


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
) -> StubBattleTestServices:
    return StubBattleTestServices(
        identity=StubIdentityService(user_id),
        people=StubPeopleService(people or _people_page()),
        tasks=StubTasksService(tasks or _tasks_page()),
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
    assert all(len(scenario.prompt_variants) == 20 for scenario in scenarios)
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
                failures=["oracle mismatch"],
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
    assert artifact.summary.overall_passed is False


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
