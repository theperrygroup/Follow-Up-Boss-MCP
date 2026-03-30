# Security Incident Playbook

## Purpose

This playbook defines the repository-local response for the most likely credential and integration incidents in `followupboss-mcp`.

Use it when any of the following may have happened:

- `FOLLOWUPBOSS_API_KEY` or `FOLLOWUPBOSS_ACCESS_TOKEN` was exposed
- `FOLLOWUPBOSS_SYSTEM_KEY` may have leaked
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
