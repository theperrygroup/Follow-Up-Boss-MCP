# Codex and Claude Code plugins

The repository includes an installable `follow-up-boss` plugin in
[`plugins/follow-up-boss`](../plugins/follow-up-boss). It bundles native manifests
for both clients, one remote MCP connection, and one shared CRM workflow skill.
The existing MCP service remains available to other clients at
`https://fub.theperry.group/mcp`.

The [privacy policy](../PRIVACY.md) describes hosted data handling, retention,
and user controls. Both native manifests link to the same published policy version.

## Codex

Codex supports this repository's Claude-compatible marketplace catalog and loads
the native `.codex-plugin/plugin.json` manifest from the plugin directory.
From a local checkout, register the repository root, then install the plugin:

```bash
codex plugin marketplace add .
codex plugin add follow-up-boss@follow-up-boss-mcp
```

Once this version has been merged to the repository's default branch, it can also
be installed directly from GitHub:

```bash
codex plugin marketplace add theperrygroup/Follow-Up-Boss-MCP
codex plugin add follow-up-boss@follow-up-boss-mcp
```

Start a new Codex task after installation so it picks up the plugin's skill and
MCP tools. Complete OAuth when prompted by the client's connection flow. If you
already configured the hosted endpoint as a standalone MCP server, use one
connection for your work to avoid duplicate tool inventories; installation does
not remove or replace your existing connection.

## Claude Code

See the [Claude Code installation and verification guide](claude-plugin.md).
The same package supplies the `/follow-up-boss:follow-up-boss` skill and the remote
MCP connection. Claude web and Desktop custom connectors are configured separately
using the hosted URL; installing a Claude Code plugin does not configure them.

## Verify the connection

1. Confirm `follow-up-boss` appears in the client's installed plugin list.
2. Complete the browser OAuth flow for your own Follow Up Boss account. Keep keys,
   passwords, and tokens out of plugin configuration and chat.
3. Ask “Who am I in Follow Up Boss?” and verify that `followupboss_get_identity`
   returns the expected account and user.
4. Try a read such as “Show my overdue tasks.” Review the target, assignee, and
   dates before authorizing a write.

An installed manifest, a public HTTP `401`, or successful OAuth metadata discovery
does not prove an authenticated CRM tool call. Report these checks separately.
Use the [MCP troubleshooting guide](../README.md#troubleshooting) for connection
errors and the [tool catalog](mcp-usage.md) for supported operations.

## Develop and distribute

Keep `.codex-plugin/plugin.json` and `.claude-plugin/plugin.json` inside the plugin
directory. Keep `.mcp.json`, `skills/`, and assets at the plugin root so each client
can load a standalone cached copy. Update the version in both manifests together.
The root `.claude-plugin/marketplace.json` is a catalog pointing to the package,
not a second plugin. The package manifests supply its version.

Validate the Claude package and catalog using `claude plugin validate --strict`.
The repository tests check cross-client metadata, paths, MCP configuration, and
workflow tool references. Test each client with its actual plugin installer and
verify the installed copy before claiming an installation works.

Local/GitHub marketplace distribution is separate from approval or listing in a
public vendor directory. This repository does not claim either directory listing.

When the privacy policy changes, publish the policy commit first, then update
both manifest URLs and the package README to that commit's public `PRIVACY.md`
permalink. Update the directory drafts as well. A commit permalink stays valid
when the development branch is merged or removed and identifies the policy
version offered with that package.

Format references: [OpenAI plugin packaging](https://developers.openai.com/plugins/build/plugins),
[Claude Code plugin reference](https://code.claude.com/docs/en/plugins-reference),
and [Claude Code marketplaces](https://code.claude.com/docs/en/plugin-marketplaces).
