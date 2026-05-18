"""Command-line entrypoint for the Follow Up Boss MCP server."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from typing import cast

from followupboss_mcp.config import FollowUpBossServerSettings, FollowUpBossSettings, TransportMode
from followupboss_mcp.mcp_server import create_server
from followupboss_mcp.observability import configure_sentry, flush_sentry


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser.

    Returns:
        The configured argument parser for the supported server transports.
    """
    parser = argparse.ArgumentParser(
        prog="followupboss-mcp",
        description="Run the Follow Up Boss MCP server.",
    )
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser(
        "stdio",
        help="Run the single-tenant local-dev MCP server over stdio.",
    )

    streamable_http = subparsers.add_parser(
        "streamable-http",
        help="Run the single-tenant local-dev MCP server over streamable HTTP.",
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
    """Run the CLI.

    Args:
        argv: Optional command-line arguments.

    Returns:
        The process exit code.
    """
    parser = build_parser()
    args = parser.parse_args(argv)
    early_transport = (
        cast(TransportMode, args.command) if args.command in {"stdio", "streamable-http"} else None
    )
    configure_sentry(entrypoint="followupboss-mcp", transport=early_transport)
    server_settings = FollowUpBossServerSettings()
    command = args.command or server_settings.transport
    configure_sentry(entrypoint="followupboss-mcp", transport=cast(TransportMode, command))
    local_dev_settings = FollowUpBossSettings()

    try:
        if command == "stdio":
            server = create_server(
                local_dev_settings,
                server_settings=server_settings.model_copy(update={"transport": "stdio"}),
            )
            server.run(transport="stdio")
            return 0

        resolved_server_settings = server_settings.model_copy(
            update={
                "transport": "streamable-http",
                "host": getattr(args, "host", server_settings.host),
                "port": getattr(args, "port", server_settings.port),
                "streamable_http_path": getattr(
                    args,
                    "path",
                    server_settings.streamable_http_path,
                ),
            }
        )
        server = create_server(local_dev_settings, server_settings=resolved_server_settings)
        server.run(transport="streamable-http")
        return 0
    finally:
        flush_sentry()


if __name__ == "__main__":
    raise SystemExit(main())
