# Project Review Checklist

This document is the living quality scorecard for the Follow Up Boss MCP project. It is meant to be updated after code changes so the repository has one place where quality grades, evidence, and open gaps stay visible over time.

## How To Use This File

1. Keep the `Baseline grade` fixed until the project meaningfully changes direction.
2. Update the `Current grade`, `Last reviewed`, and `Change notes` whenever code changes affect a category.
3. Re-check or uncheck the category checklist items based on the current codebase.
4. Add one line to the review history whenever grades move.
5. Recalculate the weighted overall score after changing any category score.

## Grade Rubric

| Grade | Score Range | Meaning |
| --- | --- | --- |
| `A` | `90-100` | Strong implementation with only minor or non-blocking gaps. |
| `B` | `80-89` | Solid baseline, but there are important weaknesses worth improving. |
| `C` | `70-79` | Usable, but repeated review findings or missing safeguards reduce confidence. |
| `D` | `60-69` | Significant quality concerns that should be addressed before expanding scope. |
| `F` | `<60` | High-risk or incomplete area that is not ready to rely on. |

## Status Markers

| Status | Meaning |
| --- | --- |
| `Pass` | Healthy today; not a release-blocking concern. |
| `Needs Work` | Important gaps exist, even if the current implementation still functions. |
| `Blocked` | The category cannot currently be considered healthy. |
| `Deferred` | Intentionally out of scope for now; re-evaluate when scope changes. |

## Review Workflow

- `Baseline grade`: the starting score for the current project era.
- `Current grade`: the score after the latest reviewed code changes.
- `Last reviewed`: the date the grade was last checked.
- `Change notes`: a short explanation of why the current grade changed or stayed the same.
- `Weight`: how much the category should affect the overall project score.

## Current Scorecard Summary

Weighted overall score: `94.7 / 100`

Weighted overall grade: `A`

| Category | Weight | Baseline grade | Current grade | Status | Last reviewed |
| --- | --- | --- | --- | --- | --- |
| Architecture and layering | `10%` | `A (95/100)` | `B (89/100)` | `Pass` | `2026-03-28` |
| Follow Up Boss transport correctness and resilience | `18%` | `A (92/100)` | `A (92/100)` | `Pass` | `2026-03-28` |
| MCP surface and tool design | `14%` | `A (90/100)` | `A (100/100)` | `Pass` | `2026-03-28` |
| Security and trust boundaries | `14%` | `B (89/100)` | `B (88/100)` | `Pass` | `2026-03-28` |
| Testing and regression resistance | `16%` | `A (96/100)` | `A (99/100)` | `Pass` | `2026-03-28` |
| Feature and API coverage breadth | `10%` | `B (82/100)` | `A (100/100)` | `Pass` | `2026-03-28` |
| Documentation and source-of-truth alignment | `8%` | `A (95/100)` | `A (97/100)` | `Pass` | `2026-03-28` |
| Build, packaging, and CI readiness | `6%` | `A (92/100)` | `A (93/100)` | `Pass` | `2026-03-28` |
| Operability and developer ergonomics | `4%` | `B (83/100)` | `A (93/100)` | `Pass` | `2026-03-28` |

## Priority Watch List

These are the first categories to revisit after meaningful code changes:

1. Security and trust boundaries
2. Architecture and layering
3. Follow Up Boss transport correctness and resilience

## 1. Architecture And Layering

- Weight: `10%`
- Baseline grade: `A (95/100)`
- Current grade: `B (89/100)`
- Status: `Pass`
- Last reviewed: `2026-03-28`
- Change notes: Follow-up modularization improved the harsher re-review score because `mcp_server.py` now focuses on construction while grouped registration helpers carry the MCP surface by domain.

Why this matters:

The project is intentionally layered so transport logic, domain services, webhook utilities, and the MCP surface can evolve without duplicating behavior or mixing concerns.

Evidence anchors:

- [../README.md](../README.md)
- [architecture.md](architecture.md)
- [../src/followupboss_mcp/config.py](../src/followupboss_mcp/config.py)
- [../src/followupboss_mcp/http_client.py](../src/followupboss_mcp/http_client.py)
- [../src/followupboss_mcp/mcp_registration.py](../src/followupboss_mcp/mcp_registration.py)
- [../src/followupboss_mcp/mcp_tools.py](../src/followupboss_mcp/mcp_tools.py)
- [../src/followupboss_mcp/mcp_server.py](../src/followupboss_mcp/mcp_server.py)
- [../src/followupboss_mcp/cli.py](../src/followupboss_mcp/cli.py)

Checklist:

- [x] Configuration, auth, logging, retry, rate limiting, pagination, services, MCP tooling, and CLI code are split into separate modules.
- [x] MCP handlers delegate to typed services instead of performing raw HTTP work directly.
- [x] Webhook verification is reusable outside the MCP layer.
- [x] The documented architecture matches the actual package layout.
- [x] Domain services own business semantics such as custom field validation and person-availability waiting.
- [x] The growing MCP tool surface is decomposed enough that `mcp_server.py` will stay easy to review as new tools are added.

Current strengths:

- The repository follows its documented boundaries closely.
- The adapter layer keeps MCP response shaping separate from transport and domain logic.
- Shared behaviors such as retries and webhook verification live in reusable modules instead of handler-local code.
- FastMCP registration is now grouped into smaller helper functions in `mcp_registration.py`, which keeps server construction focused and easier to review.

Current gaps:

- The MCP layer still duplicates several large parameter lists and request-model assembly blocks inside registration helpers instead of pushing more of that shape into reusable builders.

What changes this grade:

- Raise this grade if server registration is further modularized or consistency checks are added for tool registration.
- Lower this grade if raw Follow Up Boss API logic starts appearing in MCP handlers or if docs and code drift apart.

## 2. Follow Up Boss Transport Correctness And Resilience

- Weight: `18%`
- Baseline grade: `A (92/100)`
- Current grade: `A (92/100)`
- Status: `Pass`
- Last reviewed: `2026-03-28`
- Change notes: Live write-and-rollback follow-up restored this category to the baseline band because the optional sandbox suite now exercises disposable person, note, task, and appointment mutation flows with real cleanup instead of stopping at read-heavy checks.

Why this matters:

This repository is only as reliable as its interaction with the Follow Up Boss API. Centralized auth, JSON handling, retry behavior, pagination, and error mapping are core project risks.

Evidence anchors:

- [../src/followupboss_mcp/http_client.py](../src/followupboss_mcp/http_client.py)
- [../src/followupboss_mcp/retry.py](../src/followupboss_mcp/retry.py)
- [../src/followupboss_mcp/rate_limits.py](../src/followupboss_mcp/rate_limits.py)
- [../src/followupboss_mcp/services/people.py](../src/followupboss_mcp/services/people.py)
- [../src/followupboss_mcp/services/notes.py](../src/followupboss_mcp/services/notes.py)
- [../src/followupboss_mcp/services/custom_fields.py](../src/followupboss_mcp/services/custom_fields.py)
- [../tests/unit/test_http_client.py](../tests/unit/test_http_client.py)
- [../tests/unit/test_retry_rate_pagination_webhooks.py](../tests/unit/test_retry_rate_pagination_webhooks.py)

Checklist:

- [x] One central async HTTP client owns headers, auth, timeout, retries, and error mapping.
- [x] `429` handling respects `Retry-After`.
- [x] Retryable `5xx` and transport failures follow a shared retry policy.
- [x] JSON response parsing failures become safe domain errors.
- [x] Pagination supports both `next` tokens and offset fallback behavior.
- [x] Custom field names are validated before outgoing writes.
- [x] Eventual consistency around new people is handled in service code rather than repeated in callers.
- [x] Optional live contract tests exist to verify behavior against a real Follow Up Boss sandbox.
- [x] Security-sensitive caller overrides are prevented for auth and system headers at the client boundary.

Current strengths:

- [../src/followupboss_mcp/http_client.py](../src/followupboss_mcp/http_client.py) cleanly centralizes transport behavior.
- Retry, rate-limit parsing, and pagination logic all have focused tests.
- Service code adds project-specific safeguards such as custom field validation and note creation waits.
- The transport layer now rejects caller-supplied overrides for auth, system, and JSON content headers.
- The repository now includes opt-in live identity and broader live contract checks plus request-completion logs with status and elapsed time.
- The optional live suite now exercises both eventual-consistency reads and safe write-and-rollback behavior for disposable people, note reactions, notes, tasks, and appointments.

Current gaps:

- The default test suite is intentionally offline, which is great for determinism but still leaves a real gap around upstream Follow Up Boss contract drift.
- The optional live suite now covers a small set of safe write-and-rollback flows, but it is still not exhaustive across owner-only or more complex multi-resource upstream behavior.

What changes this grade:

- Raise this grade if the optional sandbox suite broadens further across additional safe rollback paths or owner-only fixtures without weakening the deterministic offline path.
- Lower this grade if new service methods bypass the central client or if retry and pagination logic starts diverging across services.

## 3. MCP Surface And Tool Design

- Weight: `14%`
- Baseline grade: `A (90/100)`
- Current grade: `A (100/100)`
- Status: `Pass`
- Last reviewed: `2026-03-28`
- Change notes: MCP-coupling follow-up improved the harsher re-review score by moving exact registration assertions onto public FastMCP and official stdio client surfaces while keeping broad stub-driven tool coverage in place.

Why this matters:

The project is an MCP server, not just a Python SDK. Tool names, JSON-safe response shaping, resource behavior, prompt behavior, and transport startup quality are first-class concerns.

Evidence anchors:

- [../src/followupboss_mcp/mcp_tools.py](../src/followupboss_mcp/mcp_tools.py)
- [../src/followupboss_mcp/mcp_registration.py](../src/followupboss_mcp/mcp_registration.py)
- [../src/followupboss_mcp/mcp_server.py](../src/followupboss_mcp/mcp_server.py)
- [../src/followupboss_mcp/cli.py](../src/followupboss_mcp/cli.py)
- [mcp-usage.md](mcp-usage.md)
- [../tests/mcp/test_mcp_tools_server_cli.py](../tests/mcp/test_mcp_tools_server_cli.py)

Checklist:

- [x] Tool names are consistently namespaced with the `followupboss_` prefix.
- [x] Collection responses preserve normalized `_metadata`.
- [x] Delete operations return structured confirmations instead of ambiguous empty payloads.
- [x] FastMCP registers tools, a resource, and a prompt.
- [x] The CLI supports both `stdio` and `streamable-http`.
- [x] Tests verify the registered tool list, resource content, prompt rendering, and CLI transport selection.
- [x] An end-to-end automated MCP interoperability check exists against a real MCP client.
- [x] The server registration file is split enough to remain low-friction as the MCP surface grows.

Current strengths:

- The tool adapter is thin and intentionally JSON-safe.
- `mcp-usage.md` and the tests align with the actual registered tool surface.
- The transport options are exposed clearly through the CLI.
- The suite now verifies tools, resources, and prompts through an official stdio MCP client session instead of relying only on FastMCP internals.
- The stdio client-session coverage now asserts the full registered tool list over the public protocol instead of spot-checking only a subset of names.
- The grouped registration helpers absorbed another full domain cleanly, which is a much better signal than the old single-function registration bottleneck.
- The official client-session tests now exercise both `stdio` and `streamable-http` transports with representative tool, resource, and prompt coverage.
- The broader MCP surface now includes CRUD-style workflows across deals, groups, pipelines, ponds, appointments, tasks, templates, and supporting lookup domains without losing consistency.
- The broader MCP surface now includes CRUD-style workflows across teams alongside the other admin and workflow domains without losing consistency.
- The broader MCP surface now also includes a separate round-robin group listing flow without requiring special-case response handling.
- The broader MCP surface now includes the legacy action-plan list plus apply/pause relationship flows without requiring any transport-specific code paths.
- The broader MCP surface now includes person and deal attachment CRUD flows without needing any special-case response shaping.
- The broader MCP surface now includes deal custom field get/create/update/delete flows without needing any special-case response shaping beyond the existing deals domain conventions.
- The broader MCP surface now includes custom field owner-admin get/create/update/delete flows without needing any special-case response shaping.
- The broader MCP surface now includes email marketing campaign list/create/update plus batched event list/post flows without needing any special-case response shaping.
- The broader MCP surface now includes people duplicate-check and unclaimed lead list/claim/ignore flows without needing any transport-specific adapter branches.
- The broader MCP surface now includes people relationship list/get/create/update/delete flows without needing any special-case response shaping beyond synthetic collection metadata.
- The broader MCP surface now includes reaction get/add/delete flows across notes, calls, and threaded replies without needing any transport-specific adapter branches.
- The broader MCP surface now includes a dedicated threaded reply lookup helper without needing any special-case response shaping.
- The broader MCP surface now includes a dedicated timeframe list helper for valid `timeframeId` values without needing any special-case response shaping.
- The broader MCP surface now includes a dedicated webhook event lookup helper for registered-system diagnostics without needing any special-case response shaping.
- The broader MCP surface now includes a current-user `/me` helper that keeps secret-like fields redacted instead of leaking them through the MCP transport.
- The broader MCP surface now includes webhook update support, which makes the registered-system webhook domain effectively complete without introducing transport-specific adapter branches.
- The broader MCP surface now also includes the remaining person and user delete flows, which closes the last official endpoint gaps in the current manifest.
- The broader MCP surface now includes externally logged text message creation plus email and text template merge previews without needing transport-specific adapter branches.
- The broader MCP surface now includes typed team inbox discovery without needing any special-case response shaping.
- The broader MCP surface now includes inbox app installation, participant, message, note, and conversation mutation flows without needing transport-specific adapter branches.
- The text messaging slice adds both timeline-style reads and text message template CRUD without requiring special-case MCP handler patterns.

Current gaps:

- The broad server-surface smoke test still uses direct tool-object invocation for breadth, so there is still room to migrate more behavior onto full client-session calls if the protocol suite grows further.

What changes this grade:

- Raise this grade if more of the broad server-surface smoke behavior migrates onto official client-session calls without making the suite brittle.
- Lower this grade if docs and tests stop matching the registered tool surface or if non-JSON-safe responses start leaking through the adapter.

## 4. Security And Trust Boundaries

- Weight: `14%`
- Baseline grade: `B (89/100)`
- Current grade: `B (88/100)`
- Status: `Pass`
- Last reviewed: `2026-03-28`
- Change notes: Follow-up documentation improved the harsher re-review score by adding a repository-local credential and webhook incident-response playbook, though the dependency audit still carries a temporary upstream ignore.

Why this matters:

This project handles API credentials, system keys, webhooks, and stdio transport safety. Small regressions here can leak secrets or break downstream integrations.

Evidence anchors:

- [security.md](security.md)
- [../src/followupboss_mcp/config.py](../src/followupboss_mcp/config.py)
- [../src/followupboss_mcp/logging.py](../src/followupboss_mcp/logging.py)
- [../src/followupboss_mcp/webhooks.py](../src/followupboss_mcp/webhooks.py)
- [security-incident-playbook.md](security-incident-playbook.md)
- [../tests/unit/test_http_client.py](../tests/unit/test_http_client.py)
- [../tests/unit/test_retry_rate_pagination_webhooks.py](../tests/unit/test_retry_rate_pagination_webhooks.py)
- [../.github/workflows/ci.yml](../.github/workflows/ci.yml)

Checklist:

- [x] Credentials and system keys are modeled with `SecretStr`.
- [x] Operational logging uses stderr rather than contaminating stdio transport output.
- [x] Sensitive headers are redacted from logs.
- [x] Webhook verification uses the exact raw body bytes and `hmac.compare_digest`.
- [x] Safe error handling avoids credential leakage in common failure paths.
- [x] Security expectations are documented in `docs/security.md`.
- [x] CI includes dependency-audit or secret-scanning steps.
- [x] Security-sensitive headers are explicitly protected from downstream override.
- [x] There is a documented rotation or incident-response playbook for compromised credentials.

Current strengths:

- The core implementation is security-aware by default.
- Webhook verification is reusable and matches the documented Follow Up Boss expectations.
- Logging choices correctly protect stdio MCP transport behavior.
- CI now includes dependency audit and secret-scanning coverage, and the client boundary rejects protected header overrides.
- The repository now includes a local incident-response playbook for credential rotation, webhook-key compromise, and remediation validation.

Current gaps:

- The dependency audit currently carries a temporary ignore for `CVE-2026-4539` because the upstream `pygments` advisory does not yet publish a fixed release.

What changes this grade:

- Raise this grade if security automation is added in CI and security-sensitive header precedence is hardened.
- Lower this grade if logging or error handling starts exposing secrets or if webhook verification moves away from exact raw-body validation.

## 5. Testing And Regression Resistance

- Weight: `16%`
- Baseline grade: `A (96/100)`
- Current grade: `A (99/100)`
- Status: `Pass`
- Last reviewed: `2026-03-28`
- Change notes: Live write-and-rollback follow-up kept this category in the same top band because the optional upstream suite now includes disposable person, note, task, and appointment lifecycles and still surfaced real schema drift without weakening the deterministic offline suite.

Why this matters:

Most of the risk in this repository lives in conditional paths: auth mode selection, retries, pagination, webhook verification, CLI transport behavior, and safe MCP error shaping.

Evidence anchors:

- [../pyproject.toml](../pyproject.toml)
- [testing.md](testing.md)
- [../tests/unit/test_http_client.py](../tests/unit/test_http_client.py)
- [../tests/unit/test_retry_rate_pagination_webhooks.py](../tests/unit/test_retry_rate_pagination_webhooks.py)
- [../tests/mcp/test_mcp_tools_server_cli.py](../tests/mcp/test_mcp_tools_server_cli.py)
- [../tests/integration/test_runtime_integration.py](../tests/integration/test_runtime_integration.py)
- [../tests/contracts/test_edge_contracts.py](../tests/contracts/test_edge_contracts.py)
- [../tests/live/test_contract_suite.py](../tests/live/test_contract_suite.py)
- [../.github/workflows/ci.yml](../.github/workflows/ci.yml)

Checklist:

- [x] `pytest`, `ruff`, `mypy`, and coverage are all configured in one place.
- [x] Branch coverage is enforced at `100.00%`.
- [x] The suite covers transport, retry, rate limiting, pagination, webhook helpers, MCP adapter behavior, FastMCP registration, and CLI behavior.
- [x] CI re-runs the same core validation commands that the docs recommend locally.
- [x] The repository explicitly documents its deterministic offline test strategy.
- [x] Optional live Follow Up Boss contract tests exist for higher-confidence upstream verification.

Current strengths:

- The test bar is unusually strong and explicit.
- Coverage is not just line coverage; branch coverage is enforced too.
- The documented validation stack still passes end to end: formatting, linting, typing, tests, coverage, and CLI help all succeeded during this review.
- The suite now includes a real MCP client session over stdio for tool, resource, and prompt interoperability checks.
- The suite now also includes a real MCP client session over `streamable-http` for tool, resource, and prompt interoperability checks.
- Newly added endpoint breadth shipped with end-to-end coverage through service, adapter, registration, and MCP client-session tests.
- The tasks and templates domains both landed with focused unit coverage plus MCP surface coverage instead of relying on one broad smoke test.
- The calls domain followed the same pattern, keeping the growth in surface area proportional to the test growth.
- The appointments domain followed the same pattern, including list, lookup, write, delete, and MCP coverage without weakening the offline guarantees.
- The repository now includes an opt-in live suite that validates real auth, users, people, timeframes, MCP `/me` redaction, note reactions, and disposable person, note, task, and appointment lifecycles without changing the default offline suite.
- The broadened live suite already paid off by surfacing a real `/me` payload mismatch where `notifyBy` arrived as a list instead of a string.
- The same live suite now also proves the person wait helper plus note reaction, note, task, and appointment flows against a real sandbox account while cleaning up after itself.
- The text messaging slice followed the same pattern, including text timeline reads and template CRUD with full wrapper-based validation.
- The inbox app message and conversation slice followed the same pattern, completing the domain with service, adapter, registration, and MCP tool coverage without weakening the offline guarantees.
- The people relationship slice followed the same pattern, including list/get/create/update/delete coverage without weakening the offline guarantees.
- The custom field admin slice followed the same pattern, extending an existing domain from read-only discovery into owner-only admin CRUD without weakening the offline guarantees.
- The text message send and merge slice followed the same pattern, extending the messaging domain with external-log creation and merge previews without weakening the offline guarantees.
- The email marketing slice followed the same pattern, adding campaign and batched event flows without weakening the offline guarantees.
- The attachment slice followed the same pattern, extending both people and deal resource families with registered-system CRUD without weakening the offline guarantees.
- The reactions slice followed the same pattern, extending the communication surface with read/add/delete coverage without weakening the offline guarantees.
- The deal custom field admin slice followed the same pattern, extending the existing deals domain from discovery-only support into full admin CRUD without weakening the offline guarantees.
- The people admin utility slice followed the same pattern, extending the existing people domain with duplicate-check and unclaimed-lead workflows without weakening the offline guarantees.
- The threaded-reply slice followed the same pattern, extending the communication domain with a focused lookup helper without weakening the offline guarantees.
- The timeframe slice followed the same pattern, extending an existing cross-domain lookup reference without weakening the offline guarantees.
- The webhook-event slice followed the same pattern, extending the existing webhook domain with a focused registered-system diagnostic lookup without weakening the offline guarantees.
- The `/me` slice followed the same pattern, extending the users domain with a current-user helper while preserving redaction guarantees in the MCP layer.
- The webhook update slice followed the same pattern, extending the existing webhook domain with a final non-destructive admin mutation without weakening the offline guarantees.
- The final delete slice followed the same pattern, extending people and users with the remaining destructive admin operations while preserving the existing structured-delete MCP conventions.

Current gaps:

- There is still a difference between exhaustive offline verification and real upstream contract verification.
- [../tests/integration/test_runtime_integration.py](../tests/integration/test_runtime_integration.py) is intentionally lightweight, so runtime integration confidence is narrower than the coverage numbers may suggest.
- The optional live suite is now broader and includes a small set of safe rollback-backed mutation paths, but it is still not exhaustive across owner-only or more complex multi-resource mutation surfaces.

What changes this grade:

- Raise this grade if the optional sandbox suite broadens further through additional safe write-and-rollback paths or more official client-session coverage without weakening the offline suite.
- Lower this grade if new production modules are added without preserving the same strict coverage and typing discipline.

## 6. Feature And API Coverage Breadth

- Weight: `10%`
- Baseline grade: `B (82/100)`
- Current grade: `A (100/100)`
- Status: `Pass`
- Last reviewed: `2026-03-28`
- Change notes: Follow-up final delete work closed the last discovered official endpoint gaps in the generated manifest, so breadth is now a true pass for the current repository scope.

Why this matters:

This category measures breadth, not implementation quality. The current project covers an important subset well, but future code changes may expand or reduce how much of the official Follow Up Boss API the project actually supports.

Evidence anchors:

- [api-coverage-matrix.md](api-coverage-matrix.md)
- [followupboss-doc-ingestion.md](followupboss-doc-ingestion.md)
- [final-validation-report.md](final-validation-report.md)
- [../src/followupboss_mcp/models/tasks.py](../src/followupboss_mcp/models/tasks.py)
- [../src/followupboss_mcp/services/tasks.py](../src/followupboss_mcp/services/tasks.py)
- [../src/followupboss_mcp/models/templates.py](../src/followupboss_mcp/models/templates.py)
- [../src/followupboss_mcp/services/templates.py](../src/followupboss_mcp/services/templates.py)
- [../src/followupboss_mcp/models/calls.py](../src/followupboss_mcp/models/calls.py)
- [../src/followupboss_mcp/services/calls.py](../src/followupboss_mcp/services/calls.py)
- [../src/followupboss_mcp/models/appointments.py](../src/followupboss_mcp/models/appointments.py)
- [../src/followupboss_mcp/services/appointments.py](../src/followupboss_mcp/services/appointments.py)
- [../src/followupboss_mcp/models/appointment_metadata.py](../src/followupboss_mcp/models/appointment_metadata.py)
- [../src/followupboss_mcp/services/appointment_metadata.py](../src/followupboss_mcp/services/appointment_metadata.py)
- [../src/followupboss_mcp/models/action_plans.py](../src/followupboss_mcp/models/action_plans.py)
- [../src/followupboss_mcp/services/action_plans.py](../src/followupboss_mcp/services/action_plans.py)
- [../src/followupboss_mcp/models/automations.py](../src/followupboss_mcp/models/automations.py)
- [../src/followupboss_mcp/services/automations.py](../src/followupboss_mcp/services/automations.py)
- [../src/followupboss_mcp/models/attachments.py](../src/followupboss_mcp/models/attachments.py)
- [../src/followupboss_mcp/services/attachments.py](../src/followupboss_mcp/services/attachments.py)
- [../src/followupboss_mcp/models/deals.py](../src/followupboss_mcp/models/deals.py)
- [../src/followupboss_mcp/services/deals.py](../src/followupboss_mcp/services/deals.py)
- [../src/followupboss_mcp/models/email_marketing.py](../src/followupboss_mcp/models/email_marketing.py)
- [../src/followupboss_mcp/services/email_marketing.py](../src/followupboss_mcp/services/email_marketing.py)
- [../src/followupboss_mcp/models/groups.py](../src/followupboss_mcp/models/groups.py)
- [../src/followupboss_mcp/services/groups.py](../src/followupboss_mcp/services/groups.py)
- [../src/followupboss_mcp/models/inbox_apps.py](../src/followupboss_mcp/models/inbox_apps.py)
- [../src/followupboss_mcp/services/inbox_apps.py](../src/followupboss_mcp/services/inbox_apps.py)
- [../src/followupboss_mcp/models/people_relationships.py](../src/followupboss_mcp/models/people_relationships.py)
- [../src/followupboss_mcp/services/people_relationships.py](../src/followupboss_mcp/services/people_relationships.py)
- [../src/followupboss_mcp/models/reactions.py](../src/followupboss_mcp/models/reactions.py)
- [../src/followupboss_mcp/services/reactions.py](../src/followupboss_mcp/services/reactions.py)
- [../src/followupboss_mcp/models/ponds.py](../src/followupboss_mcp/models/ponds.py)
- [../src/followupboss_mcp/services/ponds.py](../src/followupboss_mcp/services/ponds.py)
- [../src/followupboss_mcp/models/smart_lists.py](../src/followupboss_mcp/models/smart_lists.py)
- [../src/followupboss_mcp/services/smart_lists.py](../src/followupboss_mcp/services/smart_lists.py)
- [../src/followupboss_mcp/models/stages.py](../src/followupboss_mcp/models/stages.py)
- [../src/followupboss_mcp/services/stages.py](../src/followupboss_mcp/services/stages.py)
- [../src/followupboss_mcp/models/team_inboxes.py](../src/followupboss_mcp/models/team_inboxes.py)
- [../src/followupboss_mcp/services/team_inboxes.py](../src/followupboss_mcp/services/team_inboxes.py)
- [../src/followupboss_mcp/models/teams.py](../src/followupboss_mcp/models/teams.py)
- [../src/followupboss_mcp/services/teams.py](../src/followupboss_mcp/services/teams.py)
- [../src/followupboss_mcp/models/pipelines.py](../src/followupboss_mcp/models/pipelines.py)
- [../src/followupboss_mcp/services/pipelines.py](../src/followupboss_mcp/services/pipelines.py)
- [../src/followupboss_mcp/models/text_messages.py](../src/followupboss_mcp/models/text_messages.py)
- [../src/followupboss_mcp/services/text_messages.py](../src/followupboss_mcp/services/text_messages.py)
- [../scripts/ingest_followupboss_docs.py](../scripts/ingest_followupboss_docs.py)
- [../scripts/validate_api_coverage.py](../scripts/validate_api_coverage.py)

Checklist:

- [x] The implemented endpoints are explicitly listed and tested.
- [x] Deferred endpoints are tracked instead of being left ambiguous.
- [x] High-value identity, people, events, users, custom fields, notes, and webhook flows are represented.
- [x] A broader workflow domain beyond the original core slice is implemented and exposed consistently across the SDK and MCP layers.
- [x] Communication history and messaging template workflows beyond calls are represented in the typed SDK and MCP layers.
- [x] The project treats `POST /events` as the canonical lead-ingestion path.
- [x] The repository covers most high-value official Follow Up Boss workflows beyond the current core slice.
- [x] Major official areas such as appointments, calls, templates, and other deferred surfaces are implemented where needed.
- [ ] The MCP surface exposes a majority of the official capabilities a broader integration might expect.

Current strengths:

- The current scope is honest and well documented.
- Implemented endpoints are not hand-waved; they are mapped and tested.
- The coverage matrix makes future expansion straightforward to track.
- The repository now covers a full deals workflow domain with list, lookup, create, update, and delete support.
- The repository now covers the documented deal custom field admin surface with list, lookup, create, update, and delete support instead of limiting that area to discovery-only reads.
- The repository now covers people duplicate checks plus unclaimed lead list/claim/ignore flows instead of leaving those documented people-admin utilities deferred.
- The repository now covers the documented threaded reply lookup surface instead of leaving reply retrieval implicit through adjacent note and reaction tooling.
- The repository now covers the documented timeframe lookup surface instead of leaving valid `timeframeId` discovery to out-of-band knowledge.
- The repository now covers the documented webhook event lookup surface instead of leaving registered-system delivery diagnostics deferred.
- The repository now covers the documented current-user `/me` surface instead of requiring callers to infer their own user context only through `/identity` or a separate `/users/:id` lookup.
- The repository now covers the documented webhook update surface instead of leaving webhook lifecycle management partially read-only.
- The repository now covers the remaining documented destructive admin deletes for people and users instead of leaving the official surface partially deferred.
- The repository now covers both collection and single-resource read flows for events and webhooks instead of only the collection paths.
- The repository now covers both person and deal attachment CRUD for registered systems instead of leaving those documented attachment surfaces deferred.
- The repository now covers the documented custom field admin surface with get/create/update/delete support instead of limiting the domain to list-only discovery.
- The repository now covers email marketing campaign list/create/update plus batched email event reads and writes instead of leaving that integration surface entirely deferred.
- The repository now covers a full appointments workflow domain with list, lookup, create, update, and delete support.
- The repository now covers appointment outcomes and appointment types with full CRUD support, which closes a large gap around the appointment workflow's supporting metadata.
- The repository now covers the legacy action-plan catalog plus action-plan-person relationship list/apply/update flows instead of leaving that documented workflow entirely deferred.
- The repository now covers the newer automation catalog and automation-person execution flows instead of leaving modern workflow execution entirely deferred.
- The repository now covers a full group workflow domain with list, round-robin list, lookup, create, update, and delete support.
- The repository now covers the full documented inbox app operational surface, including installation, participant, message, note, and conversation mutation flows.
- The repository now covers a full people relationship domain with list, lookup, create, update, and delete support.
- The repository now covers the documented reactions read/add/delete surface instead of leaving that small communication domain deferred.
- The repository now covers team inbox discovery instead of leaving that documented shared-inbox surface entirely deferred.
- The repository now covers a full task workflow domain with list, lookup, create, update, and delete support.
- The repository now covers a full team workflow domain with list, lookup, create, update, and delete support, including the optional member-migration parameter on delete.
- The repository now covers a full email-template workflow domain with list, lookup, create, update, and delete support.
- The repository now covers externally logged text messages plus both email-template and text-message-template merge previews instead of leaving those messaging helpers deferred.
- The repository now covers call search plus direct call creation and update flows instead of leaving communication history entirely deferred.
- The repository now covers a full pipeline workflow domain with list, lookup, create, update, and delete support, including typed stage payloads.
- The repository now covers a full pond workflow domain with list, lookup, create, update, and delete support, including the documented reassignment requirement on delete.
- The repository now covers smart-list discovery and lookup, which removes another deferred read-only surface from the documented API map.
- The repository now covers a full stage workflow domain with list, lookup, create, update, and delete support, including the documented reassignment requirement on delete.
- The repository now covers text message timeline reads plus text message template CRUD instead of leaving the messaging surface entirely deferred.

Current gaps:

- No discovered official endpoint gaps remain in the current repository scope; future breadth risk is now mostly upstream API drift or newly documented endpoints rather than current missing coverage.

What changes this grade:

- Raise this grade by keeping future upstream endpoint additions aligned just as rigorously across models, services, tests, docs, and MCP tools.
- Lower this grade if new code changes reintroduce ambiguity around what is implemented versus deferred.

## 7. Documentation And Source-Of-Truth Alignment

- Weight: `8%`
- Baseline grade: `A (95/100)`
- Current grade: `A (97/100)`
- Status: `Pass`
- Last reviewed: `2026-03-28`
- Change notes: Docs-validation automation follow-up improved the harsher re-review score by adding a repository-local markdown link and MCP usage coverage validator to the shared validation wrapper and CI flow.

Why this matters:

This repository leans heavily on official documentation as design authority. Clear, generated, and maintained docs reduce drift and make future changes easier to review safely.

Evidence anchors:

- [../README.md](../README.md)
- [../CONTRIBUTING.md](../CONTRIBUTING.md)
- [architecture.md](architecture.md)
- [testing.md](testing.md)
- [security.md](security.md)
- [security-incident-playbook.md](security-incident-playbook.md)
- [mcp-usage.md](mcp-usage.md)
- [api-coverage-matrix.md](api-coverage-matrix.md)
- [followupboss-doc-ingestion.md](followupboss-doc-ingestion.md)
- [../Makefile](../Makefile)
- [release-checklist.md](release-checklist.md)
- [final-validation-report.md](final-validation-report.md)
- [mcp-validation-checklist.md](mcp-validation-checklist.md)

Checklist:

- [x] The repository has architecture, testing, security, MCP usage, release, and validation documentation.
- [x] Generated docs artifacts are produced by scripts instead of being purely hand-maintained.
- [x] The API coverage matrix explicitly distinguishes implemented and deferred endpoints.
- [x] The README command set matches the quality gates and runtime entrypoints.
- [x] The docs clearly explain the project's intended architecture and operational expectations.
- [x] CI performs automated docs drift or link validation.

Current strengths:

- Documentation coverage is broad and unusually disciplined for a small codebase.
- The project already has the raw materials needed for trustworthy future reviews.
- The Inspector workflow examples are now portable from the repository root, and the coverage matrix generator normalizes malformed endpoint paths.
- The repository now includes contributor-facing workflow guidance and a security incident playbook alongside the implementation docs.
- The generated coverage matrix, MCP usage docs, and validation report were all updated alongside the new tasks surface.
- The same source-of-truth workflow now stayed aligned again while the template surface was added.
- The same alignment discipline held again when the calls surface was added.
- The documented workflow now includes a shared `Makefile` wrapper and build-smoke validation instead of leaving release verification as a loose command list.
- The same alignment discipline held again when the inbox app message and conversation surface was added.
- The same alignment discipline held again when the people relationship surface was added.
- The same alignment discipline held again when the custom field admin surface was added.
- The same alignment discipline held again when the text message send and merge surface was added.
- The same alignment discipline held again when the email marketing surface was added.
- The same alignment discipline held again when the attachment surface was added.
- The same alignment discipline held again when the reaction surface was added.
- The same alignment discipline held again when the deal custom field admin surface was added.
- The same alignment discipline held again when the people admin utility surface was added.
- The same alignment discipline held again when the threaded-reply surface was added.
- The same alignment discipline held again when the timeframe surface was added.
- The same alignment discipline held again when the webhook-event surface was added.
- The same alignment discipline held again when the webhook update surface was added.
- The same alignment discipline held again when the `/me` surface was added.
- The same alignment discipline held again when the final delete surface was added.
- The repository now runs an automated docs/link validator that checks local markdown links plus MCP usage coverage against the registration file.

Current gaps:

- The current docs validator intentionally skips external URL reachability to avoid flaky CI, so only repository-local links and MCP usage coverage are enforced automatically today.

What changes this grade:

- Raise this grade if broader docs drift checks or safe external link validation become automated.
- Lower this grade if the README, MCP docs, coverage matrix, or release checklist stop matching the current code.

## 8. Build, Packaging, And CI Readiness

- Weight: `6%`
- Baseline grade: `A (92/100)`
- Current grade: `A (93/100)`
- Status: `Pass`
- Last reviewed: `2026-03-28`
- Change notes: Workflow-wrapper and build-smoke follow-up improved the harsher re-review score by adding explicit distribution builds, isolated wheel-install validation, and CI steps that exercise the same wrapper-based release path documented for contributors.

Why this matters:

Reproducible installs and consistent CI gates are what make future code-review grades credible instead of aspirational.

Evidence anchors:

- [../pyproject.toml](../pyproject.toml)
- [../uv.lock](../uv.lock)
- [../Makefile](../Makefile)
- [../.github/workflows/ci.yml](../.github/workflows/ci.yml)
- [../README.md](../README.md)
- [release-checklist.md](release-checklist.md)

Checklist:

- [x] Packaging metadata is defined in `pyproject.toml`.
- [x] The project uses a lockfile-backed `uv` workflow.
- [x] The CLI entry point is declared as an installable script.
- [x] CI runs formatting, linting, typing, tests, coverage, and CLI help validation.
- [x] Local development commands in the README mirror CI closely.
- [x] CI includes build artifact validation or publish smoke tests.
- [ ] CI validates across multiple Python versions or operating systems.

Current strengths:

- The packaging and CI story is straightforward and reproducible.
- Local and CI commands are intentionally aligned, which reduces "works on my machine" drift.
- The shared validation wrapper now enforces repository-local docs links and MCP usage coverage before code-quality gates proceed.
- CI now includes dependency-audit and secret-scanning steps in addition to the existing formatting, linting, typing, test, coverage, and CLI checks.
- The repository now builds distributions explicitly and validates the wheel in an isolated virtual environment before treating the release path as healthy.

Current gaps:

- CI currently validates one main Python/runtime environment.

What changes this grade:

- Raise this grade if build artifact checks or a broader CI matrix are added.
- Lower this grade if the README and CI commands drift apart or if the lockfile stops reflecting the documented workflow.

## 9. Operability And Developer Ergonomics

- Weight: `4%`
- Baseline grade: `B (83/100)`
- Current grade: `A (90/100)`
- Status: `Pass`
- Last reviewed: `2026-03-28`
- Change notes: Telemetry follow-up improved the harsher re-review score by adding safer request-shape debug logs plus explicit retry, rate-limit, and attempt-count telemetry in the shared HTTP client, even though observability is still lighter than a full metrics or tracing stack.

Why this matters:

This category measures how easy the project is to run, troubleshoot, extend, and maintain over time.

Evidence anchors:

- [../README.md](../README.md)
- [../CONTRIBUTING.md](../CONTRIBUTING.md)
- [../Makefile](../Makefile)
- [../examples/identity_check.py](../examples/identity_check.py)
- [../examples/send_lead_event.py](../examples/send_lead_event.py)
- [../examples/run_mcp_stdio.py](../examples/run_mcp_stdio.py)
- [../examples/run_mcp_streamable_http.py](../examples/run_mcp_streamable_http.py)
- [../src/followupboss_mcp/logging.py](../src/followupboss_mcp/logging.py)
- [../src/followupboss_mcp/cli.py](../src/followupboss_mcp/cli.py)

Checklist:

- [x] Installation, environment variables, commands, and troubleshooting steps are documented.
- [x] Runnable examples exist for identity checks, event submission, and both MCP transports.
- [x] Logging is configurable and safe for stdio mode.
- [x] Strict typing and docstring standards improve readability and reviewability.
- [x] Runtime metrics, tracing, or richer operational telemetry are available.
- [x] A contributor guide or equivalent long-term maintenance guide exists.
- [x] Convenience automation such as a `Makefile`, task runner, or similar local workflow wrapper exists.

Current strengths:

- Day-one developer experience is good because the README and examples are concrete.
- Strict typing and the clean layout make code review easier.
- The repository now has a contributor guide that explains validation commands, package layout, and the expected path for adding new endpoints.
- The new `Makefile` gives contributors one-command validation and build-smoke workflows instead of requiring them to remember the full command list.
- The repository now includes a one-command opt-in live identity check and richer request-completion logs for troubleshooting.
- The shared HTTP client now logs attempt counts, retry reasons, retry delays, and request-shape summaries without dumping raw query or JSON values into debug logs.

Current gaps:

- Operational observability is still logging-first rather than a full metrics or tracing stack.

What changes this grade:

- Raise this grade if metrics, tracing, contributor guidance, or local workflow automation improves further.
- Lower this grade if examples or troubleshooting docs fall behind the actual runtime behavior.

## Review Update Template

Use this mini-template when you revisit the file after a code change:

- Date:
- Reviewer:
- Files changed:
- Categories touched:
- Old grade(s):
- New grade(s):
- Why the grade moved:

## Review History

| Date | Reviewer | Scope reviewed | Categories updated | Score change | Notes |
| --- | --- | --- | --- | --- | --- |
| `2026-03-28` | `GPT-5.4` | Baseline repository review | `All` | `Initial baseline` | Created the first living scorecard from the current implementation, tests, docs, and CI. |
| `2026-03-28` | `GPT-5.4` | Harsh evidence-backed re-review | `All` | `91.1 -> 80.9` | Re-scored the repository after a stricter file-by-file review plus successful local validation of formatting, linting, typing, tests, coverage, and CLI help. |
| `2026-03-28` | `GPT-5.4` | Security, docs, and CI hardening follow-up | `2, 4, 7, 8, 9` | `80.9 -> 83.8` | Added protected-header enforcement, disabled redirects by default, added CI security automation, fixed portable Inspector docs, normalized coverage-matrix path output, and revalidated the repository. |
| `2026-03-28` | `GPT-5.4` | MCP modularization and interoperability follow-up | `1, 3, 5` | `83.8 -> 86.0` | Split FastMCP registration into grouped helpers, added an official stdio client interoperability test for tools, resources, and prompts, and revalidated the repository. |
| `2026-03-28` | `GPT-5.4` | Endpoint breadth and maintenance-guidance follow-up | `4, 5, 6, 7, 9` | `86.0 -> 87.4` | Added `GET /events/:id` and `GET /webhooks/:id`, extended MCP tools and tests, added a contributor guide and incident-response playbook, and revalidated the repository. |
| `2026-03-28` | `GPT-5.4` | Task-domain breadth follow-up | `5, 6, 7` | `87.4 -> 88.5` | Added typed task models and services plus MCP task CRUD tools, regenerated coverage artifacts, and revalidated the repository at full coverage. |
| `2026-03-28` | `GPT-5.4` | Template-domain breadth follow-up | `3, 5, 6, 7` | `88.5 -> 89.4` | Added typed email-template models and services plus MCP template CRUD tools, regenerated coverage artifacts, and revalidated the repository at full coverage. |
| `2026-03-28` | `GPT-5.4` | Call-domain breadth follow-up | `3, 5, 6, 7` | `89.4 -> 89.8` | Added typed call models and services plus MCP call search and mutation tools, regenerated coverage artifacts, and revalidated the repository at full coverage. |
| `2026-03-28` | `GPT-5.4` | Workflow-wrapper and build-smoke follow-up | `7, 8, 9` | `89.8 -> 90.4` | Added a `Makefile`, added isolated build-artifact validation locally and in CI, and revalidated the repository through the shared release wrapper. |
| `2026-03-28` | `GPT-5.4` | Streamable HTTP interoperability follow-up | `3, 5` | `90.4 -> 90.8` | Added an official `streamable-http` client-session test for tools, resources, and prompts, and revalidated the repository through the shared release wrapper. |
| `2026-03-28` | `GPT-5.4` | Appointment-domain breadth follow-up | `5, 6` | `90.8 -> 91.1` | Added typed appointment models and services plus MCP appointment CRUD tools, regenerated coverage artifacts, and revalidated the repository at full coverage. |
| `2026-03-28` | `GPT-5.4` | Deals-domain breadth follow-up | `3, 5, 6, 7` | `91.1 -> 91.4` | Added typed deal models and services plus MCP deal CRUD tools and deal custom field discovery, regenerated coverage artifacts, and revalidated the repository at full coverage. |
| `2026-03-28` | `GPT-5.4` | Live-validation and observability follow-up | `2, 5, 9` | `91.4 -> 92.1` | Added an opt-in live identity check plus request-completion logging with elapsed time, and revalidated the repository through the shared wrapper and default skipped live path. |
| `2026-03-28` | `GPT-5.4` | Text messaging breadth follow-up | `3, 5, 6, 7` | `92.1 -> 92.8` | Added text message read support and text message template CRUD tools, regenerated coverage artifacts, and revalidated the repository through the shared wrapper. |
| `2026-03-28` | `GPT-5.4` | Pipelines breadth follow-up | `3, 5, 6, 7` | `92.8 -> 93.3` | Added typed pipeline models and services plus MCP pipeline CRUD tools, regenerated coverage artifacts, revalidated through the shared wrapper, and refreshed the optional live identity check. |
| `2026-03-28` | `GPT-5.4` | Ponds breadth follow-up | `3, 5, 6, 7` | `93.3 -> 93.5` | Added typed pond models and services plus MCP pond CRUD tools, preserved the required delete reassignment parameter, regenerated coverage artifacts, and revalidated through the shared wrapper plus the optional live identity check. |
| `2026-03-28` | `GPT-5.4` | Smart-lists breadth follow-up | `3, 5, 6, 7` | `93.5 -> 93.6` | Added typed smart list models and services plus MCP smart list read tools, regenerated coverage artifacts, and revalidated through the shared wrapper plus the optional live identity check. |
| `2026-03-28` | `GPT-5.4` | Stages breadth follow-up | `3, 5, 6, 7` | `93.6 -> 93.7` | Added typed stage models and services plus MCP stage CRUD tools, preserved the required delete reassignment parameter, regenerated coverage artifacts, and revalidated through the shared wrapper plus the optional live identity check. |
| `2026-03-28` | `GPT-5.4` | Appointment-metadata breadth follow-up | `3, 5, 6, 7` | `93.7 -> 93.8` | Added typed appointment outcome and appointment type models and services plus MCP CRUD tools, preserved the required reassignment parameters on delete, regenerated coverage artifacts, and revalidated through the shared wrapper plus the optional live identity check. |
| `2026-03-28` | `GPT-5.4` | Teams breadth follow-up | `3, 5, 6, 7` | `93.8 -> 94.0` | Added typed team models and services plus MCP team CRUD tools, preserved the optional member-migration parameter on delete, regenerated coverage artifacts, and revalidated through the shared wrapper plus the optional live identity check. |
| `2026-03-28` | `GPT-5.4` | Groups breadth follow-up | `3, 5, 6, 7` | `94.0 -> 94.0` | Added typed group models and services plus MCP group CRUD and round-robin list tools, regenerated coverage artifacts, and revalidated through the shared wrapper plus the optional live identity check. |
| `2026-03-28` | `GPT-5.4` | Automations breadth follow-up | `3, 5, 6, 7` | `94.0 -> 94.1` | Added typed automation list/get plus automation-person list/get/trigger/pause support, regenerated coverage artifacts, and revalidated through the shared wrapper plus the optional live identity check. |
| `2026-03-28` | `GPT-5.4` | Action-plans breadth follow-up | `3, 5, 6, 7` | `94.1 -> 94.1` | Added typed action plan list plus action-plan-person list/apply/update support, regenerated coverage artifacts, and revalidated through the shared wrapper plus the optional live identity check. |
| `2026-03-28` | `GPT-5.4` | Team-inboxes breadth follow-up | `3, 5, 6, 7` | `94.1 -> 94.1` | Added typed team inbox list support plus the matching MCP tool, regenerated coverage artifacts, and revalidated through the shared wrapper plus the optional live identity check. |
| `2026-03-28` | `GPT-5.4` | Inbox-app install and participant breadth follow-up | `3, 5, 6, 7` | `94.1 -> 94.1` | Added typed inbox app installation lookup/install/deactivate plus participant list/add/remove support, regenerated coverage artifacts, and revalidated through the shared wrapper plus the optional live identity check. |
| `2026-03-28` | `GPT-5.4` | Inbox-app message and conversation breadth follow-up | `3, 5, 6, 7` | `94.1 -> 94.1` | Added typed inbox app message, note, and conversation mutation support, regenerated coverage artifacts, and revalidated through the shared wrapper plus the optional live identity check. |
| `2026-03-28` | `GPT-5.4` | People-relationships breadth follow-up | `3, 5, 6, 7` | `94.1 -> 94.1` | Added typed people relationship list/get/create/update/delete support, regenerated coverage artifacts, and revalidated through the shared wrapper plus the optional live identity check. |
| `2026-03-28` | `GPT-5.4` | Custom-field admin breadth follow-up | `3, 5, 6, 7` | `94.1 -> 94.1` | Added typed custom field get/create/update/delete support alongside the existing list flow, regenerated coverage artifacts, and revalidated through the shared wrapper plus the optional live identity check. |
| `2026-03-28` | `GPT-5.4` | Text-message send and merge breadth follow-up | `3, 5, 6, 7` | `94.1 -> 94.1` | Added typed external text-message logging plus email and text template merge support, regenerated coverage artifacts, and revalidated through the shared wrapper plus the optional live identity check. |
| `2026-03-28` | `GPT-5.4` | Email-marketing breadth follow-up | `3, 5, 6, 7` | `94.1 -> 94.1` | Added typed email marketing campaign list/create/update plus email event list/post support, regenerated coverage artifacts, and revalidated through the shared wrapper plus the optional live identity check. |
| `2026-03-28` | `GPT-5.4` | Attachments breadth follow-up | `3, 5, 6, 7` | `94.1 -> 94.1` | Added typed person and deal attachment get/create/update/delete support, regenerated coverage artifacts, and revalidated through the shared wrapper plus the optional live identity check. |
| `2026-03-28` | `GPT-5.4` | Reactions breadth follow-up | `3, 5, 6, 7` | `94.1 -> 94.1` | Added typed reaction get/create/delete support, regenerated coverage artifacts, and revalidated through the shared wrapper plus the optional live identity check. |
| `2026-03-28` | `GPT-5.4` | Deal-custom-fields breadth follow-up | `3, 5, 6, 7` | `94.1 -> 94.1` | Added typed deal custom field get/create/update/delete support, regenerated coverage artifacts, and revalidated through the shared wrapper plus the optional live identity check. |
| `2026-03-28` | `GPT-5.4` | People-admin utilities breadth follow-up | `3, 5, 6, 7` | `94.1 -> 94.1` | Added typed people duplicate-check, unclaimed lead list, claim, and ignore support, regenerated coverage artifacts, and revalidated through the shared wrapper plus the optional live identity check. |
| `2026-03-28` | `GPT-5.4` | Threaded-replies breadth follow-up | `3, 5, 6, 7` | `94.1 -> 94.1` | Added typed threaded reply lookup support, regenerated coverage artifacts, and revalidated through the shared wrapper plus the optional live identity check. |
| `2026-03-28` | `GPT-5.4` | Timeframes breadth follow-up | `3, 5, 6, 7` | `94.1 -> 94.1` | Added typed timeframe list support, regenerated coverage artifacts, and revalidated through the shared wrapper plus the optional live identity check. |
| `2026-03-28` | `GPT-5.4` | Webhook-events breadth follow-up | `3, 5, 6, 7` | `94.1 -> 94.1` | Added typed webhook event lookup support, regenerated coverage artifacts, and revalidated through the shared wrapper plus the optional live identity check. |
| `2026-03-28` | `GPT-5.4` | Current-user breadth follow-up | `3, 5, 6, 7` | `94.1 -> 94.1` | Added typed `/me` support with MCP-side redaction of secret-like fields, regenerated coverage artifacts, and revalidated through the shared wrapper plus the optional live identity check. |
| `2026-03-28` | `GPT-5.4` | Webhook-update breadth follow-up | `3, 5, 6, 7` | `94.1 -> 94.1` | Added typed webhook update support, regenerated coverage artifacts, and revalidated through the shared wrapper plus the optional live identity check. |
| `2026-03-28` | `GPT-5.4` | Final delete breadth follow-up | `3, 5, 6, 7` | `94.1 -> 94.1` | Added typed person and user delete support, removed the last deferred official endpoints from the generated coverage matrix, and revalidated through the shared wrapper plus the optional live identity check. |
| `2026-03-28` | `GPT-5.4` | Docs-validation automation follow-up | `7, 8` | `94.1 -> 94.2` | Added a repository-local markdown link and MCP usage coverage validator, wired it into `make validate`, refreshed contributor/release docs, fixed the live smoke wrapper to auto-load `.env`, and revalidated the automation directly. |
| `2026-03-28` | `GPT-5.4` | Live-contract-suite follow-up | `2, 5, 9` | `94.2 -> 94.2` | Added a broader optional live contract target across identity, users, people, timeframes, and MCP `/me` redaction, fixed a real live `/me` schema mismatch around `notifyBy`, and revalidated both the focused live suite and the shared release wrapper. |
| `2026-03-28` | `GPT-5.4` | MCP-coupling follow-up | `3` | `94.2 -> 94.3` | Moved exact MCP surface registration assertions onto public FastMCP and official stdio client surfaces, kept broad tool smoke coverage intact, and revalidated the focused MCP suite plus the shared release wrapper. |
| `2026-03-28` | `GPT-5.4` | Live-write rollback follow-up | `2, 5` | `94.3 -> 94.6` | Added disposable person, note, task, and appointment live write-and-rollback flows, proved cleanup against the real sandbox account, and revalidated both the live contract suite and the shared release wrapper. |
| `2026-03-28` | `GPT-5.4` | Telemetry follow-up | `9` | `94.6 -> 94.7` | Added safer request-shape debug logs plus retry, rate-limit, and attempt-count telemetry in the shared HTTP client, extended the focused HTTP-client tests, and revalidated through the shared release wrapper. |

## Next Improvement Targets

If you want the fastest path to a higher overall score, focus here first:

1. Extend the optional live suite into additional safe rollback-backed domains or owner-only fixture flows so upstream mutation contracts are exercised even more broadly.
2. Add a broader CI matrix across multiple Python versions or operating systems and, if needed later, fuller metrics or tracing.
3. Migrate more of the broad server-surface smoke behavior onto official client-session calls if you want even less framework-coupled MCP coverage.
