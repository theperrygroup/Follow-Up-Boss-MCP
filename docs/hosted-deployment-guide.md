# Hosted Deployment Guide

## Scope

This guide defines the reference production shape for one shared multi-tenant
`streamable-http` deployment of the Follow Up Boss MCP server.

The repository CLI and README quickstart remain local single-tenant developer paths.
Production hosting should use a dedicated wrapper around `create_server(...)` that wires
concrete implementations of:

- `HostedIdentityVerifier`
- `TenantStore`
- `HostedRateLimitBackend`

For the tenant-creation and credential-intake workflow, see
[customer-onboarding-flow.md](customer-onboarding-flow.md). For auth failure modes and incident
handling, see [security.md](security.md) and
[security-incident-playbook.md](security-incident-playbook.md).

## Reference Production Decisions

| Concern | Reference choice | Why |
| --- | --- | --- |
| Transport | `streamable-http` only | Matches the hosted boundary already implemented in the repository. |
| Hosted auth verifier backend | Opaque bearer tokens hashed in PostgreSQL and resolved by a concrete `HostedIdentityVerifier` | Immediate revocation, straightforward operator rotation, and no separate JWT signing or JWKS infrastructure required for the first hosted release. |
| Tenant metadata store | PostgreSQL `tenants` and `tenant_credentials` tables | Strong consistency, auditable row updates, and simple operator tooling. |
| Tenant secret store | AWS Secrets Manager referenced by `secret_ref` or ARN from the credential row | Keeps raw Follow Up Boss secrets out of the database while still allowing request-time resolution into `TenantCredentialRecord`. |
| Hosted endpoint rate-limit backend | Redis shared by every app instance | Prevents per-process budget drift and replaces the development-only in-memory limiter. |
| TLS termination | Trusted reverse proxy or load balancer | The app can stay on private HTTP behind the proxy, but the client-facing contract is always HTTPS. |
| Failure stance | Fail closed for auth, tenant store, secret store, and rate-limit backend outages | Matches the repository's hosted security model. |

Opaque hosted bearer tokens are the reference backend for the first shared deployment. Signed
JWTs remain compatible with the verifier abstraction, but they are not the reference operator path
until there is a stronger need for third-party issuer federation or public-key distribution.

## What Production Must Not Use

- Do not run `uv run python -m followupboss_mcp.cli streamable-http` as the shared production
  entrypoint. That CLI is intentionally local and single-tenant.
- Do not use `DevelopmentTenantStore` or `DevelopmentHostedTokenVerifier` in shared staging or
  production.
- Do not rely on the default in-memory hosted rate limiter across more than one application
  instance.
- Do not load customer-specific `FOLLOWUPBOSS_API_KEY`, `FOLLOWUPBOSS_ACCESS_TOKEN`, or
  `FOLLOWUPBOSS_SYSTEM_KEY` into shared process bootstrap configuration.

## Reference Component Layout

```mermaid
flowchart LR
    A["Hosted client"] --> B["HTTPS proxy or load balancer"]
    B --> C["Shared FastMCP app"]
    C --> D["Opaque token verifier\nPostgreSQL token table"]
    C --> E["Tenant store\nPostgreSQL metadata"]
    E --> F["AWS Secrets Manager"]
    C --> G["Redis rate-limit backend"]
    C --> H["Request-scoped Follow Up Boss client"]
    H --> I["Follow Up Boss API"]
```

The shared deployment wrapper should construct:

- `HostedAuthSettings`
- a PostgreSQL-backed `HostedIdentityVerifier`
- a PostgreSQL plus AWS Secrets Manager-backed `TenantStore`
- `HostedEndpointRateLimiter` configured with a Redis-backed `HostedRateLimitBackend`

## Required Infrastructure

The reference shared deployment needs:

- one or more ASGI application instances running the FastMCP server
- a trusted HTTPS proxy or load balancer in front of the app instances
- PostgreSQL for tenant metadata and hosted bearer-token metadata
- AWS Secrets Manager for raw Follow Up Boss API keys, OAuth access tokens, and optional
  `system_key` values
- Redis for multi-instance hosted endpoint rate limiting
- centralized log aggregation capable of filtering on audit events such as
  `hosted_auth_failed` and `tenant_resolution_failed`
- alerting on auth failures, tenant-store failures, secret-store failures, and hosted
  rate-limit backend failures

The reference AWS-flavored deployment maps naturally to:

- ECS, EKS, or another container scheduler for the app
- RDS PostgreSQL for metadata
- AWS Secrets Manager for tenant secret payloads
- ElastiCache Redis or another managed Redis service for rate limiting

Equivalent managed services on other platforms are acceptable as long as they preserve the same
runtime boundaries:

- metadata in a durable database
- raw tenant secrets in a managed secret store
- rate-limit budgets in a shared low-latency backend

## Reference Data Model

The production wrapper should project these backing records into the repository models:

| Backing store | Reference fields | Projected runtime model |
| --- | --- | --- |
| `tenants` table | `tenant_id`, `tenant_slug`, `display_name`, `credential_id`, `status` | `TenantRecord` |
| `tenant_credentials` table | `credential_id`, `tenant_id`, `auth_mode`, `system_name`, `secret_ref`, `status` | `TenantCredentialRecord` after secret resolution |
| `hosted_access_tokens` table | `token_id`, `token_hash`, `tenant_id`, `subject`, `client_id`, `scopes`, `credential_id`, `expires_at`, `revoked_at` | `HostedVerifiedIdentity` |

The raw Follow Up Boss secret payload should live only in AWS Secrets Manager. The PostgreSQL
credential row should contain non-secret metadata plus the secret reference needed to fetch the
payload at request time.

## Bootstrap Configuration

### Existing Repository Bootstrap Settings

The production wrapper should still honor the existing server bootstrap and shared transport
defaults:

- `FOLLOWUPBOSS_TRANSPORT=streamable-http`
- `FOLLOWUPBOSS_HOST`
- `FOLLOWUPBOSS_PORT`
- `FOLLOWUPBOSS_STREAMABLE_HTTP_PATH`
- `FOLLOWUPBOSS_LOG_LEVEL`
- `FOLLOWUPBOSS_BASE_URL`
- `FOLLOWUPBOSS_TIMEOUT_SECONDS`
- `FOLLOWUPBOSS_MAX_RETRIES`

These values remain global defaults for the hosted deployment. They are safe to share across
tenants because they do not carry customer-specific Follow Up Boss credentials.

### Reference Hosted Wrapper Settings

The local CLI does not parse hosted production settings today. The shared deployment should
instead use a thin wrapper that reads operator configuration and constructs the hosted objects
programmatically. The following environment variable names are the reference contract for that
wrapper:

| Variable | Purpose |
| --- | --- |
| `FOLLOWUPBOSS_HOSTED_ISSUER_URL` | Stable issuer URL exposed in `HostedAuthSettings`. For opaque tokens, point this at the hosted control-plane or customer portal base URL. |
| `FOLLOWUPBOSS_HOSTED_RESOURCE_SERVER_URL` | External HTTPS URL for the shared MCP endpoint, such as `https://mcp.example.com/mcp`. |
| `FOLLOWUPBOSS_HOSTED_REQUIRED_SCOPES` | Comma-separated scope list. The reference value is `followupboss:mcp`. |
| `FOLLOWUPBOSS_TENANT_DATABASE_URL` | PostgreSQL connection string for tenant and hosted-token metadata. |
| `FOLLOWUPBOSS_TENANT_SECRET_PREFIX` | AWS Secrets Manager path prefix, such as `followupboss/prod/tenants/`. |
| `FOLLOWUPBOSS_TENANT_SECRET_REGION` | AWS region used for the tenant secret store. |
| `FOLLOWUPBOSS_REDIS_URL` | Redis connection string for hosted rate limiting. |
| `FOLLOWUPBOSS_RATE_LIMIT_REQUESTS_PER_WINDOW` | Hosted request budget per window. Start at `300`. |
| `FOLLOWUPBOSS_RATE_LIMIT_WINDOW_SECONDS` | Hosted rate-limit window length. Start at `60`. |
| `FOLLOWUPBOSS_RATE_LIMIT_INCLUDE_CLIENT_IP` | `true` only when proxy trust is fully defined and sanitized. Default `false`. |

Reference example:

```bash
FOLLOWUPBOSS_TRANSPORT=streamable-http
FOLLOWUPBOSS_HOST=0.0.0.0
FOLLOWUPBOSS_PORT=8000
FOLLOWUPBOSS_STREAMABLE_HTTP_PATH=/mcp
FOLLOWUPBOSS_LOG_LEVEL=INFO
FOLLOWUPBOSS_BASE_URL=https://api.followupboss.com/v1
FOLLOWUPBOSS_TIMEOUT_SECONDS=10
FOLLOWUPBOSS_MAX_RETRIES=3

FOLLOWUPBOSS_HOSTED_ISSUER_URL=https://portal.example.com
FOLLOWUPBOSS_HOSTED_RESOURCE_SERVER_URL=https://mcp.example.com/mcp
FOLLOWUPBOSS_HOSTED_REQUIRED_SCOPES=followupboss:mcp
FOLLOWUPBOSS_TENANT_DATABASE_URL=postgresql://app:***@db.example.com:5432/followupboss_mcp
FOLLOWUPBOSS_TENANT_SECRET_PREFIX=followupboss/prod/tenants/
FOLLOWUPBOSS_TENANT_SECRET_REGION=us-east-1
FOLLOWUPBOSS_REDIS_URL=redis://cache.example.com:6379/0
FOLLOWUPBOSS_RATE_LIMIT_REQUESTS_PER_WINDOW=300
FOLLOWUPBOSS_RATE_LIMIT_WINDOW_SECONDS=60
FOLLOWUPBOSS_RATE_LIMIT_INCLUDE_CLIENT_IP=false
```

### Hosted Wrapper Construction

The dedicated hosted wrapper should remain the production entrypoint, but now for a narrower
reason: it is responsible for constructing the hosted auth verifier, tenant store, secret-store
integration, and optional shared rate-limit backend.

The hosted `create_server()` path can now accept a dedicated
`FollowUpBossTenantRuntimeDefaults` object for the shared non-secret Follow Up Boss defaults. When
that object is omitted, the server falls back to the built-in `base_url`, timeout, and retry
defaults without reading process-wide tenant credential environment variables.

That keeps the local CLI explicitly single-tenant while letting the hosted wrapper decide whether
those non-secret defaults come from environment variables, another config source, or the repository
constants.

## HTTPS And Proxy Assumptions

The reference deployment assumes:

- the externally visible MCP URL is always HTTPS
- TLS is terminated only at a trusted proxy or load balancer
- the app instances listen on private HTTP only inside the trusted network boundary
- the proxy preserves the `Authorization` header exactly as received
- the proxy strips any client-supplied forwarded headers before adding its own trusted
  `X-Forwarded-*` values
- the app treats `client_ip` as untrusted unless the proxy chain and header sanitation policy are
  documented and enforced
- the proxy does not rewrite the hosted MCP path unless
  `FOLLOWUPBOSS_HOSTED_RESOURCE_SERVER_URL` is updated to the exact external path
- proxy idle timeouts are long enough for normal `streamable-http` client sessions
- proxy or CDN buffering is disabled for MCP traffic

Keep `FOLLOWUPBOSS_RATE_LIMIT_INCLUDE_CLIENT_IP=false` until both of these are true:

1. every trusted proxy hop is explicitly known
2. the deployment strips and rewrites forwarded headers at the edge

Until then, rate limiting should stay partitioned only by `tenant_id` and `client_id`.

## Hosted Auth Verifier Expectations

The reference `HostedIdentityVerifier` should:

- accept opaque bearer tokens generated by the operator control plane
- store only a one-way hash of the raw token in PostgreSQL
- reject revoked, expired, or unknown tokens without revealing whether the tenant exists
- always populate `tenant_id`, `subject`, and `client_id`
- always populate `credential_id` in the reference deployment so credential binding mismatches
  fail closed on the next request
- optionally populate `token_id`, `scopes`, and `expires_at`

Recommended token metadata:

- `subject`: stable integration principal or service account identifier
- `client_id`: stable client application identifier such as `customer-portal` or `zapier-prod`
- `scopes`: start with `followupboss:mcp`
- `expires_at`: short enough to limit blast radius, long enough for operational usability
- `credential_id`: the currently active tenant credential binding

The reference verifier does not need to expose raw token values after issuance. Token rotation is
done by creating a second active token row, distributing it, and then revoking the old row after
validation.

## Tenant Store And Secret Store Expectations

The reference `TenantStore` should resolve tenants in two steps:

1. read non-secret tenant and credential metadata from PostgreSQL
2. fetch the raw Follow Up Boss secret payload from AWS Secrets Manager using the credential row's
   secret reference

The assembled runtime must then produce a `TenantCredentialRecord` containing:

- `credential_id`
- `tenant_id`
- `auth_mode`
- one of `api_key` or `access_token`
- optional `system_name`
- optional `system_key`
- `status`

Reference storage rules:

- `tenant_id` is stable and never reused
- `tenant_slug` is stable enough for logs and operator dashboards
- `credential_id` is stable across in-place secret rotation when existing hosted tokens should
  continue working
- raw API keys, access tokens, and `system_key` values never live in PostgreSQL plaintext columns
- IAM access to the secret store is scoped only to the app role and operator workflows that manage
  tenant onboarding or rotation

## Hosted Rate-Limit Backend Expectations

Redis is the reference hosted rate-limit backend.

The backend should preserve the repository's current semantics:

- budget keys partition by `tenant_id` and `client_id`
- `client_ip` is optional and disabled by default
- default starting budget is `300` requests per `60` seconds
- backend failures default to `closed`
- exceeded budgets return `429 rate_limited` with `Retry-After`
- backend failures in closed mode return `503 temporarily_unavailable` with `Retry-After`

Operational rules:

- do not key rate limits by raw bearer token; rotation should not silently mint new budgets for
  the same client
- use one shared Redis deployment or cluster for every app instance serving the same environment
- alert on `hosted_rate_limit_backend_failed`
- watch `hosted_rate_limit_exceeded` by `tenant_id` and `client_id` for abuse or runaway clients

## Staged Validation Prerequisites

Before rollout, prepare two real hosted test tenants on the same shared deployment:

- `tenant-a`: one real Follow Up Boss sandbox or disposable account
- `tenant-b`: a different real Follow Up Boss sandbox or disposable account

Create one unique fixture person in each account so tenant isolation can be checked safely:

- `TENANT_A_FIXTURE_EMAIL`, only present in tenant A
- `TENANT_B_FIXTURE_EMAIL`, only present in tenant B

Export:

```bash
export STAGING_MCP_URL="https://staging-mcp.example.com/mcp"
export TENANT_A_TOKEN="replace-with-real-hosted-token"
export TENANT_B_TOKEN="replace-with-real-hosted-token"
export TENANT_A_FIXTURE_EMAIL="mcp-tenant-a@example.com"
export TENANT_B_FIXTURE_EMAIL="mcp-tenant-b@example.com"
```

## Staged Validation Commands

### 1. Invalid Token Fails Closed

```bash
TOKEN="definitely-invalid" uv run python - <<'PY'
import asyncio
import os

import httpx
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client


async def main() -> None:
    try:
        async with httpx.AsyncClient(
            headers={"Authorization": f"Bearer {os.environ['TOKEN']}"},
            timeout=30.0,
        ) as http_client:
            async with streamable_http_client(
                os.environ["STAGING_MCP_URL"],
                http_client=http_client,
            ) as (read_stream, write_stream, _):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    await session.call_tool("followupboss_get_identity", {})
    except Exception as exc:
        print(f"expected auth failure: {type(exc).__name__}: {exc}")
        return
    raise SystemExit("expected hosted auth failure but the request succeeded")


asyncio.run(main())
PY
```

This should fail before any authenticated tool call succeeds.

### 2. Shared Deployment Smoke For Each Tenant

```bash
run_tenant_smoke() {
  LABEL="$1" TOKEN="$2" OWN_FIXTURE_EMAIL="$3" OTHER_FIXTURE_EMAIL="$4" uv run python - <<'PY'
import asyncio
import json
import os

import httpx
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client


async def main() -> None:
    async with httpx.AsyncClient(
        headers={"Authorization": f"Bearer {os.environ['TOKEN']}"},
        timeout=30.0,
    ) as http_client:
        async with streamable_http_client(
            os.environ["STAGING_MCP_URL"],
            http_client=http_client,
        ) as (read_stream, write_stream, _):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()

                identity = await session.call_tool("followupboss_get_identity", {})
                own_people = await session.call_tool(
                    "followupboss_search_people",
                    {"email": os.environ["OWN_FIXTURE_EMAIL"], "limit": 5},
                )
                other_people = await session.call_tool(
                    "followupboss_search_people",
                    {"email": os.environ["OTHER_FIXTURE_EMAIL"], "limit": 5},
                )

                resources = await session.list_resources()
                resource_result = await session.read_resource(resources.resources[0].uri)
                prompts = await session.list_prompts()
                prompt_result = await session.get_prompt(
                    prompts.prompts[0].name,
                    {
                        "source": "Portal",
                        "type": "Inquiry",
                        "message": "Hosted deployment validation",
                        "email": os.environ["OWN_FIXTURE_EMAIL"],
                    },
                )

                own_count = len(own_people.structuredContent["people"])
                other_count = len(other_people.structuredContent["people"])
                if own_count < 1:
                    raise SystemExit("expected at least one own-tenant fixture result")
                if other_count != 0:
                    raise SystemExit("expected zero cross-tenant fixture results")

                print(
                    json.dumps(
                        {
                            "label": os.environ["LABEL"],
                            "identity": identity.structuredContent,
                            "own_fixture_count": own_count,
                            "other_fixture_count": other_count,
                            "resource_count": len(resource_result.contents),
                            "prompt_message_count": len(prompt_result.messages),
                        },
                        indent=2,
                        sort_keys=True,
                    )
                )


asyncio.run(main())
PY
}

run_tenant_smoke "tenant-a" "$TENANT_A_TOKEN" "$TENANT_A_FIXTURE_EMAIL" "$TENANT_B_FIXTURE_EMAIL"
run_tenant_smoke "tenant-b" "$TENANT_B_TOKEN" "$TENANT_B_FIXTURE_EMAIL" "$TENANT_A_FIXTURE_EMAIL"
```

Both commands must use the same `STAGING_MCP_URL`. That is the proof that one shared deployment is
serving both tenants safely.

### 3. Credential Rotation Smoke

After rotating tenant B's Follow Up Boss credential in the secret store without changing
`credential_id`, rerun:

```bash
run_tenant_smoke "tenant-b-post-rotation" "$TENANT_B_TOKEN" "$TENANT_B_FIXTURE_EMAIL" "$TENANT_A_FIXTURE_EMAIL"
```

This should still succeed on the next request. Tenant A should remain unaffected.

### 4. Hosted Token Rotation Smoke

After issuing a replacement hosted bearer token for tenant A:

```bash
export TENANT_A_TOKEN_NEW="replace-with-new-hosted-token"
run_tenant_smoke "tenant-a-new-token" "$TENANT_A_TOKEN_NEW" "$TENANT_A_FIXTURE_EMAIL" "$TENANT_B_FIXTURE_EMAIL"
```

Then revoke the old tenant A token and confirm it fails closed by rerunning the invalid-token check
with the old value.

## Rollout Checks

Do not widen rollout until every check below passes:

- invalid or revoked hosted bearer tokens fail before any tool call succeeds
- tenant A and tenant B both succeed against the same shared `STAGING_MCP_URL`
- tenant A can read tenant A's fixture but not tenant B's fixture
- tenant B can read tenant B's fixture but not tenant A's fixture
- at least one resource read and one prompt render succeed under hosted auth
- logs show `hosted_auth_succeeded`, `tenant_resolution_succeeded`, and `upstream_credential_usage`
  for both tenants
- logs do not show `hosted_rate_limit_backend_failed`
- a no-downtime Follow Up Boss credential rotation succeeds for one tenant without impacting the
  other tenant
- a hosted bearer-token rotation succeeds, and the revoked token fails closed on the next request

Use this table to capture rollout evidence:

| Check | Status | Evidence |
| --- | --- | --- |
| Invalid token fails closed | | |
| Tenant A shared-endpoint smoke | | |
| Tenant B shared-endpoint smoke | | |
| Cross-tenant fixture isolation | | |
| Resource and prompt auth boundary | | |
| Tenant B credential rotation | | |
| Tenant A bearer-token rotation | | |
| Hosted rate-limit backend healthy | | |

## Local Development Fallback

The acceptable non-production fallback remains:

- local `stdio` and local single-tenant `streamable-http` use `FollowUpBossSettings` from
  environment variables
- hosted-style local testing can use `DevelopmentTenantStore.from_local_dev_settings(...)`
- hosted-style local token testing can use `DevelopmentHostedTokenVerifier.from_mapping(...)`

Those helpers are acceptable only for local development, focused tests, and disposable staging-like
experiments that do not use production tenant secrets.
