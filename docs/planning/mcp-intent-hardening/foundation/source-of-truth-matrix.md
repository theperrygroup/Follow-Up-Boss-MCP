# MCP Intent Hardening Source Of Truth Matrix

## Purpose

This matrix defines which artifacts are authoritative for MCP intent hardening.
It prevents planning docs from becoming the source of runtime truth.

## Authority Matrix

| Question | Source of truth | Supporting artifacts | Update rule |
| --- | --- | --- | --- |
| Which MCP tools are registered? | `src/followupboss_mcp/mcp_registration.py` | `tests/mcp/test_mcp_tools_server_cli.py`, `docs/mcp-usage.md` | Update tests with code, then update public docs. |
| What does an intent helper do at runtime? | `src/followupboss_mcp/mcp_tools.py` | domain services under `src/followupboss_mcp/services/`, request models under `src/followupboss_mcp/models/` | Runtime behavior is live only after adapter tests prove the exact request shape. |
| What server-level guidance does the MCP expose? | `src/followupboss_mcp/mcp_server.py` | MCP registration descriptions | Keep instructions concise and aligned with registered helper names. |
| What behavior is covered offline? | `tests/mcp/test_mcp_tools_server_cli.py` and relevant unit tests | `docs/testing.md` | Add regression coverage before treating a helper as ready for live validation. |
| What proves a vague chatbot prompt went the right direction? | `src/followupboss_mcp/battle_tests.py`, `src/followupboss_mcp/battle_test_ai.py`, and future run artifacts | `tests/unit/test_battle_tests.py`, `tests/unit/test_battle_test_ai.py`, `docs/planning/mcp-intent-hardening/execution/intent-battle-test-plan.md`, `docs/planning/mcp-intent-hardening/foundation/battle-test-verification-adr.md` | Treat the direct API oracle and captured MCP transcript as run evidence; planning docs only define the expected contract. |
| What should users and operators read? | `docs/mcp-usage.md` and `docs/mcp-validation-checklist.md` | `docs/architecture.md`, `docs/testing.md` | Update after registered-surface and adapter behavior are settled. |
| What is planned but not live? | `docs/planning/mcp-intent-hardening/execution/execution-plan.md` | focused trackers and active plan | Keep status language as planned until code and tests land. |

## Current Runtime Anchors

| Anchor | Current checked-in meaning | Planning implication |
| --- | --- | --- |
| `followupboss_get_latest_lead` | Registered helper intended for newest lead assigned to the authenticated user. | Treat as an existing anchor, then harden docs and validation around it. |
| `followupboss_list_my_overdue_tasks` | Registered helper intended for incomplete overdue tasks assigned to the authenticated user. | Treat as an existing anchor, then harden docs and validation around it. |
| `followupboss_list_my_tasks_due_today` | Registered helper intended for incomplete tasks due today assigned to the authenticated user. | Treat as an existing anchor, then harden docs and validation around it. |
| `FollowUpBossToolAdapter._search_people_with_default_scope` | Applies authenticated-user scope unless explicit owner or pond inclusion changes the request. | Needs clear tests and docs so default scoping is understood rather than accidental. |
| `FollowUpBossToolAdapter._list_my_tasks_by_due` | Builds identity-scoped task-list requests for canonical due buckets. | Needs broader intent taxonomy and validation proof for future due-bucket helpers. |
| `src/followupboss_mcp/battle_tests.py` | Encodes the first read-only battle-test scenarios, route evaluator, transcript shape, typed oracle helpers, run summaries, JSON artifact writing, and default model-profile run labels. | Treat as reusable evaluator code and artifact-boundary code, not evidence that a live chatbot run has happened. |
| `src/followupboss_mcp/battle_test_ai.py` | Encodes OpenAI and Anthropic route-selection adapters and the AI-backed model-profile runner. | Treat as executable harness code, not evidence that a live run artifact exists. |

## Drift Rules

- If registration, tests, and docs disagree, treat registration plus tests as the
  immediate runtime truth and update docs.
- If code and planning docs disagree, update planning status instead of
  rewriting code to match stale planning language.
- If public docs name a helper that no longer exists, fix docs before the next
  release validation.
- If a future intent helper needs a new model or service abstraction, record the
  rationale in the active plan before implementation starts.
- If a battle-test prompt, registered description, and API oracle disagree,
  record the failure against the scenario run first, then update code, tests, or
  docs according to the artifact that was wrong.
