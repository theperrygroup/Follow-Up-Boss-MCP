"""Tests for the tenant-store abstractions and development store."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from followupboss_mcp.auth import AuthMode, BasicAuthStrategy, BearerAuthStrategy
from followupboss_mcp.config import FollowUpBossSettings
from followupboss_mcp.errors import (
    TenantCredentialNotFoundError,
    TenantCredentialRevokedError,
    TenantDisabledError,
    TenantNotFoundError,
)
from followupboss_mcp.tenant_store import (
    DevelopmentTenantStore,
    TenantCredentialRecord,
    TenantCredentialStatus,
    TenantRecord,
    TenantStatus,
)


def _tenant_record(**overrides: object) -> TenantRecord:
    """Build a representative tenant record for tests.

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
    """Build a representative credential record for tests.

    Args:
        **overrides: Field overrides for the default credential payload.

    Returns:
        A validated tenant credential record.
    """
    payload: dict[str, object] = {
        "credential_id": "credential-1",
        "tenant_id": "tenant-1",
        "auth_mode": AuthMode.API_KEY,
        "api_key": "secret-key",
        "system_name": "Local System",
        "system_key": "system-secret",
        "status": TenantCredentialStatus.ACTIVE,
    }
    payload.update(overrides)
    return TenantCredentialRecord.model_validate(payload)


def test_tenant_record_and_credential_record_validation() -> None:
    """Tenant records and credential records should validate required fields."""
    tenant = _tenant_record(display_name="  Tenant One  ")
    assert tenant.display_name == "Tenant One"

    api_key_record = _credential_record(system_name="  Local System  ")
    assert api_key_record.system_name == "Local System"
    assert api_key_record.system_key_value() == "system-secret"
    assert isinstance(api_key_record.auth_strategy(), BasicAuthStrategy)
    assert "secret-key" not in repr(api_key_record)
    assert "system-secret" not in repr(api_key_record)

    oauth_record = _credential_record(
        auth_mode=AuthMode.OAUTH,
        api_key=None,
        access_token="oauth-token",
        system_key=None,
    )
    assert isinstance(oauth_record.auth_strategy(), BearerAuthStrategy)

    with pytest.raises(ValidationError):
        TenantRecord.model_validate(
            {
                "tenant_id": " ",
                "tenant_slug": "tenant-one",
                "credential_id": "credential-1",
            }
        )
    with pytest.raises(ValidationError):
        TenantCredentialRecord.model_validate(
            {
                "credential_id": "credential-1",
                "tenant_id": "tenant-1",
                "auth_mode": AuthMode.API_KEY,
            }
        )


def test_development_tenant_store_from_json_and_file(tmp_path: Path) -> None:
    """The development store should load the same document from JSON or disk."""
    document_json = json.dumps(
        {
            "tenants": [
                {
                    "tenant_id": "tenant-1",
                    "tenant_slug": "tenant-one",
                    "display_name": "Tenant One",
                    "credential_id": "credential-1",
                    "status": "active",
                }
            ],
            "credentials": [
                {
                    "credential_id": "credential-1",
                    "tenant_id": "tenant-1",
                    "auth_mode": "api_key",
                    "api_key": "secret-key",
                    "system_name": "Local System",
                    "system_key": "system-secret",
                    "status": "active",
                }
            ],
        }
    )

    from_json = DevelopmentTenantStore.from_json(document_json)
    document_path = tmp_path / "tenant-store.json"
    document_path.write_text(document_json, encoding="utf-8")
    from_file = DevelopmentTenantStore.from_file(document_path)

    assert from_json.snapshot() == from_file.snapshot()
    assert from_json.snapshot().tenants[0].tenant_id == "tenant-1"
    assert from_json.snapshot().credentials[0].credential_id == "credential-1"


def test_development_tenant_store_rejects_duplicate_identifiers() -> None:
    """The development store should reject duplicate tenant or credential IDs."""
    tenant = _tenant_record()
    duplicate_tenant = _tenant_record(tenant_id="tenant-1", tenant_slug="tenant-two")
    credential = _credential_record()

    with pytest.raises(ValidationError):
        DevelopmentTenantStore(
            tenants=[tenant, duplicate_tenant],
            credentials=[credential],
        )


@pytest.mark.asyncio
async def test_development_tenant_store_resolves_active_tenant() -> None:
    """The development store should resolve an active tenant and active credential."""
    tenant = _tenant_record()
    credential = _credential_record()
    store = DevelopmentTenantStore(tenants=[tenant], credentials=[credential])

    resolved = await store.resolve_tenant("tenant-1")

    assert await store.get_tenant("tenant-1") == tenant
    assert await store.get_credential("credential-1") == credential
    assert resolved.tenant == tenant
    assert resolved.credential == credential


@pytest.mark.asyncio
async def test_development_tenant_store_from_local_dev_settings() -> None:
    """Local single-tenant settings should be wrappable in the dev store."""
    settings = FollowUpBossSettings.model_validate(
        {
            "auth_mode": AuthMode.OAUTH,
            "access_token": "oauth-token",
            "system_name": "  Local System  ",
            "system_key": "system-secret",
        }
    )

    store = DevelopmentTenantStore.from_local_dev_settings(
        settings,
        tenant_id="demo-tenant",
        tenant_slug="demo",
        display_name="  Demo Tenant  ",
        credential_id="demo-credential",
    )

    resolved = await store.resolve_tenant("demo-tenant")

    assert resolved.tenant.tenant_id == "demo-tenant"
    assert resolved.tenant.tenant_slug == "demo"
    assert resolved.tenant.display_name == "Demo Tenant"
    assert resolved.credential.credential_id == "demo-credential"
    assert resolved.credential.auth_mode is AuthMode.OAUTH
    assert resolved.credential.system_name == "Local System"
    assert resolved.credential.system_key_value() == "system-secret"
    assert isinstance(resolved.credential.auth_strategy(), BearerAuthStrategy)


@pytest.mark.asyncio
async def test_development_tenant_store_raises_for_unknown_tenant() -> None:
    """Unknown tenant IDs should fail with a tenant-not-found error."""
    store = DevelopmentTenantStore(tenants=[], credentials=[])

    with pytest.raises(TenantNotFoundError):
        await store.resolve_tenant("missing-tenant")


@pytest.mark.asyncio
async def test_development_tenant_store_raises_for_disabled_tenant() -> None:
    """Disabled tenants should fail before credential resolution."""
    store = DevelopmentTenantStore(
        tenants=[_tenant_record(status=TenantStatus.DISABLED)],
        credentials=[_credential_record()],
    )

    with pytest.raises(TenantDisabledError):
        await store.resolve_tenant("tenant-1")


@pytest.mark.asyncio
async def test_development_tenant_store_raises_for_missing_credential() -> None:
    """Missing credential records should fail closed."""
    store = DevelopmentTenantStore(
        tenants=[_tenant_record(credential_id="missing-credential")],
        credentials=[],
    )

    with pytest.raises(TenantCredentialNotFoundError):
        await store.resolve_tenant("tenant-1")


@pytest.mark.asyncio
async def test_development_tenant_store_raises_for_revoked_credential() -> None:
    """Revoked credentials should fail closed."""
    store = DevelopmentTenantStore(
        tenants=[_tenant_record()],
        credentials=[_credential_record(status=TenantCredentialStatus.REVOKED)],
    )

    with pytest.raises(TenantCredentialRevokedError):
        await store.resolve_tenant("tenant-1")
