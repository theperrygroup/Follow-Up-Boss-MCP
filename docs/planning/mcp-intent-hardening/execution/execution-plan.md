# MCP Intent Hardening Execution Plan

This file is the checked-in ledger for the planning set. It records what has
landed, what is blocked, and what still remains open.

## 1. Ledger Scope

- This ledger records checked-in proof.
- Use `roadmap.md` for baseline dependency order.
- Use focused trackers for current readiness detail.

## 1A. How To Read This Ledger Now

- This file is the ledger, not proof that intent hardening is fully live.
- The strongest checked-in planning proof is the scaffold under
  `docs/planning/mcp-intent-hardening/`.
- The strongest checked-in runtime proof is the existing intent-helper surface
  in `src/followupboss_mcp/mcp_registration.py` and
  `src/followupboss_mcp/mcp_tools.py`.
- The biggest remaining gap is a complete intent taxonomy with matching tests,
  public docs, and live validation scenarios.

## 2. Current Checked-In Status

- Planning root created for MCP intent hardening.
- Foundation docs define the intent boundary and source-of-truth hierarchy.
- Registered tool descriptions now make the existing latest-lead and owned-task
  helpers more authoritative for common user-owned intents.
- Person and task update/delete descriptions now require explicit IDs rather
  than vague natural-language inference.
- Public MCP docs and the live validation checklist now include the first
  intent-routing and explicit-ID validation guidance.
- Trackers record that runtime hardening is still in progress, not complete.
- Execution docs define the active sequence and baseline roadmap.

## 3. Current Blockers

- The first public intent-to-tool guide exists, but the full MCP surface has not
  been classified by routing risk.
- Mutation safety language has only been hardened for person and task
  update/delete tools.
- Future helper candidates have not been ranked against actual ambiguous user
  requests.
- Live validation scenarios should wait until the offline contract is expanded.

## 4. Completed Planning Or Landed Proof

### 2026-05-08 - Planning Scaffold

- Checked-in proof:
  - `docs/planning/mcp-intent-hardening/README.md`
  - `docs/planning/mcp-intent-hardening/ARTIFACT_PATH_INDEX.md`
  - `docs/planning/mcp-intent-hardening/foundation/intent-boundary-adr.md`
  - `docs/planning/mcp-intent-hardening/execution/intent-hardening-plan.md`
- Result:
  - The initiative now has one canonical planning root, one active plan, and
    focused trackers for routing and safety validation.

### Existing Runtime Anchors Observed During Scaffold

- Checked-in proof:
  - `src/followupboss_mcp/mcp_registration.py`
  - `src/followupboss_mcp/mcp_tools.py`
  - `tests/mcp/test_mcp_tools_server_cli.py`
- Result:
  - Existing helper anchors for latest assigned lead and authenticated-user task
    due buckets can be treated as starting points for the hardening plan.

### 2026-05-08 - Phase 01 Description Hardening

- Checked-in proof:
  - `docs/planning/mcp-intent-hardening/execution/intent_PHASE_01_description_hardening.md`
  - `src/followupboss_mcp/mcp_registration.py`
  - `tests/mcp/test_mcp_tools_server_cli.py`
  - `docs/mcp-usage.md`
  - `docs/mcp-validation-checklist.md`
- Result:
  - Broad people and task tools now steer common owned intents to existing
    narrow helpers.
  - Existing helper descriptions now state that authenticated-user identity is
    resolved internally.
  - Person and task update/delete descriptions now require explicit IDs.

## 5. Current Work Queue

| Task | Status | Why it is still open |
| --- | --- | --- |
| Inventory and classify existing intent-like helpers | In progress | Initial anchors are documented, but the full MCP surface has not been classified. |
| Harden generic descriptions around narrow helpers | In progress | Highest-confidence people and task wording has landed; a full-surface pass remains open. |
| Add or reject future intent helpers | Planned | Helper candidates need ranking by ambiguity, safety, and duplication risk. |
| Expand offline validation | In progress | Registered metadata assertions landed for the first slice; future helper or safety wording work still needs coverage. |
| Update public docs and validation checklist | In progress | First intent-routing and explicit-ID guidance landed; future helper decisions still need doc sync. |
| Run live intent validation | Planned | Should happen only after offline contract and docs are ready. |

## 6. Current Conclusion

- MCP intent hardening has a planning home and a concrete active sequence. It is
  not done; the next implementation slice should start with inventory and
  description hardening, then move through tests, docs, and live validation.
