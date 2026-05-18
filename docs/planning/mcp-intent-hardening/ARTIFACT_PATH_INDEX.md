# MCP Intent Hardening Artifact Path Index

## Purpose

- This file is the canonical naming and path index for the planning set.
- This file is not the current-status ledger.
- Future prompts should use this file instead of hardcoded path assumptions.

## Canonical Role Index

### Planning Root

- Actual repo path: `docs/planning/mcp-intent-hardening/`
- Already exists: `YES`
- Canonical for future prompts: `YES`
- Confidence: `High`
- Explanation: This is the first and only planning root for MCP intent hardening.

### Landing README

- Actual repo path: `docs/planning/mcp-intent-hardening/README.md`
- Already exists: `YES`
- Canonical for future prompts: `YES`
- Confidence: `High`
- Explanation: This file defines read order, precedence, and working rules.

### Artifact Path Index

- Actual repo path: `docs/planning/mcp-intent-hardening/ARTIFACT_PATH_INDEX.md`
- Already exists: `YES`
- Canonical for future prompts: `YES`
- Confidence: `High`
- Explanation: This file records canonical homes for planning artifacts.

### Foundation Directory

- Actual repo path: `docs/planning/mcp-intent-hardening/foundation/`
- Already exists: `YES`
- Canonical for future prompts: `YES`
- Confidence: `High`
- Explanation: Durable intent boundaries and source-of-truth rules live here.

### Source Of Truth Matrix

- Actual repo path: `docs/planning/mcp-intent-hardening/foundation/source-of-truth-matrix.md`
- Already exists: `YES`
- Canonical for future prompts: `YES`
- Confidence: `High`
- Explanation: This matrix maps planning docs, code, tests, and public docs to
  their authority for intent hardening.

### Intent Boundary ADR

- Actual repo path: `docs/planning/mcp-intent-hardening/foundation/intent-boundary-adr.md`
- Already exists: `YES`
- Canonical for future prompts: `YES`
- Confidence: `High`
- Explanation: This ADR defines which work belongs in this initiative.

### Battle-Test Verification ADR

- Actual repo path: `docs/planning/mcp-intent-hardening/foundation/battle-test-verification-adr.md`
- Already exists: `YES`
- Canonical for future prompts: `YES`
- Confidence: `High`
- Explanation: This ADR defines how vague chatbot prompts must be verified
  through observed MCP routing and direct Follow Up Boss API truth.

### Tracker Directory

- Actual repo path: `docs/planning/mcp-intent-hardening/trackers/`
- Already exists: `YES`
- Canonical for future prompts: `YES`
- Confidence: `High`
- Explanation: Current readiness and focused risk trackers live here.

### Master Readiness Tracker

- Actual repo path: `docs/planning/mcp-intent-hardening/trackers/readiness-overview.md`
- Already exists: `YES`
- Canonical for future prompts: `YES`
- Confidence: `High`
- Explanation: This tracker is the aggregate live planning status surface.

### Intent Routing Readiness Tracker

- Actual repo path: `docs/planning/mcp-intent-hardening/trackers/intent-routing-readiness.md`
- Already exists: `YES`
- Canonical for future prompts: `YES`
- Confidence: `High`
- Explanation: This tracker owns tool-selection and request-routing readiness.

### Safety Validation Readiness Tracker

- Actual repo path: `docs/planning/mcp-intent-hardening/trackers/safety-validation-readiness.md`
- Already exists: `YES`
- Canonical for future prompts: `YES`
- Confidence: `High`
- Explanation: This tracker owns fail-closed, mutation, and validation evidence.

### Battle-Test Readiness Tracker

- Actual repo path: `docs/planning/mcp-intent-hardening/trackers/battle-test-readiness.md`
- Already exists: `YES`
- Canonical for future prompts: `YES`
- Confidence: `High`
- Explanation: This tracker owns prompt corpus, transcript capture, API oracle,
  fixture, cleanup, and live battle-test readiness.

### Execution Directory

- Actual repo path: `docs/planning/mcp-intent-hardening/execution/`
- Already exists: `YES`
- Canonical for future prompts: `YES`
- Confidence: `High`
- Explanation: The live ledger, baseline roadmap, active plan, and future phase
  proof files live here.

### Execution Plan

- Actual repo path: `docs/planning/mcp-intent-hardening/execution/execution-plan.md`
- Already exists: `YES`
- Canonical for future prompts: `YES`
- Confidence: `High`
- Explanation: This is the checked-in ledger for completed proof and blockers.

### Roadmap

- Actual repo path: `docs/planning/mcp-intent-hardening/execution/roadmap.md`
- Already exists: `YES`
- Canonical for future prompts: `YES`
- Confidence: `High`
- Explanation: This records baseline sequencing and dependency order.

### Active Plan

- Actual repo path: `docs/planning/mcp-intent-hardening/execution/intent-hardening-plan.md`
- Already exists: `YES`
- Canonical for future prompts: `YES`
- Confidence: `High`
- Explanation: This is the canonical active plan for the current hardening
  sequence.

### Focused Battle-Test Plan

- Actual repo path: `docs/planning/mcp-intent-hardening/execution/intent-battle-test-plan.md`
- Already exists: `YES`
- Canonical for future prompts: `YES`
- Confidence: `High`
- Explanation: This is the focused execution artifact for vague chatbot prompt
  corpus design and API-oracle verification.

### Future Phase Proof Files

- Actual repo path: `docs/planning/mcp-intent-hardening/execution/intent_PHASE_##_<slug>.md`
- Already exists: `YES`
- Canonical for future prompts: `YES`
- Confidence: `High`
- Explanation: Add one proof file when a slice needs durable evidence beyond the
  aggregate execution ledger.

### Phase 01 Description Hardening Proof

- Actual repo path: `docs/planning/mcp-intent-hardening/execution/intent_PHASE_01_description_hardening.md`
- Already exists: `YES`
- Canonical for future prompts: `YES`
- Confidence: `High`
- Explanation: This file records the first checked-in implementation slice for
  MCP intent metadata and validation-doc hardening.

### Phase 02 Battle-Test Planning Proof

- Actual repo path: `docs/planning/mcp-intent-hardening/execution/intent_PHASE_02_battle_test_planning.md`
- Already exists: `YES`
- Canonical for future prompts: `YES`
- Confidence: `High`
- Explanation: This file records the docs-only planning slice for vague-prompt
  battle testing and API-oracle verification.

### Phase 03 Read-Only Battle-Test Schema Proof

- Actual repo path: `docs/planning/mcp-intent-hardening/execution/intent_PHASE_03_read_only_battle_test_schema.md`
- Already exists: `YES`
- Canonical for future prompts: `YES`
- Confidence: `High`
- Explanation: This file records the first reusable implementation slice for
  read-only battle-test scenario encoding and oracle evaluation.

### Phase 04 Battle-Test Run Artifact Evaluator Proof

- Actual repo path: `docs/planning/mcp-intent-hardening/execution/intent_PHASE_04_run_artifact_evaluator.md`
- Already exists: `YES`
- Canonical for future prompts: `YES`
- Confidence: `High`
- Explanation: This file records reusable run-artifact summary, serialization,
  missing-scenario, and unknown-transcript evaluator support.

### Phase 05 Battle-Test Model Profile Matrix Proof

- Actual repo path: `docs/planning/mcp-intent-hardening/execution/intent_PHASE_05_model_profile_matrix.md`
- Already exists: `YES`
- Canonical for future prompts: `YES`
- Confidence: `High`
- Explanation: This file records default GPT-5.5 low-reasoning and Sonnet 4.7
  battle-test profile labels and separate artifact boundaries.

### Phase 06 AI Model Profile Runner Proof

- Actual repo path: `docs/planning/mcp-intent-hardening/execution/intent_PHASE_06_ai_model_profile_runner.md`
- Already exists: `YES`
- Canonical for future prompts: `YES`
- Confidence: `High`
- Explanation: This file records the checked-in OpenAI/Anthropic route selector
  runner, local command, and remaining live-run evidence gap.

## Runtime Artifact Homes

These homes are named because they are already stable in the repository. This
index does not claim planned changes have landed there.

| Surface | Canonical path |
| --- | --- |
| MCP registration and tool descriptions | `src/followupboss_mcp/mcp_registration.py` |
| MCP adapter and intent helper behavior | `src/followupboss_mcp/mcp_tools.py` |
| Server-level MCP instructions | `src/followupboss_mcp/mcp_server.py` |
| People query models used by lead intent | `src/followupboss_mcp/models/people.py` |
| MCP server and adapter tests | `tests/mcp/test_mcp_tools_server_cli.py` |
| Cross-cutting service tests | `tests/unit/test_services.py` |
| Battle-test scenario schema and read-only oracle helpers | `src/followupboss_mcp/battle_tests.py` |
| AI-backed battle-test model-profile runner | `src/followupboss_mcp/battle_test_ai.py` |
| Battle-test unit tests | `tests/unit/test_battle_tests.py` |
| AI-backed battle-test unit tests | `tests/unit/test_battle_test_ai.py` |
| Local AI battle-test command | `scripts/run_battle_test_model_profiles.py` |
| MCP public usage docs | `docs/mcp-usage.md` |
| Live MCP validation checklist | `docs/mcp-validation-checklist.md` |

## Directory Structure

```text
docs/planning/mcp-intent-hardening/
  README.md
  ARTIFACT_PATH_INDEX.md
  foundation/
    README.md
    source-of-truth-matrix.md
    intent-boundary-adr.md
    battle-test-verification-adr.md
  trackers/
    README.md
    readiness-overview.md
    intent-routing-readiness.md
    safety-validation-readiness.md
    battle-test-readiness.md
  execution/
    README.md
    execution-plan.md
    roadmap.md
    intent-hardening-plan.md
    intent-battle-test-plan.md
    intent_PHASE_01_description_hardening.md
    intent_PHASE_02_battle_test_planning.md
    intent_PHASE_03_read_only_battle_test_schema.md
    intent_PHASE_04_run_artifact_evaluator.md
    intent_PHASE_05_model_profile_matrix.md
    intent_PHASE_06_ai_model_profile_runner.md
    intent_PHASE_##_<slug>.md
```
