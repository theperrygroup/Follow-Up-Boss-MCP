"""Run the Follow Up Boss MCP server over streamable HTTP."""

from __future__ import annotations

from followupboss_mcp.config import FollowUpBossSettings
from followupboss_mcp.mcp_server import create_server


def main() -> None:
    """Run the example."""
    server = create_server(
        FollowUpBossSettings(), host="127.0.0.1", port=8000, streamable_http_path="/mcp"
    )
    server.run(transport="streamable-http")


if __name__ == "__main__":
    main()
