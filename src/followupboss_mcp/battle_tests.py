"""Scenario models and oracle helpers for MCP battle testing."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from enum import StrEnum
from pathlib import Path
from random import Random
from typing import Any, Protocol, cast

from pydantic import Field, model_validator

from followupboss_mcp.mcp_tools import FollowUpBossToolAdapter, ListUncontactedLeadsToolInput
from followupboss_mcp.models.appointments import AppointmentListRequest, AppointmentRecord
from followupboss_mcp.models.calls import CallListRequest, CallRecord
from followupboss_mcp.models.common import JsonValue, RequestModel, ResponseModel
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
from followupboss_mcp.models.users import UserListRequest, UserRecord
from followupboss_mcp.pagination import PageResult
from followupboss_mcp.task_intents import upcoming_task_due_start as _upcoming_task_due_start

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

    APPOINTMENTS = "appointments"
    CALLS = "calls"
    EXPLICIT_NOTE = "explicit_note"
    LATEST_ASSIGNED_LEAD = "latest_assigned_lead"
    MY_OVERDUE_TASKS = "my_overdue_tasks"
    MY_TASKS_DUE_TODAY = "my_tasks_due_today"
    MY_UNCONTACTED_LEADS = "my_uncontacted_leads"
    MY_UPCOMING_TASKS = "my_upcoming_tasks"
    NAMED_SMART_LIST_PEOPLE = "named_smart_list_people"
    PEOPLE_SEARCH = "people_search"
    PERSON_ACTIVITY = "person_activity"
    PERSON_DUPLICATE_CHECK = "person_duplicate_check"
    ROUTE_ONLY_PENDING = "route_only_pending"
    SMART_LISTS = "smart_lists"
    TEMPLATES = "templates"
    TEXT_MESSAGE_TEMPLATES = "text_message_templates"
    TEXT_MESSAGES = "text_messages"
    UNCLAIMED_PEOPLE = "unclaimed_people"
    UNSUPPORTED_NOTE_SEARCH = "unsupported_note_search"


class BattleTestConversationKind(StrEnum):
    """Supported chained battle-test conversation shapes."""

    MULTI_TURN = "multi_turn"
    MULTI_ASK = "multi_ask"


class BattleTestFailureCategory(StrEnum):
    """Coarse failure categories for battle-test triage summaries."""

    ORACLE_RESPONSE_MISMATCH = "oracle_response_mismatch"
    ORACLE_TRANSPORT_ERROR = "oracle_transport_error"
    ROUTE_NO_CALL = "route_no_call"
    ROUTE_WRONG_TOOL = "route_wrong_tool"
    UNKNOWN = "unknown"
    UNSUPPORTED_NOT_EXPLAINED = "unsupported_not_explained"


class BattleTestFixtureKind(StrEnum):
    """Disposable fixture domains supported by mutation battle-test planning."""

    APPOINTMENT = "appointment"
    NOTE = "note"
    PERSON = "person"
    TASK = "task"


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
    required_argument_values: JsonObject = Field(default_factory=dict)


class ApiOracleSpec(RequestModel):
    """Description of the direct API truth check for one scenario."""

    kind: BattleTestOracleKind
    description: str
    smart_list_name: str | None = None
    answer_must_be_grounded: bool = False
    requires_authenticated_owner_scope: bool = False


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


class BattleTestConversationTurn(RequestModel):
    """Expected behavior for one turn inside a chained battle-test scenario."""

    id: str
    prompt: str
    grade: BattleTestGrade
    expected_mcp: ExpectedMcpRoute
    api_oracle: ApiOracleSpec
    response_assertions: tuple[str, ...] = ()
    cleanup: str = "none"

    @model_validator(mode="after")
    def _require_non_empty_strings(self) -> BattleTestConversationTurn:
        """Require stable turn identifiers and prompts.

        Returns:
            The validated turn.

        Raises:
            ValueError: If the turn ID or prompt is blank.
        """
        if not self.id.strip() or not self.prompt.strip():
            raise ValueError("Battle-test conversation turns need non-empty IDs and prompts.")
        return self


class BattleTestConversationScenario(RequestModel):
    """Machine-readable chained or multi-ask battle-test scenario."""

    id: str
    kind: BattleTestConversationKind
    turns: tuple[BattleTestConversationTurn, ...]
    prompt: str | None = None
    description: str = ""

    @model_validator(mode="after")
    def _require_valid_conversation(self) -> BattleTestConversationScenario:
        """Validate conversation identity, turns, and prompt shape.

        Returns:
            The validated conversation scenario.

        Raises:
            ValueError: If the scenario ID, turn set, turn IDs, or multi-ask
                prompt are invalid.
        """
        if not self.id.strip():
            raise ValueError("Battle-test conversation scenarios need non-empty IDs.")
        if not self.turns:
            raise ValueError("Battle-test conversation scenarios need at least one turn.")
        turn_ids = [turn.id for turn in self.turns]
        if len(set(turn_ids)) != len(turn_ids):
            raise ValueError("Battle-test conversation turn IDs must be unique.")
        if self.kind is BattleTestConversationKind.MULTI_ASK and not (self.prompt or "").strip():
            raise ValueError("Multi-ask battle-test scenarios need a non-empty prompt.")
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


class BattleTestMultiCallTranscript(RequestModel):
    """Captured ordered tool calls for one single-message multi-ask prompt."""

    scenario_id: str
    prompt: str
    transcripts: tuple[BattleTestTranscript, ...]
    assistant_message: str | None = None


class BattleTestConversationTranscript(RequestModel):
    """Captured transcript bundle for one chained conversation scenario."""

    conversation_id: str
    kind: BattleTestConversationKind
    turn_transcripts: tuple[BattleTestTranscript, ...]
    prompt: str | None = None


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
    failure_categories: tuple[BattleTestFailureCategory, ...] = ()
    oracle_snapshot: BattleTestOracleSnapshot | None = None


class BattleTestConversationEvaluation(ResponseModel):
    """Aggregate evaluation for one chained conversation scenario."""

    conversation_id: str
    kind: BattleTestConversationKind
    passed: bool
    turn_evaluations: tuple[BattleTestEvaluation, ...]
    failures: tuple[str, ...] = ()


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
    failure_category_counts: dict[str, int] = Field(default_factory=dict)
    overall_passed: bool


class BattleTestRunArtifact(ResponseModel):
    """Serializable artifact for one battle-test transcript evaluation run."""

    metadata: BattleTestRunMetadata
    summary: BattleTestRunSummary
    evaluations: tuple[BattleTestEvaluation, ...]
    missing_scenario_ids: tuple[str, ...] = ()
    unknown_transcript_scenario_ids: tuple[str, ...] = ()
    conversation_evaluations: tuple[BattleTestConversationEvaluation, ...] = ()


class BattleTestFixtureCleanupAction(RequestModel):
    """Cleanup action required for one disposable battle-test fixture."""

    fixture_kind: BattleTestFixtureKind
    tool_name: str
    identifier_key: str
    created_id: int | None = None
    notes: str = ""


class BattleTestFixturePlan(RequestModel):
    """Plan for disposable mutation fixtures and cleanup proof."""

    run_prefix: str
    fixture_kinds: tuple[BattleTestFixtureKind, ...]
    cleanup_actions: tuple[BattleTestFixtureCleanupAction, ...]
    skip_reasons: tuple[str, ...] = ()


class IdentityOracleService(Protocol):
    """Minimal identity service needed by read-only oracle checks."""

    async def get_identity(self) -> IdentityResponse:
        """Return the authenticated Follow Up Boss identity."""


class PeopleOracleService(Protocol):
    """Minimal people service needed by read-only oracle checks."""

    async def get_person(
        self,
        person_id: int,
        request: object | None = None,
    ) -> PersonRecord:
        """Get one person for direct API oracle provenance."""

    async def search_people(
        self, request: PeopleSearchRequest | None = None
    ) -> PageResult[PersonRecord]:
        """Search people for direct API oracle comparison."""

    async def check_duplicate_person(
        self, request: PersonDuplicateCheckRequest
    ) -> PersonDuplicateCheckRecord:
        """Check duplicate person identity for direct API oracle comparison."""

    async def list_unclaimed_people(
        self, request: UnclaimedPeopleListRequest | None = None
    ) -> PageResult[PersonRecord]:
        """List unclaimed people for direct API oracle comparison."""


class SmartListsOracleService(Protocol):
    """Minimal smart-list service needed by read-only oracle checks."""

    async def list_smart_lists(
        self, request: SmartListListRequest | None = None
    ) -> PageResult[SmartListRecord]:
        """List smart lists for direct API oracle comparison."""


class UsersOracleService(Protocol):
    """Minimal users service needed by owner-name oracle checks."""

    async def list_users(self, request: UserListRequest | None = None) -> PageResult[UserRecord]:
        """List users for exact owner-name resolution."""


class TasksOracleService(Protocol):
    """Minimal tasks service needed by read-only oracle checks."""

    async def list_tasks(self, request: TaskListRequest | None = None) -> PageResult[TaskRecord]:
        """List tasks for direct API oracle comparison."""


class AppointmentsOracleService(Protocol):
    """Minimal appointment service needed by read-only oracle checks."""

    async def list_appointments(
        self, request: AppointmentListRequest | None = None
    ) -> PageResult[AppointmentRecord]:
        """List appointments for direct API oracle comparison."""


class CallsOracleService(Protocol):
    """Minimal call service needed by read-only oracle checks."""

    async def list_calls(self, request: CallListRequest | None = None) -> PageResult[CallRecord]:
        """List calls for direct API oracle comparison."""


class TextMessagesOracleService(Protocol):
    """Minimal text-message service needed by read-only oracle checks."""

    async def list_text_messages(
        self, request: TextMessageListRequest | None = None
    ) -> PageResult[TextMessageRecord]:
        """List text message logs for direct API oracle comparison."""


class EmailEventsOracleService(Protocol):
    """Minimal email-event service needed by person-activity oracle checks."""

    async def list_email_events(
        self,
        request: EmailEventListRequest | None = None,
    ) -> PageResult[EmailEventRecord]:
        """List email events for direct API oracle comparison."""


class EventsOracleService(Protocol):
    """Minimal event service needed by person-activity oracle checks."""

    async def search_events(
        self,
        request: EventSearchRequest | None = None,
    ) -> PageResult[EventRecord]:
        """Search events for direct API oracle comparison."""


class TemplatesOracleService(Protocol):
    """Minimal email-template service needed by read-only oracle checks."""

    async def list_templates(
        self, request: TemplateListRequest | None = None
    ) -> PageResult[TemplateRecord]:
        """List email templates for direct API oracle comparison."""


class TextMessageTemplatesOracleService(Protocol):
    """Minimal text-template service needed by read-only oracle checks."""

    async def list_text_message_templates(
        self, request: TextMessageTemplateListRequest | None = None
    ) -> PageResult[TextMessageTemplateRecord]:
        """List text message templates for direct API oracle comparison."""


class NotesOracleService(Protocol):
    """Minimal note service needed by explicit-ID oracle checks."""

    async def get_note(self, note_id: int) -> NoteRecord:
        """Fetch one note by ID for direct API oracle comparison."""


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

    @property
    def smart_lists(self) -> SmartListsOracleService:
        """Return the smart-list service used for oracle checks."""

    @property
    def users(self) -> UsersOracleService:
        """Return the users service used for owner-name oracle checks."""

    @property
    def appointments(self) -> AppointmentsOracleService:
        """Return the appointment service used for oracle checks."""

    @property
    def calls(self) -> CallsOracleService:
        """Return the call service used for oracle checks."""

    @property
    def text_messages(self) -> TextMessagesOracleService:
        """Return the text-message service used for oracle checks."""

    @property
    def email_marketing(self) -> EmailEventsOracleService:
        """Return the email-marketing service used for oracle checks."""

    @property
    def events(self) -> EventsOracleService:
        """Return the event service used for oracle checks."""

    @property
    def templates(self) -> TemplatesOracleService:
        """Return the template service used for oracle checks."""

    @property
    def text_message_templates(self) -> TextMessageTemplatesOracleService:
        """Return the text-message-template service used for oracle checks."""

    @property
    def notes(self) -> NotesOracleService:
        """Return the note service used for oracle checks."""


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
SONNET_46_PROFILE = BattleTestModelProfile(
    id="sonnet-4.6",
    provider=BattleTestModelProvider.ANTHROPIC,
    model="claude-sonnet-4-6",
    display_name="Sonnet 4.6",
)
_DEFAULT_MODEL_PROFILES = (GPT_55_LOW_REASONING_PROFILE, SONNET_46_PROFILE)


def battle_test_model_profiles() -> tuple[BattleTestModelProfile, ...]:
    """Return the default model profiles for separate battle-test runs.

    Returns:
        The default profile tuple containing GPT-5.5 low reasoning and Sonnet
        4.6 labels.
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


def build_disposable_fixture_plan(
    *,
    run_prefix: str,
    fixture_kinds: tuple[BattleTestFixtureKind, ...] = (
        BattleTestFixtureKind.PERSON,
        BattleTestFixtureKind.TASK,
        BattleTestFixtureKind.NOTE,
        BattleTestFixtureKind.APPOINTMENT,
    ),
) -> BattleTestFixturePlan:
    """Build the disposable fixture cleanup plan for mutation battle tests.

    Args:
        run_prefix: Unique prefix to apply to created fixture names.
        fixture_kinds: Fixture domains to prepare.

    Returns:
        A fixture plan with cleanup actions ordered from dependent resources to
        parent resources.

    Raises:
        ValueError: If `run_prefix` is blank.
    """
    if not run_prefix.strip():
        raise ValueError("Battle-test fixture plans require a non-empty run prefix.")
    cleanup_by_kind = {
        BattleTestFixtureKind.APPOINTMENT: BattleTestFixtureCleanupAction(
            fixture_kind=BattleTestFixtureKind.APPOINTMENT,
            tool_name="followupboss_delete_appointment",
            identifier_key="appointment_id",
            notes="Delete appointment fixtures before deleting linked people.",
        ),
        BattleTestFixtureKind.NOTE: BattleTestFixtureCleanupAction(
            fixture_kind=BattleTestFixtureKind.NOTE,
            tool_name="followupboss_delete_note",
            identifier_key="note_id",
            notes="Delete note fixtures before deleting linked people.",
        ),
        BattleTestFixtureKind.TASK: BattleTestFixtureCleanupAction(
            fixture_kind=BattleTestFixtureKind.TASK,
            tool_name="followupboss_delete_task",
            identifier_key="task_id",
            notes="Delete task fixtures before deleting linked people.",
        ),
        BattleTestFixtureKind.PERSON: BattleTestFixtureCleanupAction(
            fixture_kind=BattleTestFixtureKind.PERSON,
            tool_name="followupboss_delete_person",
            identifier_key="person_id",
            notes="Delete disposable person fixtures last.",
        ),
    }
    cleanup_order = (
        BattleTestFixtureKind.APPOINTMENT,
        BattleTestFixtureKind.NOTE,
        BattleTestFixtureKind.TASK,
        BattleTestFixtureKind.PERSON,
    )
    requested = set(fixture_kinds)
    return BattleTestFixturePlan(
        run_prefix=run_prefix,
        fixture_kinds=fixture_kinds,
        cleanup_actions=tuple(cleanup_by_kind[kind] for kind in cleanup_order if kind in requested),
        skip_reasons=(
            "Mutation scenarios must be skipped unless every cleanup action receives a created ID.",
        ),
    )


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


def expanded_read_only_battle_test_scenarios() -> tuple[BattleTestScenario, ...]:
    """Return the expanded read-only battle-test scenario corpus.

    Returns:
        The original focused read-only corpus plus broader read-only API
        surfaces that can be checked against direct Follow Up Boss API truth.
    """
    return _READ_ONLY_SCENARIOS + _EXPANDED_READ_ONLY_SCENARIOS


def smart_list_grounding_battle_test_scenarios() -> tuple[BattleTestScenario, ...]:
    """Return targeted named-smart-list grounding regression scenarios.

    Returns:
        Scenarios that encode the hard invariant that Zillow follow-up prompts
        grounded to `Eligible For Transfer` must not return off-list people.
    """
    return _SMART_LIST_GROUNDING_SCENARIOS


def text_logging_context_battle_test_scenarios() -> tuple[BattleTestScenario, ...]:
    """Return mutation-aware text logging context regression scenarios.

    Returns:
        Route-only scenarios that verify follow-up text logging reuses exactly
        one previously resolved lead/contact as recipient context.
    """
    return _TEXT_LOGGING_CONTEXT_SCENARIOS


def read_only_battle_test_conversations(
    kind: BattleTestConversationKind | None = None,
) -> tuple[BattleTestConversationScenario, ...]:
    """Return the read-only chained and multi-ask battle-test corpus.

    Args:
        kind: Optional conversation kind to filter by.

    Returns:
        Chained battle-test scenarios. When `kind` is provided, only
        conversations of that kind are returned.
    """
    if kind is None:
        return _READ_ONLY_CONVERSATIONS
    return tuple(
        conversation for conversation in _READ_ONLY_CONVERSATIONS if conversation.kind is kind
    )


def expanded_battle_test_conversations(
    kind: BattleTestConversationKind | None = None,
) -> tuple[BattleTestConversationScenario, ...]:
    """Return the expanded chained and multi-ask battle-test corpus.

    Args:
        kind: Optional conversation kind to filter by.

    Returns:
        Original chained scenarios plus broader cross-surface conversations.
    """
    conversations = _READ_ONLY_CONVERSATIONS + _EXPANDED_CONVERSATIONS
    if kind is None:
        return conversations
    return tuple(conversation for conversation in conversations if conversation.kind is kind)


def smart_list_grounding_battle_test_conversations(
    kind: BattleTestConversationKind | None = None,
) -> tuple[BattleTestConversationScenario, ...]:
    """Return targeted named-smart-list grounding conversations.

    Args:
        kind: Optional conversation kind to filter by.

    Returns:
        Conversations that exercise direct and memory-style named-list routing.
    """
    if kind is None:
        return _SMART_LIST_GROUNDING_CONVERSATIONS
    return tuple(
        conversation
        for conversation in _SMART_LIST_GROUNDING_CONVERSATIONS
        if conversation.kind is kind
    )


def text_logging_context_battle_test_conversations(
    kind: BattleTestConversationKind | None = None,
) -> tuple[BattleTestConversationScenario, ...]:
    """Return mutation-aware text logging context conversations.

    Args:
        kind: Optional conversation kind to filter by.

    Returns:
        Conversations that exercise prior-person context reuse for text logging.
    """
    if kind is None:
        return _TEXT_LOGGING_CONTEXT_CONVERSATIONS
    return tuple(
        conversation
        for conversation in _TEXT_LOGGING_CONTEXT_CONVERSATIONS
        if conversation.kind is kind
    )


def expand_battle_test_prompt_variants(
    scenarios: tuple[BattleTestScenario, ...] | None = None,
) -> tuple[BattleTestScenario, ...]:
    """Expand prompt variants into individually evaluated scenario cases.

    Args:
        scenarios: Optional scenario corpus to expand. Defaults to the read-only
            battle-test corpus.

    Returns:
        A tuple where each prompt variant has a stable variant-specific scenario
        ID such as `BT-READ-001-P01`.
    """
    expanded: list[BattleTestScenario] = []
    for scenario in scenarios or read_only_battle_test_scenarios():
        for index, prompt in enumerate(scenario.prompt_variants, start=1):
            expanded.append(
                BattleTestScenario(
                    id=f"{scenario.id}-P{index:02d}",
                    grade=scenario.grade,
                    prompt_variants=(prompt,),
                    expected_mcp=scenario.expected_mcp,
                    api_oracle=scenario.api_oracle,
                    response_assertions=scenario.response_assertions,
                    cleanup=scenario.cleanup,
                )
            )
    return tuple(expanded)


def sample_battle_test_scenarios(
    scenarios: tuple[BattleTestScenario, ...],
    *,
    max_cases: int | None = None,
    sample_seed: int = 0,
) -> tuple[BattleTestScenario, ...]:
    """Return a deterministic sample from a scenario corpus.

    Args:
        scenarios: Scenario corpus to sample.
        max_cases: Optional maximum number of cases to return. `None` keeps the
            full corpus.
        sample_seed: Seed used when sampling a subset.

    Returns:
        A deterministic, original-order subset of scenarios.
    """
    if max_cases is None or max_cases >= len(scenarios):
        return scenarios
    if max_cases <= 0:
        return ()
    rng = Random(sample_seed)
    selected_indexes = set(rng.sample(range(len(scenarios)), max_cases))
    return tuple(scenario for index, scenario in enumerate(scenarios) if index in selected_indexes)


def sample_battle_test_conversations(
    conversations: tuple[BattleTestConversationScenario, ...],
    *,
    max_cases: int | None = None,
    sample_seed: int = 0,
) -> tuple[BattleTestConversationScenario, ...]:
    """Return a deterministic sample from a chained conversation corpus.

    Args:
        conversations: Conversation corpus to sample.
        max_cases: Optional maximum number of conversations to return. `None`
            keeps the full corpus.
        sample_seed: Seed used when sampling a subset.

    Returns:
        A deterministic, original-order subset of conversations.
    """
    if max_cases is None or max_cases >= len(conversations):
        return conversations
    if max_cases <= 0:
        return ()
    rng = Random(sample_seed)
    selected_indexes = set(rng.sample(range(len(conversations)), max_cases))
    return tuple(
        conversation
        for index, conversation in enumerate(conversations)
        if index in selected_indexes
    )


def conversation_turn_to_scenario(
    conversation: BattleTestConversationScenario,
    turn: BattleTestConversationTurn,
) -> BattleTestScenario:
    """Convert one conversation turn into an evaluatable single-turn scenario.

    Args:
        conversation: Parent conversation scenario.
        turn: Turn contract to convert.

    Returns:
        A single-turn scenario with a stable composite ID.
    """
    return BattleTestScenario(
        id=f"{conversation.id}-{turn.id}",
        grade=turn.grade,
        prompt_variants=(turn.prompt,),
        expected_mcp=turn.expected_mcp,
        api_oracle=turn.api_oracle,
        response_assertions=turn.response_assertions,
        cleanup=turn.cleanup,
    )


def flatten_battle_test_conversations(
    conversations: tuple[BattleTestConversationScenario, ...] | None = None,
) -> tuple[BattleTestScenario, ...]:
    """Flatten chained conversations into turn-level scenarios.

    Args:
        conversations: Optional conversation corpus. Defaults to the read-only
            chained battle-test corpus.

    Returns:
        Single-turn scenario contracts for every conversation turn.
    """
    flattened: list[BattleTestScenario] = []
    for conversation in conversations or read_only_battle_test_conversations():
        flattened.extend(
            conversation_turn_to_scenario(conversation, turn) for turn in conversation.turns
        )
    return tuple(flattened)


def scenario_by_id(scenario_id: str) -> BattleTestScenario:
    """Return one registered battle-test scenario by ID.

    Args:
        scenario_id: Stable scenario identifier to look up.

    Returns:
        The matching scenario.

    Raises:
        KeyError: If `scenario_id` is not part of the read-only corpus.
    """
    scenarios = {
        scenario.id: scenario
        for scenario in (
            expanded_read_only_battle_test_scenarios()
            + smart_list_grounding_battle_test_scenarios()
            + text_logging_context_battle_test_scenarios()
        )
    }
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
            reasoning and Sonnet 4.6 profiles.
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


async def evaluate_battle_test_conversation(
    oracle: ReadOnlyBattleTestOracle,
    conversation: BattleTestConversationScenario,
    transcript: BattleTestConversationTranscript,
) -> BattleTestConversationEvaluation:
    """Evaluate one captured chained conversation.

    Args:
        oracle: Read-only oracle used for each turn evaluation.
        conversation: Expected conversation contract.
        transcript: Captured turn transcripts for the conversation.

    Returns:
        Conversation-level pass/fail result with per-turn evaluations.
    """
    failures: list[str] = []
    if transcript.conversation_id != conversation.id:
        failures.append(
            f"Conversation transcript {transcript.conversation_id!r} does not match "
            f"{conversation.id!r}."
        )
    if transcript.kind is not conversation.kind:
        failures.append(
            f"Conversation transcript kind {transcript.kind!r} does not match "
            f"{conversation.kind!r}."
        )
    expected_scenarios = tuple(
        conversation_turn_to_scenario(conversation, turn) for turn in conversation.turns
    )
    transcript_by_id = {
        turn_transcript.scenario_id: turn_transcript
        for turn_transcript in transcript.turn_transcripts
    }
    evaluations: list[BattleTestEvaluation] = []
    for scenario in expected_scenarios:
        turn_transcript = transcript_by_id.get(scenario.id)
        if turn_transcript is None:
            failures.append(f"Missing transcript for conversation turn {scenario.id!r}.")
            continue
        evaluations.append(await oracle.evaluate(scenario, turn_transcript))
    for turn_transcript in transcript.turn_transcripts:
        if turn_transcript.scenario_id not in {scenario.id for scenario in expected_scenarios}:
            failures.append(
                f"Unexpected transcript for conversation turn {turn_transcript.scenario_id!r}."
            )
    failures.extend(
        f"{evaluation.scenario_id}: {failure}"
        for evaluation in evaluations
        for failure in evaluation.failures
    )
    return BattleTestConversationEvaluation(
        conversation_id=conversation.id,
        kind=conversation.kind,
        passed=not failures,
        turn_evaluations=tuple(evaluations),
        failures=tuple(failures),
    )


async def evaluate_battle_test_conversations(
    oracle: ReadOnlyBattleTestOracle,
    transcripts: tuple[BattleTestConversationTranscript, ...],
    *,
    conversations: tuple[BattleTestConversationScenario, ...] | None = None,
) -> tuple[BattleTestConversationEvaluation, ...]:
    """Evaluate multiple captured chained conversations.

    Args:
        oracle: Read-only oracle used for each turn evaluation.
        transcripts: Captured conversation transcripts.
        conversations: Optional expected conversation corpus.

    Returns:
        Conversation evaluations in corpus order for captured conversations.
    """
    conversation_corpus = conversations or read_only_battle_test_conversations()
    transcript_by_id = {transcript.conversation_id: transcript for transcript in transcripts}
    return tuple(
        [
            await evaluate_battle_test_conversation(
                oracle,
                conversation,
                transcript_by_id[conversation.id],
            )
            for conversation in conversation_corpus
            if conversation.id in transcript_by_id
        ]
    )


def build_battle_test_run_artifact(
    *,
    metadata: BattleTestRunMetadata,
    evaluations: tuple[BattleTestEvaluation, ...],
    total_scenarios: int,
    missing_scenario_ids: tuple[str, ...] = (),
    unknown_transcript_scenario_ids: tuple[str, ...] = (),
    conversation_evaluations: tuple[BattleTestConversationEvaluation, ...] = (),
) -> BattleTestRunArtifact:
    """Build a serializable battle-test run artifact.

    Args:
        metadata: Metadata for the run.
        evaluations: Per-scenario evaluation results.
        total_scenarios: Number of scenarios expected for the run.
        missing_scenario_ids: Scenario IDs that did not have transcripts.
        unknown_transcript_scenario_ids: Transcript scenario IDs outside the
            expected scenario corpus.
        conversation_evaluations: Optional chain-level evaluations.

    Returns:
        A run artifact with computed summary counts.
    """
    passed_count = sum(1 for evaluation in evaluations if evaluation.passed)
    failed_count = sum(1 for evaluation in evaluations if not evaluation.passed)
    missing_count = len(missing_scenario_ids)
    unknown_count = len(unknown_transcript_scenario_ids)
    failure_category_counts = summarize_failure_categories(evaluations)
    return BattleTestRunArtifact(
        metadata=metadata,
        summary=BattleTestRunSummary(
            total_scenarios=total_scenarios,
            evaluated_scenarios=len(evaluations),
            passed_scenarios=passed_count,
            failed_scenarios=failed_count,
            missing_scenarios=missing_count,
            unknown_transcripts=unknown_count,
            failure_category_counts=failure_category_counts,
            overall_passed=failed_count == 0 and missing_count == 0 and unknown_count == 0,
        ),
        evaluations=evaluations,
        missing_scenario_ids=missing_scenario_ids,
        unknown_transcript_scenario_ids=unknown_transcript_scenario_ids,
        conversation_evaluations=conversation_evaluations,
    )


def summarize_failure_categories(
    evaluations: tuple[BattleTestEvaluation, ...],
) -> dict[str, int]:
    """Count failure categories across evaluated scenarios.

    Args:
        evaluations: Evaluations to summarize.

    Returns:
        Category counts keyed by stable category string.
    """
    counts: dict[str, int] = {}
    for evaluation in evaluations:
        categories = evaluation.failure_categories or categorize_battle_test_failures(
            evaluation.failures
        )
        for category in categories:
            counts[category.value] = counts.get(category.value, 0) + 1
    return dict(sorted(counts.items()))


def categorize_battle_test_failures(
    failures: Sequence[str],
) -> tuple[BattleTestFailureCategory, ...]:
    """Derive coarse triage categories from failure messages.

    Args:
        failures: Human-readable failure messages from one evaluation.

    Returns:
        Stable failure categories, deduplicated in first-seen order.
    """
    categories: list[BattleTestFailureCategory] = []
    for failure in failures:
        category = categorize_battle_test_failure(failure)
        if category not in categories:
            categories.append(category)
    return tuple(categories)


def categorize_battle_test_failure(failure: str) -> BattleTestFailureCategory:
    """Derive one coarse triage category from a failure message.

    Args:
        failure: Human-readable failure message from one evaluation.

    Returns:
        The best-effort failure category.
    """
    if "API oracle failed: Transport error while calling Follow Up Boss" in failure:
        return BattleTestFailureCategory.ORACLE_TRANSPORT_ERROR
    if "Expected one of" in failure and "got None" in failure:
        return BattleTestFailureCategory.ROUTE_NO_CALL
    if (
        "Expected one of" in failure
        or "Selected forbidden tool" in failure
        or "Expected an allowed safe route" in failure
    ):
        return BattleTestFailureCategory.ROUTE_WRONG_TOOL
    if "Expected the assistant to explain the unsupported API capability" in failure:
        return BattleTestFailureCategory.UNSUPPORTED_NOT_EXPLAINED
    if failure.startswith("Expected ") or "API oracle failed:" in failure:
        return BattleTestFailureCategory.ORACLE_RESPONSE_MISMATCH
    return BattleTestFailureCategory.UNKNOWN


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
            transcript,
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
        if scenario.api_oracle.kind is BattleTestOracleKind.MY_UPCOMING_TASKS:
            return await self._upcoming_task_snapshot(scenario, transcript)
        if scenario.api_oracle.kind is BattleTestOracleKind.SMART_LISTS:
            return await self._page_snapshot(
                scenario,
                await self._services.smart_lists.list_smart_lists(
                    SmartListListRequest(
                        include_all=_optional_bool(transcript.arguments.get("include_all")),
                        limit=_optional_int(transcript.arguments.get("limit")),
                        offset=_optional_int(transcript.arguments.get("offset")),
                    )
                ),
                response_key="smartlists",
                expected_key="smart_list_ids",
            )
        if scenario.api_oracle.kind is BattleTestOracleKind.NAMED_SMART_LIST_PEOPLE:
            return await self._named_smart_list_people_snapshot(scenario, transcript)
        if scenario.api_oracle.kind is BattleTestOracleKind.PEOPLE_SEARCH:
            return await self._page_snapshot(
                scenario,
                await self._services.people.search_people(
                    PeopleSearchRequest(
                        assigned_to=_optional_string(transcript.arguments.get("assigned_to")),
                        assigned_user_id=_optional_int(
                            transcript.arguments.get("assigned_user_id")
                        ),
                        contacted=_optional_bool(transcript.arguments.get("contacted")),
                        email=_optional_string(transcript.arguments.get("email")),
                        limit=_optional_int(transcript.arguments.get("limit")),
                        name=_optional_string(transcript.arguments.get("name")),
                        phone=_optional_string(transcript.arguments.get("phone")),
                        smart_list_id=_optional_int(transcript.arguments.get("smart_list_id")),
                        source=_optional_string(transcript.arguments.get("source")),
                        stage=_optional_string(transcript.arguments.get("stage")),
                    )
                ),
                response_key="people",
                expected_key="person_ids",
            )
        if scenario.api_oracle.kind is BattleTestOracleKind.MY_UNCONTACTED_LEADS:
            return await self._uncontacted_leads_snapshot(scenario, transcript)
        if scenario.api_oracle.kind is BattleTestOracleKind.PERSON_DUPLICATE_CHECK:
            return await self._duplicate_person_snapshot(scenario, transcript)
        if scenario.api_oracle.kind is BattleTestOracleKind.UNCLAIMED_PEOPLE:
            return await self._page_snapshot(
                scenario,
                await self._services.people.list_unclaimed_people(
                    UnclaimedPeopleListRequest(
                        limit=_optional_int(transcript.arguments.get("limit")),
                        offset=_optional_int(transcript.arguments.get("offset")),
                    )
                ),
                response_key="people",
                expected_key="person_ids",
            )
        if scenario.api_oracle.kind is BattleTestOracleKind.APPOINTMENTS:
            return await self._page_snapshot(
                scenario,
                await self._services.appointments.list_appointments(
                    AppointmentListRequest(
                        limit=_optional_int(transcript.arguments.get("limit")),
                        offset=_optional_int(transcript.arguments.get("offset")),
                        person_id=_optional_int(transcript.arguments.get("person_id")),
                        user_id=_optional_int(transcript.arguments.get("user_id")),
                    )
                ),
                response_key="appointments",
                expected_key="appointment_ids",
            )
        if scenario.api_oracle.kind is BattleTestOracleKind.CALLS:
            return await self._page_snapshot(
                scenario,
                await self._services.calls.list_calls(
                    CallListRequest(
                        limit=_optional_int(transcript.arguments.get("limit")),
                        offset=_optional_int(transcript.arguments.get("offset")),
                        person_id=_optional_int(transcript.arguments.get("person_id")),
                        phone=_optional_string(transcript.arguments.get("phone")),
                    )
                ),
                response_key="calls",
                expected_key="call_ids",
            )
        if scenario.api_oracle.kind is BattleTestOracleKind.TEXT_MESSAGES:
            return await self._page_snapshot(
                scenario,
                await self._services.text_messages.list_text_messages(
                    TextMessageListRequest(
                        person_id=_optional_int(transcript.arguments.get("person_id")),
                    )
                ),
                response_key="textmessages",
                expected_key="text_message_ids",
            )
        if scenario.api_oracle.kind is BattleTestOracleKind.PERSON_ACTIVITY:
            return await self._person_activity_snapshot(scenario, transcript)
        if scenario.api_oracle.kind is BattleTestOracleKind.TEMPLATES:
            return await self._page_snapshot(
                scenario,
                await self._services.templates.list_templates(
                    TemplateListRequest(
                        limit=_optional_int(transcript.arguments.get("limit")),
                        offset=_optional_int(transcript.arguments.get("offset")),
                    )
                ),
                response_key="templates",
                expected_key="template_ids",
            )
        if scenario.api_oracle.kind is BattleTestOracleKind.TEXT_MESSAGE_TEMPLATES:
            return await self._page_snapshot(
                scenario,
                await self._services.text_message_templates.list_text_message_templates(
                    TextMessageTemplateListRequest(
                        limit=_optional_int(transcript.arguments.get("limit")),
                        offset=_optional_int(transcript.arguments.get("offset")),
                    )
                ),
                response_key="textmessagetemplates",
                expected_key="template_ids",
            )
        if scenario.api_oracle.kind is BattleTestOracleKind.EXPLICIT_NOTE:
            return await self._explicit_note_snapshot(scenario, transcript)
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
        if (
            scenario.api_oracle.kind is BattleTestOracleKind.ROUTE_ONLY_PENDING
            and scenario.grade
            in {
                BattleTestGrade.MUST_CLARIFY,
                BattleTestGrade.MUST_REQUIRE_ID,
            }
        ):
            return BattleTestOracleSnapshot(
                scenario_id=scenario.id,
                kind=scenario.api_oracle.kind,
                automated=True,
                expected={"route_only": True},
                notes=("Route-only safety scenario passed its route-level contract.",),
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
            failure_categories=categorize_battle_test_failures(failures),
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

    async def _upcoming_task_snapshot(
        self,
        scenario: BattleTestScenario,
        transcript: BattleTestTranscript,
    ) -> BattleTestOracleSnapshot:
        """Build direct API truth for authenticated-user upcoming tasks."""
        user_id = await self._authenticated_user_id()
        due_start = _upcoming_task_due_start()
        page = await self._services.tasks.list_tasks(
            TaskListRequest(
                assigned_user_id=user_id,
                due_start=due_start,
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
                "due_start": due_start.isoformat(),
                "is_completed": False,
                "task_ids": [task.id for task in page.items],
            },
        )

    async def _uncontacted_leads_snapshot(
        self,
        scenario: BattleTestScenario,
        transcript: BattleTestTranscript,
    ) -> BattleTestOracleSnapshot:
        """Build direct API truth for no-last-communication people-search helpers.

        Args:
            scenario: Scenario contract being checked.
            transcript: Captured helper transcript whose owner and pagination
                arguments should be mirrored by direct API search.

        Returns:
            A stable snapshot containing expected uncontacted person IDs and
            owner-scope metadata.
        """
        mine = _optional_bool(transcript.arguments.get("mine")) is not False
        tool_input = ListUncontactedLeadsToolInput(
            assigned_user_id=_optional_int(transcript.arguments.get("assigned_user_id")),
            assigned_user_name=_optional_string(transcript.arguments.get("assigned_user_name")),
            owner_name=_optional_string(transcript.arguments.get("owner_name")),
            agent_name=_optional_string(transcript.arguments.get("agent_name")),
            fields=_optional_string_list(transcript.arguments.get("fields")),
            lead_source=_optional_string(transcript.arguments.get("lead_source")),
            mine=mine,
            next_token=_optional_string(transcript.arguments.get("next_token")),
            offset=_optional_int(transcript.arguments.get("offset")),
            limit=_optional_int(transcript.arguments.get("limit")),
            source=_optional_string(transcript.arguments.get("source")),
            source_name=_optional_string(transcript.arguments.get("source_name")),
            stage=_optional_string(transcript.arguments.get("stage")),
        )
        service_bundle = cast(Any, self._services)
        assigned_user_id = await tool_input.resolved_assigned_user_id(service_bundle)
        page = await FollowUpBossToolAdapter(service_bundle)._list_uncontacted_leads(
            tool_input.model_copy(update={"assigned_user_id": assigned_user_id})
        )
        return BattleTestOracleSnapshot(
            scenario_id=scenario.id,
            kind=scenario.api_oracle.kind,
            automated=True,
            expected={
                "response_key": "people",
                "assigned_user_id": assigned_user_id,
                "last_communication": None,
                "mine": mine,
                "person_ids": [_record_id(person) for person in page.items],
            },
        )

    async def _page_snapshot(
        self,
        scenario: BattleTestScenario,
        page: PageResult[Any],
        *,
        response_key: str,
        expected_key: str,
    ) -> BattleTestOracleSnapshot:
        """Build direct API truth for a generic paginated read-only response.

        Args:
            scenario: Scenario contract being checked.
            page: Direct API page result.
            response_key: MCP response key containing records.
            expected_key: Snapshot key used for expected record IDs.

        Returns:
            A stable snapshot containing expected IDs and response-key metadata.
        """
        return BattleTestOracleSnapshot(
            scenario_id=scenario.id,
            kind=scenario.api_oracle.kind,
            automated=True,
            expected={
                "response_key": response_key,
                expected_key: [_record_id(item) for item in page.items],
            },
        )

    async def _person_activity_snapshot(
        self,
        scenario: BattleTestScenario,
        transcript: BattleTestTranscript,
    ) -> BattleTestOracleSnapshot:
        """Build direct API truth for person-scoped communication activity.

        Args:
            scenario: Scenario contract being checked.
            transcript: Captured helper transcript whose `person_id` and
                include flags should be mirrored by direct API calls.

        Returns:
            A stable snapshot containing per-surface expected IDs.

        Raises:
            RuntimeError: If the transcript omits the required `person_id`.
        """
        person_id = _optional_int(transcript.arguments.get("person_id"))
        if person_id is None:
            raise RuntimeError("Person activity oracle requires a person_id argument.")

        limit = _optional_int(transcript.arguments.get("limit"))
        offset = _optional_int(transcript.arguments.get("offset"))
        expected: JsonObject = {"person_id": person_id}
        person = await self._services.people.get_person(person_id)
        expected["resolved_person_id"] = person.id

        if _optional_bool(transcript.arguments.get("include_calls")) is not False:
            calls = await self._services.calls.list_calls(
                CallListRequest(limit=limit, offset=offset, person_id=person_id)
            )
            expected["call_ids"] = [_record_id(item) for item in calls.items]

        if _optional_bool(transcript.arguments.get("include_text_messages")) is not False:
            text_messages = await self._services.text_messages.list_text_messages(
                TextMessageListRequest(person_id=person_id)
            )
            expected["text_message_ids"] = [_record_id(item) for item in text_messages.items]

        if _optional_bool(transcript.arguments.get("include_email_events")) is not False:
            email_events = await self._services.email_marketing.list_email_events(
                EmailEventListRequest(limit=limit, offset=offset, person_id=person_id)
            )
            expected["email_event_ids"] = [_record_id(item) for item in email_events.items]

        if _optional_bool(transcript.arguments.get("include_events")) is not False:
            events = await self._services.events.search_events(
                EventSearchRequest(limit=limit, offset=offset, person_id=person_id)
            )
            expected["event_ids"] = [_record_id(item) for item in events.items]

        if _optional_bool(transcript.arguments.get("include_appointments")) is not False:
            appointments = await self._services.appointments.list_appointments(
                AppointmentListRequest(limit=limit, offset=offset, person_id=person_id)
            )
            expected["appointment_ids"] = [_record_id(item) for item in appointments.items]

        return BattleTestOracleSnapshot(
            scenario_id=scenario.id,
            kind=scenario.api_oracle.kind,
            automated=True,
            expected=expected,
        )

    async def _named_smart_list_people_snapshot(
        self,
        scenario: BattleTestScenario,
        transcript: BattleTestTranscript,
    ) -> BattleTestOracleSnapshot:
        """Build direct API truth for people inside one named smart list.

        Args:
            scenario: Scenario contract with `api_oracle.smart_list_name`.
            transcript: Captured people-search transcript whose `smart_list_id`
                must match the resolved list.

        Returns:
            A stable snapshot containing resolved list identity and allowed
            person identifiers for response and answer grounding.

        Raises:
            RuntimeError: If the scenario does not name a smart list, or if the
                list name is missing or ambiguous in Follow Up Boss.
        """
        smart_list_name = scenario.api_oracle.smart_list_name
        if smart_list_name is None:
            raise RuntimeError("Named smart-list oracle requires a smart_list_name.")
        smart_list = _resolve_named_smart_list(
            await self._list_all_smart_lists(),
            smart_list_name,
        )
        mine = (
            True
            if scenario.api_oracle.requires_authenticated_owner_scope
            else _optional_bool(transcript.arguments.get("mine")) is not False
        )
        assigned_user_id = (
            None
            if scenario.api_oracle.requires_authenticated_owner_scope
            else _optional_int(transcript.arguments.get("assigned_user_id"))
        )
        assigned_user_name = (
            None
            if scenario.api_oracle.requires_authenticated_owner_scope
            else _optional_string(transcript.arguments.get("assigned_user_name"))
        )
        if assigned_user_id is None and assigned_user_name is not None:
            assigned_user_id = await self._resolve_user_id_by_name(assigned_user_name)
        if assigned_user_id is None and mine:
            assigned_user_id = await self._authenticated_user_id()
        page = await self._services.people.search_people(
            PeopleSearchRequest(
                assigned_user_id=assigned_user_id,
                fields=_optional_string_list(transcript.arguments.get("fields")),
                limit=_optional_int(transcript.arguments.get("limit")),
                next_token=_optional_string(transcript.arguments.get("next_token")),
                offset=_optional_int(transcript.arguments.get("offset")),
                source=_named_smart_list_source_filter(
                    smart_list.name or smart_list_name,
                    transcript,
                ),
                stage=_optional_string(transcript.arguments.get("stage")),
                smart_list_id=smart_list.id,
            )
        )
        return BattleTestOracleSnapshot(
            scenario_id=scenario.id,
            kind=scenario.api_oracle.kind,
            automated=True,
            expected={
                "response_key": "people",
                "smart_list_id": smart_list.id,
                "smart_list_name": smart_list.name or smart_list_name,
                "assigned_user_id": assigned_user_id,
                "mine": mine,
                "person_ids": [_record_id(person) for person in page.items],
                "answer_must_be_grounded": scenario.api_oracle.answer_must_be_grounded,
                "allowed_answer_names": _person_answer_names(page.items),
                "allowed_answer_phones": _person_answer_phones(page.items),
            },
        )

    async def _list_all_smart_lists(self) -> list[SmartListRecord]:
        """List every visible smart list for named-list oracle resolution.

        Returns:
            Smart-list records across all available pages.
        """
        smart_lists: list[SmartListRecord] = []
        offset = 0
        while True:
            page = await self._services.smart_lists.list_smart_lists(
                SmartListListRequest(include_all=True, limit=100, offset=offset)
            )
            smart_lists.extend(page.items)
            if not page.metadata.has_next() or page.metadata.count == 0:
                return smart_lists
            offset = page.metadata.offset + page.metadata.count

    async def _resolve_user_id_by_name(self, assigned_user_name: str) -> int:
        """Resolve one active user by exact normalized name for oracle truth.

        Args:
            assigned_user_name: Owner name supplied to the MCP transcript.

        Returns:
            The unique active Follow Up Boss user ID.

        Raises:
            RuntimeError: If no active user or multiple active users match.
        """
        users = await self._list_all_users_for_name(assigned_user_name)
        normalized_name = _normalize_user_name(assigned_user_name)
        matches = [
            user
            for user in users
            if _normalize_user_name(user.name or _user_full_name(user)) == normalized_name
            and _is_active_user(user)
        ]
        if not matches:
            raise RuntimeError(
                f"Active Follow Up Boss user named {assigned_user_name!r} was not found."
            )
        if len(matches) > 1:
            match_ids = [user.id for user in matches]
            raise RuntimeError(
                f"Active Follow Up Boss user named {assigned_user_name!r} is ambiguous; "
                f"matched IDs {match_ids!r}."
            )
        return matches[0].id

    async def _list_all_users_for_name(self, assigned_user_name: str) -> list[UserRecord]:
        """List all pages for an exact owner-name oracle lookup.

        Args:
            assigned_user_name: Name query sent to the users service.

        Returns:
            User records returned by every page of the users endpoint.
        """
        users: list[UserRecord] = []
        offset = 0
        while True:
            page = await self._services.users.list_users(
                UserListRequest(
                    include_deleted=False,
                    limit=100,
                    name=assigned_user_name,
                    offset=offset,
                )
            )
            users.extend(page.items)
            if not page.metadata.has_next() or page.metadata.count == 0:
                return users
            offset = page.metadata.offset + page.metadata.count

    async def _duplicate_person_snapshot(
        self,
        scenario: BattleTestScenario,
        transcript: BattleTestTranscript,
    ) -> BattleTestOracleSnapshot:
        """Build direct API truth for a duplicate-person check."""
        duplicate = await self._services.people.check_duplicate_person(
            PersonDuplicateCheckRequest(
                email=_optional_string(transcript.arguments.get("email")),
                phone=_optional_string(transcript.arguments.get("phone")),
            )
        )
        return BattleTestOracleSnapshot(
            scenario_id=scenario.id,
            kind=scenario.api_oracle.kind,
            automated=True,
            expected={
                "found": duplicate.found,
                "matched_by": duplicate.matched_by,
            },
        )

    async def _explicit_note_snapshot(
        self,
        scenario: BattleTestScenario,
        transcript: BattleTestTranscript,
    ) -> BattleTestOracleSnapshot:
        """Build direct API truth for an explicit note lookup."""
        note_id = _optional_int(transcript.arguments.get("note_id"))
        if note_id is None:
            raise RuntimeError("Explicit note oracle requires a note_id argument.")
        note = await self._services.notes.get_note(note_id)
        return BattleTestOracleSnapshot(
            scenario_id=scenario.id,
            kind=scenario.api_oracle.kind,
            automated=True,
            expected={"note_id": note.id},
        )


def _check_required_route(
    scenario: BattleTestScenario,
    transcript: BattleTestTranscript,
    failures: list[str],
) -> None:
    """Append failures for a required-route scenario."""
    selected_tool = transcript.selected_tool
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
    if (
        transcript.selected_tool is not None
        and transcript.selected_tool not in scenario.expected_mcp.allowed_tools
    ):
        failures.append(
            f"Expected one of {scenario.expected_mcp.allowed_tools!r}, "
            f"got {transcript.selected_tool!r}."
        )
    if missing and not transcript.clarified:
        failures.append(
            f"Expected explicit arguments or clarification for missing keys {missing!r}."
        )
    if missing and transcript.selected_tool is not None:
        failures.append(
            f"Selected {transcript.selected_tool!r} without required arguments {missing!r}."
        )
    wrong_values = {
        key: {"expected": expected_value, "actual": transcript.arguments.get(key)}
        for key, expected_value in scenario.expected_mcp.required_argument_values.items()
        if transcript.arguments.get(key) != expected_value
    }
    if wrong_values and not transcript.clarified:
        failures.append(f"Expected explicit argument values {wrong_values!r}.")


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
        BattleTestOracleKind.MY_UPCOMING_TASKS,
    }:
        return _compare_task_response(transcript, snapshot)
    if snapshot.kind in {
        BattleTestOracleKind.APPOINTMENTS,
        BattleTestOracleKind.CALLS,
        BattleTestOracleKind.SMART_LISTS,
        BattleTestOracleKind.TEMPLATES,
        BattleTestOracleKind.TEXT_MESSAGE_TEMPLATES,
        BattleTestOracleKind.TEXT_MESSAGES,
        BattleTestOracleKind.UNCLAIMED_PEOPLE,
    }:
        return _compare_page_response(transcript, snapshot)
    if snapshot.kind is BattleTestOracleKind.PEOPLE_SEARCH:
        return _compare_page_response(transcript, snapshot)
    if snapshot.kind is BattleTestOracleKind.MY_UNCONTACTED_LEADS:
        return _compare_page_response(transcript, snapshot)
    if snapshot.kind is BattleTestOracleKind.NAMED_SMART_LIST_PEOPLE:
        return _compare_named_smart_list_people_response(transcript, snapshot)
    if snapshot.kind is BattleTestOracleKind.PERSON_ACTIVITY:
        return _compare_person_activity_response(transcript, snapshot)
    if snapshot.kind is BattleTestOracleKind.PERSON_DUPLICATE_CHECK:
        return _compare_duplicate_response(transcript, snapshot)
    if snapshot.kind is BattleTestOracleKind.EXPLICIT_NOTE:
        return _compare_single_id_response(transcript, snapshot, expected_key="note_id")
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


def _compare_page_response(
    transcript: BattleTestTranscript,
    snapshot: BattleTestOracleSnapshot,
) -> list[str]:
    """Compare a generic paginated MCP response to API truth."""
    response = _mapping_or_none(transcript.response)
    if response is None:
        return ["Expected paginated MCP response to be an object."]
    response_key = snapshot.expected.get("response_key")
    if not isinstance(response_key, str):
        return ["Expected page oracle snapshot to include a response key."]
    records = response.get(response_key)
    if not isinstance(records, list):
        return [f"Expected MCP response to include a {response_key!r} list."]
    actual_ids = [item.get("id") for item in records if isinstance(item, dict)]
    expected_ids = _first_expected_id_list(snapshot)
    if actual_ids != expected_ids:
        return [f"Expected {response_key} ids {expected_ids!r}, got {actual_ids!r}."]
    return []


def _compare_named_smart_list_people_response(
    transcript: BattleTestTranscript,
    snapshot: BattleTestOracleSnapshot,
) -> list[str]:
    """Compare a named-smart-list people response to resolved API truth."""
    failures: list[str] = []
    expected_smart_list_id = snapshot.expected.get("smart_list_id")
    expected_smart_list_name = snapshot.expected.get("smart_list_name")
    if transcript.selected_tool == "followupboss_search_people_in_smart_list":
        failures.extend(
            _compare_named_smart_list_helper_route(
                transcript,
                expected_smart_list_id=expected_smart_list_id,
                expected_smart_list_name=expected_smart_list_name,
                expected_assigned_user_id=snapshot.expected.get("assigned_user_id"),
            )
        )
    elif transcript.selected_tool == "followupboss_search_people":
        actual_smart_list_id = _optional_int(transcript.arguments.get("smart_list_id"))
        if actual_smart_list_id != expected_smart_list_id:
            failures.append(
                f"Expected named smart-list search to use smart_list_id "
                f"{expected_smart_list_id!r}, got {actual_smart_list_id!r}."
            )
    else:
        failures.append(
            "Expected named smart-list people scenario to use "
            "followupboss_search_people_in_smart_list or followupboss_search_people."
        )
    failures.extend(_compare_page_response(transcript, snapshot))
    failures.extend(_compare_named_smart_list_owner_response(transcript, snapshot))
    if snapshot.expected.get("answer_must_be_grounded") is True:
        failures.extend(_compare_assistant_answer_grounding(transcript, snapshot))
    return failures


def _compare_named_smart_list_helper_route(
    transcript: BattleTestTranscript,
    *,
    expected_smart_list_id: JsonValue,
    expected_smart_list_name: JsonValue,
    expected_assigned_user_id: JsonValue,
) -> list[str]:
    """Compare helper arguments and provenance for a named smart-list search."""
    failures: list[str] = []
    actual_name = _optional_string(transcript.arguments.get("smart_list_name"))
    if not isinstance(expected_smart_list_name, str):
        failures.append("Expected named smart-list oracle snapshot to include a list name.")
    elif actual_name is None or _normalize_smart_list_name(
        actual_name
    ) != _normalize_smart_list_name(expected_smart_list_name):
        failures.append(
            f"Expected helper smart_list_name {expected_smart_list_name!r}, got {actual_name!r}."
        )
    response = _mapping_or_none(transcript.response)
    smart_list = response.get("smartlist") if response is not None else None
    if not isinstance(smart_list, dict):
        failures.append("Expected helper response to include a smartlist object.")
    elif smart_list.get("id") != expected_smart_list_id:
        failures.append(
            f"Expected helper smartlist id {expected_smart_list_id!r}, "
            f"got {smart_list.get('id')!r}."
        )
    if isinstance(expected_smart_list_name, str) and _is_eligible_for_transfer_smart_list(
        expected_smart_list_name
    ):
        actual_source = _optional_string(transcript.arguments.get("source"))
        if actual_source is not None:
            failures.append(
                "Expected Eligible For Transfer route to omit lead-source filters; "
                f"got source={actual_source!r}."
            )
    if isinstance(expected_assigned_user_id, int):
        actual_assigned_user_id = _optional_int(transcript.arguments.get("assigned_user_id"))
        if _optional_bool(transcript.arguments.get("mine")) is False and (
            actual_assigned_user_id != expected_assigned_user_id
        ):
            failures.append(
                "Expected helper route to include owner scope "
                f"{expected_assigned_user_id!r}, got {actual_assigned_user_id!r}."
            )
    return failures


def _compare_named_smart_list_owner_response(
    transcript: BattleTestTranscript,
    snapshot: BattleTestOracleSnapshot,
) -> list[str]:
    """Compare returned people owner scope for named smart-list responses.

    Args:
        transcript: Captured MCP transcript to inspect.
        snapshot: API oracle snapshot containing the expected owner, if any.

    Returns:
        Owner-scope failures for response records that expose `assignedUserId`.
    """
    expected_assigned_user_id = snapshot.expected.get("assigned_user_id")
    if not isinstance(expected_assigned_user_id, int):
        return []
    response = _mapping_or_none(transcript.response)
    records = response.get("people") if response is not None else None
    if not isinstance(records, list):
        return []
    wrong_owner_ids = [
        record.get("id")
        for record in records
        if isinstance(record, dict)
        and record.get("assignedUserId") is not None
        and record.get("assignedUserId") != expected_assigned_user_id
    ]
    if not wrong_owner_ids:
        return []
    return [
        "Expected all returned people to match assigned_user_id "
        f"{expected_assigned_user_id!r}; off-owner ids: {wrong_owner_ids!r}."
    ]


def _compare_person_activity_response(
    transcript: BattleTestTranscript,
    snapshot: BattleTestOracleSnapshot,
) -> list[str]:
    """Compare a person-activity helper response to direct API truth."""
    response = _mapping_or_none(transcript.response)
    if response is None:
        return ["Expected person-activity MCP response to be an object."]

    failures: list[str] = []
    person = response.get("person")
    expected_person_id = snapshot.expected.get("resolved_person_id")
    if not isinstance(person, dict):
        failures.append("Expected person-activity MCP response to include a person object.")
    elif person.get("id") != expected_person_id:
        failures.append(
            f"Expected person-activity person id {expected_person_id!r}, got {person.get('id')!r}."
        )

    response_expectations = (
        ("calls", "call_ids"),
        ("textmessages", "text_message_ids"),
        ("emEvents", "email_event_ids"),
        ("events", "event_ids"),
        ("appointments", "appointment_ids"),
    )
    for response_key, expected_key in response_expectations:
        if expected_key not in snapshot.expected:
            continue
        records = response.get(response_key)
        if not isinstance(records, list):
            failures.append(f"Expected person-activity response to include {response_key!r}.")
            continue
        actual_ids = [item.get("id") for item in records if isinstance(item, dict)]
        expected_ids = snapshot.expected.get(expected_key)
        if actual_ids != expected_ids:
            failures.append(f"Expected {response_key} ids {expected_ids!r}, got {actual_ids!r}.")
        off_scope_ids = [
            item.get("id")
            for item in records
            if isinstance(item, dict)
            and item.get("personId") is not None
            and item.get("personId") != snapshot.expected.get("person_id")
        ]
        if off_scope_ids:
            failures.append(
                "Expected person-activity records to stay scoped to "
                f"person {snapshot.expected.get('person_id')!r}; off-scope IDs: {off_scope_ids!r}."
            )

    return failures


def _compare_assistant_answer_grounding(
    transcript: BattleTestTranscript,
    snapshot: BattleTestOracleSnapshot,
) -> list[str]:
    """Verify assistant-visible answer identifiers are grounded in oracle people."""
    message = transcript.assistant_message
    if not message:
        return []
    allowed_phone_values = snapshot.expected.get("allowed_answer_phones")
    allowed_name_values = snapshot.expected.get("allowed_answer_names")
    allowed_phone_list = allowed_phone_values if isinstance(allowed_phone_values, list) else []
    allowed_name_list = allowed_name_values if isinstance(allowed_name_values, list) else []
    allowed_phones = {
        str(phone) for phone in allowed_phone_list if isinstance(phone, str) and phone
    }
    allowed_names = {
        str(name).casefold() for name in allowed_name_list if isinstance(name, str) and name
    }
    failures: list[str] = []
    expected_person_ids = snapshot.expected.get("person_ids")
    if (
        isinstance(expected_person_ids, list)
        and len(expected_person_ids) > 0
        and _answer_claims_empty_smart_list(message)
    ):
        failures.append(
            "Assistant answer claimed the named smart-list result was empty despite "
            f"oracle people ids {expected_person_ids!r}."
        )
    for phone in _phone_like_tokens(message):
        normalized_phone = _normalize_phone(phone)
        if normalized_phone and normalized_phone not in allowed_phones:
            failures.append(
                f"Assistant answer mentioned off-list phone {phone!r} for named smart-list "
                "scenario."
            )
    for row_name in _table_like_answer_names(message):
        if row_name.casefold() not in allowed_names:
            failures.append(
                f"Assistant answer mentioned off-list name {row_name!r} for named smart-list "
                "scenario."
            )
    return failures


def _compare_duplicate_response(
    transcript: BattleTestTranscript,
    snapshot: BattleTestOracleSnapshot,
) -> list[str]:
    """Compare a duplicate-check MCP response to API truth."""
    response = _mapping_or_none(transcript.response)
    if response is None:
        return ["Expected duplicate-check MCP response to be an object."]
    failures: list[str] = []
    if response.get("found") != snapshot.expected.get("found"):
        failures.append(
            f"Expected duplicate found={snapshot.expected.get('found')!r}, "
            f"got {response.get('found')!r}."
        )
    if response.get("matchedBy") != snapshot.expected.get("matched_by"):
        failures.append(
            f"Expected duplicate matchedBy={snapshot.expected.get('matched_by')!r}, "
            f"got {response.get('matchedBy')!r}."
        )
    return failures


def _compare_single_id_response(
    transcript: BattleTestTranscript,
    snapshot: BattleTestOracleSnapshot,
    *,
    expected_key: str,
) -> list[str]:
    """Compare a single-object MCP response ID to API truth."""
    response = _mapping_or_none(transcript.response)
    if response is None:
        return ["Expected single-object MCP response to be an object."]
    expected_id = snapshot.expected.get(expected_key)
    actual_id = response.get("id")
    if actual_id != expected_id:
        return [f"Expected response id {expected_id!r}, got {actual_id!r}."]
    return []


def _first_expected_id_list(snapshot: BattleTestOracleSnapshot) -> list[JsonValue] | None:
    """Return the first ID-list value from an oracle snapshot."""
    for key, value in snapshot.expected.items():
        if key.endswith("_ids") and isinstance(value, list):
            return value
    return None


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


def _optional_bool(value: JsonValue) -> bool | None:
    """Return an optional boolean transcript argument."""
    if isinstance(value, bool):
        return value
    return None


def _resolve_named_smart_list(
    smart_lists: Sequence[SmartListRecord],
    smart_list_name: str,
) -> SmartListRecord:
    """Resolve a smart list by exact normalized name.

    Args:
        smart_lists: Candidate smart lists returned by Follow Up Boss.
        smart_list_name: User-facing list name to resolve.

    Returns:
        The uniquely matching smart list.

    Raises:
        RuntimeError: If no list or more than one list matches the normalized
            name.
    """
    target = _normalize_smart_list_name(smart_list_name)
    matches = [
        smart_list
        for smart_list in smart_lists
        if _normalize_smart_list_name(smart_list.name or "") == target
    ]
    if not matches:
        raise RuntimeError(f"Smart list named {smart_list_name!r} was not found.")
    if len(matches) > 1:
        match_ids = [smart_list.id for smart_list in matches]
        raise RuntimeError(
            f"Smart list named {smart_list_name!r} is ambiguous; matched IDs {match_ids!r}."
        )
    return matches[0]


def _normalize_smart_list_name(value: str) -> str:
    """Normalize a smart-list name for exact matching."""
    collapsed = " ".join(value.casefold().strip().split())
    return _strip_decorative_smart_list_name_edges(collapsed)


def _is_eligible_for_transfer_smart_list(value: str) -> bool:
    """Return whether a smart-list name is the Zillow transfer boundary.

    Args:
        value: Raw or normalized smart-list name.

    Returns:
        `True` when the name matches `Eligible For Transfer`.
    """
    return _normalize_smart_list_name(value) == "eligible for transfer"


def _named_smart_list_source_filter(
    smart_list_name: str,
    transcript: BattleTestTranscript,
) -> str | None:
    """Return the source filter that should be mirrored by the oracle.

    Args:
        smart_list_name: Resolved smart-list name for the route.
        transcript: Captured tool transcript that may include optional filters.

    Returns:
        The transcript source filter, except for `Eligible For Transfer` where the
        list itself is the lead-source boundary.
    """
    if _is_eligible_for_transfer_smart_list(smart_list_name):
        return None
    return _optional_string(transcript.arguments.get("source"))


def _normalize_user_name(value: str) -> str:
    """Normalize a Follow Up Boss user name for exact matching.

    Args:
        value: Raw user name from a transcript or API user record.

    Returns:
        Lowercased text with repeated whitespace collapsed.
    """
    return " ".join(value.casefold().strip().split())


def _user_full_name(user: UserRecord) -> str:
    """Return a display name assembled from user first and last names.

    Args:
        user: Follow Up Boss user record.

    Returns:
        First and last names joined with single spaces.
    """
    return " ".join(part for part in (user.first_name, user.last_name) if part)


def _is_active_user(user: UserRecord) -> bool:
    """Return whether a user should be considered active for oracle routing.

    Args:
        user: Follow Up Boss user record.

    Returns:
        `True` if the user status is absent or not a deleted/inactive status.
    """
    if user.status is None:
        return True
    return user.status.casefold() not in {"deleted", "disabled", "inactive", "archived"}


def _strip_decorative_smart_list_name_edges(value: str) -> str:
    """Remove decorative symbols from the edges of a smart-list name."""
    start = 0
    end = len(value)
    while start < end and not value[start].isalnum():
        start += 1
    while end > start and not value[end - 1].isalnum():
        end -= 1
    return value[start:end].strip()


def _person_answer_names(people: Sequence[PersonRecord]) -> list[JsonValue]:
    """Return person names allowed in a grounded assistant answer."""
    names: list[JsonValue] = []
    for person in people:
        for name in (person.name, _join_person_name(person.first_name, person.last_name)):
            if name and name not in names:
                names.append(name)
    return names


def _person_answer_phones(people: Sequence[PersonRecord]) -> list[JsonValue]:
    """Return normalized phone numbers allowed in a grounded assistant answer."""
    phones: list[JsonValue] = []
    for person in people:
        for phone in person.phones:
            normalized = _normalize_phone(phone.value)
            if normalized and normalized not in phones:
                phones.append(normalized)
    return phones


def _join_person_name(first_name: str | None, last_name: str | None) -> str | None:
    """Join first and last names when either component is present."""
    name = " ".join(part for part in (first_name, last_name) if part)
    return name or None


def _phone_like_tokens(value: str) -> tuple[str, ...]:
    """Extract phone-like tokens from assistant text."""
    tokens: list[str] = []
    current: list[str] = []
    for character in value:
        if character.isdigit() or character in {"(", ")", "-", ".", " ", "+"}:
            current.append(character)
            continue
        token = "".join(current).strip()
        if _normalize_phone(token):
            tokens.append(token)
        current = []
    token = "".join(current).strip()
    if _normalize_phone(token):
        tokens.append(token)
    return tuple(tokens)


def _table_like_answer_names(value: str) -> tuple[str, ...]:
    """Extract likely table-row names from assistant answer text."""
    names: list[str] = []
    for raw_line in value.splitlines():
        line = raw_line.strip()
        if not line or "|" not in line:
            continue
        first_cell = line.split("|", 1)[0].strip()
        if not first_cell or first_cell.casefold() in {"name", "---"}:
            continue
        if any(character.isalpha() for character in first_cell):
            names.append(first_cell)
    return tuple(names)


def _answer_claims_empty_smart_list(value: str) -> bool:
    """Return whether an assistant answer says the scoped smart-list result is empty.

    Args:
        value: Assistant-visible text to inspect.

    Returns:
        `True` when the answer contains common empty-result wording for a
        smart-list-scoped lead result.
    """
    normalized = " ".join(value.casefold().split())
    empty_phrases = (
        "smart list is currently empty",
        "smart-list is currently empty",
        "smart list is empty",
        "smart-list is empty",
        "no zillow leads",
        "no scoped people",
        "nothing at imminent risk",
        "nothing in that list",
        "no leads in that list",
    )
    return any(phrase in normalized for phrase in empty_phrases)


def _normalize_phone(value: str) -> str | None:
    """Normalize a phone string to digits for answer grounding."""
    digits = "".join(character for character in value if character.isdigit())
    if len(digits) >= 7:
        return digits
    return None


def _record_id(value: object) -> JsonValue:
    """Return a record ID from a typed response model or mapping."""
    if isinstance(value, Mapping):
        item = value.get("id")
        return _coerce_json_value(item)
    return _coerce_json_value(getattr(value, "id", None))


_PROMPT_VARIATION_WRAPPERS = (
    "{prompt}",
    "Please help with this: {prompt}",
    "Quick CRM check: {prompt}",
    "In Follow Up Boss, {prompt}",
    "Could you handle this for me: {prompt}",
)


def _expand_prompt_families(base_prompts: tuple[str, ...]) -> tuple[str, ...]:
    """Expand seed prompts through deterministic phrasing families.

    Args:
        base_prompts: Seed prompts that preserve the canonical intent.

    Returns:
        Seed prompts multiplied across stable phrasing wrappers.
    """
    return tuple(
        wrapper.format(prompt=prompt)
        for wrapper in _PROMPT_VARIATION_WRAPPERS
        for prompt in base_prompts
    )


_READ_ONLY_SCENARIOS: tuple[BattleTestScenario, ...] = (
    BattleTestScenario(
        id="BT-READ-001",
        grade=BattleTestGrade.MUST_ROUTE,
        prompt_variants=_expand_prompt_families(
            (
                "What is my latest lead?",
                "Who was the newest lead I got?",
                "Show me the most recent lead assigned to me",
                "Pull up my newest person",
                "Anything new for me?",
                "Did I get any new leads?",
                "Who is the latest person assigned to me?",
                "Bring up the newest lead in my name",
                "Show the last lead that came to me",
                "What lead just landed in my account?",
                "Open my freshest lead",
                "Who is my newest assigned contact?",
                "What is the most recent person I should follow up with?",
                "Show the newest record owned by me",
                "Any fresh leads assigned to me today?",
                "Find my most recently created lead",
                "Who did I most recently receive?",
                "Pull my latest incoming prospect",
                "Show my newest FUB person",
                "What new person is waiting for me?",
            )
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
        prompt_variants=_expand_prompt_families(
            (
                "What am I late on?",
                "Show my overdue tasks",
                "Which follow-ups did I miss?",
                "What tasks are past due for me?",
                "Anything I should have done already?",
                "What follow-ups are overdue for me?",
                "Do I have any late to-dos?",
                "Show the tasks I missed",
                "What did I forget to complete?",
                "Which of my tasks are behind schedule?",
                "List my overdue follow-ups",
                "What should I have handled already?",
                "Any past-due reminders assigned to me?",
                "Show what is late under my name",
                "What tasks are overdue on my plate?",
                "Give me my missed follow-up list",
                "What FUB tasks did I let slip?",
                "Anything overdue that I own?",
                "Which assigned tasks are already late?",
                "Show my stale tasks",
            )
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
        prompt_variants=_expand_prompt_families(
            (
                "What do I need to do today?",
                "Show my tasks today",
                "What's on deck for me today?",
                "Any follow-ups due today?",
                "Give me today's to-do list",
                "What follow-ups are due for me today?",
                "Show today's tasks assigned to me",
                "What should I work on today?",
                "Any reminders for me today?",
                "List my due-today FUB tasks",
                "What is on my calendar of tasks today?",
                "Show the follow-ups I owe today",
                "Anything I need to complete before end of day?",
                "What tasks are assigned to me for today?",
                "Give me my daily follow-up list",
                "What is due now for me?",
                "Any current-day tasks in my queue?",
                "Show my action items due today",
                "What should I not miss today?",
                "Which incomplete tasks are due today under my name?",
            )
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
        grade=BattleTestGrade.MUST_ROUTE,
        prompt_variants=_expand_prompt_families(
            (
                "What do I have coming up?",
                "Show my next tasks",
                "What's due later this week?",
                "Any follow-ups after today?",
                "What should I prep for next?",
                "What follow-ups are coming soon?",
                "Show my upcoming tasks",
                "What is due after today?",
                "Anything on my plate later?",
                "What tasks should I plan for?",
                "Give me my future to-do list",
                "Which follow-ups are next for me?",
                "What should I get ready for this week?",
                "Show tasks that are not due yet",
                "Any incomplete tasks coming up?",
                "What reminders are scheduled ahead?",
                "What do I have after today in FUB?",
                "List upcoming follow-ups assigned to me",
                "What is next on my CRM task list?",
                "Show later tasks I should be aware of",
            )
        ),
        expected_mcp=ExpectedMcpRoute(
            allowed_tools=("followupboss_list_my_upcoming_tasks",),
            forbidden_tools=(),
        ),
        api_oracle=ApiOracleSpec(
            kind=BattleTestOracleKind.MY_UPCOMING_TASKS,
            description=(
                "Direct query for incomplete tasks due after today and assigned "
                "to authenticated user."
            ),
        ),
        response_assertions=("response.tasks[*].id == api_oracle.task_ids",),
    ),
    BattleTestScenario(
        id="BT-READ-005",
        grade=BattleTestGrade.MUST_EXPLAIN_UNSUPPORTED,
        prompt_variants=_expand_prompt_families(
            (
                "Show notes for lead 123",
                "What notes are on this person?",
                "Find all notes for this FUB lead",
                "Search notes by person ID",
                "Do they have any notes?",
                "Pull up the notes for this lead",
                "Can you search notes attached to person 123?",
                "Show every note on that contact",
                "Look through this person's notes",
                "Find notes for the buyer",
                "What note history does this lead have?",
                "Search all notes for that FUB person",
                "Do we have notes saved on this contact?",
                "Open the note thread for this lead",
                "Find lead notes by contact ID",
                "Show me notes related to this person record",
                "Can you list notes for lead ID 123?",
                "What has been noted on this person?",
                "Search the notes field for this lead",
                "Pull notes connected to this contact",
            )
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


_EXPANDED_READ_ONLY_SCENARIOS: tuple[BattleTestScenario, ...] = (
    BattleTestScenario(
        id="BT-READ-006",
        grade=BattleTestGrade.MUST_ROUTE,
        prompt_variants=_expand_prompt_families(
            (
                "Show my smart lists",
                "List the smart lists in FUB",
                "What saved lists are available?",
                "Pull up the available smart lists",
                "Show CRM smart lists",
                "What smart lists can I use?",
                "List my FUB saved people lists",
                "Show available lead lists",
                "What lists can I filter people by?",
                "Display smart list options",
            )
        ),
        expected_mcp=ExpectedMcpRoute(allowed_tools=("followupboss_list_smart_lists",)),
        api_oracle=ApiOracleSpec(
            kind=BattleTestOracleKind.SMART_LISTS,
            description="Direct smart-list query for available Follow Up Boss smart lists.",
        ),
        response_assertions=("response.smartlists[*].id == api_oracle.smart_list_ids",),
    ),
    BattleTestScenario(
        id="BT-READ-007",
        grade=BattleTestGrade.MUST_REQUIRE_ID,
        prompt_variants=_expand_prompt_families(
            (
                "Show people in smart list 1",
                "Pull smart list ID 1 people",
                "Search people from smart list 1",
                "List contacts in smart list 1",
                "Show the first people in saved list 1",
                "Open smart list 1 contacts",
                "Find leads in smart list 1",
                "Use smart list 1 for a people search",
                "Show buyers from smart list ID 1",
                "List records filtered by smart list 1",
            )
        ),
        expected_mcp=ExpectedMcpRoute(
            allowed_tools=("followupboss_search_people",),
            required_argument_keys=("smart_list_id",),
        ),
        api_oracle=ApiOracleSpec(
            kind=BattleTestOracleKind.PEOPLE_SEARCH,
            description="Direct people query filtered by the selected smart-list ID.",
        ),
        response_assertions=("response.people[*].id == api_oracle.person_ids",),
    ),
    BattleTestScenario(
        id="BT-READ-008",
        grade=BattleTestGrade.MUST_REQUIRE_ID,
        prompt_variants=_expand_prompt_families(
            (
                "Check whether alex@example.com is already in FUB",
                "Do we already have alex@example.com?",
                "Look for duplicate email alex@example.com",
                "Can I add alex@example.com or is it a duplicate?",
                "Check duplicate person by alex@example.com",
                "Has alex@example.com been seen before?",
                "Search duplicate record for alex@example.com",
                "Would alex@example.com create a duplicate?",
                "Verify if alex@example.com exists",
                "Duplicate check alex@example.com",
            )
        ),
        expected_mcp=ExpectedMcpRoute(
            allowed_tools=("followupboss_check_duplicate_person",),
            required_argument_keys=("email",),
        ),
        api_oracle=ApiOracleSpec(
            kind=BattleTestOracleKind.PERSON_DUPLICATE_CHECK,
            description="Direct duplicate-check endpoint for the same email or phone.",
        ),
        response_assertions=("response.found == api_oracle.found",),
    ),
    BattleTestScenario(
        id="BT-READ-009",
        grade=BattleTestGrade.MUST_ROUTE,
        prompt_variants=_expand_prompt_families(
            (
                "Show unclaimed leads",
                "Any unclaimed people available?",
                "What leads can I claim?",
                "Show pond lead offers",
                "List available unclaimed people",
                "Are there new leads to claim?",
                "Pull unclaimed person offers",
                "Show available lead claims",
                "List unclaimed FUB people",
                "What unclaimed contacts are waiting?",
            )
        ),
        expected_mcp=ExpectedMcpRoute(allowed_tools=("followupboss_list_unclaimed_people",)),
        api_oracle=ApiOracleSpec(
            kind=BattleTestOracleKind.UNCLAIMED_PEOPLE,
            description="Direct unclaimed-people query for available claim offers.",
        ),
        response_assertions=("response.people[*].id == api_oracle.person_ids",),
    ),
    BattleTestScenario(
        id="BT-READ-010",
        grade=BattleTestGrade.MUST_ROUTE,
        prompt_variants=_expand_prompt_families(
            (
                "Show appointments",
                "List my FUB appointments",
                "What appointments are in Follow Up Boss?",
                "Pull upcoming appointments",
                "Show calendar items from FUB",
                "List appointment records",
                "Any appointments in the CRM?",
                "Show the appointment list",
                "Pull appointment data",
                "Display FUB appointments",
            )
        ),
        expected_mcp=ExpectedMcpRoute(allowed_tools=("followupboss_list_appointments",)),
        api_oracle=ApiOracleSpec(
            kind=BattleTestOracleKind.APPOINTMENTS,
            description="Direct appointment query with matching safe filters.",
        ),
        response_assertions=("response.appointments[*].id == api_oracle.appointment_ids",),
    ),
    BattleTestScenario(
        id="BT-READ-011",
        grade=BattleTestGrade.MUST_ROUTE,
        prompt_variants=_expand_prompt_families(
            (
                "Show recent calls",
                "List call logs",
                "Pull FUB calls",
                "Any calls recorded?",
                "Show the call history list",
                "List recent phone call records",
                "Display calls from Follow Up Boss",
                "What calls are logged?",
                "Pull call records",
                "Show CRM call activity",
            )
        ),
        expected_mcp=ExpectedMcpRoute(allowed_tools=("followupboss_list_calls",)),
        api_oracle=ApiOracleSpec(
            kind=BattleTestOracleKind.CALLS,
            description="Direct calls query with matching safe filters.",
        ),
        response_assertions=("response.calls[*].id == api_oracle.call_ids",),
    ),
    BattleTestScenario(
        id="BT-READ-012",
        grade=BattleTestGrade.MUST_ROUTE,
        prompt_variants=_expand_prompt_families(
            (
                "Show text message logs",
                "List SMS records",
                "Pull recent text messages",
                "What text messages are logged?",
                "Show FUB text message history",
                "List recorded texts",
                "Display text message records",
                "Any SMS logs in FUB?",
                "Pull CRM text logs",
                "Show text communications",
            )
        ),
        expected_mcp=ExpectedMcpRoute(allowed_tools=("followupboss_list_text_messages",)),
        api_oracle=ApiOracleSpec(
            kind=BattleTestOracleKind.TEXT_MESSAGES,
            description="Direct text-message query with matching safe filters.",
        ),
        response_assertions=("response.textmessages[*].id == api_oracle.text_message_ids",),
    ),
    BattleTestScenario(
        id="BT-READ-013",
        grade=BattleTestGrade.MUST_ROUTE,
        prompt_variants=_expand_prompt_families(
            (
                "Show email templates",
                "List templates",
                "Pull FUB email templates",
                "What message templates are available?",
                "Display email template records",
                "List saved email templates",
                "Show available email templates",
                "Pull template list",
                "What templates can I use?",
                "Show CRM templates",
            )
        ),
        expected_mcp=ExpectedMcpRoute(allowed_tools=("followupboss_list_templates",)),
        api_oracle=ApiOracleSpec(
            kind=BattleTestOracleKind.TEMPLATES,
            description="Direct email-template query with matching safe filters.",
        ),
        response_assertions=("response.templates[*].id == api_oracle.template_ids",),
    ),
    BattleTestScenario(
        id="BT-READ-014",
        grade=BattleTestGrade.MUST_ROUTE,
        prompt_variants=_expand_prompt_families(
            (
                "Show text templates",
                "List SMS templates",
                "Pull text message templates",
                "What text templates are available?",
                "Display SMS template records",
                "List saved text templates",
                "Show available text message templates",
                "Pull text template list",
                "What SMS templates can I use?",
                "Show CRM text templates",
            )
        ),
        expected_mcp=ExpectedMcpRoute(allowed_tools=("followupboss_list_text_message_templates",)),
        api_oracle=ApiOracleSpec(
            kind=BattleTestOracleKind.TEXT_MESSAGE_TEMPLATES,
            description="Direct text-template query with matching safe filters.",
        ),
        response_assertions=("response.textmessagetemplates[*].id == api_oracle.template_ids",),
    ),
    BattleTestScenario(
        id="BT-READ-015",
        grade=BattleTestGrade.MUST_REQUIRE_ID,
        prompt_variants=_expand_prompt_families(
            (
                "Fetch note ID 1",
                "Open note 1",
                "Get FUB note ID 1",
                "Show note record 1",
                "Pull note 1 by ID",
                "Retrieve note ID 1",
                "Display explicit note 1",
                "Open the note with ID 1",
                "Show FUB note 1",
                "Get the note whose ID is 1",
            )
        ),
        expected_mcp=ExpectedMcpRoute(
            allowed_tools=("followupboss_get_note",),
            required_argument_keys=("note_id",),
        ),
        api_oracle=ApiOracleSpec(
            kind=BattleTestOracleKind.EXPLICIT_NOTE,
            description="Direct note lookup for the same explicit note ID.",
        ),
        response_assertions=("response.id == api_oracle.note_id",),
    ),
    BattleTestScenario(
        id="BT-READ-016",
        grade=BattleTestGrade.MUST_REQUIRE_ID,
        prompt_variants=_expand_prompt_families(
            (
                "Show all communication history for person 1",
                "Pull calls texts emails and events for contact ID 1",
                "What activity do we have for lead 1?",
                "List the interaction timeline for person_id 1",
                "Show calls and text messages for Follow Up Boss person 1",
                "Get activity records tied to contact 1",
                "Show what we have sent to person 1",
                "Pull the communication log for lead ID 1",
                "Review appointments calls and events for person 1",
                "Summarize the FUB activity history for contact ID 1",
            )
        ),
        expected_mcp=ExpectedMcpRoute(
            allowed_tools=("followupboss_list_person_activity",),
            forbidden_tools=(
                "followupboss_list_calls",
                "followupboss_list_text_messages",
                "followupboss_list_email_events",
                "followupboss_search_events",
                "followupboss_list_appointments",
            ),
            required_argument_keys=("person_id",),
        ),
        api_oracle=ApiOracleSpec(
            kind=BattleTestOracleKind.PERSON_ACTIVITY,
            description=(
                "Direct person-scoped activity queries for calls, texts, email events, "
                "events, and appointments."
            ),
        ),
        response_assertions=(
            "response.person.id == api_oracle.resolved_person_id",
            "response.calls[*].id == api_oracle.call_ids",
            "response.textmessages[*].id == api_oracle.text_message_ids",
            "response.emEvents[*].id == api_oracle.email_event_ids",
            "response.events[*].id == api_oracle.event_ids",
            "response.appointments[*].id == api_oracle.appointment_ids",
        ),
    ),
    BattleTestScenario(
        id="BT-READ-017",
        grade=BattleTestGrade.MUST_CLARIFY,
        prompt_variants=_expand_prompt_families(
            (
                "Show this lead's communication history",
                "Pull activity for that contact",
                "What messages has this person received?",
                "Show the latest lead's calls and texts",
                "Give me the contact history for the Zillow person",
                "List all recent conversations for this lead",
                "What did we send that buyer?",
                "Show activity for the contact we discussed",
                "Pull communication history for my lead",
                "Review the timeline for this person",
            )
        ),
        expected_mcp=ExpectedMcpRoute(
            allowed_tools=(),
            forbidden_tools=(
                "followupboss_list_person_activity",
                "followupboss_list_calls",
                "followupboss_list_text_messages",
                "followupboss_list_email_events",
                "followupboss_search_events",
                "followupboss_list_appointments",
            ),
        ),
        api_oracle=ApiOracleSpec(
            kind=BattleTestOracleKind.ROUTE_ONLY_PENDING,
            description="Require clarification before returning broad communication history.",
        ),
        response_assertions=("clarified is true", "selected_tool is None"),
    ),
    BattleTestScenario(
        id="BT-READ-018",
        grade=BattleTestGrade.MUST_REQUIRE_ID,
        prompt_variants=_expand_prompt_families(
            (
                "Show Scott Willey's zero communication leads.",
                "Scott Willey has 323 leads with zero communication; list them.",
                "Pull Scott Willey's no-communication leads using the uncontacted helper.",
                "Get me Scott Willey's leads that have no last communication.",
                "Which leads assigned to Scott Willey have no communication recorded?",
                "Show leads I haven't communicated with for Scott Willey.",
                "List never-contacted people assigned to Scott Willey.",
                "Use direct filtering to show Scott Willey's uncontacted leads.",
                "Count Scott Willey's no-communication leads, then show them.",
                "Show those zero communication leads for Scott Willey.",
            )
        ),
        expected_mcp=ExpectedMcpRoute(
            allowed_tools=("followupboss_list_uncontacted_leads",),
            forbidden_tools=(
                "followupboss_search_people_in_smart_list",
                "followupboss_list_smart_lists",
                "followupboss_search_people",
                "followupboss_list_person_activity",
                "followupboss_get_latest_lead",
            ),
            required_argument_keys=("assigned_user_name",),
            required_argument_values={"assigned_user_name": "Scott Willey"},
        ),
        api_oracle=ApiOracleSpec(
            kind=BattleTestOracleKind.MY_UNCONTACTED_LEADS,
            description=(
                "Direct people search filtered to empty lastCommunication and resolved Scott "
                "Willey owner scope; no saved-list lookup or per-person activity inference."
            ),
        ),
        response_assertions=(
            "request.lastCommunication is empty",
            "request.assigned_user_name == Scott Willey",
            "response.people[*].id == api_oracle.person_ids",
        ),
    ),
    BattleTestScenario(
        id="BT-READ-019",
        grade=BattleTestGrade.MUST_ROUTE,
        prompt_variants=_expand_prompt_families(
            (
                "Which leads should I check for uncontacted ones? All my leads.",
                "Show all my uncontacted leads.",
                "List my never-contacted leads.",
                "Who are my leads with no communication?",
                "Show my zero communication leads.",
                "Get my leads with no last communication.",
                "Which of my leads have not been contacted?",
                "Pull my leads where last communication is empty.",
                "Count my no-communication leads, then show them.",
                "Show those uncontacted leads from all my leads.",
            )
        ),
        expected_mcp=ExpectedMcpRoute(
            allowed_tools=("followupboss_list_uncontacted_leads",),
            forbidden_tools=(
                "followupboss_search_people_in_smart_list",
                "followupboss_list_smart_lists",
                "followupboss_search_people",
                "followupboss_list_person_activity",
            ),
        ),
        api_oracle=ApiOracleSpec(
            kind=BattleTestOracleKind.MY_UNCONTACTED_LEADS,
            description=(
                "Direct authenticated-user people search filtered to empty lastCommunication; "
                "no saved-list lookup."
            ),
        ),
        response_assertions=(
            "request.lastCommunication is empty",
            "request.assigned_user_id == authenticated_user.id",
            "response.people[*].id == api_oracle.person_ids",
        ),
    ),
    BattleTestScenario(
        id="BT-READ-020",
        grade=BattleTestGrade.MUST_ROUTE,
        prompt_variants=_expand_prompt_families(
            (
                "Show my leads that need contact.",
                "Who needs contact from all my leads?",
                "Find the Needs Contact leads for me, not a smart list.",
                "Pull my needs-contact leads using filters.",
                "Which of my leads are in a needs contact state?",
                "Show my leads needing contact because they are uncontacted.",
                "List all my leads that have zero communication and need contact.",
                "Get the people I need to contact because last communication is empty.",
                "Show the Needs Contact results from my people search.",
                "Use no-last-communication filtering for my needs-contact leads.",
            )
        ),
        expected_mcp=ExpectedMcpRoute(
            allowed_tools=("followupboss_list_uncontacted_leads",),
            forbidden_tools=(
                "followupboss_search_people_in_smart_list",
                "followupboss_list_smart_lists",
                "followupboss_search_people",
                "followupboss_list_person_activity",
            ),
        ),
        api_oracle=ApiOracleSpec(
            kind=BattleTestOracleKind.MY_UNCONTACTED_LEADS,
            description=(
                "Direct authenticated-user empty-lastCommunication search for needs-contact "
                "wording that does not explicitly ask for a saved smart list."
            ),
        ),
        response_assertions=(
            "request.lastCommunication is empty",
            "request.smart_list_id is None",
            "response.people[*].id == api_oracle.person_ids",
        ),
    ),
)


_SMART_LIST_GROUNDING_SCENARIOS: tuple[BattleTestScenario, ...] = (
    BattleTestScenario(
        id="BT-SMARTLIST-001",
        grade=BattleTestGrade.MUST_ROUTE,
        prompt_variants=(
            "Show me the Eligible For Transfer smart-list metadata only.",
            "List the saved smart list named Eligible For Transfer, not its people.",
            "Look up available smart lists so I can confirm Eligible For Transfer exists.",
            "Show smart-list names and IDs for Eligible For Transfer only.",
            "Pull smart-list metadata for Eligible For Transfer without searching people.",
        ),
        expected_mcp=ExpectedMcpRoute(allowed_tools=("followupboss_list_smart_lists",)),
        api_oracle=ApiOracleSpec(
            kind=BattleTestOracleKind.SMART_LISTS,
            description="Direct smart-list query used to resolve Eligible For Transfer.",
        ),
        response_assertions=("response.smartlists contains Eligible For Transfer",),
    ),
    BattleTestScenario(
        id="BT-SMARTLIST-002",
        grade=BattleTestGrade.MUST_REQUIRE_ID,
        prompt_variants=(
            "What Zillow leads do I need to follow up with in Eligible For Transfer?",
            "Show only my Zillow follow-up leads from the Eligible For Transfer smart list.",
            "Which Eligible For Transfer Zillow leads do I need to follow up with?",
            "Pull Zillow leads I need to follow up with, but only from Eligible For Transfer.",
            "Use the Eligible For Transfer smart list for Zillow leads I should call.",
            "How many Zillow leads are in my Eligible For Transfer follow-up queue?",
            "Give me my people in Eligible For Transfer that came from Zillow.",
            "List my Eligible For Transfer leads from Zillow only.",
            "Who should I work from Eligible For Transfer for Zillow?",
            "Show Zillow source people scoped to my Eligible For Transfer queue.",
            "In the Eligible For Transfer smart list, which Zillow leads need my attention?",
            "Pull the Eligible For Transfer list and only show Zillow leads assigned to me.",
            "My Eligible For Transfer Zillow follow-up queue please.",
            "Find my Zillow leads inside Eligible For Transfer, not outside it.",
            "Show me my Zillow contacts from the Eligible For Transfer list.",
            "Which Zillow contacts in Eligible For Transfer do I need to call?",
            "Use Eligible For Transfer as the boundary for my Zillow follow-ups.",
            "From Eligible For Transfer, show my leads where source is Zillow.",
            "For my Zillow follow-up block, use Eligible For Transfer only.",
            "I need the Zillow leads within Eligible For Transfer.",
            "What zillow leads do i need to follow up with in Eligible For Transfer?",
            "What Zillow people do I need to follow up with from Eligible For Transfer?",
            "Which Zillow leads in Eligible For Transfer are mine to call?",
            "Show the Zillow leads assigned to me in Eligible For Transfer.",
            "Give me my Zillow call list from Eligible For Transfer.",
            "Use Eligible For Transfer and tell me which Zillow leads I should call.",
            "For me only, pull Zillow leads from Eligible For Transfer.",
            "Which of my Eligible For Transfer people came from Zillow?",
            "Show my transfer-eligible Zillow contacts.",
            "Pull Zillow contacts in Eligible For Transfer for my follow-up block.",
            "How many Zillow leads do I personally have in Eligible For Transfer?",
            "List the Zillow leads I own in Eligible For Transfer.",
            "Find my Zillow source contacts inside the transfer list.",
            "Eligible For Transfer is the boundary; show my Zillow leads.",
            "Only show Zillow leads assigned to me from Eligible For Transfer.",
            "Who from Zillow should I follow up with in Eligible For Transfer?",
            "Which Eligible For Transfer contacts from Zillow are assigned to me?",
            "Show my Zillow follow-up queue from the transfer list.",
            "Count my Zillow leads in Eligible For Transfer before listing them.",
            "I need to call Zillow leads from Eligible For Transfer, but only mine.",
            "What Zillow leads do I have in the Eligible For Transfer list?",
            "Show Zillow leads from Eligible For Transfer using my owner scope.",
            "For my calls today, pull Zillow leads from Eligible For Transfer.",
            "Which Zillow transfers are assigned to me?",
            "Pull my Zillow people from the eligible transfer smart list.",
        ),
        expected_mcp=ExpectedMcpRoute(
            allowed_tools=("followupboss_search_people_in_smart_list",),
            forbidden_tools=(
                "followupboss_get_latest_lead",
                "followupboss_search_people",
                "followupboss_list_smart_lists",
            ),
            required_argument_keys=("smart_list_name",),
        ),
        api_oracle=ApiOracleSpec(
            kind=BattleTestOracleKind.NAMED_SMART_LIST_PEOPLE,
            description=(
                "Resolve Eligible For Transfer by exact smart-list name and verify the "
                "people response and visible answer are a subset of that list and owner."
            ),
            smart_list_name="Eligible For Transfer",
            answer_must_be_grounded=True,
            requires_authenticated_owner_scope=True,
        ),
        response_assertions=(
            "request.smart_list_name == api_oracle.smart_list_name",
            "request.mine is not false for I/me/my follow-up wording",
            "response.smartlist.id == api_oracle.smart_list_id",
            "response.people[*].assignedUserId == authenticated_user.id",
            "response.people[*].id == api_oracle.person_ids",
            "assistant_answer contains no off-list names or phones",
        ),
    ),
    BattleTestScenario(
        id="BT-SMARTLIST-003",
        grade=BattleTestGrade.MUST_CLARIFY,
        prompt_variants=(
            "What Zillow leads do I need to follow up with?",
            "Show Zillow leads I should work next.",
            "Which Zillow leads need follow-up?",
            "Pull my Zillow follow-up list.",
            "Any Zillow leads I should call?",
        ),
        expected_mcp=ExpectedMcpRoute(
            forbidden_tools=(
                "followupboss_search_people_in_smart_list",
                "followupboss_search_people",
                "followupboss_get_latest_lead",
            )
        ),
        api_oracle=ApiOracleSpec(
            kind=BattleTestOracleKind.ROUTE_ONLY_PENDING,
            description=(
                "Without prior context or an explicit smart-list name, Zillow follow-up "
                "requests must clarify instead of returning a broad people search."
            ),
        ),
        response_assertions=("selected_tool is None", "clarified is true"),
    ),
    BattleTestScenario(
        id="BT-SMARTLIST-004",
        grade=BattleTestGrade.MUST_REQUIRE_ID,
        prompt_variants=(
            "Show everyone's people in eligible   for transfer from Zillow.",
            "Pull all users' Zillow leads in eligible for transfer.",
            "Search ELIGIBLE FOR TRANSFER for all account Zillow leads.",
            "From Eligible    For    Transfer, show team-wide Zillow leads.",
            "List all account-wide Zillow contacts in the eligible for transfer smart list.",
            "Search the Eligible For Transfer smart list for everyone with Zillow leads.",
            "Search only the eligible for transfer smart list for account-wide Zillow follow-ups.",
            "Can you count everyone's Zillow leads in ELIGIBLE FOR TRANSFER?",
            "Find every account Zillow person inside eligible for transfer.",
            "Show me Eligible For Transfer members where the source is Zillow for everyone.",
        ),
        expected_mcp=ExpectedMcpRoute(
            allowed_tools=("followupboss_search_people_in_smart_list",),
            forbidden_tools=(
                "followupboss_get_latest_lead",
                "followupboss_search_people",
                "followupboss_list_smart_lists",
            ),
            required_argument_keys=("smart_list_name", "mine"),
            required_argument_values={"mine": False},
        ),
        api_oracle=ApiOracleSpec(
            kind=BattleTestOracleKind.NAMED_SMART_LIST_PEOPLE,
            description=(
                "Resolve Eligible For Transfer despite casing and whitespace variation and "
                "verify the scoped people response cannot leak off-list identifiers."
            ),
            smart_list_name="Eligible For Transfer",
            answer_must_be_grounded=True,
        ),
        response_assertions=(
            "request.smart_list_name normalizes to api_oracle.smart_list_name",
            "response.smartlist.id == api_oracle.smart_list_id",
            "assistant_answer contains no off-list names or phones",
        ),
    ),
    BattleTestScenario(
        id="BT-SMARTLIST-005",
        grade=BattleTestGrade.MUST_REQUIRE_ID,
        prompt_variants=(
            "Show my people in the Needs Contact smart list.",
            "Search the Needs Contact smart list for my leads.",
            "Pull people from the saved list named Needs Contact.",
            "Use the Needs Contact smart list, not the contacted filter.",
            "List my leads inside the Needs Contact saved list.",
        ),
        expected_mcp=ExpectedMcpRoute(
            allowed_tools=("followupboss_search_people_in_smart_list",),
            forbidden_tools=(
                "followupboss_list_uncontacted_leads",
                "followupboss_search_people",
                "followupboss_list_smart_lists",
            ),
            required_argument_keys=("smart_list_name",),
            required_argument_values={"smart_list_name": "Needs Contact"},
        ),
        api_oracle=ApiOracleSpec(
            kind=BattleTestOracleKind.NAMED_SMART_LIST_PEOPLE,
            description=(
                "Explicit saved-list wording should still resolve and search the named "
                "Needs Contact smart list."
            ),
            smart_list_name="Needs Contact",
            answer_must_be_grounded=True,
        ),
        response_assertions=(
            "request.smart_list_name == Needs Contact",
            "response.smartlist.id == api_oracle.smart_list_id",
            "response.people[*].id == api_oracle.person_ids",
        ),
    ),
)


_TEXT_LOGGING_CONTEXT_SCENARIOS: tuple[BattleTestScenario, ...] = (
    BattleTestScenario(
        id="BT-TEXTLOG-001",
        grade=BattleTestGrade.MUST_REQUIRE_ID,
        prompt_variants=(
            (
                "Log this as a text from 555-0001: Hey Lauren, checking in about the "
                "Zillow transfer."
            ),
            "Log a text for them from 555-0001 saying: Hey Lauren, just checking in.",
            (
                "Save this SMS on that lead from 555-0001: Lauren, I wanted to follow "
                "up before the transfer window closes."
            ),
        ),
        expected_mcp=ExpectedMcpRoute(
            allowed_tools=("followupboss_add_note",),
            forbidden_tools=(
                "followupboss_create_text_message",
                "followupboss_search_people",
                "followupboss_list_text_messages",
                "followupboss_search_people_in_smart_list",
            ),
            required_argument_keys=("person_id", "body"),
            required_argument_values={
                "person_id": 917,
            },
        ),
        api_oracle=ApiOracleSpec(
            kind=BattleTestOracleKind.ROUTE_ONLY_PENDING,
            description=(
                "Mutation-aware route-only check: an outbound text-log follow-up must use "
                "the safe note path with the one previously resolved person instead of "
                "writing through Follow Up Boss's registered-system text endpoint."
            ),
        ),
        response_assertions=(
            "request.person_id == prior_context.people[0].id",
            "request.body contains the text message transcript",
            "assistant must route outbound text transcripts to followupboss_add_note",
            "assistant must not ask who the text is with when one prior person is resolved",
        ),
        cleanup="mutation-route-only",
    ),
)


def _base_scenario(scenario_id: str) -> BattleTestScenario:
    """Return one base scenario for corpus construction."""
    return {
        scenario.id: scenario
        for scenario in (
            expanded_read_only_battle_test_scenarios()
            + smart_list_grounding_battle_test_scenarios()
            + text_logging_context_battle_test_scenarios()
        )
    }[scenario_id]


def _conversation_turn(
    turn_id: str,
    scenario_id: str,
    prompt: str,
) -> BattleTestConversationTurn:
    """Build a chained turn from an existing read-only scenario contract."""
    scenario = _base_scenario(scenario_id)
    return BattleTestConversationTurn(
        id=turn_id,
        prompt=prompt,
        grade=scenario.grade,
        expected_mcp=scenario.expected_mcp,
        api_oracle=scenario.api_oracle,
        response_assertions=scenario.response_assertions,
        cleanup=scenario.cleanup,
    )


_CHAIN_STYLE_PREFIXES = (
    "",
    "Please keep this in FUB: ",
    "Quick CRM workflow: ",
    "Before I start calls: ",
    "For my follow-up block: ",
)

_CHAIN_BLUEPRINTS: tuple[
    tuple[
        BattleTestConversationKind,
        str,
        tuple[tuple[str, str], ...],
    ],
    ...,
] = (
    (
        BattleTestConversationKind.MULTI_TURN,
        "",
        (
            ("BT-READ-001", "Show my latest lead"),
            ("BT-READ-003", "Now show what I need to do today"),
        ),
    ),
    (
        BattleTestConversationKind.MULTI_TURN,
        "",
        (
            ("BT-READ-002", "What am I late on?"),
            ("BT-READ-004", "What should I prep for after today?"),
        ),
    ),
    (
        BattleTestConversationKind.MULTI_TURN,
        "",
        (
            ("BT-READ-003", "Show today's work"),
            ("BT-READ-002", "Now show anything overdue"),
            ("BT-READ-004", "Then show what is coming up next"),
        ),
    ),
    (
        BattleTestConversationKind.MULTI_TURN,
        "",
        (
            ("BT-READ-001", "Pull my newest lead"),
            ("BT-READ-005", "Can you show notes for that lead?"),
        ),
    ),
    (
        BattleTestConversationKind.MULTI_TURN,
        "",
        (
            ("BT-READ-004", "What do I have coming up?"),
            ("BT-READ-003", "What about today?"),
        ),
    ),
    (
        BattleTestConversationKind.MULTI_ASK,
        "Show my latest lead and what I need to do today.",
        (
            ("BT-READ-001", "Show my latest lead and what I need to do today."),
            ("BT-READ-003", "Show my latest lead and what I need to do today."),
        ),
    ),
    (
        BattleTestConversationKind.MULTI_ASK,
        "What am I late on, and what is coming up after today?",
        (
            ("BT-READ-002", "What am I late on, and what is coming up after today?"),
            ("BT-READ-004", "What am I late on, and what is coming up after today?"),
        ),
    ),
    (
        BattleTestConversationKind.MULTI_ASK,
        "Show today's tasks, upcoming tasks, and overdue tasks for me.",
        (
            ("BT-READ-003", "Show today's tasks, upcoming tasks, and overdue tasks for me."),
            ("BT-READ-004", "Show today's tasks, upcoming tasks, and overdue tasks for me."),
            ("BT-READ-002", "Show today's tasks, upcoming tasks, and overdue tasks for me."),
        ),
    ),
    (
        BattleTestConversationKind.MULTI_ASK,
        "Pull my newest lead and tell me whether you can search that lead's notes.",
        (
            (
                "BT-READ-001",
                "Pull my newest lead and tell me whether you can search that lead's notes.",
            ),
            (
                "BT-READ-005",
                "Pull my newest lead and tell me whether you can search that lead's notes.",
            ),
        ),
    ),
    (
        BattleTestConversationKind.MULTI_ASK,
        "Check my CRM queue: overdue, today, and later follow-ups.",
        (
            ("BT-READ-002", "Check my CRM queue: overdue, today, and later follow-ups."),
            ("BT-READ-003", "Check my CRM queue: overdue, today, and later follow-ups."),
            ("BT-READ-004", "Check my CRM queue: overdue, today, and later follow-ups."),
        ),
    ),
)


def _build_read_only_conversations() -> tuple[BattleTestConversationScenario, ...]:
    """Build deterministic multi-turn and multi-ask read-only conversations."""
    conversations: list[BattleTestConversationScenario] = []
    sequence = 1
    for style_prefix in _CHAIN_STYLE_PREFIXES:
        for kind, multi_ask_prompt, turns in _CHAIN_BLUEPRINTS:
            prompt = f"{style_prefix}{multi_ask_prompt}" if multi_ask_prompt else None
            turn_models = tuple(
                _conversation_turn(
                    f"T{turn_index:02d}",
                    scenario_id,
                    f"{style_prefix}{turn_prompt}",
                )
                for turn_index, (scenario_id, turn_prompt) in enumerate(turns, start=1)
            )
            conversations.append(
                BattleTestConversationScenario(
                    id=f"BT-CHAIN-{sequence:03d}",
                    kind=kind,
                    prompt=prompt,
                    turns=turn_models,
                    description="Read-only chained prompt routing coverage.",
                )
            )
            sequence += 1
    return tuple(conversations)


_READ_ONLY_CONVERSATIONS = _build_read_only_conversations()


_EXPANDED_CHAIN_BLUEPRINTS: tuple[
    tuple[
        BattleTestConversationKind,
        str,
        tuple[tuple[str, str], ...],
    ],
    ...,
] = (
    (
        BattleTestConversationKind.MULTI_TURN,
        "",
        (
            ("BT-READ-006", "Show my smart lists"),
            ("BT-READ-007", "Now show people in smart list 1"),
        ),
    ),
    (
        BattleTestConversationKind.MULTI_TURN,
        "",
        (
            ("BT-READ-010", "Show appointments"),
            ("BT-READ-011", "Then show recent calls"),
            ("BT-READ-012", "Then show text message logs"),
        ),
    ),
    (
        BattleTestConversationKind.MULTI_ASK,
        "Check duplicate email alex@example.com and show unclaimed leads.",
        (
            (
                "BT-READ-008",
                "Check duplicate email alex@example.com and show unclaimed leads.",
            ),
            (
                "BT-READ-009",
                "Check duplicate email alex@example.com and show unclaimed leads.",
            ),
        ),
    ),
    (
        BattleTestConversationKind.MULTI_ASK,
        "Show appointments, recent calls, and text message logs.",
        (
            ("BT-READ-010", "Show appointments, recent calls, and text message logs."),
            ("BT-READ-011", "Show appointments, recent calls, and text message logs."),
            ("BT-READ-012", "Show appointments, recent calls, and text message logs."),
        ),
    ),
    (
        BattleTestConversationKind.MULTI_ASK,
        "List email templates and text templates.",
        (
            ("BT-READ-013", "List email templates and text templates."),
            ("BT-READ-014", "List email templates and text templates."),
        ),
    ),
    (
        BattleTestConversationKind.MULTI_TURN,
        "",
        (
            (
                "BT-READ-018",
                "How many no-communication leads are assigned to Scott Willey?",
            ),
            (
                "BT-READ-018",
                "Now show those leads.",
            ),
        ),
    ),
    (
        BattleTestConversationKind.MULTI_TURN,
        "",
        (
            (
                "BT-READ-019",
                "How many of my leads have zero communication?",
            ),
            (
                "BT-READ-019",
                "Show those leads.",
            ),
        ),
    ),
    (
        BattleTestConversationKind.MULTI_TURN,
        "",
        (
            (
                "BT-READ-006",
                "List my smart lists so I know what saved views exist.",
            ),
            (
                "BT-READ-019",
                "Now show my uncontacted leads from all my leads.",
            ),
        ),
    ),
    (
        BattleTestConversationKind.MULTI_ASK,
        "List smart lists and show my uncontacted leads.",
        (
            (
                "BT-READ-006",
                "List smart lists and show my uncontacted leads.",
            ),
            (
                "BT-READ-019",
                "List smart lists and show my uncontacted leads.",
            ),
        ),
    ),
)


def _build_expanded_conversations() -> tuple[BattleTestConversationScenario, ...]:
    """Build deterministic expanded chained read-only conversations."""
    conversations: list[BattleTestConversationScenario] = []
    sequence = 1
    for style_prefix in _CHAIN_STYLE_PREFIXES:
        for kind, multi_ask_prompt, turns in _EXPANDED_CHAIN_BLUEPRINTS:
            prompt = f"{style_prefix}{multi_ask_prompt}" if multi_ask_prompt else None
            turn_models = tuple(
                _conversation_turn(
                    f"T{turn_index:02d}",
                    scenario_id,
                    f"{style_prefix}{turn_prompt}",
                )
                for turn_index, (scenario_id, turn_prompt) in enumerate(turns, start=1)
            )
            conversations.append(
                BattleTestConversationScenario(
                    id=f"BT-CHAIN-X{sequence:03d}",
                    kind=kind,
                    prompt=prompt,
                    turns=turn_models,
                    description="Expanded read-only chained prompt routing coverage.",
                )
            )
            sequence += 1
    return tuple(conversations)


_EXPANDED_CONVERSATIONS = _build_expanded_conversations()


_SMART_LIST_GROUNDING_BLUEPRINTS: tuple[
    tuple[
        BattleTestConversationKind,
        str | None,
        tuple[tuple[str, str], ...],
    ],
    ...,
] = (
    (
        BattleTestConversationKind.MULTI_ASK,
        (
            "Show saved smart-list metadata first, then show my Zillow leads in "
            "Eligible For Transfer."
        ),
        (
            (
                "BT-SMARTLIST-001",
                (
                    "Show saved smart-list metadata first, then show my Zillow leads in "
                    "Eligible For Transfer."
                ),
            ),
            (
                "BT-SMARTLIST-002",
                (
                    "Show saved smart-list metadata first, then show my Zillow leads in "
                    "Eligible For Transfer."
                ),
            ),
        ),
    ),
    (
        BattleTestConversationKind.MULTI_TURN,
        None,
        (
            (
                "BT-SMARTLIST-001",
                "Show me only metadata for the Eligible For Transfer smart list.",
            ),
            (
                "BT-SMARTLIST-002",
                "What Zillow leads do I need to follow up with?",
            ),
        ),
    ),
    (
        BattleTestConversationKind.MULTI_TURN,
        None,
        (
            (
                "BT-SMARTLIST-003",
                "What Zillow leads do I need to follow up with?",
            ),
        ),
    ),
    (
        BattleTestConversationKind.MULTI_TURN,
        None,
        (
            (
                "BT-SMARTLIST-001",
                "Pull only Eligible For Transfer smart-list metadata before my Zillow calls.",
            ),
            (
                "BT-SMARTLIST-002",
                "Now show my Zillow leads from that list.",
            ),
        ),
    ),
    (
        BattleTestConversationKind.MULTI_TURN,
        None,
        (
            (
                "BT-SMARTLIST-001",
                "Confirm Eligible For Transfer exists; use it as my Zillow follow-up list.",
            ),
            (
                "BT-SMARTLIST-002",
                "What zillow leads do i need to follow up with",
            ),
        ),
    ),
    (
        BattleTestConversationKind.MULTI_TURN,
        None,
        (
            (
                "BT-SMARTLIST-001",
                "List only metadata for the saved smart list named Eligible For Transfer.",
            ),
            (
                "BT-SMARTLIST-002",
                "Which Zillow leads do I need to call?",
            ),
        ),
    ),
    (
        BattleTestConversationKind.MULTI_TURN,
        None,
        (
            (
                "BT-SMARTLIST-001",
                "Show only the smart-list metadata for Eligible For Transfer.",
            ),
            (
                "BT-SMARTLIST-002",
                "Show the Zillow follow-up queue for me.",
            ),
        ),
    ),
    (
        BattleTestConversationKind.MULTI_TURN,
        None,
        (
            (
                "BT-SMARTLIST-001",
                "Pull only smart-list metadata for Eligible For Transfer before my next ask.",
            ),
            (
                "BT-SMARTLIST-002",
                "Give me the Zillow leads I should follow up with.",
            ),
        ),
    ),
    (
        BattleTestConversationKind.MULTI_TURN,
        None,
        (
            (
                "BT-SMARTLIST-001",
                "List the Eligible For Transfer smart-list metadata only.",
            ),
            (
                "BT-SMARTLIST-002",
                "How many Zillow leads do I have to work?",
            ),
        ),
    ),
    (
        BattleTestConversationKind.MULTI_ASK,
        (
            "Use Eligible For Transfer as my Zillow follow-up boundary, then tell me "
            "what Zillow leads I need to call."
        ),
        (
            (
                "BT-SMARTLIST-001",
                (
                    "Use Eligible For Transfer as my Zillow follow-up boundary, then tell me "
                    "what Zillow leads I need to call."
                ),
            ),
            (
                "BT-SMARTLIST-002",
                (
                    "Use Eligible For Transfer as my Zillow follow-up boundary, then tell me "
                    "what Zillow leads I need to call."
                ),
            ),
        ),
    ),
)


def _build_smart_list_grounding_conversations() -> tuple[BattleTestConversationScenario, ...]:
    """Build targeted named-smart-list grounding conversations."""
    conversations: list[BattleTestConversationScenario] = []
    for index, (kind, prompt, turns) in enumerate(_SMART_LIST_GROUNDING_BLUEPRINTS, start=1):
        conversations.append(
            BattleTestConversationScenario(
                id=f"BT-SMARTLIST-CHAIN-{index:03d}",
                kind=kind,
                prompt=prompt,
                turns=tuple(
                    _conversation_turn(f"T{turn_index:02d}", scenario_id, turn_prompt)
                    for turn_index, (scenario_id, turn_prompt) in enumerate(turns, start=1)
                ),
                description="Named smart-list grounding regression coverage.",
            )
        )
    return tuple(conversations)


_SMART_LIST_GROUNDING_CONVERSATIONS = _build_smart_list_grounding_conversations()


_TEXT_LOGGING_CONTEXT_BLUEPRINTS: tuple[
    tuple[
        BattleTestConversationKind,
        str | None,
        tuple[tuple[str, str], ...],
    ],
    ...,
] = (
    (
        BattleTestConversationKind.MULTI_TURN,
        None,
        (
            (
                "BT-SMARTLIST-002",
                "Which Zillow leads do I need to follow up with in Eligible For Transfer?",
            ),
            (
                "BT-TEXTLOG-001",
                (
                    "Log this as a text from 555-0001: Hey Lauren, checking in about the "
                    "Zillow transfer."
                ),
            ),
        ),
    ),
)


def _build_text_logging_context_conversations() -> tuple[BattleTestConversationScenario, ...]:
    """Build mutation-aware text logging context conversations."""
    conversations: list[BattleTestConversationScenario] = []
    for index, (kind, prompt, turns) in enumerate(_TEXT_LOGGING_CONTEXT_BLUEPRINTS, start=1):
        conversations.append(
            BattleTestConversationScenario(
                id=f"BT-TEXTLOG-CHAIN-{index:03d}",
                kind=kind,
                prompt=prompt,
                turns=tuple(
                    _conversation_turn(f"T{turn_index:02d}", scenario_id, turn_prompt)
                    for turn_index, (scenario_id, turn_prompt) in enumerate(turns, start=1)
                ),
                description="Text logging sticky-recipient context regression coverage.",
            )
        )
    return tuple(conversations)


_TEXT_LOGGING_CONTEXT_CONVERSATIONS = _build_text_logging_context_conversations()
