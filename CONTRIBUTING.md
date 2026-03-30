# Contributing

## Goals

This repository is intentionally strict. Contributions should preserve:

- typed domain models and services
- centralized HTTP behavior
- JSON-safe MCP responses
- deterministic offline tests
- `100.00%` line and branch coverage for production code

## Setup

```bash
uv sync
```

## Common Shortcuts

```bash
make validate
make docs-check
make build-smoke
make release-validate
make live-identity-check
make live-contract-check
```

## Core Validation Commands

Run the same checks locally that CI enforces:

```bash
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

If you need to validate the packaged artifacts, run:

```bash
uv build --clear
uv run python scripts/validate_build_artifacts.py
```

If you need real upstream contract checks and the required credentials are available, run:

```bash
FOLLOWUPBOSS_RUN_LIVE_TESTS=1 make live-identity-check
FOLLOWUPBOSS_RUN_LIVE_TESTS=1 make live-contract-check
```

`live-identity-check` is the smallest auth and transport smoke path. `live-contract-check`
adds a broader representative suite across identity, users, people, timeframes,
MCP-layer `/me` redaction, note reactions, registered-system person attachments when
configured, and disposable person-centered note, task, and appointment write-and-rollback flows.

Both targets auto-load a repository-local `.env` when present, so manual export is optional for the common local workflow.

## Project Structure

- `src/followupboss_mcp/http_client.py`: auth, headers, retries, rate limits, JSON parsing, and HTTP error mapping
- `src/followupboss_mcp/services/`: typed Follow Up Boss operations by domain
- `src/followupboss_mcp/mcp_tools.py`: MCP-safe adapter layer
- `src/followupboss_mcp/mcp_registration.py`: grouped FastMCP tool, resource, and prompt registration helpers
- `src/followupboss_mcp/mcp_server.py`: server construction, service bundle wiring, and lifespan management
- `tests/`: unit, contract, integration, and MCP coverage

## Adding Or Expanding Endpoints

When you add a Follow Up Boss endpoint, update all of these layers together:

1. Add or extend typed request and response models in `src/followupboss_mcp/models/`.
2. Add the typed service method in `src/followupboss_mcp/services/`.
3. Expose the operation in `src/followupboss_mcp/mcp_tools.py` when it belongs in the MCP surface.
4. Register the MCP tool in `src/followupboss_mcp/mcp_registration.py`.
5. Add or update tests in:
   - `tests/unit/` for service behavior
   - `tests/mcp/` for adapter and MCP surface behavior
6. Update `scripts/validate_api_coverage.py` and regenerate `docs/api-coverage-matrix.md`.
7. Update user-facing docs such as `README.md`, `docs/mcp-usage.md`, and `docs/final-validation-report.md` when the surface changed.

## MCP Testing Guidance

- Prefer adapter tests for focused response-shaping behavior.
- Keep at least one official MCP client interoperability test for the registered surface.
- Avoid depending only on private FastMCP internals when a client-session test can prove the same behavior.

## Security Expectations

- Never commit real credentials or customer payloads.
- Keep `Authorization` and `X-System-Key` redaction intact.
- Do not reintroduce caller-controlled overrides for protected transport headers.
- Review `docs/security-incident-playbook.md` if a credential may have been exposed.

## Documentation Expectations

Treat docs as part of the implementation. If behavior, tool surface, validation commands, or generated artifacts change, update the docs in the same change.
