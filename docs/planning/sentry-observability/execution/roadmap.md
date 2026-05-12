# Sentry Observability Task Roadmap

This roadmap converts the current understanding of the initiative into a
phased, dependency-aware task plan.

Treat this file as the baseline dependency map. For the freshest checked-in
status, use `execution-plan.md` plus the focused trackers.

## Scope And Evidence

- Source references:
  - `pyproject.toml`
  - `README.md`
  - `src/followupboss_mcp/config.py`
  - `src/followupboss_mcp/logging.py`
  - `src/followupboss_mcp/mcp_server.py`
  - `src/followupboss_mcp/cli.py`
  - `src/followupboss_mcp/hosted_reference.py`
  - `deploy/ecs/task-definition.template.json`
  - `.github/workflows/deploy-staging.yml`
  - `docs/hosted-deployment-guide.md`
- Primary code or doc anchors:
  - `FollowUpBossServerSettings`
  - `FollowUpBossSettings`
  - `configure_logging`
  - `redact_value`
  - `create_server`
  - `followupboss-mcp`
  - `followupboss-mcp-hosted`
- Historical blockers at roadmap creation:
  - No prior `docs/planning/` root existed for Sentry.
  - No Sentry dependency or runtime integration existed in the checked-in code.

## Current Checked-In Progress Snapshot

- Planning scaffold exists.
- Core runtime implementation is checked in for dependency, settings,
  initialization, sanitizer, and bootstrap wiring.
- Deployment configuration is partially checked in for ECS and staging workflow
  variables; Sentry alerting remains planned.

## Harsh Sequencing Rule

- Do not enable hosted event submission until privacy filtering is implemented
  and tested.
- Do not claim Sentry is live until automated checks and staged smoke evidence
  exist.

## Phase 0 - SDK And Contract Confirmation

### P0-001 - Read Current Sentry Python SDK Guidance

- Why this task exists: Sentry SDK setup guidance changes over time and should
  drive the implementation details.
- Exact files or modules affected: planning notes first, then implementation
  files after confirmation.
- Dependency prerequisites: Planning scaffold.
- Severity: High.
- Estimated complexity: Low.
- Feature domain: Observability setup.
- Whether this is: implementation preparation.
- Acceptance criteria: The implementation pass records which Sentry Python SDK
  guidance was used and updates this plan if the guidance changes expected
  setup.
- What could break if this task is skipped: The project may receive stale SDK
  configuration or miss current integration defaults.

### P0-002 - Confirm Sentry Project Inputs

- Why this task exists: DSN, environment, release, and alert routing determine
  the runtime and deployment contract.
- Exact files or modules affected: `README.md`,
  `docs/hosted-deployment-guide.md`, `deploy/ecs/task-definition.template.json`.
- Dependency prerequisites: P0-001.
- Severity: High.
- Estimated complexity: Low.
- Feature domain: Deployment configuration.
- Whether this is: docs and operator setup.
- Acceptance criteria: DSN source, environment names, release naming, and alert
  destination are documented or explicitly deferred.
- What could break if this task is skipped: Events may be sent to the wrong
  project or become hard to triage by release and environment.

## Phase 1 - Core Runtime Instrumentation

### P1-001 - Add Dependency And Typed Settings

- Why this task exists: Sentry must be configured through the project's existing
  typed settings style.
- Exact files or modules affected: `pyproject.toml`,
  `src/followupboss_mcp/config.py`, tests.
- Dependency prerequisites: P0-001, P0-002.
- Severity: High.
- Estimated complexity: Medium.
- Feature domain: Runtime configuration.
- Whether this is: implementation and tests.
- Acceptance criteria: Settings cover DSN, environment, release, traces sample
  rate, profiles sample rate, and disabled behavior with type hints and
  Google-style docstrings for new code.
- What could break if this task is skipped: Sentry setup may rely on implicit
  environment reads that are hard to test or document.

### P1-002 - Add Privacy-Safe Initialization Helper

- Why this task exists: One initializer keeps SDK calls consistent across local
  and hosted entrypoints.
- Exact files or modules affected: future instrumentation module,
  `src/followupboss_mcp/logging.py`, tests.
- Dependency prerequisites: P1-001.
- Severity: Critical.
- Estimated complexity: Medium.
- Feature domain: Error monitoring and privacy.
- Whether this is: implementation and tests.
- Acceptance criteria: Initialization is idempotent, disabled without DSN, and
  applies a before-send privacy filter that redacts or drops sensitive data.
- What could break if this task is skipped: Sentry may leak secrets or behave
  differently across entrypoints.

### P1-003 - Wire Bootstrap Paths

- Why this task exists: Local and hosted runtimes need consistent observability.
- Exact files or modules affected: `src/followupboss_mcp/cli.py`,
  `src/followupboss_mcp/mcp_server.py`,
  `src/followupboss_mcp/hosted_reference.py`, tests.
- Dependency prerequisites: P1-002.
- Severity: High.
- Estimated complexity: Medium.
- Feature domain: Runtime bootstrap.
- Whether this is: implementation and tests.
- Acceptance criteria: Sentry initializes early in local and hosted paths without
  breaking no-DSN local development or stdio stdout safety.
- What could break if this task is skipped: Some production failures may remain
  invisible or only partially contextualized.

## Phase 2 - Context And Noise Control

### P2-001 - Add Safe Runtime Context

- Why this task exists: Errors need enough metadata to triage without exposing
  customer data.
- Exact files or modules affected: instrumentation module, server or adapter
  bootstrap tests.
- Dependency prerequisites: P1-003.
- Severity: Medium.
- Estimated complexity: Medium.
- Feature domain: Error triage.
- Whether this is: implementation and tests.
- Acceptance criteria: Events include safe release, environment, transport,
  entrypoint, and operation-family context where available.
- What could break if this task is skipped: Sentry issues may be too generic to
  route quickly.

### P2-002 - Decide Breadcrumb And Handled Error Policy

- Why this task exists: The project already logs expected upstream and hosted
  failures; Sentry should not turn every handled case into noisy issues.
- Exact files or modules affected: HTTP client, tenant runtime, hosted auth, or
  instrumentation docs depending on chosen policy.
- Dependency prerequisites: P1-003.
- Severity: Medium.
- Estimated complexity: Medium.
- Feature domain: Observability policy.
- Whether this is: implementation and docs.
- Acceptance criteria: Handled auth, tenant, rate-limit, and upstream API
  failures have a documented capture policy with tests for any promoted events.
- What could break if this task is skipped: Operators may drown in expected
  operational failures or miss important ones.

## Phase 3 - Deployment And Operations

### P3-001 - Update Hosted Configuration

- Why this task exists: Hosted deployments need reproducible Sentry settings.
- Exact files or modules affected: `deploy/ecs/task-definition.template.json`,
  `deploy/ecs/README.md`, `docs/hosted-deployment-guide.md`, `README.md`.
- Dependency prerequisites: P1-003.
- Severity: High.
- Estimated complexity: Low.
- Feature domain: Hosted deployment.
- Whether this is: docs and deployment templates.
- Acceptance criteria: Operators can set Sentry DSN, environment, release, and
  sampling values from documented deployment configuration.
- What could break if this task is skipped: Runtime code may exist but never be
  enabled in hosted environments.

### P3-002 - Add Release And Alerting Workflow

- Why this task exists: Sentry issues are most useful when grouped by release
  and routed to an owner.
- Exact files or modules affected: `.github/workflows/deploy-staging.yml`,
  release docs, hosted deployment docs, possibly Sentry API automation.
- Dependency prerequisites: P3-001.
- Severity: Medium.
- Estimated complexity: Medium.
- Feature domain: Operations.
- Whether this is: docs, CI/CD, or external operator setup.
- Acceptance criteria: Release values are deterministic and alerting setup is
  documented with ownership and severity.
- What could break if this task is skipped: Issues may lack deployment context or
  sit untriaged.

## Phase 4 - Validation And Evidence

### P4-001 - Run Automated Quality Gates

- Why this task exists: The repository enforces strict typing, linting, tests,
  and coverage.
- Exact files or modules affected: touched implementation and docs.
- Dependency prerequisites: P1-P3 implementation slices.
- Severity: High.
- Estimated complexity: Low.
- Feature domain: Validation.
- Whether this is: tests.
- Acceptance criteria: Relevant focused tests and full project gates pass, or
  blockers are recorded in `execution-plan.md`.
- What could break if this task is skipped: Observability changes may regress
  existing runtime behavior.

### P4-002 - Run Staged Sentry Smoke Validation

- Why this task exists: Automated tests cannot prove the event reached the
  correct Sentry project and environment.
- Exact files or modules affected: runbook and phase proof docs.
- Dependency prerequisites: P4-001 and hosted Sentry configuration.
- Severity: High.
- Estimated complexity: Medium.
- Feature domain: Release validation.
- Whether this is: live validation and docs.
- Acceptance criteria: A sanitized intentional exception appears in Sentry with
  expected release, environment, and no sensitive data.
- What could break if this task is skipped: The team may believe Sentry is live
  without end-to-end evidence.
