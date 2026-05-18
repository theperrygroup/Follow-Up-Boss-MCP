# Intent Phase 03: Read-Only Battle-Test Schema Proof

## Scope

This proof file records the first implementation slice for vague-prompt MCP
battle testing. It covers scenario schema, the first read-only prompt corpus,
route grading, and typed API-oracle comparison helpers. It does not claim that a
chatbot client transcript capture runner or live battle-test run exists yet.

## Checked-In Proof

| Area | Proof |
| --- | --- |
| Scenario schema and corpus | `src/followupboss_mcp/battle_tests.py` defines scenario grades, expected MCP routes, oracle specs, transcript records, and the `BT-READ-001` through `BT-READ-005` corpus. |
| Read-only API oracle helpers | `src/followupboss_mcp/battle_tests.py` can evaluate captured transcripts for latest lead, overdue tasks, today's tasks, unsupported note search, and route-only pending scenarios. |
| Focused tests | `tests/unit/test_battle_tests.py` covers corpus stability, route grading, API-oracle comparison, unsupported-intent handling, pending oracle handling, and missing identity failure. |
| Validation proof | Focused Ruff, pytest, mypy, and coverage commands passed for the new battle-test module and tests. |

## Behavior Covered

- `BT-READ-001` requires `followupboss_get_latest_lead` and compares the MCP
  person ID to a direct assigned-user people query.
- `BT-READ-002` requires `followupboss_list_my_overdue_tasks` and compares task
  IDs to a direct incomplete overdue task query for the authenticated user.
- `BT-READ-003` requires `followupboss_list_my_tasks_due_today` and compares task
  IDs to a direct incomplete due-today task query for the authenticated user.
- `BT-READ-004` is encoded as route-only pending until the project chooses a
  canonical future-task API filter or helper.
- `BT-READ-005` passes only when the assistant explains unsupported note search
  without selecting a note or event-search fallback tool.

## Remaining Gaps

- No chatbot or MCP client transcript capture runner exists yet.
- No command-line battle-test runner exists yet.
- No live Follow Up Boss battle-test run has been executed.
- No mutation, destructive-safety, or boundary prompt batches have been encoded.
- `BT-READ-004` still needs a canonical automated API oracle decision.

## Validation Commands

```bash
uv run ruff format "src/followupboss_mcp/battle_tests.py" "tests/unit/test_battle_tests.py"
uv run ruff check "src/followupboss_mcp/battle_tests.py" "tests/unit/test_battle_tests.py"
uv run pytest "tests/unit/test_battle_tests.py"
uv run mypy --no-incremental --explicit-package-bases "src/followupboss_mcp/battle_tests.py" "tests/unit/test_battle_tests.py"
uv run coverage run --branch -m pytest "tests/unit/test_battle_tests.py"
uv run coverage report --include="src/followupboss_mcp/battle_tests.py" --fail-under=100
```

## Conclusion

Phase 03 lands the first reusable battle-test code. The next slice should wire a
client transcript capture path or runner that can feed real selected MCP tools
and arguments into the checked-in schema and oracle helpers.
