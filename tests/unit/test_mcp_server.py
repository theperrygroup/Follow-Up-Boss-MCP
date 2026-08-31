"""Focused unit tests for server-construction helper branches."""

from __future__ import annotations

from typing import cast

import pytest
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route

from followupboss_mcp.auth import AuthMode
from followupboss_mcp.config import (
    FollowUpBossServerSettings,
    FollowUpBossSettings,
    FollowUpBossTenantRuntimeDefaults,
    FollowUpBossTenantSettings,
)
from followupboss_mcp.hosted_auth import (
    DevelopmentHostedTokenVerifier,
    HostedAuthSettings,
    HostedVerifiedIdentity,
)
from followupboss_mcp.hosted_oauth import HostedOAuthApplication
from followupboss_mcp.hosted_rate_limits import HostedEndpointRateLimiter, HostedRateLimitMiddleware
from followupboss_mcp.http_client import FollowUpBossClientProtocol
from followupboss_mcp.mcp_server import (
    FollowUpBossMCPServer,
    _resolve_hosted_auth,
    _resolve_local_tenant_settings,
    _resolve_tenant_runtime_defaults,
    create_server,
)
from followupboss_mcp.tenant_store import (
    DevelopmentTenantStore,
    TenantCredentialRecord,
    TenantCredentialStatus,
    TenantRecord,
    TenantStatus,
)
from mcp.server.auth.settings import AuthSettings
from mcp.server.mcpserver import MCPServer
from mcp.server.transport_security import TransportSecuritySettings


def _hosted_auth_settings() -> HostedAuthSettings:
    """Build representative hosted auth settings for server tests.

    Returns:
        Hosted auth settings for a streamable HTTP endpoint.
    """
    return HostedAuthSettings.model_validate(
        {
            "issuer_url": "https://issuer.example.com",
            "resource_server_url": "https://mcp.example.com/mcp",
        }
    )


def _hosted_token_verifier() -> DevelopmentHostedTokenVerifier:
    """Build a representative hosted token verifier for server tests.

    Returns:
        A development hosted token verifier seeded with one token.
    """
    return DevelopmentHostedTokenVerifier.from_mapping(
        {
            "dev-token": HostedVerifiedIdentity.model_validate(
                {
                    "tenant_id": "tenant-1",
                    "subject": "user-123",
                    "client_id": "portal-app",
                    "credential_id": "credential-1",
                }
            )
        }
    )


def _tenant_store() -> DevelopmentTenantStore:
    """Build a representative development tenant store for server tests.

    Returns:
        A development tenant store with one active tenant and credential.
    """
    return DevelopmentTenantStore(
        tenants=[
            TenantRecord.model_validate(
                {
                    "tenant_id": "tenant-1",
                    "tenant_slug": "tenant-one",
                    "display_name": "Tenant One",
                    "credential_id": "credential-1",
                    "status": TenantStatus.ACTIVE,
                }
            )
        ],
        credentials=[
            TenantCredentialRecord.model_validate(
                {
                    "credential_id": "credential-1",
                    "tenant_id": "tenant-1",
                    "auth_mode": AuthMode.API_KEY,
                    "api_key": "secret-key",
                    "status": TenantCredentialStatus.ACTIVE,
                }
            )
        ],
    )


def _noop_register_server_surface(*args: object, **kwargs: object) -> None:
    """Skip MCP surface registration for focused branch coverage tests."""
    del args, kwargs


async def _ok_route(_: object) -> PlainTextResponse:
    """Return a minimal OK response for Starlette route tests.

    Returns:
        A plain-text OK response.
    """
    return PlainTextResponse("ok")


def test_resolve_hosted_auth_requires_complete_configuration() -> None:
    """Hosted auth should reject partial configuration and build full verifier state."""
    assert _resolve_hosted_auth(
        hosted_auth=None,
        hosted_token_verifier=None,
        tenant_store=None,
    ) == (None, None)

    with pytest.raises(
        ValueError,
        match="hosted_auth, hosted_token_verifier, and tenant_store must be provided together.",
    ):
        _resolve_hosted_auth(
            hosted_auth=_hosted_auth_settings(),
            hosted_token_verifier=None,
            tenant_store=None,
        )

    resolved_auth_settings, resolved_token_verifier = _resolve_hosted_auth(
        hosted_auth=_hosted_auth_settings(),
        hosted_token_verifier=_hosted_token_verifier(),
        tenant_store=_tenant_store(),
    )
    assert resolved_auth_settings is not None
    assert resolved_token_verifier is not None


def test_resolve_local_tenant_settings_builds_defaults_when_settings_are_omitted(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Local tenant settings should fall back to composite defaults only when needed."""

    class FakeCompositeSettings:
        """Return one fixed tenant-settings payload for omitted local settings."""

        def tenant_settings(self) -> FollowUpBossTenantSettings:
            """Return credentialed local tenant settings."""
            return FollowUpBossTenantSettings.model_validate({"api_key": "bootstrap-key"})

    monkeypatch.setattr("followupboss_mcp.mcp_server.FollowUpBossSettings", FakeCompositeSettings)

    resolved_settings = _resolve_local_tenant_settings(None, client=None)

    assert resolved_settings is not None
    assert resolved_settings.api_key is not None
    assert resolved_settings.api_key.get_secret_value() == "bootstrap-key"
    assert (
        _resolve_local_tenant_settings(
            None,
            client=cast(FollowUpBossClientProtocol, object()),
        )
        is None
    )


def test_resolve_local_tenant_settings_and_runtime_defaults_handle_explicit_models() -> None:
    """Explicit settings models should be preserved or projected correctly."""
    composite_settings = FollowUpBossSettings.model_validate({"api_key": "local-key"})
    tenant_settings = FollowUpBossTenantSettings.model_validate({"api_key": "tenant-key"})
    runtime_defaults = FollowUpBossTenantRuntimeDefaults.model_validate(
        {"base_url": "https://api.example.com/v1/"}
    )

    resolved_from_composite = _resolve_local_tenant_settings(composite_settings, client=None)
    assert resolved_from_composite is not None
    assert resolved_from_composite.api_key is not None
    assert resolved_from_composite.api_key.get_secret_value() == "local-key"
    assert _resolve_local_tenant_settings(tenant_settings, client=None) is tenant_settings
    assert _resolve_local_tenant_settings(runtime_defaults, client=None) is None

    builtin_defaults = _resolve_tenant_runtime_defaults(None)
    assert builtin_defaults == FollowUpBossTenantRuntimeDefaults.builtin_defaults()
    projected_defaults = _resolve_tenant_runtime_defaults(tenant_settings)
    assert projected_defaults == tenant_settings.tenant_runtime_defaults()
    assert _resolve_tenant_runtime_defaults(runtime_defaults) is runtime_defaults


def test_transport_security_property_returns_configured_policy() -> None:
    """The public property should expose the exact configured transport policy."""
    transport_security = TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=["mcp.example.com"],
        allowed_origins=["https://mcp.example.com"],
    )
    server = FollowUpBossMCPServer("Test MCP")

    server.configure_streamable_http(
        host="0.0.0.0",
        port=9100,
        streamable_http_path="/tenant-mcp",
        json_response=True,
        transport_security=transport_security,
    )

    assert server.transport_security is transport_security


def test_run_applies_configured_streamable_http_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Streamable HTTP startup should pass every stored v2 transport option."""
    captured: list[tuple[str, dict[str, object]]] = []

    def fake_run(_: MCPServer, transport: str = "stdio", **kwargs: object) -> None:
        captured.append((transport, kwargs))

    monkeypatch.setattr(MCPServer, "run", fake_run)
    transport_security = TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=["mcp.example.com"],
        allowed_origins=["https://mcp.example.com"],
    )
    server = FollowUpBossMCPServer("Test MCP")
    server.configure_streamable_http(
        host="0.0.0.0",
        port=9100,
        streamable_http_path="/tenant-mcp",
        json_response=True,
        transport_security=transport_security,
    )

    server.run(transport="streamable-http")
    server.run(transport="stdio")

    assert captured == [
        (
            "streamable-http",
            {
                "host": "0.0.0.0",
                "port": 9100,
                "streamable_http_path": "/tenant-mcp",
                "json_response": True,
                "transport_security": transport_security,
            },
        ),
        ("stdio", {}),
    ]


def test_streamable_http_app_returns_base_app_without_hosted_rate_limiter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The hosted MCPServer subclass should return the base app when limiting is disabled."""
    base_app = Starlette(routes=[Route("/mcp", _ok_route)])

    monkeypatch.setattr(
        "followupboss_mcp.mcp_server.MCPServer.streamable_http_app",
        lambda self, **_: base_app,
    )

    server = FollowUpBossMCPServer(
        "Test MCP",
        log_level="INFO",
    )

    assert server.streamable_http_app() is base_app


def test_streamable_http_app_mounts_hosted_oauth_routes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Hosted OAuth routes should be added beside the streamable HTTP route."""
    base_app = Starlette(routes=[Route("/mcp", _ok_route)])
    oauth_route = Route("/oauth/token", _ok_route, methods=["POST"])

    class FakeHostedOAuthApplication:
        """Minimal OAuth route provider."""

        def routes(self) -> tuple[Route, ...]:
            """Return one OAuth route."""
            return (oauth_route,)

    monkeypatch.setattr(
        "followupboss_mcp.mcp_server.MCPServer.streamable_http_app",
        lambda self, **_: base_app,
    )

    server = FollowUpBossMCPServer(
        "Test MCP",
        log_level="INFO",
    )
    server._hosted_oauth_application = cast(HostedOAuthApplication, FakeHostedOAuthApplication())

    returned_app = server.streamable_http_app()

    assert returned_app is base_app
    assert {cast(Route, route).path for route in base_app.routes} == {"/mcp", "/oauth/token"}


def test_streamable_http_app_skips_duplicate_hosted_oauth_routes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Hosted OAuth route mounting should not duplicate existing paths."""
    existing_route = Route("/oauth/token", _ok_route, methods=["POST"])
    base_app = Starlette(routes=[existing_route])

    class FakeHostedOAuthApplication:
        """Minimal OAuth route provider with one duplicate path."""

        def routes(self) -> tuple[Route, ...]:
            """Return one duplicate OAuth route."""
            return (Route("/oauth/token", _ok_route, methods=["POST"]),)

    monkeypatch.setattr(
        "followupboss_mcp.mcp_server.MCPServer.streamable_http_app",
        lambda self, **_: base_app,
    )

    server = FollowUpBossMCPServer(
        "Test MCP",
        log_level="INFO",
    )
    server._hosted_oauth_application = cast(HostedOAuthApplication, FakeHostedOAuthApplication())

    server.streamable_http_app()

    assert base_app.routes == [existing_route]


def test_streamable_http_app_leaves_non_matching_routes_unwrapped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Hosted rate limiting should only wrap the configured streamable HTTP route."""
    base_app = Starlette(routes=[Route("/other", _ok_route)])

    monkeypatch.setattr(
        "followupboss_mcp.mcp_server.MCPServer.streamable_http_app",
        lambda self, **_: base_app,
    )

    server = FollowUpBossMCPServer(
        "Test MCP",
        log_level="INFO",
    )
    _, token_verifier = _resolve_hosted_auth(
        hosted_auth=_hosted_auth_settings(),
        hosted_token_verifier=_hosted_token_verifier(),
        tenant_store=_tenant_store(),
    )
    assert token_verifier is not None
    server._hosted_rate_limiter = HostedEndpointRateLimiter()
    server._token_verifier = token_verifier

    returned_app = server.streamable_http_app()
    route = cast(Route, base_app.routes[0])

    assert returned_app is base_app
    assert not isinstance(route.app, HostedRateLimitMiddleware)


def test_create_server_uses_explicit_server_settings_and_local_single_tenant_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Explicit server settings should be honored for local single-tenant startup."""
    monkeypatch.setattr(
        "followupboss_mcp.mcp_server.register_server_surface",
        _noop_register_server_surface,
    )

    server = create_server(
        FollowUpBossSettings.model_validate({"api_key": "local-key"}),
        server_settings=FollowUpBossServerSettings.model_validate(
            {
                "host": "0.0.0.0",
                "port": 9100,
                "streamable_http_path": "/tenant",
                "log_level": "debug",
            }
        ),
    )

    assert server is not None
    assert server._hosted_rate_limiter is None


def test_create_server_requires_tenant_store_when_hosted_auth_resolution_is_forced(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Hosted server creation should fail closed if tenant resolution is unavailable."""
    monkeypatch.setattr(
        "followupboss_mcp.mcp_server._resolve_hosted_auth",
        lambda **_: (
            AuthSettings.model_validate(
                {
                    "issuer_url": "https://issuer.example.com",
                    "resource_server_url": "https://mcp.example.com/mcp",
                }
            ),
            object(),
        ),
    )

    with pytest.raises(ValueError, match="tenant_store is required when hosted auth is enabled."):
        create_server()


def test_create_server_rejects_injected_client_when_hosted_auth_is_enabled() -> None:
    """Hosted server creation should reject shared clients that bypass tenant auth."""
    with pytest.raises(ValueError, match="client cannot be provided when hosted auth is enabled."):
        create_server(
            hosted_auth=_hosted_auth_settings(),
            hosted_token_verifier=_hosted_token_verifier(),
            tenant_store=_tenant_store(),
            client=cast(FollowUpBossClientProtocol, object()),
        )


def test_create_server_requires_credentialed_local_settings_without_hosted_auth() -> None:
    """Local startup should reject credential-free runtime defaults when no client is injected."""
    with pytest.raises(
        ValueError,
        match=(
            "Credentialed tenant settings are required when hosted auth is disabled "
            "and no client is injected."
        ),
    ):
        create_server(FollowUpBossTenantRuntimeDefaults.model_validate({}))


@pytest.mark.asyncio
async def test_create_server_hosted_lifespan_allows_no_shared_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Hosted runtime mode should complete lifespan shutdown even without a shared client."""
    monkeypatch.setattr(
        "followupboss_mcp.mcp_server.register_server_surface",
        _noop_register_server_surface,
    )

    server = create_server(
        hosted_auth=_hosted_auth_settings(),
        hosted_token_verifier=_hosted_token_verifier(),
        tenant_store=_tenant_store(),
    )

    async with server._lowlevel_server.lifespan(server._lowlevel_server):
        assert server._hosted_rate_limiter is not None


@pytest.mark.asyncio
async def test_create_server_hosted_lifespan_closes_rate_limiter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Hosted lifespan shutdown should close an injected hosted rate limiter."""

    class RecordingRateLimiter(HostedEndpointRateLimiter):
        """Hosted rate limiter stub that records whether `aclose()` was called."""

        def __init__(self) -> None:
            super().__init__()
            self.closed = False

        async def aclose(self) -> None:
            self.closed = True

    monkeypatch.setattr(
        "followupboss_mcp.mcp_server.register_server_surface",
        _noop_register_server_surface,
    )
    rate_limiter = RecordingRateLimiter()
    server = create_server(
        hosted_auth=_hosted_auth_settings(),
        hosted_token_verifier=_hosted_token_verifier(),
        tenant_store=_tenant_store(),
        hosted_rate_limiter=rate_limiter,
    )

    async with server._lowlevel_server.lifespan(server._lowlevel_server):
        assert rate_limiter.closed is False
    assert rate_limiter.closed is True


@pytest.mark.asyncio
async def test_create_server_hosted_lifespan_closes_oauth_application(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Hosted lifespan shutdown should close injected OAuth route providers."""

    class RecordingOAuthApplication:
        """OAuth route provider that records shutdown."""

        def __init__(self) -> None:
            self.closed = False

        def routes(self) -> tuple[Route, ...]:
            """Return no routes for this focused lifespan test."""
            return ()

        async def aclose(self) -> None:
            """Record close calls."""
            self.closed = True

    monkeypatch.setattr(
        "followupboss_mcp.mcp_server.register_server_surface",
        _noop_register_server_surface,
    )
    oauth_application = RecordingOAuthApplication()
    server = create_server(
        hosted_auth=_hosted_auth_settings(),
        hosted_token_verifier=_hosted_token_verifier(),
        tenant_store=_tenant_store(),
        hosted_oauth_application=cast(HostedOAuthApplication, oauth_application),
    )

    async with server._lowlevel_server.lifespan(server._lowlevel_server):
        assert oauth_application.closed is False
    assert oauth_application.closed is True


@pytest.mark.asyncio
async def test_create_server_hosted_lifespan_opens_and_closes_managed_resources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Hosted lifespan should open managed resources and close them in reverse order."""

    class RecordingRateLimiter(HostedEndpointRateLimiter):
        """Hosted rate limiter stub that records whether `aclose()` was called."""

        def __init__(self) -> None:
            super().__init__()
            self.closed = False

        async def aclose(self) -> None:
            """Record hosted rate limiter shutdown."""
            self.closed = True

    class RecordingResource:
        """Async managed resource stub that records open and close ordering."""

        def __init__(self, name: str, events: list[str]) -> None:
            """Initialize the recording resource.

            Args:
                name: The resource label recorded in lifecycle events.
                events: Shared lifecycle event log.
            """
            self._events = events
            self._name = name

        async def open(self) -> None:
            """Record resource startup."""
            self._events.append(f"open:{self._name}")

        async def aclose(self) -> None:
            """Record resource shutdown."""
            self._events.append(f"close:{self._name}")

    monkeypatch.setattr(
        "followupboss_mcp.mcp_server.register_server_surface",
        _noop_register_server_surface,
    )
    events: list[str] = []
    rate_limiter = RecordingRateLimiter()
    resources = (
        RecordingResource("first", events),
        RecordingResource("second", events),
    )
    server = create_server(
        hosted_auth=_hosted_auth_settings(),
        hosted_token_verifier=_hosted_token_verifier(),
        tenant_store=_tenant_store(),
        hosted_rate_limiter=rate_limiter,
        managed_resources=resources,
    )

    async with server._lowlevel_server.lifespan(server._lowlevel_server):
        assert events == ["open:first", "open:second"]
        assert rate_limiter.closed is False
    assert events == [
        "open:first",
        "open:second",
        "close:second",
        "close:first",
    ]
    assert rate_limiter.closed is True


@pytest.mark.asyncio
async def test_streamable_http_application_owns_shared_resource_lifecycle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The v2 application lifespan should own process-wide hosted resources once."""

    class RecordingResource:
        """Async managed resource that records application lifecycle events."""

        def __init__(self, events: list[str]) -> None:
            self._events = events

        async def open(self) -> None:
            """Record process startup."""
            self._events.append("open")

        async def aclose(self) -> None:
            """Record process shutdown."""
            self._events.append("close")

    monkeypatch.setattr(
        "followupboss_mcp.mcp_server.register_server_surface",
        _noop_register_server_surface,
    )
    events: list[str] = []
    server = create_server(
        hosted_auth=_hosted_auth_settings(),
        hosted_token_verifier=_hosted_token_verifier(),
        tenant_store=_tenant_store(),
        managed_resources=(RecordingResource(events),),
    )
    app = server.streamable_http_app()

    async with app.router.lifespan_context(app):
        assert events == ["open"]

    assert events == ["open", "close"]


@pytest.mark.asyncio
async def test_create_server_local_lifespan_skips_rate_limiter_shutdown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Local lifespan should still open and close managed resources without a hosted limiter."""

    class RecordingClient:
        """Minimal client stub that records shutdown."""

        def __init__(self) -> None:
            """Initialize the recording client."""
            self.closed = False

        async def aclose(self) -> None:
            """Record client shutdown."""
            self.closed = True

    class RecordingResource:
        """Async managed resource stub that records open and close ordering."""

        def __init__(self, name: str, events: list[str]) -> None:
            """Initialize the recording resource.

            Args:
                name: The resource label recorded in lifecycle events.
                events: Shared lifecycle event log.
            """
            self._events = events
            self._name = name

        async def open(self) -> None:
            """Record resource startup."""
            self._events.append(f"open:{self._name}")

        async def aclose(self) -> None:
            """Record resource shutdown."""
            self._events.append(f"close:{self._name}")

    monkeypatch.setattr(
        "followupboss_mcp.mcp_server.register_server_surface",
        _noop_register_server_surface,
    )
    events: list[str] = []
    client = RecordingClient()
    resources = (RecordingResource("only", events),)
    server = create_server(
        client=cast(FollowUpBossClientProtocol, client),
        managed_resources=resources,
    )

    async with server._lowlevel_server.lifespan(server._lowlevel_server):
        assert events == ["open:only"]
        assert client.closed is False
    assert events == ["open:only", "close:only"]
    assert client.closed is True
