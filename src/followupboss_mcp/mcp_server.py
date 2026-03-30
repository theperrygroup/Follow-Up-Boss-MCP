"""FastMCP server construction."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from followupboss_mcp.config import (
    FollowUpBossServerSettings,
    FollowUpBossSettings,
    FollowUpBossTenantSettings,
)
from followupboss_mcp.hosted_auth import (
    HostedAuthSettings,
    HostedIdentityVerifier,
    HostedTenantTokenVerifier,
)
from followupboss_mcp.http_client import FollowUpBossAsyncClient, FollowUpBossClientProtocol
from followupboss_mcp.logging import configure_logging
from followupboss_mcp.mcp_registration import register_server_surface
from followupboss_mcp.mcp_tools import FollowUpBossToolAdapter
from followupboss_mcp.tenant_store import TenantStore
from followupboss_mcp.tenant_runtime import (
    RequestScopedTenantServiceBundleResolver,
    StaticServiceBundleResolver,
    TenantRuntimeFactory,
    build_service_bundle,
)
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP

_PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _resolve_hosted_auth(
    *,
    hosted_auth: HostedAuthSettings | None,
    hosted_token_verifier: HostedIdentityVerifier | None,
    tenant_store: TenantStore | None,
) -> tuple[AuthSettings | None, HostedTenantTokenVerifier | None]:
    """Validate hosted-auth inputs and build FastMCP auth objects.

    Args:
        hosted_auth: Hosted resource-server auth settings.
        hosted_token_verifier: Hosted token verifier that returns verified
            identity payloads.
        tenant_store: Tenant store used to resolve the canonical `tenant_id`
            claim into one active tenant.

    Returns:
        The FastMCP auth settings and token verifier, or `(None, None)` when
        hosted auth is disabled.

    Raises:
        ValueError: If hosted auth is only partially configured.
    """
    if hosted_auth is None and hosted_token_verifier is None and tenant_store is None:
        return None, None
    if hosted_auth is None or hosted_token_verifier is None or tenant_store is None:
        raise ValueError(
            "hosted_auth, hosted_token_verifier, and tenant_store must be provided together."
        )
    return hosted_auth.to_mcp_auth_settings(), HostedTenantTokenVerifier(
        identity_verifier=hosted_token_verifier,
        tenant_store=tenant_store,
    )


def create_server(
    settings: FollowUpBossTenantSettings | FollowUpBossSettings | None = None,
    *,
    server_settings: FollowUpBossServerSettings | None = None,
    client: FollowUpBossClientProtocol | None = None,
    hosted_auth: HostedAuthSettings | None = None,
    hosted_token_verifier: HostedIdentityVerifier | None = None,
    tenant_store: TenantStore | None = None,
    host: str | None = None,
    port: int | None = None,
    streamable_http_path: str | None = None,
) -> FastMCP:
    """Create and register the FastMCP server.

    Args:
        settings: Optional tenant-scoped runtime settings. When omitted and no
            client is injected, the backward-compatible local-dev settings model
            is loaded from the environment.
        server_settings: Optional server-only bootstrap settings for host, port,
            transport, and log level.
        client: Optional prebuilt client implementation used mainly by tests.
        hosted_auth: Optional hosted-auth resource-server settings for bearer
            token verification on the streamable HTTP transport.
        hosted_token_verifier: Optional hosted token verifier that validates
            bearer tokens into the canonical hosted identity payload.
        tenant_store: Optional tenant store used to resolve the canonical
            hosted `tenant_id` claim into one active tenant.
        host: Optional explicit host override.
        port: Optional explicit port override.
        streamable_http_path: Optional explicit streamable HTTP path override.

    Returns:
        A fully registered FastMCP server. When hosted auth is enabled without
        an injected client, tenant-specific runtimes are resolved for each tool
        call instead of sharing one startup-time client.
    """
    if server_settings is not None:
        resolved_server_settings = server_settings
    elif isinstance(settings, FollowUpBossSettings):
        resolved_server_settings = settings.server_settings()
    else:
        resolved_server_settings = FollowUpBossServerSettings()

    resolved_logger = configure_logging(resolved_server_settings.log_level)

    resolved_settings: FollowUpBossTenantSettings | None
    if settings is None:
        resolved_settings = None if client is not None else FollowUpBossSettings().tenant_settings()
    elif isinstance(settings, FollowUpBossSettings):
        resolved_settings = settings.tenant_settings()
    else:
        resolved_settings = settings

    resolved_mcp_auth_settings, resolved_token_verifier = _resolve_hosted_auth(
        hosted_auth=hosted_auth,
        hosted_token_verifier=hosted_token_verifier,
        tenant_store=tenant_store,
    )

    runtime_factory: TenantRuntimeFactory | None = None
    if resolved_mcp_auth_settings is not None:
        if resolved_settings is None or tenant_store is None:
            raise ValueError("settings and tenant_store are required when hosted auth is enabled.")
        runtime_factory = TenantRuntimeFactory(
            default_settings=resolved_settings,
            tenant_store=tenant_store,
            logger=resolved_logger,
        )

    shared_client: FollowUpBossClientProtocol | None = None
    if client is not None:
        shared_client = client
        service_bundle_resolver = StaticServiceBundleResolver(build_service_bundle(shared_client))
    elif runtime_factory is not None:
        service_bundle_resolver = RequestScopedTenantServiceBundleResolver(runtime_factory)
    else:
        shared_client = FollowUpBossAsyncClient(resolved_settings, logger=resolved_logger)
        service_bundle_resolver = StaticServiceBundleResolver(build_service_bundle(shared_client))
    adapter = FollowUpBossToolAdapter(service_bundle_resolver)
    resolved_host = host if host is not None else resolved_server_settings.host
    resolved_port = port if port is not None else resolved_server_settings.port
    resolved_streamable_http_path = (
        streamable_http_path
        if streamable_http_path is not None
        else resolved_server_settings.streamable_http_path
    )

    @asynccontextmanager
    async def lifespan(_: FastMCP) -> AsyncIterator[None]:
        yield
        if shared_client is not None:
            await shared_client.aclose()

    mcp = FastMCP(
        "Follow Up Boss MCP",
        instructions=(
            "Use the typed Follow Up Boss tools for identity checks, lead search, lead ingestion, "
            "action plans, appointments, appointment types, appointment outcomes, attachments, "
            "automations, calls, custom fields, deals, email marketing, groups, inbox apps, "
            "people relationships, pipelines, ponds, reactions, smart lists, stages, tasks, "
            "team inboxes, teams, templates, text messages, threaded replies, timeframes, "
            "notes, users, and webhook administration."
        ),
        host=resolved_host,
        port=resolved_port,
        streamable_http_path=resolved_streamable_http_path,
        json_response=True,
        log_level=resolved_server_settings.log_level,
        lifespan=lifespan,
        auth=resolved_mcp_auth_settings,
        token_verifier=resolved_token_verifier,
    )
    register_server_surface(
        mcp,
        adapter,
        project_root=_PROJECT_ROOT,
        tenant_runtime_factory=runtime_factory,
    )
    return mcp
