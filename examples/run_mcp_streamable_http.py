"""Run the Follow Up Boss MCP server over streamable HTTP."""

from __future__ import annotations

from followupboss_mcp.config import FollowUpBossServerSettings, FollowUpBossSettings
from followupboss_mcp.mcp_server import create_server


def main() -> None:
    """Run the example.

    This keeps the single-tenant environment-backed flow explicit for local
    inspection while hosted multi-tenant HTTP support is refactored.
    """
    server_settings = FollowUpBossServerSettings.model_validate(
        {
            "transport": "streamable-http",
            "host": "127.0.0.1",
            "port": 8000,
            "streamable_http_path": "/mcp",
        }
    )
    server = create_server(FollowUpBossSettings(), server_settings=server_settings)
    server.run(transport=server_settings.transport)


if __name__ == "__main__":
    main()
