"""AI-backed model selectors for MCP battle-test runs."""

from __future__ import annotations

import json
import os
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Protocol, cast

import httpx
from pydantic import Field

from followupboss_mcp.battle_tests import (
    BattleTestMcpClient,
    BattleTestModelProfile,
    BattleTestModelProvider,
    BattleTestRunArtifact,
    BattleTestScenario,
    BattleTestToolCall,
    BattleTestTranscript,
    ReadOnlyBattleTestOracle,
    battle_test_model_profiles,
    build_model_profile_run_metadata,
    capture_mcp_tool_transcript,
    evaluate_battle_test_run,
    expand_battle_test_prompt_variants,
    read_only_battle_test_scenarios,
    write_battle_test_run_artifact,
)
from followupboss_mcp.models.common import JsonValue, RequestModel

type JsonObject = dict[str, JsonValue]

_OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
_ANTHROPIC_MESSAGES_URL = "https://api.anthropic.com/v1/messages"
_ANTHROPIC_VERSION = "2023-06-01"
_CLARIFY_TOOL = "battle_test_clarify"
_UNSUPPORTED_TOOL = "battle_test_explain_unsupported"
_TASK_INTENT_RESPONSE_FIELDS = (
    "id",
    "name",
    "dueDate",
    "assignedUserId",
    "personId",
    "isCompleted",
    "type",
)


class BattleTestAiToolSpec(RequestModel):
    """Tool metadata exposed to an AI model during route selection."""

    name: str
    description: str
    input_schema: JsonObject


class BattleTestModelDecision(RequestModel):
    """AI-selected route for one prompt before the MCP call is executed."""

    scenario_id: str
    prompt: str
    selected_tool: str | None = None
    arguments: JsonObject = Field(default_factory=dict)
    assistant_message: str | None = None
    clarified: bool = False
    unsupported_explained: bool = False


class BattleTestModelSelector(Protocol):
    """Protocol implemented by AI provider-specific route selectors."""

    async def select_tool(
        self,
        *,
        profile: BattleTestModelProfile,
        scenario: BattleTestScenario,
        prompt: str,
        tools: tuple[BattleTestAiToolSpec, ...],
    ) -> BattleTestModelDecision:
        """Select one MCP route or clarification outcome for a prompt."""


type SelectorMap = Mapping[BattleTestModelProvider, BattleTestModelSelector]
type AsyncHttpClientFactory = Callable[[], httpx.AsyncClient]


def read_only_battle_test_ai_tool_specs() -> tuple[BattleTestAiToolSpec, ...]:
    """Return the tool menu used by read-only AI route-selection runs.

    Returns:
        Tool specs for the current read-only battle-test corpus, including
        sentinel tools for clarification and unsupported API capabilities.
    """
    fields_schema: JsonObject = {
        "type": "object",
        "properties": {"fields": _array_schema("Optional response fields to request.")},
        "additionalProperties": False,
    }
    paginated_fields_schema: JsonObject = {
        "type": "object",
        "properties": {
            "fields": _enum_array_schema(
                "Optional task response fields to request.",
                _TASK_INTENT_RESPONSE_FIELDS,
            ),
            "limit": _integer_schema("Optional page size."),
            "next_token": _string_schema("Optional next page token."),
            "offset": _integer_schema("Optional offset."),
        },
        "additionalProperties": False,
    }
    message_schema = _message_schema()
    return (
        BattleTestAiToolSpec(
            name="followupboss_get_latest_lead",
            description="Return the newest lead assigned to the authenticated user.",
            input_schema=fields_schema,
        ),
        BattleTestAiToolSpec(
            name="followupboss_search_people",
            description=(
                "Broad people search. Do not use for latest-owned-lead intent when "
                "followupboss_get_latest_lead applies."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "name": _string_schema("Optional person name query."),
                    "smart_list_id": _integer_schema("Resolved smart list ID."),
                    "limit": _integer_schema("Optional page size."),
                },
                "additionalProperties": False,
            },
        ),
        BattleTestAiToolSpec(
            name="followupboss_list_my_overdue_tasks",
            description="List incomplete overdue tasks assigned to the authenticated user.",
            input_schema=paginated_fields_schema,
        ),
        BattleTestAiToolSpec(
            name="followupboss_list_my_tasks_due_today",
            description="List incomplete tasks due today assigned to the authenticated user.",
            input_schema=paginated_fields_schema,
        ),
        BattleTestAiToolSpec(
            name="followupboss_list_tasks",
            description=(
                "Broad task list for explicit filters. Do not use for my overdue or "
                "my tasks today when narrow helpers apply."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "assigned_user_id": _integer_schema("Explicit Follow Up Boss user ID."),
                    "due": _string_schema("Documented due bucket such as today or overdue."),
                    "is_completed": {"type": "boolean"},
                    "limit": _integer_schema("Optional page size."),
                },
                "additionalProperties": False,
            },
        ),
        BattleTestAiToolSpec(
            name="followupboss_search_events",
            description="Search events. Do not use as a substitute for notes by person ID.",
            input_schema={"type": "object", "properties": {}, "additionalProperties": False},
        ),
        BattleTestAiToolSpec(
            name="followupboss_get_note",
            description="Fetch one note by explicit note ID only.",
            input_schema={
                "type": "object",
                "properties": {"note_id": _integer_schema("Explicit note ID.")},
                "required": ["note_id"],
                "additionalProperties": False,
            },
        ),
        BattleTestAiToolSpec(
            name=_CLARIFY_TOOL,
            description="Use when the prompt is too vague or unsafe to execute.",
            input_schema=message_schema,
        ),
        BattleTestAiToolSpec(
            name=_UNSUPPORTED_TOOL,
            description=(
                "Use when Follow Up Boss or this MCP does not support the requested action."
            ),
            input_schema=message_schema,
        ),
    )


def battle_test_selection_instructions() -> str:
    """Return provider-neutral instructions for AI route selection.

    Returns:
        A concise system instruction string for tool-selection-only runs.
    """
    return (
        "You are selecting a Follow Up Boss MCP tool for a battle test. "
        "Call exactly one tool when the user's prompt has a safe supported route. "
        f"Use {_CLARIFY_TOOL} when the prompt needs more information before any MCP call. "
        f"Use {_UNSUPPORTED_TOOL} when this MCP or the Follow Up Boss API does not support "
        "the requested capability. Do not invent IDs, owners, filters, or unsupported tools."
    )


def battle_test_ai_selectors_from_env(
    *,
    env: Mapping[str, str] | None = None,
    http_client_factory: AsyncHttpClientFactory | None = None,
) -> dict[BattleTestModelProvider, BattleTestModelSelector]:
    """Build AI model selectors from environment variables.

    Args:
        env: Environment mapping to inspect. Defaults to `os.environ`.
        http_client_factory: Optional factory for creating provider HTTP clients.

    Returns:
        Selectors for each configured AI provider.
    """
    source = os.environ if env is None else env
    selectors: dict[BattleTestModelProvider, BattleTestModelSelector] = {}
    openai_key = _first_env_value(
        source,
        "FOLLOWUPBOSS_BATTLE_TEST_OPENAI_API_KEY",
        "OPENAI_API_KEY",
    )
    anthropic_key = _first_env_value(
        source,
        "FOLLOWUPBOSS_BATTLE_TEST_ANTHROPIC_API_KEY",
        "ANTHROPIC_API_KEY",
        "CLAUDE_API_KEY",
    )
    if openai_key is not None:
        selectors[BattleTestModelProvider.OPENAI] = OpenAiBattleTestModelSelector(
            openai_key,
            http_client=http_client_factory() if http_client_factory is not None else None,
        )
    if anthropic_key is not None:
        selectors[BattleTestModelProvider.ANTHROPIC] = AnthropicBattleTestModelSelector(
            anthropic_key,
            http_client=http_client_factory() if http_client_factory is not None else None,
        )
    return selectors


def load_env_file(path: Path) -> None:
    """Load simple KEY=VALUE pairs from an env file without echoing secrets.

    Existing environment variables win over file values.

    Args:
        path: Env file path to load when present.
    """
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key and key not in os.environ:
            os.environ[key] = _strip_env_quotes(value.strip())


class OpenAiBattleTestModelSelector:
    """OpenAI Responses API selector for battle-test tool routing."""

    def __init__(
        self,
        api_key: str,
        *,
        http_client: httpx.AsyncClient | None = None,
        responses_url: str = _OPENAI_RESPONSES_URL,
    ) -> None:
        """Initialize the OpenAI selector.

        Args:
            api_key: OpenAI API key.
            http_client: Optional injected async HTTP client.
            responses_url: Responses API URL.
        """
        self._api_key = api_key
        self._http_client = http_client or httpx.AsyncClient()
        self._responses_url = responses_url

    async def aclose(self) -> None:
        """Close the underlying HTTP client."""
        await self._http_client.aclose()

    async def select_tool(
        self,
        *,
        profile: BattleTestModelProfile,
        scenario: BattleTestScenario,
        prompt: str,
        tools: tuple[BattleTestAiToolSpec, ...],
    ) -> BattleTestModelDecision:
        """Select a route with the OpenAI Responses API."""
        payload: dict[str, object] = {
            "model": profile.model,
            "instructions": battle_test_selection_instructions(),
            "input": prompt,
            "tools": [_openai_tool_spec(tool) for tool in tools],
            "tool_choice": "auto",
        }
        if profile.reasoning_effort is not None:
            payload["reasoning"] = {"effort": profile.reasoning_effort}
        response = await self._http_client.post(
            self._responses_url,
            headers={"Authorization": f"Bearer {self._api_key}"},
            json=payload,
        )
        response.raise_for_status()
        data: object = response.json()
        if not isinstance(data, dict):
            raise ValueError("OpenAI route-selection response must be an object.")
        return _openai_decision_from_response(
            scenario=scenario,
            prompt=prompt,
            payload=cast(Mapping[str, object], data),
        )


class AnthropicBattleTestModelSelector:
    """Anthropic Messages API selector for battle-test tool routing."""

    def __init__(
        self,
        api_key: str,
        *,
        http_client: httpx.AsyncClient | None = None,
        messages_url: str = _ANTHROPIC_MESSAGES_URL,
    ) -> None:
        """Initialize the Anthropic selector.

        Args:
            api_key: Anthropic API key.
            http_client: Optional injected async HTTP client.
            messages_url: Messages API URL.
        """
        self._api_key = api_key
        self._http_client = http_client or httpx.AsyncClient()
        self._messages_url = messages_url

    async def aclose(self) -> None:
        """Close the underlying HTTP client."""
        await self._http_client.aclose()

    async def select_tool(
        self,
        *,
        profile: BattleTestModelProfile,
        scenario: BattleTestScenario,
        prompt: str,
        tools: tuple[BattleTestAiToolSpec, ...],
    ) -> BattleTestModelDecision:
        """Select a route with the Anthropic Messages API."""
        response = await self._http_client.post(
            self._messages_url,
            headers={
                "x-api-key": self._api_key,
                "anthropic-version": _ANTHROPIC_VERSION,
            },
            json={
                "model": profile.model,
                "max_tokens": 512,
                "system": battle_test_selection_instructions(),
                "messages": [{"role": "user", "content": prompt}],
                "tools": [_anthropic_tool_spec(tool) for tool in tools],
                "tool_choice": {"type": "auto"},
            },
        )
        response.raise_for_status()
        data: object = response.json()
        if not isinstance(data, dict):
            raise ValueError("Anthropic route-selection response must be an object.")
        return _anthropic_decision_from_response(
            scenario=scenario,
            prompt=prompt,
            payload=cast(Mapping[str, object], data),
        )


async def capture_ai_selected_transcript(
    *,
    selector: BattleTestModelSelector,
    profile: BattleTestModelProfile,
    scenario: BattleTestScenario,
    prompt: str,
    mcp_client: BattleTestMcpClient,
    tools: tuple[BattleTestAiToolSpec, ...] | None = None,
) -> BattleTestTranscript:
    """Ask an AI model for a route and capture the resulting transcript.

    Args:
        selector: Provider selector used to choose the route.
        profile: Model profile being evaluated.
        scenario: Scenario contract being run.
        prompt: Prompt variant to ask the model.
        mcp_client: MCP client used to execute selected real tools.
        tools: Optional tool specs. Defaults to read-only battle-test specs.

    Returns:
        A battle-test transcript ready for oracle evaluation.
    """
    try:
        decision = await selector.select_tool(
            profile=profile,
            scenario=scenario,
            prompt=prompt,
            tools=tools or read_only_battle_test_ai_tool_specs(),
        )
    except Exception as exc:
        return BattleTestTranscript(
            scenario_id=scenario.id,
            prompt=prompt,
            response={"error": f"AI route selection failed: {exc}"},
            assistant_message=str(exc),
        )
    if decision.selected_tool is None:
        return BattleTestTranscript(
            scenario_id=scenario.id,
            prompt=prompt,
            assistant_message=decision.assistant_message,
            clarified=decision.clarified,
            unsupported_explained=decision.unsupported_explained,
        )
    tool_call = BattleTestToolCall(
        scenario_id=scenario.id,
        prompt=prompt,
        tool_name=decision.selected_tool,
        arguments=decision.arguments,
        assistant_message=decision.assistant_message,
    )
    try:
        return await capture_mcp_tool_transcript(mcp_client, tool_call)
    except Exception as exc:
        return BattleTestTranscript(
            scenario_id=scenario.id,
            prompt=prompt,
            selected_tool=decision.selected_tool,
            arguments=decision.arguments,
            response={"error": str(exc)},
            assistant_message=decision.assistant_message,
        )


async def run_ai_model_profile_battle_tests(
    *,
    mcp_client: BattleTestMcpClient,
    oracle: ReadOnlyBattleTestOracle,
    selectors: SelectorMap,
    run_id_prefix: str,
    client: str,
    profiles: tuple[BattleTestModelProfile, ...] | None = None,
    scenarios: tuple[BattleTestScenario, ...] | None = None,
    artifact_directory: Path | None = None,
    prompt_variant_index: int = 0,
    all_prompt_variants: bool = False,
    environment: str | None = None,
    started_at: str | None = None,
    notes: tuple[str, ...] = (),
) -> tuple[BattleTestRunArtifact, ...]:
    """Run the read-only battle-test corpus separately for each model profile.

    Args:
        mcp_client: MCP client used to execute model-selected tools.
        oracle: Direct API oracle used to evaluate MCP responses.
        selectors: Provider-specific AI selectors.
        run_id_prefix: Shared run prefix for sibling profile artifacts.
        client: Client or harness label.
        profiles: Optional profile list. Defaults to GPT-5.5 low reasoning and
            Sonnet 4.6.
        scenarios: Optional scenario corpus. Defaults to read-only scenarios.
        artifact_directory: Optional output directory for JSON artifacts.
        prompt_variant_index: Prompt variant index to run for each scenario.
        all_prompt_variants: Whether to expand every scenario prompt variant
            into a separately evaluated case.
        environment: Optional target environment label.
        started_at: Optional ISO-like run timestamp.
        notes: Optional notes stored in each artifact.

    Returns:
        One run artifact per model profile.
    """
    scenario_corpus = _resolve_prompt_variant_corpus(
        scenarios=scenarios,
        all_prompt_variants=all_prompt_variants,
    )
    artifacts: list[BattleTestRunArtifact] = []
    for profile in profiles or battle_test_model_profiles():
        selector = selectors.get(profile.provider)
        if selector is None:
            raise RuntimeError(
                f"No battle-test selector configured for provider {profile.provider}."
            )
        transcripts = tuple(
            [
                await capture_ai_selected_transcript(
                    selector=selector,
                    profile=profile,
                    scenario=scenario,
                    prompt=_prompt_variant(
                        scenario,
                        0 if all_prompt_variants else prompt_variant_index,
                    ),
                    mcp_client=mcp_client,
                )
                for scenario in scenario_corpus
            ]
        )
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
            transcripts,
            metadata=metadata,
            scenarios=scenario_corpus,
        )
        if artifact_directory is not None:
            write_battle_test_run_artifact(
                artifact,
                artifact_directory / f"{metadata.run_id}.json",
            )
        artifacts.append(artifact)
    return tuple(artifacts)


def _resolve_prompt_variant_corpus(
    *,
    scenarios: tuple[BattleTestScenario, ...] | None,
    all_prompt_variants: bool,
) -> tuple[BattleTestScenario, ...]:
    """Resolve the scenario corpus for one AI runner invocation."""
    scenario_corpus = scenarios or read_only_battle_test_scenarios()
    if all_prompt_variants:
        return expand_battle_test_prompt_variants(scenario_corpus)
    return scenario_corpus


def _first_env_value(env: Mapping[str, str], *keys: str) -> str | None:
    """Return the first non-empty env var value from `keys`."""
    for key in keys:
        value = env.get(key)
        if value:
            return value
    return None


def _strip_env_quotes(value: str) -> str:
    """Strip a single matching quote pair from an env file value."""
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def _prompt_variant(scenario: BattleTestScenario, index: int) -> str:
    """Return one prompt variant from a scenario."""
    if index < 0 or index >= len(scenario.prompt_variants):
        raise IndexError(f"Prompt variant index {index} is out of range for {scenario.id}.")
    return scenario.prompt_variants[index]


def _string_schema(description: str) -> JsonObject:
    """Return a JSON schema string property."""
    return {"type": "string", "description": description}


def _integer_schema(description: str) -> JsonObject:
    """Return a JSON schema integer property."""
    return {"type": "integer", "description": description}


def _array_schema(description: str) -> JsonObject:
    """Return a JSON schema string-array property."""
    return {
        "type": "array",
        "description": description,
        "items": {"type": "string"},
    }


def _enum_array_schema(description: str, allowed_values: tuple[str, ...]) -> JsonObject:
    """Return a JSON schema string-array property with enum-constrained values.

    Args:
        description: Human-readable schema description.
        allowed_values: Values accepted for each item in the array.

    Returns:
        A JSON schema object for a string array with enumerated items.
    """
    return {
        "type": "array",
        "description": description,
        "items": {"type": "string", "enum": list(allowed_values)},
    }


def _message_schema() -> JsonObject:
    """Return the sentinel message input schema."""
    return {
        "type": "object",
        "properties": {"message": _string_schema("User-facing explanation or question.")},
        "required": ["message"],
        "additionalProperties": False,
    }


def _openai_tool_spec(tool: BattleTestAiToolSpec) -> dict[str, object]:
    """Serialize one tool spec for OpenAI Responses."""
    return {
        "type": "function",
        "name": tool.name,
        "description": tool.description,
        "parameters": tool.input_schema,
    }


def _anthropic_tool_spec(tool: BattleTestAiToolSpec) -> dict[str, object]:
    """Serialize one tool spec for Anthropic Messages."""
    return {
        "name": tool.name,
        "description": tool.description,
        "input_schema": tool.input_schema,
    }


def _openai_decision_from_response(
    *,
    scenario: BattleTestScenario,
    prompt: str,
    payload: Mapping[str, object],
) -> BattleTestModelDecision:
    """Parse an OpenAI Responses route-selection response."""
    output = payload.get("output")
    if isinstance(output, list):
        for item in output:
            if isinstance(item, Mapping) and item.get("type") == "function_call":
                name = item.get("name")
                if isinstance(name, str):
                    return _decision_from_tool_call(
                        scenario=scenario,
                        prompt=prompt,
                        tool_name=name,
                        raw_arguments=item.get("arguments"),
                        fallback_message=_openai_text(payload),
                    )
    return BattleTestModelDecision(
        scenario_id=scenario.id,
        prompt=prompt,
        assistant_message=_openai_text(payload),
    )


def _anthropic_decision_from_response(
    *,
    scenario: BattleTestScenario,
    prompt: str,
    payload: Mapping[str, object],
) -> BattleTestModelDecision:
    """Parse an Anthropic Messages route-selection response."""
    content = payload.get("content")
    text = _anthropic_text(payload)
    if isinstance(content, list):
        for item in content:
            if isinstance(item, Mapping) and item.get("type") == "tool_use":
                name = item.get("name")
                if isinstance(name, str):
                    return _decision_from_tool_call(
                        scenario=scenario,
                        prompt=prompt,
                        tool_name=name,
                        raw_arguments=item.get("input"),
                        fallback_message=text,
                    )
    return BattleTestModelDecision(
        scenario_id=scenario.id,
        prompt=prompt,
        assistant_message=text,
    )


def _decision_from_tool_call(
    *,
    scenario: BattleTestScenario,
    prompt: str,
    tool_name: str,
    raw_arguments: object,
    fallback_message: str | None,
) -> BattleTestModelDecision:
    """Convert one provider tool call into a normalized decision."""
    arguments = _arguments_object(raw_arguments)
    if tool_name == _CLARIFY_TOOL:
        return BattleTestModelDecision(
            scenario_id=scenario.id,
            prompt=prompt,
            assistant_message=_message_argument(arguments) or fallback_message,
            clarified=True,
        )
    if tool_name == _UNSUPPORTED_TOOL:
        return BattleTestModelDecision(
            scenario_id=scenario.id,
            prompt=prompt,
            assistant_message=_message_argument(arguments) or fallback_message,
            unsupported_explained=True,
        )
    return BattleTestModelDecision(
        scenario_id=scenario.id,
        prompt=prompt,
        selected_tool=tool_name,
        arguments=arguments,
        assistant_message=fallback_message,
    )


def _arguments_object(raw_arguments: object) -> JsonObject:
    """Normalize provider tool-call arguments into a JSON object."""
    if isinstance(raw_arguments, str):
        loaded = json.loads(raw_arguments or "{}")
        return _json_object(loaded)
    return _json_object(raw_arguments)


def _json_object(value: object) -> JsonObject:
    """Return a JSON object from a provider payload."""
    if not isinstance(value, Mapping):
        return {}
    normalized: JsonObject = {}
    for key, item in value.items():
        if isinstance(key, str):
            normalized[key] = _json_value(item)
    return normalized


def _json_value(value: object) -> JsonValue:
    """Normalize one provider payload value into the project JSON type."""
    if value is None or isinstance(value, bool | int | float | str):
        return value
    if isinstance(value, Mapping):
        return _json_object(value)
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    return str(value)


def _message_argument(arguments: Mapping[str, JsonValue]) -> str | None:
    """Return the sentinel message argument when present."""
    message = arguments.get("message")
    return message if isinstance(message, str) else None


def _openai_text(payload: Mapping[str, object]) -> str | None:
    """Extract text output from an OpenAI response when available."""
    output_text = payload.get("output_text")
    if isinstance(output_text, str):
        return output_text
    return None


def _anthropic_text(payload: Mapping[str, object]) -> str | None:
    """Extract text output from an Anthropic response when available."""
    content = payload.get("content")
    if not isinstance(content, list):
        return None
    text_parts: list[str] = []
    for item in content:
        if not isinstance(item, Mapping) or item.get("type") != "text":
            continue
        text = item.get("text")
        if isinstance(text, str):
            text_parts.append(text)
    return "\n".join(text_parts) if text_parts else None
