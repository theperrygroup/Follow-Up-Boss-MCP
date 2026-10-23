# Authentication release contracts

Run `make auth-test` for the deterministic auth suite. It requires no live account,
credentials, browser sign-in, or external network access. These tests are also part
of the default test and coverage runs.

The lifecycle contract starts with no access tokens or tenant records. It drives
discovery, client registration or CIMD, PKCE authorization, the provider callback,
token exchange, and an authenticated MCP identity call. The same contract runs for
ChatGPT, Codex loopback callbacks, and registered clients, using both modern and
legacy MCP. It reconstructs the application with retained state, then checks expiry,
refresh, one-time code/refresh-token replay, and tenant/credential revocation.

Only external HTTP and persistence are replaced with deterministic test adapters.
The OAuth routes, metadata parser, upstream HTTP client, tenant authorization
middleware, and MCP transport run normally. The in-memory serialized persistence
does not claim to test PostgreSQL, Redis, or AWS availability.

`make build-smoke` installs the built wheel with its test dependencies into a fresh
environment and runs the lifecycle contract outside the checkout. It clears
`PYTHONPATH` and inherited pytest settings, prevents pytest from adding checkout import
paths, and disables external Sentry configuration. This catches packaging and supported-dependency failures that
source-only tests miss.

`make auth-client-check` separately fetches current public ChatGPT and Codex client
metadata through the production CIMD parser. CI requires it before building release
artifacts; production deployment requires it before replacing the service. It fails
on unreachable, malformed, incompatible, or unregistered client metadata. It never
falls back to an older fixture after a live check fails.

After the service stabilizes, `scripts/verify_public_oauth.py` verifies the bearer
challenge and discovery contract and starts authorization for both real client IDs.
Each request must redirect to the expected Follow Up Boss authorization endpoint.
The probe does not follow the redirect, authenticate a user, or issue a bearer token.
It creates one expiring pending authorization record per client and reports no OAuth
state, provider credentials, or redirect query values.

Public checks and synthetic provider callbacks are not proof of completed live user
authentication. Human MFA and a read-only identity check remain separate live
acceptance evidence; a metadata flag or successful redirect must never substitute
for them.
