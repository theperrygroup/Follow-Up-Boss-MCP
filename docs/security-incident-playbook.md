# Security Incident Playbook

## Purpose

This playbook defines the repository-local and hosted-operations response for the most likely
credential and integration incidents in `followupboss-mcp`.

Use it when any of the following may have happened:

- `FOLLOWUPBOSS_API_KEY` or `FOLLOWUPBOSS_ACCESS_TOKEN` was exposed
- `FOLLOWUPBOSS_SYSTEM_KEY` may have leaked
- a hosted bearer token may have leaked or needs emergency revocation
- one hosted tenant must be disabled, remediated, and safely re-enabled
- CI or git history detected a committed secret
- webhook deliveries are failing after a suspected key rotation or compromise

## Roles

- Incident lead: the person coordinating containment and validation
- Credential owner: the person with access to the Follow Up Boss integration or account settings
- Reviewer: a second person who confirms remediation and log/document cleanup

## Immediate Containment

1. Stop using the suspected secret in local shells, CI, and running services.
2. Identify where the secret was exposed:
   - terminal history
   - `.env` files
   - CI logs
   - git commits or pull requests
   - pasted customer payloads or screenshots
3. Revoke or rotate the affected Follow Up Boss credential as quickly as possible.
4. If the exposure involved `X-System-Key`, assume webhook signature trust is broken until receivers are updated.

## Hosted Tenant Emergency Runbook

Use this path for hosted `streamable-http` deployments when a tenant bearer token, tenant Follow Up
Boss credential, or both may be compromised.

### Fail-Closed Behavior To Expect

- disabling a tenant or revoking its stored credential blocks the next hosted request with `401`
  `invalid_token`
- revoking a hosted bearer token in the verifier backend blocks the next hosted request as soon as
  the verifier observes that change
- requests that already passed auth are not retroactively cancelled, but later requests must
  authenticate again
- if tenant state changes between auth and runtime creation, the call still fails closed with
  `Hosted tenant runtime is unavailable.`

### Exact Emergency Steps

1. Disable the tenant if you need immediate containment or the blast radius is unclear.
   - Set `TenantRecord.status` to `disabled` for the affected `tenant_id`.
   - Expect the next hosted request for that tenant to fail with `401` `invalid_token`.
   - Look for `tenant_resolution_failed` with `reason=tenant_disabled`.
2. Revoke the hosted bearer token or tokens.
   - Revoke or remove the token in the system backing `HostedIdentityVerifier`.
   - Revoke all active tokens for the affected tenant or client if the exposure scope is unclear.
   - Expect the next use of the old token to log `hosted_auth_failed` with
     `reason=token_verification_failed`.
3. Rotate the tenant Follow Up Boss credential.
   - Create a replacement Follow Up Boss API key or OAuth token.
   - Update the stored secret for the affected `TenantCredentialRecord`.
   - Keep the stable `credential_id` unchanged during the first cutover unless forced token
     reissuance is part of the response.
   - If webhook trust was also affected, rotate `system_key` and revalidate webhook signatures
     before recovery.
4. Verify containment before re-enabling traffic.
   - Confirm the old bearer token now returns `401` `invalid_token`.
   - Confirm the disabled tenant no longer reaches `upstream_credential_usage` apart from any
     in-flight request that started before containment.
   - Confirm the new Follow Up Boss credential is stored and available to the hosted runtime.
5. Verify recovery with a replacement access path.
   - If bearer tokens were revoked, issue a replacement hosted bearer token first.
   - Authenticate through the hosted endpoint and run a low-risk tool such as
     `followupboss_get_identity`.
   - Confirm `hosted_auth_succeeded`, `tenant_resolution_succeeded`, and `upstream_credential_usage`
     for the expected tenant.
   - Confirm the response points at the expected Follow Up Boss user and account.
6. Re-enable the tenant only after verification passes.
   - Set `TenantRecord.status` back to `active`.
   - Monitor the first few requests for `hosted_auth_failed`, `tenant_resolution_failed`, upstream
     Follow Up Boss auth failures, or unexpected rate-limit events.

### No-Downtime Tenant Credential Rotation

Use this path when the hosted bearer token is still trusted and only the tenant's upstream Follow
Up Boss credential needs rotation.

1. Create a replacement Follow Up Boss API key or OAuth token.
2. Update the stored secret in place for the current tenant credential record or secret reference.
3. Do not change `credential_id` unless coordinated hosted token reissuance is part of the plan.
4. Verify the new secret through the hosted MCP endpoint with `followupboss_get_identity`.
5. Confirm `hosted_auth_succeeded`, `tenant_resolution_succeeded`, and `upstream_credential_usage`
   for the expected tenant.
6. Revoke the old Follow Up Boss credential only after the hosted verification succeeds.
7. Keep watching for `credential_binding_mismatch`, upstream auth failures, or unexpected `403`
   responses after cutover.

### Hosted Audit Trail To Review

- `hosted_auth_failed`: expected after a token revoke; repeated hits usually mean stale callers are
  still retrying with the old token
- `tenant_resolution_failed`: check `reason` values such as `tenant_disabled`,
  `credential_revoked`, `credential_not_found`, `tenant_store_unavailable`,
  `tenant_secret_store_unavailable`, or `credential_binding_mismatch`
- `upstream_credential_usage`: should stop for a disabled tenant after in-flight requests drain,
  then resume only after recovery
- `hosted_rate_limit_backend_failed`: secondary signal that a recovery issue may be rate-limit
  infrastructure rather than tenant auth or credential state

## API Key Or OAuth Token Rotation

1. Create or obtain a replacement credential in Follow Up Boss.
2. Update local environment variables:
   - `FOLLOWUPBOSS_API_KEY` for API key mode
   - `FOLLOWUPBOSS_ACCESS_TOKEN` for OAuth mode
3. Update CI or deployment secrets before re-enabling automated runs.
4. Run:

   ```bash
   uv run python examples/identity_check.py
   uv run python -m followupboss_mcp.cli --help
   ```

5. Confirm the old credential no longer works, if it is safe to check.

## System Key Or Webhook Compromise

1. Generate a replacement `X-System-Key` in the Follow Up Boss integration settings.
2. Update all webhook receivers to use the new key before trusting incoming payloads again.
3. Recreate or verify webhook registrations if the integration metadata changed.
4. Validate the receiver behavior with a known-good signed payload or staging workflow.
5. Review recent webhook deliveries for unexpected failures or suspicious activity.

## Repository Secret Exposure

1. Remove the leaked value from tracked files immediately.
2. If the secret reached git history or a public PR, treat rotation as mandatory.
3. Re-run secret scanning locally or in CI to confirm the obvious leak is gone.
4. Avoid committing real credentials, real customer payloads, or screenshots that embed secrets.

## Validation After Remediation

Run the standard repository checks after containment:

```bash
uv export --format requirements.txt --all-groups --locked --no-editable --no-emit-project --output-file /tmp/followupboss-mcp-requirements.txt
uvx --from pip-audit pip-audit -r /tmp/followupboss-mcp-requirements.txt --strict --disable-pip --no-deps
uv run ruff format --check .
uv run ruff check .
uv run mypy src tests
uv run pytest
uv run coverage run --branch -m pytest
uv run coverage report --fail-under=100
uv run python -m followupboss_mcp.cli --help
```

## Post-Incident Review

Document the following before closing the incident:

- what leaked or was suspected
- when it happened
- where it was exposed
- what was rotated or revoked
- what follow-up prevention work is required

Common follow-up items:

- tighten secret storage or shell usage
- remove unnecessary debug output
- add or refine CI scanning rules
- improve developer guidance where the leak occurred
