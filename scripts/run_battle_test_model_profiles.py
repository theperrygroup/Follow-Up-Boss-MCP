"""Run read-only MCP battle tests against configured AI model profiles."""

from __future__ import annotations

import argparse
import asyncio
import json
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol, cast

from followupboss_mcp.battle_test_ai import (
    battle_test_ai_selectors_from_env,
    load_env_file,
    run_ai_model_profile_battle_tests,
    run_ai_model_profile_conversation_battle_tests,
)
from followupboss_mcp.battle_tests import (
    BattleTestConversationKind,
    BattleTestRunArtifact,
    ReadOnlyBattleTestOracle,
    battle_test_model_profile_by_id,
    expanded_battle_test_conversations,
    expanded_read_only_battle_test_scenarios,
    smart_list_grounding_battle_test_conversations,
    smart_list_grounding_battle_test_scenarios,
)
from followupboss_mcp.config import FollowUpBossSettings
from followupboss_mcp.http_client import FollowUpBossAsyncClient
from followupboss_mcp.mcp_server import create_server
from followupboss_mcp.models.common import JsonValue
from followupboss_mcp.tenant_runtime import build_service_bundle


class FastMcpCallable(Protocol):
    """Protocol for the MCPServer tool-calling surface used by this script."""

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> object:
        """Call one registered MCP tool."""


class FastMcpBattleTestClient:
    """Small adapter exposing MCPServer `call_tool()` through the battle-test protocol."""

    def __init__(self, server: FastMcpCallable) -> None:
        """Initialize the adapter.

        Args:
            server: MCPServer object returned by `create_server()`.
        """
        self._server = server

    async def call_tool(
        self,
        name: str,
        arguments: Mapping[str, JsonValue] | None = None,
    ) -> object:
        """Call one registered MCPServer tool.

        Args:
            name: MCP tool name.
            arguments: Optional JSON-compatible tool arguments.

        Returns:
            The structured tool response returned by MCPServer.
        """
        result = await self._server.call_tool(name, dict(arguments or {}))
        decoded_result = _decode_fastmcp_result(result)
        return decoded_result if decoded_result is not None else result


def _decode_fastmcp_result(result: object) -> JsonValue:
    """Decode common MCPServer tool result shapes into JSON payloads.

    Args:
        result: Raw `MCPServer.call_tool()` result.

    Returns:
        Decoded JSON payload when the result is structured or JSON text,
        otherwise `None`.
    """
    if isinstance(result, dict):
        return result
    if isinstance(result, tuple) and len(result) == 2 and isinstance(result[1], dict):
        return result[1]
    if isinstance(result, Sequence) and not isinstance(result, str | bytes | bytearray):
        for item in result:
            text = getattr(item, "text", None)
            if isinstance(text, str):
                parsed = json.loads(text)
                if _is_json_value(parsed):
                    return cast(JsonValue, parsed)
    return None


def _is_json_value(value: object) -> bool:
    """Return whether a value conforms to the project JSON type.

    Args:
        value: Candidate value.

    Returns:
        `True` when `value` can be treated as `JsonValue`.
    """
    if value is None or isinstance(value, bool | int | float | str):
        return True
    if isinstance(value, list):
        return all(_is_json_value(item) for item in value)
    if isinstance(value, dict):
        return all(isinstance(key, str) and _is_json_value(item) for key, item in value.items())
    return False


def build_parser() -> argparse.ArgumentParser:
    """Build the battle-test runner argument parser.

    Returns:
        Configured parser for the model-profile runner.
    """
    parser = argparse.ArgumentParser(
        description="Run read-only MCP battle tests through GPT-5.5 low reasoning and Sonnet 4.6.",
    )
    parser.add_argument(
        "--env-file",
        default=".env",
        type=Path,
        help="Environment file to load before resolving API keys.",
    )
    parser.add_argument(
        "--artifact-dir",
        default=Path("docs/planning/mcp-intent-hardening/execution/run-artifacts"),
        type=Path,
        help="Directory where profile-specific JSON artifacts should be written.",
    )
    parser.add_argument(
        "--run-id-prefix",
        default=None,
        help="Shared run ID prefix. Defaults to a UTC timestamp.",
    )
    parser.add_argument(
        "--client-label",
        default="local-fastmcp-ai",
        help="Client label stored in run metadata.",
    )
    parser.add_argument(
        "--environment",
        default="local",
        help="Environment label stored in run metadata.",
    )
    parser.add_argument(
        "--prompt-variant-index",
        default=0,
        type=int,
        help="Prompt variant index to run for each scenario.",
    )
    parser.add_argument(
        "--all-prompt-variants",
        action="store_true",
        help="Run every prompt variant as a separate evaluated scenario case.",
    )
    parser.add_argument(
        "--corpus",
        choices=(
            "read-only",
            "read-expanded",
            "chains",
            "chains-expanded",
            "multi-ask",
            "multi-ask-expanded",
            "all",
            "all-expanded",
            "smart-list-grounding",
            "mutation-safe",
            "boundary",
        ),
        default="read-only",
        help="Corpus tier to run. Defaults to the original read-only single-turn corpus.",
    )
    parser.add_argument(
        "--max-cases",
        default=None,
        type=int,
        help="Deterministically cap the number of scenario or conversation cases.",
    )
    parser.add_argument(
        "--sample-seed",
        default=0,
        type=int,
        help="Seed used when --max-cases samples a corpus.",
    )
    parser.add_argument(
        "--chain-depth",
        default=None,
        type=int,
        help="Maximum number of turns to keep per chained conversation.",
    )
    parser.add_argument(
        "--all-variation-families",
        action="store_true",
        help="Alias for running every read-only prompt variation family.",
    )
    parser.add_argument(
        "--profile",
        action="append",
        choices=("gpt-5.5-low-reasoning", "sonnet-4.6"),
        help="Model profile ID to run. Repeat to run multiple profiles; defaults to both.",
    )
    return parser


async def run(argv: Sequence[str] | None = None) -> int:
    """Run the model-profile battle-test command.

    Args:
        argv: Optional CLI arguments.

    Returns:
        Process exit code.
    """
    parser = build_parser()
    args = parser.parse_args(argv)
    load_env_file(args.env_file)
    selectors = battle_test_ai_selectors_from_env()
    profiles = (
        tuple(battle_test_model_profile_by_id(profile_id) for profile_id in args.profile)
        if args.profile
        else None
    )
    settings = FollowUpBossSettings()
    started_at = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    base_run_id_prefix = (
        args.run_id_prefix or f"{args.corpus}-{started_at.replace(':', '').replace('-', '')}"
    )
    async with FollowUpBossAsyncClient(settings) as client:
        services = build_service_bundle(client)
        server = create_server(settings, client=client)
        mcp_client = FastMcpBattleTestClient(server)
        oracle = ReadOnlyBattleTestOracle(services)
        artifacts: list[BattleTestRunArtifact] = []
        if args.corpus in {"read-only", "read-expanded", "all", "all-expanded"}:
            read_expanded = args.corpus in {"read-expanded", "all-expanded"}
            artifacts.extend(
                await run_ai_model_profile_battle_tests(
                    mcp_client=mcp_client,
                    oracle=oracle,
                    selectors=selectors,
                    run_id_prefix=(
                        base_run_id_prefix
                        if args.corpus in {"read-only", "read-expanded"}
                        else f"{base_run_id_prefix}-read-only"
                    ),
                    client=args.client_label,
                    profiles=profiles,
                    artifact_directory=args.artifact_dir,
                    prompt_variant_index=args.prompt_variant_index,
                    all_prompt_variants=args.all_prompt_variants or args.all_variation_families,
                    max_cases=args.max_cases,
                    sample_seed=args.sample_seed,
                    environment=args.environment,
                    started_at=started_at,
                    notes=(
                        ("read-expanded" if read_expanded else "read-only"),
                        "ai-selected-tools",
                    ),
                    scenarios=(
                        expanded_read_only_battle_test_scenarios() if read_expanded else None
                    ),
                )
            )
        if args.corpus == "smart-list-grounding":
            artifacts.extend(
                await run_ai_model_profile_battle_tests(
                    mcp_client=mcp_client,
                    oracle=oracle,
                    selectors=selectors,
                    run_id_prefix=f"{base_run_id_prefix}-single-turn",
                    client=args.client_label,
                    profiles=profiles,
                    artifact_directory=args.artifact_dir,
                    prompt_variant_index=args.prompt_variant_index,
                    all_prompt_variants=args.all_prompt_variants or args.all_variation_families,
                    max_cases=args.max_cases,
                    sample_seed=args.sample_seed,
                    environment=args.environment,
                    started_at=started_at,
                    notes=("smart-list-grounding", "single-turn"),
                    scenarios=smart_list_grounding_battle_test_scenarios(),
                )
            )
            artifacts.extend(
                await run_ai_model_profile_conversation_battle_tests(
                    mcp_client=mcp_client,
                    oracle=oracle,
                    selectors=selectors,
                    run_id_prefix=f"{base_run_id_prefix}-conversations",
                    client=args.client_label,
                    profiles=profiles,
                    conversations=smart_list_grounding_battle_test_conversations(),
                    artifact_directory=args.artifact_dir,
                    max_cases=args.max_cases,
                    sample_seed=args.sample_seed,
                    chain_depth=args.chain_depth,
                    environment=args.environment,
                    started_at=started_at,
                    notes=("smart-list-grounding", "conversations"),
                )
            )
        if args.corpus in {
            "chains",
            "chains-expanded",
            "multi-ask",
            "multi-ask-expanded",
            "all",
            "all-expanded",
        }:
            kind = None
            if args.corpus in {"chains", "chains-expanded"}:
                kind = BattleTestConversationKind.MULTI_TURN
            elif args.corpus in {"multi-ask", "multi-ask-expanded"}:
                kind = BattleTestConversationKind.MULTI_ASK
            conversations = (
                expanded_battle_test_conversations(kind)
                if args.corpus in {"chains-expanded", "multi-ask-expanded", "all-expanded"}
                else None
            )
            artifacts.extend(
                await run_ai_model_profile_conversation_battle_tests(
                    mcp_client=mcp_client,
                    oracle=oracle,
                    selectors=selectors,
                    run_id_prefix=(
                        base_run_id_prefix
                        if args.corpus
                        in {"chains", "chains-expanded", "multi-ask", "multi-ask-expanded"}
                        else f"{base_run_id_prefix}-conversations"
                    ),
                    client=args.client_label,
                    profiles=profiles,
                    kind=kind,
                    conversations=conversations,
                    artifact_directory=args.artifact_dir,
                    max_cases=args.max_cases,
                    sample_seed=args.sample_seed,
                    chain_depth=args.chain_depth,
                    environment=args.environment,
                    started_at=started_at,
                    notes=(args.corpus, "ai-selected-tools", "chained"),
                )
            )
        if args.corpus in {"mutation-safe", "boundary"}:
            print(f"{args.corpus}: SKIP (no live runnable corpus is encoded for this tier yet)")
    for artifact in artifacts:
        profile_id = (
            artifact.metadata.model_profile.id if artifact.metadata.model_profile else "unknown"
        )
        status = "PASS" if artifact.summary.overall_passed else "FAIL"
        breakdown = _format_failure_breakdown(artifact.summary.failure_category_counts)
        print(
            f"{profile_id}: {status} ({artifact.summary.passed_scenarios}/"
            f"{artifact.summary.total_scenarios} passed){breakdown}"
        )
    return 0 if all(artifact.summary.overall_passed for artifact in artifacts) else 1


def _format_failure_breakdown(counts: Mapping[str, int]) -> str:
    """Format compact failure category counts for command output.

    Args:
        counts: Failure category counts from a run artifact summary.

    Returns:
        Empty string when no failures were categorized, otherwise a compact
        parenthesized breakdown.
    """
    if not counts:
        return ""
    parts = [f"{category}={count}" for category, count in sorted(counts.items())]
    return f" [{', '.join(parts)}]"


def main(argv: Sequence[str] | None = None) -> int:
    """Synchronous command entrypoint.

    Args:
        argv: Optional CLI arguments.

    Returns:
        Process exit code.
    """
    return asyncio.run(run(argv))


if __name__ == "__main__":
    raise SystemExit(main())
