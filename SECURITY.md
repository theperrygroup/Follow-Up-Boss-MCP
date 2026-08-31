# Security Policy

## Reporting a vulnerability or compromised connection

Do not report vulnerabilities, access tokens, credentials, or customer data in a public GitHub
issue. Email `john@theperry.group` with a concise description and a safe way to reproduce the
problem. Do not attach production CRM records or raw secrets.

For a lost or compromised client that used `https://fub.theperry.group/mcp`:

1. Remove or disconnect the connector in the AI client to stop its normal use.
2. Revoke the integration's Follow Up Boss authorization from the affected account.
3. Email `john@theperry.group` to request revocation of the hosted MCP access and refresh tokens.

Removing a connector from an AI client does not, by itself, prove that already-issued hosted tokens
or the upstream Follow Up Boss authorization were revoked.

## Response expectations

The Perry Group will acknowledge a security report, determine the affected surface, and coordinate
containment and remediation privately. Please allow a reasonable period for a fix before public
disclosure.

For implementation details about authentication, tenant isolation, secret handling, logging, and
operator response, see [docs/security.md](docs/security.md) and the
[security incident playbook](docs/security-incident-playbook.md).
