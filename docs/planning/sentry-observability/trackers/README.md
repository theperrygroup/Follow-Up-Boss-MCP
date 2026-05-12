# Sentry Observability Trackers

This folder records current readiness for adding Sentry to the project.

## Read Order

1. `readiness-overview.md`
2. `runtime-instrumentation-readiness.md`
3. `deployment-operations-readiness.md`
4. `../execution/execution-plan.md`

## Grade Rules

| Status | Meaning |
| --- | --- |
| `Planned` | The work exists only as a proposal or roadmap item. |
| `In progress` | Some planning or implementation exists, but acceptance criteria are still open. |
| `Checked in` | The named doc or code artifact exists in the repo now. |
| `Blocked` | The next step is known but cannot proceed honestly yet. |
| `Live` | Runtime behavior is deployed and validated with evidence. |

## Update Rules

- Update focused trackers before the aggregate readiness overview.
- Do not mark runtime instrumentation live until tests prove disabled,
  configured, and sanitized event paths.
- Do not mark deployment operations live until Sentry DSN, release metadata, and
  alert/runbook decisions are represented in checked-in docs or operator proof.
