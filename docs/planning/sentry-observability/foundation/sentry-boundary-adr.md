# ADR: Sentry Observability Boundary

## Status

Accepted for planning.

## Context

The Follow Up Boss MCP project is a Python 3.12 package that exposes local
stdio, local streamable HTTP, and hosted multi-tenant streamable HTTP entrypoints.
It already centralizes runtime settings, stderr-safe logging, redaction helpers,
hosted tenant resolution, and ECS deployment templates.

The project does not currently include Sentry. Adding Sentry touches dependency
management, runtime bootstrap, privacy filtering, tests, deployment settings,
operator documentation, and alerting.

## Decision

Create one planning root for Sentry observability under
`docs/planning/sentry-observability/`.

The initiative owns:

- adding the `sentry-python` dependency and reading current SDK guidance before
  implementation
- defining Sentry settings such as DSN, environment, release, sampling, and
  enablement behavior
- initializing Sentry exactly once across local CLI and hosted entrypoints
- integrating error capture with FastMCP, Starlette-hosted paths, outbound HTTP
  breadcrumbs, and logging where appropriate
- filtering event payloads through project-owned redaction rules before events
  leave the process
- documenting ECS, GitHub Actions, release metadata, and operator alert setup
- validating the integration with automated tests and a staged smoke check

The initiative does not own:

- changing Follow Up Boss API behavior
- changing MCP tool contracts unless needed to add non-sensitive observability
  context
- replacing the existing Python logging strategy
- adding customer analytics or product telemetry
- storing raw tenant credentials, OAuth tokens, API keys, system keys, or
  customer payloads in Sentry

## Privacy Boundary

Sentry events may include:

- package version, release, environment, transport, and entrypoint
- exception class and stack trace
- sanitized route or operation family
- non-reversible tenant or subject identifiers only when hashed or otherwise
  explicitly non-sensitive

Sentry events must not include:

- `Authorization` headers
- Follow Up Boss API keys, OAuth access tokens, or `system_key` values
- tenant secret references when they reveal customer-specific secret paths
- raw person, task, note, message, email, phone, address, or webhook payload data
- request bodies or full upstream response bodies

## Consequences

- The first implementation slice should build reusable instrumentation helpers
  instead of sprinkling `sentry_sdk.init(...)` calls across entrypoints.
- The existing `redact_value(...)` and header redaction behavior should be reused
  or extended before Sentry events can be considered safe.
- Tests must cover both enablement and disabled behavior so local development
  remains predictable without a DSN.
- Deployment docs and templates must land before hosted Sentry can be considered
  rollout-ready.
