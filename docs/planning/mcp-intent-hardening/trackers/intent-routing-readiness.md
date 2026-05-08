# Intent Routing Readiness

## Purpose

This tracker follows whether natural user intents have one safe, documented MCP
tool path.

## Current Snapshot

Snapshot date: `2026-05-08`

| Intent family | Current state | Required next proof |
| --- | --- | --- |
| "My latest lead" | In progress | Existing helper, registration description, public docs, validation checklist, and registered metadata tests now prefer it over broad people search; live validation remains open. |
| "My overdue tasks" | In progress | Existing helper, adapter request-shape tests, public docs, validation checklist, and registered metadata tests are present; live validation remains open. |
| "My tasks today" | In progress | Existing helper, adapter request-shape tests, public docs, validation checklist, and registered metadata tests are present; live validation remains open. |
| "Count people in smart list" | Planned | Existing broad-search wording hints at smart-list counting; needs explicit routing proof or a deliberate non-helper decision. |
| "Find or update a specific record" | Planned | Need rules for when broad search is acceptable versus when a get/update/delete requires explicit IDs. |
| "Create or mutate from vague intent" | Planned | Need mutation safety wording and tests that tool schemas require typed payloads or explicit identifiers. |

## Routing Rules To Preserve

- If a narrow helper exists for a common "my" request, generic tools should name
  that helper in their descriptions.
- Generic search can remain flexible, but it should not be the preferred route
  for a high-confidence owned intent.
- The authenticated user's identity should be resolved by the adapter or service
  boundary, not by asking the client to infer a user ID.
- A future helper should be added only when it removes meaningful ambiguity or
  enforces a safer default.

## Open Questions

- Should "my upcoming tasks" become a separate helper, or should it remain a
  documented `followupboss_list_tasks` filter pattern?
- Should smart-list counting get a helper, or is the existing two-step
  `followupboss_list_smart_lists` plus `followupboss_search_people` guidance
  sufficient?
- Should destructive operations include stronger description text that forbids
  inferred IDs from prior ambiguous search results?

## Current Conclusion

- Routing is partially hardened for newest assigned lead and two task due
  buckets, including registered metadata tests and first-pass public docs. The
  broader intent map remains planned and should be implemented incrementally
  with tests before public docs claim full coverage.
