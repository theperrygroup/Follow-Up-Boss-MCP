"""Run the Follow Up Boss MCP server over stdio."""

from __future__ import annotations

from followupboss_mcp.config import FollowUpBossSettings
from followupboss_mcp.mcp_server import create_server


def main() -> None:
    """Run the example."""
    server = create_server(FollowUpBossSettings())
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
