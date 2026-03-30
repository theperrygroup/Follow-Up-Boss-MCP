"""Focused unit tests for tenant runtime models and request-scoped factories."""

from __future__ import annotations

import io
import logging
from typing import cast

import pytest

from followupboss_mcp.auth import AuthMode
from followupboss_mcp.config import (
    FollowUpBossTenantRuntimeDefaults,
    FollowUpBossTenantSettings,
)
from followupboss_mcp.errors import TenantCredentialNotFoundError
from followupboss_mcp.hosted_auth import HostedAuthenticatedTenant
from followupboss_mcp.http_client import FollowUpBossAsyncClient, FollowUpBossClientProtocol
from followupboss_mcp.tenant_runtime import (
    RequestScopedTenantServiceBundleResolver,
    TenantRuntimeFactory,
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
    """Build a representative tenant record for runtime-factory tests.

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
    """Build a representative credential record for runtime-factory tests.

    Args:
        **overrides: Field overrides for the default credential payload.

    Returns:
        A validated tenant credential record.
    """
    payload: dict[str, object] = {
        "credential_id": "credential-1",
        "tenant_id": "tenant-1",
        "auth_mode": AuthMode.API_KEY,
        "api_key": "tenant-one-api-key",
        "system_name": "Tenant One System",
        "system_key": "tenant-one-system-key",
        "status": TenantCredentialStatus.ACTIVE,
    }
    payload.update(overrides)
    return TenantCredentialRecord.model_validate(payload)


class UnavailableSecretStore(TenantStore):
    """Tenant store stub whose credential backend is unavailable."""

    async def get_tenant(self, tenant_id: str) -> TenantRecord | None:
        """Return one active tenant for runtime-factory tests."""
        del tenant_id
        return _tenant_record()

    async def get_credential(self, credential_id: str) -> TenantCredentialRecord | None:
        """Fail while loading tenant credential material."""
        del credential_id
        raise RuntimeError("secret backend unavailable")


class RecordingClient:
    """Minimal Follow Up Boss client stub used for runtime-factory tests."""

    async def aclose(self) -> None:
        """Close the stub client."""

    async def request_json(
        self,
        method: str,
        path: str,
        *,
        headers: dict[str, str] | None = None,
        json_body: dict[str, object] | None = None,
        params: dict[str, str] | None = None,
    ) -> dict[str, object]:
        """Return one deterministic payload for protocol compatibility."""
        del method, path, headers, json_body, params
        return {"ok": True}


class ClosingRecordingClient(RecordingClient):
    """Client stub that records whether cleanup ran."""

    def __init__(self) -> None:
        """Initialize the cleanup-tracking client stub."""
        self.closed = False

    async def aclose(self) -> None:
        """Record that cleanup ran for the client."""
        self.closed = True


def _authenticated_tenant(**overrides: object) -> HostedAuthenticatedTenant:
    """Build a representative authenticated tenant context for tests.

    Args:
        **overrides: Field overrides for the default authenticated payload.

    Returns:
        A validated authenticated tenant context.
    """
    payload: dict[str, object] = {
        "tenant_id": "tenant-1",
        "tenant_slug": "tenant-one",
        "display_name": "Tenant One",
        "credential_id": "credential-1",
    }
    payload.update(overrides)
    return HostedAuthenticatedTenant.model_validate(payload)


@pytest.mark.asyncio
async def test_tenant_runtime_factory_builds_runtime_from_authenticated_tenant() -> None:
    """The runtime factory should merge tenant credentials with shared defaults."""
    default_settings = FollowUpBossTenantRuntimeDefaults.model_validate(
        {
            "base_url": "https://api.followupboss.com/v1/",
            "timeout_seconds": 12,
            "max_retries": 2,
        }
    )
    tenant_store = DevelopmentTenantStore(
        tenants=[_tenant_record()],
        credentials=[_credential_record()],
    )
    factory = TenantRuntimeFactory(
        default_settings=default_settings,
        tenant_store=tenant_store,
    )
    authenticated_tenant = HostedAuthenticatedTenant.model_validate(
        {
            "tenant_id": "tenant-1",
            "tenant_slug": "tenant-one",
            "display_name": "Tenant One",
            "credential_id": "credential-1",
        }
    )

    runtime = await factory.runtime_from_authenticated_tenant(authenticated_tenant)

    assert runtime.tenant == authenticated_tenant
    assert runtime.settings.auth_mode is AuthMode.API_KEY
    assert runtime.settings.api_key is not None
    assert runtime.settings.api_key.get_secret_value() == "tenant-one-api-key"
    assert runtime.settings.system_name == "Tenant One System"
    assert runtime.settings.system_key_value() == "tenant-one-system-key"
    assert str(runtime.settings.base_url) == "https://api.followupboss.com/v1"
    assert runtime.settings.timeout_seconds == 12
    assert runtime.settings.max_retries == 2


@pytest.mark.asyncio
async def test_tenant_runtime_factory_emits_audit_event_for_upstream_credential_usage() -> None:
    """Creating a tenant client should emit a non-secret upstream audit event."""
    stream = io.StringIO()
    logger = logging.getLogger("followupboss_mcp_test_tenant_runtime_audit")
    logger.handlers.clear()
    logger.setLevel("INFO")
    logger.propagate = False
    logger.addHandler(logging.StreamHandler(stream))
    factory = TenantRuntimeFactory(
        default_settings=FollowUpBossTenantRuntimeDefaults.model_validate({}),
        tenant_store=DevelopmentTenantStore(
            tenants=[_tenant_record()],
            credentials=[_credential_record()],
        ),
        logger=logger,
        client_factory=lambda settings, logger: cast(
            FollowUpBossClientProtocol,
            RecordingClient(),
        ),
    )
    authenticated_tenant = HostedAuthenticatedTenant.model_validate(
        {
            "tenant_id": "tenant-1",
            "tenant_slug": "tenant-one",
            "display_name": "Tenant One",
            "credential_id": "credential-1",
        }
    )

    runtime = await factory.runtime_from_authenticated_tenant(authenticated_tenant)
    client = factory.create_client(runtime)

    assert isinstance(client, RecordingClient)
    log_output = stream.getvalue()
    assert '"event": "upstream_credential_usage"' in log_output
    assert '"tenant_id": "tenant-1"' in log_output
    assert '"tenant_slug": "tenant-one"' in log_output
    assert '"credential_id": "credential-1"' in log_output
    assert '"auth_mode": "api_key"' in log_output
    assert "tenant-one-api-key" not in log_output
    assert "tenant-one-system-key" not in log_output


@pytest.mark.asyncio
async def test_tenant_runtime_factory_rejects_mismatched_authenticated_credential() -> None:
    """Mismatched authenticated credential bindings should fail closed."""
    factory = TenantRuntimeFactory(
        default_settings=FollowUpBossTenantRuntimeDefaults.model_validate({}),
        tenant_store=DevelopmentTenantStore(
            tenants=[_tenant_record()],
            credentials=[_credential_record()],
        ),
    )
    authenticated_tenant = HostedAuthenticatedTenant.model_validate(
        {
            "tenant_id": "tenant-1",
            "tenant_slug": "tenant-one",
            "display_name": "Tenant One",
            "credential_id": "wrong-credential",
        }
    )

    with pytest.raises(TenantCredentialNotFoundError):
        await factory.runtime_from_authenticated_tenant(authenticated_tenant)


@pytest.mark.asyncio
async def test_tenant_runtime_factory_resolves_current_tenant_from_auth_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The runtime factory should resolve the current hosted tenant from auth context."""
    authenticated_tenant = HostedAuthenticatedTenant.model_validate(
        {
            "tenant_id": "tenant-1",
            "tenant_slug": "tenant-one",
            "display_name": "Tenant One",
            "credential_id": "credential-1",
        }
    )
    monkeypatch.setattr(
        "followupboss_mcp.tenant_runtime.get_hosted_authenticated_tenant",
        lambda: authenticated_tenant,
    )
    factory = TenantRuntimeFactory(
        default_settings=FollowUpBossTenantRuntimeDefaults.model_validate({}),
        tenant_store=DevelopmentTenantStore(
            tenants=[_tenant_record()],
            credentials=[_credential_record()],
        ),
    )

    runtime = await factory.runtime_for_current_tenant()

    assert runtime.tenant == authenticated_tenant
    assert runtime.settings.api_key is not None
    assert runtime.settings.api_key.get_secret_value() == "tenant-one-api-key"


@pytest.mark.asyncio
async def test_tenant_runtime_factory_rejects_missing_auth_context() -> None:
    """Missing hosted auth context should fail closed when resolving current runtime."""
    factory = TenantRuntimeFactory(
        default_settings=FollowUpBossTenantRuntimeDefaults.model_validate({}),
        tenant_store=DevelopmentTenantStore(
            tenants=[_tenant_record()],
            credentials=[_credential_record()],
        ),
    )

    with pytest.raises(RuntimeError, match="Hosted tenant runtime is unavailable."):
        await factory.runtime_for_current_tenant()


@pytest.mark.asyncio
async def test_tenant_runtime_factory_rejects_unavailable_secret_store(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unavailable tenant secret storage should fail closed with a safe error."""
    authenticated_tenant = HostedAuthenticatedTenant.model_validate(
        {
            "tenant_id": "tenant-1",
            "tenant_slug": "tenant-one",
            "display_name": "Tenant One",
            "credential_id": "credential-1",
        }
    )
    monkeypatch.setattr(
        "followupboss_mcp.tenant_runtime.get_hosted_authenticated_tenant",
        lambda: authenticated_tenant,
    )
    factory = TenantRuntimeFactory(
        default_settings=FollowUpBossTenantRuntimeDefaults.model_validate({}),
        tenant_store=UnavailableSecretStore(),
    )

    with pytest.raises(RuntimeError, match="Hosted tenant runtime is unavailable.") as exc_info:
        await factory.runtime_for_current_tenant()

    assert "secret backend unavailable" not in str(exc_info.value)


def test_tenant_runtime_factory_accepts_tenant_settings_defaults() -> None:
    """Tenant settings inputs should be reduced to runtime defaults."""
    factory = TenantRuntimeFactory(
        default_settings=FollowUpBossTenantSettings.model_validate(
            {
                "auth_mode": AuthMode.API_KEY,
                "api_key": "bootstrap-api-key",
                "base_url": "https://example.followupboss.test/v1/",
                "timeout_seconds": 21,
                "max_retries": 4,
            }
        ),
        tenant_store=DevelopmentTenantStore(
            tenants=[_tenant_record()],
            credentials=[_credential_record(api_key="tenant-runtime-api-key")],
        ),
    )

    projected_settings = factory.settings_from_credential(_credential_record())

    assert projected_settings.api_key is not None
    assert projected_settings.api_key.get_secret_value() == "tenant-one-api-key"
    assert str(projected_settings.base_url) == "https://example.followupboss.test/v1"
    assert projected_settings.timeout_seconds == 21
    assert projected_settings.max_retries == 4


@pytest.mark.asyncio
async def test_tenant_runtime_factory_service_bundle_for_tenant_closes_client() -> None:
    """Tenant-specific service bundles should always close their request client."""
    created_clients: list[ClosingRecordingClient] = []

    def client_factory(
        settings: FollowUpBossTenantSettings,
        logger: logging.Logger | None,
    ) -> FollowUpBossClientProtocol:
        del settings, logger
        client = ClosingRecordingClient()
        created_clients.append(client)
        return cast(FollowUpBossClientProtocol, client)

    factory = TenantRuntimeFactory(
        default_settings=FollowUpBossTenantRuntimeDefaults.model_validate({}),
        tenant_store=DevelopmentTenantStore(
            tenants=[_tenant_record()],
            credentials=[_credential_record()],
        ),
        client_factory=client_factory,
    )

    async with factory.service_bundle_for_tenant(_authenticated_tenant()) as services:
        assert services.identity is not None

    assert len(created_clients) == 1
    assert created_clients[0].closed is True


@pytest.mark.asyncio
async def test_request_scoped_service_bundle_resolver_uses_current_tenant_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The request-scoped resolver should reuse the current auth context safely."""
    created_clients: list[ClosingRecordingClient] = []

    def client_factory(
        settings: FollowUpBossTenantSettings,
        logger: logging.Logger | None,
    ) -> FollowUpBossClientProtocol:
        del settings, logger
        client = ClosingRecordingClient()
        created_clients.append(client)
        return cast(FollowUpBossClientProtocol, client)

    monkeypatch.setattr(
        "followupboss_mcp.tenant_runtime.get_hosted_authenticated_tenant",
        lambda: _authenticated_tenant(),
    )
    factory = TenantRuntimeFactory(
        default_settings=FollowUpBossTenantRuntimeDefaults.model_validate({}),
        tenant_store=DevelopmentTenantStore(
            tenants=[_tenant_record()],
            credentials=[_credential_record()],
        ),
        client_factory=client_factory,
    )
    resolver = RequestScopedTenantServiceBundleResolver(factory)

    async with resolver.service_bundle() as services:
        assert services.people is not None

    assert len(created_clients) == 1
    assert created_clients[0].closed is True


@pytest.mark.asyncio
async def test_tenant_runtime_factory_default_client_factory_builds_async_client() -> None:
    """The default client factory should return the shared async client type."""
    settings = FollowUpBossTenantSettings.model_validate(
        {
            "auth_mode": AuthMode.API_KEY,
            "api_key": "runtime-api-key",
        }
    )

    client = TenantRuntimeFactory._default_client_factory(settings, logger=None)

    assert isinstance(client, FollowUpBossAsyncClient)
    await client.aclose()
