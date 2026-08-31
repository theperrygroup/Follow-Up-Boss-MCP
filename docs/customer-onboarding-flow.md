# Customer Onboarding Flow

## Scope

This document defines the operator-facing onboarding flow for a new hosted customer on the shared
multi-tenant Follow Up Boss MCP deployment.

It answers four questions:

1. How is a tenant record created?
2. How is that tenant's Follow Up Boss credential stored?
3. How is that credential validated before activation?
4. How are hosted bearer tokens issued, rotated, and revoked?

For the shared deployment shape itself, see
[hosted-deployment-guide.md](hosted-deployment-guide.md). For incident handling after a tenant is
active, see [security-incident-playbook.md](security-incident-playbook.md).

## Reference Storage Model

The reference onboarding flow uses three backing records:

| Backing record | Purpose | Runtime projection |
| --- | --- | --- |
| `tenants` row | Stable tenant identity and active credential binding | `TenantRecord` |
| `tenant_credentials` row plus AWS Secrets Manager payload | Follow Up Boss auth mode plus secret reference | `TenantCredentialRecord` |
| `hosted_access_tokens` row | Resource-bound bearer-token metadata and revocation state | `HostedVerifiedIdentity` |
| `hosted_oauth_refresh_tokens` row | Resource-bound refresh metadata and rotation state | `HostedOAuthRefreshToken` |

Reference fields:

### `tenants`

- `tenant_id`
- `tenant_slug`
- `display_name`
- `credential_id`
- `status`

### `tenant_credentials`

- `credential_id`
- `tenant_id`
- `auth_mode`
- `system_name`
- `secret_ref`
- `status`

### `hosted_access_tokens`

- `token_id`
- `token_hash`
- `tenant_id`
- `subject`
- `client_id`
- `scopes`
- `resource`
- `credential_id`
- `expires_at`
- `revoked_at`

### `hosted_oauth_refresh_tokens`

- `token_hash`
- `tenant_id`
- `subject`
- `client_id`
- `scopes`
- `resource`
- `credential_id`
- `expires_at`
- `revoked_at`

The raw Follow Up Boss API key, OAuth access token, and optional `system_key` should live only in
AWS Secrets Manager. The database should store only the secret reference plus non-secret metadata.

## Required Operator Inputs

Before creating a tenant, collect:

- customer display name
- desired `tenant_slug`
- one stable internal `tenant_id`
- Follow Up Boss auth mode: `api_key` or `oauth`
- the raw Follow Up Boss API key or OAuth access token
- the registered system name and key when the tenant must use endpoints that require `X-System`
  and `X-System-Key`
- optional `system_name`
- optional `system_key`
- the client integration identifier to place in hosted tokens, such as `customer-portal` or
  `zapier-prod`
- token owner or subject identifier, such as a service account name or customer admin principal
- confirmation that the client targets the production protected resource exactly as
  `https://fub.theperry.group/mcp`

For the first hosted release, the data model and runtime remain dual-mode. The default operator
path should still prefer API key onboarding when the customer does not specifically need OAuth.
For registered-system-dependent calls, operators should first register the integration with Follow
Up Boss and capture the issued header values from the official flow described in
[Registration and Identification](https://docs.followupboss.com/reference/identification).

## Onboarding Sequence

### 1. Create The Tenant Disabled

Create the tenant row first, but keep it disabled until credential validation succeeds.

Reference row:

| Field | Example |
| --- | --- |
| `tenant_id` | `tenant-acme-prod` |
| `tenant_slug` | `acme` |
| `display_name` | `Acme Realty` |
| `credential_id` | `cred-2026-03-acme-primary` |
| `status` | `disabled` |

Why disabled first:

- it prevents accidental live traffic before Follow Up Boss auth is verified
- it lets operators create metadata and secret records idempotently
- it keeps the activation flip explicit and auditable

### 2. Store The Follow Up Boss Credential

Create the credential metadata row and the secret-store payload together.

Reference metadata row:

| Field | Example |
| --- | --- |
| `credential_id` | `cred-2026-03-acme-primary` |
| `tenant_id` | `tenant-acme-prod` |
| `auth_mode` | `api_key` |
| `system_name` | `Acme MCP` |
| `secret_ref` | `arn:aws:secretsmanager:us-east-1:123456789012:secret:followupboss/prod/tenants/tenant-acme-prod/cred-2026-03-acme-primary` |
| `status` | `active` |

Reference AWS Secrets Manager payload:

```json
{
  "api_key": "raw-follow-up-boss-api-key",
  "access_token": null,
  "system_key": "optional-registered-system-key"
}
```

Rules:

- store only the secret reference in PostgreSQL, never the raw Follow Up Boss secret
- store exactly one of `api_key` or `access_token`
- keep `credential_id` stable if the intent is a future in-place secret rotation
- grant secret-read access only to the app role and tightly scoped operator workflows
- if the tenant needs registered-system-dependent endpoints, persist the issued `X-System-Key` in
  the secret payload and persist the corresponding `system_name` in the credential metadata row

### 3. Validate The Follow Up Boss Credential Before Activation

Do not issue hosted bearer tokens until the Follow Up Boss credential has been validated.

The validation path should assemble the same runtime shape the hosted server will use:

1. resolve the tenant row
2. resolve the credential metadata row
3. fetch the raw secret payload from AWS Secrets Manager
4. build `TenantCredentialRecord`
5. project the credential into `FollowUpBossTenantSettings`
6. make one low-risk Follow Up Boss call

Reference validation call order:

- first choice: `followupboss_get_identity`
- optional second check when `system_name` and `system_key` are present: one safe webhook or
  registered-system-dependent check

Validation outcomes:

- success: keep the credential active and move to tenant activation
- failure: leave the tenant disabled, record the reason, and either delete the failed credential
  row or mark it unusable in the operator system

Recommended activation gate:

- `followupboss_get_identity` succeeds
- the returned account or user is the one the operator expects
- no raw credential values appear in logs

### 4. Activate The Tenant

After validation succeeds, flip:

- `tenants.status` from `disabled` to `active`

No hosted token should succeed for a disabled tenant. Keeping activation as a separate step makes
rollout, rollback, and customer-communication timing much simpler.

### 5. Issue Resource-Bound Hosted Tokens

The hosted OAuth server issues opaque bearer and refresh tokens for one protected resource:
`https://fub.theperry.group/mcp`. A controlled operator backend may seed an opaque access-token
row directly, but it must apply the same exact resource binding.

Token issuance flow:

1. require the authorization request to include
   `resource=https://fub.theperry.group/mcp`
2. carry that value through pending authorization and bind the authorization code to it
3. require the authorization-code token request to repeat the same exact resource
4. generate cryptographically random raw access and refresh tokens and return them only to the
   client
5. hash both tokens before storing their metadata in PostgreSQL
6. write the exact resource to both the access-token and refresh-token rows
7. on each MCP request, resolve the access-token hash only under that resource and project the row
   into `HostedVerifiedIdentity`

Reference token row:

| Field | Example |
| --- | --- |
| `token_id` | `tok-2026-03-acme-portal-01` |
| `token_hash` | `sha256:...` |
| `tenant_id` | `tenant-acme-prod` |
| `subject` | `acme-admin-1` |
| `client_id` | `customer-portal` |
| `scopes` | `["followupboss:mcp"]` |
| `resource` | `https://fub.theperry.group/mcp` |
| `credential_id` | `cred-2026-03-acme-primary` |
| `expires_at` | `1772505600` |
| `revoked_at` | `null` |

Reference refresh-token row:

| Field | Example |
| --- | --- |
| `token_hash` | `sha256:...` |
| `tenant_id` | `tenant-acme-prod` |
| `subject` | `acme-admin-1` |
| `client_id` | `customer-portal` |
| `scopes` | `["followupboss:mcp"]` |
| `resource` | `https://fub.theperry.group/mcp` |
| `credential_id` | `cred-2026-03-acme-primary` |
| `expires_at` | `1775097600` |
| `revoked_at` | `null` |

Reference rules:

- always store only a one-way hash of the token
- always bind the token to `tenant_id`
- always bind access and refresh tokens to exactly `https://fub.theperry.group/mcp`
- always bind the token to `credential_id` in the reference deployment so credential mismatches
  fail closed on the next request
- use `subject` for the stable human or service principal that owns the token
- use `client_id` for the calling application or environment
- reject a missing or different `resource` on authorization, authorization-code, or refresh-token
  requests with OAuth `invalid_target`
- require a refresh request to match the stored refresh-token resource; after all checks pass,
  revoke that refresh token and issue a new pair with the same resource

The short-lived Redis compatibility rule is intentionally narrower than the durable token rules.
During a rolling deployment, a legacy pending authorization or authorization-code payload that has
no resource can be bound only to the one configured canonical resource. An explicit different
resource is rejected. PostgreSQL access- and refresh-token rows with NULL or foreign resources are
never accepted by this rule.

### 6. Customer Validation After Token Delivery

Once the customer receives the hosted bearer token, validate the shared deployment with two safe
checks:

1. `followupboss_get_identity`
2. one low-risk list or search call such as `followupboss_search_people` with a known disposable
   fixture

The tenant should be considered fully onboarded only after both checks succeed through the shared
hosted MCP endpoint at `https://fub.theperry.group/mcp`. A missing-resource or wrong-resource token
must also be confirmed to fail before tenant resolution.

## Existing Token Row Transition

Existing PostgreSQL deployments must transition both token tables together:

1. Add nullable `resource` columns with a temporary constant default of
   `https://fub.theperry.group/mcp`. This binds writes from an old application instance that omits
   the new column.
2. Review status counts for both tables. Stop on any foreign-resource row.
3. Backfill NULL rows only after acknowledging the exact reviewed access- and refresh-token counts
   and confirming that every such token was issued only for this resource.
4. Deploy the resource-aware writer and verifier. New writes set `resource` explicitly and NULL or
   foreign-resource access tokens fail closed.
5. After all old writers are retired and both unbound and foreign counts are zero, drop the
   temporary defaults and enforce `NOT NULL` on both columns.

If an application rollback is required after finalization, restore the canonical defaults before
making the columns nullable. Do not delete the columns or erase existing resource values.

## Follow Up Boss Credential Rotation

The preferred rotation path is an in-place secret update that keeps `credential_id` stable.

Sequence:

1. create the replacement Follow Up Boss API key or OAuth access token
2. update the AWS Secrets Manager payload referenced by the existing `credential_id`
3. re-run the low-risk validation check, preferably `followupboss_get_identity`
4. revoke the old Follow Up Boss credential only after the hosted validation succeeds

Why keep `credential_id` stable:

- existing hosted bearer tokens remain valid
- the next hosted request sees the new secret immediately
- there is no coordinated hosted token reissue required

If you must change `credential_id`, issue replacement hosted bearer tokens first. Once the old
tokens are revoked, requests bound to the old credential should fail closed with the existing
credential-binding-mismatch behavior.

## Hosted Bearer Token Rotation

Hosted bearer-token rotation is separate from Follow Up Boss credential rotation.

Reference rotation flow:

1. submit the current refresh token with the same `client_id` and exact canonical `resource`
2. let the token endpoint validate expiry, revocation, client, and stored resource binding
3. after validation, let the server revoke the presented refresh token and mint a replacement
   access/refresh pair bound to the same resource
4. validate the new access token against the shared deployment
5. confirm the rotated refresh token can no longer be reused

For a manual operator handoff instead, mint a second access token with the same canonical resource,
validate it, then revoke the old token.

Recommended overlap rule:

- allow brief overlap only for the exact handoff window
- do not keep multiple long-lived active tokens unless the customer truly needs separate clients

## Token Revocation And Tenant Disable

Use the smallest containment action that solves the incident:

- revoke one hosted bearer token when a single client token is exposed
- rotate the Follow Up Boss credential when the upstream tenant secret is exposed
- disable the tenant when the customer should be cut off immediately

Expected next-request behavior:

- revoked hosted token: `invalid_token`
- access token with a missing or different resource: `invalid_token` before tenant resolution
- disabled tenant: `invalid_token`
- revoked or missing Follow Up Boss credential: `invalid_token`
- mismatched `credential_id`: `invalid_token`

Expected OAuth grant behavior:

- missing or different authorization resource: `invalid_target`
- missing or different authorization-code token resource: `invalid_target`
- missing, different, or stored-mismatched refresh-token resource: `invalid_target`

## Audit Requirements

Every onboarding, activation, and rotation workflow should leave enough evidence to correlate with
the runtime audit events already emitted by the server:

- `hosted_auth_succeeded`
- `hosted_auth_failed`
- `tenant_resolution_succeeded`
- `tenant_resolution_failed`
- `upstream_credential_usage`
- `hosted_rate_limit_exceeded`
- `hosted_rate_limit_backend_failed`

Operator-side onboarding records should also capture:

- who created the tenant
- when the credential was validated
- which `credential_id` is active
- which `token_id` values were issued, rotated, or revoked

## Minimal Onboarding Checklist

Use this checklist for each new hosted tenant:

- create tenant row with `status=disabled`
- create credential row plus AWS Secrets Manager payload
- validate the Follow Up Boss credential with `followupboss_get_identity`
- flip the tenant to `status=active`
- mint one hosted bearer token bound to the active `credential_id`
- validate the token against the shared deployment
- record the tenant, credential, and token identifiers in the operator system

## Local And Non-Production Fallback

For local development and focused tests only:

- `stdio` remains environment-backed through `FollowUpBossSettings`
- hosted-style local tests can seed `DevelopmentTenantStore`
- hosted-style local token tests can seed `DevelopmentHostedTokenVerifier`

Those fallbacks are acceptable only for non-production use and must never contain real production
tenant secrets.
