# Security

## Authentication Modes

The repository supports the two authentication modes documented by Follow Up Boss:

- API key auth using HTTP Basic auth with the API key as the username and an empty password
- OAuth using a Bearer token

`FOLLOWUPBOSS_AUTH_MODE` selects the active mode. API key auth is the default path.

## Secret Handling

- credentials are loaded from environment variables through `FollowUpBossSettings`
- `api_key`, `access_token`, and `system_key` are stored as `SecretStr`
- auth strategy `repr()` output is redacted
- `Authorization` and `X-System-Key` are redacted from logs
- the repository does not commit secret values or sample live credentials

## Logging And Stdio Safety

- stdout is reserved for MCP transport traffic in stdio mode
- operational logging uses Python logging instead of mixing diagnostics into the protocol stream
- debug logging is safe for transport inspection because sensitive headers are redacted before they are emitted

## Request Hardening

- auth and system headers are injected centrally in the HTTP client
- caller-supplied `Authorization`, `X-System`, `X-System-Key`, and `Content-Type` overrides are rejected at the client boundary
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

The repository exposes this logic in `src/followupboss_mcp/webhooks.py` so it can be reused in ASGI, WSGI, serverless, or queue-driven receivers.

## CI Security Automation

- CI runs a dependency audit against exported locked third-party requirements
- CI runs secret scanning to catch committed credentials before release
- the dependency audit temporarily ignores `CVE-2026-4539` because the current `pygments` advisory does not yet list a fixed release

## Incident Response Guidance

Repository-local credential rotation and remediation steps live in [security-incident-playbook.md](security-incident-playbook.md).

## Webhook Receiver Guidance

- acknowledge quickly with a `2xx` response
- perform longer processing after the acknowledgment
- verify the signature before trusting the payload
- parse the payload only after verification succeeds

The helper `build_fast_ack()` exists specifically to make the fast-ack pattern explicit and reusable.

## Permissions Caveat

Follow Up Boss API access is limited by the permissions of the user or account behind the API key or access token. A `403` usually means:

- the credential is valid
- the authenticated principal does not have access to the requested resource or admin action

Webhook administration is especially sensitive to account permissions and registered system metadata.

## Custom Field Safety

Outgoing custom field writes must use the Follow Up Boss field `name`, not the label displayed in the UI. The repository validates this so callers do not silently send labels like `Birthday` when Follow Up Boss expects a field key like `customBirthday`.
