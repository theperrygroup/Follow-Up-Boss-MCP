"""AI-backed model selectors for MCP battle-test runs."""

from __future__ import annotations

import json
import os
from collections.abc import Awaitable, Callable, Mapping
from pathlib import Path
from typing import Protocol, cast

import httpx
from pydantic import Field

from followupboss_mcp.battle_tests import (
    BattleTestConversationEvaluation,
    BattleTestConversationKind,
    BattleTestConversationScenario,
    BattleTestConversationTranscript,
    BattleTestGrade,
    BattleTestMcpClient,
    BattleTestModelProfile,
    BattleTestModelProvider,
    BattleTestMultiCallTranscript,
    BattleTestRunArtifact,
    BattleTestScenario,
    BattleTestToolCall,
    BattleTestTranscript,
    ExpectedMcpRoute,
    ReadOnlyBattleTestOracle,
    battle_test_model_profiles,
    build_model_profile_run_metadata,
    capture_mcp_tool_transcript,
    conversation_turn_to_scenario,
    evaluate_battle_test_conversation,
    evaluate_battle_test_run,
    expand_battle_test_prompt_variants,
    flatten_battle_test_conversations,
    read_only_battle_test_conversations,
    read_only_battle_test_scenarios,
    sample_battle_test_conversations,
    sample_battle_test_scenarios,
    write_battle_test_run_artifact,
)
from followupboss_mcp.models.common import JsonValue, RequestModel

type JsonObject = dict[str, JsonValue]

_OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
_ANTHROPIC_MESSAGES_URL = "https://api.anthropic.com/v1/messages"
_ANTHROPIC_VERSION = "2023-06-01"
_CLARIFY_TOOL = "battle_test_clarify"
_UNSUPPORTED_TOOL = "battle_test_explain_unsupported"
_LATEST_LEAD_RESPONSE_FIELDS = (
    "id",
    "name",
    "firstName",
    "lastName",
    "created",
    "assignedUserId",
    "stage",
    "source",
    "lastActivity",
)
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
        "properties": {
            "fields": _enum_array_schema(
                "Optional latest-lead person response fields to request.",
                _LATEST_LEAD_RESPONSE_FIELDS,
            )
        },
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
                "followupboss_get_latest_lead applies. Use for explicit name, email, phone, "
                "known numeric smart_list_id people searches, or direct documented search "
                "filters such as contacted=false. Use contacted=false for uncontacted, "
                "never-contacted, zero-communication, or no-communication leads. For a named "
                "owner such as Scott Willey, pass assigned_to='Scott Willey'. Do not use this "
                "for named smart-list people prompts; use followupboss_search_people_in_smart_list."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "assigned_to": _string_schema("Assigned owner name filter."),
                    "assigned_user_id": _integer_schema("Assigned owner user ID filter."),
                    "contacted": {"type": "boolean"},
                    "name": _string_schema("Optional person name query."),
                    "smart_list_id": _integer_schema("Resolved smart list ID."),
                    "source": _string_schema(
                        "Lead source filter. Required as source='Zillow' whenever the prompt "
                        "mentions Zillow and a resolved smart_list_id is used."
                    ),
                    "stage": _string_schema("Optional stage filter."),
                    "limit": _integer_schema("Optional page size."),
                },
                "additionalProperties": False,
            },
        ),
        BattleTestAiToolSpec(
            name="followupboss_search_people_in_smart_list",
            description=(
                "Search people inside one exact named smart list. Use this for named "
                "smart-list prompts such as Zillow leads in Eligible For Transfer. This "
                "tool resolves the list name internally, searches only inside that "
                "smart-list ID, and returns smart-list provenance. Do not include people "
                "absent from this tool result in the answer. When the prompt says Zillow "
                "leads, include source='Zillow'. The helper defaults to mine=true, so "
                "omitted owner scope is authenticated-user scoped. Set mine=false only "
                "for explicit everyone/account-wide prompts. For named owners such as "
                "Scott Willey, pass assigned_user_name and let the helper resolve it. "
                "Do not invent owner IDs."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "assigned_user_name": _string_schema(
                        "Exact Follow Up Boss owner/agent name, such as Scott Willey."
                    ),
                    "smart_list_name": _string_schema("Exact Follow Up Boss smart-list name."),
                    "fields": _enum_array_schema(
                        "Optional person response fields to request.",
                        _LATEST_LEAD_RESPONSE_FIELDS,
                    ),
                    "limit": _integer_schema("Optional page size."),
                    "mine": {
                        "type": "boolean",
                        "default": True,
                        "description": (
                            "True for I/me/my follow-up requests; false only when explicitly "
                            "account-wide/everyone."
                        ),
                    },
                    "next_token": _string_schema("Optional next page token."),
                    "offset": _integer_schema("Optional offset."),
                    "source": _string_schema("Optional source filter, such as Zillow."),
                    "stage": _string_schema("Optional stage filter."),
                },
                "required": ["smart_list_name", "mine"],
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
            name="followupboss_list_my_upcoming_tasks",
            description=(
                "List incomplete tasks due after today and assigned to the authenticated user."
            ),
            input_schema=paginated_fields_schema,
        ),
        BattleTestAiToolSpec(
            name="followupboss_list_tasks",
            description=(
                "Broad task list for explicit filters. Do not use for my overdue or "
                "my tasks today or my upcoming tasks when narrow helpers apply."
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
            name="followupboss_list_smart_lists",
            description=(
                "List available Follow Up Boss smart lists. Use before searching a named "
                "list when no smart_list_id is known, then search people only with the "
                "resolved ID. For prompts like Zillow leads in Eligible For Transfer, this "
                "resolution step is mandatory."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "include_all": {"type": "boolean"},
                    "limit": _integer_schema("Optional page size."),
                    "offset": _integer_schema("Optional offset."),
                },
                "additionalProperties": False,
            },
        ),
        BattleTestAiToolSpec(
            name="followupboss_check_duplicate_person",
            description=(
                "Check whether a person already exists when the prompt provides an "
                "explicit email or phone."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "email": _string_schema("Email address to duplicate-check."),
                    "phone": _string_schema("Phone number to duplicate-check."),
                },
                "additionalProperties": False,
            },
        ),
        BattleTestAiToolSpec(
            name="followupboss_list_unclaimed_people",
            description=(
                "List unclaimed people or lead offers available to claim. Do not claim "
                "or ignore them."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "limit": _integer_schema("Optional page size."),
                    "offset": _integer_schema("Optional offset."),
                },
                "additionalProperties": False,
            },
        ),
        BattleTestAiToolSpec(
            name="followupboss_list_person_activity",
            description=(
                "List communication and activity history for one explicit person_id. "
                "Use this for lead/contact/person history prompts that ask for calls, "
                "texts, email events, events, appointments, messages, communication log, "
                "interaction timeline, or what we sent. If no explicit person_id is "
                "available from the prompt or prior turn, clarify instead of using broad "
                "activity list tools."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "person_id": _integer_schema("Explicit Follow Up Boss person ID."),
                    "include_appointments": {"type": "boolean"},
                    "include_calls": {"type": "boolean"},
                    "include_email_events": {"type": "boolean"},
                    "include_events": {"type": "boolean"},
                    "include_text_messages": {"type": "boolean"},
                    "limit": _integer_schema("Optional per-surface page size."),
                    "offset": _integer_schema("Optional per-surface offset."),
                },
                "required": ["person_id"],
                "additionalProperties": False,
            },
        ),
        BattleTestAiToolSpec(
            name="followupboss_list_appointments",
            description=(
                "List appointment records. Use safe filters when a person_id or user_id "
                "is explicitly provided; otherwise list safely."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "person_id": _integer_schema("Explicit person ID filter."),
                    "user_id": _integer_schema("Explicit user ID filter."),
                    "limit": _integer_schema("Optional page size."),
                    "offset": _integer_schema("Optional offset."),
                },
                "additionalProperties": False,
            },
        ),
        BattleTestAiToolSpec(
            name="followupboss_list_calls",
            description=(
                "List call records. Use explicit person_id or phone filters when "
                "provided; otherwise list safely."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "person_id": _integer_schema("Explicit person ID filter."),
                    "phone": _string_schema("Explicit phone filter."),
                    "limit": _integer_schema("Optional page size."),
                    "offset": _integer_schema("Optional offset."),
                },
                "additionalProperties": False,
            },
        ),
        BattleTestAiToolSpec(
            name="followupboss_list_text_messages",
            description="List recorded text-message logs. This does not send a live SMS.",
            input_schema={
                "type": "object",
                "properties": {
                    "person_id": _integer_schema("Explicit person ID filter."),
                },
                "additionalProperties": False,
            },
        ),
        BattleTestAiToolSpec(
            name="followupboss_list_email_events",
            description=(
                "List email marketing event logs. For lead/contact/person communication "
                "history, prefer followupboss_list_person_activity with an explicit person_id."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "person_id": _integer_schema("Explicit person ID filter."),
                    "type": _string_schema("Optional email event type."),
                    "limit": _integer_schema("Optional page size."),
                    "offset": _integer_schema("Optional offset."),
                },
                "additionalProperties": False,
            },
        ),
        BattleTestAiToolSpec(
            name="followupboss_list_templates",
            description=(
                "List saved email templates. Use merge tools only when explicit template "
                "and recipient details are provided."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "limit": _integer_schema("Optional page size."),
                    "offset": _integer_schema("Optional offset."),
                },
                "additionalProperties": False,
            },
        ),
        BattleTestAiToolSpec(
            name="followupboss_list_text_message_templates",
            description=(
                "List saved text-message templates. Use merge tools only when explicit "
                "template and recipient details are provided."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "limit": _integer_schema("Optional page size."),
                    "offset": _integer_schema("Optional offset."),
                },
                "additionalProperties": False,
            },
        ),
        BattleTestAiToolSpec(
            name="followupboss_search_events",
            description=(
                "Search events. Do not use as a substitute for notes by person, lead, "
                "or contact ID; use battle_test_explain_unsupported for those requests."
            ),
            input_schema={"type": "object", "properties": {}, "additionalProperties": False},
        ),
        BattleTestAiToolSpec(
            name="followupboss_get_note",
            description=(
                "Fetch one note by explicit note ID only. For note history, notes by person, "
                "notes by lead, or notes by contact, use battle_test_explain_unsupported."
            ),
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
                "Use when Follow Up Boss or this MCP does not support the requested action, "
                "including note history or notes by person, lead, or contact. In multi-action "
                "prompts, call this as one ordered action for the unsupported portion while "
                "still calling supported tools for the supported portions. This includes "
                "questions asking whether notes can be searched by lead or contact."
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
        "Do not answer with plain text only when any safe supported or sentinel route applies. "
        "Call exactly one tool when the user's prompt has one safe supported route. "
        "When one prompt asks for multiple independent supported actions, call the needed "
        "tools in the same order as the user asked. If a prompt mixes supported actions with "
        "unsupported actions, call the supported tools and also call the unsupported sentinel "
        "for the unsupported part, preserving the user's order. "
        "For example, 'pull my newest lead and tell me whether you can search that lead's "
        "notes' requires followupboss_get_latest_lead followed by "
        f"{_UNSUPPORTED_TOOL}. "
        "Route temporal task requests by the user's words: late, overdue, past due, behind, "
        "or missed means followupboss_list_my_overdue_tasks; today, due today, or not miss "
        "today means followupboss_list_my_tasks_due_today; coming up, upcoming, later, after "
        "today, next, future, or ahead means followupboss_list_my_upcoming_tasks. "
        "Use followupboss_search_people with contacted=false for uncontacted, never-contacted, "
        "zero-communication, no-communication, or haven't communicated leads when the user is "
        "asking for search filtering rather than a named saved list. If the prompt names an "
        "owner such as Scott Willey, pass assigned_to='Scott Willey'. Do not list or resolve "
        "smart lists for these direct search-filter prompts. "
        "Use followupboss_search_people_in_smart_list for named smart-list people prompts; "
        "pass the exact smart_list_name, such as Eligible For Transfer, and optional safe "
        "filters such as source='Zillow'. When the prompt says Zillow leads, include "
        "source='Zillow'. Treat 'came from Zillow', 'source is Zillow', 'Zillow follow-up "
        "block', 'boundary for Zillow follow-ups', and 'Zillow leads I should call' the "
        "same way: use smart_list_name='Eligible For Transfer' and source='Zillow' when "
        "Eligible For Transfer is named. For named smart-list follow-up prompts using I, "
        "me, my, mine, I should call, I need to work, or do I need to follow up, set "
        "mine=true so the helper scopes to the authenticated user even when the credential "
        "is admin-visible. Set mine=false only when the prompt explicitly asks for everyone, "
        "all agents, account-wide, team-wide, or an overall count. For a named owner such as "
        "Scott Willey, pass assigned_user_name and let the helper resolve the owner; do not "
        "invent owner IDs or return account-wide results. The final answer must not include "
        "any person absent from that smart-list-scoped tool result. Use "
        "followupboss_list_smart_lists "
        "only when the user is asking to list or inspect saved lists, not as the final route "
        "for a named-list people search. Use followupboss_search_people when a people search "
        "includes an explicit name, email, phone, or known numeric smart_list_id, and "
        "never use a source-only people search for a bare Zillow follow-up prompt. "
        "followupboss_check_duplicate_person only when an email or phone is provided. "
        "If the prompt says Zillow leads and the current or prior context maps Zillow leads "
        "to Eligible For Transfer, call followupboss_search_people_in_smart_list with "
        "smart_list_name='Eligible For Transfer' before any broad people search. If Zillow "
        "leads has no current or prior smart-list context, call battle_test_clarify and ask "
        "which smart list or saved view should scope the Zillow leads; do not broad-search "
        "or answer from memory. Never default a bare Zillow-leads prompt to Eligible For "
        "Transfer unless the prompt or an earlier turn explicitly named that list. "
        "Use followupboss_list_person_activity for communication history, activity history, "
        "messages, calls, texts, email events, events, appointments, interaction timelines, "
        "or what we sent only when the prompt or prior turn provides an explicit person_id. "
        "If a lead/contact/person history request says this lead, that contact, my lead, "
        "latest lead, Zillow person, or similar without a resolved person_id, call "
        "battle_test_clarify; do not use broad calls, text messages, email events, events, "
        "or appointments list tools for that vague person-history request. "
        "Use list tools for appointments, calls, text-message logs, email templates, and "
        "text-message templates; these are read-only listing intents. "
        "Fetch notes only with an explicit note ID. "
        "For multi-turn prompts, route the current user turn independently; use prior turns "
        "only to resolve references such as that lead, this contact, that list, or those leads. "
        "For count-to-list follow-ups such as 'show those leads' after a contacted=false people "
        "search count, re-run followupboss_search_people with the same contacted and owner filters "
        "from context. Only use smart-list follow-up context when the previous turn "
        "explicitly used "
        "a smart list. "
        f"Use {_CLARIFY_TOOL} when the prompt needs more information before any MCP call. "
        f"Use {_UNSUPPORTED_TOOL} when this MCP or the Follow Up Boss API does not support "
        "the requested capability. Note history and notes by person, lead, or contact are "
        f"unsupported unless the user provides an explicit note ID; use {_UNSUPPORTED_TOOL} "
        "for those requests. Do not invent IDs, owners, filters, or unsupported tools."
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
        decisions = await self.select_tools(
            profile=profile,
            scenario=scenario,
            prompt=prompt,
            tools=tools,
        )
        return decisions[0]

    async def select_tools(
        self,
        *,
        profile: BattleTestModelProfile,
        scenario: BattleTestScenario,
        prompt: str,
        tools: tuple[BattleTestAiToolSpec, ...],
    ) -> tuple[BattleTestModelDecision, ...]:
        """Select one or more routes with the OpenAI Responses API."""
        payload: dict[str, object] = {
            "model": profile.model,
            "instructions": battle_test_selection_instructions(),
            "input": prompt,
            "tools": [_openai_tool_spec(tool) for tool in tools],
            "tool_choice": "required",
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
        return _openai_decisions_from_response(
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
        decisions = await self.select_tools(
            profile=profile,
            scenario=scenario,
            prompt=prompt,
            tools=tools,
        )
        return decisions[0]

    async def select_tools(
        self,
        *,
        profile: BattleTestModelProfile,
        scenario: BattleTestScenario,
        prompt: str,
        tools: tuple[BattleTestAiToolSpec, ...],
    ) -> tuple[BattleTestModelDecision, ...]:
        """Select one or more routes with the Anthropic Messages API."""
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
                "tool_choice": {"type": "any"},
            },
        )
        response.raise_for_status()
        data: object = response.json()
        if not isinstance(data, dict):
            raise ValueError("Anthropic route-selection response must be an object.")
        return _anthropic_decisions_from_response(
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


async def capture_ai_selected_multi_call_transcript(
    *,
    selector: BattleTestModelSelector,
    profile: BattleTestModelProfile,
    conversation: BattleTestConversationScenario,
    mcp_client: BattleTestMcpClient,
    tools: tuple[BattleTestAiToolSpec, ...] | None = None,
) -> BattleTestMultiCallTranscript:
    """Ask an AI model for multiple routes from one multi-ask prompt.

    Args:
        selector: Provider selector used to choose routes.
        profile: Model profile being evaluated.
        conversation: Multi-ask conversation contract.
        mcp_client: MCP client used to execute selected real tools.
        tools: Optional tool specs. Defaults to read-only battle-test specs.

    Returns:
        Ordered multi-call transcript for the single user prompt.

    Raises:
        ValueError: If `conversation` is not a multi-ask scenario.
    """
    if conversation.kind is not BattleTestConversationKind.MULTI_ASK:
        raise ValueError("Multi-call transcript capture requires a multi-ask conversation.")
    prompt = conversation.prompt or conversation.turns[0].prompt
    expected_scenarios = tuple(
        conversation_turn_to_scenario(conversation, turn) for turn in conversation.turns
    )
    selector_prompt = _multi_call_prompt(prompt, expected_count=len(expected_scenarios))
    try:
        decisions = await _select_tool_decisions(
            selector=selector,
            profile=profile,
            scenario=expected_scenarios[0],
            prompt=selector_prompt,
            tools=tools or read_only_battle_test_ai_tool_specs(),
        )
    except Exception as exc:
        return BattleTestMultiCallTranscript(
            scenario_id=conversation.id,
            prompt=prompt,
            transcripts=tuple(
                BattleTestTranscript(
                    scenario_id=scenario.id,
                    prompt=prompt,
                    response={"error": f"AI route selection failed: {exc}"},
                    assistant_message=str(exc),
                )
                for scenario in expected_scenarios
            ),
            assistant_message=str(exc),
        )
    transcripts: list[BattleTestTranscript] = []
    for index, expected_scenario in enumerate(expected_scenarios):
        decision = (
            decisions[index]
            if index < len(decisions)
            else _empty_decision(
                expected_scenario,
                prompt,
                assistant_message=_first_assistant_message(decisions),
            )
        )
        transcripts.append(
            await _capture_decision_transcript(
                mcp_client=mcp_client,
                scenario=expected_scenario,
                prompt=prompt,
                decision=decision,
            )
        )
    for index, decision in enumerate(decisions[len(expected_scenarios) :], start=1):
        extra_scenario = BattleTestScenario(
            id=f"{conversation.id}-EXTRA-{index:02d}",
            grade=BattleTestGrade.MAY_ROUTE,
            prompt_variants=(prompt,),
            expected_mcp=ExpectedMcpRoute(),
            api_oracle=expected_scenarios[0].api_oracle,
        )
        transcripts.append(
            await _capture_decision_transcript(
                mcp_client=mcp_client,
                scenario=extra_scenario,
                prompt=prompt,
                decision=decision,
            )
        )
    return BattleTestMultiCallTranscript(
        scenario_id=conversation.id,
        prompt=prompt,
        transcripts=tuple(transcripts),
        assistant_message=decisions[0].assistant_message if decisions else None,
    )


async def capture_ai_selected_conversation_transcript(
    *,
    selector: BattleTestModelSelector,
    profile: BattleTestModelProfile,
    conversation: BattleTestConversationScenario,
    mcp_client: BattleTestMcpClient,
    tools: tuple[BattleTestAiToolSpec, ...] | None = None,
) -> BattleTestConversationTranscript:
    """Capture one true multi-turn or single-message multi-ask conversation.

    Args:
        selector: Provider selector used to choose routes.
        profile: Model profile being evaluated.
        conversation: Conversation contract to execute.
        mcp_client: MCP client used to execute selected real tools.
        tools: Optional tool specs. Defaults to read-only battle-test specs.

    Returns:
        Captured conversation transcript.
    """
    if conversation.kind is BattleTestConversationKind.MULTI_ASK:
        multi_call = await capture_ai_selected_multi_call_transcript(
            selector=selector,
            profile=profile,
            conversation=conversation,
            mcp_client=mcp_client,
            tools=tools,
        )
        return BattleTestConversationTranscript(
            conversation_id=conversation.id,
            kind=conversation.kind,
            turn_transcripts=multi_call.transcripts,
            prompt=multi_call.prompt,
        )

    history: list[BattleTestTranscript] = []
    turn_transcripts: list[BattleTestTranscript] = []
    for turn in conversation.turns:
        scenario = conversation_turn_to_scenario(conversation, turn)
        prompt = _conversation_prompt(turn.prompt, tuple(history))
        try:
            decision = await _select_tool_decisions(
                selector=selector,
                profile=profile,
                scenario=scenario,
                prompt=prompt,
                tools=tools or read_only_battle_test_ai_tool_specs(),
            )
        except Exception as exc:
            transcript = BattleTestTranscript(
                scenario_id=scenario.id,
                prompt=turn.prompt,
                response={"error": f"AI route selection failed: {exc}"},
                assistant_message=str(exc),
            )
        else:
            transcript = await _capture_decision_transcript(
                mcp_client=mcp_client,
                scenario=scenario,
                prompt=turn.prompt,
                decision=decision[0],
            )
        history.append(transcript)
        turn_transcripts.append(transcript)
    return BattleTestConversationTranscript(
        conversation_id=conversation.id,
        kind=conversation.kind,
        turn_transcripts=tuple(turn_transcripts),
    )


async def _select_tool_decisions(
    *,
    selector: BattleTestModelSelector,
    profile: BattleTestModelProfile,
    scenario: BattleTestScenario,
    prompt: str,
    tools: tuple[BattleTestAiToolSpec, ...],
) -> tuple[BattleTestModelDecision, ...]:
    """Select one or more tool decisions through a compatible selector.

    Args:
        selector: Provider selector or test double.
        profile: Model profile being evaluated.
        scenario: Scenario contract used for prompt context.
        prompt: Prompt sent to the model.
        tools: Tool specs exposed to the model.

    Returns:
        One or more normalized model decisions.
    """
    select_tools = getattr(selector, "select_tools", None)
    if callable(select_tools):
        multi_selector = cast(
            Callable[
                ...,
                Awaitable[tuple[BattleTestModelDecision, ...]],
            ],
            select_tools,
        )
        return await multi_selector(
            profile=profile,
            scenario=scenario,
            prompt=prompt,
            tools=tools,
        )
    return (
        await selector.select_tool(
            profile=profile,
            scenario=scenario,
            prompt=prompt,
            tools=tools,
        ),
    )


def _empty_decision(
    scenario: BattleTestScenario,
    prompt: str,
    *,
    assistant_message: str | None = None,
) -> BattleTestModelDecision:
    """Return an empty decision for a missing expected multi-call route."""
    return BattleTestModelDecision(
        scenario_id=scenario.id,
        prompt=prompt,
        assistant_message=assistant_message,
        unsupported_explained=(
            scenario.grade is BattleTestGrade.MUST_EXPLAIN_UNSUPPORTED
            and _text_explains_unsupported_capability(assistant_message)
        ),
    )


def _first_assistant_message(decisions: tuple[BattleTestModelDecision, ...]) -> str | None:
    """Return the first non-empty assistant message from model decisions.

    Args:
        decisions: Normalized tool-selection decisions.

    Returns:
        First assistant message, if the provider returned one.
    """
    for decision in decisions:
        if decision.assistant_message:
            return decision.assistant_message
    return None


def _multi_call_prompt(prompt: str, *, expected_count: int) -> str:
    """Render a single-message multi-ask prompt with routing-count guidance.

    Args:
        prompt: Original user prompt.
        expected_count: Number of independent route decisions expected.

    Returns:
        Prompt text for the selector. The guidance gives the model the expected
        number of ordered decisions without revealing the intended tools.
    """
    return (
        f"{prompt}\n\n"
        "Battle-test routing requirement: this single user message requires "
        f"{expected_count} ordered routing decisions. Return exactly "
        f"{expected_count} ordered tool or sentinel calls, one per requested action. "
        "Do not answer in plain text only."
    )


async def _capture_decision_transcript(
    *,
    mcp_client: BattleTestMcpClient,
    scenario: BattleTestScenario,
    prompt: str,
    decision: BattleTestModelDecision,
) -> BattleTestTranscript:
    """Capture a transcript from a preselected model decision.

    Args:
        mcp_client: MCP client used to execute real tool calls.
        scenario: Expected scenario for the captured transcript.
        prompt: User prompt to record.
        decision: Model-selected route or sentinel decision.

    Returns:
        A battle-test transcript.
    """
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


def _conversation_prompt(
    current_prompt: str,
    history: tuple[BattleTestTranscript, ...],
) -> str:
    """Render prior turns into a deterministic selector prompt.

    Args:
        current_prompt: Current user turn.
        history: Captured prior turns.

    Returns:
        Prompt string containing prior user prompts and assistant/tool outcomes.
    """
    if not history:
        return current_prompt
    lines = ["Previous conversation context:"]
    for transcript in history:
        lines.append(f"User: {transcript.prompt}")
        if transcript.selected_tool is not None:
            lines.append(f"Assistant/tool: called {transcript.selected_tool}")
            response_summary = _history_response_summary(transcript.response)
            if response_summary is not None:
                lines.append(f"Tool response: {response_summary}")
        elif transcript.unsupported_explained:
            lines.append("Assistant/tool: explained unsupported capability")
        elif transcript.clarified:
            lines.append("Assistant/tool: asked for clarification")
        elif transcript.assistant_message:
            lines.append(f"Assistant: {transcript.assistant_message}")
    lines.append(f"Current user: {current_prompt}")
    return "\n".join(lines)


def _history_response_summary(response: JsonValue) -> str | None:
    """Return a compact JSON summary for prior tool results in selector prompts.

    Args:
        response: Captured MCP response from a previous turn.

    Returns:
        A truncated JSON string, or `None` when there is no response to expose.
    """
    if response is None:
        return None
    summary = json.dumps(response, sort_keys=True)
    if len(summary) <= 1200:
        return summary
    return f"{summary[:1197]}..."


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
    max_cases: int | None = None,
    sample_seed: int = 0,
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
        max_cases: Optional deterministic cap on evaluated cases.
        sample_seed: Seed used when sampling with `max_cases`.
        environment: Optional target environment label.
        started_at: Optional ISO-like run timestamp.
        notes: Optional notes stored in each artifact.

    Returns:
        One run artifact per model profile.
    """
    scenario_corpus = sample_battle_test_scenarios(
        _resolve_prompt_variant_corpus(
            scenarios=scenarios,
            all_prompt_variants=all_prompt_variants,
        ),
        max_cases=max_cases,
        sample_seed=sample_seed,
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


async def run_ai_model_profile_conversation_battle_tests(
    *,
    mcp_client: BattleTestMcpClient,
    oracle: ReadOnlyBattleTestOracle,
    selectors: SelectorMap,
    run_id_prefix: str,
    client: str,
    profiles: tuple[BattleTestModelProfile, ...] | None = None,
    conversations: tuple[BattleTestConversationScenario, ...] | None = None,
    kind: BattleTestConversationKind | None = None,
    artifact_directory: Path | None = None,
    max_cases: int | None = None,
    sample_seed: int = 0,
    chain_depth: int | None = None,
    environment: str | None = None,
    started_at: str | None = None,
    notes: tuple[str, ...] = (),
) -> tuple[BattleTestRunArtifact, ...]:
    """Run chained or multi-ask battle tests for each model profile.

    Args:
        mcp_client: MCP client used to execute model-selected tools.
        oracle: Direct API oracle used to evaluate MCP responses.
        selectors: Provider-specific AI selectors.
        run_id_prefix: Shared run prefix for sibling profile artifacts.
        client: Client or harness label.
        profiles: Optional profile list. Defaults to the standard model set.
        conversations: Optional conversation corpus. Defaults to read-only
            chained scenarios.
        kind: Optional conversation kind filter.
        artifact_directory: Optional output directory for JSON artifacts.
        max_cases: Optional deterministic cap on conversation cases.
        sample_seed: Seed used when sampling with `max_cases`.
        chain_depth: Optional max number of turns kept per conversation.
        environment: Optional target environment label.
        started_at: Optional ISO-like run timestamp.
        notes: Optional notes stored in each artifact.

    Returns:
        One run artifact per model profile, with turn-level and chain-level
        evaluations.
    """
    conversation_corpus = conversations or read_only_battle_test_conversations(kind)
    if chain_depth is not None:
        conversation_corpus = tuple(
            conversation.model_copy(update={"turns": conversation.turns[:chain_depth]})
            for conversation in conversation_corpus
        )
    conversation_corpus = sample_battle_test_conversations(
        conversation_corpus,
        max_cases=max_cases,
        sample_seed=sample_seed,
    )
    scenario_corpus = flatten_battle_test_conversations(conversation_corpus)
    artifacts: list[BattleTestRunArtifact] = []
    for profile in profiles or battle_test_model_profiles():
        selector = selectors.get(profile.provider)
        if selector is None:
            raise RuntimeError(
                f"No battle-test selector configured for provider {profile.provider}."
            )
        conversation_transcripts = tuple(
            [
                await capture_ai_selected_conversation_transcript(
                    selector=selector,
                    profile=profile,
                    conversation=conversation,
                    mcp_client=mcp_client,
                )
                for conversation in conversation_corpus
            ]
        )
        turn_transcripts = tuple(
            transcript
            for conversation_transcript in conversation_transcripts
            for transcript in conversation_transcript.turn_transcripts
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
            turn_transcripts,
            metadata=metadata,
            scenarios=scenario_corpus,
        )
        conversation_evaluations = tuple(
            [
                await _evaluate_captured_conversation(
                    oracle=oracle,
                    conversation=conversation,
                    transcripts=conversation_transcripts,
                )
                for conversation in conversation_corpus
            ]
        )
        artifact = artifact.model_copy(
            update={"conversation_evaluations": conversation_evaluations}
        )
        if artifact_directory is not None:
            write_battle_test_run_artifact(
                artifact,
                artifact_directory / f"{metadata.run_id}.json",
            )
        artifacts.append(artifact)
    return tuple(artifacts)


async def _evaluate_captured_conversation(
    *,
    oracle: ReadOnlyBattleTestOracle,
    conversation: BattleTestConversationScenario,
    transcripts: tuple[BattleTestConversationTranscript, ...],
) -> BattleTestConversationEvaluation:
    """Evaluate one captured conversation from a transcript tuple."""
    transcript_by_id = {transcript.conversation_id: transcript for transcript in transcripts}
    return await evaluate_battle_test_conversation(
        oracle,
        conversation,
        transcript_by_id[conversation.id],
    )


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
    return _openai_decisions_from_response(
        scenario=scenario,
        prompt=prompt,
        payload=payload,
    )[0]


def _openai_decisions_from_response(
    *,
    scenario: BattleTestScenario,
    prompt: str,
    payload: Mapping[str, object],
) -> tuple[BattleTestModelDecision, ...]:
    """Parse all OpenAI Responses route-selection tool calls."""
    output = payload.get("output")
    decisions: list[BattleTestModelDecision] = []
    if isinstance(output, list):
        for item in output:
            if isinstance(item, Mapping) and item.get("type") == "function_call":
                name = item.get("name")
                if isinstance(name, str):
                    decisions.append(
                        _decision_from_tool_call(
                            scenario=scenario,
                            prompt=prompt,
                            tool_name=name,
                            raw_arguments=item.get("arguments"),
                            fallback_message=_openai_text(payload),
                        )
                    )
    if decisions:
        return tuple(decisions)
    message = _openai_text(payload)
    return (
        BattleTestModelDecision(
            scenario_id=scenario.id,
            prompt=prompt,
            assistant_message=message,
            unsupported_explained=(
                scenario.grade is BattleTestGrade.MUST_EXPLAIN_UNSUPPORTED
                and _text_explains_unsupported_capability(message)
            ),
        ),
    )


def _anthropic_decision_from_response(
    *,
    scenario: BattleTestScenario,
    prompt: str,
    payload: Mapping[str, object],
) -> BattleTestModelDecision:
    """Parse an Anthropic Messages route-selection response."""
    return _anthropic_decisions_from_response(
        scenario=scenario,
        prompt=prompt,
        payload=payload,
    )[0]


def _anthropic_decisions_from_response(
    *,
    scenario: BattleTestScenario,
    prompt: str,
    payload: Mapping[str, object],
) -> tuple[BattleTestModelDecision, ...]:
    """Parse all Anthropic Messages route-selection tool calls."""
    content = payload.get("content")
    text = _anthropic_text(payload)
    decisions: list[BattleTestModelDecision] = []
    if isinstance(content, list):
        for item in content:
            if isinstance(item, Mapping) and item.get("type") == "tool_use":
                name = item.get("name")
                if isinstance(name, str):
                    decisions.append(
                        _decision_from_tool_call(
                            scenario=scenario,
                            prompt=prompt,
                            tool_name=name,
                            raw_arguments=item.get("input"),
                            fallback_message=text,
                        )
                    )
    if decisions:
        return tuple(decisions)
    return (
        BattleTestModelDecision(
            scenario_id=scenario.id,
            prompt=prompt,
            assistant_message=text,
            unsupported_explained=(
                scenario.grade is BattleTestGrade.MUST_EXPLAIN_UNSUPPORTED
                and _text_explains_unsupported_capability(text)
            ),
        ),
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


def _text_explains_unsupported_capability(message: str | None) -> bool:
    """Return whether assistant text explains an unsupported capability.

    Args:
        message: Provider text response to inspect.

    Returns:
        `True` when the text appears to explain that notes or another capability
        cannot be served by the current MCP/API surface.
    """
    if not message:
        return False
    lowered = message.lower()
    unsupported_phrases = (
        "not support",
        "doesn't support",
        "does not support",
        "unsupported",
        "can't",
        "cannot",
        "not able",
        "does not expose",
        "don't have access",
    )
    capability_terms = ("note", "api", "mcp", "capability")
    return any(phrase in lowered for phrase in unsupported_phrases) and any(
        term in lowered for term in capability_terms
    )


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
