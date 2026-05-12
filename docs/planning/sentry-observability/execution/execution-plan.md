# Sentry Observability Execution Plan

This file is the checked-in ledger for the planning set. It records what has
landed, what is blocked, and what still remains open.

## 1. Ledger Scope

- This ledger records checked-in proof.
- Use `roadmap.md` for baseline dependency order.
- Use focused trackers for current readiness detail.

## 1A. How To Read This Ledger Now

- This file is the ledger, not proof that Sentry is live.
- The strongest checked-in planning proof is the scaffold under
  `docs/planning/sentry-observability/`.
- The strongest checked-in runtime proof is the core Sentry instrumentation in
  `src/followupboss_mcp/observability.py`, `SentrySettings`, bootstrap wiring,
  focused tests, and hosted deployment configuration.
- The biggest remaining gap is real Sentry project configuration, alert
  ownership, full validation, and staged smoke evidence.

## 2. Current Checked-In Status

- Planning root created for Sentry observability.
- Foundation docs define the observability boundary and source-of-truth
  hierarchy.
- Trackers record runtime instrumentation and deployment operations as planned.
- Execution docs define the active rollout sequence and baseline roadmap.
- `sentry-sdk` is installed and initialized lazily only when `SENTRY_DSN` is
  configured.
- `before_send` sanitization redacts secret-like values and representative
  Follow Up Boss customer payload fields.
- Local and hosted startup paths attach entrypoint and transport tags.
- README, hosted deployment docs, ECS template, and staging deployment workflow
  now include Sentry runtime variables.
- Repo inspection identified a Python 3.12 MCP server with existing settings,
  logging redaction, local CLI, hosted reference entrypoint, ECS deployment
  templates, and strict quality gates.

## 3. Current Blockers

- Sentry DSN, organization/project, environment names, release naming, and alert
  destination are not known yet.
- Full lint, type, test, coverage, and docs validation still needs to run after
  this implementation slice.
- Staged Sentry smoke validation has not run.

## 4. Completed Planning Or Landed Proof

### 2026-05-10 - Planning Scaffold

- Checked-in proof:
  - `docs/planning/sentry-observability/README.md`
  - `docs/planning/sentry-observability/ARTIFACT_PATH_INDEX.md`
  - `docs/planning/sentry-observability/foundation/sentry-boundary-adr.md`
  - `docs/planning/sentry-observability/execution/sentry-rollout-plan.md`
- Result:
  - The initiative now has one canonical planning root, one active plan, and
    focused trackers for runtime instrumentation and deployment operations.

### 2026-05-10 - Phase 01 Core Instrumentation

- Checked-in proof:
  - `docs/planning/sentry-observability/execution/sentry_PHASE_01_core_instrumentation.md`
  - `pyproject.toml`
  - `uv.lock`
  - `src/followupboss_mcp/config.py`
  - `src/followupboss_mcp/observability.py`
  - `src/followupboss_mcp/cli.py`
  - `src/followupboss_mcp/mcp_server.py`
  - `src/followupboss_mcp/hosted_reference.py`
  - `tests/unit/test_observability.py`
  - `README.md`
  - `docs/hosted-deployment-guide.md`
  - `deploy/ecs/task-definition.template.json`
  - `.github/workflows/deploy-staging.yml`
- Result:
  - Sentry is disabled by default, enabled by `SENTRY_DSN`, initialized lazily,
    and filtered through a privacy-safe `before_send` hook.

## 5. Current Work Queue

| Task | Status | Why it is still open |
| --- | --- | --- |
| Confirm Sentry project and SDK guidance | In progress | SDK guidance was read; real DSN/project and alert destination remain unknown. |
| Add privacy-safe runtime instrumentation | In progress | Core code and focused tests landed; full validation is still pending. |
| Wire local and hosted entrypoints | Checked in | Bootstrap paths call the Sentry initializer with entrypoint and transport tags. |
| Update deployment and operator docs | In progress | ECS, README, hosted guide, and workflow metadata are updated; alert ownership remains open. |
| Run automated and staged validation | In progress | Focused tests pass; full gates and staged Sentry smoke remain open. |

## 6. Current Conclusion

Sentry observability has core runtime instrumentation checked in, but it is not
ready for runtime rollout until full validation, Sentry project configuration,
alert ownership, and staged smoke evidence are complete.
