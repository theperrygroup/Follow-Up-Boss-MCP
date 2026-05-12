# Sentry Observability Readiness Tracker

## Purpose

This tracker records the current readiness state under a strict "planning is not
runtime" interpretation.

## Interpretation Rule

- `Complete` means the tracked planning or prerequisite slice is checked in.
- It does not mean Sentry is live in the project.
- Runtime truth still comes from the checked-in codebase.

## Current Snapshot

Snapshot date: `2026-05-10`

| Slice | Status | Current answer |
| --- | --- | --- |
| Planning scaffold | Checked in | This planning root defines scope, artifact homes, active rollout, trackers, and baseline roadmap. |
| Platform detection | Checked in | The repo is a Python 3.12 package, so the expected Sentry SDK is `sentry-python`. |
| SDK-specific guidance | Checked in | The Sentry Python SDK setup guidance and current Sentry Python options docs were read before implementation. |
| Runtime instrumentation | In progress | Dependency, settings, initializer, sanitizer, bootstrap wiring, and focused tests are checked in; staged Sentry smoke is still open. |
| Deployment operations | In progress | ECS, GitHub Actions, hosted docs, and release metadata are wired; real Sentry project and alert settings remain open. |
| Validation evidence | In progress | Focused automated tests pass; full project gates and staged Sentry validation remain open. |

## Broad Blockers Before Sentry Rollout

- Confirm the Sentry project DSN and target environment names.
- Decide whether Sentry alert configuration will be manual operator setup or
  represented in a checked-in artifact.
- Run full lint, type, test, coverage, and docs validation.
- Run staged Sentry smoke validation with a sanitized intentional exception.

## Focused Tracker Snapshot

| Focused tracker | Current state | Why it matters |
| --- | --- | --- |
| `runtime-instrumentation-readiness.md` | In progress | Owns dependency, settings, initialization, sanitizer, and unit coverage. |
| `deployment-operations-readiness.md` | In progress | Owns hosted configuration, release metadata, alerts, and runbooks. |

## Current Conclusion

Sentry observability has privacy-safe core instrumentation checked in, but it is
not live until full validation, project configuration, alert ownership, and a
staged smoke test land.
