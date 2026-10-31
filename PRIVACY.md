# Follow Up Boss MCP Privacy Policy

**Effective date: September 29, 2026**

The Perry Group operates the Follow Up Boss MCP service at
`https://fub.theperry.group/mcp` and publishes the associated Follow Up Boss
plugins for Codex and Claude. This policy explains how that integration handles
personal information. It covers the hosted service and our plugin packages;
independently operated, self-hosted copies have their own operators and policies.

This is an independent community integration, not an official Follow Up Boss,
OpenAI, or Anthropic product. For privacy questions or requests, contact
[john@theperry.group](mailto:john@theperry.group) with the subject
“Follow Up Boss MCP privacy request.”

## Information we process

- **Account and connection information.** When you connect, we process your
  Follow Up Boss account and user identifiers, account name, and identity details
  returned by Follow Up Boss, which can include your name, email, and role. We
  store connection, OAuth client, permission scope, and credential-reference
  metadata to associate each request with its authorized account.
- **Authorization information.** We store the Follow Up Boss access and refresh
  credentials needed to operate the connection in AWS Secrets Manager. Hosted
  MCP access and refresh tokens are stored as hashes, together with identifiers,
  scopes, expiry, and revocation information. The sign-in flow also temporarily
  processes redirect addresses, authorization state, and authorization codes.
  Authenticate through the connection flow; do not paste passwords or tokens
  into a conversation or support request.
- **Requested CRM information.** The tools you use determine what is processed.
  This can include leads' and contacts' names, email addresses, telephone numbers,
  postal addresses, property interests, tags, assignments, notes, communications,
  tasks, appointments, deal values, commissions, transaction dates, participants,
  attachments or attachment links, and custom fields. Tool arguments and Follow
  Up Boss responses pass through the hosted service to carry out your requests.
  Records can concern other people, so only connect accounts and request data
  you are authorized to use.
- **Operational information.** We and our hosting and monitoring providers
  process request times, routes, status codes, latency, errors, client/network
  information such as IP addresses, and account, user, OAuth client, token, or
  credential identifiers. These identifiers can be associated with a person or
  organization. Diagnostic data can contain limited context from a failed
  request despite our redaction controls.
- **Support correspondence.** If you contact us, we receive the contact details
  and information you choose to send. Avoid sending customer records or secrets
  unless we arrange an appropriate way to investigate a specific issue.

The MCP service receives tool requests and the content your client sends with
them. It does not independently retrieve your full ChatGPT, Codex, or Claude
conversation history. Installing a plugin alone does not authorize CRM access.

## How we use information

We use this information to authenticate and maintain your connection, retrieve
the CRM records you request, carry out authorized changes, return results to
your client, enforce account separation and rate limits, investigate failures or
abuse, and respond to support and privacy requests. A requested CRM change may
activate Follow Up Boss workflows or other integrations configured on your
account. Your account permissions and the client's tool-approval controls apply.

The hosted integration does not include advertising, data-sale, or model-training
functionality. The AI client you choose processes the tool results under its own
terms, privacy policy, and account settings.

## Who receives information

- **Follow Up Boss** receives the API requests needed for your CRM operations and
  stores records created or changed in your account.
- **Your chosen MCP/AI client**, such as OpenAI's ChatGPT or Codex, Anthropic's
  Claude, or another client you configure, receives tool responses. Review that
  provider's data controls before requesting CRM information.
- **Service providers** help operate the integration. AWS provides application
  hosting, credential storage, and service logging; Cloudflare provides network
  delivery and protection; Sentry receives error diagnostics. The hosted service
  also uses PostgreSQL for connection metadata and Redis for temporary OAuth
  state and rate-limit data. Providers process the information needed for their
  respective functions.
- **Authorized operators and support personnel** may access information needed
  to operate, secure, or support the service. We may also disclose information
  when required by law or necessary to address misuse or protect people's rights
  and security.

The application runs in the United States. Network, monitoring, client, and CRM
providers may process information in other locations under their own policies
and your agreements with them.

## Retention and deletion

Different records have different lifetimes. A token's validity period is not a
promise that its database record has been erased.

| Information | Retention in this integration |
| --- | --- |
| CRM tool arguments and results | Processed for the request; the service does not maintain a separate CRM-record archive. Diagnostic exceptions and copies in your client or Follow Up Boss have the retention described below. |
| Pending OAuth sign-in state | Expires after 10 minutes, or is consumed earlier during sign-in. |
| Single-use authorization codes | Expire after 5 minutes, or are consumed earlier when exchanged. |
| Temporary rate-limit counters | Expire at the end of their rate-limit window. |
| Hosted MCP tokens | Access tokens are valid for 1 hour and refresh tokens for up to 30 days unless revoked earlier. Refresh rotation revokes the previous refresh token. Expired or revoked metadata can remain in the database; there is no scheduled time-based purge of these rows. |
| Account, client-registration, and connection records; stored Follow Up Boss credentials | Retained while supporting the connection and until removed by the operator, including in response to a verified deletion request. Disconnecting a client or expiring a token does not automatically delete these records or secrets. |
| Application logs in AWS CloudWatch | Retained for 30 days under the current log-group setting. |
| Other diagnostics and network-security records | Sentry and Cloudflare records follow the applicable provider/project retention settings. This integration does not currently impose a separate fixed maximum or automatically erase those records when you disconnect. Contact us to request deletion of identifiable records we control. |
| Privacy and support correspondence | Retained to handle the request and related security, legal, or recordkeeping needs; there is no automatic deletion deadline. You may request deletion. |

Deletion from our service does not delete CRM records in Follow Up Boss or copies
of results, conversations, or exported files held by your AI client or other
recipients. Those copies are governed by the respective account controls and
provider policies. If a legal obligation or an active security investigation
requires us to retain information, we will explain the relevant restriction when
responding to your request where permitted.

## Your choices and requests

You can stop using the tools, disable or uninstall the plugin, and disconnect the
MCP connection in your client. To stop upstream account access, revoke the
integration's authorization in Follow Up Boss as well. Ask us to revoke hosted
MCP access and refresh tokens when you need operator assistance. An action
already authorized and in progress may finish before a revocation takes effect.

To request access, correction, or deletion of personal information we hold, or to
raise a privacy concern, email [john@theperry.group](mailto:john@theperry.group).
Identify the integration and the account involved without sending credentials.
We may need to verify your identity and authority over the account before acting.
We will explain what we can delete or correct and any applicable limits. If a
record is controlled by your employer or another Follow Up Boss account owner,
we may direct you to that administrator. Applicable law may provide additional
rights, including a right to complain to a privacy regulator.

## Security

We use HTTPS for the public connection, account-scoped authentication, a managed
credential store, and redaction controls for known secrets and sensitive payload
fields. Request-body capture and local-variable capture are disabled in the
application's Sentry configuration. These controls reduce exposure; they do not
mean that every diagnostic record is anonymous or that any service is risk-free.
Report a suspected exposure privately to the contact above.

## Changes to this policy

We will update the effective date when this policy changes and update the policy
link supplied with the plugin when publishing a new policy version. Review the
policy linked by your installed plugin or directory listing for the applicable
version. Material changes will be described in the policy or release information.
