# Execution Docs

This folder holds the ordered plan and the checked-in ledger for MCP intent
hardening.

Read this alongside:

- `../trackers/README.md`
- `../trackers/readiness-overview.md`
- `../foundation/intent-boundary-adr.md`

## File Roles

| File type | Use it for | Not for |
| --- | --- | --- |
| `execution-plan.md` | Live checked-in ledger, blockers, completed proof | Historical baseline sequencing |
| `intent-hardening-plan.md` | Canonical current hardening sequence | Replacing the ledger |
| `intent-battle-test-plan.md` | Focused vague-prompt battle-test corpus and API oracle sequence | Replacing the overall active plan or run evidence |
| `roadmap.md` | Baseline dependency order and historical context | Freshest status snapshot |
| `intent_PHASE_##_<slug>.md` | Durable proof for one explicit slice | Replacing the aggregate ledger |

## Fastest Answers

| Question | Open first |
| --- | --- |
| What is the latest checked-in status? | `../trackers/readiness-overview.md`, then `execution-plan.md` |
| What is the current active sequence? | `intent-hardening-plan.md` |
| How do we battle test vague chatbot prompts? | `intent-battle-test-plan.md`, then `../foundation/battle-test-verification-adr.md` |
| What is the baseline task order? | `roadmap.md` |
| Where should future proof files go? | `../ARTIFACT_PATH_INDEX.md` |

## Rules

- Add or update a phase file when one slice needs durable proof beyond a brief
  ledger note.
- Treat `intent-hardening-plan.md` as canonical for the current focused seam.
- Treat `intent-battle-test-plan.md` as the focused plan for prompt corpus and
  API-oracle details, not as evidence that a battle-test run has happened.
- Let focused trackers plus `readiness-overview.md` define current readiness.
- Edit `roadmap.md` only when the baseline sequence or task definitions change.
- Do not use `roadmap.md` as the current-status document.
