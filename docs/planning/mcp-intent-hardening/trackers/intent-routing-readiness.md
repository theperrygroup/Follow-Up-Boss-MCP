# Intent Routing Readiness

## Purpose

This tracker follows whether natural user intents have one safe, documented MCP
tool path.

## Current Snapshot

Snapshot date: `2026-05-18`

| Intent family | Current state | Required next proof |
| --- | --- | --- |
| "My latest lead" | In progress | Existing helper, registration description, public docs, validation checklist, and registered metadata tests now prefer it over broad people search; live validation remains open. |
| "My overdue tasks" | In progress | Existing helper, adapter request-shape tests, public docs, validation checklist, and registered metadata tests are present; live validation remains open. |
| "My tasks today" | In progress | Existing helper, adapter request-shape tests, public docs, validation checklist, and registered metadata tests are present; live validation remains open. |
| "Count people in smart list" | Planned | Existing broad-search wording hints at smart-list counting; needs explicit routing proof or a deliberate non-helper decision. |
| "Find or update a specific record" | Planned | Need rules for when broad search is acceptable versus when a get/update/delete requires explicit IDs. |
| "Create or mutate from vague intent" | Planned | Need mutation safety wording and tests that tool schemas require typed payloads or explicit identifiers. |
| Vague chatbot prompt corpus | In progress | `src/followupboss_mcp/battle_tests.py` now encodes the first `BT-READ-*` corpus and route assertions; additional prompt batches remain planned. |

## Routing Rules To Preserve

- If a narrow helper exists for a common "my" request, generic tools should name
  that helper in their descriptions.
- Generic search can remain flexible, but it should not be the preferred route
  for a high-confidence owned intent.
- The authenticated user's identity should be resolved by the adapter or service
  boundary, not by asking the client to infer a user ID.
- A future helper should be added only when it removes meaningful ambiguity or
  enforces a safer default.
- Vague prompt variants should be tested as prompt-to-tool-to-oracle scenarios,
  not just as isolated tool calls.

## Open Questions

- Should "my upcoming tasks" become a separate helper, or should it remain a
  documented `followupboss_list_tasks` filter pattern?
- Should smart-list counting get a helper, or is the existing two-step
  `followupboss_list_smart_lists` plus `followupboss_search_people` guidance
  sufficient?
- Should destructive operations include stronger description text that forbids
  inferred IDs from prior ambiguous search results?
- Which battle-test client should be canonical for observed tool selection:
  Cursor, MCP Inspector, a local harness, or multiple clients?

## Current Conclusion

- Routing is partially hardened for newest assigned lead and two task due
  buckets, including registered metadata tests, first-pass public docs, and a
  read-only battle-test evaluator. The broader intent map and non-read-only
  prompt batches remain planned and should be implemented incrementally with
  tests before public docs claim full coverage.
