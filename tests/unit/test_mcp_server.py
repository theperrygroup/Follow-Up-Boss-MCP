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
from followupboss_mcp.hosted_rate_limits import HostedEndpointRateLimiter, HostedRateLimitMiddleware
from followupboss_mcp.http_client import FollowUpBossClientProtocol
from followupboss_mcp.mcp_server import (
    FollowUpBossFastMCP,
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


def test_streamable_http_app_returns_base_app_without_hosted_rate_limiter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The hosted FastMCP subclass should return the base app when limiting is disabled."""
    base_app = Starlette(routes=[Route("/mcp", _ok_route)])

    monkeypatch.setattr(
        "followupboss_mcp.mcp_server.FastMCP.streamable_http_app",
        lambda self: base_app,
    )

    server = FollowUpBossFastMCP(
        "Test MCP",
        host="127.0.0.1",
        port=8000,
        streamable_http_path="/mcp",
        json_response=True,
        log_level="INFO",
    )

    assert server.streamable_http_app() is base_app


def test_streamable_http_app_leaves_non_matching_routes_unwrapped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Hosted rate limiting should only wrap the configured streamable HTTP route."""
    base_app = Starlette(routes=[Route("/other", _ok_route)])

    monkeypatch.setattr(
        "followupboss_mcp.mcp_server.FastMCP.streamable_http_app",
        lambda self: base_app,
    )

    server = FollowUpBossFastMCP(
        "Test MCP",
        host="127.0.0.1",
        port=8000,
        streamable_http_path="/mcp",
        json_response=True,
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

    server = cast(
        FollowUpBossFastMCP,
        create_server(
            FollowUpBossSettings.model_validate({"api_key": "local-key"}),
            server_settings=FollowUpBossServerSettings.model_validate(
                {
                    "host": "0.0.0.0",
                    "port": 9100,
                    "streamable_http_path": "/tenant",
                    "log_level": "debug",
                }
            ),
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

    server = cast(
        FollowUpBossFastMCP,
        create_server(
            hosted_auth=_hosted_auth_settings(),
            hosted_token_verifier=_hosted_token_verifier(),
            tenant_store=_tenant_store(),
        ),
    )

    async with server._mcp_server.lifespan(server._mcp_server):
        assert server._hosted_rate_limiter is not None
