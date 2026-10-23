"""Exercise OAuth-issued credentials through the real hosted MCP HTTP surface.

Only external HTTP and persistence are replaced. No bearer token or tenant is
seeded: the public OAuth callback must create everything the MCP request needs.
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest
from bs4 import BeautifulSoup
from starlette.testclient import TestClient

from followupboss_mcp.auth import AuthMode
from followupboss_mcp.cimd import ClientIdMetadataDocumentFetcher
from followupboss_mcp.config import FollowUpBossTenantRuntimeDefaults, FollowUpBossTenantSettings
from followupboss_mcp.hosted_auth import HostedAuthSettings, HostedVerifiedIdentity
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
from followupboss_mcp.http_client import FollowUpBossAsyncClient
from followupboss_mcp.mcp_server import create_server
from followupboss_mcp.tenant_store import (
    TenantCredentialRecord,
    TenantCredentialStatus,
    TenantRecord,
    TenantStatus,
    TenantStore,
)

_ORIGIN = "https://mcp.example.com"
_RESOURCE = f"{_ORIGIN}/mcp"
_API = "https://api.followupboss.test/v1/"
_SCOPE = "followupboss:mcp"
_MODERN = "2026-07-28"
_LEGACY = "2025-11-25"
_IDENTITY = {
    "account": {"id": 123, "name": "Lifecycle Account"},
    "user": {"id": 456, "email": "agent@example.test", "name": "Lifecycle Agent"},
}


class _HTTPResponse(Protocol):
    @property
    def status_code(self) -> int: ...

    @property
    def text(self) -> str: ...

    @property
    def headers(self) -> Mapping[str, str]: ...

    def json(self) -> Any: ...


def _hash(token: str) -> str:
    return "sha256:" + hashlib.sha256(token.encode()).hexdigest()


@dataclass
class _Persistence(TenantStore):
    """External-storage stand-in shared by fresh server instances.

    Persist model JSON, not live model objects, so writes and later reads cross
    a serialization boundary just as they do with the production stores.
    """

    now: int = field(default_factory=lambda: int(time.time()))
    clients: dict[str, str] = field(default_factory=dict)
    pending: dict[str, str] = field(default_factory=dict)
    codes: dict[str, str] = field(default_factory=dict)
    access: dict[str, str] = field(default_factory=dict)
    refresh: dict[str, str] = field(default_factory=dict)
    tenants: dict[str, str] = field(default_factory=dict)
    credentials: dict[str, str] = field(default_factory=dict)

    async def save_client(self, client: HostedOAuthDynamicClient) -> None:
        self.clients[client.client_id] = client.model_dump_json()

    async def get_client(self, client_id: str) -> HostedOAuthDynamicClient | None:
        raw = self.clients.get(client_id)
        return HostedOAuthDynamicClient.model_validate_json(raw) if raw else None

    async def save_pending_authorization(
        self, authorization: HostedOAuthPendingAuthorization
    ) -> None:
        self.pending[authorization.fub_state] = authorization.model_dump_json()

    async def consume_pending_authorization(
        self, fub_state: str
    ) -> HostedOAuthPendingAuthorization | None:
        raw = self.pending.pop(fub_state, None)
        return HostedOAuthPendingAuthorization.model_validate_json(raw) if raw else None

    async def save_authorization_code(self, code: HostedOAuthAuthorizationCode) -> None:
        self.codes[code.code_hash] = code.model_dump_json()

    async def consume_authorization_code(
        self, code_hash: str
    ) -> HostedOAuthAuthorizationCode | None:
        raw = self.codes.pop(code_hash, None)
        return HostedOAuthAuthorizationCode.model_validate_json(raw) if raw else None

    async def save_access_token(self, token: HostedOAuthAccessTokenMetadata) -> None:
        self.access[token.token_hash] = token.model_dump_json()

    async def save_refresh_token(self, token: HostedOAuthRefreshToken) -> None:
        self.refresh[token.token_hash] = token.model_dump_json()

    async def get_refresh_token(self, token_hash: str) -> HostedOAuthRefreshToken | None:
        raw = self.refresh.get(token_hash)
        return HostedOAuthRefreshToken.model_validate_json(raw) if raw else None

    async def revoke_refresh_token(self, token_hash: str, *, revoked_at: int) -> None:
        token = HostedOAuthRefreshToken.model_validate_json(self.refresh[token_hash])
        self.refresh[token_hash] = token.model_copy(
            update={"revoked_at": revoked_at}
        ).model_dump_json()

    async def verify_token(self, token: str) -> HostedVerifiedIdentity | None:
        raw = self.access.get(_hash(token))
        if raw is None:
            return None
        record = HostedOAuthAccessTokenMetadata.model_validate_json(raw)
        if record.expires_at <= self.now:
            return None
        return HostedVerifiedIdentity.model_validate(record.model_dump(exclude={"token_hash"}))

    async def provision_tenant(
        self,
        *,
        identity: FollowUpBossOAuthIdentity,
        token_payload: FollowUpBossOAuthTokenPayload,
    ) -> ProvisionedHostedTenant:
        tenant = TenantRecord(
            tenant_id=identity.tenant_id,
            tenant_slug=identity.tenant_id,
            display_name=identity.account_name,
            credential_id=identity.credential_id,
        )
        credential = TenantCredentialRecord(
            credential_id=identity.credential_id,
            tenant_id=identity.tenant_id,
            auth_mode=AuthMode.OAUTH,
            access_token=token_payload.access_token,
            system_name="Lifecycle Test",
        )
        self.tenants[tenant.tenant_id] = tenant.model_dump_json()
        # SecretStr deliberately redacts normal JSON dumps; the external secret
        # store holds the actual value, so serialize that field explicitly here.
        payload = credential.model_dump(mode="json")
        payload["access_token"] = token_payload.access_token.get_secret_value()
        self.credentials[credential.credential_id] = json.dumps(payload)
        return ProvisionedHostedTenant(
            tenant_id=identity.tenant_id,
            credential_id=identity.credential_id,
            subject=identity.subject,
        )

    async def get_tenant(self, tenant_id: str) -> TenantRecord | None:
        raw = self.tenants.get(tenant_id)
        return TenantRecord.model_validate_json(raw) if raw else None

    async def get_credential(self, credential_id: str) -> TenantCredentialRecord | None:
        raw = self.credentials.get(credential_id)
        return TenantCredentialRecord.model_validate_json(raw) if raw else None

    async def aclose(self) -> None:
        """Closing one application does not delete external persisted data."""


@dataclass(frozen=True)
class _Client:
    name: str
    client_id: str | None
    registered_redirect: str
    redirect: str


_CLIENTS = (
    _Client(
        "chatgpt",
        "https://chatgpt.com/oauth/client.json",
        "https://chatgpt.com/connector_platform_oauth_redirect",
        "https://chatgpt.com/connector_platform_oauth_redirect",
    ),
    _Client(
        "codex",
        "https://chatgpt.com/oauth/codex/client.json",
        "http://127.0.0.1/callback",
        "http://127.0.0.1:54321/callback",
    ),
    _Client("dcr", None, "http://127.0.0.1:54321/callback", "http://127.0.0.1:54321/callback"),
)


@dataclass
class _ExternalHTTP:
    client: _Client
    identity_calls: int = 0
    metadata_calls: int = 0
    token_calls: int = 0

    def __call__(self, request: httpx.Request) -> httpx.Response:
        if request.url.host == "93.184.216.34":
            assert self.client.client_id is not None
            assert request.url.path == urlsplit(self.client.client_id).path
            assert request.headers["host"] == "chatgpt.com"
            assert request.extensions["sni_hostname"] == "chatgpt.com"
            self.metadata_calls += 1
            return httpx.Response(
                200,
                headers={"Cache-Control": "no-store"},
                json={
                    "client_id": self.client.client_id,
                    "client_name": self.client.name,
                    "redirect_uris": [self.client.registered_redirect],
                    "token_endpoint_auth_method": "private_key_jwt",
                    "token_endpoint_auth_methods_supported": ["none", "private_key_jwt"],
                },
            )
        if str(request.url) == "https://fub.example.test/oauth/token":
            self.token_calls += 1
            expected = base64.b64encode(b"test-client:test-client-secret").decode()
            assert request.headers["authorization"] == f"Basic {expected}"
            form = parse_qs(request.content.decode())
            assert form["grant_type"] == ["authorization_code"]
            assert form["code"] == ["synthetic-fub-code"]
            assert form["redirect_uri"] == [f"{_ORIGIN}/oauth/follow-up-boss/callback"]
            assert form["state"]
            return httpx.Response(
                200,
                json={"access_token": "synthetic-fub-token", "expires_in": 3600},
            )
        assert str(request.url) == f"{_API}identity", "Unexpected external HTTP request"
        assert request.headers["authorization"] == "Bearer synthetic-fub-token"
        assert request.headers["x-system"] == "Lifecycle Test"
        self.identity_calls += 1
        return httpx.Response(200, json=_IDENTITY)


async def _resolve_metadata_address(host: str, port: int) -> tuple[str, ...]:
    assert (host, port) == ("chatgpt.com", 443)
    return ("93.184.216.34",)


def _server_client(state: _Persistence, http: httpx.AsyncClient) -> TestClient:
    settings = HostedOAuthSettings.model_validate(
        {
            "issuer_url": _ORIGIN,
            "resource_server_url": _RESOURCE,
            "required_scopes": [_SCOPE],
            "fub_client_id": "test-client",
            "fub_client_secret": "test-client-secret",
            "fub_callback_url": f"{_ORIGIN}/oauth/follow-up-boss/callback",
            "fub_authorize_url": "https://fub.example.test/oauth/authorize",
            "fub_token_url": "https://fub.example.test/oauth/token",
            "fub_base_url": _API,
            "token_secret_prefix": "followupboss/test/",
            "system_name": "Lifecycle Test",
            "access_token_seconds": 60,
            "refresh_token_seconds": 3600,
        }
    )
    oauth = HostedOAuthApplication(
        settings=settings,
        store=state,
        tenant_provisioner=state,
        fub_client=FollowUpBossOAuthClient(settings, http_client=http),
        client_metadata_fetcher=ClientIdMetadataDocumentFetcher(
            http_client=http, address_resolver=_resolve_metadata_address
        ),
        time_provider=lambda: state.now,
    )

    def tenant_client(
        settings: FollowUpBossTenantSettings, logger: logging.Logger | None
    ) -> FollowUpBossAsyncClient:
        return FollowUpBossAsyncClient(settings, http_client=http, logger=logger)

    server = create_server(
        FollowUpBossTenantRuntimeDefaults.model_validate({"base_url": _API, "max_retries": 0}),
        hosted_auth=HostedAuthSettings.model_validate(
            {"issuer_url": _ORIGIN, "resource_server_url": _RESOURCE, "required_scopes": [_SCOPE]}
        ),
        hosted_token_verifier=state,
        tenant_store=state,
        hosted_oauth_application=oauth,
        tenant_client_factory=tenant_client,
    )
    return TestClient(server.streamable_http_app(), base_url=_ORIGIN)


class _MCP:
    def __init__(self, http: TestClient, protocol: str, token: str) -> None:
        self.http = http
        self.protocol = protocol
        self.session_headers: dict[str, str] = {}
        if protocol == _LEGACY:
            initialized = self.post(
                "initialize",
                token,
                {
                    "protocolVersion": protocol,
                    "capabilities": {},
                    "clientInfo": {"name": "oauth-lifecycle", "version": "1"},
                },
            )
            assert initialized.status_code == 200, initialized.text
            assert initialized.json()["result"]["protocolVersion"] == protocol
            self.session_headers["Mcp-Session-Id"] = initialized.headers["mcp-session-id"]
            notified = self.post("notifications/initialized", token, notification=True)
            assert notified.status_code == 202, notified.text
        else:
            discovered = self.post("server/discover", token)
            assert discovered.status_code == 200, discovered.text
            assert protocol in discovered.json()["result"]["supportedVersions"]

    def post(
        self,
        method: str,
        token: str,
        params: dict[str, Any] | None = None,
        *,
        notification: bool = False,
    ) -> _HTTPResponse:
        params = dict(params or {})
        headers = {
            "Accept": "application/json, text/event-stream",
            "Authorization": f"Bearer {token}",
            "MCP-Protocol-Version": self.protocol,
            **self.session_headers,
        }
        if self.protocol == _MODERN:
            headers.update({"Accept": "application/json", "Mcp-Method": method})
            if "name" in params:
                headers["Mcp-Name"] = str(params["name"])
            params["_meta"] = {
                "io.modelcontextprotocol/protocolVersion": self.protocol,
                "io.modelcontextprotocol/clientInfo": {"name": "oauth-lifecycle", "version": "1"},
                "io.modelcontextprotocol/clientCapabilities": {},
            }
        body: dict[str, Any] = {"jsonrpc": "2.0", "method": method, "params": params}
        if not notification:
            body["id"] = 1
        return self.http.post("/mcp", headers=headers, json=body)

    def identity(self, token: str) -> _HTTPResponse:
        return self.post(
            "tools/call", token, {"name": "followupboss_get_identity", "arguments": {}}
        )


def _assert_identity(response: _HTTPResponse) -> None:
    assert response.status_code == 200, response.text
    result = response.json()["result"]
    assert result.get("isError", False) is False, result
    identity = result["structuredContent"]
    assert identity["id"] == 456
    assert identity["accountId"] == 123
    assert identity["email"] == "agent@example.test"


@pytest.mark.parametrize("protocol", [_MODERN, _LEGACY])
@pytest.mark.parametrize("oauth_client", _CLIENTS, ids=lambda client: client.name)
@pytest.mark.asyncio
async def test_oauth_tokens_survive_restart_and_authorize_mcp_until_expiry_or_revocation(
    oauth_client: _Client, protocol: str
) -> None:
    state = _Persistence()
    external = _ExternalHTTP(oauth_client)
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(external), base_url=_API
    ) as outbound:
        with _server_client(state, outbound) as installer:
            assert not state.access and not state.tenants and not state.credentials
            challenge_response = installer.post("/mcp", json={})
            assert challenge_response.status_code == 401
            assert (
                "/.well-known/oauth-protected-resource/mcp"
                in challenge_response.headers["www-authenticate"]
            )
            assert external.identity_calls == 0
            protected = installer.get("/.well-known/oauth-protected-resource/mcp").json()
            assert protected["resource"] == _RESOURCE
            assert protected["authorization_servers"] == [f"{_ORIGIN}/"]
            metadata = installer.get("/.well-known/oauth-authorization-server").json()
            assert metadata["issuer"] == protected["authorization_servers"][0]
            assert metadata["token_endpoint_auth_methods_supported"] == ["none"]
            assert "S256" in metadata["code_challenge_methods_supported"]
            assert metadata["authorization_response_iss_parameter_supported"] is True
            assert metadata["client_id_metadata_document_supported"] is True
            assert _SCOPE in metadata["scopes_supported"]

            client_id = oauth_client.client_id
            if client_id is None:
                registered = installer.post(
                    metadata["registration_endpoint"],
                    json={
                        "client_name": oauth_client.name,
                        "redirect_uris": [oauth_client.registered_redirect],
                        "token_endpoint_auth_method": "none",
                        "scope": _SCOPE,
                    },
                )
                assert registered.status_code == 201, registered.text
                client_id = registered.json()["client_id"]
            verifier = "lifecycle-verifier-with-at-least-forty-three-characters"
            challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
            authorized = installer.get(
                metadata["authorization_endpoint"],
                params={
                    "response_type": "code",
                    "client_id": client_id,
                    "redirect_uri": oauth_client.redirect,
                    "scope": _SCOPE,
                    "resource": protected["resource"],
                    "state": "original-client-state",
                    "code_challenge": challenge.decode().rstrip("="),
                    "code_challenge_method": "S256",
                },
                follow_redirects=False,
            )
            assert authorized.status_code == 307, authorized.text
            fub_location = urlsplit(authorized.headers["location"])
            assert fub_location.netloc == "fub.example.test"
            fub_query = parse_qs(fub_location.query)
            assert fub_query["response_type"] == ["auth_code"]
            assert fub_query["client_id"] == ["test-client"]
            callback = installer.get(
                fub_query["redirect_uri"][0],
                params={
                    "state": fub_query["state"][0],
                    "response": "approved",
                    "code": "synthetic-fub-code",
                },
                follow_redirects=False,
            )
            if oauth_client.client_id is None:
                assert callback.status_code == 307, callback.text
                redirect = callback.headers["location"]
            else:
                assert callback.status_code == 200, callback.text
                assert callback.headers["cache-control"] == "no-store"
                link = BeautifulSoup(callback.text, "html.parser").find(
                    "a", attrs={"data-testid": "continue"}
                )
                assert link is not None
                redirect = str(link["href"])
                assert external.metadata_calls == 2
            destination = urlsplit(redirect)
            assert destination._replace(query="").geturl() == oauth_client.redirect
            returned = parse_qs(destination.query)
            assert returned["state"] == ["original-client-state"]
            assert returned["iss"] == [metadata["issuer"]]
            exchange = {
                "grant_type": "authorization_code",
                "code": returned["code"][0],
                "client_id": client_id,
                "redirect_uri": oauth_client.redirect,
                "code_verifier": verifier,
                "resource": _RESOURCE,
            }
            token_response = installer.post(metadata["token_endpoint"], data=exchange)
            assert token_response.status_code == 200, token_response.text
            tokens = token_response.json()
            assert tokens["scope"] == _SCOPE
            assert tokens["token_type"] == "Bearer"
            assert external.token_calls == 1
            assert external.identity_calls == 1
            assert state.access and state.tenants and state.credentials
            issued = HostedOAuthAccessTokenMetadata.model_validate_json(
                state.access[_hash(tokens["access_token"])]
            )
            assert issued.client_id == client_id
            assert issued.subject == "fub-user-456"
            assert issued.tenant_id == "fub-account-123"
            assert issued.resource == _RESOURCE
            assert issued.scopes == (_SCOPE,)

        # The second application has new middleware, OAuth and MCP state. Only
        # the external persistence survives; no manually injected token can hide
        # a mismatch between issuance, lookup, tenant resolution and transport.
        with _server_client(state, outbound) as restarted:
            replay = restarted.post(metadata["token_endpoint"], data=exchange)
            assert replay.status_code == 400
            assert replay.json()["error"] == "invalid_grant"
            mcp = _MCP(restarted, protocol, tokens["access_token"])
            _assert_identity(mcp.identity(tokens["access_token"]))
            assert external.identity_calls == 2
            assert mcp.identity("synthetic-fub-token").status_code == 401
            assert external.identity_calls == 2

            state.now += tokens["expires_in"] + 1
            expired = mcp.identity(tokens["access_token"])
            assert expired.status_code == 401, expired.text
            assert external.identity_calls == 2
            refresh_form = {
                "grant_type": "refresh_token",
                "refresh_token": tokens["refresh_token"],
                "client_id": client_id,
                "resource": _RESOURCE,
            }
            refreshed = restarted.post(metadata["token_endpoint"], data=refresh_form)
            assert refreshed.status_code == 200, refreshed.text
            renewed = refreshed.json()
            assert renewed["access_token"] != tokens["access_token"]
            assert renewed["refresh_token"] != tokens["refresh_token"]
            _assert_identity(mcp.identity(renewed["access_token"]))
            assert external.identity_calls == 3
            replay = restarted.post(metadata["token_endpoint"], data=refresh_form)
            assert replay.status_code == 400
            assert replay.json()["error"] == "invalid_grant"
            assert len(state.access) == 2

            tenant_key, raw_tenant = next(iter(state.tenants.items()))
            tenant = TenantRecord.model_validate_json(raw_tenant)
            state.tenants[tenant_key] = tenant.model_copy(
                update={"status": TenantStatus.DISABLED}
            ).model_dump_json()
            assert mcp.identity(renewed["access_token"]).status_code == 401
            assert external.identity_calls == 3
            state.tenants[tenant_key] = raw_tenant
            raw_credential = state.credentials[tenant.credential_id]
            credential = TenantCredentialRecord.model_validate_json(raw_credential)
            # Mutate only the persisted status without redacting the stored
            # synthetic secret during a model JSON serialization.
            credential_payload = json.loads(raw_credential)
            credential_payload["status"] = TenantCredentialStatus.REVOKED
            state.credentials[credential.credential_id] = json.dumps(credential_payload)
            assert mcp.identity(renewed["access_token"]).status_code == 401
            assert external.identity_calls == 3
