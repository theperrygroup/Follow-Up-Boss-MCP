# Follow Up Boss plugin for Claude Code

The plugin bundles the hosted Follow Up Boss MCP connection and workflow guidance. Install it
through Claude Code's plugin marketplace system; no Python server, API key, or local proxy is
required. The service is operated by The Perry Group and is an independent integration, not an
official Follow Up Boss product.

## Install

Run these commands in your terminal:

```bash
claude plugin marketplace add theperrygroup/Follow-Up-Boss-MCP
claude plugin install follow-up-boss@follow-up-boss-mcp
```

These commands install for your user account. For a local checkout containing the plugin, run
`claude plugin marketplace add .` from the repository root instead of the first command. The
GitHub installation requires a repository revision that includes `.claude-plugin/marketplace.json`.

Start a new Claude Code session, or follow Claude Code's prompt to reload plugins. Open `/mcp`,
select the plugin's `follow_up_boss` server, and complete the OAuth sign-in. The scoped server name
is `plugin:follow-up-boss:follow_up_boss`. The server URL is:

```text
https://fub.theperry.group/mcp
```

Claude Code discovers authentication from the hosted service. Do not add an API key, token, OAuth
client secret, or `Authorization` header to the plugin files.

## Verify and use

Confirm that the plugin is enabled and its components are present:

```bash
claude plugin list
claude plugin details follow-up-boss
```

Then ask Claude: **“Who am I in Follow Up Boss?”** A successful identity tool response verifies
the authenticated connection. Installation or a component inventory alone does not verify OAuth
or access to your account.

After connecting, ask for work such as “Show my overdue follow-up tasks” or “Find this contact and
summarize their recent activity.” Changes to records require an authorized user request and remain
subject to Claude Code's tool permissions and the connected Follow Up Boss account's access.
See the [tool guide](mcp-usage.md) and [security guide](security.md).

## Claude chat, Desktop, and Cowork

The commands above install a **Claude Code plugin**, including when Claude Code runs in the
Desktop app's Code tab. For Claude chat's hosted MCP access, add a custom connector using the same
server URL in **Customize → Connectors** and complete its OAuth flow. A Code plugin installation
does not by itself configure that chat connector.

Claude also offers plugins in Cowork and other Claude surfaces; their installation, synchronization,
and available components depend on that surface and workspace policy. This package's documented
and tested installation target is Claude Code. It is not a `.mcpb` desktop extension that launches
a local server. See Anthropic's [custom connector instructions](https://support.claude.com/en/articles/11175166-get-started-with-custom-connectors-using-remote-mcp)
and [plugins in Claude](https://support.claude.com/en/articles/13837440-use-plugins-in-claude).

## Troubleshooting

- **Plugin not found:** add the marketplace first, then use the full install ID
  `follow-up-boss@follow-up-boss-mcp`. For an unpublished checkout, add its local repository path.
- **Authentication required:** use `/mcp` to authenticate or re-authenticate the plugin server.
  An unauthenticated `401` from the hosted URL is expected.
- **Another Follow Up Boss connection is already configured:** inspect `/mcp` to see the active
  source. Claude Code may prefer an existing manually configured server for the same endpoint.
  Keep the connection you intend to use; do not copy credentials between configurations.
- **Plugin files changed:** bump the version for published releases, update the marketplace and
  plugin, then start a new session or reload when prompted.

## Maintainer validation

From the repository root, validate both the package and marketplace with the installed Claude Code
CLI before release:

```bash
claude plugin validate --strict ./plugins/follow-up-boss
claude plugin validate --strict .
```

The package uses `.claude-plugin/plugin.json` for metadata and Claude Code's default discovery of
the shared `.mcp.json` and `skills/` directory. The marketplace points at the complete plugin root
so these files travel together. Validate an actual local marketplace install as well as the JSON;
authenticated tool verification is a separate check requiring the account owner's OAuth sign-in.

Schema and lifecycle references: [plugin manifest](https://code.claude.com/docs/en/plugins-reference),
[marketplace creation](https://code.claude.com/docs/en/plugin-marketplaces), and
[MCP in Claude Code](https://code.claude.com/docs/en/mcp).
