# ADR: MCP Intent Hardening Boundary

## Status

Accepted for planning on `2026-05-08`.

## Context

The MCP surface exposes many typed Follow Up Boss tools. Some user requests are
high-level and ownership-sensitive, such as "my latest lead," "my overdue
tasks," and "what do I need to do today?" Those requests should resolve to
narrow tools that encode identity-aware defaults instead of relying on a broad
search or list call with caller-supplied filters.

The current working tree already includes several checked-in intent anchors:

- `followupboss_get_latest_lead` in `src/followupboss_mcp/mcp_registration.py`
- `followupboss_list_my_overdue_tasks` in `src/followupboss_mcp/mcp_registration.py`
- `followupboss_list_my_tasks_due_today` in `src/followupboss_mcp/mcp_registration.py`
- authenticated-user scoping in `FollowUpBossToolAdapter` in
  `src/followupboss_mcp/mcp_tools.py`
- offline MCP registration and adapter assertions in
  `tests/mcp/test_mcp_tools_server_cli.py`

Those anchors are useful but not a complete intent-hardening program. The
remaining work is to define the broader taxonomy, keep ambiguous routing safe,
and validate that docs, tool descriptions, and tests keep the intended tools
authoritative.

## Decision

This planning tree owns MCP intent hardening for Follow Up Boss tool selection,
tool descriptions, request defaults, validation evidence, and public MCP docs.

The initiative includes:

- identity-scoped read helpers for common "my" intents
- clear tool descriptions that steer clients away from broad tools when a narrow
  helper exists
- fail-closed behavior when authenticated-user identity is required but absent
- mutation and destructive-tool wording that requires explicit identifiers and
  avoids inference from vague intent
- tests that assert both adapter behavior and registered MCP tool availability
- docs and validation checklist updates after runtime changes land

The initiative does not include:

- replacing the Follow Up Boss API model layer with a separate intent engine
- adding model-provider-specific prompt hacks that are not expressed in the MCP
  surface
- broad hosted auth or tenant-isolation work except where intent helpers rely on
  the active authenticated identity
- live-account validation evidence before code and offline tests define the
  expected contract

## Invariants

- "My" means the authenticated Follow Up Boss user resolved from the active
  runtime, not an arbitrary owner name inferred by the client.
- Intent helpers must preserve pagination and field-selection affordances when
  the underlying API supports them.
- Intent helpers that require identity must fail closed before issuing an
  upstream broad query when identity is unavailable.
- Generic tools can still expose documented Follow Up Boss filters, but their
  descriptions should point to the narrow helper for common ambiguous requests.
- Destructive and externally visible mutations must require explicit IDs or
  typed payloads. Vague user intent alone is not sufficient proof for side
  effects.

## Consequences

- New intent helpers should be small, typed wrappers over existing services
  unless a service-level abstraction is genuinely required.
- Every new helper needs registration, adapter tests, and registered-surface
  tests before it can be called live.
- Public docs can describe planned direction, but must distinguish planned
  helpers from checked-in helper names.
- Future phase proof files should use the
  `execution/intent_PHASE_##_<slug>.md` naming pattern when a slice needs
  durable evidence.
