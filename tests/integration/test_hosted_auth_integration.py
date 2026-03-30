"""Integration tests for hosted inbound auth on the streamable HTTP transport."""

from __future__ import annotations

from typing import Literal

import pytest
from starlette.testclient import TestClient

from followupboss_mcp.auth import AuthMode
from followupboss_mcp.config import FollowUpBossSettings
from followupboss_mcp.hosted_auth import (
    DevelopmentHostedTokenVerifier,
    HostedAuthSettings,
    HostedVerifiedIdentity,
)
from followupboss_mcp.hosted_rate_limits import (
    HostedEndpointRateLimiter,
    HostedRateLimitDecision,
    HostedRateLimitKey,
    HostedRateLimitSettings,
)
from followupboss_mcp.mcp_server import create_server
from followupboss_mcp.tenant_store import (
    DevelopmentTenantStore,
    TenantCredentialRecord,
    TenantCredentialStatus,
    TenantRecord,
    TenantStatus,
    TenantStore,
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


class UnavailableHostedTenantStore(TenantStore):
    """Tenant store stub whose backend becomes unavailable during auth."""

    def __init__(self, *, failure_point: str) -> None:
        """Initialize the unavailable store stub.

        Args:
            failure_point: Either `tenant` for metadata lookup failures or
                `secret` for credential lookup failures.
        """
        self._failure_point = failure_point

    async def get_tenant(self, tenant_id: str) -> TenantRecord | None:
        """Return one tenant or raise when the tenant store is unavailable."""
        del tenant_id
        if self._failure_point == "tenant":
            raise RuntimeError("tenant database unavailable")
        return _tenant_record()

    async def get_credential(self, credential_id: str) -> TenantCredentialRecord | None:
        """Return one credential or raise when the secret store is unavailable."""
        del credential_id
        if self._failure_point == "secret":
            raise RuntimeError("secret backend unavailable")
        return _credential_record()


class FailingHostedRateLimitBackend:
    """Rate-limit backend stub that always raises."""

    async def consume(
        self,
        key: HostedRateLimitKey,
        *,
        limit: int,
        window_seconds: float,
    ) -> HostedRateLimitDecision:
        """Raise a backend failure for every rate-limit check."""
        del key, limit, window_seconds
        raise RuntimeError("rate limit backend unavailable")


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


@pytest.mark.parametrize("failure_point", ["tenant", "secret"])
def test_hosted_streamable_http_unavailable_store_fails_closed_before_client_creation(
    monkeypatch: pytest.MonkeyPatch,
    failure_point: str,
) -> None:
    """Unavailable tenant or secret stores should fail closed during hosted auth."""
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
        tenant_store=UnavailableHostedTenantStore(failure_point=failure_point),
    )

    with TestClient(server.streamable_http_app()) as client:
        response = client.post(
            "/mcp",
            json=_INITIALIZE_REQUEST,
            headers={"Authorization": "Bearer valid-token"},
        )

    assert response.status_code == 401
    assert response.json() == {
        "error": "invalid_token",
        "error_description": "Authentication required",
    }
    assert "tenant database unavailable" not in response.text
    assert "secret backend unavailable" not in response.text
    assert created_clients == []


def test_hosted_streamable_http_rate_limit_budgets_are_isolated_per_tenant_and_client() -> None:
    """Hosted rate limits should isolate budgets by tenant and client."""
    tenant_store = DevelopmentTenantStore(
        tenants=[
            _tenant_record(),
            _tenant_record(
                tenant_id="tenant-2",
                tenant_slug="tenant-two",
                display_name="Tenant Two",
                credential_id="credential-2",
            ),
        ],
        credentials=[
            _credential_record(),
            _credential_record(
                credential_id="credential-2",
                tenant_id="tenant-2",
                api_key="secret-key-two",
            ),
        ],
    )
    token_verifier = DevelopmentHostedTokenVerifier.from_mapping(
        {
            "tenant-1-client-a": HostedVerifiedIdentity.model_validate(
                {
                    "tenant_id": "tenant-1",
                    "subject": "user-tenant-1-a",
                    "client_id": "portal-app",
                }
            ),
            "tenant-2-client-a": HostedVerifiedIdentity.model_validate(
                {
                    "tenant_id": "tenant-2",
                    "subject": "user-tenant-2-a",
                    "client_id": "portal-app",
                }
            ),
            "tenant-1-client-b": HostedVerifiedIdentity.model_validate(
                {
                    "tenant_id": "tenant-1",
                    "subject": "user-tenant-1-b",
                    "client_id": "automation-app",
                }
            ),
        }
    )
    server = create_server(
        FollowUpBossSettings.model_validate({"api_key": "local-dev-key"}),
        hosted_auth=_hosted_auth_settings(),
        hosted_token_verifier=token_verifier,
        tenant_store=tenant_store,
        hosted_rate_limiter=HostedEndpointRateLimiter(
            settings=HostedRateLimitSettings(
                requests_per_window=1,
                window_seconds=60.0,
            )
        ),
    )

    with TestClient(server.streamable_http_app(), base_url="http://127.0.0.1:8000") as client:
        first_response = client.post(
            "/mcp",
            json=_INITIALIZE_REQUEST,
            headers={
                "Authorization": "Bearer tenant-1-client-a",
                "Accept": "application/json",
            },
        )
        second_same_budget_response = client.post(
            "/mcp",
            json=_INITIALIZE_REQUEST,
            headers={
                "Authorization": "Bearer tenant-1-client-a",
                "Accept": "application/json",
            },
        )
        different_tenant_response = client.post(
            "/mcp",
            json=_INITIALIZE_REQUEST,
            headers={
                "Authorization": "Bearer tenant-2-client-a",
                "Accept": "application/json",
            },
        )
        different_client_response = client.post(
            "/mcp",
            json=_INITIALIZE_REQUEST,
            headers={
                "Authorization": "Bearer tenant-1-client-b",
                "Accept": "application/json",
            },
        )

    assert first_response.status_code == 200
    assert second_same_budget_response.status_code == 429
    assert second_same_budget_response.json() == {
        "error": "rate_limited",
        "error_description": "Rate limit exceeded",
    }
    assert second_same_budget_response.headers["Retry-After"] == "60"
    assert different_tenant_response.status_code == 200
    assert different_client_response.status_code == 200


@pytest.mark.parametrize(
    ("backend_failure_mode", "expected_status_code"),
    [
        ("closed", 503),
        ("open", 200),
    ],
)
def test_hosted_streamable_http_rate_limit_backend_failures_are_handled_explicitly(
    backend_failure_mode: Literal["closed", "open"],
    expected_status_code: int,
) -> None:
    """Hosted rate-limit backend failures should follow the configured failure mode."""
    server = create_server(
        FollowUpBossSettings.model_validate({"api_key": "local-dev-key"}),
        hosted_auth=_hosted_auth_settings(),
        hosted_token_verifier=_hosted_token_verifier(),
        tenant_store=_tenant_store(),
        hosted_rate_limiter=HostedEndpointRateLimiter(
            settings=HostedRateLimitSettings(
                requests_per_window=1,
                window_seconds=60.0,
                backend_failure_mode=backend_failure_mode,
            ),
            backend=FailingHostedRateLimitBackend(),
        ),
    )

    with TestClient(server.streamable_http_app(), base_url="http://127.0.0.1:8000") as client:
        response = client.post(
            "/mcp",
            json=_INITIALIZE_REQUEST,
            headers={
                "Authorization": "Bearer valid-token",
                "Accept": "application/json",
            },
        )

    assert response.status_code == expected_status_code
    assert "rate limit backend unavailable" not in response.text
    if expected_status_code == 503:
        assert response.json() == {
            "error": "temporarily_unavailable",
            "error_description": "Hosted rate limiting is temporarily unavailable",
        }
        assert response.headers["Retry-After"] == "60"
