# Follow Up Boss MCP Task Tracker

## Overall Goal

Build a production-grade Python 3.12+ repository that ingests official Follow Up Boss and official MCP documentation, provides a strictly typed Follow Up Boss SDK/client, exposes a production-grade MCP server via the official Python MCP SDK/FastMCP, includes extensive documentation, and enforces strict quality gates with 100% line and 100% branch coverage for all production code under `src/followupboss_mcp`.

## Assumptions

- The repository starts empty and all required files must be created from scratch.
- Official Follow Up Boss docs and official MCP docs are the only design authorities.
- The default API root is the Follow Up Boss v1 API base URL documented in the official API docs.
- The MCP server will support `stdio` and streamable HTTP transports using the official Python MCP SDK where available in the current release.
- Optional live contract tests, if included, will be fully gated by environment variables and excluded from the default suite.

## Architecture Decisions

- Use `uv` for dependency and environment management.
- Use a `src/` layout with package name `followupboss_mcp`.
- Use async `httpx.AsyncClient` as the canonical transport and keep MCP tools on top of the typed async service layer.
- Use `pydantic` v2 models for request and response types with strict request validation and forward-compatible response parsing.
- Separate layers into config, auth, retry/rate-limit, pagination, HTTP client, domain services, MCP adapter, and CLI.
- Keep webhook verification outside the MCP layer in dedicated reusable utilities.
- Generate documentation ingestion artifacts and coverage matrix from a repeatable script-backed process.

## Phase Plan

1. Bootstrap repository structure, tracker, and tooling skeleton.
2. Ingest official Follow Up Boss and MCP docs into structured artifacts.
3. Implement the typed client stack, models, services, and webhook helpers.
4. Implement MCP tools, server transports, CLI, and examples.
5. Write exhaustive tests and enforce strict lint, typing, formatting, and coverage gates.
6. Run full validation, update docs and tracker, and publish the final validation report.

## Status Markers

- `NOT_STARTED`
- `IN_PROGRESS`
- `DONE`
- `BLOCKED`
- `DEFERRED`

## Tasks

- `DONE` Create `TASKS.followupboss-mcp.md` with required sections.
- `DONE` Scaffold repository layout, package directories, tests, docs, examples, scripts, and CI.
- `DONE` Ingest official Follow Up Boss docs into `docs/followupboss-endpoint-manifest.json`.
- `DONE` Write and regenerate `docs/followupboss-doc-ingestion.md` from ingestion results.
- `DONE` Create and maintain `docs/api-coverage-matrix.md`.
- `DONE` Implement config, constants, auth, logging, retry, rate limiting, pagination, and HTTP transport layers.
- `DONE` Implement typed domain models for common, identity, people, events, users, custom fields, notes, and webhooks.
- `DONE` Implement typed services for identity, people, events, users, custom fields, notes, and webhooks.
- `DONE` Implement webhook verification and helper utilities.
- `DONE` Implement MCP tool layer and production-grade MCP server.
- `DONE` Implement CLI and runnable examples.
- `DONE` Write README and architecture, usage, testing, security, release, ingestion, coverage, and validation docs.
- `DONE` Write exhaustive unit, integration, contract, and MCP tests with 100% line and branch coverage for production code.
- `DONE` Configure `pyproject.toml`, `.gitignore`, `.editorconfig`, and GitHub Actions CI.
- `DONE` Run `uv sync`.
- `DONE` Run `uv run ruff format --check .`.
- `DONE` Run `uv run ruff check .`.
- `DONE` Run `uv run mypy src tests`.
- `DONE` Run `uv run pytest`.
- `DONE` Run `uv run coverage run --branch -m pytest`.
- `DONE` Run `uv run coverage report --fail-under=100`.
- `DONE` Run `uv run python -m followupboss_mcp.cli --help`.
- `DONE` Write `docs/final-validation-report.md`.
- `DONE` Implement typed reaction get/create/delete coverage across models, services, MCP tools, tests, and docs.
- `DONE` Re-run `make release-validate` and `make live-identity-check` after the reactions slice.
- `DONE` Implement typed deal custom field get/create/update/delete coverage across models, services, MCP tools, tests, and docs.
- `DONE` Re-run `make release-validate` and `make live-identity-check` after the deal custom field admin slice.
- `DONE` Implement typed people duplicate-check, unclaimed lead list, claim, and ignore coverage across models, services, MCP tools, tests, and docs.
- `DONE` Re-run `make release-validate` and `make live-identity-check` after the people admin utility slice.
- `DONE` Implement typed timeframe list coverage across models, services, MCP tools, tests, and docs.
- `DONE` Re-run `make release-validate` and `make live-identity-check` after the timeframe slice.
- `DONE` Implement typed threaded reply lookup coverage across models, services, MCP tools, tests, and docs.
- `DONE` Re-run `make release-validate` and `make live-identity-check` after the threaded reply slice.
- `DONE` Implement typed webhook event lookup coverage across models, services, MCP tools, tests, and docs.
- `DONE` Re-run `make release-validate` and `make live-identity-check` after the webhook event slice.
- `DONE` Implement typed current-user `/me` coverage across models, services, MCP tools, tests, and docs.
- `DONE` Re-run `make release-validate` and `make live-identity-check` after the `/me` slice.
- `DONE` Implement typed webhook update coverage across models, services, MCP tools, tests, and docs.
- `DONE` Re-run `make release-validate` and `make live-identity-check` after the webhook update slice.
- `DONE` Implement typed person and user delete coverage across models, services, MCP tools, tests, and docs.
- `DONE` Re-run `make release-validate` and `make live-identity-check` after the final delete slice.
- `DONE` Add automated markdown link and MCP usage validation across scripts, the shared validation wrapper, contributor docs, and release docs.
- `DONE` Restore and relink the MCP validation runbook, then make `make live-identity-check` auto-load a repository-local `.env` when present.
- `DONE` Re-run `make release-validate` and `FOLLOWUPBOSS_RUN_LIVE_TESTS=1 make live-identity-check` after the docs-validation automation slice.
- `DONE` Broaden the optional live validation suite beyond the identity path into representative multi-domain contract checks across identity, users, people, timeframes, and MCP `/me` redaction.
- `DONE` Fix live-discovered `/me` schema drift so `notifyBy` accepts both string and list payloads.
- `DONE` Re-run `FOLLOWUPBOSS_RUN_LIVE_TESTS=1 make live-contract-check` and `make release-validate` after the broader live-suite slice.
- `DONE` Reduce private FastMCP-manager coupling in the server-surface test by moving exact registration assertions onto public FastMCP and official stdio client surfaces.
- `DONE` Re-run focused MCP tests and `make release-validate` after the MCP-coupling slice.
- `DONE` Extend the optional live suite with disposable person, note reaction, note, task, appointment, and registered-system person-attachment flows that exercise real create, update, lookup, and cleanup behavior.
- `DONE` Re-run `FOLLOWUPBOSS_RUN_LIVE_TESTS=1 make live-contract-check` and `make release-validate` after the live write-and-rollback slice.
- `DONE` Add safer request-shape debug logs plus retry, rate-limit, and attempt-count telemetry in the shared HTTP client.
- `DONE` Re-run focused HTTP-client tests and `make release-validate` after the telemetry slice.
- `DONE` Add an owner-only live webhook CRUD path that skips cleanly when the current credential lacks access.
- `DONE` Add broader CI environment diversity across operating systems while keeping artifact work on the baseline lane.
- `DONE` Validate the updated workflow syntax and re-run `make release-validate` after the OS-matrix slice.
- `DONE` Route the broad MCP server-surface smoke test through public `server.call_tool(...)` instead of private tool-function invocation.
- `DONE` Broaden CI validation across more than one Python/runtime environment.
- `DONE` Validate the workflow syntax and re-run `make release-validate` after the CI-matrix slice.
- `DONE` Centralize more MCP request-model assembly through a shared typed builder in `mcp_registration.py`.
- `DONE` Upgrade locked `pygments` to a fixed release and remove the temporary `CVE-2026-4539` audit ignore from local and CI validation flows.
- `DONE` Extend the shared typed request-builder adoption across additional MCP registration helpers and restore the architecture category to its baseline band.
- `DONE` Expand shared typed request-builder adoption across additional MCP registration helpers such as groups, appointment metadata, calls, pipelines, ponds, teams, templates, text messages, notes, and webhooks.
- `DONE` Finish the remaining request/input-model constructor tail in `mcp_registration.py` so request assembly is effectively centralized behind the shared typed builder.

## Blockers

- None.

## Evidence

- Workspace path: `/Users/x/Library/CloudStorage/Dropbox/Portfolio/MCP/Follow Up Boss`
- Confirmed official Follow Up Boss docs expose structured endpoint metadata via the embedded `ssr-props` JSON payload and ingested `174` official reference pages.
- Confirmed official webhook guidance requires fast `2xx` acknowledgment and `FUB-Signature` verification using HMAC-SHA256 over the base64-encoded raw payload with `X-System-Key`.
- Implemented the production package under `src/followupboss_mcp` with typed transport, models, services, webhook helpers, MCP adapter, server, and CLI.
- Added examples in `examples/` and scripts in `scripts/`.
- Added unit, contract, integration, and MCP tests in `tests/`.
- Added CI workflow in `.github/workflows/ci.yml`.
- Ran `uv sync` with successful output: `Resolved 53 packages in 6ms` and `Audited 51 packages in 6ms`.
- Ran `uv run python scripts/ingest_followupboss_docs.py` with successful output writing the manifest and ingestion report.
- Ran `uv run python scripts/validate_api_coverage.py` with successful output writing `docs/api-coverage-matrix.md`.
- Ran `uv run ruff format --check .` with successful output: `42 files already formatted`.
- Ran `uv run ruff check .` with successful output: `All checks passed!`.
- Ran `uv run mypy src tests` with successful output: `Success: no issues found in 36 source files`.
- Ran `uv run pytest` with successful output: `40 passed`.
- Ran `uv run coverage run --branch -m pytest` with successful output: `40 passed`.
- Ran `uv run coverage report --fail-under=100` with successful output showing `TOTAL 1149 0 150 0 100.00%`.
- Ran `uv run python -m followupboss_mcp.cli --help` with successful usage output.
- Wrote `docs/final-validation-report.md` with the final validated status.
- Expanded the implementation to include typed reactions get/create/delete support across the SDK, MCP surface, tests, and generated coverage docs.
- Re-ran `make release-validate` with successful output: `Success: no issues found in 80 source files`, `105 passed, 1 skipped`, and `TOTAL 4027 0 350 0 100.00%`.
- Re-ran `make live-identity-check` with successful output: `1 skipped` when live credentials were not enabled.
- Expanded the implementation to include typed deal custom field get/create/update/delete support across the SDK, MCP surface, tests, and generated coverage docs.
- Re-ran `make release-validate` with successful output: `Success: no issues found in 80 source files`, `105 passed, 1 skipped`, and `TOTAL 4109 0 356 0 100.00%`.
- Re-ran `make live-identity-check` with successful output: `1 skipped` when live credentials were not enabled.
- Expanded the implementation to include typed people duplicate-check, unclaimed lead list, claim, and ignore support across the SDK, MCP surface, tests, and generated coverage docs.
- Re-ran `make release-validate` with successful output: `Success: no issues found in 80 source files`, `107 passed, 1 skipped`, and `TOTAL 4244 0 398 0 100.00%`.
- Re-ran `make live-identity-check` with successful output: `1 skipped` when live credentials were not enabled.
- Expanded the implementation to include typed timeframe list support across the SDK, MCP surface, tests, and generated coverage docs.
- Re-ran `make release-validate` with successful output: `Success: no issues found in 82 source files`, `109 passed, 1 skipped`, and `TOTAL 4282 0 402 0 100.00%`.
- Re-ran `make live-identity-check` with successful output: `1 skipped` when live credentials were not enabled.
- Expanded the implementation to include typed threaded reply lookup support across the SDK, MCP surface, tests, and generated coverage docs.
- Re-ran `make release-validate` with successful output: `Success: no issues found in 84 source files`, `110 passed, 1 skipped`, and `TOTAL 4318 0 404 0 100.00%`.
- Re-ran `make live-identity-check` with successful output: `1 skipped` when live credentials were not enabled.
- Expanded the implementation to include typed webhook event lookup support across the SDK, MCP surface, tests, and generated coverage docs.
- Re-ran `make release-validate` with successful output: `Success: no issues found in 84 source files`, `110 passed, 1 skipped`, and `TOTAL 4338 0 406 0 100.00%`.
- Re-ran `make live-identity-check` with successful output: `1 skipped` when live credentials were not enabled.
- Expanded the implementation to include typed current-user `/me` support with MCP-side redaction for secret-like fields across the SDK, MCP surface, tests, and generated coverage docs.
- Re-ran `make release-validate` with successful output: `Success: no issues found in 84 source files`, `110 passed, 1 skipped`, and `TOTAL 4390 0 410 0 100.00%`.
- Re-ran `make live-identity-check` with successful output: `1 skipped` when live credentials were not enabled.
- Expanded the implementation to include typed webhook update support across the SDK, MCP surface, tests, and generated coverage docs.
- Re-ran `make release-validate` with successful output: `Success: no issues found in 84 source files`, `110 passed, 1 skipped`, and `TOTAL 4402 0 410 0 100.00%`.
- Re-ran `make live-identity-check` with successful output: `1 skipped` when live credentials were not enabled.
- Expanded the implementation to include typed person delete and user delete support across the SDK, MCP surface, tests, and generated coverage docs.
- Re-ran `make release-validate` with successful output: `Success: no issues found in 84 source files`, `110 passed, 1 skipped`, and `TOTAL 4423 0 410 0 100.00%`.
- Re-ran `make live-identity-check` with successful output: `1 skipped` when live credentials were not enabled.
- Re-ran `make validate` with successful output: `Success: no issues found in 82 source files`, `109 passed, 1 skipped`, and `TOTAL 4282 0 402 0 100.00%`.
- Re-ran `FOLLOWUPBOSS_RUN_LIVE_TESTS=1 make live-identity-check` with successful output: `1 passed`.
- Ran credential-backed MCP validation with the current `.env` and updated `docs/mcp-validation-checklist.md` with live results for transports, pagination, error handling, and domain coverage across people, relationships, attachments, reactions, events, action plans, automations, calls, text messages, appointments, deals, deal attachments, templates, text message templates, and notes.
- Added settings support for both documented `FOLLOWUPBOSS_*` variables and legacy `FOLLOW_UP_BOSS_*` aliases, then verified `FOLLOWUPBOSS_RUN_LIVE_TESTS=1 make live-identity-check` works with the raw `.env` names directly.
- Added `scripts/validate_docs_links.py`, wired it into `make validate`, refreshed the README, contributing guide, release checklist, final validation report, and harsh review checklist, and restored `docs/mcp-validation-checklist.md` so local docs validation now has a complete repository target set.
- Re-ran `uv run python scripts/validate_docs_links.py` with successful output: `Docs validation passed.`.
- Re-ran `make release-validate` with successful output: `Success: no issues found in 84 source files`, `110 passed, 1 skipped`, `TOTAL 4423 0 410 0 100.00%`, and `Validated build artifacts: followupboss_mcp-0.1.0.tar.gz followupboss_mcp-0.1.0-py3-none-any.whl`.
- Re-ran `FOLLOWUPBOSS_RUN_LIVE_TESTS=1 make live-identity-check` with successful output: `1 passed`, and verified the target auto-loads a repository-local `.env` when present.
- Added `tests/live/test_contract_suite.py` plus the `make live-contract-check` wrapper, refreshed the README, contributing guide, testing guide, release checklist, validation runbook, final validation report, and harsh review checklist, and widened `/me` parsing so `notifyBy` accepts both string and list payloads observed in live data.
- Re-ran `FOLLOWUPBOSS_RUN_LIVE_TESTS=1 make live-contract-check` with successful output: `3 passed`.
- Re-ran `make release-validate` with successful output: `Success: no issues found in 85 source files`, `110 passed, 3 skipped`, `TOTAL 4423 0 410 0 100.00%`, and `Validated build artifacts: followupboss_mcp-0.1.0.tar.gz followupboss_mcp-0.1.0-py3-none-any.whl`.
- Moved the broad MCP server-surface registration assertions off private FastMCP manager maps and onto public FastMCP list/read APIs plus the official stdio client session, while keeping the broad tool smoke coverage intact.
- Re-ran `uv run pytest tests/mcp/test_mcp_tools_server_cli.py` with successful output: `5 passed`.
- Re-ran `make release-validate` with successful output: `Success: no issues found in 85 source files`, `110 passed, 3 skipped`, `TOTAL 4423 0 410 0 100.00%`, and `Validated build artifacts: followupboss_mcp-0.1.0.tar.gz followupboss_mcp-0.1.0-py3-none-any.whl`.
- Extended `tests/live/test_contract_suite.py` with disposable person, note reaction, note, task, and appointment rollback flows, refreshed the README, contributing guide, testing guide, validation runbook, final validation report, harsh review checklist, and task tracker, and verified cleanup reaches real `404` reads after person, task, and appointment deletion.
- Re-ran `FOLLOWUPBOSS_RUN_LIVE_TESTS=1 make live-contract-check` with successful output: `4 passed`.
- Re-ran `make release-validate` with successful output: `Success: no issues found in 85 source files`, `110 passed, 4 skipped`, `TOTAL 4423 0 410 0 100.00%`, and `Validated build artifacts: followupboss_mcp-0.1.0.tar.gz followupboss_mcp-0.1.0-py3-none-any.whl`.
- Added safer request-shape debug logs plus explicit retry, rate-limit, and attempt-count telemetry in `src/followupboss_mcp/http_client.py`, refreshed the security, MCP usage, final validation, harsh review, and task-tracker docs, and kept request logging free of raw query and JSON values.
- Re-ran `uv run pytest tests/unit/test_http_client.py` with successful output: `10 passed`.
- Re-ran `make release-validate` with successful output: `Success: no issues found in 85 source files`, `111 passed, 4 skipped`, `TOTAL 4429 0 410 0 100.00%`, and `Validated build artifacts: followupboss_mcp-0.1.0.tar.gz followupboss_mcp-0.1.0-py3-none-any.whl`.
- Extended `tests/live/test_contract_suite.py` with registered-system person attachment create/get/update/delete coverage, refreshed the README, contributing guide, testing guide, validation runbook, final validation report, harsh review checklist, and task tracker, and proved the registered-system attachment path works under the current credential.
- Re-ran `FOLLOWUPBOSS_RUN_LIVE_TESTS=1 make live-contract-check` with successful output: `5 passed`.
- Re-ran `make release-validate` with successful output: `Success: no issues found in 85 source files`, `111 passed, 5 skipped`, `TOTAL 4429 0 410 0 100.00%`, and `Validated build artifacts: followupboss_mcp-0.1.0.tar.gz followupboss_mcp-0.1.0-py3-none-any.whl`.
- Split `.github/workflows/ci.yml` into dedicated secret-scan, multi-version quality, and build-smoke jobs, widened validation to Python `3.12` and `3.13`, refreshed the final validation report and harsh review checklist, and kept artifact validation on the baseline lane.
- Synced the build-readiness docs to the current workflow state, which now runs build-smoke validation across Ubuntu, macOS, and Windows in addition to the broader validation matrix.
- Added an owner-only webhook CRUD test to `tests/live/test_contract_suite.py`, refreshed the testing, validation, and task-tracker docs, and verified the current credential records the webhook path as an automated clean skip rather than a manual blocker.
- Re-ran `FOLLOWUPBOSS_RUN_LIVE_TESTS=1 make live-contract-check` with successful output: `5 passed, 1 skipped`.
- Re-ran `make release-validate` with successful output: `Success: no issues found in 85 source files`, `111 passed, 6 skipped`, `TOTAL 4433 0 410 0 100.00%`, and `Validated build artifacts: followupboss_mcp-0.1.0.tar.gz followupboss_mcp-0.1.0-py3-none-any.whl`.
- Extended `.github/workflows/ci.yml` with a macOS Python `3.12` validation lane on top of the existing Ubuntu Python `3.12` and `3.13` matrix, refreshed the final validation report and harsh review checklist, and kept build-smoke validation on the baseline Ubuntu lane.
- Re-ran workflow YAML parsing with successful output: `workflow yaml ok`.
- Synced the build-readiness docs and harsh scorecard to the current workflow state, which already validates Linux, macOS, and Windows on both Python `3.12` and `3.13`, then revalidated through the shared local release wrapper.
- Routed the broad MCP server-surface smoke test in `tests/mcp/test_mcp_tools_server_cli.py` through public FastMCP `list_tools()` metadata plus `server.call_tool(...)`, keeping the full registered tool surface coverage intact while removing direct private tool-function invocation.
- Re-ran `uv run pytest tests/mcp/test_mcp_tools_server_cli.py` with successful output: `5 passed`.
- Re-ran `make release-validate` with successful output: `Success: no issues found in 85 source files`, `111 passed, 6 skipped`, `TOTAL 4433 0 410 0 100.00%`, and `Validated build artifacts: followupboss_mcp-0.1.0.tar.gz followupboss_mcp-0.1.0-py3-none-any.whl`.
- Expanded the official streamable-HTTP client-session test with representative event, task, call, template, and appointment flows in addition to the existing identity, `/me`, people, timeframes, resource, and prompt coverage.
- Re-ran `uv run pytest tests/mcp/test_mcp_tools_server_cli.py` with successful output: `5 passed`.
- Centralized more MCP request-model assembly in `src/followupboss_mcp/mcp_registration.py` through a shared typed builder, which removed a large set of repeated `model_validate({...})` blocks without changing the public MCP signatures.
- Re-ran `uv run pytest tests/mcp/test_mcp_tools_server_cli.py tests/unit/test_services.py` with successful output: `83 passed`.
- Expanded the shared typed builder adoption across groups, appointment metadata, calls, pipelines, ponds, teams, templates, text messages, notes, and webhooks, further reducing direct inline request-model construction inside `mcp_registration.py`.
- Re-ran `uv run pytest tests/mcp/test_mcp_tools_server_cli.py tests/unit/test_services.py` with successful output: `83 passed`.
- Extended the shared typed builder adoption across additional registration helpers such as users and appointment metadata, leaving mostly public parameter-list verbosity rather than repeated validation dictionaries.
- Re-ran `uv run pytest tests/mcp/test_mcp_tools_server_cli.py tests/unit/test_services.py` with successful output: `83 passed`.
- Expanded the shared typed builder adoption across custom fields, calls, pipelines, ponds, teams, templates, text messages, notes, and webhooks, further reducing direct inline request-model construction inside `mcp_registration.py`.
- Re-ran `uv run pytest tests/mcp/test_mcp_tools_server_cli.py tests/unit/test_services.py` with successful output: `83 passed`.
- Finished the remaining request/input-model constructor tail in `src/followupboss_mcp/mcp_registration.py`, leaving request assembly effectively centralized behind the shared typed builder rather than split across ad hoc direct constructors.
- Re-ran `uv run pytest tests/mcp/test_mcp_tools_server_cli.py tests/unit/test_services.py` with successful output: `83 passed`.
- Expanded the streamable-HTTP official client-session test with representative `get_me`, people search, delete-confirmation, and timeframe-list flows while keeping the full registered tool list assertion in place.
- Re-ran `uv run pytest tests/mcp/test_mcp_tools_server_cli.py` with successful output: `5 passed`.
- Added an owner-only webhook CRUD test to `tests/live/test_contract_suite.py`, refreshed the live-validation docs, and verified the current credential now records the webhook path as an automated clean skip instead of a manual blocker.
- Re-ran `FOLLOWUPBOSS_RUN_LIVE_TESTS=1 make live-contract-check` with successful output: `5 passed, 1 skipped`.
- Added optional `FOLLOWUPBOSS_OWNER_*` override support to the live webhook path so a stronger owner credential can exercise webhook CRUD without replacing the default live credential.
- Upgraded the locked `pygments` dependency from `2.19.2` to `2.20.0`, removed the temporary `CVE-2026-4539` ignore from the Makefile, CI, README, contributing, testing, security, and incident-response docs, and restored a clean dependency-audit path without exceptions.
- Re-ran `uvx --from pip-audit pip-audit -r /tmp/followupboss-mcp-requirements.txt --strict --disable-pip --no-deps` with successful output: `No known vulnerabilities found`.

## Final Acceptance Checklist

- Task tracker exists and reflects actual work completed.
- Follow Up Boss docs ingested into manifest and readable summary.
- API coverage matrix exists and is explicit.
- Typed client exists.
- MCP server exists.
- Documentation is extensive and in sync with code.
- `mypy --strict` passes.
- Linting passes.
- Formatting passes.
- Tests pass.
- Line coverage is 100%.
- Branch coverage is 100%.
- CI is configured.
- Final validation report exists.

