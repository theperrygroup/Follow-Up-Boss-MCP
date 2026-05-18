# MCP Intent Hardening Docs

This directory is the canonical operating guide for the MCP intent hardening
planning set.

## Role

- This tree is docs-only.
- Runtime truth comes from checked-in code, not roadmap items alone.
- Intent hardening means making high-level user requests route to the safest
  scoped Follow Up Boss MCP tool, with predictable defaults and clear validation
  proof.

## Interpretation Rules

- Planning complete is not the same as shipped.
- Readiness does not by itself prove runtime ownership.
- The active plan may outrank the historical roadmap for the current execution
  seam.
- Existing intent helpers are checked-in runtime facts only where the named code
  anchors already exist.
- Proposed routing, safety, and documentation work must not be marked live until
  code, tests, and docs are checked in.

## Current Status Snapshot

Snapshot date: `2026-05-18`

| Lens | Current answer |
| --- | --- |
| Planning foundation | Full scaffold checked in for MCP intent hardening, now extended with a battle-test verification contract and prompt-corpus plan. |
| Runtime feature or implementation truth | Current working tree includes intent-scoped helpers for latest assigned lead, authenticated-user task due buckets, the first read-only battle-test evaluator, JSON run artifact support, model-profile artifact separation, and an AI-backed profile runner for GPT-5.5 low reasoning and Sonnet 4.7. Broader intent taxonomy, live run evidence, and mutation validation remain planned. |
| Highest-risk remaining surface | Vague chatbot prompts have not yet been exercised through the AI-backed runner with persisted live evidence. |

## Fastest Reality Check

- `foundation/intent-boundary-adr.md`: durable definition of what this tree
  means by intent hardening.
- `execution/intent-hardening-plan.md`: canonical active plan for the current
  sequence.
- `foundation/battle-test-verification-adr.md`: durable rules for verifying
  vague chatbot prompts through MCP routing and API truth.
- `execution/intent-battle-test-plan.md`: focused prompt corpus and battle-test
  oracle sequence.
- `execution/intent_PHASE_03_read_only_battle_test_schema.md`: checked-in proof
  for the first reusable battle-test code slice.
- `execution/intent_PHASE_04_run_artifact_evaluator.md`: checked-in proof for
  corpus-level run summaries and JSON artifact writing.
- `execution/intent_PHASE_05_model_profile_matrix.md`: checked-in proof for
  separate GPT-5.5 low-reasoning and Sonnet 4.7 artifact profiles.
- `execution/intent_PHASE_06_ai_model_profile_runner.md`: checked-in proof for
  the OpenAI/Anthropic model-profile runner and local command.
- `trackers/readiness-overview.md`: current readiness state across planning,
  runtime, validation, and docs.
- `execution/execution-plan.md`: checked-in ledger for what has landed.

## Start Here

1. `foundation/intent-boundary-adr.md`
2. `foundation/battle-test-verification-adr.md`
3. `execution/intent-hardening-plan.md`
4. `execution/intent-battle-test-plan.md`
5. `trackers/readiness-overview.md`
6. `execution/execution-plan.md`
7. `execution/roadmap.md` only for historical sequencing
8. `ARTIFACT_PATH_INDEX.md` for canonical paths

## Directory Guide

| Folder or file | Role | Open first when you need |
| --- | --- | --- |
| `foundation/README.md` | Durable decisions | Ownership, scope, or precedence questions |
| `trackers/README.md` | Live readiness scoreboards | Current blockers and risk state |
| `execution/README.md` | Execution navigation | Next implementation slice |
| `execution/intent-hardening-plan.md` | Canonical active sequence | The current hardening implementation order |
| `execution/intent-battle-test-plan.md` | Focused battle-test sequence | Vague prompt corpus and API oracle design |
| `ARTIFACT_PATH_INDEX.md` | Naming and path index | Canonical artifact homes |

## Document Precedence

1. `foundation/` wins for durable rules.
2. `execution/intent-hardening-plan.md` wins for the current focused execution
   seam.
3. `execution/intent-battle-test-plan.md` wins for battle-test prompt corpus and
   oracle sequencing, while remaining subordinate to the overall active plan.
4. Focused trackers plus `execution/execution-plan.md` win for live checked-in
   status.
5. `execution/roadmap.md` is baseline sequencing, not the freshest status.
6. `ARTIFACT_PATH_INDEX.md` wins for exact paths and naming.

## Common Workflows

| Goal | Open these first |
| --- | --- |
| Start the next slice | `trackers/readiness-overview.md`, `execution/execution-plan.md`, `execution/intent-hardening-plan.md` |
| Get current reality | `foundation/source-of-truth-matrix.md`, `trackers/readiness-overview.md`, `execution/execution-plan.md` |
| Decide whether a new helper belongs here | `foundation/intent-boundary-adr.md`, `execution/intent-hardening-plan.md` |
| Build or run vague chatbot battle tests | `foundation/battle-test-verification-adr.md`, `execution/intent-battle-test-plan.md`, `trackers/battle-test-readiness.md` |
| Find proof file naming | `ARTIFACT_PATH_INDEX.md`, `execution/README.md` |

## Update Order

1. Relevant phase proof doc, if needed
2. Relevant focused tracker
3. `trackers/readiness-overview.md`
4. `execution/execution-plan.md`
5. Relevant `foundation/` doc, if durable rules changed
6. `README.md` or `ARTIFACT_PATH_INDEX.md` only if navigation or canonical paths
   changed

## Working Rules

- Keep this tree docs-only.
- Keep status language honest.
- Do not scatter related intent-hardening planning across multiple initiative
  roots.
- Do not treat tool descriptions as sufficient proof without tests that show the
  registered MCP surface still routes and validates the intended payloads.
