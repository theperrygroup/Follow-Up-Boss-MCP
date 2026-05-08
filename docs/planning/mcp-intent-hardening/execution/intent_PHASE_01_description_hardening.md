# Intent Phase 01: Description Hardening Proof

## Scope

This proof file records the first implementation slice for MCP intent
hardening. It covers registered tool metadata and public validation docs, not
new runtime helper behavior.

## Checked-In Proof

| Area | Proof |
| --- | --- |
| MCP registration | `src/followupboss_mcp/mcp_registration.py` now strengthens broad-search, broad-task-list, owned-helper, and explicit-ID mutation descriptions. |
| Registered-surface tests | `tests/mcp/test_mcp_tools_server_cli.py` asserts the helper-routing and explicit-ID description substrings exposed by `server.list_tools()`. |
| Public usage docs | `docs/mcp-usage.md` includes an intent-routing table for latest lead, owned task helpers, smart-list counts, and explicit-ID mutations. |
| Live validation checklist | `docs/mcp-validation-checklist.md` adds helper-intent checks and explicit-ID mutation validation expectations. |

## Behavior Covered

- `followupboss_search_people` still supports broad people search, but its
  description tells clients not to use it for latest-owned-lead intent.
- `followupboss_get_latest_lead` explicitly resolves the authenticated user
  internally.
- `followupboss_list_tasks` remains the generic task list, but points common
  owned-task intents at `followupboss_list_my_overdue_tasks` and
  `followupboss_list_my_tasks_due_today`.
- Person and task update/delete descriptions now require explicit IDs rather
  than vague natural-language inference.

## Remaining Gaps

- This slice does not add new helper tools.
- The full MCP surface has not yet been classified into risk categories.
- Mutation safety wording outside person and task tools still needs a broader
  audit.
- Live validation has not run for this slice yet.

## Conclusion

Phase 01 is a checked-in description and validation-doc hardening slice. It
makes existing intent helpers more authoritative for MCP clients, while leaving
future helper expansion and full-surface mutation audit open.
