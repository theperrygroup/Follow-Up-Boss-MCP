# Testing

## Testing Strategy

The default local and CI suite is fully offline and deterministic. It covers every production file in `src/followupboss_mcp` at `100.00%` line coverage and `100.00%` branch coverage.

Test directories are organized by intent:

- `tests/unit`: transport, helpers, models, and service-level behavior
- `tests/integration`: runtime entrypoints and server lifecycle behavior
- `tests/contracts`: edge contracts for shared utilities
- `tests/mcp`: MCP adapter, FastMCP registration, official stdio and streamable HTTP client interoperability, prompt, resource, and CLI behavior

## Mocking Strategy

The suite uses two complementary approaches:

- `respx` for real `httpx` request interception in transport tests
- tiny typed protocol-compatible stubs for service and MCP tests

This keeps HTTP behavior realistic where it matters while keeping service and MCP tests fast and focused.

## Failure Modes Covered

The default suite covers:

- configuration validation
- Basic auth and Bearer auth header generation
- required and optional system-header behavior
- JSON request encoding
- response parsing
- `400`, `401`, `403`, `404`, `418`, `429`, and retryable `5xx` mapping
- `Retry-After` parsing for delta seconds and HTTP-date formats
- exhausted retries
- next-token pagination
- offset fallback pagination
- query and field serialization
- custom field name validation
- canonical event payload shaping
- eventual-consistency polling for newly created people
- webhook signature verification and fast-ack helpers
- MCP tool success and failure paths
- FastMCP resource and prompt registration
- official stdio MCP client interoperability for tools, resources, and prompts
- official streamable HTTP MCP client interoperability for tools, resources, and prompts
- CLI startup and `__main__` execution behavior

## Coverage Commands

```bash
uv run pytest
uv run coverage run --branch -m pytest
uv run coverage report --fail-under=100
```

## Branch Coverage Explanation

Branch coverage matters here because most production risk lives in conditional behavior:

- auth mode selection
- retry or fail decisions
- `Retry-After` parsing paths
- next-token versus offset pagination
- custom field validation branches
- error mapping branches
- stdio versus streamable HTTP startup paths

Requiring `100.00%` branch coverage ensures those code paths are exercised explicitly rather than only executing the happy path once.

## Typing And Lint Gates

The test suite is part of a larger quality gate:

```bash
uv export --format requirements.txt --all-groups --locked --no-editable --no-emit-project --output-file /tmp/followupboss-mcp-requirements.txt
uvx --from pip-audit pip-audit -r /tmp/followupboss-mcp-requirements.txt --strict --disable-pip --no-deps --ignore-vuln CVE-2026-4539
uv run ruff format --check .
uv run ruff check .
uv run mypy src tests
uv run pytest
uv run coverage run --branch -m pytest
uv run coverage report --fail-under=100
```

## Live Contract Test Strategy

Live Follow Up Boss tests are intentionally not required for the default suite. If you add live contract tests later:

1. gate them behind explicit environment variables
2. skip them by default in local development and CI
3. keep the offline suite sufficient to preserve the `100.00%` coverage requirement
4. never weaken the default coverage gate in order to accommodate live tests

The current opt-in live checks are:

```bash
FOLLOWUPBOSS_RUN_LIVE_TESTS=1 make live-identity-check
FOLLOWUPBOSS_RUN_LIVE_TESTS=1 make live-contract-check
```

`live-identity-check` only exercises the `GET /identity` path and is intended to validate
real auth and transport behavior without turning the default suite into a live dependency.

`live-contract-check` keeps the same opt-in behavior while broadening upstream verification
across identity, users, people, timeframes, MCP-layer current-user redaction, note
reactions, and disposable person-centered note, task, and appointment write-and-rollback flows.
