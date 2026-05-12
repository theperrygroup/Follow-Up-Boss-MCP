# Sentry Observability Source Of Truth Matrix

## Purpose

This matrix records which artifact wins when Sentry observability docs,
implementation, tests, deployment configuration, or external operator settings
disagree.

## Authority Matrix

| Question | Source of truth | Supporting artifacts |
| --- | --- | --- |
| Is Sentry runtime integration implemented? | Checked-in code and tests | `src/followupboss_mcp/`, `tests/`, `pyproject.toml` |
| Which SDK should this project use? | Current repo stack plus current Sentry SDK guidance | `pyproject.toml`, `README.md`, Sentry Python SDK guidance read during implementation |
| Which environment variables are supported? | Settings models and documented runtime tables | `src/followupboss_mcp/config.py`, `README.md`, `docs/hosted-deployment-guide.md`, `deploy/ecs/task-definition.template.json` |
| Which payload fields are redacted before Sentry submission? | Runtime sanitizer and tests | `src/followupboss_mcp/logging.py`, future Sentry instrumentation module, unit tests |
| Which exceptions are captured? | Runtime bootstrap and tests | `src/followupboss_mcp/mcp_server.py`, `src/followupboss_mcp/cli.py`, `src/followupboss_mcp/hosted_reference.py` |
| Is hosted deployment configured? | Deployment templates and operator docs | `deploy/ecs/task-definition.template.json`, `.github/workflows/deploy-staging.yml`, `docs/hosted-deployment-guide.md` |
| Are alerts live in Sentry? | Sentry project or workflow configuration | Sentry project settings, future alert docs or IaC |
| What has landed in this planning set? | Execution ledger and focused trackers | `../execution/execution-plan.md`, `../trackers/readiness-overview.md` |

## Current Observed Facts

- The repository is a Python 3.12 package and MCP server.
- No Sentry dependency or runtime references were present at planning creation.
- Existing logging is stderr-safe and includes secret redaction helpers.
- Hosted deployment runs through the `followupboss-mcp-hosted` entrypoint and
  ECS/Fargate templates.
- The current release and validation culture requires ruff, mypy, pytest, and
  100% coverage for production code.

## Conflict Rules

- If planning docs say Sentry is live but no runtime code exists, code wins and
  the docs must be downgraded.
- If external Sentry settings exist but are not documented or automated, record
  them as operator configuration, not checked-in infrastructure.
- If a Sentry event contains sensitive Follow Up Boss data during validation,
  privacy readiness is blocked even if errors are otherwise captured.
- If the current Sentry Python SDK guidance conflicts with this plan, update the
  active plan before implementation rather than preserving stale instructions.
