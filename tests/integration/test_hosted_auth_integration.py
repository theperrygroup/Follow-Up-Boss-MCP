"""Integration tests for hosted inbound auth on the streamable HTTP transport."""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from followupboss_mcp.auth import AuthMode
from followupboss_mcp.config import FollowUpBossSettings
from followupboss_mcp.hosted_auth import (
    DevelopmentHostedTokenVerifier,
    HostedAuthSettings,
    HostedVerifiedIdentity,
)
from followupboss_mcp.mcp_server import create_server
from followupboss_mcp.tenant_store import (
    DevelopmentTenantStore,
    TenantCredentialRecord,
    TenantCredentialStatus,
    TenantRecord,
    TenantStatus,
)

_INITIALIZE_REQUEST = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-03-26",
        "capabilities": {},
        "clientInfo": {"name": "pytest", "version": "1.0"},
    },
}


def _tenant_record(**overrides: object) -> TenantRecord:
    """Build a representative tenant record for hosted-auth integration tests.

    Args:
        **overrides: Field overrides for the default tenant payload.

    Returns:
        A validated tenant record.
    """
    payload: dict[str, object] = {
        "tenant_id": "tenant-1",
        "tenant_slug": "tenant-one",
        "display_name": "Tenant One",
        "credential_id": "credential-1",
        "status": TenantStatus.ACTIVE,
    }
    payload.update(overrides)
    return TenantRecord.model_validate(payload)


def _credential_record(**overrides: object) -> TenantCredentialRecord:
    """Build a representative credential record for hosted-auth integration tests.

    Args:
        **overrides: Field overrides for the default credential payload.

    Returns:
        A validated credential record.
    """
    payload: dict[str, object] = {
        "credential_id": "credential-1",
        "tenant_id": "tenant-1",
        "auth_mode": AuthMode.API_KEY,
        "api_key": "secret-key",
        "status": TenantCredentialStatus.ACTIVE,
    }
    payload.update(overrides)
    return TenantCredentialRecord.model_validate(payload)


def _hosted_auth_settings() -> HostedAuthSettings:
    """Return representative hosted resource-server settings.

    Returns:
        Hosted auth settings suitable for FastMCP integration tests.
    """
    return HostedAuthSettings.model_validate(
        {
            "issuer_url": "https://issuer.example.com",
            "resource_server_url": "https://mcp.example.com/mcp",
        }
    )


def _hosted_token_verifier() -> DevelopmentHostedTokenVerifier:
    """Return a development verifier with representative hosted tokens.

    Returns:
        A development hosted-token verifier with active and failing token cases.
    """
    return DevelopmentHostedTokenVerifier.from_mapping(
        {
            "valid-token": HostedVerifiedIdentity.model_validate(
                {
                    "tenant_id": "tenant-1",
                    "subject": "user-123",
                    "client_id": "portal-app",
                }
            ),
            "expired-token": HostedVerifiedIdentity.model_validate(
                {
                    "tenant_id": "tenant-1",
                    "subject": "user-123",
                    "client_id": "portal-app",
                    "expires_at": 1,
                }
            ),
            "disabled-token": HostedVerifiedIdentity.model_validate(
                {
                    "tenant_id": "tenant-disabled",
                    "subject": "user-123",
                    "client_id": "portal-app",
                }
            ),
            "missing-tenant-token": HostedVerifiedIdentity.model_validate(
                {
                    "tenant_id": "tenant-missing",
                    "subject": "user-123",
                    "client_id": "portal-app",
                }
            ),
            "revoked-token": HostedVerifiedIdentity.model_validate(
                {
                    "tenant_id": "tenant-revoked",
                    "subject": "user-123",
                    "client_id": "portal-app",
                }
            ),
            "wrong-tenant-token": HostedVerifiedIdentity.model_validate(
                {
                    "tenant_id": "tenant-1",
                    "subject": "user-123",
                    "client_id": "portal-app",
                    "credential_id": "credential-2",
                }
            ),
        }
    )


def _tenant_store() -> DevelopmentTenantStore:
    """Return a development tenant store with active and failing tenants.

    Returns:
        A development tenant store spanning active, disabled, and revoked cases.
    """
    return DevelopmentTenantStore(
        tenants=[
            _tenant_record(),
            _tenant_record(
                tenant_id="tenant-disabled",
                tenant_slug="tenant-disabled",
                credential_id="credential-disabled",
                status=TenantStatus.DISABLED,
            ),
            _tenant_record(
                tenant_id="tenant-revoked",
                tenant_slug="tenant-revoked",
                credential_id="credential-revoked",
            ),
        ],
        credentials=[
            _credential_record(),
            _credential_record(
                credential_id="credential-disabled",
                tenant_id="tenant-disabled",
            ),
            _credential_record(
                credential_id="credential-revoked",
                tenant_id="tenant-revoked",
                status=TenantCredentialStatus.REVOKED,
            ),
        ],
    )


@pytest.mark.parametrize(
    "token",
    [
        None,
        "invalid-token",
        "expired-token",
        "disabled-token",
        "missing-tenant-token",
        "revoked-token",
        "wrong-tenant-token",
    ],
)
def test_hosted_streamable_http_auth_failures_fail_closed_before_client_creation(
    monkeypatch: pytest.MonkeyPatch,
    token: str | None,
) -> None:
    """Hosted streamable HTTP auth failures should reject before client creation."""
    created_clients: list[object] = []

    class CountingClient:
        """Minimal client stub that records whether it was instantiated."""

        def __init__(self, *_: object, **__: object) -> None:
            created_clients.append(object())

        async def aclose(self) -> None:
            """Close the client stub."""
            return None

        async def request_json(self, *_: object, **__: object) -> dict[str, object]:
            """Return a placeholder payload if the client is ever used."""
            return {"id": 1}

    monkeypatch.setattr("followupboss_mcp.mcp_server.FollowUpBossAsyncClient", CountingClient)

    server = create_server(
        FollowUpBossSettings.model_validate({"api_key": "local-dev-key"}),
        hosted_auth=_hosted_auth_settings(),
        hosted_token_verifier=_hosted_token_verifier(),
        tenant_store=_tenant_store(),
    )

    headers = {} if token is None else {"Authorization": f"Bearer {token}"}
    with TestClient(server.streamable_http_app()) as client:
        response = client.post("/mcp", json=_INITIALIZE_REQUEST, headers=headers)

    assert response.status_code == 401
    assert response.json() == {
        "error": "invalid_token",
        "error_description": "Authentication required",
    }
    assert created_clients == []
