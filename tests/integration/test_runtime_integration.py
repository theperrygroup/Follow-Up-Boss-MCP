"""Integration tests for runtime entrypoints and server lifecycle behavior."""

from __future__ import annotations

import runpy
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

import followupboss_mcp.cli as cli_module
from followupboss_mcp.auth import AuthMode
from followupboss_mcp.config import FollowUpBossSettings, FollowUpBossTenantRuntimeDefaults
from followupboss_mcp.constants import (
    DEFAULT_BASE_URL,
    DEFAULT_MAX_RETRIES,
    DEFAULT_TIMEOUT_SECONDS,
)
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


class ClosingClient:
    """Queue-free client stub that records lifecycle closure."""

    def __init__(self) -> None:
        self.closed = False

    async def aclose(self) -> None:
        """Close the stub client."""
        self.closed = True

    async def request_json(self, method: str, path: str, **_: object) -> dict[str, object]:
        """Return a minimal JSON payload."""
        del method, path
        return {"id": 1}


@pytest.mark.asyncio
async def test_create_server_lifespan_closes_injected_client() -> None:
    """The server lifespan should close the injected client on shutdown."""
    client = ClosingClient()
    server = create_server(FollowUpBossSettings.model_validate({"api_key": "key"}), client=client)
    async with server._lowlevel_server.lifespan(server._lowlevel_server):
        assert client.closed is False
    assert client.closed is True


def test_create_server_hosted_mode_uses_builtin_runtime_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Hosted bootstrap should ignore tenant env vars unless defaults are passed explicitly."""
    captured_defaults: list[FollowUpBossTenantRuntimeDefaults] = []

    class RecordingRuntimeFactory:
        """Capture the hosted runtime defaults passed into server construction."""

        def __init__(
            self,
            *,
            default_settings: FollowUpBossTenantRuntimeDefaults,
            tenant_store: object,
            logger: object | None = None,
            client_factory: object | None = None,
        ) -> None:
            """Record the provided hosted runtime defaults."""
            del tenant_store, logger, client_factory
            captured_defaults.append(default_settings)

        @asynccontextmanager
        async def service_bundle_for_current_tenant(self) -> AsyncIterator[object]:
            """Yield a placeholder bundle if the resolver is ever exercised."""
            yield object()

    monkeypatch.setenv("FOLLOWUPBOSS_AUTH_MODE", "oauth")
    monkeypatch.delenv("FOLLOWUPBOSS_API_KEY", raising=False)
    monkeypatch.delenv("FOLLOWUPBOSS_ACCESS_TOKEN", raising=False)
    monkeypatch.setenv("FOLLOWUPBOSS_BASE_URL", "https://ignored.example.com/v1/")
    monkeypatch.setenv("FOLLOWUPBOSS_TIMEOUT_SECONDS", "99")
    monkeypatch.setenv("FOLLOWUPBOSS_MAX_RETRIES", "42")
    monkeypatch.setattr("followupboss_mcp.mcp_server.TenantRuntimeFactory", RecordingRuntimeFactory)

    create_server(
        hosted_auth=HostedAuthSettings.model_validate(
            {
                "issuer_url": "https://issuer.example.com",
                "resource_server_url": "https://mcp.example.com/mcp",
            }
        ),
        hosted_token_verifier=DevelopmentHostedTokenVerifier.from_mapping(
            {
                "dev-token": HostedVerifiedIdentity.model_validate(
                    {
                        "tenant_id": "tenant-1",
                        "subject": "user-123",
                        "client_id": "portal-app",
                    }
                )
            }
        ),
        tenant_store=DevelopmentTenantStore(
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
        ),
    )

    assert len(captured_defaults) == 1
    defaults = captured_defaults[0]
    assert str(defaults.base_url) == DEFAULT_BASE_URL
    assert defaults.timeout_seconds == DEFAULT_TIMEOUT_SECONDS
    assert defaults.max_retries == DEFAULT_MAX_RETRIES


def test_cli_module_runs_main_when_executed_as_script(monkeypatch: pytest.MonkeyPatch) -> None:
    """Executing the CLI module as a script should trigger the `__main__` block."""
    created_settings: list[object] = []
    runs: list[tuple[str, Any]] = []

    @dataclass
    class FakeServerSettings:
        """Tiny server-settings stand-in for CLI entrypoint tests."""

        transport: str = "stdio"
        host: str = "127.0.0.1"
        port: int = 8000
        streamable_http_path: str = "/mcp"

        def model_copy(self, *, update: dict[str, Any]) -> FakeServerSettings:
            """Return a copied settings object with updates applied."""
            return FakeServerSettings(
                transport=str(update.get("transport", self.transport)),
                host=str(update.get("host", self.host)),
                port=int(update.get("port", self.port)),
                streamable_http_path=str(
                    update.get(
                        "streamable_http_path",
                        self.streamable_http_path,
                    )
                ),
            )

    class FakeServer:
        def run(self, transport: str) -> None:
            runs.append(("run", transport))

    def fake_create_server(settings: object, **kwargs: object) -> FakeServer:
        created_settings.append(settings)
        runs.append(("create", {"kwargs": kwargs, "settings": settings}))
        return FakeServer()

    monkeypatch.setattr("followupboss_mcp.config.FollowUpBossSettings", lambda: object())
    monkeypatch.setattr(
        "followupboss_mcp.config.FollowUpBossServerSettings",
        lambda: FakeServerSettings(),
    )
    monkeypatch.setattr("followupboss_mcp.mcp_server.create_server", fake_create_server)
    monkeypatch.setattr(sys, "argv", ["followupboss_mcp.cli", "stdio"])

    module_path = Path(cli_module.__file__).resolve()
    with pytest.raises(SystemExit) as exc_info:
        runpy.run_path(str(module_path), run_name="__main__")

    assert exc_info.value.code == 0
    assert runs[0][0] == "create"
    assert runs[0][1] == {
        "kwargs": {
            "server_settings": FakeServerSettings(),
        },
        "settings": created_settings[0],
    }
    assert runs[1] == ("run", "stdio")
