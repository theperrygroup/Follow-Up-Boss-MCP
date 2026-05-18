# Intent Phase 06: AI Model Profile Battle-Test Runner Proof

## Scope

This proof file records the first AI-backed runner slice for vague-prompt MCP
battle testing. It covers provider-specific tool-selection calls for GPT-5.5 low
reasoning and Sonnet 4.7, local `.env` loading for API keys, FastMCP tool
execution, and separate profile-specific artifact writing. It does not claim
that a live battle-test run has been executed yet.

## Checked-In Proof

| Area | Proof |
| --- | --- |
| AI route selectors | `src/followupboss_mcp/battle_test_ai.py` defines OpenAI Responses and Anthropic Messages selectors that convert model tool calls into `BattleTestTranscript` data. |
| Profile-specific runner | `run_ai_model_profile_battle_tests()` runs each model profile separately, can expand every prompt variant into its own case, and writes sibling artifacts when an output directory is provided. |
| Local command | `scripts/run_battle_test_model_profiles.py` loads `.env`, builds a local FastMCP client, and runs the checked-in profile matrix with either one variant or `--all-prompt-variants`. |
| Focused tests | `tests/unit/test_battle_test_ai.py` mocks OpenAI and Anthropic API payloads, verifies GPT-5.5 low reasoning payloads, verifies Sonnet 4.7 tool-use parsing, and checks separate artifact output. |

## Behavior Covered

- GPT-5.5 low-reasoning runs include `reasoning: {"effort": "low"}` in the
  OpenAI Responses payload.
- Sonnet 4.7 runs use the Anthropic Messages tool-use shape and remain separate
  from GPT evidence.
- Models receive a read-only MCP tool menu plus sentinel tools for clarification
  and unsupported API capability explanations.
- The read-only corpus contains 20 prompt variants for each `BT-READ-*` scenario,
  and all-variant runs expand those into 100 scenario cases per model profile.
- Selected real MCP tools are executed through a local FastMCP adapter before
  direct API oracle evaluation.
- MCP tool execution errors are preserved as failed transcripts so one bad model
  argument does not abort the sibling profile run.
- Clarification and unsupported sentinel decisions produce transcripts without
  executing a real MCP tool.

## Remaining Gaps

- Live AI/API-backed run artifacts currently show failures; they should be used
  for hardening, not treated as readiness proof.
- Only the first read-only scenario corpus is executable through this runner.
- `BT-READ-004` remains route-only pending until the future-task oracle contract
  is finalized.
- Mutation, destructive-safety, and boundary prompt batches remain unencoded.

## Conclusion

Phase 06 makes the model-profile battle-test loop executable with API keys from
`.env`. The next slice should run the command against the intended sandbox or
approved read-only account, inspect the profile-specific JSON artifacts, and
refresh this ledger with observed run evidence rather than reusable runner
capability.
