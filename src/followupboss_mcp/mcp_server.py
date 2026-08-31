"""MCP server construction."""

from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from typing import Any, Literal, Protocol

from starlette.applications import Starlette
from starlette.routing import Route

from followupboss_mcp import __version__
from followupboss_mcp.config import (
    FollowUpBossServerSettings,
    FollowUpBossSettings,
    FollowUpBossTenantRuntimeDefaults,
    FollowUpBossTenantSettings,
    SentrySettings,
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
from followupboss_mcp.observability import configure_sentry
from followupboss_mcp.tenant_runtime import (
    RequestScopedTenantServiceBundleResolver,
    ServiceBundleResolver,
    StaticServiceBundleResolver,
    TenantClientFactory,
    TenantRuntimeFactory,
    build_service_bundle,
)
from followupboss_mcp.tenant_store import TenantStore
from mcp.server.auth.settings import AuthSettings
from mcp.server.mcpserver import MCPServer
from mcp.server.streamable_http import EventStore
from mcp.server.transport_security import TransportSecuritySettings

_DEFAULT_MAX_REQUEST_BODY_SIZE = 4 * 1024 * 1024


class AsyncManagedResource(Protocol):
    """Protocol for async resources managed by the MCP server lifespan."""

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
    """Validate hosted-auth inputs and build MCP server auth objects.

    Args:
        hosted_auth: Hosted resource-server auth settings.
        hosted_token_verifier: Hosted token verifier that returns verified
            identity payloads.
        tenant_store: Tenant store used to resolve the canonical `tenant_id`
            claim into one active tenant.

    Returns:
        The MCP auth settings and token verifier, or `(None, None)` when
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
        expected_resource=str(hosted_auth.resource_server_url),
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


def _transport_security_settings(
    *,
    hosted_auth: HostedAuthSettings | None,
    host: str,
    port: int,
) -> TransportSecuritySettings:
    """Build an explicit Host and Origin allowlist for Streamable HTTP.

    The v2 SDK only enables its localhost defaults when the app factory receives
    a loopback host. Hosted deployments bind to a wildcard address, so their
    public resource URL must be translated into an explicit allowlist instead
    of silently disabling DNS-rebinding protection.

    Args:
        hosted_auth: Optional hosted resource-server settings whose public URL
            identifies the production Host and Origin.
        host: Configured server bind host.
        port: Configured server bind port.

    Returns:
        Enabled transport-security settings for production and loopback access.
    """
    allowed_hosts = {
        "127.0.0.1",
        "127.0.0.1:*",
        "localhost",
        "localhost:*",
        "[::1]",
        "[::1]:*",
    }
    allowed_origins = {
        "http://127.0.0.1",
        "http://127.0.0.1:*",
        "http://localhost",
        "http://localhost:*",
        "http://[::1]",
        "http://[::1]:*",
    }

    if hosted_auth is not None:
        resource_url = hosted_auth.resource_server_url
        public_host = resource_url.host
        public_port = resource_url.port
        # ``AnyHttpUrl`` guarantees both values; keep the guard for defensive callers.
        if public_host is None or public_port is None:  # pragma: no cover
            raise ValueError("hosted resource_server_url must include a valid host and port.")
        allowed_hosts.add(public_host)
        allowed_hosts.add(f"{public_host}:{public_port}")
        public_origin = f"{resource_url.scheme}://{public_host}"
        allowed_origins.add(public_origin)
        allowed_origins.add(f"{public_origin}:{public_port}")
    elif host not in {"0.0.0.0", "::", "[::]"}:
        bind_host = f"[{host}]" if ":" in host and not host.startswith("[") else host
        allowed_hosts.add(bind_host)
        allowed_hosts.add(f"{bind_host}:{port}")
        allowed_origins.add(f"http://{bind_host}")
        allowed_origins.add(f"http://{bind_host}:{port}")

    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=sorted(allowed_hosts),
        allowed_origins=sorted(allowed_origins),
    )


class FollowUpBossMCPServer(MCPServer):
    """MCPServer subclass with hosted endpoint abuse controls."""

    _hosted_rate_limiter: HostedEndpointRateLimiter | None = None
    _hosted_oauth_application: HostedOAuthApplication | None = None
    _streamable_http_host = "127.0.0.1"
    _streamable_http_port = 8000
    _streamable_http_path = "/mcp"
    _streamable_http_json_response = True
    _transport_security = _transport_security_settings(
        hosted_auth=None,
        host=_streamable_http_host,
        port=_streamable_http_port,
    )

    @property
    def transport_security(self) -> TransportSecuritySettings:
        """Return the configured Streamable HTTP transport security policy."""
        return self._transport_security

    def configure_streamable_http(
        self,
        *,
        host: str,
        port: int,
        streamable_http_path: str,
        json_response: bool,
        transport_security: TransportSecuritySettings,
    ) -> None:
        """Store application-owned defaults moved off the v2 constructor."""
        self._streamable_http_host = host
        self._streamable_http_port = port
        self._streamable_http_path = streamable_http_path
        self._streamable_http_json_response = json_response
        self._transport_security = transport_security

    def run(
        self,
        transport: Literal["stdio", "sse", "streamable-http"] = "stdio",
        **kwargs: Any,
    ) -> None:
        """Run the server, applying configured v2 Streamable HTTP defaults."""
        if transport == "streamable-http":
            kwargs.setdefault("host", self._streamable_http_host)
            kwargs.setdefault("port", self._streamable_http_port)
            kwargs.setdefault("streamable_http_path", self._streamable_http_path)
            kwargs.setdefault("json_response", self._streamable_http_json_response)
            kwargs.setdefault("transport_security", self._transport_security)
        super().run(transport=transport, **kwargs)

    def streamable_http_app(
        self,
        *,
        streamable_http_path: str | None = None,
        json_response: bool | None = None,
        stateless_http: bool = False,
        event_store: EventStore | None = None,
        retry_interval: int | None = None,
        max_request_body_size: int = _DEFAULT_MAX_REQUEST_BODY_SIZE,
        transport_security: TransportSecuritySettings | None = None,
        host: str | None = None,
    ) -> Starlette:
        """Return the streamable HTTP app with hosted abuse controls applied.

        Returns:
            The configured streamable HTTP Starlette application.
        """
        resolved_path = streamable_http_path or self._streamable_http_path
        app = super().streamable_http_app(
            streamable_http_path=resolved_path,
            json_response=(
                self._streamable_http_json_response if json_response is None else json_response
            ),
            stateless_http=stateless_http,
            event_store=event_store,
            retry_interval=retry_interval,
            max_request_body_size=max_request_body_size,
            transport_security=transport_security or self._transport_security,
            host=host or self._streamable_http_host,
        )
        if self._hosted_oauth_application is not None:
            existing_paths = {getattr(route, "path", None) for route in app.routes}
            for oauth_route in self._hosted_oauth_application.routes():
                if oauth_route.path not in existing_paths:
                    app.routes.append(oauth_route)

        if self._hosted_rate_limiter is not None and self._token_verifier is not None:
            for route in app.routes:
                if (
                    isinstance(route, Route)
                    and route.path == resolved_path
                    and not isinstance(route.app, HostedRateLimitMiddleware)
                ):
                    route.app = HostedRateLimitMiddleware(
                        route.app,
                        rate_limiter=self._hosted_rate_limiter,
                    )
                    break

        return app


# Compatibility alias for callers that imported the project-specific v1 name.
FollowUpBossFastMCP = FollowUpBossMCPServer


def create_server(
    settings: FollowUpBossTenantRuntimeDefaults | FollowUpBossTenantSettings | None = None,
    *,
    server_settings: FollowUpBossServerSettings | None = None,
    client: FollowUpBossClientProtocol | None = None,
    hosted_auth: HostedAuthSettings | None = None,
    hosted_token_verifier: HostedIdentityVerifier | None = None,
    tenant_store: TenantStore | None = None,
    tenant_client_factory: TenantClientFactory | None = None,
    hosted_rate_limiter: HostedEndpointRateLimiter | None = None,
    hosted_oauth_application: HostedOAuthApplication | None = None,
    managed_resources: Sequence[AsyncManagedResource] = (),
    sentry_settings: SentrySettings | None = None,
    sentry_entrypoint: str = "followupboss-mcp",
    host: str | None = None,
    port: int | None = None,
    streamable_http_path: str | None = None,
) -> FollowUpBossMCPServer:
    """Create and register the MCP server.

    Args:
        settings: Optional non-secret hosted runtime defaults or credentialed
            local tenant settings. When omitted, local single-tenant flows keep
            using the backward-compatible environment-backed credential model,
            while hosted flows use only built-in client defaults unless the
            caller passes explicit hosted runtime defaults.
        server_settings: Optional server-only bootstrap settings for host, port,
            transport, and log level.
        client: Optional prebuilt client implementation used mainly by local
            tests. Hosted auth rejects injected clients because they would
            bypass per-request tenant credentials.
        hosted_auth: Optional hosted-auth resource-server settings for bearer
            token verification on the streamable HTTP transport.
        hosted_token_verifier: Optional hosted token verifier that validates
            bearer tokens into the canonical hosted identity payload.
        tenant_store: Optional tenant store used to resolve the canonical
            hosted `tenant_id` claim into one active tenant.
        tenant_client_factory: Optional per-tenant client factory used mainly by
            hosted tests. Unlike `client`, this factory is called after the
            authenticated tenant credential has been resolved.
        hosted_rate_limiter: Optional hosted endpoint rate limiter. When hosted
            auth is enabled and no limiter is provided, a default in-memory
            per-tenant/per-client limiter is applied to the streamable HTTP
            endpoint.
        hosted_oauth_application: Optional OAuth authorization-server routes to
            expose beside the hosted streamable HTTP endpoint.
        managed_resources: Optional async resources to open before serving and
            close during shutdown, such as shared hosted metadata pools.
        sentry_settings: Optional Sentry settings used to initialize error
            monitoring. When omitted, Sentry settings are loaded from
            environment variables and disabled when no DSN is configured.
        sentry_entrypoint: Stable runtime entrypoint tag for Sentry events.
        host: Optional explicit host override.
        port: Optional explicit port override.
        streamable_http_path: Optional explicit streamable HTTP path override.

    Returns:
        A fully registered MCP server. When hosted auth is enabled without
        an injected client, tenant-specific runtimes are resolved for each tool
        call instead of sharing one startup-time client.
    """
    if server_settings is not None:
        resolved_server_settings = server_settings
    elif isinstance(settings, FollowUpBossSettings):
        resolved_server_settings = settings.server_settings()
    else:
        resolved_server_settings = FollowUpBossServerSettings()

    configure_sentry(
        sentry_settings,
        entrypoint=sentry_entrypoint,
        transport=resolved_server_settings.transport,
    )
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
        if client is not None:
            raise ValueError("client cannot be provided when hosted auth is enabled.")
        runtime_factory = TenantRuntimeFactory(
            default_settings=_resolve_tenant_runtime_defaults(settings),
            tenant_store=tenant_store,
            logger=resolved_logger,
            client_factory=tenant_client_factory,
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
    async def managed_lifespan() -> AsyncIterator[None]:
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

    @asynccontextmanager
    async def lifespan(_: MCPServer) -> AsyncIterator[None]:
        async with managed_lifespan():
            yield

    mcp = FollowUpBossMCPServer(
        "Follow Up Boss MCP",
        version=__version__,
        instructions=(
            "Use the typed Follow Up Boss tools for identity checks, lead search, lead ingestion, "
            "latest owned lead lookup, owned task intent helpers, lead deal lookups, "
            "action plans, appointments, appointment types, appointment outcomes, attachments, "
            "automations, calls, custom fields, deals, email marketing, groups, inbox apps, "
            "people relationships, pipelines, ponds, reactions, smart lists, stages, tasks, "
            "team inboxes, teams, templates, text messages, threaded replies, timeframes, "
            "notes, users, and webhook administration. For uncontacted, never-contacted, "
            "no-communication, zero-communication, or needs-contact lead filter requests, "
            "use followupboss_list_uncontacted_leads rather than smart-list lookup unless "
            "the user explicitly says smart list or saved list. If a user asks "
            "for notes associated "
            "with a Follow Up Boss person or lead ID, do not search events or infer that "
            "there are no notes. Follow Up Boss has not made note search by FUB person ID "
            "available via the API; tell the user this and suggest asking "
            "support@followupboss.com to make it possible to search for notes associated "
            "with a FUB person ID."
        ),
        log_level=resolved_server_settings.log_level,
        lifespan=lifespan,
        auth=resolved_mcp_auth_settings,
        token_verifier=resolved_token_verifier,
    )
    mcp._hosted_rate_limiter = resolved_hosted_rate_limiter
    mcp._hosted_oauth_application = hosted_oauth_application
    mcp.configure_streamable_http(
        host=resolved_host,
        port=resolved_port,
        streamable_http_path=resolved_streamable_http_path,
        json_response=True,
        transport_security=_transport_security_settings(
            hosted_auth=hosted_auth,
            host=resolved_host,
            port=resolved_port,
        ),
    )
    register_server_surface(
        mcp,
        adapter,
        tenant_runtime_factory=runtime_factory,
    )
    return mcp
