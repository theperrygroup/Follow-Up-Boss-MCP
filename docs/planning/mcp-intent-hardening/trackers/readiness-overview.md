# MCP Intent Hardening Readiness Tracker

## Purpose

This tracker records the current readiness state under a strict "planning is not
runtime" interpretation.

## Interpretation Rule

- `Complete` means the tracked planning or prerequisite slice is checked in.
- It does not mean the feature is live in the product.
- Runtime truth still comes from the checked-in codebase.

## Current Snapshot

Snapshot date: `2026-05-18`

| Slice | Status | Current answer |
| --- | --- | --- |
| Planning scaffold | Complete | Full scaffold exists under `docs/planning/mcp-intent-hardening/`. |
| Intent boundary | Complete | `foundation/intent-boundary-adr.md` defines scope, invariants, and non-goals. |
| Existing helper inventory | In progress | Current anchors are documented, but broader intent taxonomy and doc sync remain open. |
| Runtime hardening | In progress | Latest-lead and task due-bucket helpers exist, and first-pass description hardening has landed for people and tasks. Additional intent categories and wider safety wording remain planned. |
| Offline validation | In progress | Tests assert existing helpers and the first registered metadata hardening slice, but planned routing taxonomy and docs drift checks are not complete. |
| Public docs and live validation | In progress | `docs/mcp-usage.md` and `docs/mcp-validation-checklist.md` now include first-pass intent guidance; live validation remains planned. |
| Vague-prompt battle testing | In progress | Read-only scenario schema, `BT-READ-001` through `BT-READ-005`, route grading, typed oracle helpers, JSON run artifact evaluation, default model-profile artifact separation, and an AI-backed local runner are checked in; live run artifacts, fixture graph, and mutation batches remain planned. |

## Broad Blockers Before Intent-Hardening Readiness

- The canonical intent taxonomy has not been implemented in code or tests.
- Generic tool descriptions still need a systematic pass to point ambiguous
  user-specific requests at narrow helpers.
- Public MCP docs include first-pass intent guidance, but they are not yet a
  complete intent-routing guide for the full MCP surface.
- Live validation should wait until the offline contract names the intended
  helper behavior.
- Vague-prompt battle testing still needs a live AI/API-backed run artifact
  before the checked-in runner can prove chatbot behavior in the target account.

## Focused Tracker Snapshot

| Focused tracker | Current state | Why it matters |
| --- | --- | --- |
| `intent-routing-readiness.md` | In progress | Existing helper anchors and first-pass description redirects are present, but the full routing taxonomy is planned. |
| `safety-validation-readiness.md` | In progress | Identity fail-closed behavior and explicit-ID wording for people/tasks have some proof, but broader mutation wording and live validation remain planned. |
| `battle-test-readiness.md` | In progress | The first read-only corpus, oracle evaluator, run artifact writer, default model-profile matrix, and AI-backed local runner are checked in, but live run artifacts do not exist yet. |

## Current Conclusion

- The initiative is planned and partially grounded in checked-in helper anchors.
  It now has a battle-test plan and first read-only evaluator for vague chatbot
  prompts, plus a run artifact evaluator, model-profile artifact matrix, and
  local AI runner, but it is not yet complete because taxonomy, safety wording,
  live run evidence, mutation scenarios, and broader validation proof remain
  open.
