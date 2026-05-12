# Deployment Operations Readiness

## Scope

This tracker owns hosted deployment, release metadata, Sentry project
configuration, alerts, and operator documentation.

## Current Status

Status: `In progress`

The repository has ECS/Fargate deployment templates, hosted deployment docs, and
GitHub Actions workflows. Sentry environment variables and release rendering are
now checked in, while real project configuration and alerting remain open.

## Required Operations Decisions

| Decision | Current answer | Status |
| --- | --- | --- |
| DSN source | Hosted deployments read `SENTRY_DSN` from environment configuration. | Checked in |
| Environment names | Runtime defaults to `local`; hosted docs use deployment stages such as staging and production. | In progress |
| Release value | Staging workflow renders `SENTRY_RELEASE` as `followupboss-mcp@${{ github.sha }}`. | Checked in |
| ECS configuration | Sentry variables are in `deploy/ecs/task-definition.template.json` and hosted docs. | Checked in |
| CI/CD metadata | `.github/workflows/deploy-staging.yml` injects Sentry release, environment, DSN, and optional trace sample rate. | Checked in |
| Alerts | Configure alerts for unhandled server errors, hosted auth failures, tenant resolution failures, and rate-limit backend failures. | Planned |
| Runbook | Hosted rollout checks include a sanitized Sentry exception smoke. | In progress |

## Acceptance Criteria

- [x] README and hosted deployment docs describe the Sentry environment variables.
- [x] ECS task template includes the agreed Sentry runtime variables.
- [x] GitHub Actions or deployment docs define how `SENTRY_RELEASE` is populated.
- [ ] Alerting expectations are documented with ownership and severity.
- [ ] A staged smoke path proves an intentional sanitized exception reaches the
  expected Sentry project and environment.
- [ ] Any manual Sentry project settings are recorded as operator configuration.

## Open Questions

- Will Sentry alerts be configured manually in the Sentry UI, via Sentry API, or
  via future infrastructure as code?
- Should staging and production use separate Sentry projects or one project with
  separate environment names?
- Which team or operator owns Sentry issue triage after deployment?

## Current Blockers

- DSN, organization/project slug, final environment naming, and alert
  destination are not known yet.
- Staged Sentry smoke validation has not run.
