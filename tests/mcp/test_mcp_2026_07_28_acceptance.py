"""Wire-level acceptance tests for MCP protocol revision 2026-07-28."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from importlib.metadata import version
from typing import Any

import pytest
from starlette.testclient import TestClient

from followupboss_mcp.mcp_server import create_server

_MODERN_PROTOCOL_VERSION = "2026-07-28"
_LEGACY_PROTOCOL_VERSION = "2025-11-25"
_PROTOCOL_VERSION_META_KEY = "io.modelcontextprotocol/protocolVersion"
_CLIENT_INFO_META_KEY = "io.modelcontextprotocol/clientInfo"
_CLIENT_CAPABILITIES_META_KEY = "io.modelcontextprotocol/clientCapabilities"
_SERVER_INFO_META_KEY = "io.modelcontextprotocol/serverInfo"
_MCP_SDK_MAJOR = int(version("mcp").partition(".")[0])
_REQUIRES_MCP_V2 = pytest.mark.skipif(
    _MCP_SDK_MAJOR < 2,
    reason="MCP 2026-07-28 requires the Python MCP SDK v2",
)


class _UnusedFollowUpBossClient:
    """Satisfy server construction without making external FUB requests."""

    async def aclose(self) -> None:
        """Close the inert client."""

    async def request_json(
        self,
        method: str,
        path: str,
        *,
        headers: Mapping[str, str] | None = None,
        json_body: Mapping[str, object] | None = None,
        params: Mapping[str, str] | None = None,
    ) -> dict[str, object] | list[object]:
        """Fail if a metadata-only acceptance request reaches Follow Up Boss."""
        del method, path, headers, json_body, params
        raise AssertionError("Protocol metadata tests must not call Follow Up Boss.")


def _create_test_server() -> Any:
    """Create the production server surface with an inert downstream client."""
    return create_server(
        client=_UnusedFollowUpBossClient(),
        host="127.0.0.1",
        port=8000,
        streamable_http_path="/mcp",
    )


@pytest.fixture
def mcp_http_client() -> Iterator[TestClient]:
    """Serve the MCP application in-process with a transport-valid host header."""
    server = _create_test_server()
    with TestClient(
        server.streamable_http_app(),
        base_url="http://127.0.0.1:8000",
    ) as client:
        yield client


def _modern_meta(
    *,
    protocol_version: str = _MODERN_PROTOCOL_VERSION,
) -> dict[str, object]:
    """Return the self-describing metadata required on every modern request."""
    return {
        _PROTOCOL_VERSION_META_KEY: protocol_version,
        _CLIENT_INFO_META_KEY: {"name": "followupboss-mcp-acceptance", "version": "1"},
        _CLIENT_CAPABILITIES_META_KEY: {},
    }


def _modern_body(
    method: str,
    *,
    request_id: int = 1,
    params: Mapping[str, object] | None = None,
    protocol_version: str = _MODERN_PROTOCOL_VERSION,
) -> dict[str, object]:
    """Build one complete modern JSON-RPC request envelope."""
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": method,
        "params": {
            **(params or {}),
            "_meta": _modern_meta(protocol_version=protocol_version),
        },
    }


def _modern_headers(method: str, *, name: str | None = None) -> dict[str, str]:
    """Build the mandatory modern Streamable HTTP routing headers."""
    headers = {
        "Accept": "application/json",
        "MCP-Protocol-Version": _MODERN_PROTOCOL_VERSION,
        "Mcp-Method": method,
    }
    if name is not None:
        headers["Mcp-Name"] = name
    return headers


def _post_modern(
    client: TestClient,
    method: str,
    *,
    request_id: int = 1,
    params: Mapping[str, object] | None = None,
    name: str | None = None,
) -> Any:
    """Post one modern request without initialization or session state."""
    return client.post(
        "/mcp",
        headers=_modern_headers(method, name=name),
        json=_modern_body(method, request_id=request_id, params=params),
    )


def _assert_modern_result_metadata(result: Mapping[str, object]) -> None:
    """Assert the safe default result envelope emitted by the v2 SDK."""
    assert result["resultType"] == "complete"
    assert result["ttlMs"] == 0
    assert result["cacheScope"] == "private"

    meta = result["_meta"]
    assert isinstance(meta, dict)
    server_info = meta[_SERVER_INFO_META_KEY]
    assert isinstance(server_info, dict)
    assert server_info["name"] == "Follow Up Boss MCP"
    assert isinstance(server_info["version"], str)
    assert server_info["version"]


@_REQUIRES_MCP_V2
def test_server_discover_advertises_the_modern_contract(
    mcp_http_client: TestClient,
) -> None:
    """Discovery should expose modern versions, surfaces, and result metadata."""
    response = _post_modern(mcp_http_client, "server/discover")

    assert response.status_code == 200
    assert "mcp-session-id" not in response.headers
    payload = response.json()
    result = payload["result"]
    assert _MODERN_PROTOCOL_VERSION in result["supportedVersions"]
    assert {"tools", "resources", "prompts"} <= result["capabilities"].keys()
    assert isinstance(result["instructions"], str)
    assert result["instructions"]
    _assert_modern_result_metadata(result)


@_REQUIRES_MCP_V2
@pytest.mark.parametrize(
    ("method", "collection_key"),
    [
        ("tools/list", "tools"),
        ("resources/list", "resources"),
        ("prompts/list", "prompts"),
    ],
)
def test_modern_catalog_results_are_private_immediately_stale_and_complete(
    mcp_http_client: TestClient,
    method: str,
    collection_key: str,
) -> None:
    """Catalog responses should carry conservative cache and result metadata."""
    response = _post_modern(mcp_http_client, method)

    assert response.status_code == 200
    assert "mcp-session-id" not in response.headers
    result = response.json()["result"]
    assert result[collection_key]
    _assert_modern_result_metadata(result)


@_REQUIRES_MCP_V2
def test_modern_http_is_sessionless_and_rejects_get(
    mcp_http_client: TestClient,
) -> None:
    """Independent POSTs should work without initialize or transport sessions."""
    first = _post_modern(mcp_http_client, "tools/list", request_id=1)
    second = _post_modern(mcp_http_client, "tools/list", request_id=2)

    assert first.status_code == second.status_code == 200
    assert first.json()["id"] == 1
    assert second.json()["id"] == 2
    assert "mcp-session-id" not in first.headers
    assert "mcp-session-id" not in second.headers

    get_response = mcp_http_client.get(
        "/mcp",
        headers={"MCP-Protocol-Version": _MODERN_PROTOCOL_VERSION},
    )
    assert get_response.status_code == 405
    assert get_response.headers["allow"] == "POST"
    assert "mcp-session-id" not in get_response.headers


@_REQUIRES_MCP_V2
@pytest.mark.parametrize(
    ("body_method", "headers", "params", "body_protocol_version"),
    [
        (
            "tools/list",
            {
                "Accept": "application/json",
                "MCP-Protocol-Version": _MODERN_PROTOCOL_VERSION,
                "Mcp-Method": "tools/list",
            },
            {},
            _LEGACY_PROTOCOL_VERSION,
        ),
        (
            "tools/list",
            {
                "Accept": "application/json",
                "MCP-Protocol-Version": _MODERN_PROTOCOL_VERSION,
                "Mcp-Method": "resources/list",
            },
            {},
            _MODERN_PROTOCOL_VERSION,
        ),
        (
            "tools/call",
            {
                "Accept": "application/json",
                "MCP-Protocol-Version": _MODERN_PROTOCOL_VERSION,
                "Mcp-Method": "tools/call",
                "Mcp-Name": "followupboss_get_me",
            },
            {"name": "followupboss_get_identity", "arguments": {}},
            _MODERN_PROTOCOL_VERSION,
        ),
    ],
)
def test_modern_http_rejects_routing_header_mismatches(
    mcp_http_client: TestClient,
    body_method: str,
    headers: Mapping[str, str],
    params: Mapping[str, object],
    body_protocol_version: str,
) -> None:
    """Wire headers must agree with the self-describing request body."""
    response = mcp_http_client.post(
        "/mcp",
        headers=headers,
        json=_modern_body(
            body_method,
            params=params,
            protocol_version=body_protocol_version,
        ),
    )

    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == -32020
    assert "header does not match" in error["message"]


def test_legacy_streamable_http_initialize_remains_compatible(
    mcp_http_client: TestClient,
) -> None:
    """The shared endpoint should preserve the sessionful 2025-11-25 flow."""
    transport_headers = {
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
    }
    initialize_response = mcp_http_client.post(
        "/mcp",
        headers=transport_headers,
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": _LEGACY_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "legacy-wire-acceptance", "version": "1"},
            },
        },
    )

    assert initialize_response.status_code == 200
    assert initialize_response.json()["result"]["protocolVersion"] == _LEGACY_PROTOCOL_VERSION
    session_id = initialize_response.headers["mcp-session-id"]
    session_headers = {
        **transport_headers,
        "MCP-Protocol-Version": _LEGACY_PROTOCOL_VERSION,
        "Mcp-Session-Id": session_id,
    }

    initialized_response = mcp_http_client.post(
        "/mcp",
        headers=session_headers,
        json={"jsonrpc": "2.0", "method": "notifications/initialized"},
    )
    assert initialized_response.status_code == 202

    list_response = mcp_http_client.post(
        "/mcp",
        headers=session_headers,
        json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
    )
    assert list_response.status_code == 200
    result = list_response.json()["result"]
    assert result["tools"]
    assert "resultType" not in result
    assert "ttlMs" not in result
    assert "cacheScope" not in result


@_REQUIRES_MCP_V2
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("mode", "expected_protocol_version"),
    [
        ("auto", _MODERN_PROTOCOL_VERSION),
        ("legacy", _LEGACY_PROTOCOL_VERSION),
    ],
)
async def test_official_v2_client_supports_modern_and_legacy_modes(
    mode: str,
    expected_protocol_version: str,
) -> None:
    """The official client should negotiate both protocol eras with one server."""
    from mcp.client import Client

    async with Client(_create_test_server(), mode=mode) as client:
        assert client.protocol_version == expected_protocol_version
        result = await client.list_tools()
        assert result.tools
