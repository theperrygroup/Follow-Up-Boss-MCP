"""FastMCP server construction."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from followupboss_mcp.config import FollowUpBossSettings
from followupboss_mcp.http_client import FollowUpBossAsyncClient, FollowUpBossClientProtocol
from followupboss_mcp.mcp_registration import register_server_surface
from followupboss_mcp.mcp_tools import FollowUpBossToolAdapter, ServiceBundle
from followupboss_mcp.services.appointments import AppointmentsService
from followupboss_mcp.services.calls import CallsService
from followupboss_mcp.services.custom_fields import CustomFieldsService
from followupboss_mcp.services.deals import DealsService
from followupboss_mcp.services.events import EventsService
from followupboss_mcp.services.identity import IdentityService
from followupboss_mcp.services.notes import NotesService
from followupboss_mcp.services.people import PeopleService
from followupboss_mcp.services.pipelines import PipelinesService
from followupboss_mcp.services.tasks import TasksService
from followupboss_mcp.services.templates import TemplatesService
from followupboss_mcp.services.text_messages import (
    TextMessagesService,
    TextMessageTemplatesService,
)
from followupboss_mcp.services.users import UsersService
from followupboss_mcp.services.webhooks import WebhooksService
from mcp.server.fastmcp import FastMCP

_PROJECT_ROOT = Path(__file__).resolve().parents[2]


def build_service_bundle(client: FollowUpBossClientProtocol) -> ServiceBundle:
    """Create the typed service bundle used by the MCP adapter.

    Args:
        client: The shared Follow Up Boss client implementation.

    Returns:
        A fully wired service bundle that shares the same transport client.
    """
    people_service = PeopleService(client)
    return ServiceBundle(
        appointments=AppointmentsService(client),
        calls=CallsService(client),
        custom_fields=CustomFieldsService(client),
        deals=DealsService(client),
        events=EventsService(client),
        identity=IdentityService(client),
        notes=NotesService(client, people_service=people_service),
        people=people_service,
        pipelines=PipelinesService(client),
        tasks=TasksService(client),
        text_message_templates=TextMessageTemplatesService(client),
        text_messages=TextMessagesService(client),
        templates=TemplatesService(client),
        users=UsersService(client),
        webhooks=WebhooksService(client),
    )


def create_server(
    settings: FollowUpBossSettings | None = None,
    *,
    client: FollowUpBossClientProtocol | None = None,
    host: str = "127.0.0.1",
    port: int = 8000,
    streamable_http_path: str = "/mcp",
) -> FastMCP:
    """Create and register the FastMCP server."""
    resolved_settings = settings or FollowUpBossSettings()
    resolved_client = client or FollowUpBossAsyncClient(resolved_settings)
    services = build_service_bundle(resolved_client)
    adapter = FollowUpBossToolAdapter(services)

    @asynccontextmanager
    async def lifespan(_: FastMCP) -> AsyncIterator[None]:
        yield
        await resolved_client.aclose()

    mcp = FastMCP(
        "Follow Up Boss MCP",
        instructions=(
            "Use the typed Follow Up Boss tools for identity checks, lead search, lead ingestion, "
            "appointments, calls, deals, pipelines, tasks, templates, text messages, notes, "
            "users, custom fields, and webhook administration."
        ),
        host=host,
        port=port,
        streamable_http_path=streamable_http_path,
        json_response=True,
        log_level=resolved_settings.log_level,
        lifespan=lifespan,
    )
    register_server_surface(mcp, adapter, project_root=_PROJECT_ROOT)
    return mcp
