# Phase 05 - Battle-Test Model Profile Matrix

## Scope

This proof records the model-profile execution slice for MCP battle testing.
The goal is to allow the same scenario corpus to be evaluated separately for
GPT-5.5 low reasoning and Sonnet 4.7 runs without merging their evidence.

## Checked-In Proof

- `src/followupboss_mcp/battle_tests.py`
- `tests/unit/test_battle_tests.py`
- `docs/planning/mcp-intent-hardening/execution/intent-battle-test-plan.md`
- `docs/planning/mcp-intent-hardening/trackers/battle-test-readiness.md`

## What Landed

- `BattleTestModelProfile` and `BattleTestModelProvider` now define model run
  labels.
- The default battle-test model profiles are:
  - `gpt-5.5-low-reasoning`
  - `sonnet-4.7`
- `BattleTestRunMetadata` can carry the model profile used for a run.
- `build_model_profile_run_metadata()` suffixes a shared run ID prefix with the
  model profile ID.
- `evaluate_model_profile_battle_test_runs()` evaluates transcripts keyed by
  profile ID and can write one JSON artifact per profile.

## What This Does Not Prove

- No live chatbot run has been executed.
- No provider SDK integration is checked in.
- The profiles are run labels and artifact boundaries, not proof that either
  external model completed a scenario.

## Validation

- Focused unit tests cover profile lookup, metadata generation, and separate
  artifact writing for GPT-5.5 low reasoning and Sonnet 4.7.
- Focused linting and unit tests passed for the battle-test module and tests.
