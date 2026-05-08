"""End-to-end hosted-auth tests for the streamable HTTP transport."""

from __future__ import annotations

import asyncio
import json
import os
import socket
import sys
import textwrap
from pathlib import Path

import httpx
import pytest

from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.shared.exceptions import McpError

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _reserve_port() -> int:
    """Return one currently unused loopback TCP port.

    Returns:
        An available TCP port bound from the local loopback interface.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        sock.listen(1)
        return int(sock.getsockname()[1])


async def _wait_for_port(host: str, port: int, *, attempts: int = 50) -> None:
    """Wait until one TCP port accepts connections.

    Args:
        host: The loopback host that should accept connections.
        port: The TCP port that should accept connections.
        attempts: Maximum connection attempts before failing.

    Raises:
        AssertionError: If the server does not start listening in time.
    """
    for _ in range(attempts):
        try:
            reader, writer = await asyncio.open_connection(host, port)
        except OSError:
            await asyncio.sleep(0.1)
            continue
        writer.close()
        await writer.wait_closed()
        return
    raise AssertionError(f"Timed out waiting for {host}:{port} to accept connections.")


def _server_python_env() -> dict[str, str]:
    """Build the environment used by subprocess-based MCP server tests.

    Returns:
        An environment mapping that exposes the repository's `src/` layout to the
        subprocess server under test.
    """
    server_env = dict(os.environ)
    existing_pythonpath = server_env.get("PYTHONPATH")
    pythonpath_entries = [str(PROJECT_ROOT / "src")]
    if existing_pythonpath:
        pythonpath_entries.append(existing_pythonpath)
    server_env["PYTHONPATH"] = os.pathsep.join(pythonpath_entries)
    return server_env


@pytest.mark.asyncio
async def test_streamable_http_hosted_auth_supports_authenticated_official_client() -> None:
    """The official client should work end to end with hosted bearer auth."""
    port = _reserve_port()
    server_script = textwrap.dedent(
        f"""
        from collections.abc import Mapping

        from followupboss_mcp.auth import AuthMode
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


        class QueueClient:
            def __init__(self) -> None:
                self.responses = [
                    {{"id": 1, "name": "Picard"}},
                ]

            async def aclose(self) -> None:
                return None

            async def request_json(
                self,
                method: str,
                path: str,
                *,
                headers: Mapping[str, str] | None = None,
                json_body: Mapping[str, object] | None = None,
                params: Mapping[str, str] | None = None,
            ) -> dict[str, object]:
                del method, path, headers, json_body, params
                return self.responses.pop(0)


        tenant_store = DevelopmentTenantStore(
            tenants=[
                TenantRecord.model_validate(
                    {{
                        "tenant_id": "tenant-1",
                        "tenant_slug": "tenant-one",
                        "display_name": "Tenant One",
                        "credential_id": "credential-1",
                        "status": TenantStatus.ACTIVE,
                    }}
                )
            ],
            credentials=[
                TenantCredentialRecord.model_validate(
                    {{
                        "credential_id": "credential-1",
                        "tenant_id": "tenant-1",
                        "auth_mode": AuthMode.API_KEY,
                        "api_key": "secret-key",
                        "status": TenantCredentialStatus.ACTIVE,
                    }}
                )
            ],
        )

        hosted_token_verifier = DevelopmentHostedTokenVerifier.from_mapping(
            {{
                "dev-token": HostedVerifiedIdentity.model_validate(
                    {{
                        "tenant_id": "tenant-1",
                        "subject": "user-123",
                        "client_id": "portal-app",
                    }}
                )
            }}
        )

        hosted_auth = HostedAuthSettings.model_validate(
            {{
                "issuer_url": "https://issuer.example.com",
                "resource_server_url": "http://127.0.0.1:{port}/mcp",
            }}
        )

        create_server(
            hosted_auth=hosted_auth,
            hosted_token_verifier=hosted_token_verifier,
            tenant_store=tenant_store,
            tenant_client_factory=lambda settings, logger: QueueClient(),
            host="127.0.0.1",
            port={port},
            streamable_http_path="/mcp",
        ).run(transport="streamable-http")
        """
    )
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        "-c",
        server_script,
        cwd=str(PROJECT_ROOT),
        env=_server_python_env(),
    )
    try:
        await _wait_for_port("127.0.0.1", port)
        async with httpx.AsyncClient(
            headers={"Authorization": "Bearer dev-token"},
        ) as http_client:
            async with streamable_http_client(
                f"http://127.0.0.1:{port}/mcp",
                http_client=http_client,
            ) as (
                read_stream,
                write_stream,
                _,
            ):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    identity_result = await session.call_tool("followupboss_get_identity")
                    assert identity_result.isError is False
                    assert identity_result.structuredContent == {"id": 1, "name": "Picard"}
    finally:
        process.terminate()
        await process.wait()


@pytest.mark.asyncio
async def test_streamable_http_hosted_auth_isolates_tools_resources_and_prompts_per_bearer_token(
    tmp_path: Path,
) -> None:
    """Different bearer tokens should isolate every tenant-aware MCP surface."""
    port = _reserve_port()
    output_path = tmp_path / "tenant-runtime-events.jsonl"
    server_script = textwrap.dedent(
        f"""
        import json
        from collections.abc import Mapping
        from pathlib import Path

        import followupboss_mcp.tenant_runtime as tenant_runtime
        from followupboss_mcp.auth import AuthMode
        from followupboss_mcp.config import FollowUpBossSettings, FollowUpBossTenantSettings
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

        OUTPUT_PATH = Path({str(output_path)!r})


        def _record_event(payload: dict[str, object]) -> None:
            with OUTPUT_PATH.open("a", encoding="utf-8") as output_file:
                output_file.write(json.dumps(payload) + "\\n")


        class RecordingClient:
            next_instance_id = 1

            def __init__(
                self,
                settings: FollowUpBossTenantSettings | FollowUpBossSettings | None = None,
                *,
                logger: object | None = None,
            ) -> None:
                del logger
                assert settings is not None
                self.settings = settings
                self.instance_id = RecordingClient.next_instance_id
                RecordingClient.next_instance_id += 1
                _record_event(
                    {{
                        "event": "created",
                        "instance_id": self.instance_id,
                        "credential": self._credential_value(),
                    }}
                )

            async def aclose(self) -> None:
                _record_event({{"event": "closed", "instance_id": self.instance_id}})

            async def request_json(
                self,
                method: str,
                path: str,
                *,
                headers: Mapping[str, str] | None = None,
                json_body: Mapping[str, object] | None = None,
                params: Mapping[str, str] | None = None,
            ) -> dict[str, object]:
                del method, path, headers, json_body, params
                return {{
                    "id": self.instance_id,
                    "credential": self._credential_value(),
                }}

            def _credential_value(self) -> str:
                if self.settings.api_key is not None:
                    return self.settings.api_key.get_secret_value()
                assert self.settings.access_token is not None
                return self.settings.access_token.get_secret_value()


        tenant_runtime.FollowUpBossAsyncClient = RecordingClient

        tenant_store = DevelopmentTenantStore(
            tenants=[
                TenantRecord.model_validate(
                    {{
                        "tenant_id": "tenant-1",
                        "tenant_slug": "tenant-one",
                        "display_name": "Tenant One",
                        "credential_id": "credential-1",
                        "status": TenantStatus.ACTIVE,
                    }}
                ),
                TenantRecord.model_validate(
                    {{
                        "tenant_id": "tenant-2",
                        "tenant_slug": "tenant-two",
                        "display_name": "Tenant Two",
                        "credential_id": "credential-2",
                        "status": TenantStatus.ACTIVE,
                    }}
                ),
            ],
            credentials=[
                TenantCredentialRecord.model_validate(
                    {{
                        "credential_id": "credential-1",
                        "tenant_id": "tenant-1",
                        "auth_mode": AuthMode.API_KEY,
                        "api_key": "tenant-one-key",
                        "status": TenantCredentialStatus.ACTIVE,
                    }}
                ),
                TenantCredentialRecord.model_validate(
                    {{
                        "credential_id": "credential-2",
                        "tenant_id": "tenant-2",
                        "auth_mode": AuthMode.API_KEY,
                        "api_key": "tenant-two-key",
                        "status": TenantCredentialStatus.ACTIVE,
                    }}
                ),
            ],
        )

        hosted_token_verifier = DevelopmentHostedTokenVerifier.from_mapping(
            {{
                "tenant-one-token": HostedVerifiedIdentity.model_validate(
                    {{
                        "tenant_id": "tenant-1",
                        "subject": "user-123",
                        "client_id": "portal-app",
                        "credential_id": "credential-1",
                    }}
                ),
                "tenant-two-token": HostedVerifiedIdentity.model_validate(
                    {{
                        "tenant_id": "tenant-2",
                        "subject": "user-456",
                        "client_id": "portal-app",
                        "credential_id": "credential-2",
                    }}
                ),
            }}
        )

        hosted_auth = HostedAuthSettings.model_validate(
            {{
                "issuer_url": "https://issuer.example.com",
                "resource_server_url": "http://127.0.0.1:{port}/mcp",
            }}
        )

        create_server(
            FollowUpBossSettings.model_validate({{"api_key": "bootstrap-key"}}),
            hosted_auth=hosted_auth,
            hosted_token_verifier=hosted_token_verifier,
            tenant_store=tenant_store,
            host="127.0.0.1",
            port={port},
            streamable_http_path="/mcp",
        ).run(transport="streamable-http")
        """
    )
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        "-c",
        server_script,
        cwd=str(PROJECT_ROOT),
        env=_server_python_env(),
    )
    try:
        await _wait_for_port("127.0.0.1", port)

        async def call_surface(token: str) -> dict[str, str | dict[str, object]]:
            """Call the hosted MCP surfaces with one bearer token.

            Args:
                token: The bearer token to present to the hosted server.

            Returns:
                The structured outputs returned by the tool, resource, and prompt
                surfaces for the authenticated tenant.
            """
            async with httpx.AsyncClient(
                headers={"Authorization": f"Bearer {token}"},
            ) as http_client:
                async with streamable_http_client(
                    f"http://127.0.0.1:{port}/mcp",
                    http_client=http_client,
                ) as (
                    read_stream,
                    write_stream,
                    _,
                ):
                    async with ClientSession(read_stream, write_stream) as session:
                        await session.initialize()
                        resources = await session.list_resources()
                        assert len(resources.resources) == 1
                        resource_result = await session.read_resource(resources.resources[0].uri)
                        resource_text = getattr(resource_result.contents[0], "text", None)
                        assert isinstance(resource_text, str)

                        prompts = await session.list_prompts()
                        assert len(prompts.prompts) == 1
                        prompt_result = await session.get_prompt(
                            prompts.prompts[0].name,
                            {
                                "source": "Portal",
                                "type": "Inquiry",
                                "message": "Hi",
                                "email": "a@example.com",
                            },
                        )
                        prompt_text = getattr(prompt_result.messages[0].content, "text", None)
                        assert isinstance(prompt_text, str)

                        identity_result = await session.call_tool("followupboss_get_identity")
                        assert identity_result.isError is False
                        assert isinstance(identity_result.structuredContent, dict)
                        return {
                            "resource": resource_text,
                            "prompt": prompt_text,
                            "tool": identity_result.structuredContent,
                        }

        first_result = await call_surface("tenant-one-token")
        second_result = await call_surface("tenant-two-token")
    finally:
        process.terminate()
        await process.wait()

    events = [
        json.loads(line)
        for line in output_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    assert first_result["tool"] == {"id": 1, "credential": "tenant-one-key"}
    assert second_result["tool"] == {"id": 2, "credential": "tenant-two-key"}
    assert "tenant_slug: tenant-one" in str(first_result["resource"])
    assert "tenant_slug: tenant-two" not in str(first_result["resource"])
    assert "tenant_slug: tenant-two" in str(second_result["resource"])
    assert "tenant_slug: tenant-one" not in str(second_result["resource"])
    assert "tenant_slug: tenant-one" in str(first_result["prompt"])
    assert "tenant_slug: tenant-two" not in str(first_result["prompt"])
    assert "tenant_slug: tenant-two" in str(second_result["prompt"])
    assert "tenant_slug: tenant-one" not in str(second_result["prompt"])
    assert events == [
        {
            "event": "created",
            "instance_id": 1,
            "credential": "tenant-one-key",
        },
        {
            "event": "closed",
            "instance_id": 1,
        },
        {
            "event": "created",
            "instance_id": 2,
            "credential": "tenant-two-key",
        },
        {
            "event": "closed",
            "instance_id": 2,
        },
    ]


@pytest.mark.asyncio
async def test_streamable_http_hosted_auth_resource_and_prompt_runtime_errors_remain_mcp_safe() -> (
    None
):
    """Hosted resource and prompt runtime failures should stay MCP-safe."""
    port = _reserve_port()
    server_script = textwrap.dedent(
        f"""
        import followupboss_mcp.tenant_runtime as tenant_runtime
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


        async def unsafe_runtime_error(self) -> object:
            del self
            raise RuntimeError(
                "Hosted tenant runtime is unavailable. token=super-secret-token"
            )


        tenant_runtime.TenantRuntimeFactory.runtime_for_current_tenant = unsafe_runtime_error

        tenant_store = DevelopmentTenantStore(
            tenants=[
                TenantRecord.model_validate(
                    {{
                        "tenant_id": "tenant-1",
                        "tenant_slug": "tenant-one",
                        "display_name": "Tenant One",
                        "credential_id": "credential-1",
                        "status": TenantStatus.ACTIVE,
                    }}
                )
            ],
            credentials=[
                TenantCredentialRecord.model_validate(
                    {{
                        "credential_id": "credential-1",
                        "tenant_id": "tenant-1",
                        "auth_mode": AuthMode.API_KEY,
                        "api_key": "secret-key",
                        "status": TenantCredentialStatus.ACTIVE,
                    }}
                )
            ],
        )

        hosted_token_verifier = DevelopmentHostedTokenVerifier.from_mapping(
            {{
                "dev-token": HostedVerifiedIdentity.model_validate(
                    {{
                        "tenant_id": "tenant-1",
                        "subject": "user-123",
                        "client_id": "portal-app",
                        "credential_id": "credential-1",
                    }}
                )
            }}
        )

        hosted_auth = HostedAuthSettings.model_validate(
            {{
                "issuer_url": "https://issuer.example.com",
                "resource_server_url": "http://127.0.0.1:{port}/mcp",
            }}
        )

        create_server(
            FollowUpBossSettings.model_validate({{"api_key": "bootstrap-key"}}),
            hosted_auth=hosted_auth,
            hosted_token_verifier=hosted_token_verifier,
            tenant_store=tenant_store,
            host="127.0.0.1",
            port={port},
            streamable_http_path="/mcp",
        ).run(transport="streamable-http")
        """
    )
    process = await asyncio.create_subprocess_exec(
        sys.executable,
        "-c",
        server_script,
        cwd=str(PROJECT_ROOT),
        env=_server_python_env(),
    )
    try:
        await _wait_for_port("127.0.0.1", port)
        async with httpx.AsyncClient(
            headers={"Authorization": "Bearer dev-token"},
        ) as http_client:
            async with streamable_http_client(
                f"http://127.0.0.1:{port}/mcp",
                http_client=http_client,
            ) as (
                read_stream,
                write_stream,
                _,
            ):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()

                    resources = await session.list_resources()
                    with pytest.raises(McpError) as resource_exc_info:
                        await session.read_resource(resources.resources[0].uri)

                    assert resource_exc_info.value.error.message == (
                        "Error reading resource followupboss://api-coverage-matrix: "
                        "Hosted tenant runtime is unavailable."
                    )
                    assert "super-secret-token" not in resource_exc_info.value.error.message

                    prompts = await session.list_prompts()
                    with pytest.raises(McpError) as prompt_exc_info:
                        await session.get_prompt(
                            prompts.prompts[0].name,
                            {
                                "source": "Portal",
                                "type": "Inquiry",
                                "message": "Hi",
                                "email": "a@example.com",
                            },
                        )

                    assert prompt_exc_info.value.error.message == (
                        "Error rendering prompt followupboss_compose_lead_event: "
                        "Hosted tenant runtime is unavailable."
                    )
                    assert "super-secret-token" not in prompt_exc_info.value.error.message
    finally:
        process.terminate()
        await process.wait()
