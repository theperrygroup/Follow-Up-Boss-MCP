# Multi-Tenant Hosting Checklist

## Goal

Refactor the hosted Follow Up Boss MCP server so outside customers can connect to one shared
`streamable-http` deployment while using their own Follow Up Boss account credentials instead
of a single process-wide credential.

## Current State Snapshot

- `src/followupboss_mcp/config.py` now separates server bootstrap settings from tenant runtime
settings while preserving a backward-compatible local single-tenant wrapper.
- `src/followupboss_mcp/mcp_server.py` chooses between a local static client bundle and a hosted
request-scoped tenant runtime path.
- `src/followupboss_mcp/mcp_registration.py` resolves tools, resources, and prompts against the
active hosted tenant context instead of one startup-time adapter.
- Hosted inbound authentication, tenant resolution, audit logging, and hosted endpoint rate
limiting are implemented for `streamable-http`.
- `stdio` remains a local single-tenant developer path; hosted multi-tenant deployments use
`streamable-http`.

## Success Criteria

- [x] Hosted `streamable-http` requests require inbound authentication.
- [x] Each authenticated caller resolves to exactly one tenant.
- [x] Tenant credentials are loaded from a database or secret store, not global environment
variables.
- [x] `FollowUpBossAsyncClient` instances are created per request or per session instead of once
at process startup.
- [x] MCP tools, resources, and prompts use the authenticated tenant context safely.
- [x] Invalid, expired, or unauthorized tokens fail closed with safe error messages.
- [x] Cross-tenant access is prevented and covered by tests.
- [x] Local development remains possible and documented.

## Core Objectives

- [x] Split server config from tenant auth config.
- [x] Stop creating one shared `FollowUpBossAsyncClient` in `create_server()`.
- [x] Make client and service creation request-scoped or session-scoped based on the
authenticated customer.
- [x] Add inbound auth for the hosted MCP endpoint so the server can identify the tenant.

## Key Touchpoints

- `src/followupboss_mcp/config.py`
- `src/followupboss_mcp/auth.py`
- `src/followupboss_mcp/http_client.py`
- `src/followupboss_mcp/mcp_server.py`
- `src/followupboss_mcp/mcp_registration.py`
- `src/followupboss_mcp/mcp_tools.py`
- `tests/mcp/test_mcp_tools_server_cli.py`
- `tests/unit/test_auth_config_logging.py`
- `docs/architecture.md`
- `docs/customer-onboarding-flow.md`
- `docs/hosted-deployment-guide.md`
- `docs/mcp-usage.md`
- `docs/security.md`

## Phase 0: Decisions And Guardrails

- [x] Confirm the hosted multi-tenant product is only supported over `streamable-http`.
- [x] Decide that `stdio` remains an explicit local-dev-only single-tenant developer path for
now.
- [x] Decide whether inbound auth uses signed JWTs, opaque API tokens, or both.
Decision: the hosted contract stays verifier-backed and can use signed JWTs, opaque token
lookups, or another backend as long as it yields the canonical `HostedVerifiedIdentity`.
- [x] Decide whether tenant credentials support stored API keys, stored OAuth access tokens, or
both.
Decision: hosted tenant credentials support both API key and OAuth modes through
`TenantCredentialRecord`.
- [x] Decide whether tenant runtime objects should be request-scoped or session-scoped for the
hosted HTTP transport.
Decision: the first hosted release stays request-scoped; session-scoped reuse is deferred
until there is performance data that justifies the extra lifecycle complexity.
- [x] Decide where tenant secrets live in production.
Decision: the reference deployment keeps tenant metadata and hosted bearer-token metadata in
Postgres while storing Follow Up Boss secret payloads in AWS Secrets Manager referenced by
`secret_ref`.
- [x] Decide what local development fallback is acceptable for secret storage.
Decision: local `stdio` and local single-tenant `streamable-http` stay environment-backed,
while hosted-style local testing may use `DevelopmentTenantStore` and
`DevelopmentHostedTokenVerifier`; no shared hosted environment should use the development
store or verifier.
- [x] Define minimum audit logging requirements for tenant authentication and upstream Follow Up
Boss usage.
Decision: operators retain `hosted_auth_*`, `tenant_resolution_*`,
`upstream_credential_usage`, and `hosted_rate_limit_*` events with `tenant_id`, `client_id`,
optional `token_id`, and failure reasons.
- [x] Define token revocation, expiration, and credential-rotation requirements.

## Phase 1: Split Server Config From Tenant Credentials

- [x] Introduce a server-only settings model for host, port, log level, transport, and other
non-tenant runtime options.
- [x] Remove customer-specific Follow Up Boss credentials from the startup settings path used by
hosted mode.
- [x] Preserve only server-level environment variables in the hosted server bootstrap flow.
- [x] Decide that `base_url`, `timeout_seconds`, and `max_retries` remain global defaults on the
tenant runtime model while still allowing future per-tenant overrides.
- [x] Keep backwards-compatible local development behavior explicit if a single-tenant path is
still needed for local inspection.
- [x] Update configuration tests to reflect the split between server settings and tenant auth
material.

## Phase 2: Tenant Store And Secret Handling

- [x] Define the tenant model fields needed to resolve a customer safely.
- [x] Define a credential record shape that supports both API key and OAuth token modes.
- [x] Define a storage abstraction for tenant lookup and secret retrieval.
- [x] Choose the production implementation.
Decision: the reference production pattern is a database row plus external secret-manager
reference.
Alternatives not selected for the reference deployment:
- Database row with encrypted credential payload.
- Another production-safe secret storage pattern.
- [x] Implement a development-safe store for local testing.
- [x] Ensure tenant credentials are encrypted at rest or retrieved from a managed secret store.
- [x] Define how secret rotation updates the stored tenant credential without downtime.
- [x] Define how disabled tenants, revoked credentials, and missing credentials are surfaced.
- [x] Add tests for tenant lookup, credential lookup, disabled tenants, and missing-secret cases.

## Phase 3: Inbound Auth And Tenant Resolution

- [x] Choose the canonical inbound auth header and token shape for hosted clients.
- [x] Add token verification using the supported FastMCP auth hooks for hosted HTTP.
- [x] Define the verified identity payload needed to resolve the tenant.
- [x] Add a tenant-resolution layer that maps the inbound identity to one active tenant.
- [x] Reject unauthenticated requests before any Follow Up Boss client is created.
- [x] Reject authenticated requests whose tenant is disabled, missing, or not authorized.
- [x] Ensure auth failures do not leak whether another tenant exists.
- [x] Add focused auth tests for missing, invalid, expired, disabled-tenant,
revoked-credential, and wrong-tenant token cases.
- [x] Add integration tests that prove hosted HTTP requests fail closed without a valid token.

## Phase 4: Request-Scoped Or Session-Scoped Runtime Wiring

- [x] Add a tenant runtime model that contains the resolved tenant identity plus credential
material needed to build the Follow Up Boss client.
- [x] Add a factory that converts tenant credential records into the auth strategy required by
`FollowUpBossAsyncClient`.
- [x] Refactor `create_server()` so it no longer creates one shared `FollowUpBossAsyncClient` for
all callers.
- [x] Refactor service construction so it is driven by a tenant-specific client.
- [x] Refactor tool adapter creation so it is driven by a tenant-specific service bundle.
- [x] Add cleanup logic so request-scoped or session-scoped clients are always closed.
- [x] Decide whether shared transport concerns such as retry and timeout settings are inherited
from server defaults or overridden per tenant.
- [x] Add tests that prove two different authenticated callers do not share the same Follow Up
Boss client instance or credential set.

## Phase 5: MCP Context Plumbing

- [x] Update the server wiring so MCP handlers can access the authenticated tenant context.
- [x] Decide whether tools, resources, and prompts all require tenant auth or whether any remain
intentionally public.
- [x] Refactor the registration helpers as needed so tenant-aware operations can resolve the
correct runtime adapter from context instead of using a single startup-time adapter.
- [x] Keep the public MCP tool names stable unless a breaking change is explicitly required.
- [x] Ensure resource and prompt handlers do not accidentally bypass tenant resolution.
- [x] Confirm error handling remains JSON-safe and MCP-friendly after the tenant-aware refactor.

## Phase 6: Security Hardening

- [x] Ensure secret-like fields remain redacted in logs and object representations.
- [x] Ensure inbound auth tokens are never logged in plaintext.
- [x] Add per-tenant audit events for authentication, tenant resolution, and upstream credential
usage where appropriate.
- [x] Add per-tenant rate limiting or abuse controls for the hosted endpoint.
- [x] Document token revocation and emergency credential rotation procedures.
- [x] Confirm the hosted design fails closed when the tenant store or secret store is unavailable.
- [x] Re-review webhook and attachment flows for tenant-isolation assumptions.

## Phase 7: Test Coverage

- [x] Add unit tests for the new server-only settings model.
- [x] Add unit tests for the tenant store abstraction and its error cases.
- [x] Add unit tests for inbound token verification and tenant resolution.
- [x] Add unit tests for client-factory construction from tenant credentials.
- [x] Add MCP HTTP tests that prove different bearer tokens route to different tenant runtimes.
- [x] Add MCP HTTP tests that prove invalid or missing auth is rejected.
- [x] Add MCP tests that confirm tools, resources, and prompts still work after the refactor.
- [x] Add regression coverage for `stdio` so its supported behavior is explicit and documented.
- [x] Re-run focused MCP, auth, and HTTP client suites during the refactor.
- [x] Re-run the full quality gate before closing the workstream.
Status: re-ran `make release-validate` on 2026-03-30 after closing the remaining coverage gaps
in `src/followupboss_mcp/config.py`, `src/followupboss_mcp/hosted_auth.py`,
`src/followupboss_mcp/hosted_rate_limits.py`, `src/followupboss_mcp/logging.py`,
`src/followupboss_mcp/mcp_registration.py`, `src/followupboss_mcp/mcp_server.py`, and
`src/followupboss_mcp/mcp_tools.py`. `sync`, `audit`, `docs-check`, `format-check`, `lint`,
`mypy src tests`, `uv run pytest`, `uv run coverage run --branch -m pytest`,
`uv run coverage report --fail-under=100`, `uv run python -m followupboss_mcp.cli --help`, and
build smoke all pass; coverage now reports `TOTAL 5177 0 582 0 100.00%`.
The repository now includes the reference hosted staging backends and dedicated hosted entrypoint
needed to attempt Phase 9, but the remaining open checklist items still require real staging and
external validation.

## Phase 8: Documentation And Operations

- [x] Update `docs/architecture.md` for the new hosted multi-tenant runtime model.
- [x] Update `docs/mcp-usage.md` to explain hosted authentication requirements.
- [x] Update `docs/security.md` with tenant secret handling, inbound auth, and rotation guidance.
- [x] Add a hosted deployment guide that explains required infrastructure and secrets.
- [x] Document the expected customer onboarding flow for saving their Follow Up Boss credential.
- [x] Document how to disable a tenant, revoke a token, and rotate a compromised credential.
- [x] Decide whether `README.md` should describe the hosted multi-tenant path directly or point to
a dedicated deployment document.
Decision: `README.md` points to dedicated hosted deployment and onboarding docs instead of
duplicating operator guidance inline.

## Phase 9: Rollout Checklist

Status: reference hosted Postgres, AWS Secrets Manager, and Redis integrations now live in
`src/followupboss_mcp/hosted_reference.py`, and the repository exposes
`followupboss-mcp-hosted` as the dedicated hosted entrypoint. The checklist items below remain
open until a real shared staging environment and external tenants validate them end to end.

No further in-repo implementation is required before attempting these rollout steps unless staging
finds a real gap. The remaining work is infrastructure setup, staged validation, operational
evidence capture, and external pilot execution.

### Run Metadata

| Field | Value |
| --- | --- |
| Planned staging date | 2026-03-30 |
| Primary operator | OpenAI GPT-5.4 agent |
| Reviewer | `jp26jp` |
| Deployment revision, image tag, or commit | `bbeefc7`, ECR tag `staging` |
| Shared `PRODUCTION_MCP_URL` | `https://fub.theperry.group/mcp` |
| Staging dashboard or log link | CloudWatch Logs group `/ecs/followupboss-mcp-staging` |
| Incident or escalation channel | Direct operator escalation to `jp26jp` |
| Notes | Shared staging runtime is live on ECS/Fargate. During the 2026-03-30 pilot window, `tenant-b` was rotated in place from the earlier Perry Group placeholder credential to the real external `j-26` Follow Up Boss account while keeping `credential_id` stable. Shared-URL smoke then passed for both tenants with `own_fixture_count=1`, `other_fixture_count=0`, `resource_count=1`, and `prompt_message_count=1`, and CloudWatch recorded hosted auth, tenant resolution, and upstream credential usage without hosted rate-limit backend failures. |

### Required Inputs Before First Staging Run

- [x] One named primary operator and one reviewer have access to the staging deploy, PostgreSQL,
  AWS Secrets Manager, Redis, and log dashboards.
- [x] `docs/hosted-deployment-guide.md`, `docs/customer-onboarding-flow.md`, and
  `docs/security-incident-playbook.md` are treated as the source-of-truth runbooks for deployment,
  onboarding, and rollback.
- [x] One shared `PRODUCTION_MCP_URL` is chosen for the entire hosted validation run.
- [x] `tenant-a` and `tenant-b` are different real Follow Up Boss accounts with one unique fixture
  email or person each.
- [x] The operator can disable a tenant, revoke a hosted bearer token, rotate a Follow Up Boss
  credential, and issue a replacement hosted token without waiting on application code changes.
- [x] Log and dashboard access is ready for `hosted_auth_*`, `tenant_resolution_*`,
  `upstream_credential_usage`, and hosted rate-limit events.
- [x] If any staged or pilot workflow depends on Follow Up Boss registered-system headers, the
  deployment has valid `X-System` and `X-System-Key` values issued through the official
  system-registration flow documented at
  [Registration and Identification](https://docs.followupboss.com/reference/identification).

### Shared Staging Environment Contract

Export these values before running the staged validation commands:

```bash
export PRODUCTION_MCP_URL="https://fub.theperry.group/mcp"
export TENANT_A_TOKEN="replace-with-real-hosted-token"
export TENANT_B_TOKEN="replace-with-real-hosted-token"
export TENANT_A_FIXTURE_EMAIL="mcp-tenant-a@example.com"
export TENANT_B_FIXTURE_EMAIL="mcp-tenant-b@example.com"
```

`tenant-a` and `tenant-b` must both use the same `PRODUCTION_MCP_URL`. Execute the `Invalid Token
Fails Closed`, `Shared Deployment Smoke For Each Tenant`, `Credential Rotation Smoke`, and
`Hosted Token Rotation Smoke` command blocks in `docs/hosted-deployment-guide.md`, then attach the
exact outputs or operator notes to the rollout evidence captured below.

- [x] Stand up a staging tenant store and secret store.
  Required work:
  - Provision staging PostgreSQL for `tenants`, `tenant_credentials`, and
    `hosted_access_tokens`.
  - Provision a staging AWS Secrets Manager prefix for tenant secrets and scope app IAM access to
    that prefix only.
  - If any tenant needs registered-system-dependent endpoints, store the shared integration's
    `system_name` and `system_key` through the tenant credential path instead of shared bootstrap
    environment variables.
  - Provision shared staging Redis for hosted rate limiting.
  - Deploy `followupboss-mcp-hosted` behind HTTPS with the hosted environment variables documented
    in `docs/hosted-deployment-guide.md`.
  - Confirm the deployed service is using the shared staging Postgres, AWS Secrets Manager, and
    Redis backends instead of any development-only in-memory or JSON-backed helpers.
- [x] Validate at least two test tenants against the same hosted server instance.
  Required work:
  - Create `tenant-a` and `tenant-b` rows plus active credential rows in staging.
  - Store one real Follow Up Boss credential payload for each tenant in AWS Secrets Manager.
  - Mint one hosted bearer token for each tenant bound to the active `credential_id`.
  - Create one unique fixture person or email in each tenant account.
  - Run the shared-endpoint smoke commands in `docs/hosted-deployment-guide.md` against one
    shared `PRODUCTION_MCP_URL`.
  - Confirm each tenant output shows a successful identity response, at least one own-tenant
    fixture result, zero cross-tenant fixture results, at least one resource read, and at least
    one prompt message.
- [x] Confirm tenant A cannot access tenant B data even with replayed or swapped identifiers.
  Required work:
  - Re-run the staged smoke using tenant A's token against tenant B's fixture and confirm zero
    results.
  - Re-run the staged smoke using tenant B's token against tenant A's fixture and confirm zero
    results.
  - Attempt one swapped or replayed identifier scenario, such as an old token bound to the wrong
    `credential_id`, and confirm the hosted auth layer fails closed.
  - Capture the exact command outputs or operator notes as rollout evidence.
- [x] Confirm the hosted endpoint behaves correctly after token expiration and credential
rotation.
  Required work:
  - Rotate one tenant's Follow Up Boss secret in place while keeping `credential_id` stable, then
    rerun the tenant smoke check.
  - Mint a replacement hosted bearer token for one tenant, validate it, revoke the previous token,
    and confirm the old token now fails closed.
  - Validate one expiration path, either with a short-lived test token or by forcing an expired
    token row in staging.
  - Confirm the unaffected tenant still works throughout the other tenant's rotation exercise.
- [x] Confirm operational dashboards or logs can distinguish tenant auth failures from upstream
Follow Up Boss failures.
  Required work:
  - Verify log aggregation and dashboards expose `hosted_auth_failed`,
    `tenant_resolution_failed`, `upstream_credential_usage`, and hosted rate-limit events.
  - Trigger at least one safe auth failure and confirm it is distinguishable from an upstream
    Follow Up Boss failure.
  - Trigger at least one safe upstream failure and confirm it is not mislabeled as hosted auth.
  - Record the dashboard query, log filter, or alert path operators will use during incidents.
- [x] Pilot the hosted flow with one external customer before wider rollout.
  Required work:
  - Choose one external pilot customer with a reversible onboarding plan and known operator owner.
  - Onboard the tenant through the staged onboarding flow, validate identity plus one low-risk list
    or search call, and monitor initial usage.
  - Confirm token rotation, tenant disable, and rollback instructions are ready before pilot start.
  - Record pilot outcomes, open issues, and explicit go or no-go criteria for wider rollout.

Recommended execution order:
1. Provision staging infrastructure and deploy `followupboss-mcp-hosted`.
2. Seed `tenant-a` and `tenant-b` plus hosted tokens and fixture records.
3. Run the staged validation commands in `docs/hosted-deployment-guide.md`.
4. Capture auth, isolation, rotation, and observability evidence.
5. Only after the staged checklist is clean, run the external pilot.

### Required Rollout Evidence

| Check | Status | Evidence |
| --- | --- | --- |
| Invalid token fails closed before any tool call | PASS | During the 2026-03-30 pilot window, a fresh invalid bearer token against `https://fub.theperry.group/mcp` failed closed before `followupboss_get_identity` could execute, and CloudWatch recorded `hosted_auth_failed`. |
| Tenant A shared-endpoint smoke | PASS | `tenant-a` resolved through the shared staging URL to Perry Group `accountId=1108468760` with `own_fixture_count=1`, `other_fixture_count=0`, `resource_count=1`, and `prompt_message_count=1`. |
| Tenant B shared-endpoint smoke | PASS | After rotating the staging `tenant-b` secret in place and updating `system_name` to `J-26`, the shared staging URL resolved `tenant-b` to `j-26` `accountId=1746230763` with `own_fixture_count=1`, `other_fixture_count=0`, `resource_count=1`, and `prompt_message_count=1`. |
| Cross-tenant fixture isolation | PASS | Unique fixture emails `mcp-tenant-a-pilot-1774898106@example.com` and `mcp-tenant-b-pilot-1774898106@example.com` each resolved only under the matching tenant token. Both cross-tenant searches returned zero results, and a temporary `tenant-b` token intentionally bound to `cred-staging-tenant-a-primary` failed closed. |
| Resource and prompt auth boundary | PASS | Both tenant smoke runs successfully read `followupboss://api-coverage-matrix` and rendered `followupboss_compose_lead_event` only after hosted auth succeeded. |
| No-downtime Follow Up Boss credential rotation | PASS | The same `tenant-b` hosted token first resolved to Perry Group `accountId=1108468760`, then after an in-place AWS Secrets Manager secret update plus `tenant_credentials.system_name='J-26'` under unchanged `credential_id=cred-staging-tenant-b-primary`, the next request resolved to `j-26` `accountId=1746230763`. `tenant-a` remained healthy throughout the same window. |
| Hosted bearer-token rotation and revoke | PASS | A replacement tenant-a token was minted, validated successfully, then the original token was revoked and now returns `401`. |
| Expired-token failure path | PASS | A staged tenant-a token row with `expires_at` in the past now returns `401` at the hosted endpoint. |
| Auth failures distinguished from upstream failures | PASS | CloudWatch Logs group `/ecs/followupboss-mcp-staging` recorded `hosted_auth_failed=1`, `hosted_auth_succeeded=36`, `tenant_resolution_succeeded=36`, and `upstream_credential_usage=8` during the pilot window, with no sign that safe upstream activity was mislabeled as hosted auth. |
| Hosted rate-limit backend healthy | PASS | CloudWatch Logs group `/ecs/followupboss-mcp-staging` recorded `hosted_rate_limit_backend_failed=0` during the 2026-03-30 pilot window. |
| External pilot result | PASS | External pilot customer `j-26` was onboarded through the staged flow under operator owner `jp26jp`. Identity plus a low-risk hosted people search passed over the shared staging URL, the temporary validation fixtures were cleaned up afterward, and the wider-rollout recommendation is `GO` while the no-go conditions remain clean. |

### No-Go Conditions And Rollback Triggers

Do not widen rollout if any of the following are true:

- an invalid, expired, revoked, or tenant-mismatched hosted token can still reach a tool, resource,
  or prompt successfully
- tenant A can retrieve tenant B fixture data, or tenant B can retrieve tenant A fixture data
- credential rotation or bearer-token revocation is not visible on the next request
- dashboards or logs cannot separate `hosted_auth_failed`, `tenant_resolution_failed`,
  `upstream_credential_usage`, upstream Follow Up Boss failures, and hosted rate-limit backend
  failures
- pilot rollback steps are not ready for immediate use

If any no-go condition is hit, pause rollout and follow `docs/security-incident-playbook.md`
before rerunning staging.

### Final Sign-Off

| Role | Name | Status | Notes |
| --- | --- | --- | --- |
| Primary operator | OpenAI GPT-5.4 agent | COMPLETE | Rotated `tenant-b` to the real `j-26` credential, reran shared staging smoke, and captured CloudWatch evidence on 2026-03-30. |
| Reviewer | `jp26jp` | PENDING HUMAN SIGN-OFF | Access confirmed for the staging deploy, PostgreSQL, AWS Secrets Manager, and CloudWatch during the pilot window; final wider-rollout approval remains human-owned. |
| Pilot owner | `jp26jp` | GO | External pilot customer `j-26` passed identity plus low-risk search on the shared staging MCP URL; widen rollout only while the existing no-go conditions remain clean. |

## Open Questions

- [x] Should local `stdio` continue to read tenant credentials from environment variables, or
should it also move behind the tenant store abstraction?
Decision: keep `stdio` environment-backed for the local developer path and use the tenant
store abstraction only for hosted-style local and test flows.
- [x] Do we want session-scoped client reuse for streamable HTTP, or is request-scoped
construction simpler and safer for the first release?
Decision: request-scoped construction is the current hosted default; revisit session reuse
only if later measurements show a real need.
- [x] Is the first hosted release API-key-only, OAuth-only, or dual-mode?
Decision: the hosted data model and runtime stay dual-mode, while operator onboarding
defaults to the simpler API-key path unless a tenant specifically requires OAuth.
- [x] Which secret-store and database backend should be treated as the production reference
implementation?
Decision: Postgres backs tenant and opaque-token metadata, AWS Secrets Manager holds Follow
Up Boss secrets, and Redis backs shared hosted endpoint rate limits.
- [x] Do resources and prompts require the same inbound auth guarantees as tools, or can any stay
unauthenticated?
Decision: hosted mode keeps no intentionally public resources or prompts; all registered MCP
surfaces follow the same tenant-auth boundary.

## Evidence Log

- [x] Record the FastMCP auth hook choice and the rationale.
- [x] Record the tenant store interface and production implementation choice.
- [x] Record the inbound auth token format and revocation model.
- [x] Record the client lifecycle choice: request-scoped or session-scoped.
- [x] Record the staged validation commands and evidence capture template.
- [ ] Record the final staged validation results from the shared staging deployment.

## Done Definition

- [x] Server config and tenant credential handling are separated cleanly.
- [x] Hosted HTTP requests require inbound auth and resolve to a single tenant.
- [x] Tenant credentials are no longer loaded from process-wide environment variables in hosted
mode.
- [x] No shared Follow Up Boss client is created at server startup for hosted mode.
- [x] Tenant-specific clients, services, and adapters are created safely from authenticated
context.
- [x] Tests cover multi-tenant routing, auth failure paths, and tenant isolation.
- [x] Documentation explains how the hosted multi-tenant deployment works.

## Evidence Notes

- Added `FollowUpBossServerSettings` and `FollowUpBossTenantSettings`, while keeping
`FollowUpBossSettings` as a backward-compatible local single-tenant wrapper.
- Updated `create_server()`, the CLI, examples, and focused docs/tests so server bootstrap
settings and tenant auth/runtime settings are no longer modeled as one undifferentiated
object.
- Added `TenantRecord`, `TenantCredentialRecord`, `TenantStore`, and
`DevelopmentTenantStore`, plus focused tenant-store tests for active, disabled, revoked,
and missing-credential resolution paths while keeping a local-dev bridge via
`DevelopmentTenantStore.from_local_dev_settings(...)`.
- Added `HostedVerifiedIdentity`, `HostedAuthSettings`, a tenant-resolving FastMCP token
verifier, and `DevelopmentHostedTokenVerifier`, while deferring default client creation
behind hosted auth so invalid, expired, disabled-tenant, revoked-credential, missing-tenant,
and wrong-tenant bearer tokens fail closed before any upstream Follow Up Boss client is
instantiated.
- Added `TenantRuntime`, `TenantRuntimeFactory`, and request-scoped service-bundle resolution
so hosted tool calls materialize tenant-specific `FollowUpBossTenantSettings`, inherit
`base_url`/`timeout_seconds`/`max_retries` from shared defaults, close clients after each
call, and prove with focused MCP/auth tests that different bearer tokens do not share client
instances or credential material.
- Routed hosted resources and prompts through the same `TenantRuntimeFactory` auth-context path
as tools, decided that hosted mode exposes no intentionally public MCP surfaces, and proved
with `uv run pytest tests/unit/test_tenant_runtime.py tests/mcp/test_hosted_auth_streamable_http.py tests/integration/test_hosted_auth_integration.py tests/mcp/test_mcp_tools_server_cli.py tests/integration/test_runtime_integration.py`
that tools, resources, and prompts preserve tenant isolation while local server-surface
behavior remains intact.
- Hardened hosted resource/prompt runtime-resolution failures so MCP responses stay JSON-safe
and token-safe, expanded logging/object redaction to include bearer-token-style fields and
`HostedAccessToken` representations, wrapped tenant/secret store backend outages into
fail-closed tenant-store errors, and revalidated with
`uv run pytest tests/unit/test_auth_config_logging.py tests/unit/test_hosted_auth.py tests/unit/test_tenant_store.py tests/unit/test_tenant_runtime.py tests/integration/test_hosted_auth_integration.py tests/mcp/test_hosted_auth_streamable_http.py tests/unit/test_http_client.py`.
- Added machine-readable audit-log helpers plus per-tenant hosted audit events for bearer-token
authentication success/failure, tenant-resolution success/failure, and request-scoped
upstream credential usage without logging raw bearer tokens, API keys, access tokens, or
system keys, and revalidated with
`uv run pytest tests/unit/test_auth_config_logging.py tests/unit/test_hosted_auth.py tests/unit/test_tenant_runtime.py`.
- Added a hosted `streamable-http` rate limiter keyed by `tenant_id` and `client_id`, kept the
IP dimension optional and disabled by default until a proxy-trust policy is defined, chose
explicit backend failure modes with fail-closed `503 temporarily_unavailable` as the default,
and proved tenant/client budgets do not bleed across bearer tokens with
`uv run pytest tests/unit/test_hosted_rate_limits.py tests/unit/test_hosted_auth.py tests/integration/test_hosted_auth_integration.py tests/mcp/test_hosted_auth_streamable_http.py`.
- Updated `docs/security.md` and `docs/security-incident-playbook.md` to record the hosted
bearer-token contract, per-request revocation model, no-downtime tenant credential-rotation
guidance, fail-closed operator expectations, audit signals, and the exact disable, revoke,
rotate, and recovery runbook for hosted tenants.
- Updated `docs/architecture.md` and `docs/mcp-usage.md` to record the FastMCP hosted auth
hook choice, the client-facing bearer-token contract, the request-scoped multi-tenant
runtime model, the no-public-surface rule for hosted tools/resources/prompts, and the
distinction between local single-tenant developer flows and hosted `streamable-http`.
- Added `docs/hosted-deployment-guide.md`, `docs/customer-onboarding-flow.md`, and new
`README.md` links to choose the reference hosted production baseline: opaque bearer tokens
verified against Postgres-backed token metadata, Postgres tenant metadata with AWS Secrets
Manager secret references, Redis-backed shared rate limits, explicit HTTPS and proxy
assumptions, staged two-tenant rollout commands, and the operator onboarding plus rotation
flow.
- Re-reviewed webhook and attachment MCP flows against the current hosted runtime wiring; the
tool registrations still route through the shared `FollowUpBossToolAdapter` service bundle,
so attachment and webhook operations do not introduce a separate tenant-resolution bypass.
- Added `FollowUpBossTenantRuntimeDefaults` plus a credential-free hosted bootstrap path in
`create_server()` and `TenantRuntimeFactory`, so hosted auth now falls back to built-in
`base_url`/timeout/retry defaults instead of reading process-wide tenant credential environment
variables, and revalidated with
`uv run pytest tests/unit/test_auth_config_logging.py tests/unit/test_tenant_runtime.py tests/integration/test_runtime_integration.py tests/unit/test_hosted_auth.py tests/integration/test_hosted_auth_integration.py tests/mcp/test_hosted_auth_streamable_http.py`.
- Added focused coverage for the remaining hosted bootstrap and MCP helper branches in
`config.py`, `hosted_auth.py`, `hosted_rate_limits.py`, `logging.py`, `mcp_registration.py`,
`mcp_server.py`, and `mcp_tools.py`, then re-ran `make release-validate` on 2026-03-30. The full
stack now passes through `sync`, `audit`, `docs-check`, `format-check`, `lint`,
`mypy src tests`, `uv run pytest`, branch coverage at `TOTAL 5177 0 582 0 100.00%`, CLI help, and
build smoke validation, so the quality-gate checklist item is closed and only the staged rollout
tasks remain open.
- Added `FollowUpBossHostedDeploymentSettings`, `PostgresHostedTokenVerifier`,
`PostgresAwsTenantStore`, `AwsSecretsManagerTenantSecretStore`, `RedisHostedRateLimitBackend`, and
the `followupboss-mcp-hosted` entrypoint so the repository now ships a concrete reference hosted
deployment path for Phase 9 staging. Hardened hosted auth to emit a distinct
`token_verifier_unavailable` audit reason, added hosted rate-limiter shutdown support, updated the
hosted deployment guide with the concrete wrapper and reference schema, and revalidated with
`uv run ruff check src/followupboss_mcp/hosted_reference.py src/followupboss_mcp/hosted_auth.py src/followupboss_mcp/hosted_rate_limits.py src/followupboss_mcp/mcp_server.py src/followupboss_mcp/__init__.py tests/unit/test_hosted_reference.py tests/unit/test_hosted_auth.py tests/unit/test_hosted_rate_limits.py tests/unit/test_mcp_server.py tests/unit/test_auth_config_logging.py`,
`uv run mypy src tests/unit/test_hosted_reference.py tests/unit/test_hosted_auth.py tests/unit/test_hosted_rate_limits.py tests/unit/test_mcp_server.py tests/unit/test_auth_config_logging.py`,
and `uv run pytest tests/unit/test_hosted_reference.py tests/unit/test_hosted_auth.py tests/unit/test_hosted_rate_limits.py tests/unit/test_mcp_server.py tests/unit/test_auth_config_logging.py`.
