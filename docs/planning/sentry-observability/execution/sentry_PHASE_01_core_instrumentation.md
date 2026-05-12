# Sentry Phase 01: Core Instrumentation Proof

## Scope

This proof file records the first implementation slice for Sentry
observability. It covers dependency installation, typed settings, privacy-safe
initialization, local and hosted bootstrap wiring, deployment configuration, and
focused automated tests.

## Checked-In Proof

| Area | Proof |
| --- | --- |
| Dependency | `pyproject.toml` and `uv.lock` include `sentry-sdk`. |
| Settings | `src/followupboss_mcp/config.py` includes typed `SentrySettings`. |
| Runtime initializer | `src/followupboss_mcp/observability.py` initializes Sentry lazily and only when `SENTRY_DSN` is set. |
| Bootstrap | `src/followupboss_mcp/cli.py`, `src/followupboss_mcp/mcp_server.py`, and `src/followupboss_mcp/hosted_reference.py` call the initializer with safe entrypoint and transport tags. |
| Privacy filter | `before_send` sanitization reuses `redact_value(...)` and redacts customer payload keys before submission. |
| Startup performance | `src/followupboss_mcp/__init__.py` lazily loads hosted reference exports so local MCP subprocess startup does not import the hosted PostgreSQL stack unnecessarily. |
| Tests | `tests/unit/test_observability.py`, `tests/unit/test_auth_config_logging.py`, and focused MCP/server tests cover settings, sanitizer, initialization, exports, and startup behavior. |
| Deployment docs | `README.md`, `docs/hosted-deployment-guide.md`, `deploy/ecs/README.md`, `deploy/ecs/task-definition.template.json`, and `.github/workflows/deploy-staging.yml` describe or wire Sentry runtime variables. |
| Validation | `ruff format --check`, `ruff check`, uncached `mypy`, docs validation, full pytest, and 100% branch coverage pass locally. |

## Behavior Covered

- Sentry remains disabled when `SENTRY_DSN` is unset or blank.
- Sentry initialization is idempotent.
- The SDK is imported lazily only after a configured DSN is present.
- Initialization uses `send_default_pii=False`,
  `include_local_variables=False`, and `max_request_body_size="never"`.
- Event sanitization redacts authorization headers, system keys, secret-like
  values, tenant secret references, request bodies, cookies, and representative
  Follow Up Boss customer payload fields.
- Local and hosted bootstrap paths attach stable entrypoint and transport tags.

## Remaining Gaps

- A real Sentry project DSN and alert destination have not been configured.
- Staged end-to-end Sentry smoke validation has not run.
- Tracing and profiling remain opt-in and should stay disabled until the team
  chooses sampling rates.
- Sentry alert configuration remains operator-owned and not yet automated.

## Conclusion

Phase 01 lands privacy-safe core Sentry instrumentation and hosted deployment
configuration. The next slice should run full validation, choose Sentry project
settings, and perform a staged smoke test before claiming live rollout.
