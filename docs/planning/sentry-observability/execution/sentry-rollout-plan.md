# Sentry Observability Active Rollout Plan

This is the canonical active plan for the current Sentry observability rollout
sequence. It supersedes the roadmap when a focused implementation order is
needed.

## 1. Objective

Add Sentry to the Follow Up Boss MCP project so local and hosted Python runtimes
capture actionable errors with release and environment context while preserving
the existing secret-redaction and MCP stdio safety guarantees.

## 2. Current Runtime Starting Point

The current working tree contains these useful anchors:

- Python 3.12 package metadata and strict quality gates in `pyproject.toml`
- environment-backed settings in `src/followupboss_mcp/config.py`
- stderr-safe logging and secret redaction in `src/followupboss_mcp/logging.py`
- FastMCP construction and lifespan management in
  `src/followupboss_mcp/mcp_server.py`
- local single-tenant bootstrap in `src/followupboss_mcp/cli.py`
- hosted multi-tenant bootstrap in `src/followupboss_mcp/hosted_reference.py`
- ECS/Fargate deployment templates in `deploy/ecs/`
- hosted deployment docs in `docs/hosted-deployment-guide.md`

Core Sentry dependency, settings, initialization, sanitizer, bootstrap wiring,
hosted deployment variables, and local automated validation are now checked in.
Real Sentry project configuration, alert ownership, and staged smoke evidence
remain open.

## 3. Target Contract

| Contract area | Required behavior |
| --- | --- |
| SDK selection | `sentry-sdk` is installed after reading Sentry Python SDK guidance. |
| Disabled default | Runtime works normally without `SENTRY_DSN`. |
| Bootstrap | Sentry initializes once and early for local and hosted entrypoints. |
| Privacy | Events redact or drop Follow Up Boss secrets, headers, tokens, tenant secret paths, and customer payloads. |
| Context | Events include safe release, environment, transport, and entrypoint context. |
| Deployment | ECS and hosted docs explain Sentry variables and release metadata. |
| Validation | Automated tests prove configuration and sanitizer behavior before staged smoke validation. |

## 4. Phase Plan

### Phase A - Confirm SDK And Runtime Contract

Deliverables:

- read current Sentry Python SDK setup guidance
- confirm DSN, Sentry project, environment naming, and first alert destination
- decide initial scope for tracing and profiling
- record accepted configuration names and defaults

Acceptance criteria:

- implementation notes name the SDK guidance source and date
- runtime settings list is accepted before code lands
- tracing/profiling are either explicitly configured or deferred

### Phase B - Add Core Instrumentation

Deliverables:

- checked in: add the Sentry SDK dependency
- checked in: add typed Sentry settings with Google-style docstrings for new
  Python code
- checked in: add one reusable initialization helper
- checked in: add privacy sanitizer using existing redaction behavior as the
  baseline
- checked in: initialize Sentry from local and hosted bootstrap paths

Acceptance criteria:

- no DSN means no Sentry event submission and no startup failure
- configured DSN initializes once with environment and release context
- sanitizer tests prove sensitive keys and representative customer payload fields
  are removed or redacted
- stdio mode still avoids stdout diagnostics

### Phase C - Add Runtime Coverage And Context

Deliverables:

- wire safe operation, transport, and entrypoint context
- decide whether outbound `httpx` failures become breadcrumbs or events
- cover FastMCP and Starlette-hosted exception paths where supported by the SDK
- document any intentionally excluded context

Acceptance criteria:

- tests prove context is safe and stable
- expected handled errors do not become noisy Sentry issues unless explicitly
  promoted
- privacy filtering still wins over context enrichment

### Phase D - Update Deployment And Operator Docs

Deliverables:

- checked in: update README environment variable table
- checked in: update hosted deployment guide and ECS task definition template
- checked in: update GitHub Actions or deployment docs for `SENTRY_RELEASE`
- add alert and triage expectations to operator docs

Acceptance criteria:

- hosted operators can configure Sentry without reading source code
- release and environment fields are deterministic
- alert ownership and manual-versus-automated setup are documented

### Phase E - Run Proof

Deliverables:

- run focused unit tests for settings, initialization, sanitizer, and bootstrap
- run project quality gates appropriate to touched files
- run a staged Sentry smoke check with a sanitized intentional exception after
  automated proof passes
- update trackers, execution ledger, and phase proof files

Acceptance criteria:

- `ruff`, `mypy`, `pytest`, and coverage pass or blockers are recorded
- Sentry smoke evidence confirms the event reaches the expected project and
  environment without sensitive data
- planning docs accurately distinguish checked-in code from live deployment

## 5. Implementation Guardrails

- Keep Sentry setup in a small typed module rather than embedding SDK calls in
  every entrypoint.
- Preserve the existing logging contract and never write MCP diagnostics to
  stdout in stdio mode.
- Reuse the existing redaction helpers where they fit, and add tests for any new
  sensitive keys.
- Do not capture full request bodies, upstream response bodies, raw headers, or
  Follow Up Boss person/task/message payloads.
- Prefer explicit settings over hidden SDK defaults for sampling and release
  context.
- Do not mark hosted Sentry live until deployment configuration and smoke proof
  exist.

## 6. Next Slice

The next implementation slice should be rollout proof:

1. Confirm the real Sentry project DSN, environment naming, and alert
   destination.
2. Add or document alert ownership and triage expectations.
3. Run a staged sanitized exception smoke with `SENTRY_DSN` configured.
4. Refresh the focused trackers and execution ledger with validation evidence.
