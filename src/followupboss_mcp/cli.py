"""Command-line entrypoint for the Follow Up Boss MCP server."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from followupboss_mcp.config import FollowUpBossSettings
from followupboss_mcp.mcp_server import create_server


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="followupboss-mcp",
        description="Run the Follow Up Boss MCP server.",
    )
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("stdio", help="Run the MCP server over stdio.")

    streamable_http = subparsers.add_parser(
        "streamable-http",
        help="Run the MCP server over streamable HTTP.",
    )
    streamable_http.add_argument("--host", default="127.0.0.1", help="Bind host.")
    streamable_http.add_argument("--port", default=8000, type=int, help="Bind port.")
    streamable_http.add_argument(
        "--path",
        default="/mcp",
        help="Streamable HTTP mount path.",
    )

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI."""
    parser = build_parser()
    args = parser.parse_args(argv)
    command = args.command or "stdio"

    settings = FollowUpBossSettings()
    if command == "stdio":
        server = create_server(settings)
        server.run(transport="stdio")
        return 0

    server = create_server(settings, host=args.host, port=args.port, streamable_http_path=args.path)
    server.run(transport="streamable-http")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
