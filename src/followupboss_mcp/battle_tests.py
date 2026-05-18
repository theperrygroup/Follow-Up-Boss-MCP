"""Scenario models and oracle helpers for MCP battle testing."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from enum import StrEnum
from typing import Protocol

from pydantic import Field, model_validator

from followupboss_mcp.models.common import JsonValue, RequestModel, ResponseModel
from followupboss_mcp.models.identity import IdentityResponse
from followupboss_mcp.models.people import PeopleSearchRequest, PersonRecord
from followupboss_mcp.models.tasks import TaskListRequest, TaskRecord
from followupboss_mcp.pagination import PageResult

type JsonObject = dict[str, JsonValue]


class BattleTestGrade(StrEnum):
    """Allowed scenario grades for prompt-level MCP battle tests."""

    MUST_ROUTE = "MUST_ROUTE"
    MAY_ROUTE = "MAY_ROUTE"
    MUST_CLARIFY = "MUST_CLARIFY"
    MUST_REQUIRE_ID = "MUST_REQUIRE_ID"
    MUST_EXPLAIN_UNSUPPORTED = "MUST_EXPLAIN_UNSUPPORTED"


class BattleTestOracleKind(StrEnum):
    """Supported API-oracle families for read-only battle-test scenarios."""

    LATEST_ASSIGNED_LEAD = "latest_assigned_lead"
    MY_OVERDUE_TASKS = "my_overdue_tasks"
    MY_TASKS_DUE_TODAY = "my_tasks_due_today"
    ROUTE_ONLY_PENDING = "route_only_pending"
    UNSUPPORTED_NOTE_SEARCH = "unsupported_note_search"


class ExpectedMcpRoute(RequestModel):
    """Expected MCP tool-selection contract for one scenario."""

    allowed_tools: tuple[str, ...] = ()
    forbidden_tools: tuple[str, ...] = ()
    required_argument_keys: tuple[str, ...] = ()


class ApiOracleSpec(RequestModel):
    """Description of the direct API truth check for one scenario."""

    kind: BattleTestOracleKind
    description: str


class BattleTestScenario(RequestModel):
    """Machine-readable vague-prompt battle-test scenario."""

    id: str
    grade: BattleTestGrade
    prompt_variants: tuple[str, ...]
    expected_mcp: ExpectedMcpRoute
    api_oracle: ApiOracleSpec
    response_assertions: tuple[str, ...] = ()
    cleanup: str = "none"

    @model_validator(mode="after")
    def _require_prompts(self) -> BattleTestScenario:
        """Require at least one non-empty prompt variant.

        Returns:
            The validated scenario.

        Raises:
            ValueError: If no prompt variants are present or a variant is blank.
        """
        if not self.prompt_variants or any(not prompt.strip() for prompt in self.prompt_variants):
            raise ValueError("Battle-test scenarios must include non-empty prompt variants.")
        return self


class BattleTestTranscript(RequestModel):
    """Captured chatbot interaction for one battle-test prompt."""

    scenario_id: str
    prompt: str
    selected_tool: str | None = None
    arguments: JsonObject = Field(default_factory=dict)
    response: JsonValue = None
    assistant_message: str | None = None
    clarified: bool = False
    unsupported_explained: bool = False


class BattleTestRouteResult(ResponseModel):
    """Route-level evaluation result for one captured transcript."""

    scenario_id: str
    grade: BattleTestGrade
    selected_tool: str | None
    passed: bool
    failures: list[str] = Field(default_factory=list)


class BattleTestOracleSnapshot(ResponseModel):
    """Stable API-oracle snapshot used for transcript comparison."""

    scenario_id: str
    kind: BattleTestOracleKind
    automated: bool
    expected: JsonObject = Field(default_factory=dict)
    notes: tuple[str, ...] = ()


class BattleTestEvaluation(ResponseModel):
    """Combined route and oracle evaluation result."""

    scenario_id: str
    grade: BattleTestGrade
    route_passed: bool
    oracle_passed: bool
    passed: bool
    failures: list[str] = Field(default_factory=list)
    oracle_snapshot: BattleTestOracleSnapshot | None = None


class IdentityOracleService(Protocol):
    """Minimal identity service needed by read-only oracle checks."""

    async def get_identity(self) -> IdentityResponse:
        """Return the authenticated Follow Up Boss identity."""


class PeopleOracleService(Protocol):
    """Minimal people service needed by read-only oracle checks."""

    async def search_people(
        self, request: PeopleSearchRequest | None = None
    ) -> PageResult[PersonRecord]:
        """Search people for direct API oracle comparison."""


class TasksOracleService(Protocol):
    """Minimal tasks service needed by read-only oracle checks."""

    async def list_tasks(self, request: TaskListRequest | None = None) -> PageResult[TaskRecord]:
        """List tasks for direct API oracle comparison."""


class ReadOnlyBattleTestServices(Protocol):
    """Service bundle subset required by read-only battle-test oracles."""

    @property
    def identity(self) -> IdentityOracleService:
        """Return the identity service used for oracle checks."""

    @property
    def people(self) -> PeopleOracleService:
        """Return the people service used for oracle checks."""

    @property
    def tasks(self) -> TasksOracleService:
        """Return the tasks service used for oracle checks."""


def read_only_battle_test_scenarios() -> tuple[BattleTestScenario, ...]:
    """Return the first read-only vague-prompt scenario corpus.

    Returns:
        A tuple containing the initial `BT-READ-*` scenario definitions.
    """
    return _READ_ONLY_SCENARIOS


def scenario_by_id(scenario_id: str) -> BattleTestScenario:
    """Return one read-only battle-test scenario by ID.

    Args:
        scenario_id: Stable scenario identifier to look up.

    Returns:
        The matching scenario.

    Raises:
        KeyError: If `scenario_id` is not part of the read-only corpus.
    """
    scenarios = {scenario.id: scenario for scenario in _READ_ONLY_SCENARIOS}
    return scenarios[scenario_id]


def evaluate_transcript_route(
    scenario: BattleTestScenario,
    transcript: BattleTestTranscript,
) -> BattleTestRouteResult:
    """Evaluate whether a transcript followed the expected MCP route.

    Args:
        scenario: Scenario contract being checked.
        transcript: Captured chatbot/MCP interaction for one prompt.

    Returns:
        A route-level pass/fail result with actionable failure messages.
    """
    failures: list[str] = []
    selected_tool = transcript.selected_tool
    if transcript.scenario_id != scenario.id:
        failures.append(
            f"Transcript scenario_id {transcript.scenario_id!r} does not match {scenario.id!r}."
        )
    if selected_tool in scenario.expected_mcp.forbidden_tools:
        failures.append(f"Selected forbidden tool {selected_tool!r}.")

    route_checks: dict[BattleTestGrade, Callable[[], None]] = {
        BattleTestGrade.MUST_ROUTE: lambda: _check_required_route(
            scenario,
            selected_tool,
            failures,
        ),
        BattleTestGrade.MAY_ROUTE: lambda: _check_optional_route(scenario, transcript, failures),
        BattleTestGrade.MUST_CLARIFY: lambda: _check_clarification(transcript, failures),
        BattleTestGrade.MUST_REQUIRE_ID: lambda: _check_required_arguments(
            scenario,
            transcript,
            failures,
        ),
        BattleTestGrade.MUST_EXPLAIN_UNSUPPORTED: lambda: _check_unsupported_explanation(
            transcript,
            failures,
        ),
    }
    route_checks[scenario.grade]()

    return BattleTestRouteResult(
        scenario_id=scenario.id,
        grade=scenario.grade,
        selected_tool=selected_tool,
        passed=not failures,
        failures=failures,
    )


class ReadOnlyBattleTestOracle:
    """Build and evaluate read-only API-oracle snapshots."""

    def __init__(self, services: ReadOnlyBattleTestServices) -> None:
        """Initialize the oracle.

        Args:
            services: Typed service bundle or compatible test double used for
                direct Follow Up Boss API truth checks.
        """
        self._services = services

    async def snapshot(
        self,
        scenario: BattleTestScenario,
        transcript: BattleTestTranscript,
    ) -> BattleTestOracleSnapshot:
        """Build the expected API-oracle snapshot for a transcript.

        Args:
            scenario: Scenario contract to verify.
            transcript: Captured transcript whose arguments should be mirrored
                by the direct API oracle where applicable.

        Returns:
            A stable snapshot of the expected API truth.

        Raises:
            RuntimeError: If the authenticated user ID is unavailable.
            NotImplementedError: If the scenario has no automated oracle yet.
        """
        if scenario.api_oracle.kind is BattleTestOracleKind.LATEST_ASSIGNED_LEAD:
            return await self._latest_assigned_lead_snapshot(scenario, transcript)
        if scenario.api_oracle.kind is BattleTestOracleKind.MY_OVERDUE_TASKS:
            return await self._owned_task_snapshot(scenario, transcript, due="overdue")
        if scenario.api_oracle.kind is BattleTestOracleKind.MY_TASKS_DUE_TODAY:
            return await self._owned_task_snapshot(scenario, transcript, due="today")
        if scenario.api_oracle.kind is BattleTestOracleKind.UNSUPPORTED_NOTE_SEARCH:
            return BattleTestOracleSnapshot(
                scenario_id=scenario.id,
                kind=scenario.api_oracle.kind,
                automated=True,
                expected={"unsupported": True, "selected_tool": None},
                notes=(
                    "Follow Up Boss does not expose note search by person ID through this MCP.",
                ),
            )
        return BattleTestOracleSnapshot(
            scenario_id=scenario.id,
            kind=scenario.api_oracle.kind,
            automated=False,
            expected={},
            notes=("This scenario is encoded but does not have an automated API oracle yet.",),
        )

    async def evaluate(
        self,
        scenario: BattleTestScenario,
        transcript: BattleTestTranscript,
    ) -> BattleTestEvaluation:
        """Evaluate route selection and direct API truth for one transcript.

        Args:
            scenario: Scenario contract being evaluated.
            transcript: Captured chatbot/MCP interaction.

        Returns:
            A combined route and oracle evaluation result.
        """
        route_result = evaluate_transcript_route(scenario, transcript)
        failures = list(route_result.failures)
        oracle_snapshot: BattleTestOracleSnapshot | None = None
        oracle_passed = False
        if route_result.passed:
            oracle_snapshot = await self.snapshot(scenario, transcript)
            oracle_failures = _compare_transcript_to_oracle(scenario, transcript, oracle_snapshot)
            failures.extend(oracle_failures)
            oracle_passed = not oracle_failures
        return BattleTestEvaluation(
            scenario_id=scenario.id,
            grade=scenario.grade,
            route_passed=route_result.passed,
            oracle_passed=oracle_passed,
            passed=route_result.passed and oracle_passed,
            failures=failures,
            oracle_snapshot=oracle_snapshot,
        )

    async def _authenticated_user_id(self) -> int:
        """Return the authenticated Follow Up Boss user ID.

        Returns:
            The current user's Follow Up Boss ID.

        Raises:
            RuntimeError: If the identity payload does not include a user ID.
        """
        identity = await self._services.identity.get_identity()
        if identity.id is None:
            raise RuntimeError("Authenticated Follow Up Boss user id is unavailable.")
        return identity.id

    async def _latest_assigned_lead_snapshot(
        self,
        scenario: BattleTestScenario,
        transcript: BattleTestTranscript,
    ) -> BattleTestOracleSnapshot:
        """Build direct API truth for the latest assigned lead scenario."""
        user_id = await self._authenticated_user_id()
        page = await self._services.people.search_people(
            PeopleSearchRequest(
                assigned_user_id=user_id,
                fields=_optional_string_list(transcript.arguments.get("fields")),
                limit=1,
                sort="-created",
            )
        )
        person = page.items[0] if page.items else None
        return BattleTestOracleSnapshot(
            scenario_id=scenario.id,
            kind=scenario.api_oracle.kind,
            automated=True,
            expected={
                "assigned_user_id": user_id,
                "person_id": person.id if person is not None else None,
            },
        )

    async def _owned_task_snapshot(
        self,
        scenario: BattleTestScenario,
        transcript: BattleTestTranscript,
        *,
        due: str,
    ) -> BattleTestOracleSnapshot:
        """Build direct API truth for an authenticated-user task due bucket."""
        user_id = await self._authenticated_user_id()
        page = await self._services.tasks.list_tasks(
            TaskListRequest(
                assigned_user_id=user_id,
                due=due,
                fields=_optional_string_list(transcript.arguments.get("fields")),
                is_completed=False,
                limit=_optional_int(transcript.arguments.get("limit")),
                next_token=_optional_string(transcript.arguments.get("next_token")),
                offset=_optional_int(transcript.arguments.get("offset")),
            )
        )
        return BattleTestOracleSnapshot(
            scenario_id=scenario.id,
            kind=scenario.api_oracle.kind,
            automated=True,
            expected={
                "assigned_user_id": user_id,
                "due": due,
                "is_completed": False,
                "task_ids": [task.id for task in page.items],
            },
        )


def _check_required_route(
    scenario: BattleTestScenario,
    selected_tool: str | None,
    failures: list[str],
) -> None:
    """Append failures for a required-route scenario."""
    if selected_tool not in scenario.expected_mcp.allowed_tools:
        failures.append(
            f"Expected one of {scenario.expected_mcp.allowed_tools!r}, got {selected_tool!r}."
        )


def _check_optional_route(
    scenario: BattleTestScenario,
    transcript: BattleTestTranscript,
    failures: list[str],
) -> None:
    """Append failures for an optional-route scenario."""
    selected_tool = transcript.selected_tool
    if selected_tool is None:
        if not transcript.clarified:
            failures.append("Expected a safe tool route or a clarifying response.")
        return
    if selected_tool not in scenario.expected_mcp.allowed_tools:
        failures.append(
            f"Expected an allowed safe route {scenario.expected_mcp.allowed_tools!r}, "
            f"got {selected_tool!r}."
        )


def _check_clarification(transcript: BattleTestTranscript, failures: list[str]) -> None:
    """Append failures for a must-clarify scenario."""
    if not transcript.clarified:
        failures.append("Expected the assistant to ask a clarifying question.")
    if transcript.selected_tool is not None:
        failures.append(
            f"Expected no tool call before clarification, got {transcript.selected_tool!r}."
        )


def _check_required_arguments(
    scenario: BattleTestScenario,
    transcript: BattleTestTranscript,
    failures: list[str],
) -> None:
    """Append failures for a scenario that requires explicit arguments."""
    missing = [
        key
        for key in scenario.expected_mcp.required_argument_keys
        if key not in transcript.arguments
    ]
    if missing and not transcript.clarified:
        failures.append(
            f"Expected explicit arguments or clarification for missing keys {missing!r}."
        )
    if missing and transcript.selected_tool is not None:
        failures.append(
            f"Selected {transcript.selected_tool!r} without required arguments {missing!r}."
        )


def _check_unsupported_explanation(
    transcript: BattleTestTranscript,
    failures: list[str],
) -> None:
    """Append failures for an unsupported-intent scenario."""
    if not transcript.unsupported_explained:
        failures.append("Expected the assistant to explain the unsupported API capability.")
    if transcript.selected_tool is not None:
        failures.append(
            f"Expected no tool call for unsupported intent, got {transcript.selected_tool!r}."
        )


def _compare_transcript_to_oracle(
    scenario: BattleTestScenario,
    transcript: BattleTestTranscript,
    snapshot: BattleTestOracleSnapshot,
) -> list[str]:
    """Compare captured MCP response data with the API-oracle snapshot."""
    if not snapshot.automated:
        return [f"Scenario {scenario.id} does not have an automated API oracle yet."]
    if snapshot.kind is BattleTestOracleKind.LATEST_ASSIGNED_LEAD:
        return _compare_latest_lead_response(transcript, snapshot)
    if snapshot.kind in {
        BattleTestOracleKind.MY_OVERDUE_TASKS,
        BattleTestOracleKind.MY_TASKS_DUE_TODAY,
    }:
        return _compare_task_response(transcript, snapshot)
    return []


def _compare_latest_lead_response(
    transcript: BattleTestTranscript,
    snapshot: BattleTestOracleSnapshot,
) -> list[str]:
    """Compare a latest-lead MCP response to API truth."""
    response = _mapping_or_none(transcript.response)
    if response is None:
        return ["Expected latest-lead MCP response to be an object."]
    expected_person_id = snapshot.expected.get("person_id")
    person = response.get("person")
    if expected_person_id is None:
        if person is None:
            return []
        return ["Expected no latest assigned lead, but MCP returned a person."]
    if not isinstance(person, dict):
        return ["Expected latest-lead MCP response to include a person object."]
    actual_person_id = person.get("id")
    if actual_person_id != expected_person_id:
        return [f"Expected latest lead person id {expected_person_id!r}, got {actual_person_id!r}."]
    return []


def _compare_task_response(
    transcript: BattleTestTranscript,
    snapshot: BattleTestOracleSnapshot,
) -> list[str]:
    """Compare an owned-task MCP response to API truth."""
    response = _mapping_or_none(transcript.response)
    if response is None:
        return ["Expected task MCP response to be an object."]
    tasks = response.get("tasks")
    if not isinstance(tasks, list):
        return ["Expected task MCP response to include a tasks list."]
    actual_ids = [item.get("id") for item in tasks if isinstance(item, dict)]
    expected_ids = snapshot.expected.get("task_ids")
    if actual_ids != expected_ids:
        return [f"Expected task ids {expected_ids!r}, got {actual_ids!r}."]
    return []


def _mapping_or_none(value: JsonValue) -> Mapping[str, JsonValue] | None:
    """Return a mapping JSON value when the value has object shape."""
    if isinstance(value, dict):
        return value
    return None


def _optional_int(value: JsonValue) -> int | None:
    """Return an optional integer transcript argument."""
    if isinstance(value, int):
        return value
    return None


def _optional_string(value: JsonValue) -> str | None:
    """Return an optional string transcript argument."""
    if isinstance(value, str):
        return value
    return None


def _optional_string_list(value: JsonValue) -> list[str] | None:
    """Return an optional string-list transcript argument."""
    if not isinstance(value, list):
        return None
    strings = [item for item in value if isinstance(item, str)]
    return strings if len(strings) == len(value) else None


_READ_ONLY_SCENARIOS: tuple[BattleTestScenario, ...] = (
    BattleTestScenario(
        id="BT-READ-001",
        grade=BattleTestGrade.MUST_ROUTE,
        prompt_variants=(
            "What is my latest lead?",
            "Who was the newest lead I got?",
            "Show me the most recent lead assigned to me",
            "Pull up my newest person",
            "Anything new for me?",
        ),
        expected_mcp=ExpectedMcpRoute(
            allowed_tools=("followupboss_get_latest_lead",),
            forbidden_tools=("followupboss_search_people",),
        ),
        api_oracle=ApiOracleSpec(
            kind=BattleTestOracleKind.LATEST_ASSIGNED_LEAD,
            description="Direct people query for newest person assigned to authenticated user.",
        ),
        response_assertions=("response.person.id == api_oracle.person_id",),
    ),
    BattleTestScenario(
        id="BT-READ-002",
        grade=BattleTestGrade.MUST_ROUTE,
        prompt_variants=(
            "What am I late on?",
            "Show my overdue tasks",
            "Which follow-ups did I miss?",
            "What tasks are past due for me?",
            "Anything I should have done already?",
        ),
        expected_mcp=ExpectedMcpRoute(
            allowed_tools=("followupboss_list_my_overdue_tasks",),
            forbidden_tools=("followupboss_list_tasks",),
        ),
        api_oracle=ApiOracleSpec(
            kind=BattleTestOracleKind.MY_OVERDUE_TASKS,
            description=(
                "Direct task query for incomplete overdue tasks assigned to authenticated user."
            ),
        ),
        response_assertions=("response.tasks[*].id == api_oracle.task_ids",),
    ),
    BattleTestScenario(
        id="BT-READ-003",
        grade=BattleTestGrade.MUST_ROUTE,
        prompt_variants=(
            "What do I need to do today?",
            "Show my tasks today",
            "What's on deck for me today?",
            "Any follow-ups due today?",
            "Give me today's to-do list",
        ),
        expected_mcp=ExpectedMcpRoute(
            allowed_tools=("followupboss_list_my_tasks_due_today",),
            forbidden_tools=("followupboss_list_tasks",),
        ),
        api_oracle=ApiOracleSpec(
            kind=BattleTestOracleKind.MY_TASKS_DUE_TODAY,
            description=(
                "Direct query for incomplete tasks due today assigned to authenticated user."
            ),
        ),
        response_assertions=("response.tasks[*].id == api_oracle.task_ids",),
    ),
    BattleTestScenario(
        id="BT-READ-004",
        grade=BattleTestGrade.MAY_ROUTE,
        prompt_variants=(
            "What do I have coming up?",
            "Show my next tasks",
            "What's due later this week?",
            "Any follow-ups after today?",
            "What should I prep for next?",
        ),
        expected_mcp=ExpectedMcpRoute(
            allowed_tools=("followupboss_list_tasks", "future:followupboss_list_my_upcoming_tasks"),
            forbidden_tools=(),
        ),
        api_oracle=ApiOracleSpec(
            kind=BattleTestOracleKind.ROUTE_ONLY_PENDING,
            description=(
                "Route-only placeholder until a canonical future-task API filter is chosen."
            ),
        ),
        response_assertions=("safe route or clarification only",),
    ),
    BattleTestScenario(
        id="BT-READ-005",
        grade=BattleTestGrade.MUST_EXPLAIN_UNSUPPORTED,
        prompt_variants=(
            "Show notes for lead 123",
            "What notes are on this person?",
            "Find all notes for this FUB lead",
            "Search notes by person ID",
            "Do they have any notes?",
        ),
        expected_mcp=ExpectedMcpRoute(
            allowed_tools=(),
            forbidden_tools=("followupboss_search_events", "followupboss_get_note"),
        ),
        api_oracle=ApiOracleSpec(
            kind=BattleTestOracleKind.UNSUPPORTED_NOTE_SEARCH,
            description="Confirm no note-search tool was called or invented from event search.",
        ),
        response_assertions=("unsupported_explained is true", "selected_tool is None"),
    ),
)
