"""Tests for AI-backed MCP battle-test selectors."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import cast

import httpx
import pytest

from followupboss_mcp.battle_test_ai import (
    AnthropicBattleTestModelSelector,
    BattleTestAiToolSpec,
    BattleTestModelDecision,
    BattleTestModelSelector,
    OpenAiBattleTestModelSelector,
    _json_value,
    battle_test_ai_selectors_from_env,
    capture_ai_selected_transcript,
    load_env_file,
    read_only_battle_test_ai_tool_specs,
    run_ai_model_profile_battle_tests,
)
from followupboss_mcp.battle_tests import (
    BattleTestModelProfile,
    BattleTestModelProvider,
    BattleTestScenario,
    BattleTestTranscript,
    ReadOnlyBattleTestOracle,
    battle_test_model_profile_by_id,
    mcp_tool_result_to_json,
    scenario_by_id,
)
from followupboss_mcp.models.common import JsonValue
from followupboss_mcp.models.identity import IdentityResponse
from followupboss_mcp.models.people import PeopleSearchRequest, PersonRecord
from followupboss_mcp.models.tasks import TaskListRequest, TaskRecord
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


@dataclass
class StubBattleTestServices:
    """Read-only battle-test service bundle test double."""

    identity: StubIdentityService = field(default_factory=StubIdentityService)
    people: StubPeopleService = field(default_factory=StubPeopleService)
    tasks: StubTasksService = field(default_factory=StubTasksService)


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

    overdue_fields = overdue_schema["fields"]
    today_fields = today_schema["fields"]

    assert overdue_fields == today_fields
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
    assert "reasoning" not in requests[0]
    assert decision.selected_tool is None
    assert decision.unsupported_explained is True
    assert decision.assistant_message == "Note search by person ID is unsupported."
    await selector.aclose()


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
