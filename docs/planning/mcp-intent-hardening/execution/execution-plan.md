# MCP Intent Hardening Execution Plan

This file is the checked-in ledger for the planning set. It records what has
landed, what is blocked, and what still remains open.

## 1. Ledger Scope

- This ledger records checked-in proof.
- Use `roadmap.md` for baseline dependency order.
- Use focused trackers for current readiness detail.

## 1A. How To Read This Ledger Now

- This file is the ledger, not proof that intent hardening is fully live.
- The strongest checked-in planning proof is the scaffold under
  `docs/planning/mcp-intent-hardening/`.
- The strongest checked-in runtime proof is the existing intent-helper surface
  in `src/followupboss_mcp/mcp_registration.py` and
  `src/followupboss_mcp/mcp_tools.py`.
- The biggest remaining gap is a complete intent taxonomy with matching tests,
  public docs, encoded vague-prompt scenarios, API-oracle checks, and live
  validation scenarios.

## 2. Current Checked-In Status

- Planning root created for MCP intent hardening.
- Foundation docs define the intent boundary and source-of-truth hierarchy.
- Registered tool descriptions now make the existing latest-lead and owned-task
  helpers more authoritative for common user-owned intents.
- Person and task update/delete descriptions now require explicit IDs rather
  than vague natural-language inference.
- Public MCP docs and the live validation checklist now include the first
  intent-routing and explicit-ID validation guidance.
- Trackers record that runtime hardening is still in progress, not complete.
- Execution docs define the active sequence and baseline roadmap.
- Battle-test planning now defines how vague chatbot prompts should be verified
  through observed MCP routing and direct Follow Up Boss API oracle checks.
- Read-only battle-test code now encodes the first `BT-READ-*` scenarios with
  20 prompt variants each and can evaluate captured transcripts against typed
  service oracles for implemented read-only cases.
- Battle-test run artifact helpers now summarize evaluated transcripts, missing
  scenarios, unknown transcript IDs, and formatted JSON evidence output.
- Battle-test run metadata now carries model profiles, with default separate
  targets for GPT-5.5 low reasoning and Sonnet 4.7.
- An AI-backed profile runner can now call OpenAI Responses for GPT-5.5 low
  reasoning and Anthropic Messages for Sonnet 4.7, execute selected local FastMCP
  tools, expand all prompt variants, and write separate artifacts.

## 3. Current Blockers

- The first public intent-to-tool guide exists, but the full MCP surface has not
  been classified by routing risk.
- Mutation safety language has only been hardened for person and task
  update/delete tools.
- Future helper candidates have not been ranked against actual ambiguous user
  requests.
- Non-read-only vague chatbot prompt scenarios have not been encoded into a
  repeatable corpus.
- Live AI/API-backed battle-test artifacts exist, but currently record failures
  and are not readiness evidence.
- `BT-READ-004` remains route-only pending until future-task routing is decided.
- Live validation scenarios should wait until the offline contract is expanded.

## 4. Completed Planning Or Landed Proof

### 2026-05-08 - Planning Scaffold

- Checked-in proof:
  - `docs/planning/mcp-intent-hardening/README.md`
  - `docs/planning/mcp-intent-hardening/ARTIFACT_PATH_INDEX.md`
  - `docs/planning/mcp-intent-hardening/foundation/intent-boundary-adr.md`
  - `docs/planning/mcp-intent-hardening/execution/intent-hardening-plan.md`
- Result:
  - The initiative now has one canonical planning root, one active plan, and
    focused trackers for routing and safety validation.

### Existing Runtime Anchors Observed During Scaffold

- Checked-in proof:
  - `src/followupboss_mcp/mcp_registration.py`
  - `src/followupboss_mcp/mcp_tools.py`
  - `tests/mcp/test_mcp_tools_server_cli.py`
- Result:
  - Existing helper anchors for latest assigned lead and authenticated-user task
    due buckets can be treated as starting points for the hardening plan.

### 2026-05-08 - Phase 01 Description Hardening

- Checked-in proof:
  - `docs/planning/mcp-intent-hardening/execution/intent_PHASE_01_description_hardening.md`
  - `src/followupboss_mcp/mcp_registration.py`
  - `tests/mcp/test_mcp_tools_server_cli.py`
  - `docs/mcp-usage.md`
  - `docs/mcp-validation-checklist.md`
- Result:
  - Broad people and task tools now steer common owned intents to existing
    narrow helpers.
  - Existing helper descriptions now state that authenticated-user identity is
    resolved internally.
  - Person and task update/delete descriptions now require explicit IDs.

### 2026-05-18 - Phase 02 Battle-Test Planning

- Checked-in proof:
  - `docs/planning/mcp-intent-hardening/foundation/battle-test-verification-adr.md`
  - `docs/planning/mcp-intent-hardening/execution/intent-battle-test-plan.md`
  - `docs/planning/mcp-intent-hardening/trackers/battle-test-readiness.md`
  - `docs/planning/mcp-intent-hardening/execution/intent_PHASE_02_battle_test_planning.md`
- Result:
  - The initiative now has a prompt-to-tool-to-API verification contract and a
    seed corpus for vague chatbot battle tests.
  - This is docs-only planning proof; no scenario harness or live battle-test
    run has landed.

### 2026-05-18 - Phase 03 Read-Only Battle-Test Schema

- Checked-in proof:
  - `src/followupboss_mcp/battle_tests.py`
  - `tests/unit/test_battle_tests.py`
  - `docs/planning/mcp-intent-hardening/execution/intent_PHASE_03_read_only_battle_test_schema.md`
- Result:
  - The first read-only vague-prompt corpus is machine-readable.
  - Captured transcripts can now be evaluated for expected MCP route, forbidden
    tools, direct API oracle agreement, unsupported note-search behavior, and
    missing authenticated-user identity.
  - This is not live run evidence; it is reusable evaluator code and focused
    unit proof.

### 2026-05-18 - Phase 04 Battle-Test Run Artifact Evaluator

- Checked-in proof:
  - `src/followupboss_mcp/battle_tests.py`
  - `tests/unit/test_battle_tests.py`
  - `docs/planning/mcp-intent-hardening/execution/intent_PHASE_04_run_artifact_evaluator.md`
- Result:
  - Captured transcripts can now be evaluated as a corpus and serialized as a
    JSON run artifact with aggregate pass/fail, missing-scenario, and
    unknown-transcript counts.
  - This is still not live run evidence; it is the persistence layer that a
    future client transcript runner should call.

### 2026-05-18 - Phase 05 Battle-Test Model Profile Matrix

- Checked-in proof:
  - `src/followupboss_mcp/battle_tests.py`
  - `tests/unit/test_battle_tests.py`
  - `docs/planning/mcp-intent-hardening/execution/intent_PHASE_05_model_profile_matrix.md`
- Result:
  - Battle-test run artifacts can now carry a model profile and be written as
    separate profile-specific JSON files.
  - The default comparison targets are `gpt-5.5-low-reasoning` and `sonnet-4.7`.
  - This is still not live run evidence; it is the artifact boundary needed
    before the client-backed run executes each model separately.

### 2026-05-18 - Phase 06 AI Model Profile Battle-Test Runner

- Checked-in proof:
  - `src/followupboss_mcp/battle_test_ai.py`
  - `tests/unit/test_battle_test_ai.py`
  - `scripts/run_battle_test_model_profiles.py`
  - `docs/planning/mcp-intent-hardening/execution/intent_PHASE_06_ai_model_profile_runner.md`
- Result:
  - The local runner can load AI API keys from `.env`, ask GPT-5.5 low reasoning
    and Sonnet 4.7 to select MCP routes, execute selected tools through a local
    FastMCP adapter, evaluate transcripts through the read-only oracle, and write
    sibling profile-specific artifacts.
  - All-variant mode expands the 5 read-only scenarios into 100 prompt cases per
    model profile.
  - Initial live artifacts exist but record failures; they should drive
    hardening rather than readiness claims.

## 5. Current Work Queue

| Task | Status | Why it is still open |
| --- | --- | --- |
| Inventory and classify existing intent-like helpers | In progress | Initial anchors are documented, but the full MCP surface has not been classified. |
| Harden generic descriptions around narrow helpers | In progress | Highest-confidence people and task wording has landed; a full-surface pass remains open. |
| Add or reject future intent helpers | Planned | Helper candidates need ranking by ambiguity, safety, and duplication risk. |
| Expand offline validation | In progress | Registered metadata assertions landed for the first slice; future helper or safety wording work still needs coverage. |
| Update public docs and validation checklist | In progress | First intent-routing and explicit-ID guidance landed; future helper decisions still need doc sync. |
| Encode vague-prompt battle-test corpus | In progress | `BT-READ-001` through `BT-READ-005` are encoded; mutation, safety, and boundary prompt batches remain planned. |
| Build battle-test API oracle harness | In progress | Read-only typed service oracle helpers, model-profile run metadata, run artifact writing, and the AI-backed read-only runner exist, but live run evidence, cleanup reporting, and mutation oracles still need implementation. |
| Run live intent validation | Planned | Should happen only after offline contract and docs are ready. |

## 6. Current Conclusion

- MCP intent hardening has a planning home, a concrete active sequence, and a
  focused battle-test plan, and the first read-only evaluator. It is not done;
  the next implementation slice should execute the checked-in AI runner against
  the approved read-only environment and record sibling dated artifacts before
  mutation batches run.
