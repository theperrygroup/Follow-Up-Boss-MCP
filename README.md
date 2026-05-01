# Follow Up Boss MCP

Follow Up Boss MCP is a production-grade Python 3.12+ repository that combines:

- a typed async Follow Up Boss SDK/client built on `httpx`
- a layered domain service package built with `pydantic` v2 models
- a production-ready MCP server built with the official Python MCP SDK and `FastMCP`

The repository uses only official Follow Up Boss API documentation and official MCP documentation as design authority. It includes a real Follow Up Boss doc-ingestion step, an explicit API coverage matrix, strict static typing, deterministic tests, and enforced 100% line and 100% branch coverage for all production code under `src/followupboss_mcp`.

## Source Of Truth

- Follow Up Boss API docs: <https://docs.followupboss.com/reference/getting-started>
- MCP build-server docs: <https://modelcontextprotocol.io/docs/develop/build-server>
- MCP Inspector docs: <https://modelcontextprotocol.io/docs/tools/inspector>
- MCP debugging docs: <https://modelcontextprotocol.io/docs/tools/debugging>
- Official MCP Python SDK: <https://github.com/modelcontextprotocol/python-sdk>

## Architecture Summary

The repository is intentionally layered:

1. `config.py`, `auth.py`, `constants.py`, and `logging.py` handle configuration, auth, and safe logging.
2. `retry.py`, `rate_limits.py`, `pagination.py`, and `http_client.py` centralize transport behavior.
3. `models/*` and `services/*` provide typed Follow Up Boss operations.
4. `webhooks.py` contains reusable webhook signature verification and fast-ack helpers.
5. `mcp_tools.py`, `mcp_registration.py`, `mcp_server.py`, and `cli.py` expose the typed client through a predictable MCP surface.

More detail is in [docs/architecture.md](docs/architecture.md).

## Features

- API key authentication with HTTP Basic auth using the API key as the username and an empty password
- OAuth Bearer token support
- Configurable `X-System` and `X-System-Key` request headers
- Configurable base URL with Follow Up Boss v1 as the default
- JSON request and response handling
- 429 handling with `Retry-After`
- truncated exponential backoff with jitter for retryable 5xx failures and transport errors
- reusable pagination helpers supporting both `next` token flow and `offset` fallback
- typed services for Identity, People, People Relationships, Person Attachments, Events, Users, Custom Fields, Deals, Deal Custom Fields, Deal Attachments, Email Marketing, Groups, Inbox Apps, Pipelines, Ponds, Reactions, Smart Lists, Stages, Action Plans, Appointments, Appointment Outcomes, Appointment Types, Automations, Calls, Tasks, Team Inboxes, Teams, Templates, Text Messages, Threaded Replies, Timeframes, Notes, Webhook Events, and Webhooks
- current-user profile lookup with MCP-side redaction of secret-like fields
- people duplicate checks plus unclaimed-lead list, claim, and ignore helpers
- explicit webhook signature verification using the exact raw request body
- MCP tools, one resource, and one lead-event composition prompt
- stdio and streamable HTTP transports

## Repository Layout

- `src/followupboss_mcp`: production package
- `scripts/ingest_followupboss_docs.py`: official Follow Up Boss crawler and manifest generator
- `scripts/validate_api_coverage.py`: explicit API coverage matrix generator
- `docs/followupboss-endpoint-manifest.json`: machine-readable Follow Up Boss manifest
- `docs/api-coverage-matrix.md`: implementation matrix across discovered official endpoints
- `examples`: runnable examples for health checks, event submission, and server transports
- `tests`: unit, integration, contract, and MCP test suites

## Installation

```bash
uv sync
```

This installs the package plus the default development group defined in `pyproject.toml`.

## Environment Variables

| Variable | Required | Default | Notes |
| --- | --- | --- | --- |
| `FOLLOWUPBOSS_API_KEY` | For `api_key` auth | None | API key used as the HTTP Basic username. The legacy alias `FOLLOW_UP_BOSS_API_KEY` is also accepted. |
| `FOLLOWUPBOSS_ACCESS_TOKEN` | For `oauth` auth | None | OAuth access token used as a Bearer token. The legacy alias `FOLLOW_UP_BOSS_ACCESS_TOKEN` is also accepted. |
| `FOLLOWUPBOSS_AUTH_MODE` | No | `api_key` | Valid values: `api_key`, `oauth`. The legacy alias `FOLLOW_UP_BOSS_AUTH_MODE` is also accepted. |
| `FOLLOWUPBOSS_SYSTEM_NAME` | No | None | Sent as `X-System` when configured. Recommended for external integrations. Legacy aliases `FOLLOW_UP_BOSS_SYSTEM_NAME` and `FOLLOW_UP_BOSS_X_SYSTEM` are also accepted. |
| `FOLLOWUPBOSS_SYSTEM_KEY` | No | None | Sent as `X-System-Key` when configured. Required for Follow Up Boss webhook verification and webhook admin scenarios. Legacy aliases `FOLLOW_UP_BOSS_SYSTEM_KEY` and `FOLLOW_UP_BOSS_X_SYSTEM_KEY` are also accepted. |
| `FOLLOWUPBOSS_BASE_URL` | No | `https://api.followupboss.com/v1` | Override for alternate environments or proxies. The legacy alias `FOLLOW_UP_BOSS_BASE_URL` is also accepted. |
| `FOLLOWUPBOSS_TIMEOUT_SECONDS` | No | `10.0` | Per-request timeout. Must be greater than zero. The legacy alias `FOLLOW_UP_BOSS_TIMEOUT_SECONDS` is also accepted. |
| `FOLLOWUPBOSS_MAX_RETRIES` | No | `3` | Retry budget for retryable failures. Must be zero or greater. The legacy alias `FOLLOW_UP_BOSS_MAX_RETRIES` is also accepted. |
| `FOLLOWUPBOSS_LOG_LEVEL` | No | `INFO` | One of `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`. The legacy alias `FOLLOW_UP_BOSS_LOG_LEVEL` is also accepted. |

## Development Commands

Run the exact quality gates enforced locally and in CI:

```bash
make validate
```

Run only the docs and markdown validation checks with:

```bash
make docs-check
```

For the explicit underlying commands:

```bash
uv sync
uv export --format requirements.txt --all-groups --locked --no-editable --no-emit-project --output-file /tmp/followupboss-mcp-requirements.txt
uvx --from pip-audit pip-audit -r /tmp/followupboss-mcp-requirements.txt --strict --disable-pip --no-deps
uv run python scripts/validate_docs_links.py
uv run ruff format --check .
uv run ruff check .
uv run mypy src tests
uv run pytest
uv run coverage run --branch -m pytest
uv run coverage report --fail-under=100
uv run python -m followupboss_mcp.cli --help
```

Build and validate the distribution artifacts with:

```bash
make build-smoke
```

Run the optional live checks only when sandbox credentials are available:

```bash
FOLLOWUPBOSS_RUN_LIVE_TESTS=1 make live-identity-check
FOLLOWUPBOSS_RUN_LIVE_TESTS=1 make live-contract-check
```

`live-identity-check` is the quick auth and transport smoke path. `live-contract-check`
adds a broader suite across identity, users, people, timeframes, MCP-layer `/me`
redaction, note reactions, registered-system person attachments when configured,
and disposable person-centered note, task, and appointment write-and-rollback flows.

Both targets auto-load a repository-local `.env` when present, so manual export is optional for the common local workflow.

## Running The MCP Server

### Stdio

```bash
uv run python -m followupboss_mcp.cli stdio
```

### Streamable HTTP

```bash
uv run python -m followupboss_mcp.cli streamable-http --host 127.0.0.1 --port 8000 --path /mcp
```

Hosted multi-tenant operator guidance lives in
`docs/hosted-deployment-guide.md` and `docs/customer-onboarding-flow.md`.
Treat the local commands above as developer workflows, not as the production
recipe for the shared hosted deployment. The repository now also ships
`followupboss-mcp-hosted` as the reference hosted entrypoint described in the
hosted deployment guide. Hosted deployments can expose OAuth authorization
server routes that let Cursor delegate browser consent to Follow Up Boss and
receive MCP-scoped hosted bearer tokens.

## Examples

Identity-based health check:

```bash
uv run python examples/identity_check.py
```

Canonical lead ingestion via `POST /events`:

```bash
uv run python examples/send_lead_event.py
```

Run the MCP server directly from example scripts:

```bash
uv run python examples/run_mcp_stdio.py
uv run python examples/run_mcp_streamable_http.py
```

## MCP Inspector

The official MCP docs recommend using MCP Inspector during development. From the repository root:

```bash
npx @modelcontextprotocol/inspector uv run followupboss-mcp stdio
```

For a streamable HTTP server, start the server first and then connect Inspector to the HTTP endpoint you exposed.

## Documentation

- [docs/architecture.md](docs/architecture.md)
- [CONTRIBUTING.md](CONTRIBUTING.md)
- [docs/followupboss-doc-ingestion.md](docs/followupboss-doc-ingestion.md)
- [docs/api-coverage-matrix.md](docs/api-coverage-matrix.md)
- [docs/hosted-deployment-guide.md](docs/hosted-deployment-guide.md)
- [deploy/ecs/README.md](deploy/ecs/README.md)
- [docs/customer-onboarding-flow.md](docs/customer-onboarding-flow.md)
- [docs/mcp-usage.md](docs/mcp-usage.md)
- [docs/mcp-validation-checklist.md](docs/mcp-validation-checklist.md)
- [docs/testing.md](docs/testing.md)
- [docs/security.md](docs/security.md)
- [docs/security-incident-playbook.md](docs/security-incident-playbook.md)
- [docs/release-checklist.md](docs/release-checklist.md)
- [docs/final-validation-report.md](docs/final-validation-report.md)

## Troubleshooting

- `FOLLOWUPBOSS_API_KEY must be provided`: set `FOLLOWUPBOSS_API_KEY` or switch to `FOLLOWUPBOSS_AUTH_MODE=oauth` with `FOLLOWUPBOSS_ACCESS_TOKEN`.
- `401` or `403` errors: verify the credential, the integration user permissions, and whether the API key owner has access to the endpoint you are calling.
- `429` errors: Follow Up Boss returned a rate limit. The client respects `Retry-After`, but sustained rate limiting usually means the caller should reduce request volume.
- Note or call mutations immediately after person creation can fail if the person is not visible yet. Use the event-ingestion path or the service wait helper for eventual-consistency-sensitive flows.
- Custom field writes must use the Follow Up Boss field `name` such as `customBirthday`, not the UI label.
- In stdio mode, never write operational logs to stdout. The server uses Python logging rather than printing MCP diagnostics to stdout.

## Security Notes

- Secrets are loaded through environment variables and represented as `SecretStr` inside settings.
- Authorization and `X-System-Key` values are redacted in logs and object representations.
- Caller-supplied overrides for `Authorization`, `X-System`, `X-System-Key`, and `Content-Type` are rejected at the HTTP client boundary.
- Webhook verification uses HMAC-SHA256 over the base64-encoded raw request body with `X-System-Key`.
- Webhook receivers should acknowledge with a fast `2xx` response and move longer processing off the request thread.
- CI now includes dependency audit and secret-scanning automation without a temporary vulnerability exception in the current lockfile state.
- Successful HTTP responses now emit method, path, status, and elapsed-time logs through the existing stderr-safe logger.

More detail is in [docs/security.md](docs/security.md).

## Coverage Guarantee

This repository enforces:

- `mypy --strict`
- `ruff check`
- `ruff format --check`
- passing `pytest`
- `coverage run --branch -m pytest`
- `coverage report --fail-under=100`

The coverage gate is scoped to all production code in `src/followupboss_mcp`, and both line coverage and branch coverage must remain at `100.00%`.
