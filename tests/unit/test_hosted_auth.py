"""Focused unit tests for hosted inbound-auth models and verifier adapters."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from followupboss_mcp.auth import AuthMode
from followupboss_mcp.hosted_auth import (
    DevelopmentHostedTokenRecord,
    DevelopmentHostedTokenVerifier,
    HostedAuthSettings,
    HostedTenantTokenVerifier,
    HostedVerifiedIdentity,
)
from followupboss_mcp.tenant_store import (
    DevelopmentTenantStore,
    TenantCredentialRecord,
    TenantCredentialStatus,
    TenantRecord,
    TenantStatus,
)


def _tenant_record(**overrides: object) -> TenantRecord:
    """Build a representative tenant record for hosted-auth tests.

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
    """Build a representative credential record for hosted-auth tests.

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


def test_hosted_verified_identity_and_auth_settings_validation() -> None:
    """Hosted-auth models should normalize and validate the public contract."""
    identity = HostedVerifiedIdentity.model_validate(
        {
            "tenant_id": "  tenant-1  ",
            "subject": "  user-123  ",
            "client_id": "  portal-app  ",
            "scopes": ["tools:read", "tools:read", "tools:write"],
            "credential_id": "  credential-1  ",
            "token_id": "  token-123  ",
            "expires_at": 1,
        }
    )
    assert identity.tenant_id == "tenant-1"
    assert identity.subject == "user-123"
    assert identity.client_id == "portal-app"
    assert identity.scopes == ("tools:read", "tools:write")
    assert identity.credential_id == "credential-1"
    assert identity.token_id == "token-123"

    auth_settings = HostedAuthSettings.model_validate(
        {
            "issuer_url": "https://issuer.example.com",
            "resource_server_url": "https://mcp.example.com/mcp",
            "required_scopes": "tools:read tools:write",
        }
    )
    mcp_auth_settings = auth_settings.to_mcp_auth_settings()
    assert str(mcp_auth_settings.issuer_url) == "https://issuer.example.com/"
    assert str(mcp_auth_settings.resource_server_url) == "https://mcp.example.com/mcp"
    assert mcp_auth_settings.required_scopes == ["tools:read", "tools:write"]

    with pytest.raises(ValidationError):
        HostedVerifiedIdentity.model_validate(
            {
                "tenant_id": " ",
                "subject": "user-123",
                "client_id": "portal-app",
            }
        )
    with pytest.raises(ValidationError):
        HostedAuthSettings.model_validate(
            {
                "issuer_url": "https://issuer.example.com",
                "resource_server_url": "https://mcp.example.com/mcp",
                "required_scopes": ["tools:read", ""],
            }
        )


@pytest.mark.asyncio
async def test_development_hosted_token_verifier_snapshot_and_lookup() -> None:
    """The development token verifier should resolve known tokens only."""
    identity = HostedVerifiedIdentity.model_validate(
        {
            "tenant_id": "tenant-1",
            "subject": "user-123",
            "client_id": "portal-app",
            "scopes": ["tools:read"],
        }
    )
    verifier = DevelopmentHostedTokenVerifier(
        tokens=[
            DevelopmentHostedTokenRecord.model_validate(
                {
                    "token": "dev-token",
                    "identity": identity,
                }
            )
        ]
    )

    resolved = await verifier.verify_token("dev-token")

    assert resolved == identity
    assert await verifier.verify_token("missing-token") is None
    assert verifier.snapshot().tokens[0].token_value() == "dev-token"

    with pytest.raises(ValidationError):
        DevelopmentHostedTokenVerifier(
            tokens=[
                DevelopmentHostedTokenRecord.model_validate(
                    {
                        "token": "duplicate-token",
                        "identity": identity,
                    }
                ),
                DevelopmentHostedTokenRecord.model_validate(
                    {
                        "token": "duplicate-token",
                        "identity": identity,
                    }
                ),
            ]
        )


@pytest.mark.asyncio
async def test_hosted_tenant_token_verifier_resolves_active_tenant_context() -> None:
    """Tenant resolution should succeed for an active tenant and credential."""
    identity = HostedVerifiedIdentity.model_validate(
        {
            "tenant_id": "tenant-1",
            "subject": "user-123",
            "client_id": "portal-app",
            "scopes": ["tools:read"],
            "credential_id": "credential-1",
        }
    )
    verifier = HostedTenantTokenVerifier(
        identity_verifier=DevelopmentHostedTokenVerifier.from_mapping({"dev-token": identity}),
        tenant_store=DevelopmentTenantStore(
            tenants=[_tenant_record()],
            credentials=[_credential_record()],
        ),
    )

    access_token = await verifier.verify_token("dev-token")

    assert access_token is not None
    assert access_token.identity == identity
    assert access_token.tenant.tenant_id == "tenant-1"
    assert access_token.tenant.tenant_slug == "tenant-one"
    assert access_token.tenant.credential_id == "credential-1"
    assert access_token.client_id == "portal-app"
    assert access_token.scopes == ["tools:read"]


@pytest.mark.asyncio
async def test_hosted_tenant_token_verifier_returns_none_for_wrong_tenant_binding() -> None:
    """Credential bindings on the token should fail closed when they mismatch."""
    verifier = HostedTenantTokenVerifier(
        identity_verifier=DevelopmentHostedTokenVerifier.from_mapping(
            {
                "wrong-tenant-token": HostedVerifiedIdentity.model_validate(
                    {
                        "tenant_id": "tenant-1",
                        "subject": "user-123",
                        "client_id": "portal-app",
                        "credential_id": "credential-2",
                    }
                )
            }
        ),
        tenant_store=DevelopmentTenantStore(
            tenants=[_tenant_record()],
            credentials=[_credential_record()],
        ),
    )

    assert await verifier.verify_token("wrong-tenant-token") is None
