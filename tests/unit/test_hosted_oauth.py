"""Unit tests for hosted OAuth authorization-server helpers."""

from __future__ import annotations

import base64
import hashlib
from collections.abc import Mapping
from typing import Any, cast
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from pydantic import ValidationError
from starlette.applications import Starlette
from starlette.testclient import TestClient

import followupboss_mcp.hosted_oauth as hosted_oauth
from followupboss_mcp.hosted_oauth import (
    FollowUpBossOAuthClient,
    FollowUpBossOAuthIdentity,
    FollowUpBossOAuthTokenPayload,
    HostedOAuthAccessTokenMetadata,
    HostedOAuthApplication,
    HostedOAuthAuthorizationCode,
    HostedOAuthDynamicClient,
    HostedOAuthPendingAuthorization,
    HostedOAuthRefreshToken,
    HostedOAuthSettings,
    ProvisionedHostedTenant,
)
from followupboss_mcp.models.identity import IdentityResponse


def _settings() -> HostedOAuthSettings:
    """Build representative hosted OAuth settings."""
    return HostedOAuthSettings.model_validate(
        {
            "issuer_url": "https://mcp.example.com",
            "resource_server_url": "https://mcp.example.com/mcp",
            "required_scopes": "followupboss:mcp",
            "fub_client_id": "fub-client",
            "fub_client_secret": "fub-secret",
            "fub_callback_url": "https://mcp.example.com/oauth/follow-up-boss/callback",
            "fub_authorize_url": "https://fub.example.com/oauth/authorize",
            "fub_token_url": "https://fub.example.com/oauth/token",
            "fub_base_url": "https://api.followupboss.test/v1",
            "token_secret_prefix": "followupboss/staging/tenants/",
            "system_name": "The-Perry-Group",
            "system_key": "system-secret",
            "access_token_seconds": 60,
            "authorization_code_seconds": 60,
            "refresh_token_seconds": 120,
            "state_seconds": 60,
        }
    )


def _s256(verifier: str) -> str:
    """Return a PKCE S256 code challenge."""
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


class FakeOAuthStore:
    """In-memory hosted OAuth store for route tests."""

    def __init__(self) -> None:
        """Initialize empty in-memory stores."""
        self.clients: dict[str, HostedOAuthDynamicClient] = {}
        self.pending: dict[str, HostedOAuthPendingAuthorization] = {}
        self.consumed_pending_states: list[str] = []
        self.codes: dict[str, HostedOAuthAuthorizationCode] = {}
        self.access_tokens: list[HostedOAuthAccessTokenMetadata] = []
        self.refresh_tokens: dict[str, HostedOAuthRefreshToken] = {}
        self.revoked_refresh_tokens: list[str] = []
        self.closed = False

    async def save_client(self, client: HostedOAuthDynamicClient) -> None:
        """Persist OAuth client metadata."""
        self.clients[client.client_id] = client

    async def get_client(self, client_id: str) -> HostedOAuthDynamicClient | None:
        """Return OAuth client metadata."""
        return self.clients.get(client_id)

    async def save_pending_authorization(
        self,
        authorization: HostedOAuthPendingAuthorization,
    ) -> None:
        """Persist pending authorization state."""
        self.pending[authorization.fub_state] = authorization

    async def consume_pending_authorization(
        self,
        fub_state: str,
    ) -> HostedOAuthPendingAuthorization | None:
        """Consume pending authorization state."""
        self.consumed_pending_states.append(fub_state)
        return self.pending.pop(fub_state, None)

    async def save_authorization_code(self, code: HostedOAuthAuthorizationCode) -> None:
        """Persist an authorization code."""
        self.codes[code.code_hash] = code

    async def consume_authorization_code(
        self,
        code_hash: str,
    ) -> HostedOAuthAuthorizationCode | None:
        """Consume an authorization code."""
        return self.codes.pop(code_hash, None)

    async def save_access_token(self, token: HostedOAuthAccessTokenMetadata) -> None:
        """Persist access-token metadata."""
        self.access_tokens.append(token)

    async def save_refresh_token(self, token: HostedOAuthRefreshToken) -> None:
        """Persist refresh-token metadata."""
        self.refresh_tokens[token.token_hash] = token

    async def get_refresh_token(self, token_hash: str) -> HostedOAuthRefreshToken | None:
        """Return refresh-token metadata."""
        return self.refresh_tokens.get(token_hash)

    async def revoke_refresh_token(self, token_hash: str, *, revoked_at: int) -> None:
        """Record refresh-token revocation."""
        self.revoked_refresh_tokens.append(f"{token_hash}:{revoked_at}")
        token = self.refresh_tokens[token_hash]
        self.refresh_tokens[token_hash] = token.model_copy(update={"revoked_at": revoked_at})

    async def aclose(self) -> None:
        """Mark the fake store as closed."""
        self.closed = True


class FakeTenantProvisioner:
    """Tenant provisioner stub for OAuth route tests."""

    def __init__(self) -> None:
        """Initialize the provisioner stub."""
        self.calls: list[tuple[FollowUpBossOAuthIdentity, FollowUpBossOAuthTokenPayload]] = []
        self.provision_error: Exception | None = None
        self.closed = False

    async def provision_tenant(
        self,
        *,
        identity: FollowUpBossOAuthIdentity,
        token_payload: FollowUpBossOAuthTokenPayload,
    ) -> ProvisionedHostedTenant:
        """Return a provisioned tenant derived from the FUB identity."""
        if self.provision_error is not None:
            raise self.provision_error
        self.calls.append((identity, token_payload))
        return ProvisionedHostedTenant.model_validate(
            {
                "tenant_id": identity.tenant_id,
                "credential_id": identity.credential_id,
                "subject": identity.subject,
            }
        )

    async def aclose(self) -> None:
        """Mark the fake provisioner as closed."""
        self.closed = True


class FakeFubOAuthClient:
    """Follow Up Boss OAuth client stub for route tests."""

    def __init__(self) -> None:
        """Initialize the fake FUB OAuth client."""
        self.exchange_error: Exception | None = None
        self.identity_error: Exception | None = None
        self.closed = False

    def build_authorize_url(self, *, fub_state: str) -> str:
        """Return a fake FUB authorize URL."""
        return f"https://fub.example.com/oauth/authorize?state={fub_state}"

    async def exchange_code(
        self,
        *,
        auth_code: str,
        fub_state: str,
    ) -> FollowUpBossOAuthTokenPayload:
        """Return a fake FUB token payload."""
        del fub_state
        if self.exchange_error is not None:
            raise self.exchange_error
        return FollowUpBossOAuthTokenPayload.model_validate(
            {
                "access_token": f"fub-access-{auth_code}",
                "refresh_token": "fub-refresh",
                "expires_in": 3600,
            }
        )

    async def get_identity(self, *, access_token: str) -> FollowUpBossOAuthIdentity:
        """Return fake FUB identity metadata."""
        if self.identity_error is not None:
            raise self.identity_error
        assert access_token.startswith("fub-access-")
        return FollowUpBossOAuthIdentity.model_validate(
            {
                "account_id": "1746230763",
                "account_name": "j-26",
                "user_id": "456",
                "user_email": "agent@example.com",
                "user_name": "Agent Example",
            }
        )

    async def aclose(self) -> None:
        """Mark the fake FUB client as closed."""
        self.closed = True


def _app(
    *,
    store: FakeOAuthStore | None = None,
    provisioner: FakeTenantProvisioner | None = None,
    fub_client: FakeFubOAuthClient | None = None,
    now: int = 1000,
) -> tuple[TestClient, FakeOAuthStore, FakeTenantProvisioner, FakeFubOAuthClient]:
    """Build a TestClient around the hosted OAuth routes."""
    resolved_store = store or FakeOAuthStore()
    resolved_provisioner = provisioner or FakeTenantProvisioner()
    resolved_fub_client = fub_client or FakeFubOAuthClient()
    oauth = HostedOAuthApplication(
        settings=_settings(),
        store=resolved_store,
        tenant_provisioner=resolved_provisioner,
        fub_client=cast(Any, resolved_fub_client),
        time_provider=lambda: now,
    )
    return (
        TestClient(Starlette(routes=list(oauth.routes()))),
        resolved_store,
        resolved_provisioner,
        resolved_fub_client,
    )


def test_settings_and_metadata_validation() -> None:
    """Normalize settings and expose OAuth metadata."""
    settings = _settings()
    assert settings.issuer == "https://mcp.example.com"
    assert settings.resource_server == "https://mcp.example.com/mcp"
    assert settings.scope_string == "followupboss:mcp"
    assert settings.endpoint_url("/oauth/token") == "https://mcp.example.com/oauth/token"

    normalized_settings = HostedOAuthSettings.model_validate(
        {
            **settings.model_dump(),
            "issuer_url": "mcp.example.com/",
            "resource_server_url": "mcp.example.com/mcp/",
            "fub_authorize_url": "app.followupboss.com/oauth/authorize/",
            "fub_token_url": "app.followupboss.com/oauth/token/",
            "fub_callback_url": "mcp.example.com/oauth/follow-up-boss/callback/",
            "fub_base_url": "api.followupboss.com/v1/",
        }
    )
    assert normalized_settings.issuer == "https://mcp.example.com"
    assert normalized_settings.resource_server == "https://mcp.example.com/mcp"
    assert str(normalized_settings.fub_authorize_url) == (
        "https://app.followupboss.com/oauth/authorize"
    )
    assert str(normalized_settings.fub_token_url) == "https://app.followupboss.com/oauth/token"
    assert str(normalized_settings.fub_callback_url) == (
        "https://mcp.example.com/oauth/follow-up-boss/callback"
    )
    assert str(normalized_settings.fub_base_url) == "https://api.followupboss.com/v1"

    with pytest.raises(ValidationError):
        HostedOAuthSettings.model_validate(
            {
                **settings.model_dump(),
                "fub_client_id": " ",
            }
        )
    with pytest.raises(ValidationError):
        HostedOAuthSettings.model_validate(
            {
                **settings.model_dump(),
                "access_token_seconds": 0,
            }
        )
    with pytest.raises(ValidationError, match="fragment"):
        HostedOAuthSettings.model_validate(
            {
                **settings.model_dump(),
                "fub_authorize_url": "https://app.followupboss.com/oauth/authorize#login",
            }
        )
    with pytest.raises(ValidationError, match="query string"):
        HostedOAuthSettings.model_validate(
            {
                **settings.model_dump(),
                "fub_token_url": "https://app.followupboss.com/oauth/token?tenant=one",
            }
        )
    with pytest.raises(ValidationError, match="whitespace"):
        HostedOAuthSettings.model_validate(
            {
                **settings.model_dump(),
                "resource_server_url": "https://mcp.example.com/bad path",
            }
        )
    assert hosted_oauth._normalize_scopes(object()).__class__ is object
    assert hosted_oauth._normalize_scopes(("scope-a", 1)) == ("scope-a", 1)
    assert hosted_oauth._normalize_scopes("scope-a scope-a") == ("scope-a",)
    redirect = hosted_oauth._redirect_error(
        "http://127.0.0.1/callback",
        "invalid_request",
        state=None,
    )
    assert redirect.status_code == 302

    client, _, _, _ = _app()
    response = client.get("/.well-known/oauth-authorization-server")
    assert response.status_code == 200
    payload = response.json()
    assert payload["issuer"] == "https://mcp.example.com"
    assert payload["registration_endpoint"] == "https://mcp.example.com/oauth/register"
    assert payload["logo_uri"] == "https://mcp.example.com/assets/follow-up-boss-logo.png"

    logo_response = client.get("/assets/follow-up-boss-logo.png")
    assert logo_response.status_code == 200
    assert logo_response.headers["content-type"] == "image/png"
    assert logo_response.headers["cache-control"] == "public, max-age=604800, immutable"
    assert logo_response.content.startswith(b"\x89PNG")

    favicon_response = client.get("/favicon.ico")
    assert favicon_response.status_code == 200
    assert favicon_response.headers["content-type"] == "image/x-icon"
    assert favicon_response.headers["cache-control"] == "public, max-age=300, must-revalidate"
    assert favicon_response.content.startswith(b"\x00\x00\x01\x00")


def test_callback_configuration_mismatch_reports_to_sentry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Callback URL mismatches should fail fast with a Sentry message."""
    captured_messages: list[
        tuple[str, Mapping[str, object] | None, Mapping[str, object] | None]
    ] = []

    def fake_capture_sentry_message(
        message: str,
        *,
        level: str = "error",
        tags: Mapping[str, object] | None = None,
        extras: Mapping[str, object] | None = None,
    ) -> str:
        """Record captured callback configuration messages."""
        assert level == "error"
        captured_messages.append((message, tags, extras))
        return "event-id"

    monkeypatch.setattr(hosted_oauth, "capture_sentry_message", fake_capture_sentry_message)
    settings = _settings().model_copy(
        update={"fub_callback_url": "https://other.example.com/oauth/follow-up-boss/callback"}
    )

    with pytest.raises(ValueError, match="fub_callback_url must match"):
        hosted_oauth.validate_fub_callback_configuration(settings)

    assert captured_messages == [
        (
            "hosted_oauth_callback_url_mismatch",
            {
                "route": "/oauth/follow-up-boss/callback",
                "oauth_phase": "configuration",
            },
            {
                "expected_callback_url": "https://mcp.example.com/oauth/follow-up-boss/callback",
                "actual_callback_url": "https://other.example.com/oauth/follow-up-boss/callback",
            },
        )
    ]


def test_dynamic_client_validation_rejects_bad_redirect_shapes() -> None:
    """Dynamic client validation should reject invalid redirect metadata."""
    client = HostedOAuthDynamicClient.model_validate(
        {
            "client_id": "client-1",
            "redirect_uris": [
                "http://127.0.0.1/callback",
                "http://127.0.0.1/callback",
            ],
        }
    )
    assert client.redirect_uris == ("http://127.0.0.1/callback",)

    with pytest.raises(ValidationError):
        HostedOAuthDynamicClient.model_validate(
            {
                "client_id": "client-1",
                "redirect_uris": "http://127.0.0.1/callback",
            }
        )
    with pytest.raises(ValidationError):
        HostedOAuthDynamicClient.model_validate(
            {
                "client_id": "client-1",
                "redirect_uris": ["http://127.0.0.1/callback", 1],
            }
        )


def test_identity_derivation_requires_account_and_user_ids() -> None:
    """FUB identity projection should require stable account and user ids."""
    with pytest.raises(ValueError, match="account id"):
        FollowUpBossOAuthIdentity.from_identity_response(IdentityResponse.model_validate({}))
    with pytest.raises(ValueError, match="user id"):
        FollowUpBossOAuthIdentity.from_identity_response(
            IdentityResponse.model_validate({"accountId": 1})
        )


def test_register_authorize_callback_token_and_refresh_flow() -> None:
    """Complete the Cursor-to-FUB delegated OAuth flow."""
    client, store, provisioner, _fub_client = _app()

    registration = client.post(
        "/oauth/register",
        json={
            "client_name": "Cursor",
            "redirect_uris": ["http://127.0.0.1:3344/callback"],
            "scope": "followupboss:mcp",
        },
    )
    assert registration.status_code == 201
    client_id = registration.json()["client_id"]
    verifier = "verifier-123"
    authorize = client.get(
        "/oauth/authorize",
        params={
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": "http://127.0.0.1:3344/callback",
            "scope": "followupboss:mcp",
            "state": "cursor-state",
            "code_challenge": _s256(verifier),
            "code_challenge_method": "S256",
        },
        follow_redirects=False,
    )
    assert authorize.status_code == 307
    fub_state = parse_qs(urlparse(authorize.headers["location"]).query)["state"][0]
    assert fub_state in store.pending

    callback = client.get(
        "/oauth/follow-up-boss/callback",
        params={"state": fub_state, "response": "approved", "code": "fub-code"},
        follow_redirects=False,
    )
    assert callback.status_code == 307
    callback_query = parse_qs(urlparse(callback.headers["location"]).query)
    assert callback_query["state"] == ["cursor-state"]
    mcp_code = callback_query["code"][0]
    assert provisioner.calls[0][0].account_id == "1746230763"

    token = client.post(
        "/oauth/token",
        data={
            "grant_type": "authorization_code",
            "code": mcp_code,
            "client_id": client_id,
            "redirect_uri": "http://127.0.0.1:3344/callback",
            "code_verifier": verifier,
        },
    )
    assert token.status_code == 200
    token_payload = token.json()
    assert token_payload["token_type"] == "Bearer"
    assert token_payload["scope"] == "followupboss:mcp"
    assert len(store.access_tokens) == 1

    refresh = client.post(
        "/oauth/token",
        data={
            "grant_type": "refresh_token",
            "refresh_token": token_payload["refresh_token"],
            "client_id": client_id,
        },
    )
    assert refresh.status_code == 200
    assert refresh.json()["access_token"].startswith("mcp_at_")
    assert store.revoked_refresh_tokens


@pytest.mark.asyncio
async def test_oauth_application_closes_collaborators() -> None:
    """OAuth route provider should close the FUB client, store, and provisioner."""
    store = FakeOAuthStore()
    provisioner = FakeTenantProvisioner()
    fub_client = FakeFubOAuthClient()
    oauth = HostedOAuthApplication(
        settings=_settings(),
        store=store,
        tenant_provisioner=provisioner,
        fub_client=cast(Any, fub_client),
    )

    await oauth.aclose()

    assert store.closed is True
    assert provisioner.closed is True
    assert fub_client.closed is True

    class BareStore:
        """Store without an aclose hook."""

    class BareProvisioner:
        """Provisioner without an aclose hook."""

    bare_oauth = HostedOAuthApplication(
        settings=_settings(),
        store=cast(Any, BareStore()),
        tenant_provisioner=cast(Any, BareProvisioner()),
        fub_client=cast(Any, FakeFubOAuthClient()),
    )
    await bare_oauth.aclose()


def test_register_client_rejects_invalid_metadata() -> None:
    """Registration endpoint should reject malformed client metadata."""
    client, _, _, _ = _app()
    response = client.post("/oauth/register", json={"redirect_uris": "not-a-list"})
    assert response.status_code == 400
    assert response.json()["error"] == "invalid_client_metadata"


@pytest.mark.parametrize(
    ("params", "expected_error"),
    [
        ({}, "unsupported_response_type"),
        ({"response_type": "code"}, "invalid_request"),
        (
            {
                "response_type": "code",
                "code_challenge": "challenge",
                "code_challenge_method": "unknown",
            },
            "invalid_request",
        ),
    ],
)
def test_authorize_rejects_invalid_requests(
    params: Mapping[str, str],
    expected_error: str,
) -> None:
    """Reject malformed authorize requests before redirecting to FUB."""
    client, _, _, _ = _app()
    response = client.get("/oauth/authorize", params=params)
    assert response.status_code == 400
    assert response.json()["error"] == expected_error


def test_authorize_rejects_unknown_client_and_bad_redirect_or_scope() -> None:
    """Reject unregistered clients, redirects, and insufficient scopes."""
    client, store, _, _ = _app()
    store.clients["client-1"] = HostedOAuthDynamicClient.model_validate(
        {
            "client_id": "client-1",
            "client_name": "Cursor",
            "redirect_uris": ["http://127.0.0.1/callback"],
            "scope": "followupboss:mcp",
        }
    )
    base_params = {
        "response_type": "code",
        "code_challenge": "challenge",
        "client_id": "missing",
        "redirect_uri": "http://127.0.0.1/callback",
    }
    assert client.get("/oauth/authorize", params=base_params).json()["error"] == "invalid_client"

    bad_redirect = {**base_params, "client_id": "client-1", "redirect_uri": "http://evil.test"}
    assert client.get("/oauth/authorize", params=bad_redirect).json()["error"] == "invalid_request"

    bad_scope = {**base_params, "client_id": "client-1", "scope": "other:scope"}
    response = client.get("/oauth/authorize", params=bad_scope, follow_redirects=False)
    assert response.status_code == 302
    assert parse_qs(urlparse(response.headers["location"]).query)["error"] == ["invalid_scope"]


def test_authorize_uses_default_scopes_when_scope_is_omitted() -> None:
    """Authorize should use required scopes when the client omits `scope`."""
    client, store, _, _ = _app()
    store.clients["client-1"] = HostedOAuthDynamicClient.model_validate(
        {
            "client_id": "client-1",
            "client_name": "Cursor",
            "redirect_uris": ["http://127.0.0.1/callback"],
            "scope": "followupboss:mcp",
        }
    )

    response = client.get(
        "/oauth/authorize",
        params={
            "response_type": "code",
            "code_challenge": "plain-verifier",
            "client_id": "client-1",
            "redirect_uri": "http://127.0.0.1/callback",
        },
        follow_redirects=False,
    )

    assert response.status_code == 307
    pending = next(iter(store.pending.values()))
    assert pending.scopes == ("followupboss:mcp",)


@pytest.mark.parametrize(
    ("query", "status_code", "expected"),
    [
        ({}, 400, "Missing OAuth state."),
        ({"state": "missing"}, 400, "Invalid or expired OAuth state."),
        ({"state": "state-1", "response": "denied"}, 302, "access_denied"),
        ({"state": "state-1", "response": "approved"}, 302, "invalid_request"),
    ],
)
def test_callback_rejects_invalid_or_denied_fub_results(
    query: Mapping[str, str],
    status_code: int,
    expected: str,
) -> None:
    """Handle invalid state, denied consent, and missing FUB auth codes."""
    client, store, _, _ = _app()
    store.pending["state-1"] = HostedOAuthPendingAuthorization.model_validate(
        {
            "fub_state": "state-1",
            "client_state": "cursor-state",
            "client_id": "client-1",
            "redirect_uri": "http://127.0.0.1/callback",
            "code_challenge": "challenge",
            "code_challenge_method": "plain",
            "scopes": "followupboss:mcp",
            "expires_at": 1060,
        }
    )
    response = client.get("/oauth/follow-up-boss/callback", params=query, follow_redirects=False)
    assert response.status_code == status_code
    if status_code == 400:
        assert response.text == expected
        if "state" not in query:
            assert store.consumed_pending_states == []
    else:
        assert parse_qs(urlparse(response.headers["location"]).query)["error"] == [expected]


def test_callback_rejects_expired_state_and_exchange_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Redirect OAuth errors for expired state and FUB exchange failures."""
    captured: list[tuple[Exception, Mapping[str, object] | None, Mapping[str, object] | None]] = []

    def fake_capture_sentry_exception(
        exc: Exception,
        *,
        tags: Mapping[str, object] | None = None,
        extras: Mapping[str, object] | None = None,
    ) -> str:
        """Record captured callback exceptions."""
        captured.append((exc, tags, extras))
        return "event-id"

    monkeypatch.setattr(hosted_oauth, "capture_sentry_exception", fake_capture_sentry_exception)
    client, store, _, fub_client = _app(now=2000)
    store.pending["expired"] = HostedOAuthPendingAuthorization.model_validate(
        {
            "fub_state": "expired",
            "client_id": "client-1",
            "redirect_uri": "http://127.0.0.1/callback",
            "code_challenge": "challenge",
            "code_challenge_method": "plain",
            "scopes": "followupboss:mcp",
            "expires_at": 1000,
        }
    )
    expired = client.get(
        "/oauth/follow-up-boss/callback",
        params={"state": "expired", "response": "approved", "code": "fub-code"},
        follow_redirects=False,
    )
    assert parse_qs(urlparse(expired.headers["location"]).query)["error"] == ["invalid_request"]

    fub_client.exchange_error = RuntimeError("boom")
    store.pending["state-2"] = HostedOAuthPendingAuthorization.model_validate(
        {
            "fub_state": "state-2",
            "client_id": "client-1",
            "redirect_uri": "http://127.0.0.1/callback",
            "code_challenge": "challenge",
            "code_challenge_method": "plain",
            "scopes": "followupboss:mcp",
            "expires_at": 2060,
        }
    )
    failed = client.get(
        "/oauth/follow-up-boss/callback",
        params={"state": "state-2", "response": "approved", "code": "fub-code"},
        follow_redirects=False,
    )
    assert parse_qs(urlparse(failed.headers["location"]).query)["error"] == ["server_error"]
    assert len(captured) == 1
    assert isinstance(captured[0][0], RuntimeError)
    assert captured[0][1] == {
        "route": "/oauth/follow-up-boss/callback",
        "oauth_phase": "fub_token_exchange",
    }
    assert captured[0][2] == {
        "client_id": "client-1",
        "has_client_state": False,
        "requested_scopes": ["followupboss:mcp"],
        "resource": None,
    }


def test_callback_captures_identity_and_provisioning_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Redirect and report operational callback failures after token exchange."""
    captured_phases: list[str] = []

    def fake_capture_sentry_exception(
        exc: Exception,
        *,
        tags: Mapping[str, object] | None = None,
        extras: Mapping[str, object] | None = None,
    ) -> str:
        """Record captured callback phases."""
        del exc, extras
        assert tags is not None
        captured_phases.append(str(tags["oauth_phase"]))
        return "event-id"

    monkeypatch.setattr(hosted_oauth, "capture_sentry_exception", fake_capture_sentry_exception)

    client, store, _, fub_client = _app(now=2000)
    fub_client.identity_error = RuntimeError("identity unavailable")
    store.pending["state-identity"] = HostedOAuthPendingAuthorization.model_validate(
        {
            "fub_state": "state-identity",
            "client_id": "client-1",
            "redirect_uri": "http://127.0.0.1/callback",
            "code_challenge": "challenge",
            "code_challenge_method": "plain",
            "scopes": "followupboss:mcp",
            "expires_at": 2060,
        }
    )

    identity_failed = client.get(
        "/oauth/follow-up-boss/callback",
        params={"state": "state-identity", "response": "approved", "code": "fub-code"},
        follow_redirects=False,
    )
    assert parse_qs(urlparse(identity_failed.headers["location"]).query)["error"] == [
        "server_error"
    ]

    client, store, provisioner, _ = _app(now=2000)
    provisioner.provision_error = RuntimeError("provisioning unavailable")
    store.pending["state-provision"] = HostedOAuthPendingAuthorization.model_validate(
        {
            "fub_state": "state-provision",
            "client_id": "client-1",
            "redirect_uri": "http://127.0.0.1/callback",
            "code_challenge": "challenge",
            "code_challenge_method": "plain",
            "scopes": "followupboss:mcp",
            "expires_at": 2060,
        }
    )

    provision_failed = client.get(
        "/oauth/follow-up-boss/callback",
        params={"state": "state-provision", "response": "approved", "code": "fub-code"},
        follow_redirects=False,
    )
    assert parse_qs(urlparse(provision_failed.headers["location"]).query)["error"] == [
        "server_error"
    ]
    assert captured_phases == ["fub_identity_lookup", "tenant_provisioning"]


def test_callback_success_without_client_state_preserves_existing_query() -> None:
    """Successful callback should handle clients that omit state and use query redirects."""
    client, store, _, _ = _app()
    store.pending["state-3"] = HostedOAuthPendingAuthorization.model_validate(
        {
            "fub_state": "state-3",
            "client_id": "client-1",
            "redirect_uri": "http://127.0.0.1/callback?existing=1",
            "code_challenge": "challenge",
            "code_challenge_method": "plain",
            "scopes": "followupboss:mcp",
            "expires_at": 1060,
        }
    )

    response = client.get(
        "/oauth/follow-up-boss/callback",
        params={"state": "state-3", "response": "approved", "code": "fub-code"},
        follow_redirects=False,
    )

    assert response.status_code == 307
    parsed = urlparse(response.headers["location"])
    query = parse_qs(parsed.query)
    assert query["existing"] == ["1"]
    assert "code" in query
    assert "state" not in query


def test_token_endpoint_rejects_invalid_grants() -> None:
    """Reject malformed authorization-code and refresh-token grants."""
    client, store, _, _ = _app(now=1000)
    assert client.post("/oauth/token", data={"grant_type": "nope"}).json()["error"] == (
        "unsupported_grant_type"
    )
    assert (
        client.post(
            "/oauth/token",
            data={"grant_type": "authorization_code", "code": "missing"},
        ).json()["error"]
        == "invalid_grant"
    )
    for data in (
        {"grant_type": "authorization_code"},
        {"grant_type": "authorization_code", "code": ""},
    ):
        response = client.post("/oauth/token", data=data)
        assert response.status_code == 400
        assert response.json()["error"] == "invalid_grant"

    store.codes["sha256:" + hashlib.sha256(b"code").hexdigest()] = (
        HostedOAuthAuthorizationCode.model_validate(
            {
                "code_hash": "sha256:" + hashlib.sha256(b"code").hexdigest(),
                "client_id": "client-1",
                "redirect_uri": "http://127.0.0.1/callback",
                "code_challenge": "verifier",
                "code_challenge_method": "plain",
                "scopes": "followupboss:mcp",
                "tenant_id": "tenant-1",
                "subject": "subject-1",
                "credential_id": "credential-1",
                "expires_at": 999,
            }
        )
    )
    assert (
        client.post(
            "/oauth/token",
            data={"grant_type": "authorization_code", "code": "code"},
        ).json()["error"]
        == "invalid_grant"
    )

    valid_record = HostedOAuthAuthorizationCode.model_validate(
        {
            "code_hash": "sha256:" + hashlib.sha256(b"code-client").hexdigest(),
            "client_id": "client-1",
            "redirect_uri": "http://127.0.0.1/callback",
            "code_challenge": "verifier",
            "code_challenge_method": "plain",
            "scopes": "followupboss:mcp",
            "tenant_id": "tenant-1",
            "subject": "subject-1",
            "credential_id": "credential-1",
            "expires_at": 1001,
        }
    )
    store.codes[valid_record.code_hash] = valid_record
    assert (
        client.post(
            "/oauth/token",
            data={
                "grant_type": "authorization_code",
                "code": "code-client",
                "client_id": "wrong-client",
                "redirect_uri": "http://127.0.0.1/callback",
                "code_verifier": "verifier",
            },
        ).json()["error"]
        == "invalid_grant"
    )

    redirect_record = valid_record.model_copy(
        update={"code_hash": "sha256:" + hashlib.sha256(b"code-redirect").hexdigest()}
    )
    store.codes[redirect_record.code_hash] = redirect_record
    assert (
        client.post(
            "/oauth/token",
            data={
                "grant_type": "authorization_code",
                "code": "code-redirect",
                "client_id": "client-1",
                "redirect_uri": "http://wrong/callback",
                "code_verifier": "verifier",
            },
        ).json()["error"]
        == "invalid_grant"
    )

    pkce_record = valid_record.model_copy(
        update={"code_hash": "sha256:" + hashlib.sha256(b"code-pkce").hexdigest()}
    )
    store.codes[pkce_record.code_hash] = pkce_record
    assert (
        client.post(
            "/oauth/token",
            data={
                "grant_type": "authorization_code",
                "code": "code-pkce",
                "client_id": "client-1",
                "redirect_uri": "http://127.0.0.1/callback",
                "code_verifier": "wrong-verifier",
            },
        ).json()["error"]
        == "invalid_grant"
    )

    store.refresh_tokens["refresh-hash"] = HostedOAuthRefreshToken.model_validate(
        {
            "token_hash": "refresh-hash",
            "tenant_id": "tenant-1",
            "subject": "subject-1",
            "client_id": "client-1",
            "scopes": "followupboss:mcp",
            "credential_id": "credential-1",
            "expires_at": 999,
        }
    )
    assert (
        client.post(
            "/oauth/token",
            data={
                "grant_type": "refresh_token",
                "refresh_token": "missing",
                "client_id": "client-1",
            },
        ).json()["error"]
        == "invalid_grant"
    )
    for data in (
        {"grant_type": "refresh_token"},
        {"grant_type": "refresh_token", "refresh_token": ""},
    ):
        response = client.post("/oauth/token", data=data)
        assert response.status_code == 400
        assert response.json()["error"] == "invalid_grant"

    for raw_refresh, updates in (
        ("expired-refresh", {"expires_at": 999}),
        ("client-refresh", {"expires_at": 1001, "client_id": "client-1"}),
        ("revoked-refresh", {"expires_at": 1001, "revoked_at": 1000}),
    ):
        token_hash = "sha256:" + hashlib.sha256(raw_refresh.encode("utf-8")).hexdigest()
        store.refresh_tokens[token_hash] = HostedOAuthRefreshToken.model_validate(
            {
                "token_hash": token_hash,
                "tenant_id": "tenant-1",
                "subject": "subject-1",
                "client_id": updates.get("client_id", "other-client"),
                "scopes": "followupboss:mcp",
                "credential_id": "credential-1",
                "expires_at": updates["expires_at"],
                "revoked_at": updates.get("revoked_at"),
            }
        )
        response = client.post(
            "/oauth/token",
            data={
                "grant_type": "refresh_token",
                "refresh_token": raw_refresh,
                "client_id": "wrong-client" if raw_refresh == "client-refresh" else "client-1",
            },
        )
        assert response.json()["error"] == "invalid_grant"


def test_pkce_helper_rejects_missing_or_unknown_methods() -> None:
    """PKCE helper should reject absent verifiers and unknown challenge methods."""
    assert hosted_oauth._verify_pkce(verifier="", challenge="challenge", method="plain") is False
    assert (
        hosted_oauth._verify_pkce(
            verifier="verifier",
            challenge="challenge",
            method="unknown",
        )
        is False
    )


@pytest.mark.asyncio
async def test_follow_up_boss_oauth_client_posts_and_reads_identity() -> None:
    """Use documented Follow Up Boss OAuth endpoints and bearer identity calls."""
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/oauth/token":
            return httpx.Response(
                200,
                json={
                    "access_token": "new-access",
                    "refresh_token": "new-refresh",
                    "expires_in": 3600,
                },
            )
        return httpx.Response(
            200,
            json={
                "account": {"id": 1746230763, "name": "j-26"},
                "user": {"id": 456, "email": "agent@example.com", "name": "Agent"},
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        oauth_client = FollowUpBossOAuthClient(_settings(), http_client=http_client)
        assert "response_type=auth_code" in oauth_client.build_authorize_url(fub_state="state-1")
        exchanged = await oauth_client.exchange_code(auth_code="code-1", fub_state="state-1")
        refreshed = await oauth_client.refresh_token(refresh_token="refresh-1")
        identity = await oauth_client.get_identity(access_token="access-1")
        await oauth_client.aclose()

    assert exchanged.access_token.get_secret_value() == "new-access"
    assert refreshed.refresh_token is not None
    assert identity.account_id == "1746230763"
    assert requests[0].headers["authorization"].startswith("Basic ")
    assert requests[2].headers["authorization"] == "Bearer access-1"
    assert requests[2].headers["x-system"] == "The-Perry-Group"
    assert requests[2].headers["x-system-key"] == "system-secret"


@pytest.mark.asyncio
async def test_follow_up_boss_oauth_client_lazy_client_without_system_headers() -> None:
    """Owned FUB OAuth clients should lazy-create and close their HTTP client."""
    settings = HostedOAuthSettings.model_validate(
        {
            **_settings().model_dump(),
            "system_name": None,
            "system_key": None,
        }
    )
    oauth_client = FollowUpBossOAuthClient(settings)
    created_client = oauth_client._client()
    assert created_client.is_closed is False
    await oauth_client.aclose()
    assert created_client.is_closed is True

    seen_headers: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen_headers.update(dict(request.headers))
        return httpx.Response(
            200,
            json={"accountId": 1746230763, "id": 456},
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        injected_client = FollowUpBossOAuthClient(settings, http_client=http_client)
        identity = await injected_client.get_identity(access_token="access-1")

    assert identity.subject == "fub-user-456"
    assert "x-system" not in seen_headers
    assert "x-system-key" not in seen_headers
