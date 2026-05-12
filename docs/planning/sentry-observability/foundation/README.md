# Sentry Observability Foundation Docs

This folder holds durable rules for adding Sentry to the Follow Up Boss MCP
project.

## File Roles

| File | Use it for | Not for |
| --- | --- | --- |
| `sentry-boundary-adr.md` | Scope, privacy boundary, and instrumentation ownership | Current implementation status |
| `source-of-truth-matrix.md` | Authority across docs, code, tests, deployment, and Sentry configuration | A task checklist |

## Durable Rules

- Runtime truth comes from checked-in code and tests.
- Sentry project settings and alerts are external operator configuration until
  they are captured in docs or IaC.
- Follow Up Boss secrets, authorization headers, system keys, OAuth tokens, and
  customer payloads must be filtered before event submission.
- Errors should be grouped with useful runtime context such as transport,
  package version, release, environment, tenant identifier hash, and operation
  family when that context can be added without exposing sensitive data.

## Read Order

1. `sentry-boundary-adr.md`
2. `source-of-truth-matrix.md`
3. `../execution/sentry-rollout-plan.md`
4. `../trackers/readiness-overview.md`
