# Sentry Observability Artifact Path Index

## Purpose

- This file is the canonical naming and path index for the planning set.
- This file is not the current-status ledger.
- Future prompts should use this file instead of hardcoded path assumptions.

## Canonical Role Index

### Planning Root

- Actual repo path: `docs/planning/sentry-observability/`
- Already exists: `YES`
- Canonical for future prompts: `YES`
- Confidence: `High`
- Explanation: This is the first and only planning root for Sentry
  observability.

### Landing README

- Actual repo path: `docs/planning/sentry-observability/README.md`
- Already exists: `YES`
- Canonical for future prompts: `YES`
- Confidence: `High`
- Explanation: This file defines read order, precedence, and working rules.

### Artifact Path Index

- Actual repo path: `docs/planning/sentry-observability/ARTIFACT_PATH_INDEX.md`
- Already exists: `YES`
- Canonical for future prompts: `YES`
- Confidence: `High`
- Explanation: This file records canonical homes for planning artifacts.

### Foundation Directory

- Actual repo path: `docs/planning/sentry-observability/foundation/`
- Already exists: `YES`
- Canonical for future prompts: `YES`
- Confidence: `High`
- Explanation: Durable Sentry scope, privacy, and source-of-truth rules live
  here.

### Source Of Truth Matrix

- Actual repo path: `docs/planning/sentry-observability/foundation/source-of-truth-matrix.md`
- Already exists: `YES`
- Canonical for future prompts: `YES`
- Confidence: `High`
- Explanation: This matrix maps planning docs, code, tests, deployment docs, and
  Sentry operator configuration to their authority.

### Sentry Boundary ADR

- Actual repo path: `docs/planning/sentry-observability/foundation/sentry-boundary-adr.md`
- Already exists: `YES`
- Canonical for future prompts: `YES`
- Confidence: `High`
- Explanation: This ADR defines what belongs in the Sentry observability
  initiative and what remains outside it.

### Tracker Directory

- Actual repo path: `docs/planning/sentry-observability/trackers/`
- Already exists: `YES`
- Canonical for future prompts: `YES`
- Confidence: `High`
- Explanation: Current readiness and focused risk trackers live here.

### Master Readiness Tracker

- Actual repo path: `docs/planning/sentry-observability/trackers/readiness-overview.md`
- Already exists: `YES`
- Canonical for future prompts: `YES`
- Confidence: `High`
- Explanation: This tracker is the aggregate live planning status surface.

### Runtime Instrumentation Tracker

- Actual repo path: `docs/planning/sentry-observability/trackers/runtime-instrumentation-readiness.md`
- Already exists: `YES`
- Canonical for future prompts: `YES`
- Confidence: `High`
- Explanation: This tracker owns SDK integration, bootstrap, privacy filtering,
  and tests.

### Deployment Operations Tracker

- Actual repo path: `docs/planning/sentry-observability/trackers/deployment-operations-readiness.md`
- Already exists: `YES`
- Canonical for future prompts: `YES`
- Confidence: `High`
- Explanation: This tracker owns ECS, GitHub Actions, release metadata, DSN
  configuration, alerting, and runbook readiness.

### Execution Directory

- Actual repo path: `docs/planning/sentry-observability/execution/`
- Already exists: `YES`
- Canonical for future prompts: `YES`
- Confidence: `High`
- Explanation: The live ledger, baseline roadmap, active plan, and future phase
  proof files live here.

### Execution Plan

- Actual repo path: `docs/planning/sentry-observability/execution/execution-plan.md`
- Already exists: `YES`
- Canonical for future prompts: `YES`
- Confidence: `High`
- Explanation: This is the checked-in ledger for completed proof and blockers.

### Roadmap

- Actual repo path: `docs/planning/sentry-observability/execution/roadmap.md`
- Already exists: `YES`
- Canonical for future prompts: `YES`
- Confidence: `High`
- Explanation: This records baseline sequencing and dependency order.

### Active Plan

- Actual repo path: `docs/planning/sentry-observability/execution/sentry-rollout-plan.md`
- Already exists: `YES`
- Canonical for future prompts: `YES`
- Confidence: `High`
- Explanation: This is the canonical active plan for the current Sentry rollout
  sequence.

### Future Phase Proof Files

- Actual repo path: `docs/planning/sentry-observability/execution/sentry_PHASE_##_<slug>.md`
- Already exists: `YES`
- Canonical for future prompts: `YES`
- Confidence: `High`
- Explanation: Add one proof file when a slice needs durable evidence beyond the
  aggregate execution ledger.

### Phase 01 Core Instrumentation Proof

- Actual repo path: `docs/planning/sentry-observability/execution/sentry_PHASE_01_core_instrumentation.md`
- Already exists: `YES`
- Canonical for future prompts: `YES`
- Confidence: `High`
- Explanation: This file records the first checked-in implementation slice for
  Sentry dependency, settings, initializer, bootstrap, deployment, and tests.

## Runtime Artifact Homes

These homes are named because they are stable in the repository. This index does
not claim planned changes have landed there.

| Surface | Canonical path |
| --- | --- |
| Python package dependencies and quality gates | `pyproject.toml` |
| Server and tenant settings | `src/followupboss_mcp/config.py` |
| Secret-redacting logging helpers | `src/followupboss_mcp/logging.py` |
| Sentry initializer and event sanitizer | `src/followupboss_mcp/observability.py` |
| FastMCP server construction and lifespan | `src/followupboss_mcp/mcp_server.py` |
| Local single-tenant CLI bootstrap | `src/followupboss_mcp/cli.py` |
| Hosted deployment bootstrap | `src/followupboss_mcp/hosted_reference.py` |
| ECS task definition template | `deploy/ecs/task-definition.template.json` |
| Hosted deployment guide | `docs/hosted-deployment-guide.md` |
| README environment variable table | `README.md` |
| Unit and MCP tests | `tests/unit/`, `tests/mcp/` |
| CI and deployment workflows | `.github/workflows/` |

## Directory Structure

```text
docs/planning/sentry-observability/
  README.md
  ARTIFACT_PATH_INDEX.md
  foundation/
    README.md
    source-of-truth-matrix.md
    sentry-boundary-adr.md
  trackers/
    README.md
    readiness-overview.md
    runtime-instrumentation-readiness.md
    deployment-operations-readiness.md
  execution/
    README.md
    execution-plan.md
    roadmap.md
    sentry-rollout-plan.md
    sentry_PHASE_01_core_instrumentation.md
    sentry_PHASE_##_<slug>.md
```
