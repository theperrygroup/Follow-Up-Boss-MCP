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

Snapshot date: `2026-05-08`

| Lens | Current answer |
| --- | --- |
| Planning foundation | Full scaffold checked in for MCP intent hardening. |
| Runtime feature or implementation truth | Current working tree includes intent-scoped helpers for latest assigned lead and authenticated-user task due buckets. Broader intent taxonomy and selection validation remain planned. |
| Highest-risk remaining surface | Generic tool descriptions and broad search/list tools can still be selected for user-specific intent unless hardening, tests, and docs keep the narrow helpers authoritative. |

## Fastest Reality Check

- `foundation/intent-boundary-adr.md`: durable definition of what this tree
  means by intent hardening.
- `execution/intent-hardening-plan.md`: canonical active plan for the current
  sequence.
- `trackers/readiness-overview.md`: current readiness state across planning,
  runtime, validation, and docs.
- `execution/execution-plan.md`: checked-in ledger for what has landed.

## Start Here

1. `foundation/intent-boundary-adr.md`
2. `execution/intent-hardening-plan.md`
3. `trackers/readiness-overview.md`
4. `execution/execution-plan.md`
5. `execution/roadmap.md` only for historical sequencing
6. `ARTIFACT_PATH_INDEX.md` for canonical paths

## Directory Guide

| Folder or file | Role | Open first when you need |
| --- | --- | --- |
| `foundation/README.md` | Durable decisions | Ownership, scope, or precedence questions |
| `trackers/README.md` | Live readiness scoreboards | Current blockers and risk state |
| `execution/README.md` | Execution navigation | Next implementation slice |
| `execution/intent-hardening-plan.md` | Canonical active sequence | The current hardening implementation order |
| `ARTIFACT_PATH_INDEX.md` | Naming and path index | Canonical artifact homes |

## Document Precedence

1. `foundation/` wins for durable rules.
2. `execution/intent-hardening-plan.md` wins for the current focused execution
   seam.
3. Focused trackers plus `execution/execution-plan.md` win for live checked-in
   status.
4. `execution/roadmap.md` is baseline sequencing, not the freshest status.
5. `ARTIFACT_PATH_INDEX.md` wins for exact paths and naming.

## Common Workflows

| Goal | Open these first |
| --- | --- |
| Start the next slice | `trackers/readiness-overview.md`, `execution/execution-plan.md`, `execution/intent-hardening-plan.md` |
| Get current reality | `foundation/source-of-truth-matrix.md`, `trackers/readiness-overview.md`, `execution/execution-plan.md` |
| Decide whether a new helper belongs here | `foundation/intent-boundary-adr.md`, `execution/intent-hardening-plan.md` |
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
