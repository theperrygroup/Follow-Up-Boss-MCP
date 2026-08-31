<p align="center">
  <img
    src="https://raw.githubusercontent.com/theperrygroup/Follow-Up-Boss-MCP/main/src/followupboss_mcp/assets/follow-up-boss-logo.png"
    width="112"
    alt="Follow Up Boss MCP server logo"
  >
</p>

# Follow Up Boss MCP Server

Connect ChatGPT, Claude, Cursor, and other AI assistants to the Follow Up Boss real estate CRM
through the Model Context Protocol (MCP). Search leads, review activity, manage tasks and
appointments, work with deals, and run CRM workflows using natural language.

[![CI](https://github.com/theperrygroup/Follow-Up-Boss-MCP/actions/workflows/ci.yml/badge.svg)](https://github.com/theperrygroup/Follow-Up-Boss-MCP/actions/workflows/ci.yml)
[![Python 3.12+](https://img.shields.io/badge/Python-3.12%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/MCP-Streamable_HTTP-6f42c1)](https://modelcontextprotocol.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/theperrygroup/Follow-Up-Boss-MCP/blob/main/LICENSE)

## Connect with one URL

Most people only need the hosted MCP server. You do **not** need to clone this repository, install
Python, run a server, or paste a Follow Up Boss API key into your AI client.

**MCP server URL**

```text
https://fub.theperry.group/mcp
```

1. Open your AI client's apps, connectors, or MCP settings.
2. Choose **Add custom connector**, **Create app**, or **Add remote MCP server**.
3. Paste `https://fub.theperry.group/mcp` as the server URL.
4. If prompted, choose **Streamable HTTP** and **OAuth**.
5. Complete the browser sign-in and authorize access to Follow Up Boss.
6. Enable the new connector in a conversation and ask: **“Who am I in Follow Up Boss?”**

The client should return your Follow Up Boss identity. That confirms the connection and
authorization flow are working.

### Where to paste the URL

| Client | Setup path |
| --- | --- |
| **ChatGPT** | Enable developer mode, then go to **Settings → Apps → Create**, provide the MCP endpoint, choose OAuth, and scan the tools. Full MCP availability depends on your ChatGPT plan and workspace permissions. See [OpenAI's MCP app guide](https://help.openai.com/en/articles/12584461-developer-mode-and-full-mcp-connectors-in-chatgpt). |
| **Claude** | Go to **Customize → Connectors → + → Add custom connector**, then paste the URL and connect. Team and Enterprise workspaces require an owner to add the connector first. See [Anthropic's remote MCP guide](https://support.claude.com/en/articles/11175166-get-started-with-custom-connectors-using-remote-mcp). |
| **Cursor** | Add a remote MCP server in Cursor's MCP settings, use the URL above, and complete OAuth when Cursor opens the browser. See the [Cursor MCP documentation](https://cursor.com/docs/mcp). |
| **Other clients** | Use any client that supports remote **Streamable HTTP** MCP servers with OAuth and dynamic client registration. |

Client labels change over time. Use the exact hosted URL shown above.

## Things you can ask

- “Show me my newest lead.”
- “Which of my tasks are overdue?”
- “Find my uncontacted Zillow leads.”
- “Find my Zillow leads in the Eligible For Transfer smart list.”
- “Show the active deals for Jordan Smith.”
- “Find Jordan Smith, then create a follow-up task for them tomorrow at 9:00 AM and assign it to
  me.”
- “Find Jordan Smith, then schedule an appointment with them next Tuesday afternoon.”
- “Find Jordan Smith, then use their person ID to summarize recent calls, texts, emails, and
  appointments.”

Your AI client may ask for confirmation before it creates, updates, or deletes CRM data.

## What the Follow Up Boss MCP can do

The server exposes more than 150 tools across the Follow Up Boss API.

| Area | Examples |
| --- | --- |
| **Leads and contacts** | Search people, find the latest or uncontacted leads, check duplicates, review person activity, claim leads, and manage relationships. |
| **Daily work** | List overdue, due-today, and upcoming tasks; create follow-ups; and manage appointments, types, and outcomes. |
| **Deals and pipeline** | Work with deals, stages, pipelines, smart lists, ponds, deal custom fields, and attachments. |
| **Communication** | Review calls, text messages, email events, and lead events; add notes or retrieve and update a known note by ID. |
| **Automation and teams** | Use action plans, automations, groups, teams, team inboxes, templates, and round-robin settings. |
| **Administration** | Work with users, custom fields, webhooks, email campaigns, and registered inbox apps when the connected account has permission. |

See the [complete MCP tool catalog and usage guide](https://github.com/theperrygroup/Follow-Up-Boss-MCP/blob/main/docs/mcp-usage.md)
for the available tools and common workflows.

## Choose the right setup

| Goal | Recommended path | What you need |
| --- | --- | --- |
| Connect an AI assistant to Follow Up Boss | **Hosted MCP** | The URL above and a Follow Up Boss login |
| Develop or test the Python package | **Local development** | Git, Python 3.12+, `uv`, and test credentials |
| Operate your own shared deployment | **Self-hosting** | HTTPS infrastructure, PostgreSQL, Redis, AWS Secrets Manager, and a Follow Up Boss OAuth app |

Most users only need the hosted path, troubleshooting, and FAQ. Local development and self-hosting
are for developers and operators.

## How the hosted connection works

Your client discovers the server's OAuth configuration, sends you to Follow Up Boss to approve
access, and receives a separate MCP-scoped token. You never put a Follow Up Boss API key or password
in the MCP configuration. The hosted service resolves your account and credential again on every
tool call instead of sharing a client between tenants.

Requested CRM data is returned to your AI client so it can answer you. That client's provider and
workspace policies govern how it processes and retains the conversation, so only connect a client
that your organization approves for CRM data.

### Permissions and write access

- The integration can only access data allowed by the Follow Up Boss user who authorizes it.
- The server includes create, update, and delete tools—not only read tools.
- Review tool requests before approving actions that change CRM data.
- If your client supports tool-level controls, disable write or administrative tools when you only
  need search and reporting.

Read [Security](https://github.com/theperrygroup/Follow-Up-Boss-MCP/blob/main/docs/security.md) for
the authentication, credential storage, isolation, logging, revocation, and rate-limit details.

This is an independently developed, community integration. It is not an official Follow Up Boss
product and is not endorsed by Follow Up Boss.

The hosted endpoint at `fub.theperry.group` is operated by The Perry Group. For non-sensitive setup
support, [open a GitHub issue](https://github.com/theperrygroup/Follow-Up-Boss-MCP/issues). For a
security issue or a lost or compromised client, follow the private reporting and revocation steps
in the [security policy](https://github.com/theperrygroup/Follow-Up-Boss-MCP/blob/main/SECURITY.md).
Never include credentials, tokens, or customer data in a public issue.

## Troubleshooting

- **The URL shows `401` in a browser:** This is expected. `/mcp` is a protected machine-to-machine
  endpoint, not a web page. Paste it inside an MCP client to start OAuth.
- **The sign-in window does not open:** Confirm the client supports remote Streamable HTTP with
  OAuth, allow pop-ups, then remove and add the connector again.
- **Tools are missing:** Use the client's **Refresh tools** or **Scan tools** action. A workspace
  admin may need to approve newly discovered actions.
- **A tool returns `401`:** Reconnect the integration to repeat authorization. Automatic token
  refresh varies by client, so some clients may ask you to sign in again after the connection has
  been idle or its access token expires.
- **A tool returns `403`:** The connected Follow Up Boss user may lack permission for that record
  or action, or the operation may require registered-system headers that are not available to the
  connection.
- **A tool returns `429`:** Wait briefly, then retry with a narrower request.

## FAQ

### What is a Follow Up Boss MCP server?

It is a Model Context Protocol server that translates AI tool calls into authenticated Follow Up
Boss API operations. It lets an AI assistant work with CRM data without manually exporting or
re-entering records.

### Do I need Python or an API key?

Not for the hosted service. Paste the hosted URL into a compatible AI client and complete OAuth.
Python and API credentials are only needed for local development or self-hosting.

### Does this work with ChatGPT, Claude, and Cursor?

The hosted endpoint uses remote Streamable HTTP MCP and OAuth. ChatGPT, Claude, and Cursor support
remote MCP, subject to their current plan, workspace, and token-refresh requirements. Use the
client-specific links in [Where to paste the URL](#where-to-paste-the-url).

### Can the AI change my Follow Up Boss data?

Yes. The server includes tools that create, update, and delete records. The available data and
actions are limited by the permissions of the Follow Up Boss account you authorize and any action
controls in your AI client.

## Developer and operator setup

The hosted URL requires no local installation. Use the following sections only to work on the code
or run your own deployment.

### Local development

Use this path only when you want to develop or run the server yourself. It requires Python 3.12+,
[`uv`](https://docs.astral.sh/uv/), and a Follow Up Boss API key or OAuth token for a test account.

```bash
git clone https://github.com/theperrygroup/Follow-Up-Boss-MCP.git
cd Follow-Up-Boss-MCP
uv sync
export FOLLOWUPBOSS_API_KEY="your-test-api-key"
uv run followupboss-mcp stdio
```

To use a Follow Up Boss OAuth access token for local development instead of an API key:

```bash
export FOLLOWUPBOSS_AUTH_MODE="oauth"
export FOLLOWUPBOSS_ACCESS_TOKEN="your-test-access-token"
uv run followupboss-mcp stdio
```

To expose a local HTTP endpoint instead:

```bash
uv run followupboss-mcp streamable-http --host 127.0.0.1 --port 8000 --path /mcp
```

The URL is then `http://127.0.0.1:8000/mcp`. Do not commit real credentials. See
[MCP Usage](https://github.com/theperrygroup/Follow-Up-Boss-MCP/blob/main/docs/mcp-usage.md) for OAuth
and system-header settings, and [Contributing](https://github.com/theperrygroup/Follow-Up-Boss-MCP/blob/main/CONTRIBUTING.md)
for validation commands.

### Self-hosting

The production entrypoint adds delegated OAuth, tenant isolation, PostgreSQL token metadata, AWS
Secrets Manager, Redis rate limiting, and ECS/Fargate assets. First, configure the required
infrastructure and environment described in the
[hosted deployment guide](https://github.com/theperrygroup/Follow-Up-Boss-MCP/blob/main/docs/hosted-deployment-guide.md).
Then run:

```bash
uv run followupboss-mcp-hosted --host 0.0.0.0 --port 8000 --path /mcp
```

Local transports are single-tenant developer paths, not shared production servers.

## Documentation

### Using the MCP

- [MCP tool catalog and usage guide](https://github.com/theperrygroup/Follow-Up-Boss-MCP/blob/main/docs/mcp-usage.md)
- [Security model](https://github.com/theperrygroup/Follow-Up-Boss-MCP/blob/main/docs/security.md)
- [MCP validation checklist](https://github.com/theperrygroup/Follow-Up-Boss-MCP/blob/main/docs/mcp-validation-checklist.md)

### Developing the project

- [Contributing](https://github.com/theperrygroup/Follow-Up-Boss-MCP/blob/main/CONTRIBUTING.md)
- [Architecture](https://github.com/theperrygroup/Follow-Up-Boss-MCP/blob/main/docs/architecture.md)
- [Testing](https://github.com/theperrygroup/Follow-Up-Boss-MCP/blob/main/docs/testing.md)
- [Follow Up Boss API coverage matrix](https://github.com/theperrygroup/Follow-Up-Boss-MCP/blob/main/docs/api-coverage-matrix.md)
- [Final validation report](https://github.com/theperrygroup/Follow-Up-Boss-MCP/blob/main/docs/final-validation-report.md)

### Operating a hosted deployment

- [Hosted deployment guide](https://github.com/theperrygroup/Follow-Up-Boss-MCP/blob/main/docs/hosted-deployment-guide.md)
- [Customer onboarding flow](https://github.com/theperrygroup/Follow-Up-Boss-MCP/blob/main/docs/customer-onboarding-flow.md)
- [ECS deployment guide](https://github.com/theperrygroup/Follow-Up-Boss-MCP/blob/main/deploy/ecs/README.md)
- [Security incident playbook](https://github.com/theperrygroup/Follow-Up-Boss-MCP/blob/main/docs/security-incident-playbook.md)
- [Release checklist](https://github.com/theperrygroup/Follow-Up-Boss-MCP/blob/main/docs/release-checklist.md)

## Contributing

Issues and pull requests are welcome. Read [CONTRIBUTING.md](https://github.com/theperrygroup/Follow-Up-Boss-MCP/blob/main/CONTRIBUTING.md),
keep secrets and customer data out of commits, and run `make validate` before opening a pull request.
