# Intent Phase 02: Battle-Test Planning Proof

## Scope

This proof file records the docs-only planning slice for vague-prompt MCP battle
testing. It does not claim that the scenario harness, prompt corpus, API oracle,
or live validation run has been implemented.

## Checked-In Proof

| Area | Proof |
| --- | --- |
| Verification contract | `foundation/battle-test-verification-adr.md` defines prompt-to-tool-to-API oracle requirements and scenario grades. |
| Focused execution plan | `execution/intent-battle-test-plan.md` defines the vague prompt corpus, oracle strategy, and phase sequence. |
| Readiness tracker | `trackers/battle-test-readiness.md` tracks corpus, oracle, fixture, transcript, and live-run readiness. |
| Navigation and ledger | The landing README, artifact index, execution docs, trackers, and roadmap point future work to the new battle-test artifacts. |

## Behavior Covered

- Battle-test scenarios must start from natural-language chatbot prompts.
- Passing requires observed MCP tool selection plus direct API truth, not just a
  plausible chatbot answer.
- Prompt scenarios are graded as `MUST_ROUTE`, `MAY_ROUTE`, `MUST_CLARIFY`,
  `MUST_REQUIRE_ID`, or `MUST_EXPLAIN_UNSUPPORTED`.
- Read-only prompts should run before mutation and destructive prompts.
- Live evidence belongs in dated run artifacts or validation reports rather than
  reusable planning or checklist files.

## Remaining Gaps

- No machine-readable scenario corpus exists yet.
- No transcript-capture harness exists yet.
- No direct API oracle runner exists yet.
- No disposable fixture graph has been created for mutation scenarios.
- No live battle-test run has been executed.

## Conclusion

Phase 02 is a checked-in planning slice. It gives the battle-test workstream a
contract, corpus seed, tracker, and execution sequence, while keeping all
runtime and live-validation claims in `Planned` status until implementation and
evidence land.
