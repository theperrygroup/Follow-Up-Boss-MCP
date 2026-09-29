# Follow Up Boss plugin

An installable plugin for Codex and Claude Code, backed by the hosted Follow Up
Boss MCP at `https://fub.theperry.group/mcp`. Sign in through your client's OAuth
flow. No local Python server or API key is required.

The package includes native Codex and Claude Code manifests, the shared remote
MCP connection, and a Follow Up Boss workflow skill. Both clients use the same
connection definition and instructions. Installing this plugin does not grant CRM
access until you authorize your account.

Ask “Who am I in Follow Up Boss?” to verify authentication, then try “Show my
overdue tasks” or “Find my newest lead and summarize recent activity.” Client tool
approval controls and your Follow Up Boss account permissions apply to changes.

See the repository's [installation guide](https://github.com/theperrygroup/Follow-Up-Boss-MCP/blob/main/docs/plugins.md)
and [security policy](https://github.com/theperrygroup/Follow-Up-Boss-MCP/blob/main/SECURITY.md).
Read the [privacy policy](https://github.com/theperrygroup/Follow-Up-Boss-MCP/blob/a565e2bbd3197c0440e6af2ff26c679d3e48f3e0/PRIVACY.md)
for data use, retention, and instructions to request deletion or revoke access.

This is a community integration operated by The Perry Group, not an official
Follow Up Boss product. Claude web/Desktop custom connectors use the same MCP URL;
the Claude Code plugin has its own installation flow.
