"""Tests for MCP battle-test scenario and oracle helpers."""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from followupboss_mcp.battle_tests import (
    ApiOracleSpec,
    BattleTestGrade,
    BattleTestOracleKind,
    BattleTestScenario,
    BattleTestTranscript,
    ExpectedMcpRoute,
    ReadOnlyBattleTestOracle,
    evaluate_transcript_route,
    read_only_battle_test_scenarios,
    scenario_by_id,
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
class StubBattleTestServices:
    identity: StubIdentityService
    people: StubPeopleService
    tasks: StubTasksService


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
    assert all(len(scenario.prompt_variants) == 5 for scenario in scenarios)
    assert scenario_by_id("BT-READ-001").expected_mcp.allowed_tools == (
        "followupboss_get_latest_lead",
    )
    with pytest.raises(KeyError):
        scenario_by_id("BT-READ-999")


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
async def test_pending_route_only_scenario_is_not_oracle_complete() -> None:
    scenario = scenario_by_id("BT-READ-004")
    transcript = BattleTestTranscript(
        scenario_id=scenario.id,
        prompt=scenario.prompt_variants[0],
        selected_tool="followupboss_list_tasks",
        response={"tasks": []},
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

    with pytest.raises(RuntimeError, match="user id is unavailable"):
        await ReadOnlyBattleTestOracle(_services(user_id=None)).evaluate(scenario, transcript)
