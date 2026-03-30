"""Focused unit tests for hosted inbound-auth models and verifier adapters."""

from __future__ import annotations

import io
import logging

import pytest
from pydantic import SecretStr, ValidationError

from followupboss_mcp.auth import AuthMode
from followupboss_mcp.hosted_auth import (
    DevelopmentHostedTokenRecord,
    DevelopmentHostedTokenVerifier,
    HostedAccessToken,
    HostedAuthenticatedTenant,
    HostedAuthSettings,
    HostedTenantTokenVerifier,
    HostedVerifiedIdentity,
    _normalize_optional_string,
    _normalize_scopes,
    get_hosted_authenticated_tenant,
    get_hosted_verified_identity,
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
    with pytest.raises(ValidationError, match="expires_at must be greater than zero."):
        HostedVerifiedIdentity.model_validate(
            {
                "tenant_id": "tenant-1",
                "subject": "user-123",
                "client_id": "portal-app",
                "expires_at": 0,
            }
        )


def test_hosted_auth_normalization_helpers_preserve_invalid_shapes() -> None:
    """Hosted-auth helpers should preserve unsupported values for downstream validation."""
    unsupported_optional_value = object()
    unsupported_scope_value = object()
    invalid_scope_sequence: tuple[object, ...] = ("tools:read", 1)

    assert _normalize_optional_string(unsupported_optional_value) is unsupported_optional_value
    assert _normalize_scopes(None) == ()
    assert _normalize_scopes(unsupported_scope_value) is unsupported_scope_value
    assert _normalize_scopes(invalid_scope_sequence) is invalid_scope_sequence


def test_development_hosted_token_record_accepts_secretstr_inputs() -> None:
    """Development hosted-token records should accept `SecretStr` and reject invalid types."""
    identity = HostedVerifiedIdentity.model_validate(
        {
            "tenant_id": "tenant-1",
            "subject": "user-123",
            "client_id": "portal-app",
        }
    )

    record = DevelopmentHostedTokenRecord.model_validate(
        {
            "token": SecretStr("dev-token"),
            "identity": identity,
        }
    )

    assert record.token_value() == "dev-token"
    with pytest.raises(ValidationError):
        DevelopmentHostedTokenRecord.model_validate(
            {
                "token": 123,
                "identity": identity,
            }
        )


def test_hosted_auth_context_accessors_resolve_identity_and_tenant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Hosted-auth accessors should unwrap FastMCP auth context safely."""
    access_token = HostedAccessToken.from_verified_identity(
        token="dev-token",
        identity=HostedVerifiedIdentity.model_validate(
            {
                "tenant_id": "tenant-1",
                "subject": "user-123",
                "client_id": "portal-app",
                "credential_id": "credential-1",
            }
        ),
        tenant=HostedAuthenticatedTenant.model_validate(
            {
                "tenant_id": "tenant-1",
                "tenant_slug": "tenant-one",
                "display_name": "Tenant One",
                "credential_id": "credential-1",
            }
        ),
    )

    monkeypatch.setattr("followupboss_mcp.hosted_auth.get_access_token", lambda: access_token)
    assert get_hosted_verified_identity() == access_token.identity
    assert get_hosted_authenticated_tenant() == access_token.tenant

    monkeypatch.setattr("followupboss_mcp.hosted_auth.get_access_token", lambda: None)
    assert get_hosted_verified_identity() is None
    assert get_hosted_authenticated_tenant() is None


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

    with pytest.raises(ValidationError) as exc_info:
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
    assert "Duplicate hosted bearer tokens are not allowed." in str(exc_info.value)
    assert "duplicate-token" not in str(exc_info.value)


def test_hosted_access_token_repr_redacts_bearer_token() -> None:
    """Hosted access-token representations should never leak the bearer token."""
    access_token = HostedAccessToken.from_verified_identity(
        token="super-secret-token",
        identity=HostedVerifiedIdentity.model_validate(
            {
                "tenant_id": "tenant-1",
                "subject": "user-123",
                "client_id": "portal-app",
                "scopes": ["tools:read"],
                "credential_id": "credential-1",
            }
        ),
        tenant=HostedAuthenticatedTenant.model_validate(
            {
                "tenant_id": "tenant-1",
                "tenant_slug": "tenant-one",
                "display_name": "Tenant One",
                "credential_id": "credential-1",
            }
        ),
    )

    representation = repr(access_token)

    assert access_token.token == "super-secret-token"
    assert "super-secret-token" not in representation
    assert "***redacted***" in representation
    assert str(access_token) == representation


@pytest.mark.asyncio
async def test_hosted_tenant_token_verifier_resolves_active_tenant_context() -> None:
    """Tenant resolution should succeed for an active tenant and credential."""
    stream = io.StringIO()
    logger = logging.getLogger("followupboss_mcp_test_hosted_auth_success_audit")
    logger.handlers.clear()
    logger.setLevel("INFO")
    logger.propagate = False
    logger.addHandler(logging.StreamHandler(stream))
    identity = HostedVerifiedIdentity.model_validate(
        {
            "tenant_id": "tenant-1",
            "subject": "user-123",
            "client_id": "portal-app",
            "scopes": ["tools:read"],
            "credential_id": "credential-1",
            "token_id": "token-123",
        }
    )
    verifier = HostedTenantTokenVerifier(
        identity_verifier=DevelopmentHostedTokenVerifier.from_mapping({"dev-token": identity}),
        tenant_store=DevelopmentTenantStore(
            tenants=[_tenant_record()],
            credentials=[_credential_record()],
        ),
        logger=logger,
    )

    access_token = await verifier.verify_token("dev-token")

    assert access_token is not None
    assert access_token.identity == identity
    assert access_token.tenant.tenant_id == "tenant-1"
    assert access_token.tenant.tenant_slug == "tenant-one"
    assert access_token.tenant.credential_id == "credential-1"
    assert access_token.client_id == "portal-app"
    assert access_token.scopes == ["tools:read"]
    log_output = stream.getvalue()
    assert '"event": "hosted_auth_succeeded"' in log_output
    assert '"event": "tenant_resolution_succeeded"' in log_output
    assert '"tenant_id": "tenant-1"' in log_output
    assert '"tenant_slug": "tenant-one"' in log_output
    assert '"credential_id": "credential-1"' in log_output
    assert '"token_id": "token-123"' in log_output
    assert "dev-token" not in log_output


@pytest.mark.asyncio
async def test_hosted_tenant_token_verifier_returns_none_for_wrong_tenant_binding() -> None:
    """Credential bindings on the token should fail closed when they mismatch."""
    stream = io.StringIO()
    logger = logging.getLogger("followupboss_mcp_test_hosted_auth_failure_audit")
    logger.handlers.clear()
    logger.setLevel("INFO")
    logger.propagate = False
    logger.addHandler(logging.StreamHandler(stream))
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
        logger=logger,
    )

    assert await verifier.verify_token("wrong-tenant-token") is None
    log_output = stream.getvalue()
    assert '"event": "hosted_auth_succeeded"' in log_output
    assert '"event": "tenant_resolution_failed"' in log_output
    assert '"reason": "credential_binding_mismatch"' in log_output
    assert "wrong-tenant-token" not in log_output


@pytest.mark.asyncio
async def test_hosted_tenant_token_verifier_emits_audit_event_for_failed_verification() -> None:
    """Unknown bearer tokens should emit a safe auth-failure audit event."""
    stream = io.StringIO()
    logger = logging.getLogger("followupboss_mcp_test_hosted_auth_invalid_token_audit")
    logger.handlers.clear()
    logger.setLevel("INFO")
    logger.propagate = False
    logger.addHandler(logging.StreamHandler(stream))
    verifier = HostedTenantTokenVerifier(
        identity_verifier=DevelopmentHostedTokenVerifier.from_mapping({}),
        tenant_store=DevelopmentTenantStore(
            tenants=[_tenant_record()],
            credentials=[_credential_record()],
        ),
        logger=logger,
    )

    assert await verifier.verify_token("missing-token") is None
    log_output = stream.getvalue()
    assert '"event": "hosted_auth_failed"' in log_output
    assert '"reason": "token_verification_failed"' in log_output
    assert "missing-token" not in log_output
