# Security

## Authentication Modes

The repository supports the two outbound authentication modes documented by Follow Up Boss:

- API key auth using HTTP Basic auth with the API key as the username and an empty password
- OAuth using a Bearer token

`FOLLOWUPBOSS_AUTH_MODE` selects the active outbound mode. API key auth is the default local
single-tenant path.

Hosted multi-tenant `streamable-http` deployments add a separate inbound bearer-token layer.
Inbound hosted tokens are validated by a deployment-specific `HostedIdentityVerifier` and
normalized into one canonical `HostedVerifiedIdentity` payload with these non-secret claims:

- `tenant_id`
- `subject`
- `client_id`
- optional `scopes`
- optional `expires_at`
- optional `token_id`
- optional `credential_id`

The hosted auth layer always resolves `tenant_id` through `TenantStore` before any Follow Up Boss
client is created. When a token includes `credential_id`, the auth layer also enforces that the
stored tenant credential still matches that binding.

## Secret Handling

- local single-tenant development can still load outbound credentials from environment variables
  through `FollowUpBossSettings`
- hosted multi-tenant mode resolves `TenantRecord` and `TenantCredentialRecord` material through
  `TenantStore` on demand
- `api_key`, `access_token`, `system_key`, and bearer-token-like fields are stored as `SecretStr`
  or redacted before logging
- auth strategy `repr()` output and `HostedAccessToken` string representations redact secrets
- `Authorization` and `X-System-Key` are redacted from logs
- the repository does not commit secret values or sample live credentials
- production hosted deployments should keep tenant credentials encrypted at rest or behind a
  managed secret store; `DevelopmentTenantStore` is only for local development and tests

Hosted tenant credentials are re-resolved for every authenticated call. The hosted runtime factory
builds a fresh request-scoped Follow Up Boss client from the currently stored credential and closes
that client after the call, so hosted mode does not reuse one startup-time client or one cached
secret across tenants.

## Hosted Token Revocation And Credential Rotation

### Bearer Token Revocation

Hosted bearer tokens are revoked at the system backing `HostedIdentityVerifier`, not in the Follow
Up Boss client layer. The source of truth can therefore be a signed-token issuer, an opaque-token
database, or another verifier backend, as long as revoked or unknown tokens stop resolving to a
verified identity.

`HostedTenantTokenVerifier` runs on every hosted `streamable-http` request. Once the verifier
backend stops accepting a token, the next request using that token fails closed with:

```json
{"error":"invalid_token","error_description":"Authentication required"}
```

Operational expectations:

- repository code does not cache successful bearer-token decisions across requests
- revocation latency is therefore one more hosted HTTP request plus any cache or replication delay
  in the external verifier backend
- a request that already passed auth is not retroactively cancelled, but every later request must
  authenticate again
- tokens whose `expires_at` is in the past fail the same `invalid_token` path

### No-Downtime Follow Up Boss Credential Rotation

Hosted Follow Up Boss credentials are re-resolved on every authenticated call. `TenantRuntimeFactory`
loads the current credential from `TenantStore`, projects it into tenant settings, and builds a
fresh request-scoped `FollowUpBossAsyncClient` for that call only.

To rotate a compromised tenant Follow Up Boss API key or OAuth token without downtime:

1. Create a replacement Follow Up Boss credential.
2. Update the stored secret payload for the tenant in the tenant store or secret manager.
3. Keep the tenant's stable `credential_id` binding unchanged during the first cutover when
   existing hosted bearer tokens are expected to keep working.
4. Verify the replacement secret through the hosted MCP surface with a low-risk call such as
   `followupboss_get_identity`.
5. Revoke the old Follow Up Boss credential only after the hosted verification succeeds.

If hosted bearer tokens are bound to a `credential_id` claim, changing `credential_id` before
reissuing those tokens will intentionally fail closed with `tenant_resolution_failed` and
`reason=credential_binding_mismatch`. Use an in-place secret update or coordinate token reissuance
before switching the binding.

## Fail-Closed Expectations

| Condition | Operator-visible behavior | Primary audit signal |
| --- | --- | --- |
| Revoked, unknown, or expired bearer token | `401` with `invalid_token` / `Authentication required` | `hosted_auth_failed` with `reason=token_verification_failed` |
| Disabled tenant | `401` with `invalid_token` before any Follow Up Boss client is created | `tenant_resolution_failed` with `reason=tenant_disabled` |
| Revoked or missing tenant credential | `401` with `invalid_token` before any Follow Up Boss client is created | `tenant_resolution_failed` with `reason=credential_revoked` or `reason=credential_not_found` |
| Tenant or secret store outage during auth | `401` with `invalid_token` and no backend error details | `tenant_resolution_failed` with `reason=tenant_store_unavailable` or `reason=tenant_secret_store_unavailable` |
| Credential binding mismatch | `401` with `invalid_token` | `tenant_resolution_failed` with `reason=credential_binding_mismatch` |
| Hosted rate-limit backend outage in closed mode | `503` with `temporarily_unavailable` plus `Retry-After` | `hosted_rate_limit_backend_failed` |

If tenant state changes after auth succeeds but before the tool, resource, or prompt runtime is
resolved, the request still fails closed with the MCP-safe message `Hosted tenant runtime is
unavailable.` rather than using stale tenant credentials.

## Audit Events And On-Call Signals

- `hosted_auth_succeeded` means the bearer token verified and includes non-secret identity fields
  such as `tenant_id`, `subject`, `client_id`, and optional `token_id` / `credential_id`.
- `hosted_auth_failed` is the first place to look after a revoke. Repeated hits usually mean stale
  clients are still presenting an old bearer token.
- `tenant_resolution_succeeded` confirms the active tenant and current credential mapping were
  resolved successfully.
- `tenant_resolution_failed` is the main incident triage signal. Watch the `reason` field for
  `tenant_disabled`, `credential_revoked`, `credential_not_found`, `tenant_not_found`,
  `tenant_store_unavailable`, `tenant_secret_store_unavailable`, and `credential_binding_mismatch`.
- `upstream_credential_usage` is emitted each time hosted runtime wiring creates a Follow Up Boss
  client. This should stop for a disabled tenant after in-flight requests drain.
- `hosted_rate_limit_exceeded` and `hosted_rate_limit_backend_failed` are secondary signals that
  help distinguish tenant auth incidents from hosted abuse-control problems.

On-call symptoms to watch during revocation or rotation:

- repeated `hosted_auth_failed` after a planned revoke usually means stale clients are still
  sending the old bearer token
- repeated `tenant_resolution_failed` with `credential_binding_mismatch` usually means
  `credential_id` changed before hosted tokens were reissued or refreshed
- continued `upstream_credential_usage` for an intentionally disabled tenant after the containment
  window suggests traffic is still reaching a valid tenant configuration and needs investigation
- upstream Follow Up Boss auth or permission failures after a rotation usually mean the new
  credential was stored incorrectly or does not have the required account permissions

## Logging And Stdio Safety

- stdout is reserved for MCP transport traffic in stdio mode
- operational logging uses Python logging instead of mixing diagnostics into the protocol stream
- debug logging is safe for transport inspection because sensitive headers are redacted and
  request/query payloads are summarized by key instead of emitting raw values
- dynamic API paths are omitted from request, response, and retry logs so resource identifiers do
  not leak through operational diagnostics

## Request Hardening

- auth and system headers are injected centrally in the HTTP client
- caller-supplied `Authorization`, `X-System`, `X-System-Key`, and `Content-Type` overrides are
  rejected at the client boundary
- JSON requests set `Content-Type: application/json` when a body is present
- JSON response parsing and HTTP error mapping are centralized
- retries are limited and deterministic rather than unbounded
- redirects are disabled in the Follow Up Boss HTTP client by default

## Rate Limits And Server Retries

- `429` responses honor `Retry-After`
- retryable `5xx` responses use truncated exponential backoff with jitter
- error payloads are surfaced cleanly without leaking credentials

## Webhook Verification

Webhook verification follows the official Follow Up Boss guidance:

- use the exact raw request body bytes
- base64-encode the raw body
- compute HMAC-SHA256 using `X-System-Key`
- compare against the `FUB-Signature` header

The repository exposes this logic in `src/followupboss_mcp/webhooks.py` so it can be reused in
ASGI, WSGI, serverless, or queue-driven receivers.

## CI Security Automation

- CI runs a dependency audit against exported locked third-party requirements
- CI runs secret scanning to catch committed credentials before release
- the current lockfile now passes the dependency audit without a temporary vulnerability exception

## Incident Response Guidance

Hosted disable, revoke, rotate, and recover procedures live in
[security-incident-playbook.md](security-incident-playbook.md).

## Webhook Receiver Guidance

- acknowledge quickly with a `2xx` response
- perform longer processing after the acknowledgment
- verify the signature before trusting the payload
- parse the payload only after verification succeeds

The helper `build_fast_ack()` exists specifically to make the fast-ack pattern explicit and
reusable.

## Permissions Caveat

Follow Up Boss API access is limited by the permissions of the user or account behind the API key
or access token. A `403` usually means:

- the credential is valid
- the authenticated principal does not have access to the requested resource or admin action

Webhook administration is especially sensitive to account permissions and registered system
metadata.

## Custom Field Safety

Outgoing custom field writes must use the Follow Up Boss field `name`, not the label displayed in
the UI. The repository validates this so callers do not silently send labels like `Birthday` when
Follow Up Boss expects a field key like `customBirthday`.
