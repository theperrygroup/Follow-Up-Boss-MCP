# Intent Phase 04: Battle-Test Run Artifact Evaluator Proof

## Scope

This proof file records the second implementation slice for vague-prompt MCP
battle testing. It covers reusable run metadata, aggregate summaries, run
artifact serialization, missing scenario detection, and unknown transcript
detection. It does not claim that a live MCP client or chatbot transcript
capture runner exists yet.

## Checked-In Proof

| Area | Proof |
| --- | --- |
| Run metadata and summaries | `src/followupboss_mcp/battle_tests.py` defines `BattleTestRunMetadata`, `BattleTestRunSummary`, and `BattleTestRunArtifact`. |
| Corpus-level evaluation | `evaluate_battle_test_run()` evaluates captured transcripts against the expected scenario corpus and records missing or unknown scenario IDs. |
| Artifact serialization | `write_battle_test_run_artifact()` writes formatted JSON artifacts and creates parent directories. |
| Focused tests | `tests/unit/test_battle_tests.py` covers aggregate summaries, artifact writing, missing transcripts, unknown transcripts, and all-pass run behavior. |
| Validation proof | Focused Ruff, pytest, mypy, and coverage commands passed for the battle-test module and tests. |

## Behavior Covered

- Run artifacts include metadata, summary counts, per-scenario evaluations,
  missing scenario IDs, and unknown transcript scenario IDs.
- A run passes only when all expected scenarios are evaluated, all evaluations
  pass, and no unknown transcripts are present.
- Missing transcripts and unknown transcripts are preserved as artifact data
  instead of being silently ignored.
- Artifact writing is deterministic enough for future dated run evidence.

## Remaining Gaps

- No real MCP client transcript capture runner exists yet.
- No command-line or CI target invokes the run artifact evaluator yet.
- No live Follow Up Boss battle-test run has been executed.
- Mutation, destructive-safety, and boundary prompt batches remain unencoded.

## Validation Commands

```bash
uv run ruff format "src/followupboss_mcp/battle_tests.py" "tests/unit/test_battle_tests.py"
uv run ruff check "src/followupboss_mcp/battle_tests.py" "tests/unit/test_battle_tests.py"
uv run pytest "tests/unit/test_battle_tests.py"
uv run mypy --no-incremental --explicit-package-bases "src/followupboss_mcp/battle_tests.py" "tests/unit/test_battle_tests.py"
uv run coverage run --branch -m pytest "tests/unit/test_battle_tests.py"
uv run coverage report --include="src/followupboss_mcp/battle_tests.py" --fail-under=100
```

## Conclusion

Phase 04 makes battle-test evidence persistable once a client runner can produce
`BattleTestTranscript` records. The next slice should capture tool choices and
arguments from a real MCP client session, then write a dated run artifact through
the checked-in evaluator.
