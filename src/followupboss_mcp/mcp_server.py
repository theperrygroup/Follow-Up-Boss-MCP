"""FastMCP server construction."""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Protocol

from starlette.applications import Starlette
from starlette.routing import Route

from followupboss_mcp.config import (
    FollowUpBossServerSettings,
    FollowUpBossSettings,
    FollowUpBossTenantRuntimeDefaults,
    FollowUpBossTenantSettings,
)
from followupboss_mcp.hosted_auth import (
    HostedAuthSettings,
    HostedIdentityVerifier,
    HostedTenantTokenVerifier,
)
from followupboss_mcp.hosted_oauth import HostedOAuthApplication
from followupboss_mcp.hosted_rate_limits import (
    HostedEndpointRateLimiter,
    HostedRateLimitMiddleware,
)
from followupboss_mcp.http_client import FollowUpBossAsyncClient, FollowUpBossClientProtocol
from followupboss_mcp.logging import configure_logging
from followupboss_mcp.mcp_registration import register_server_surface
from followupboss_mcp.mcp_tools import FollowUpBossToolAdapter
from followupboss_mcp.tenant_runtime import (
    RequestScopedTenantServiceBundleResolver,
    ServiceBundleResolver,
    StaticServiceBundleResolver,
    TenantRuntimeFactory,
    build_service_bundle,
)
from followupboss_mcp.tenant_store import TenantStore
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP

_PROJECT_ROOT = Path(__file__).resolve().parents[2]


class AsyncManagedResource(Protocol):
    """Protocol for async resources managed by the FastMCP lifespan."""

    async def open(self) -> None:
        """Open the resource before the server starts handling requests."""

    async def aclose(self) -> None:
        """Close the resource during server shutdown."""


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


def _resolve_local_tenant_settings(
    settings: FollowUpBossTenantRuntimeDefaults | FollowUpBossTenantSettings | None,
    *,
    client: FollowUpBossClientProtocol | None,
) -> FollowUpBossTenantSettings | None:
    """Resolve credentialed settings for local single-tenant paths.

    Args:
        settings: Optional caller-supplied settings object.
        client: Optional injected client that makes credentialed settings
            unnecessary for local tests.

    Returns:
        Credentialed local settings when the server must build its own shared
        client, otherwise `None`.
    """
    if settings is None:
        return None if client is not None else FollowUpBossSettings().tenant_settings()
    if isinstance(settings, FollowUpBossSettings):
        return settings.tenant_settings()
    if isinstance(settings, FollowUpBossTenantSettings):
        return settings
    return None


def _resolve_tenant_runtime_defaults(
    settings: FollowUpBossTenantRuntimeDefaults | FollowUpBossTenantSettings | None,
) -> FollowUpBossTenantRuntimeDefaults:
    """Resolve non-secret hosted runtime defaults from caller settings.

    Args:
        settings: Optional caller-supplied settings object.

    Returns:
        Non-secret client defaults used for hosted tenant runtime construction.
        When omitted, built-in defaults are used without loading tenant-related
        environment variables.
    """
    if settings is None:
        return FollowUpBossTenantRuntimeDefaults.builtin_defaults()
    if isinstance(settings, FollowUpBossTenantSettings):
        return settings.tenant_runtime_defaults()
    return settings


class FollowUpBossFastMCP(FastMCP):
    """FastMCP subclass with hosted endpoint abuse controls."""

    _hosted_rate_limiter: HostedEndpointRateLimiter | None = None
    _hosted_oauth_application: HostedOAuthApplication | None = None

    def streamable_http_app(self) -> Starlette:
        """Return the streamable HTTP app with hosted abuse controls applied.

        Returns:
            The configured streamable HTTP Starlette application.
        """
        app = super().streamable_http_app()
        if self._hosted_oauth_application is not None:
            existing_paths = {getattr(route, "path", None) for route in app.routes}
            for oauth_route in self._hosted_oauth_application.routes():
                if oauth_route.path not in existing_paths:
                    app.routes.append(oauth_route)

        if self._hosted_rate_limiter is None or self._token_verifier is None:
            return app

        for route in app.routes:
            if (
                isinstance(route, Route)
                and route.path == self.settings.streamable_http_path
                and not isinstance(route.app, HostedRateLimitMiddleware)
            ):
                route.app = HostedRateLimitMiddleware(
                    route.app,
                    rate_limiter=self._hosted_rate_limiter,
                )
                break
        return app


def create_server(
    settings: FollowUpBossTenantRuntimeDefaults | FollowUpBossTenantSettings | None = None,
    *,
    server_settings: FollowUpBossServerSettings | None = None,
    client: FollowUpBossClientProtocol | None = None,
    hosted_auth: HostedAuthSettings | None = None,
    hosted_token_verifier: HostedIdentityVerifier | None = None,
    tenant_store: TenantStore | None = None,
    hosted_rate_limiter: HostedEndpointRateLimiter | None = None,
    hosted_oauth_application: HostedOAuthApplication | None = None,
    managed_resources: Sequence[AsyncManagedResource] = (),
    host: str | None = None,
    port: int | None = None,
    streamable_http_path: str | None = None,
) -> FastMCP:
    """Create and register the FastMCP server.

    Args:
        settings: Optional non-secret hosted runtime defaults or credentialed
            local tenant settings. When omitted, local single-tenant flows keep
            using the backward-compatible environment-backed credential model,
            while hosted flows use only built-in client defaults unless the
            caller passes explicit hosted runtime defaults.
        server_settings: Optional server-only bootstrap settings for host, port,
            transport, and log level.
        client: Optional prebuilt client implementation used mainly by tests.
        hosted_auth: Optional hosted-auth resource-server settings for bearer
            token verification on the streamable HTTP transport.
        hosted_token_verifier: Optional hosted token verifier that validates
            bearer tokens into the canonical hosted identity payload.
        tenant_store: Optional tenant store used to resolve the canonical
            hosted `tenant_id` claim into one active tenant.
        hosted_rate_limiter: Optional hosted endpoint rate limiter. When hosted
            auth is enabled and no limiter is provided, a default in-memory
            per-tenant/per-client limiter is applied to the streamable HTTP
            endpoint.
        hosted_oauth_application: Optional OAuth authorization-server routes to
            expose beside the hosted streamable HTTP endpoint.
        managed_resources: Optional async resources to open before serving and
            close during shutdown, such as shared hosted metadata pools.
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

    resolved_mcp_auth_settings, resolved_token_verifier = _resolve_hosted_auth(
        hosted_auth=hosted_auth,
        hosted_token_verifier=hosted_token_verifier,
        tenant_store=tenant_store,
    )

    runtime_factory: TenantRuntimeFactory | None = None
    resolved_hosted_rate_limiter = hosted_rate_limiter
    if resolved_mcp_auth_settings is not None:
        if tenant_store is None:
            raise ValueError("tenant_store is required when hosted auth is enabled.")
        runtime_factory = TenantRuntimeFactory(
            default_settings=_resolve_tenant_runtime_defaults(settings),
            tenant_store=tenant_store,
            logger=resolved_logger,
        )
        if resolved_hosted_rate_limiter is None:
            resolved_hosted_rate_limiter = HostedEndpointRateLimiter(logger=resolved_logger)

    shared_client: FollowUpBossClientProtocol | None = None
    service_bundle_resolver: ServiceBundleResolver
    if client is not None:
        shared_client = client
        service_bundle_resolver = StaticServiceBundleResolver(build_service_bundle(shared_client))
    elif runtime_factory is not None:
        service_bundle_resolver = RequestScopedTenantServiceBundleResolver(runtime_factory)
    else:
        resolved_local_settings = _resolve_local_tenant_settings(settings, client=client)
        if resolved_local_settings is None:
            raise ValueError(
                "Credentialed tenant settings are required when hosted auth is disabled "
                "and no client is injected."
            )
        shared_client = FollowUpBossAsyncClient(resolved_local_settings, logger=resolved_logger)
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
        opened_resources: list[AsyncManagedResource] = []
        try:
            for resource in managed_resources:
                await resource.open()
                opened_resources.append(resource)
            yield
        finally:
            try:
                if shared_client is not None:
                    await shared_client.aclose()
            finally:
                try:
                    for resource in reversed(opened_resources):
                        await resource.aclose()
                finally:
                    if resolved_hosted_rate_limiter is not None:
                        await resolved_hosted_rate_limiter.aclose()
                    if hosted_oauth_application is not None:
                        await hosted_oauth_application.aclose()

    mcp = FollowUpBossFastMCP(
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
    mcp._hosted_rate_limiter = resolved_hosted_rate_limiter
    mcp._hosted_oauth_application = hosted_oauth_application
    register_server_surface(
        mcp,
        adapter,
        project_root=_PROJECT_ROOT,
        tenant_runtime_factory=runtime_factory,
    )
    return mcp
