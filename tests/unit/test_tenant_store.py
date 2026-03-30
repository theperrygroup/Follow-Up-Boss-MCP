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
    TenantSecretStoreUnavailableError,
    TenantStoreUnavailableError,
)
from followupboss_mcp.tenant_store import (
    DevelopmentTenantStore,
    TenantCredentialRecord,
    TenantCredentialStatus,
    TenantRecord,
    TenantStatus,
    TenantStore,
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


class UnavailableTenantMetadataStore(TenantStore):
    """Tenant store stub whose metadata backend is unavailable."""

    async def get_tenant(self, tenant_id: str) -> TenantRecord | None:
        """Fail while loading tenant metadata."""
        del tenant_id
        raise RuntimeError("tenant database unavailable")

    async def get_credential(self, credential_id: str) -> TenantCredentialRecord | None:
        """Return no credential because metadata lookup should fail first."""
        del credential_id
        return None


class UnavailableTenantSecretStore(TenantStore):
    """Tenant store stub whose credential backend is unavailable."""

    async def get_tenant(self, tenant_id: str) -> TenantRecord | None:
        """Return one tenant so credential resolution is attempted."""
        del tenant_id
        return _tenant_record()

    async def get_credential(self, credential_id: str) -> TenantCredentialRecord | None:
        """Fail while loading tenant credential material."""
        del credential_id
        raise RuntimeError("secret backend unavailable")


class PassthroughTenantMetadataErrorStore(TenantStore):
    """Tenant store stub that raises an already-safe metadata error."""

    async def get_tenant(self, tenant_id: str) -> TenantRecord | None:
        """Raise a safe metadata-store error directly."""
        del tenant_id
        raise TenantStoreUnavailableError("safe metadata failure")

    async def get_credential(self, credential_id: str) -> TenantCredentialRecord | None:
        """Return no credential because metadata lookup should fail first."""
        del credential_id
        return None


class PassthroughTenantSecretErrorStore(TenantStore):
    """Tenant store stub that raises an already-safe secret-store error."""

    async def get_tenant(self, tenant_id: str) -> TenantRecord | None:
        """Return one tenant so credential lookup is attempted."""
        del tenant_id
        return _tenant_record()

    async def get_credential(self, credential_id: str) -> TenantCredentialRecord | None:
        """Raise a safe secret-store error directly."""
        del credential_id
        raise TenantSecretStoreUnavailableError("safe secret failure")


def test_tenant_record_and_credential_record_validation() -> None:
    """Tenant records and credential records should validate required fields."""
    tenant = _tenant_record(display_name="  Tenant One  ")
    assert tenant.display_name == "Tenant One"
    assert _tenant_record(display_name=None).display_name is None

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
    assert oauth_record.system_key_value() is None

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
    with pytest.raises(ValidationError):
        TenantCredentialRecord.model_validate(
            {
                "credential_id": "credential-1",
                "tenant_id": "tenant-1",
                "auth_mode": AuthMode.OAUTH,
                "api_key": None,
                "access_token": None,
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
    duplicate_slug_tenant = _tenant_record(tenant_id="tenant-2", tenant_slug="tenant-one")
    credential = _credential_record()
    duplicate_credential = _credential_record(
        credential_id="credential-1",
        tenant_id="tenant-2",
        api_key="secret-key-two",
    )

    with pytest.raises(ValidationError):
        DevelopmentTenantStore(
            tenants=[tenant, duplicate_tenant],
            credentials=[credential],
        )
    with pytest.raises(ValidationError):
        DevelopmentTenantStore(
            tenants=[tenant, duplicate_slug_tenant],
            credentials=[credential],
        )
    with pytest.raises(ValidationError):
        DevelopmentTenantStore(
            tenants=[tenant, _tenant_record(tenant_id="tenant-2", tenant_slug="tenant-two")],
            credentials=[credential, duplicate_credential],
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


@pytest.mark.asyncio
async def test_tenant_store_wraps_unavailable_metadata_backend() -> None:
    """Unexpected tenant-store metadata failures should map to a safe store error."""
    with pytest.raises(TenantStoreUnavailableError, match="Tenant store is unavailable."):
        await UnavailableTenantMetadataStore().resolve_tenant("tenant-1")


@pytest.mark.asyncio
async def test_tenant_store_wraps_unavailable_secret_backend() -> None:
    """Unexpected secret-store failures should map to a safe secret-store error."""
    with pytest.raises(
        TenantSecretStoreUnavailableError,
        match="Tenant secret store is unavailable.",
    ):
        await UnavailableTenantSecretStore().resolve_tenant("tenant-1")


@pytest.mark.asyncio
async def test_tenant_store_preserves_existing_safe_metadata_errors() -> None:
    """Existing tenant-store errors should be re-raised instead of wrapped again."""
    with pytest.raises(TenantStoreUnavailableError, match="safe metadata failure"):
        await PassthroughTenantMetadataErrorStore().resolve_tenant("tenant-1")


@pytest.mark.asyncio
async def test_tenant_store_preserves_existing_safe_secret_errors() -> None:
    """Existing secret-store errors should be re-raised instead of wrapped again."""
    with pytest.raises(TenantSecretStoreUnavailableError, match="safe secret failure"):
        await PassthroughTenantSecretErrorStore().resolve_tenant("tenant-1")
