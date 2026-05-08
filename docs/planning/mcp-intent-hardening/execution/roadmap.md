# MCP Intent Hardening Task Roadmap

This roadmap converts the current understanding of the initiative into a
phased, dependency-aware task plan.

Treat this file as the baseline dependency map. For the freshest checked-in
status, use `execution-plan.md` plus the focused trackers.

## Scope And Evidence

- Source references:
  - `src/followupboss_mcp/mcp_registration.py`
  - `src/followupboss_mcp/mcp_tools.py`
  - `src/followupboss_mcp/mcp_server.py`
  - `tests/mcp/test_mcp_tools_server_cli.py`
  - `docs/mcp-usage.md`
  - `docs/mcp-validation-checklist.md`
- Primary code or doc anchors:
  - `followupboss_get_latest_lead`
  - `followupboss_list_my_overdue_tasks`
  - `followupboss_list_my_tasks_due_today`
  - `FollowUpBossToolAdapter._search_people_with_default_scope`
  - `FollowUpBossToolAdapter._list_my_tasks_by_due`
- Historical blockers at roadmap creation:
  - No prior `docs/planning/` root existed for this work.
  - Existing helper anchors did not yet have a complete planning, docs, and live
    validation sequence.

## Current Checked-In Progress Snapshot

- Planning scaffold exists.
- Runtime has initial intent helper anchors.
- Full taxonomy, docs, safety wording, and validation remain open.

## Harsh Sequencing Rule

- Do not add live-validation claims before offline tests prove the intended
  helper behavior.
- Do not add more helpers until the existing helper taxonomy and generic-tool
  descriptions are inventoried.

## Phase 0 - Inventory And Classification

### P0-001 - Classify Current MCP Surface By Intent Risk

- Why this task exists: A full inventory prevents ad hoc helpers and reveals
  where generic tools need stronger guidance.
- Exact files or modules affected: `src/followupboss_mcp/mcp_registration.py`,
  `docs/planning/mcp-intent-hardening/trackers/intent-routing-readiness.md`.
- Dependency prerequisites: Planning scaffold.
- Severity: High.
- Estimated complexity: Medium.
- Feature domain: MCP registration and docs.
- Whether this is: implementation and docs.
- Acceptance criteria: Each tool family is classified as narrow helper, generic
  read, explicit-ID mutation, broad mutation, or administrative action.
- What could break if this task is skipped: Later helper additions may duplicate
  existing behavior or leave risky generic tools under-specified.

### P0-002 - Confirm Existing Helper Semantics

- Why this task exists: Existing helpers should become the baseline for future
  patterns.
- Exact files or modules affected: `src/followupboss_mcp/mcp_tools.py`,
  `tests/mcp/test_mcp_tools_server_cli.py`.
- Dependency prerequisites: P0-001.
- Severity: High.
- Estimated complexity: Low.
- Feature domain: MCP adapter tests.
- Whether this is: implementation and tests.
- Acceptance criteria: Tests prove identity-scoped request construction,
  fail-closed identity absence, pagination pass-through, and registered tool
  availability for existing helpers.
- What could break if this task is skipped: The plan may assume behavior that is
  not protected by tests.

## Phase 1 - Description And Schema Hardening

### P1-001 - Harden Generic Tool Descriptions

- Why this task exists: Tool descriptions are the primary MCP-native routing
  surface for clients.
- Exact files or modules affected: `src/followupboss_mcp/mcp_registration.py`,
  `tests/mcp/test_mcp_tools_server_cli.py`.
- Dependency prerequisites: P0-001, P0-002.
- Severity: High.
- Estimated complexity: Medium.
- Feature domain: MCP registration.
- Whether this is: implementation and tests.
- Acceptance criteria: Broad search/list tools point to narrow helpers for
  known ambiguous intents, and tests cover key description substrings or
  registered behavior where practical.
- What could break if this task is skipped: Clients may keep choosing broad
  tools for narrow user-specific requests.

### P1-002 - Audit Mutation Safety Wording

- Why this task exists: Vague intent should not cause record updates or deletes
  without explicit identifiers or typed payloads.
- Exact files or modules affected: `src/followupboss_mcp/mcp_registration.py`,
  `docs/mcp-validation-checklist.md`.
- Dependency prerequisites: P0-001.
- Severity: High.
- Estimated complexity: Medium.
- Feature domain: MCP registration and validation docs.
- Whether this is: implementation, tests, and docs.
- Acceptance criteria: Mutation descriptions distinguish explicit-ID operations
  from discovery helpers and the validation checklist includes a mutation-safety
  scenario.
- What could break if this task is skipped: A client can over-trust ambiguous
  prior search results before a side-effecting call.

## Phase 2 - Helper Expansion Or Rejection

### P2-001 - Rank Candidate Intent Helpers

- Why this task exists: Not every natural-language pattern deserves a tool.
- Exact files or modules affected: `docs/planning/mcp-intent-hardening/trackers/intent-routing-readiness.md`,
  `src/followupboss_mcp/mcp_registration.py`.
- Dependency prerequisites: P0-001, P1-001.
- Severity: Medium.
- Estimated complexity: Medium.
- Feature domain: MCP design.
- Whether this is: docs and implementation decision.
- Acceptance criteria: Each candidate is accepted, rejected, or deferred with a
  reason tied to ambiguity, safety, duplication, and testability.
- What could break if this task is skipped: Tool surface growth can become noisy
  and harder for clients to select correctly.

### P2-002 - Implement Accepted Helpers

- Why this task exists: Accepted helpers should encode safe defaults in runtime
  code rather than relying on prompt interpretation.
- Exact files or modules affected: `src/followupboss_mcp/mcp_tools.py`,
  `src/followupboss_mcp/mcp_registration.py`, relevant model or service files.
- Dependency prerequisites: P2-001.
- Severity: Medium to High depending on helper.
- Estimated complexity: Medium.
- Feature domain: MCP adapter and registration.
- Whether this is: implementation and tests.
- Acceptance criteria: Each helper has typed input, Google-style docstrings
  where new Python functions are added, thorough type hints, adapter coverage,
  and registered-surface coverage.
- What could break if this task is skipped: Planned intent semantics remain only
  in docs.

## Phase 3 - Documentation And Validation

### P3-001 - Publish Intent-To-Tool Usage Guidance

- Why this task exists: Operators and users need a concise guide for which tool
  serves common ambiguous requests.
- Exact files or modules affected: `docs/mcp-usage.md`,
  `docs/mcp-validation-checklist.md`.
- Dependency prerequisites: P1-001, P2-002 for any new helpers.
- Severity: Medium.
- Estimated complexity: Low.
- Feature domain: docs.
- Whether this is: docs-only.
- Acceptance criteria: Public docs list common intents, preferred tools, broad
  tool fallbacks, and safety notes.
- What could break if this task is skipped: The registered behavior remains hard
  to validate or teach.

### P3-002 - Run Offline And Live Validation

- Why this task exists: Hardening must be proven in both unit-level behavior and
  MCP client-facing behavior.
- Exact files or modules affected: tests and validation docs named in
  `ARTIFACT_PATH_INDEX.md`.
- Dependency prerequisites: P3-001.
- Severity: High.
- Estimated complexity: Medium.
- Feature domain: tests and live validation.
- Whether this is: validation.
- Acceptance criteria: Relevant pytest targets pass, lints show no introduced
  issues, and live validation records the read-only intent helpers plus one
  mutation-safety scenario.
- What could break if this task is skipped: The release can claim a safety
  posture that has not been exercised.
