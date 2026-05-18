"""Scenario models and oracle helpers for MCP battle testing."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from enum import StrEnum
from pathlib import Path
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


class BattleTestModelProvider(StrEnum):
    """Supported model-provider labels for battle-test run artifacts."""

    ANTHROPIC = "anthropic"
    OPENAI = "openai"


class BattleTestModelProfile(RequestModel):
    """Model profile used for one separate battle-test run."""

    id: str
    provider: BattleTestModelProvider
    model: str
    display_name: str
    reasoning_effort: str | None = None

    @model_validator(mode="after")
    def _require_non_empty_strings(self) -> BattleTestModelProfile:
        """Require stable non-empty profile strings.

        Returns:
            The validated model profile.

        Raises:
            ValueError: If a required string field is blank.
        """
        if not self.id.strip() or not self.model.strip() or not self.display_name.strip():
            raise ValueError("Battle-test model profile strings must be non-empty.")
        if self.reasoning_effort is not None and not self.reasoning_effort.strip():
            raise ValueError("Battle-test model profile reasoning_effort must be non-empty.")
        return self


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


class BattleTestToolCall(RequestModel):
    """Observed or approved MCP tool call to execute for one scenario."""

    scenario_id: str
    prompt: str
    tool_name: str
    arguments: JsonObject = Field(default_factory=dict)
    assistant_message: str | None = None


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


class BattleTestRunMetadata(RequestModel):
    """Metadata describing one battle-test execution."""

    run_id: str
    client: str
    model_profile: BattleTestModelProfile | None = None
    environment: str | None = None
    started_at: str | None = None
    notes: tuple[str, ...] = ()


class BattleTestRunSummary(ResponseModel):
    """Aggregate pass/fail counts for a battle-test run."""

    total_scenarios: int
    evaluated_scenarios: int
    passed_scenarios: int
    failed_scenarios: int
    missing_scenarios: int
    unknown_transcripts: int
    overall_passed: bool


class BattleTestRunArtifact(ResponseModel):
    """Serializable artifact for one battle-test transcript evaluation run."""

    metadata: BattleTestRunMetadata
    summary: BattleTestRunSummary
    evaluations: tuple[BattleTestEvaluation, ...]
    missing_scenario_ids: tuple[str, ...] = ()
    unknown_transcript_scenario_ids: tuple[str, ...] = ()


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


class BattleTestMcpClient(Protocol):
    """Minimal MCP client-session protocol used by battle-test capture helpers."""

    async def call_tool(
        self,
        name: str,
        arguments: Mapping[str, JsonValue] | None = None,
    ) -> object:
        """Call one MCP tool and return the client library's raw result."""


GPT_55_LOW_REASONING_PROFILE = BattleTestModelProfile(
    id="gpt-5.5-low-reasoning",
    provider=BattleTestModelProvider.OPENAI,
    model="gpt-5.5",
    display_name="GPT-5.5 low reasoning",
    reasoning_effort="low",
)
SONNET_47_PROFILE = BattleTestModelProfile(
    id="sonnet-4.7",
    provider=BattleTestModelProvider.ANTHROPIC,
    model="claude-sonnet-4.7",
    display_name="Sonnet 4.7",
)
_DEFAULT_MODEL_PROFILES = (GPT_55_LOW_REASONING_PROFILE, SONNET_47_PROFILE)


def battle_test_model_profiles() -> tuple[BattleTestModelProfile, ...]:
    """Return the default model profiles for separate battle-test runs.

    Returns:
        The default profile tuple containing GPT-5.5 low reasoning and Sonnet
        4.7 labels.
    """
    return _DEFAULT_MODEL_PROFILES


def battle_test_model_profile_by_id(profile_id: str) -> BattleTestModelProfile:
    """Return one default model profile by ID.

    Args:
        profile_id: Stable profile ID to look up.

    Returns:
        The matching default model profile.

    Raises:
        KeyError: If `profile_id` is not a default model profile.
    """
    profiles = {profile.id: profile for profile in _DEFAULT_MODEL_PROFILES}
    return profiles[profile_id]


def build_model_profile_run_metadata(
    *,
    run_id_prefix: str,
    client: str,
    model_profile: BattleTestModelProfile,
    environment: str | None = None,
    started_at: str | None = None,
    notes: tuple[str, ...] = (),
) -> BattleTestRunMetadata:
    """Build run metadata for one model-specific battle-test artifact.

    Args:
        run_id_prefix: Shared run prefix for a model comparison batch.
        client: Client or harness label used to capture transcripts.
        model_profile: Model profile being evaluated.
        environment: Optional target environment label.
        started_at: Optional ISO-like run timestamp.
        notes: Optional run notes.

    Returns:
        Run metadata with a profile-suffixed run ID.
    """
    return BattleTestRunMetadata(
        run_id=f"{run_id_prefix}-{model_profile.id}",
        client=client,
        model_profile=model_profile,
        environment=environment,
        started_at=started_at,
        notes=notes,
    )


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


async def capture_mcp_tool_transcript(
    client: BattleTestMcpClient,
    tool_call: BattleTestToolCall,
) -> BattleTestTranscript:
    """Execute one MCP tool call and capture it as a battle-test transcript.

    Args:
        client: MCP client session or compatible test double.
        tool_call: Scenario prompt plus selected tool and arguments to execute.

    Returns:
        A transcript containing the selected tool, arguments, and structured MCP
        response.
    """
    result = await client.call_tool(
        tool_call.tool_name,
        tool_call.arguments or None,
    )
    return BattleTestTranscript(
        scenario_id=tool_call.scenario_id,
        prompt=tool_call.prompt,
        selected_tool=tool_call.tool_name,
        arguments=tool_call.arguments,
        response=mcp_tool_result_to_json(result),
        assistant_message=tool_call.assistant_message,
    )


async def capture_mcp_tool_transcripts(
    client: BattleTestMcpClient,
    tool_calls: tuple[BattleTestToolCall, ...],
) -> tuple[BattleTestTranscript, ...]:
    """Execute multiple MCP tool calls and capture transcript records.

    Args:
        client: MCP client session or compatible test double.
        tool_calls: Ordered tool calls to execute.

    Returns:
        Captured transcripts in the same order as `tool_calls`.
    """
    transcripts: list[BattleTestTranscript] = []
    for tool_call in tool_calls:
        transcripts.append(await capture_mcp_tool_transcript(client, tool_call))
    return tuple(transcripts)


async def run_battle_test_tool_calls(
    client: BattleTestMcpClient,
    oracle: ReadOnlyBattleTestOracle,
    tool_calls: tuple[BattleTestToolCall, ...],
    *,
    metadata: BattleTestRunMetadata,
    scenarios: tuple[BattleTestScenario, ...] | None = None,
    artifact_path: Path | None = None,
) -> BattleTestRunArtifact:
    """Capture, evaluate, and optionally persist one MCP battle-test run.

    Args:
        client: MCP client session or compatible test double.
        oracle: Read-only API oracle used to evaluate captured transcripts.
        tool_calls: Ordered scenario tool calls to execute through the MCP
            client.
        metadata: Metadata to attach to the run artifact.
        scenarios: Optional scenario corpus. Defaults to the read-only corpus.
        artifact_path: Optional JSON output path for the run artifact.

    Returns:
        The evaluated run artifact.
    """
    transcripts = await capture_mcp_tool_transcripts(client, tool_calls)
    artifact = await evaluate_battle_test_run(
        oracle,
        transcripts,
        metadata=metadata,
        scenarios=scenarios,
    )
    if artifact_path is not None:
        write_battle_test_run_artifact(artifact, artifact_path)
    return artifact


async def evaluate_model_profile_battle_test_runs(
    oracle: ReadOnlyBattleTestOracle,
    transcripts_by_profile: Mapping[str, tuple[BattleTestTranscript, ...]],
    *,
    run_id_prefix: str,
    client: str,
    profiles: tuple[BattleTestModelProfile, ...] | None = None,
    environment: str | None = None,
    started_at: str | None = None,
    notes: tuple[str, ...] = (),
    scenarios: tuple[BattleTestScenario, ...] | None = None,
    artifact_directory: Path | None = None,
) -> tuple[BattleTestRunArtifact, ...]:
    """Evaluate and optionally write one run artifact per model profile.

    Args:
        oracle: Read-only API oracle used to evaluate each profile's captured
            transcripts.
        transcripts_by_profile: Captured transcripts keyed by model profile ID.
        run_id_prefix: Shared run prefix for the model comparison batch.
        client: Client or harness label used to capture transcripts.
        profiles: Optional profile set. Defaults to the standard GPT-5.5 low
            reasoning and Sonnet 4.7 profiles.
        environment: Optional target environment label.
        started_at: Optional ISO-like run timestamp.
        notes: Optional run notes.
        scenarios: Optional scenario corpus. Defaults to the read-only corpus.
        artifact_directory: Optional directory where one JSON artifact per
            profile should be written.

    Returns:
        One evaluated run artifact per requested model profile.
    """
    artifacts: list[BattleTestRunArtifact] = []
    for profile in profiles or battle_test_model_profiles():
        metadata = build_model_profile_run_metadata(
            run_id_prefix=run_id_prefix,
            client=client,
            model_profile=profile,
            environment=environment,
            started_at=started_at,
            notes=notes,
        )
        artifact = await evaluate_battle_test_run(
            oracle,
            transcripts_by_profile.get(profile.id, ()),
            metadata=metadata,
            scenarios=scenarios,
        )
        if artifact_directory is not None:
            write_battle_test_run_artifact(
                artifact,
                artifact_directory / f"{metadata.run_id}.json",
            )
        artifacts.append(artifact)
    return tuple(artifacts)


def mcp_tool_result_to_json(result: object) -> JsonValue:
    """Extract a JSON-safe value from an MCP client tool-call result.

    Args:
        result: Raw result returned by an MCP client library.

    Returns:
        A JSON-compatible value suitable for `BattleTestTranscript.response`.

    Raises:
        TypeError: If the result cannot be represented as JSON.
    """
    structured_content = getattr(result, "structuredContent", None)
    if structured_content is not None:
        return _coerce_json_value(structured_content)
    content = getattr(result, "content", None)
    if isinstance(content, Sequence) and not isinstance(content, str | bytes | bytearray):
        text_items = _content_text_items(content)
        if text_items:
            return {"content": text_items}
    return _coerce_json_value(result)


async def evaluate_battle_test_run(
    oracle: ReadOnlyBattleTestOracle,
    transcripts: tuple[BattleTestTranscript, ...],
    *,
    metadata: BattleTestRunMetadata,
    scenarios: tuple[BattleTestScenario, ...] | None = None,
) -> BattleTestRunArtifact:
    """Evaluate captured transcripts and build a run artifact.

    Args:
        oracle: Read-only oracle used to evaluate matching scenario transcripts.
        transcripts: Captured transcript records from an MCP client or chatbot
            runner.
        metadata: Metadata to store with the generated run artifact.
        scenarios: Optional scenario corpus. When omitted, the read-only corpus
            is used.

    Returns:
        A serializable run artifact containing per-scenario evaluations and
        aggregate pass/fail counts.
    """
    scenario_corpus = scenarios or read_only_battle_test_scenarios()
    scenario_by_key = {scenario.id: scenario for scenario in scenario_corpus}
    transcript_by_key = {transcript.scenario_id: transcript for transcript in transcripts}
    unknown_ids = tuple(
        transcript.scenario_id
        for transcript in transcripts
        if transcript.scenario_id not in scenario_by_key
    )
    missing_ids = tuple(
        scenario.id for scenario in scenario_corpus if scenario.id not in transcript_by_key
    )
    evaluations = tuple(
        [
            await oracle.evaluate(scenario, transcript_by_key[scenario.id])
            for scenario in scenario_corpus
            if scenario.id in transcript_by_key
        ]
    )
    return build_battle_test_run_artifact(
        metadata=metadata,
        evaluations=evaluations,
        total_scenarios=len(scenario_corpus),
        missing_scenario_ids=missing_ids,
        unknown_transcript_scenario_ids=unknown_ids,
    )


def build_battle_test_run_artifact(
    *,
    metadata: BattleTestRunMetadata,
    evaluations: tuple[BattleTestEvaluation, ...],
    total_scenarios: int,
    missing_scenario_ids: tuple[str, ...] = (),
    unknown_transcript_scenario_ids: tuple[str, ...] = (),
) -> BattleTestRunArtifact:
    """Build a serializable battle-test run artifact.

    Args:
        metadata: Metadata for the run.
        evaluations: Per-scenario evaluation results.
        total_scenarios: Number of scenarios expected for the run.
        missing_scenario_ids: Scenario IDs that did not have transcripts.
        unknown_transcript_scenario_ids: Transcript scenario IDs outside the
            expected scenario corpus.

    Returns:
        A run artifact with computed summary counts.
    """
    passed_count = sum(1 for evaluation in evaluations if evaluation.passed)
    failed_count = sum(1 for evaluation in evaluations if not evaluation.passed)
    missing_count = len(missing_scenario_ids)
    unknown_count = len(unknown_transcript_scenario_ids)
    return BattleTestRunArtifact(
        metadata=metadata,
        summary=BattleTestRunSummary(
            total_scenarios=total_scenarios,
            evaluated_scenarios=len(evaluations),
            passed_scenarios=passed_count,
            failed_scenarios=failed_count,
            missing_scenarios=missing_count,
            unknown_transcripts=unknown_count,
            overall_passed=failed_count == 0 and missing_count == 0 and unknown_count == 0,
        ),
        evaluations=evaluations,
        missing_scenario_ids=missing_scenario_ids,
        unknown_transcript_scenario_ids=unknown_transcript_scenario_ids,
    )


def write_battle_test_run_artifact(
    artifact: BattleTestRunArtifact,
    path: Path,
) -> None:
    """Write one battle-test run artifact to disk as formatted JSON.

    Args:
        artifact: Run artifact to serialize.
        path: Destination JSON file path.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(artifact.model_dump_json(indent=2) + "\n", encoding="utf-8")


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
            try:
                oracle_snapshot = await self.snapshot(scenario, transcript)
            except Exception as exc:
                failures.append(f"API oracle failed: {exc}")
            else:
                oracle_failures = _compare_transcript_to_oracle(
                    scenario, transcript, oracle_snapshot
                )
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


def _coerce_json_value(value: object) -> JsonValue:
    """Coerce common structured client values into the project JSON type."""
    if value is None or isinstance(value, bool | int | float | str):
        return value
    if isinstance(value, Mapping):
        return {
            str(key): _coerce_json_value(item)
            for key, item in value.items()
            if isinstance(key, str)
        }
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        return [_coerce_json_value(item) for item in value]
    model_dump = getattr(value, "model_dump", None)
    if callable(model_dump):
        dumped = model_dump(mode="json")
        return _coerce_json_value(dumped)
    raise TypeError(f"MCP tool result is not JSON serializable: {value!r}")


def _content_text_items(content: Sequence[object]) -> list[JsonValue]:
    """Return text item payloads from MCP content blocks."""
    text_items: list[JsonValue] = []
    for item in content:
        text = getattr(item, "text", None)
        if isinstance(text, str):
            text_items.append({"type": "text", "text": text})
    return text_items


def _optional_int(value: JsonValue) -> int | None:
    """Return an optional integer transcript argument, excluding JSON booleans."""
    if isinstance(value, int) and not isinstance(value, bool):
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
