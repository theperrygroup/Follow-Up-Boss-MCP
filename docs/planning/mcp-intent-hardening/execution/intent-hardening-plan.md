# MCP Intent Hardening Active Plan

This is the canonical active plan for the current MCP intent-hardening sequence.
It supersedes the roadmap when a focused implementation order is needed.

## 1. Objective

Harden the Follow Up Boss MCP surface so common high-level user requests route
to narrow, identity-aware, and validation-backed tools instead of broad generic
operations.

## 2. Current Runtime Starting Point

The current working tree already contains these useful anchors:

- latest assigned lead helper: `followupboss_get_latest_lead`
- authenticated-user overdue task helper:
  `followupboss_list_my_overdue_tasks`
- authenticated-user due-today task helper:
  `followupboss_list_my_tasks_due_today`
- adapter-level default scoping for people search when no explicit owner or pond
  inclusion is provided
- adapter-level identity resolution for task due-bucket helpers

These anchors are starting points, not proof that the entire MCP surface is
intent-hardened.

## 3. Target Contract

| Contract area | Required behavior |
| --- | --- |
| Owned read intents | Common "my" requests prefer helpers that resolve the authenticated Follow Up Boss user internally. |
| Generic reads | Broad search/list tools remain available but point users toward narrower helpers when appropriate. |
| Mutations | Side-effecting tools require explicit IDs or typed payloads and do not claim to infer destructive intent. |
| Identity failures | Helpers that need authenticated-user identity fail closed before broad upstream requests. |
| Validation | Offline tests prove request shape and registration; live checks follow only after that proof lands. |
| Docs | `docs/mcp-usage.md` and `docs/mcp-validation-checklist.md` describe the current checked-in helper contract. |

## 4. Phase Plan

### Phase A - Inventory Existing Intent Surface

Deliverables:

- classify all registered tools by intent risk and routing role
- update `trackers/intent-routing-readiness.md` with accepted helper families,
  deferred helper families, and rejection reasons
- identify generic descriptions that should refer to existing narrow helpers

Acceptance criteria:

- every registered tool family has an owner category
- current helper anchors are confirmed against code and tests
- no new helper is proposed without a stated ambiguity or safety reason

### Phase B - Harden Descriptions And Existing Helpers

Deliverables:

- update broad search/list descriptions to prefer existing helpers for common
  user-owned intents
- audit mutation descriptions for explicit-ID and typed-payload language
- add or tighten tests around registered names, helper descriptions, and adapter
  request construction where appropriate

Acceptance criteria:

- `followupboss_search_people` guidance remains compatible with broad search but
  clearly points "latest lead" intent at the helper
- task listing guidance clearly points overdue and due-today user intents at
  the helper tools
- mutation wording does not imply vague natural-language inference is enough for
  side effects

### Phase C - Decide Future Helpers

Deliverables:

- rank candidate helpers such as upcoming tasks, open lead follow-up, smart-list
  counts, or record lookup shortcuts
- reject candidates that duplicate simple typed filters without adding safety
- implement only accepted helpers with typed models, Google-style docstrings,
  thorough type hints, registration, and tests

Acceptance criteria:

- each candidate has an accepted, deferred, or rejected outcome
- accepted helpers have offline tests before docs claim availability
- rejected helpers have documented fallback guidance

### Phase D - Sync Docs And Validation

Deliverables:

- add an intent-to-tool section to `docs/mcp-usage.md`
- add intent-read and mutation-safety scenarios to
  `docs/mcp-validation-checklist.md`
- update planning trackers and execution ledger with checked-in proof

Acceptance criteria:

- public docs name only helpers that exist in `mcp_registration.py`
- validation checklist distinguishes reusable checklist items from run-specific
  evidence
- planning status uses `planned`, `in progress`, `checked in`, and `live`
  accurately

### Phase E - Run Proof

Deliverables:

- run focused pytest coverage for MCP registration and adapter behavior
- run lints or project validation appropriate to touched files
- run live MCP validation only after offline proof and docs are ready

Acceptance criteria:

- automated checks pass or blockers are recorded in `execution-plan.md`
- live validation results are recorded outside the reusable checklist if they
  are release evidence
- no planning doc claims a helper is live without matching code and proof

## 5. Implementation Guardrails

- Keep behavior in typed adapter or service methods, not ad hoc registration
  handlers.
- Prefer existing request models unless a new model makes a safer contract
  explicit.
- Add Google-style docstrings and thorough type hints for new Python functions
  or models.
- Preserve pagination and field selection for helper reads when supported.
- Fail closed before broad upstream requests when authenticated identity is
  required.

## 6. Next Slice

The next slice should be Phase A plus the smallest part of Phase B:

1. Inventory all registered tools into routing categories.
2. Identify descriptions that need explicit helper redirection.
3. Update only the highest-confidence description wording first.
4. Add focused tests for the changed registered surface.
5. Refresh `trackers/readiness-overview.md` and `execution-plan.md` with the
   checked-in proof.
