# ADR: MCP Battle-Test Verification Contract

## Status

Accepted for planning on `2026-05-18`.

## Context

The MCP intent-hardening plan needs more than direct tool checks. It needs to
exercise chatbot-like prompts that are intentionally vague, observe which MCP
tool path the client chooses, and then verify through the Follow Up Boss API
that the selected action produced or returned the correct outcome.

This differs from the reusable MCP validation checklist in two ways:

- The test input is natural-language user intent, not a preselected tool call.
- The pass condition is an oracle comparison against API truth, not merely a
  successful MCP response.

## Decision

Battle-test scenarios must be expressed as prompt-to-outcome contracts. Each
scenario should define:

- a stable scenario ID
- the vague user prompt variants to ask through the chatbot or MCP client
- the expected MCP tool or allowed tool sequence
- any explicitly forbidden tool path
- the fixture data needed to make the expected answer deterministic
- the direct API oracle used to verify the returned data or side effect
- the response-level assertion that proves the chatbot went in the right
  direction

## Required Scenario Grades

| Grade | Meaning | Example outcome |
| --- | --- | --- |
| `MUST_ROUTE` | The prompt should select one narrow MCP helper or known safe tool path. | "What am I late on?" routes to `followupboss_list_my_overdue_tasks`. |
| `MAY_ROUTE` | More than one safe read-only path is acceptable, but the outcome must match API truth. | A named smart-list count may list smart lists before searching people. |
| `MUST_CLARIFY` | The prompt is too ambiguous or unsafe to execute without more information. | "Delete the bad lead" asks for an explicit person ID. |
| `MUST_REQUIRE_ID` | A mutation can proceed only after an explicit resource ID or safe fixture reference is present. | Updating a task requires `task_id`. |
| `MUST_EXPLAIN_UNSUPPORTED` | The user intent has no valid MCP or Follow Up Boss API path. | Searching notes by Follow Up Boss person ID explains the API limitation. |

## Verification Rules

- API oracle checks should compare stable fields and side effects, not brittle
  whole-response JSON snapshots.
- Read-only prompts should be verified before mutation prompts.
- Mutation scenarios must use sandbox or disposable fixtures and must define
  cleanup before the scenario is runnable.
- Destructive prompts must not be considered passing solely because a tool call
  succeeded. The oracle must prove the intended fixture changed and unrelated
  fixtures did not.
- Unsupported-intent prompts pass only when the client explains the limitation
  and avoids inventing a false tool path.
- Live evidence belongs in a dated run artifact or validation report, not in the
  reusable checklist or planning docs.

## Consequences

- The battle-test harness may need transcript capture from the MCP client,
  direct API reads through the typed Follow Up Boss client, and fixture cleanup.
- The prompt corpus should be large and deliberately redundant because the risk
  lives in vague language and near-miss phrasing.
- The active intent-hardening plan stays canonical for sequencing, while
  `execution/intent-battle-test-plan.md` owns the focused prompt corpus and
  oracle design.
