"""Run the Follow Up Boss MCP server over stdio."""

from __future__ import annotations

from followupboss_mcp.config import FollowUpBossServerSettings, FollowUpBossSettings
from followupboss_mcp.mcp_server import create_server


def main() -> None:
    """Run the example."""
    server_settings = FollowUpBossServerSettings.model_validate({"transport": "stdio"})
    server = create_server(FollowUpBossSettings(), server_settings=server_settings)
    server.run(transport=server_settings.transport)


if __name__ == "__main__":
    main()
