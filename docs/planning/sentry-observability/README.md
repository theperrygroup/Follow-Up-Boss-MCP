# Sentry Observability Docs

This directory is the canonical operating guide for the Sentry observability
planning set.

## Role

- This tree is docs-only.
- Runtime truth comes from checked-in code, not roadmap items alone.
- Sentry observability means adding error monitoring, release context, and
  operational alerting to the Python Follow Up Boss MCP server without leaking
  Follow Up Boss credentials, tenant secrets, or customer payloads.

## Interpretation Rules

- Planning complete is not the same as Sentry being live.
- Readiness does not by itself prove runtime instrumentation exists.
- The active rollout plan may outrank the historical roadmap for the current
  implementation seam.
- The detected SDK recommendation is `sentry-python` because the repository is
  a Python 3.12 package with no JavaScript runtime package manifest.
- SDK-specific setup should read the current `sentry-python` guidance before
  implementation begins.

## Current Status Snapshot

Snapshot date: `2026-05-10`

| Lens | Current answer |
| --- | --- |
| Planning foundation | Full scaffold checked in for Sentry observability. |
| Runtime feature or implementation truth | Core Sentry dependency, settings, sanitizer, initialization, bootstrap wiring, and deployment variables are checked in; live Sentry project validation is still open. |
| Highest-risk remaining surface | Proving a staged Sentry event reaches the correct project without Follow Up Boss secrets, tenant credentials, authorization headers, or customer data. |

## Fastest Reality Check

- `foundation/sentry-boundary-adr.md`: durable scope and privacy boundary.
- `execution/sentry-rollout-plan.md`: canonical active rollout sequence.
- `trackers/readiness-overview.md`: current readiness across SDK, runtime,
  deployment, and validation.
- `execution/execution-plan.md`: checked-in ledger for what has landed.

## Start Here

1. `foundation/sentry-boundary-adr.md`
2. `execution/sentry-rollout-plan.md`
3. `trackers/readiness-overview.md`
4. `execution/execution-plan.md`
5. `execution/roadmap.md` only for historical sequencing
6. `ARTIFACT_PATH_INDEX.md` for canonical paths

## Directory Guide

| Folder or file | Role | Open first when you need |
| --- | --- | --- |
| `foundation/README.md` | Durable decisions | Scope, privacy, or source-of-truth questions |
| `trackers/README.md` | Live readiness scoreboards | Current blockers and risk state |
| `execution/README.md` | Execution navigation | Next implementation slice |
| `execution/sentry-rollout-plan.md` | Canonical active sequence | The current Sentry implementation order |
| `ARTIFACT_PATH_INDEX.md` | Naming and path index | Canonical artifact homes |

## Document Precedence

1. `foundation/` wins for durable scope, privacy, and ownership rules.
2. `execution/sentry-rollout-plan.md` wins for the current focused rollout seam.
3. Focused trackers plus `execution/execution-plan.md` win for live checked-in
   status.
4. `execution/roadmap.md` is baseline sequencing, not the freshest status.
5. `ARTIFACT_PATH_INDEX.md` wins for exact paths and naming.

## Common Workflows

| Goal | Open these first |
| --- | --- |
| Start the next slice | `trackers/readiness-overview.md`, `execution/execution-plan.md`, `execution/sentry-rollout-plan.md` |
| Get current reality | `foundation/source-of-truth-matrix.md`, `trackers/readiness-overview.md`, `execution/execution-plan.md` |
| Decide whether instrumentation belongs here | `foundation/sentry-boundary-adr.md`, `execution/sentry-rollout-plan.md` |
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
- Do not claim Sentry is live until code, configuration, tests, and deployment
  docs are checked in.
- Treat privacy filtering as a release blocker, not a follow-up.
- Keep local stdio behavior safe by preserving stderr-only operational logging
  and avoiding stdout diagnostics.
