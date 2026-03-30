# Multi-Tenant Hosting Checklist

## Goal

Refactor the hosted Follow Up Boss MCP server so outside customers can connect to one shared
`streamable-http` deployment while using their own Follow Up Boss account credentials instead
of a single process-wide credential.

## Current State Snapshot

- `src/followupboss_mcp/config.py` mixes server configuration and Follow Up Boss credentials.
- `src/followupboss_mcp/mcp_server.py` creates one shared `FollowUpBossAsyncClient` at startup.
- `src/followupboss_mcp/mcp_registration.py` registers the MCP surface against one shared tool
  adapter.
- Hosted inbound authentication is not implemented yet.
- `stdio` and `streamable-http` are both supported today, but only the HTTP transport is relevant
  for a shared hosted product.

## Success Criteria

- [ ] Hosted `streamable-http` requests require inbound authentication.
- [ ] Each authenticated caller resolves to exactly one tenant.
- [ ] Tenant credentials are loaded from a database or secret store, not global environment
      variables.
- [ ] `FollowUpBossAsyncClient` instances are created per request or per session instead of once
      at process startup.
- [x] MCP tools, resources, and prompts use the authenticated tenant context safely.
- [ ] Invalid, expired, or unauthorized tokens fail closed with safe error messages.
- [ ] Cross-tenant access is prevented and covered by tests.
- [ ] Local development remains possible and documented.

## Core Objectives

- [x] Split server config from tenant auth config.
- [ ] Stop creating one shared `FollowUpBossAsyncClient` in `create_server()`.
- [ ] Make client and service creation request-scoped or session-scoped based on the
      authenticated customer.
- [ ] Add inbound auth for the hosted MCP endpoint so the server can identify the tenant.

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
- `docs/mcp-usage.md`
- `docs/security.md`

## Phase 0: Decisions And Guardrails

- [x] Confirm the hosted multi-tenant product is only supported over `streamable-http`.
- [x] Decide that `stdio` remains an explicit local-dev-only single-tenant developer path for
      now.
- [ ] Decide whether inbound auth uses signed JWTs, opaque API tokens, or both.
- [ ] Decide whether tenant credentials support stored API keys, stored OAuth access tokens, or
      both.
- [ ] Decide whether tenant runtime objects should be request-scoped or session-scoped for the
      hosted HTTP transport.
- [ ] Decide where tenant secrets live in production.
- [ ] Decide what local development fallback is acceptable for secret storage.
- [ ] Define minimum audit logging requirements for tenant authentication and upstream Follow Up
      Boss usage.
- [x] Define token revocation, expiration, and credential-rotation requirements.

## Phase 1: Split Server Config From Tenant Credentials

- [x] Introduce a server-only settings model for host, port, log level, transport, and other
      non-tenant runtime options.
- [ ] Remove customer-specific Follow Up Boss credentials from the startup settings path used by
      hosted mode.
- [ ] Preserve only server-level environment variables in the hosted server bootstrap flow.
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
- [ ] Choose the production implementation:
- [ ] Database row with encrypted credential payload.
- [ ] Database row plus external secret-manager reference.
- [ ] Another production-safe secret storage pattern.
- [x] Implement a development-safe store for local testing.
- [ ] Ensure tenant credentials are encrypted at rest or retrieved from a managed secret store.
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
- [ ] Re-review webhook and attachment flows for tenant-isolation assumptions.

## Phase 7: Test Coverage

- [ ] Add unit tests for the new server-only settings model.
- [x] Add unit tests for the tenant store abstraction and its error cases.
- [ ] Add unit tests for inbound token verification and tenant resolution.
- [ ] Add unit tests for client-factory construction from tenant credentials.
- [x] Add MCP HTTP tests that prove different bearer tokens route to different tenant runtimes.
- [x] Add MCP HTTP tests that prove invalid or missing auth is rejected.
- [x] Add MCP tests that confirm tools, resources, and prompts still work after the refactor.
- [ ] Add regression coverage for `stdio` so its supported behavior is explicit and documented.
- [x] Re-run focused MCP, auth, and HTTP client suites during the refactor.
- [ ] Re-run the full quality gate before closing the workstream.

## Phase 8: Documentation And Operations

- [ ] Update `docs/architecture.md` for the new hosted multi-tenant runtime model.
- [ ] Update `docs/mcp-usage.md` to explain hosted authentication requirements.
- [x] Update `docs/security.md` with tenant secret handling, inbound auth, and rotation guidance.
- [ ] Add a hosted deployment guide that explains required infrastructure and secrets.
- [ ] Document the expected customer onboarding flow for saving their Follow Up Boss credential.
- [x] Document how to disable a tenant, revoke a token, and rotate a compromised credential.
- [ ] Decide whether `README.md` should describe the hosted multi-tenant path directly or point to
      a dedicated deployment document.

## Phase 9: Rollout Checklist

- [ ] Stand up a staging tenant store and secret store.
- [ ] Validate at least two test tenants against the same hosted server instance.
- [ ] Confirm tenant A cannot access tenant B data even with replayed or swapped identifiers.
- [ ] Confirm the hosted endpoint behaves correctly after token expiration and credential
      rotation.
- [ ] Confirm operational dashboards or logs can distinguish tenant auth failures from upstream
      Follow Up Boss failures.
- [ ] Pilot the hosted flow with one external customer before wider rollout.

## Open Questions

- [ ] Should local `stdio` continue to read tenant credentials from environment variables, or
      should it also move behind the tenant store abstraction?
- [ ] Do we want session-scoped client reuse for streamable HTTP, or is request-scoped construction
      simpler and safer for the first release?
- [ ] Is the first hosted release API-key-only, OAuth-only, or dual-mode?
- [ ] Which secret-store and database backend should be treated as the production reference
      implementation?
- [x] Do resources and prompts require the same inbound auth guarantees as tools, or can any stay
      unauthenticated?
      Decision: hosted mode keeps no intentionally public resources or prompts; all registered MCP
      surfaces follow the same tenant-auth boundary.

## Evidence Log

- [ ] Record the FastMCP auth hook choice and the rationale.
- [ ] Record the tenant store interface and production implementation choice.
- [x] Record the inbound auth token format and revocation model.
- [x] Record the client lifecycle choice: request-scoped or session-scoped.
- [ ] Record the final staged validation commands and results.

## Done Definition

- [ ] Server config and tenant credential handling are separated cleanly.
- [ ] Hosted HTTP requests require inbound auth and resolve to a single tenant.
- [ ] Tenant credentials are no longer loaded from process-wide environment variables in hosted
      mode.
- [ ] No shared Follow Up Boss client is created at server startup for hosted mode.
- [ ] Tenant-specific clients, services, and adapters are created safely from authenticated
      context.
- [ ] Tests cover multi-tenant routing, auth failure paths, and tenant isolation.
- [ ] Documentation explains how the hosted multi-tenant deployment works.

## Evidence Notes

- [x] Added `FollowUpBossServerSettings` and `FollowUpBossTenantSettings`, while keeping
      `FollowUpBossSettings` as a backward-compatible local single-tenant wrapper.
- [x] Updated `create_server()`, the CLI, examples, and focused docs/tests so server bootstrap
      settings and tenant auth/runtime settings are no longer modeled as one undifferentiated
      object.
- [x] Added `TenantRecord`, `TenantCredentialRecord`, `TenantStore`, and
      `DevelopmentTenantStore`, plus focused tenant-store tests for active, disabled, revoked,
      and missing-credential resolution paths while keeping a local-dev bridge via
      `DevelopmentTenantStore.from_local_dev_settings(...)`.
- [x] Added `HostedVerifiedIdentity`, `HostedAuthSettings`, a tenant-resolving FastMCP token
      verifier, and `DevelopmentHostedTokenVerifier`, while deferring default client creation
      behind hosted auth so invalid, expired, disabled-tenant, revoked-credential, missing-tenant,
      and wrong-tenant bearer tokens fail closed before any upstream Follow Up Boss client is
      instantiated.
- [x] Added `TenantRuntime`, `TenantRuntimeFactory`, and request-scoped service-bundle resolution
      so hosted tool calls materialize tenant-specific `FollowUpBossTenantSettings`, inherit
      `base_url`/`timeout_seconds`/`max_retries` from shared defaults, close clients after each
      call, and prove with focused MCP/auth tests that different bearer tokens do not share client
      instances or credential material.
- [x] Routed hosted resources and prompts through the same `TenantRuntimeFactory` auth-context path
      as tools, decided that hosted mode exposes no intentionally public MCP surfaces, and proved
      with `uv run pytest tests/unit/test_tenant_runtime.py tests/mcp/test_hosted_auth_streamable_http.py tests/integration/test_hosted_auth_integration.py tests/mcp/test_mcp_tools_server_cli.py tests/integration/test_runtime_integration.py`
      that tools, resources, and prompts preserve tenant isolation while local server-surface
      behavior remains intact.
- [x] Hardened hosted resource/prompt runtime-resolution failures so MCP responses stay JSON-safe
      and token-safe, expanded logging/object redaction to include bearer-token-style fields and
      `HostedAccessToken` representations, wrapped tenant/secret store backend outages into
      fail-closed tenant-store errors, and revalidated with
      `uv run pytest tests/unit/test_auth_config_logging.py tests/unit/test_hosted_auth.py tests/unit/test_tenant_store.py tests/unit/test_tenant_runtime.py tests/integration/test_hosted_auth_integration.py tests/mcp/test_hosted_auth_streamable_http.py tests/unit/test_http_client.py`.
- [x] Added machine-readable audit-log helpers plus per-tenant hosted audit events for bearer-token
      authentication success/failure, tenant-resolution success/failure, and request-scoped
      upstream credential usage without logging raw bearer tokens, API keys, access tokens, or
      system keys, and revalidated with
      `uv run pytest tests/unit/test_auth_config_logging.py tests/unit/test_hosted_auth.py tests/unit/test_tenant_runtime.py`.
- [x] Added a hosted `streamable-http` rate limiter keyed by `tenant_id` and `client_id`, kept the
      IP dimension optional and disabled by default until a proxy-trust policy is defined, chose
      explicit backend failure modes with fail-closed `503 temporarily_unavailable` as the default,
      and proved tenant/client budgets do not bleed across bearer tokens with
      `uv run pytest tests/unit/test_hosted_rate_limits.py tests/unit/test_hosted_auth.py tests/integration/test_hosted_auth_integration.py tests/mcp/test_hosted_auth_streamable_http.py`.
- [x] Updated `docs/security.md` and `docs/security-incident-playbook.md` to record the hosted
      bearer-token contract, per-request revocation model, no-downtime tenant credential-rotation
      guidance, fail-closed operator expectations, audit signals, and the exact disable, revoke,
      rotate, and recovery runbook for hosted tenants.
