# Execution Docs

This folder holds the ordered plan and checked-in ledger for Sentry
observability.

Read this alongside:

- `../trackers/README.md`
- `../trackers/readiness-overview.md`
- `../foundation/sentry-boundary-adr.md`

## File Roles

| File type | Use it for | Not for |
| --- | --- | --- |
| `execution-plan.md` | Live checked-in ledger, blockers, completed proof | Historical baseline sequencing |
| `sentry-rollout-plan.md` | Canonical current Sentry implementation sequence | Replacing the ledger |
| `roadmap.md` | Baseline dependency order and historical context | Freshest status snapshot |
| `sentry_PHASE_##_<slug>.md` | Durable proof for one explicit slice | Replacing the aggregate ledger |

## Fastest Answers

| Question | Open first |
| --- | --- |
| What is the latest checked-in status? | `../trackers/readiness-overview.md`, then `execution-plan.md` |
| What is the current active sequence? | `sentry-rollout-plan.md` |
| What is the baseline task order? | `roadmap.md` |
| Where should future proof files go? | `../ARTIFACT_PATH_INDEX.md` |

## Rules

- Add or update a phase file when one slice needs durable proof beyond a brief
  ledger note.
- Treat `sentry-rollout-plan.md` as canonical for the current focused seam.
- Let focused trackers plus `readiness-overview.md` define current readiness.
- Edit `roadmap.md` only when the baseline sequence or task definitions change.
- Do not use `roadmap.md` as the current-status document.
