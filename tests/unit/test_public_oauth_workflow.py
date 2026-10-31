"""Exercise production OAuth probes with mocked external HTTP only."""

from __future__ import annotations

import asyncio
import importlib.util
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlencode

import httpx
import pytest

from followupboss_mcp.cimd import ClientIdMetadataDocumentFetcher

_SPEC = importlib.util.spec_from_file_location(
    "verify_public_oauth", Path(__file__).resolve().parents[2] / "scripts/verify_public_oauth.py"
)
assert _SPEC is not None and _SPEC.loader is not None
probe = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = probe
_SPEC.loader.exec_module(probe)

_RESOURCE = "https://mcp.example.com/mcp"
_ISSUER = "https://mcp.example.com/"
_PROTECTED = "https://mcp.example.com/.well-known/oauth-protected-resource/mcp"
# Independent provider contract fixtures: changing the probe constants must not
# silently change the metadata a provider is expected to publish.
_CLIENT_METADATA = {
    "https://chatgpt.com/oauth/client.json": {
        "client_name": "ChatGPT",
        "redirect_uris": ["https://chatgpt.com/connector_platform_oauth_redirect"],
    },
    "https://chatgpt.com/oauth/codex/client.json": {
        "client_name": "Codex",
        "redirect_uris": ["http://127.0.0.1/callback"],
    },
}


def _authorization_metadata() -> dict[str, Any]:
    return {
        "issuer": _ISSUER,
        "authorization_endpoint": f"{_ISSUER}oauth/authorize",
        "token_endpoint": f"{_ISSUER}oauth/token",
        "authorization_response_iss_parameter_supported": True,
        "client_id_metadata_document_supported": True,
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code", "refresh_token"],
        "code_challenge_methods_supported": ["S256"],
        "token_endpoint_auth_methods_supported": ["none"],
        "scopes_supported": ["followupboss:mcp"],
    }


def _provider_redirect(**changes: str) -> str:
    query = {
        "response_type": "auth_code",
        "client_id": "provider-client",
        "redirect_uri": f"{_ISSUER}oauth/follow-up-boss/callback",
        "state": "private-upstream-state",
        "prompt": "login",
    }
    query.update(changes)
    return f"{probe.DEFAULT_FUB_AUTHORIZE_URL}?{urlencode(query)}"


async def _run_public(
    *,
    authorize_status: int = 307,
    location: str | None = None,
    bearer_status: int = 401,
    metadata_change: Callable[[dict[str, Any]], None] | None = None,
) -> list[httpx.Request]:
    requests: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        assert request.headers["User-Agent"] == probe.USER_AGENT
        assert request.headers["Accept"] == "application/json"
        assert "authorization" not in request.headers
        assert request.extensions["timeout"]["read"] == 15.0
        requests.append(request)
        if str(request.url) == _RESOURCE:
            return httpx.Response(
                bearer_status,
                headers={"WWW-Authenticate": f'Bearer resource_metadata="{_PROTECTED}"'},
            )
        if str(request.url) == _PROTECTED:
            return httpx.Response(
                200, json={"resource": _RESOURCE, "authorization_servers": [_ISSUER]}
            )
        if request.url.path == "/.well-known/oauth-authorization-server":
            metadata = _authorization_metadata()
            if metadata_change is not None:
                metadata_change(metadata)
            return httpx.Response(200, json=metadata)
        assert request.url.host == "mcp.example.com"
        assert request.url.path == "/oauth/authorize"
        query = parse_qs(request.url.query.decode())
        assert query["response_type"] == ["code"]
        assert query["code_challenge_method"] == ["S256"]
        assert len(query["code_challenge"][0]) == 43
        assert query["state"][0]
        assert query["resource"] == [_RESOURCE]
        assert query["scope"] == [probe.REQUIRED_SCOPE]
        expected = next(item for item in probe.CLIENTS if item.client_id == query["client_id"][0])
        assert query["redirect_uri"] == [expected.redirect_uri]
        return httpx.Response(
            authorize_status,
            headers={"Location": _provider_redirect() if location is None else location},
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        await probe.verify_public_oauth(
            _RESOURCE, _ISSUER, fub_client_id="provider-client", client=client
        )
    return requests


@pytest.mark.parametrize("status", [302, 303, 307])
async def test_public_probe_verifies_both_clients_without_following_provider(status: int) -> None:
    requests = await _run_public(authorize_status=status)
    assert len(requests) == 5
    assert [str(request.url.params["client_id"]) for request in requests[-2:]] == [
        item.client_id for item in probe.CLIENTS
    ]


@pytest.mark.parametrize("status", [200, 301, 400, 401, 500])
async def test_public_probe_rejects_an_authorization_endpoint_that_rejects_chatgpt(
    status: int,
) -> None:
    with pytest.raises(probe.OAuthProbeError, match="ChatGPT authorization"):
        await _run_public(authorize_status=status)


@pytest.mark.parametrize("status", [200, 403, 500])
async def test_public_probe_requires_unauthenticated_bearer_challenge(status: int) -> None:
    with pytest.raises(probe.OAuthProbeError, match="MCP bearer challenge"):
        await _run_public(bearer_status=status)


@pytest.mark.parametrize("field", list(_authorization_metadata()))
async def test_public_probe_requires_every_metadata_invariant(field: str) -> None:
    def change(metadata: dict[str, Any]) -> None:
        metadata.pop(field)

    with pytest.raises(probe.OAuthProbeError, match="Authorization metadata"):
        await _run_public(metadata_change=change)


@pytest.mark.parametrize(
    "location",
    [
        "",
        "https://evil.example.com/oauth/authorize",
        _provider_redirect().replace("/oauth/authorize?", "/wrong?"),
        _provider_redirect().replace("https://app.", "https://user@app."),
        _provider_redirect() + "#fragment",
        _provider_redirect(response_type="code"),
        _provider_redirect(redirect_uri="https://wrong.example/callback"),
        _provider_redirect(client_id=""),
        _provider_redirect(client_id="wrong-client"),
        _provider_redirect() + "&client_id=duplicate",
        _provider_redirect().replace("client_id=provider-client&", ""),
        _provider_redirect(state=""),
        _provider_redirect(error="invalid_client"),
        _provider_redirect() + "&state=duplicate",
    ],
)
async def test_public_probe_rejects_invalid_provider_redirects(location: str) -> None:
    with pytest.raises(probe.OAuthProbeError, match="invalid provider redirect"):
        await _run_public(location=location)


async def test_public_probe_sanitizes_transport_failure() -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("private-upstream-state", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        with pytest.raises(probe.OAuthProbeError, match="^MCP bearer challenge request failed.$"):
            await probe.verify_public_oauth(
                _RESOURCE, _ISSUER, fub_client_id="provider-client", client=client
            )


@pytest.mark.parametrize("change", ["valid", "callback", "method", "missing", "wrong_client"])
async def test_metadata_preflight_uses_production_parser(change: str) -> None:
    fetched: list[str] = []

    async def resolve(host: str, port: int) -> tuple[str, ...]:
        assert (host, port) == ("chatgpt.com", 443)
        return ("93.184.216.34",)

    def handle(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "93.184.216.34"
        assert request.headers["host"] == "chatgpt.com"
        assert request.extensions["sni_hostname"] == "chatgpt.com"
        client_id = "https://chatgpt.com" + request.url.path
        fixture = _CLIENT_METADATA[client_id]
        fetched.append(client_id)
        payload: dict[str, Any] = {
            "client_id": client_id,
            **fixture,
            "token_endpoint_auth_method": "private_key_jwt",
            "token_endpoint_auth_methods_supported": ["private_key_jwt", "none"],
        }
        if change == "callback":
            payload["redirect_uris"] = ["https://wrong.example/callback"]
        if change == "method":
            payload["token_endpoint_auth_methods_supported"] = ["private_key_jwt"]
        if change == "wrong_client":
            payload["client_id"] = "https://wrong.example/client.json"
        return httpx.Response(404 if change == "missing" else 200, json=payload)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as client:
        fetcher = ClientIdMetadataDocumentFetcher(http_client=client, address_resolver=resolve)
        try:
            if change == "valid":
                await probe.verify_client_metadata(fetcher)
                assert fetched == list(_CLIENT_METADATA)
            else:
                with pytest.raises(probe.OAuthProbeError, match="ChatGPT client metadata"):
                    await probe.verify_client_metadata(fetcher)
        finally:
            await fetcher.aclose()


async def test_metadata_only_cli_needs_no_deployment_environment(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    async def metadata() -> None:
        pass

    monkeypatch.delenv("HOSTED_RESOURCE_SERVER_URL", raising=False)
    monkeypatch.delenv("HOSTED_ISSUER_URL", raising=False)
    monkeypatch.setattr(probe, "verify_client_metadata", metadata)
    await asyncio.to_thread(probe.main, ["--metadata-only"])
    assert "ChatGPT and Codex" in capsys.readouterr().out


async def test_cli_reports_sanitized_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    async def metadata() -> None:
        raise probe.OAuthProbeError("ChatGPT client metadata verification failed.")

    monkeypatch.setattr(probe, "verify_client_metadata", metadata)
    with pytest.raises(SystemExit, match="ChatGPT client metadata verification failed"):
        await asyncio.to_thread(probe.main, ["--metadata-only"])
