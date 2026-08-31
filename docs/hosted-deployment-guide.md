# Hosted Deployment Guide

## Scope

This guide defines the reference production shape for one shared multi-tenant
`streamable-http` deployment of the Follow Up Boss MCP server.

The repository CLI and README quickstart remain local single-tenant developer paths.
The repository now also ships a reference hosted wrapper in
`src/followupboss_mcp/hosted_reference.py`, exposed as `followupboss-mcp-hosted`, which wires:

- `PostgresHostedTokenVerifier`
- `PostgresAwsTenantStore`
- `AwsSecretsManagerTenantSecretStore`
- `RedisHostedRateLimitBackend`

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
| MCP client login | Hosted OAuth authorization server delegating user consent to Follow Up Boss OAuth | Lets Cursor discover OAuth metadata, complete browser consent, and receive MCP-scoped bearer tokens without treating raw Follow Up Boss tokens as MCP credentials. |
| TLS termination | Trusted reverse proxy or load balancer | The app can stay on private HTTP behind the proxy, but the client-facing contract is always HTTPS. |
| Failure stance | Fail closed for auth, tenant store, secret store, and rate-limit backend outages | Matches the repository's hosted security model. |

Opaque hosted bearer tokens are the reference backend for the first shared deployment. Signed
JWTs remain compatible with the verifier abstraction, but they are not the reference operator path
until there is a stronger need for third-party issuer federation or public-key distribution.

## What Production Must Not Use

- Do not run `uv run python -m followupboss_mcp.cli streamable-http` as the shared production
  entrypoint. That CLI is intentionally local and single-tenant.
- Do not use `DevelopmentTenantStore` or `DevelopmentHostedTokenVerifier` in shared production.
- Do not rely on the default in-memory hosted rate limiter across more than one application
  instance.
- Do not load customer-specific `FOLLOWUPBOSS_API_KEY`, `FOLLOWUPBOSS_ACCESS_TOKEN`, or
  `FOLLOWUPBOSS_SYSTEM_KEY` into shared process bootstrap configuration.

## Reference Component Layout

```mermaid
flowchart LR
    A["Hosted client"] --> B["HTTPS proxy or load balancer"]
    B --> C["Shared MCPServer app"]
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

The repository reference wrapper constructs those abstractions with:

- `FollowUpBossHostedDeploymentSettings`
- `PostgresHostedTokenVerifier`
- `PostgresAwsTenantStore`
- `AwsSecretsManagerTenantSecretStore`
- `RedisHostedRateLimitBackend`

## Required Infrastructure

The reference shared deployment needs:

- one or more ASGI application instances running the MCPServer server
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
| `hosted_access_tokens` table | `token_id`, `token_hash`, `tenant_id`, `subject`, `client_id`, `scopes`, `resource`, `credential_id`, `expires_at`, `revoked_at` | `HostedVerifiedIdentity` |

The raw Follow Up Boss secret payload should live only in AWS Secrets Manager. The PostgreSQL
credential row should contain non-secret metadata plus the secret reference needed to fetch the
payload at request time.

### Reference PostgreSQL Schema

The repository's reference hosted backends currently read exactly these columns:

```sql
CREATE TABLE tenants (
    tenant_id TEXT PRIMARY KEY,
    tenant_slug TEXT NOT NULL UNIQUE,
    display_name TEXT NULL,
    credential_id TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('active', 'disabled'))
);

CREATE TABLE tenant_credentials (
    credential_id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL REFERENCES tenants (tenant_id),
    auth_mode TEXT NOT NULL CHECK (auth_mode IN ('api_key', 'oauth')),
    system_name TEXT NULL,
    secret_ref TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('active', 'revoked'))
);

CREATE TABLE hosted_access_tokens (
    token_id TEXT PRIMARY KEY,
    token_hash TEXT NOT NULL UNIQUE,
    tenant_id TEXT NOT NULL REFERENCES tenants (tenant_id),
    subject TEXT NOT NULL,
    client_id TEXT NOT NULL,
    scopes TEXT[] NOT NULL DEFAULT ARRAY['followupboss:mcp'],
    resource TEXT NOT NULL,
    credential_id TEXT NOT NULL,
    expires_at BIGINT NULL,
    revoked_at BIGINT NULL
);

CREATE INDEX hosted_access_tokens_lookup_idx
    ON hosted_access_tokens (token_hash)
    WHERE revoked_at IS NULL;

CREATE TABLE hosted_oauth_clients (
    client_id TEXT PRIMARY KEY,
    client_name TEXT NOT NULL,
    redirect_uris TEXT[] NOT NULL,
    scope TEXT[] NOT NULL DEFAULT ARRAY['followupboss:mcp'],
    token_endpoint_auth_method TEXT NOT NULL DEFAULT 'none'
);

CREATE TABLE hosted_oauth_refresh_tokens (
    token_hash TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL REFERENCES tenants (tenant_id),
    subject TEXT NOT NULL,
    client_id TEXT NOT NULL,
    scopes TEXT[] NOT NULL DEFAULT ARRAY['followupboss:mcp'],
    resource TEXT NOT NULL,
    credential_id TEXT NOT NULL,
    expires_at BIGINT NOT NULL,
    revoked_at BIGINT NULL
);

CREATE INDEX hosted_oauth_refresh_tokens_active_idx
    ON hosted_oauth_refresh_tokens (token_hash)
    WHERE revoked_at IS NULL;
```

`PostgresHostedTokenVerifier` looks up bearer tokens by the `sha256:`-prefixed token hash. The
repository helper `hash_hosted_bearer_token(...)` produces the expected lookup value for stored
opaque tokens.

### Existing OAuth Row Transition

Use `scripts/migrate_hosted_oauth_resource.py` for existing databases. It validates that the
explicit `--resource` is canonical and exactly matches
`FOLLOWUPBOSS_HOSTED_RESOURCE_SERVER_URL`, keeps the database URL out of the `psql` argument list,
and defaults every write phase to a non-connecting dry run. Every SQL phase uses bounded lock and
statement timeouts and a transaction. Write phases also use an advisory migration lock,
parameterized resource values, reviewed row counts, and postcondition checks.

The repository production workflow runs the same utility inside a dedicated, migration-only
Fargate task in the service VPC. Merge the reviewed migration-capable release to `main`, then
dispatch `.github/workflows/deploy-production.yml` from `main` with `operation=expand`, followed by
`operation=status`, and finally
`operation=backfill` with the two exact status counts and
`acknowledge_unbound_token_audience=true`. The helper suppresses raw PostgreSQL output; CloudWatch
and the public Actions log receive only a generic failure classification or a sanitized aggregate
receipt. On first adoption of a bare Secrets Manager ARN, the workflow requires one sole completed
ECS deployment, conservatively proves that deployment was created after the secret's last change
and safety window, rejects a distinct `AWSPENDING` version, resolves the exact `AWSCURRENT` version,
and pins the stable service and migration task to that immutable version. The workflow rechecks that
the complete version metadata is unchanged after the pin, before starting migration. Only the explicit `expand`
operation may perform that first adoption and enable ECS deployment-circuit-breaker rollback; every
other phase fails closed while the service still uses a bare ARN and never calls `update-service`.
Later phases reuse the already-pinned version as authoritative and never advance production merely
because `AWSCURRENT` rotated; a secret version upgrade requires its own deploy and acceptance path.
A normal production deployment runs the read-only `verify-ready` phase and fails before replacing
any ECS task unless both tables have zero unbound/foreign rows and are either in the guarded rolling
state (nullable with the canonical default) or the finalized state (`NOT NULL` with no default).

After authenticated modern- and legacy-protocol live acceptance, compute separate SHA-256 digests
of the two sanitized evidence records. Dispatch `operation=record-acceptance` with those digests,
the exact live-tested SHA, and the task-definition ARN from the deployment receipt. That callback
revalidates one sole completed `PRIMARY` deployment with exact task-definition and per-deployment
counts, then publishes an immutable, event-bound Actions artifact.
Then dispatch `operation=status` again. Finalization requires `operation=finalize`,
`old_writers_retired=true`, and only the successful `record-acceptance` run ID; it downloads and
validates that artifact, freshly revalidates a sole completed deployment for the accepted task
definition (unchanged across finalization's two service snapshots), and requires
the artifact's SHA, task definition, and resource to match. This binds acceptance to the immutable
image digest and rendered runtime configuration, not only the Git SHA. Use
`operation=rollback-finalize` before rolling back the application after finalization.

Set the two existing deployment values in the operator shell. Do not paste a database URL into a
command argument:

```bash
export FOLLOWUPBOSS_HOSTED_RESOURCE_SERVER_URL="https://your-host.example/mcp"
export FOLLOWUPBOSS_TENANT_DATABASE_URL="postgresql://..."
```

Perform the transition in this order:

1. Print the expand plan, then add nullable columns with a temporary constant default equal to the
   explicit canonical resource. The default makes an old application that omits the new column
   write correctly bound rows throughout the rolling deployment:

   ```bash
   uv run python scripts/migrate_hosted_oauth_resource.py expand \
     --resource "$FOLLOWUPBOSS_HOSTED_RESOURCE_SERVER_URL"
   uv run python scripts/migrate_hosted_oauth_resource.py expand \
     --resource "$FOLLOWUPBOSS_HOSTED_RESOURCE_SERVER_URL" --apply
   ```

2. Run read-only status. Record the `unbound_rows` values. If any `foreign_resource_rows` value is
   nonzero, stop; the database contains more than the one asserted audience and the script will
   not overwrite it.

   ```bash
   uv run python scripts/migrate_hosted_oauth_resource.py status \
     --resource "$FOLLOWUPBOSS_HOSTED_RESOURCE_SERVER_URL"
   ```

3. Backfill the reviewed counts before the rolling deployment. The acknowledgement is an explicit
   assertion that every currently unbound token was issued only for this MCP resource. Substitute
   the two exact counts from the immediately preceding status output:

   ```bash
   uv run python scripts/migrate_hosted_oauth_resource.py backfill \
     --resource "$FOLLOWUPBOSS_HOSTED_RESOURCE_SERVER_URL" \
     --expect-access-unbound ACCESS_COUNT \
     --expect-refresh-unbound REFRESH_COUNT \
     --acknowledge-unbound-token-audience --apply
   ```

4. Roll out the resource-aware application. Old instances omit the new column and PostgreSQL applies
   the temporary canonical default; new instances write the same value explicitly. New instances
   can therefore accept tokens issued by either version. Do not finalize while an old writer remains,
   because finalization removes that compatibility default.

5. After confirming every old writer is retired, run status again. Both `unbound_rows` and
   `foreign_resource_rows` must be zero, and `has_canonical_default` should be `true` for both
   tables. If an unexpected NULL exists, investigate its writer and repeat the reviewed-count
   backfill before continuing.

6. Print the finalization plan, then remove the temporary defaults and add the `NOT NULL`
   constraints in one transaction. The explicit flag records the operator assertion that old
   writers are gone:

   ```bash
   uv run python scripts/migrate_hosted_oauth_resource.py finalize \
     --resource "$FOLLOWUPBOSS_HOSTED_RESOURCE_SERVER_URL"
   uv run python scripts/migrate_hosted_oauth_resource.py finalize \
     --resource "$FOLLOWUPBOSS_HOSTED_RESOURCE_SERVER_URL" \
     --old-writers-retired --apply
   uv run python scripts/migrate_hosted_oauth_resource.py status \
     --resource "$FOLLOWUPBOSS_HOSTED_RESOURCE_SERVER_URL"
   ```

If the unbound tokens cannot all be attributed to the one explicit resource, do not acknowledge or
backfill them. Investigate and revoke or reissue those tokens through the normal credential
procedure instead.

Rollback is deliberately non-destructive. Before finalization, the old application can be rolled
back without a database change because the nullable columns retain their canonical defaults. After
finalization, first run the following command to restore those defaults and drop the `NOT NULL`
constraints in one transaction, then roll the application back. The columns and every resource
value remain intact for a later retry:

```bash
uv run python scripts/migrate_hosted_oauth_resource.py rollback-finalize \
  --resource "$FOLLOWUPBOSS_HOSTED_RESOURCE_SERVER_URL"
uv run python scripts/migrate_hosted_oauth_resource.py rollback-finalize \
  --resource "$FOLLOWUPBOSS_HOSTED_RESOURCE_SERVER_URL" --apply
```

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
- `SENTRY_DSN`
- `SENTRY_ENVIRONMENT`
- `SENTRY_RELEASE`
- `SENTRY_SAMPLE_RATE`
- `SENTRY_TRACES_SAMPLE_RATE`
- `SENTRY_PROFILES_SAMPLE_RATE`
- `SENTRY_ENABLE_LOGS`
- `SENTRY_DEBUG`

These values remain global defaults for the hosted deployment. They are safe to share across
tenants because they do not carry customer-specific Follow Up Boss credentials. `SENTRY_DSN`
identifies the Sentry project and enables Sentry only when set; the runtime sanitizer still prevents
Follow Up Boss secrets, authorization headers, tenant secret references, and customer payloads from
being submitted.

### Reference Hosted Wrapper Settings

The local `followupboss-mcp` CLI remains intentionally single-tenant. For the shared production
deployment, use `followupboss-mcp-hosted` or import
`create_reference_hosted_server(...)` directly. The following environment variable names are the
reference contract for that hosted wrapper:

| Variable | Purpose |
| --- | --- |
| `FOLLOWUPBOSS_HOSTED_ISSUER_URL` | Stable issuer URL exposed in `HostedAuthSettings`. For opaque tokens, point this at the hosted control-plane or customer portal base URL. |
| `FOLLOWUPBOSS_HOSTED_RESOURCE_SERVER_URL` | External HTTPS URL for the shared MCP endpoint, such as `https://mcp.example.com/mcp`. |
| `FOLLOWUPBOSS_DEPLOYMENT_ENVIRONMENT` | Hosted deployment label. The shared hosted wrapper accepts only `production`; omit the variable to use the production default. |
| `FOLLOWUPBOSS_HOSTED_REQUIRED_SCOPES` | Comma-separated scope list. The reference value is `followupboss:mcp`. |
| `FOLLOWUPBOSS_TENANT_DATABASE_URL` | PostgreSQL connection string for tenant and hosted-token metadata. |
| `FOLLOWUPBOSS_TENANT_SECRET_PREFIX` | AWS Secrets Manager path prefix, such as `followupboss/prod/tenants/`. |
| `FOLLOWUPBOSS_TENANT_SECRET_REGION` | AWS region used for the tenant secret store. |
| `FOLLOWUPBOSS_REDIS_URL` | Redis connection string for hosted rate limiting. |
| `FOLLOWUPBOSS_RATE_LIMIT_REQUESTS_PER_WINDOW` | Hosted request budget per window. Start at `300`. |
| `FOLLOWUPBOSS_RATE_LIMIT_WINDOW_SECONDS` | Hosted rate-limit window length. Start at `60`. |
| `FOLLOWUPBOSS_RATE_LIMIT_INCLUDE_CLIENT_IP` | `true` only when proxy trust is fully defined and sanitized. Default `false`. |
| `FOLLOWUPBOSS_HOSTED_OAUTH_ENABLED` | Set `true` to expose MCP OAuth authorization-server routes for Cursor and other remote MCP clients. |
| `FOLLOWUPBOSS_FUB_OAUTH_CLIENT_ID` | Follow Up Boss OAuth client id for delegated user consent. |
| `FOLLOWUPBOSS_FUB_OAUTH_CLIENT_SECRET` | Follow Up Boss OAuth client secret, loaded from Secrets Manager in ECS. |
| `FOLLOWUPBOSS_FUB_OAUTH_CALLBACK_URL` | Public callback URL registered with Follow Up Boss, such as `https://mcp.example.com/oauth/follow-up-boss/callback`. It must match the hosted OAuth callback route derived from `FOLLOWUPBOSS_HOSTED_ISSUER_URL`; startup fails fast when those values disagree. |
| `FOLLOWUPBOSS_FUB_OAUTH_SYSTEM_NAME` | Registered Follow Up Boss system name stored on OAuth-created tenant credentials. |
| `FOLLOWUPBOSS_FUB_OAUTH_SYSTEM_KEY` | Registered Follow Up Boss system key stored with OAuth-created tenant secrets. |

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

SENTRY_DSN=https://public@example.ingest.sentry.io/project-id
SENTRY_ENVIRONMENT=production
SENTRY_RELEASE=followupboss-mcp@0.1.0+replace-with-git-sha
SENTRY_SAMPLE_RATE=1.0
SENTRY_TRACES_SAMPLE_RATE=
SENTRY_PROFILES_SAMPLE_RATE=
SENTRY_ENABLE_LOGS=false
SENTRY_DEBUG=false

FOLLOWUPBOSS_HOSTED_ISSUER_URL=https://portal.example.com
FOLLOWUPBOSS_HOSTED_RESOURCE_SERVER_URL=https://mcp.example.com/mcp
FOLLOWUPBOSS_DEPLOYMENT_ENVIRONMENT=production
FOLLOWUPBOSS_HOSTED_REQUIRED_SCOPES=followupboss:mcp
FOLLOWUPBOSS_TENANT_DATABASE_URL=postgresql://app:***@db.example.com:5432/followupboss_mcp
FOLLOWUPBOSS_TENANT_SECRET_PREFIX=followupboss/prod/tenants/
FOLLOWUPBOSS_TENANT_SECRET_REGION=us-east-1
FOLLOWUPBOSS_REDIS_URL=redis://cache.example.com:6379/0
FOLLOWUPBOSS_RATE_LIMIT_REQUESTS_PER_WINDOW=300
FOLLOWUPBOSS_RATE_LIMIT_WINDOW_SECONDS=60
FOLLOWUPBOSS_RATE_LIMIT_INCLUDE_CLIENT_IP=false

FOLLOWUPBOSS_HOSTED_OAUTH_ENABLED=true
FOLLOWUPBOSS_FUB_OAUTH_CLIENT_ID=replace-with-fub-client-id
FOLLOWUPBOSS_FUB_OAUTH_CLIENT_SECRET=replace-with-secret-manager-value
FOLLOWUPBOSS_FUB_OAUTH_CALLBACK_URL=https://mcp.example.com/oauth/follow-up-boss/callback
FOLLOWUPBOSS_FUB_OAUTH_SYSTEM_NAME=The-Perry-Group
FOLLOWUPBOSS_FUB_OAUTH_SYSTEM_KEY=replace-with-secret-manager-value
```

### Reference Entrypoint

The repository's hosted reference entrypoint is:

```bash
uv run followupboss-mcp-hosted --host 0.0.0.0 --port 8000 --path /mcp
```

Equivalent module form:

```bash
uv run python -m followupboss_mcp.hosted_reference --host 0.0.0.0 --port 8000 --path /mcp
```

### Repository Deployment Assets

The repository now includes a minimal containerized deployment bundle for ECS/Fargate:

- `Dockerfile`
- `.dockerignore`
- `deploy/ecs/task-definition.template.json`
- `deploy/ecs/task-role-policy.template.json`
- `deploy/ecs/README.md`

Use those files to build the hosted image, wire the ECS task role, and register the hosted task
definition without falling back to the local single-tenant CLI.

### Hosted Wrapper Construction

The dedicated hosted wrapper should remain the production entrypoint. The repository reference
implementation now does that through `FollowUpBossHostedDeploymentSettings` plus
`create_reference_hosted_server(...)`, which:

1. builds `HostedAuthSettings` from the hosted issuer, resource-server URL, and required scopes
2. resolves opaque bearer tokens with `PostgresHostedTokenVerifier`
3. resolves tenant metadata and Follow Up Boss secrets with `PostgresAwsTenantStore`
4. applies shared Redis-backed rate limiting through `RedisHostedRateLimitBackend`

The hosted `create_server()` path can now accept a dedicated
`FollowUpBossTenantRuntimeDefaults` object for the shared non-secret Follow Up Boss defaults. When
that object is omitted, the server falls back to the built-in `base_url`, timeout, and retry
defaults without reading process-wide tenant credential environment variables.

That keeps the local CLI explicitly single-tenant while letting the hosted wrapper decide whether
those non-secret defaults come from environment variables, another config source, or the repository
constants.

## Registered System Identification

Follow Up Boss also expects integrations to register a system and send the issued `X-System` and
`X-System-Key` headers on API requests. See the official identification guide:
[Registration and Identification](https://docs.followupboss.com/reference/identification).

In this repository, those headers map to the tenant runtime fields:

- `system_name` -> `X-System`
- `system_key` -> `X-System-Key`

Local single-tenant development can provide them through any of these supported environment
variables:

- `FOLLOWUPBOSS_SYSTEM_NAME`
- `FOLLOWUPBOSS_SYSTEM_KEY`
- `FOLLOWUPBOSS_X_SYSTEM`
- `FOLLOWUPBOSS_X_SYSTEM_KEY`
- legacy `FOLLOW_UP_BOSS_SYSTEM_NAME`
- legacy `FOLLOW_UP_BOSS_SYSTEM_KEY`
- legacy `FOLLOW_UP_BOSS_X_SYSTEM`
- legacy `FOLLOW_UP_BOSS_X_SYSTEM_KEY`

Hosted deployments should not place those values in shared bootstrap environment variables. The
current hosted runtime resolves `system_name` and `system_key` through `TenantStore`, which means
operators should store the registered-system identification with the tenant credential payload when
that tenant must use registered-system-dependent Follow Up Boss endpoints such as attachment or
webhook flows.

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

## Cursor OAuth Login Flow

When `FOLLOWUPBOSS_HOSTED_OAUTH_ENABLED=true`, the hosted deployment also acts as the OAuth
authorization server advertised by MCPServer protected-resource metadata:

1. Cursor discovers `/.well-known/oauth-authorization-server`.
2. Cursor dynamically registers a public MCP client at `/oauth/register`.
3. Cursor starts `/oauth/authorize` with PKCE.
4. The hosted server redirects the browser to Follow Up Boss OAuth consent.
5. The hosted callback exchanges the Follow Up Boss `auth_code`, calls `/identity`, provisions or
   updates the tenant metadata row, and stores raw Follow Up Boss OAuth tokens only in AWS Secrets
   Manager.
6. The hosted token endpoint issues opaque MCP access and refresh tokens. Only token hashes are
   persisted in PostgreSQL.

The bearer token used against `/mcp` is still an MCP-scoped hosted token, not the raw Follow Up
Boss access token. This keeps revocation, tenant binding, rate limiting, and MCP scopes under the
hosted deployment's control.

### Follow Up Boss Redirect Preflight

The hosted server can report callback, token exchange, identity lookup, and tenant provisioning
failures to Sentry because those requests return to this process. A Follow Up Boss
`invalid_redirect_uri` page can happen earlier, immediately after step 4, while the browser is on
Follow Up Boss infrastructure. That page may never call our callback route, so it will not naturally
produce a server exception in this project.

Before enabling hosted OAuth for production, confirm that
`FOLLOWUPBOSS_FUB_OAUTH_CALLBACK_URL` exactly matches the redirect URI registered on the Follow Up
Boss OAuth application, including scheme, host, path, and trailing slash behavior. Then run one
browser login smoke from Cursor and confirm the browser reaches
`/oauth/follow-up-boss/callback` rather than stopping on a Follow Up Boss `invalid_redirect_uri`
screen.

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

## Production Validation Prerequisites

Before rollout, prepare two real hosted test tenants on the same shared deployment:

- `tenant-a`: one real Follow Up Boss sandbox or disposable account
- `tenant-b`: a different real Follow Up Boss sandbox or disposable account

Create one unique fixture person in each account so tenant isolation can be checked safely:

- `TENANT_A_FIXTURE_EMAIL`, only present in tenant A
- `TENANT_B_FIXTURE_EMAIL`, only present in tenant B

Export:

```bash
export PRODUCTION_MCP_URL="https://fub.theperry.group/mcp"
export TENANT_A_TOKEN="replace-with-real-hosted-token"
export TENANT_B_TOKEN="replace-with-real-hosted-token"
export TENANT_A_FIXTURE_EMAIL="mcp-tenant-a@example.com"
export TENANT_B_FIXTURE_EMAIL="mcp-tenant-b@example.com"
```

## Production Validation Commands

### 1. Invalid Token Fails Closed

```bash
TOKEN="definitely-invalid" uv run python - <<'PY'
import asyncio
import os

import httpx2 as httpx
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client


async def main() -> None:
    try:
        async with httpx.AsyncClient(
            headers={"Authorization": f"Bearer {os.environ['TOKEN']}"},
            timeout=30.0,
        ) as http_client:
            async with streamable_http_client(
                os.environ["PRODUCTION_MCP_URL"],
                http_client=http_client,
            ) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.discover()
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

import httpx2 as httpx
from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client


async def main() -> None:
    async with httpx.AsyncClient(
        headers={"Authorization": f"Bearer {os.environ['TOKEN']}"},
        timeout=30.0,
    ) as http_client:
        async with streamable_http_client(
            os.environ["PRODUCTION_MCP_URL"],
            http_client=http_client,
        ) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.discover()

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

                own_count = len(own_people.structured_content["people"])
                other_count = len(other_people.structured_content["people"])
                if own_count < 1:
                    raise SystemExit("expected at least one own-tenant fixture result")
                if other_count != 0:
                    raise SystemExit("expected zero cross-tenant fixture results")

                print(
                    json.dumps(
                        {
                            "label": os.environ["LABEL"],
                            "identity": identity.structured_content,
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

Both commands must use the same `PRODUCTION_MCP_URL`. That is the proof that one shared deployment is
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
- tenant A and tenant B both succeed against the same shared `PRODUCTION_MCP_URL`
- tenant A can read tenant A's fixture but not tenant B's fixture
- tenant B can read tenant B's fixture but not tenant A's fixture
- at least one resource read and one prompt render succeed under hosted auth
- logs show `hosted_auth_succeeded`, `tenant_resolution_succeeded`, and `upstream_credential_usage`
  for both tenants
- logs do not show `hosted_rate_limit_backend_failed`
- when `SENTRY_DSN` is configured, a sanitized production validation exception appears in the expected Sentry
  project, environment, and release without Follow Up Boss secrets or customer payloads
- hosted OAuth browser login reaches `/oauth/follow-up-boss/callback`; a Follow Up Boss
  `invalid_redirect_uri` page means the FUB OAuth app registration must be fixed before rollout
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
| Sentry sanitized exception smoke | | |
| Hosted OAuth callback redirect smoke | | |
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
