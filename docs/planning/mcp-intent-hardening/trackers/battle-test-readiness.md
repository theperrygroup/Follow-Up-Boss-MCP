# Battle-Test Readiness

## Purpose

This tracker follows whether vague chatbot prompts can be tested end-to-end:
natural-language request, MCP tool choice, MCP result, direct Follow Up Boss API
oracle, and cleanup.

## Current Snapshot

Snapshot date: `2026-05-18`

| Readiness lens | Status | Current answer |
| --- | --- | --- |
| Prompt corpus | In progress | `src/followupboss_mcp/battle_tests.py` now encodes `BT-READ-001` through `BT-READ-005`; mutation, safety, and boundary prompt batches remain planned. |
| Scenario grading | In progress | The grade enum and route evaluator are implemented for captured transcripts; more scenario families still need encoded assertions. |
| API oracle strategy | In progress | Read-only oracle helpers exist for latest lead, overdue tasks, today's tasks, unsupported note search, and route-only pending scenarios. |
| Fixture graph | Planned | Disposable people, tasks, deals, notes, appointments, campaigns, templates, and admin fixtures need deterministic setup and cleanup. |
| Transcript capture | In progress | `BattleTestTranscript` defines the captured data shape, and `src/followupboss_mcp/battle_test_ai.py` can convert AI-selected routes into transcripts through a local FastMCP adapter. No live transcript artifact has been produced yet. |
| Run artifact persistence | In progress | `BattleTestRunArtifact` and `write_battle_test_run_artifact()` can persist evaluated transcripts as JSON evidence; no live run artifact has been produced yet. |
| Model profile matrix | In progress | Default run profiles now exist for `gpt-5.5-low-reasoning` and `sonnet-4.7`; the local runner can invoke each provider separately and write separate artifacts. |
| Live battle-test run | Planned | No vague-prompt battle-test run has been executed or recorded. |

## Focus Areas

### Prompt Corpus

- Cover high-confidence helper intents with many natural-language variants.
- Include near-miss prompts that should clarify rather than call a broad tool.
- Include unsupported requests where the correct result is an honest limitation.
- Include mutation prompts that require explicit IDs before side effects.
- Keep `BT-READ-004` route-only until the future-task helper or canonical API
  filter is decided.

### API Oracle

- For implemented reads, compare MCP output against direct API queries for the
  same fixture or authenticated-user scope.
- For creates, verify the created object exists through direct API lookup and
  that cleanup can delete it.
- For updates, verify only the intended fixture changed.
- For deletes, verify the intended fixture is gone and unrelated fixtures still
  exist.
- For unsupported paths, verify no upstream side effect occurred.

### Safety Gates

- Do not run mutation or destructive prompt batches before read-only batches are
  stable.
- Do not treat a chatbot answer as passing without observed MCP tool selection.
- Do not use production data unless the scenario is read-only and explicitly
  approved for that account.
- Do not mark battle-test readiness complete without a repeatable run artifact
  produced from real MCP client transcripts.
- Do not combine GPT-5.5 low-reasoning and Sonnet 4.7 evidence into one pass or
  fail result; each model profile needs its own artifact.

## Open Questions

- Should the scenario corpus live as Markdown first, JSON/YAML first, or both?
- Which client should be the canonical chatbot runner: Cursor, MCP Inspector, a
  small local harness, or more than one client?
- Should the API oracle call the public Follow Up Boss API directly, or reuse
  the typed service layer so assertions share repository models?
- Which mutation domains are safe enough for the first live run after people and
  task fixtures?
- Should the local AI runner become the canonical harness, or should Cursor/MCP
  Inspector transcript capture also be recorded for comparison?

## Current Conclusion

Battle testing is now partially implemented for the first read-only corpus, run
artifact evaluation, profile-specific artifact separation, and an AI-backed
local runner. The next slice should execute a live read-only run for both default
model profiles and inspect the resulting sibling artifacts before mutation
batches are encoded.
