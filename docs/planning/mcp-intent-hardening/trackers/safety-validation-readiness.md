# Safety And Validation Readiness

## Purpose

This tracker follows whether intent hardening is backed by fail-closed behavior,
safe mutation boundaries, and repeatable validation proof.

## Current Snapshot

Snapshot date: `2026-05-18`

| Safety lens | Status | Current answer |
| --- | --- | --- |
| Identity-required reads | In progress | Existing latest-lead and task helpers require authenticated-user identity before scoped requests can be built. |
| Broad-query avoidance | In progress | People search and task list descriptions now point common owned intents to narrow helpers, but this has not been audited across the full MCP surface. |
| Mutation safeguards | In progress | Person and task update/delete descriptions now require explicit IDs; broader mutation wording still needs a focused pass. |
| Registered-surface tests | In progress | Existing MCP tests assert helper names, calls, and first-pass registered description hardening; future helper taxonomy needs matching coverage. |
| Public docs validation | In progress | `docs/mcp-usage.md` and `docs/mcp-validation-checklist.md` now include first-pass intent and explicit-ID scenarios. |
| Live validation | Planned | Live validation should follow offline implementation and doc updates. |
| Battle-test API oracle | In progress | Read-only oracle helpers are checked in for latest lead, overdue tasks, today's tasks, and unsupported note search; no live run evidence or mutation oracle exists yet. |

## Validation Expectations

- Adapter tests should prove exact request construction for identity-scoped
  helper methods.
- Registered-surface tests should prove the helper is advertised with the
  intended name.
- Public docs should include a small intent-to-tool table for common ambiguous
  requests.
- The live validation checklist should include at least one read-only helper
  intent and one mutation-safety scenario.
- Battle-test runs should capture selected MCP tools, arguments, MCP responses,
  direct API oracle results, and cleanup status.

## Safety Rules To Preserve

- Identity absence must fail closed before a broad upstream request is issued.
- Mutation tools should not promise inference from natural-language intent when
  the API requires explicit IDs.
- Tests should cover safe failure paths, not just successful helper calls.
- Live validation should run against sandbox or disposable data when mutation
  scenarios are involved.
- A side-effecting battle-test prompt is not passing until direct API proof shows
  only the intended disposable fixture changed.

## Current Conclusion

- Safety proof is partially present for existing identity-scoped helpers, but
  the initiative is not safety-complete until broader mutation wording, real
  API-oracle battle-test runs, mutation oracle checks, and live validation
  scenarios land.
