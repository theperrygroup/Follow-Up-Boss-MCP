# Runtime Instrumentation Readiness

## Scope

This tracker owns the code-level Sentry integration for the Python package and
MCP server runtimes.

## Current Status

Status: `In progress`

The Sentry runtime dependency, configuration model, initialization helper,
privacy sanitizer, bootstrap wiring, and focused tests are checked in. Live
Sentry project configuration and staged smoke validation remain open.

## Required Runtime Decisions

| Decision | Current answer | Status |
| --- | --- | --- |
| SDK | `sentry-sdk` is installed as the Python Sentry SDK. | Checked in |
| Enablement | Disabled when no DSN is configured. | Checked in |
| Settings home | `SentrySettings` lives in `src/followupboss_mcp/config.py`. | Checked in |
| Initialization home | `configure_sentry(...)` lives in `src/followupboss_mcp/observability.py` and is called from local, server, and hosted paths. | Checked in |
| Privacy filter | `before_send` reuses `redact_value(...)` and redacts high-risk customer payload fields. | Checked in |
| Transport coverage | Local stdio, local streamable HTTP, and hosted streamable HTTP bootstrap paths are wired. | Checked in |
| Sampling | Error sample rate is explicit; trace and profile rates remain opt-in and unset by default. | Checked in |

## Acceptance Criteria

- [x] `pyproject.toml` includes the selected Sentry SDK dependency.
- [x] Settings expose DSN, environment, release, sampling, and enablement behavior
  with thorough type hints and Google-style docstrings for new Python code.
- [x] Initialization is idempotent and safe when no DSN is configured.
- [x] Event filtering removes known secret-like fields, authorization headers, and
  customer payload fields before Sentry submission.
- [x] Runtime bootstrap paths initialize Sentry early enough to capture startup and
  request-time failures without writing MCP diagnostics to stdout.
- [x] Tests cover disabled initialization, configured initialization, sanitizer
  behavior, and at least one bootstrap call path.
- [ ] `ruff`, `mypy`, `pytest`, and coverage remain green after implementation.

## Open Questions

- Should transaction tracing be enabled in the first implementation slice or
  deferred until error-only monitoring is stable?
- Should tenant context be omitted entirely at first, or attached only as a
  hashed non-reversible identifier?
- Should outbound Follow Up Boss API failures be captured as Sentry events,
  breadcrumbs, or only logs unless they become unhandled exceptions?

## Current Blockers

- The DSN and environment naming convention have not been chosen.
- Full lint, type, test, and coverage validation still needs to run after the
  docs sync.
- Staged Sentry smoke validation still needs a real Sentry project.
