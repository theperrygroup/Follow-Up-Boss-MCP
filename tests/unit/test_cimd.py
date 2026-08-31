"""Focused tests for OAuth Client ID Metadata Document discovery."""

from __future__ import annotations

import asyncio
import socket
from collections.abc import AsyncIterator
from time import monotonic

import httpx
import pytest
from pydantic import ValidationError

import followupboss_mcp.cimd as cimd
from followupboss_mcp.cimd import (
    ClientIdMetadataDocument,
    ClientIdMetadataDocumentError,
    ClientIdMetadataDocumentFetcher,
)


def _metadata_payload(client_id: str) -> dict[str, object]:
    """Return one valid public-client metadata document payload."""
    return {
        "client_id": client_id,
        "client_name": "Example MCP Client",
        "redirect_uris": ["https://client.example.com/oauth/callback"],
        "scope": "followupboss:mcp",
        "token_endpoint_auth_method": "none",
    }


async def _public_address(_: str, __: int) -> tuple[str, ...]:
    """Resolve test hostnames to a representative global address."""
    return ("93.184.216.34",)


class _ChunkedBody(httpx.AsyncByteStream):
    """Response body without a declared Content-Length."""

    async def __aiter__(self) -> AsyncIterator[bytes]:
        yield b"x" * 3_000
        yield b"x" * 3_000


@pytest.mark.asyncio
async def test_fetches_valid_metadata_through_a_pinned_public_address() -> None:
    """A valid CIMD document is fetched without a second, rebinding-prone DNS lookup."""
    client_id = "https://client.example.com/oauth/client.json"

    async def resolve(host: str, port: int) -> tuple[str, ...]:
        assert (host, port) == ("client.example.com", 443)
        return ("93.184.216.34",)

    def handle(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "https://93.184.216.34/oauth/client.json"
        assert request.headers["host"] == "client.example.com"
        assert request.headers["connection"] == "close"
        assert request.extensions["sni_hostname"] == "client.example.com"
        return httpx.Response(
            200,
            headers={"Content-Type": "application/json", "Cache-Control": "public, max-age=60"},
            json={
                "client_id": client_id,
                "client_name": "Example MCP Client",
                "redirect_uris": ["https://client.example.com/oauth/callback"],
                "scope": "followupboss:mcp",
                "token_endpoint_auth_method": "none",
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as http_client:
        fetcher = ClientIdMetadataDocumentFetcher(
            http_client=http_client,
            address_resolver=resolve,
            time_provider=lambda: 1_000,
        )
        document = await fetcher.fetch(client_id)

    assert document.client_id == client_id
    assert document.client_name == "Example MCP Client"
    assert document.redirect_uris == ("https://client.example.com/oauth/callback",)
    assert document.scope == ("followupboss:mcp",)


@pytest.mark.asyncio
async def test_caches_only_until_the_clamped_http_max_age() -> None:
    """Valid metadata honors max-age without remaining trusted beyond 24 hours."""
    client_id = "https://client.example.com/oauth/client.json"
    now = [1_000]
    request_count = 0
    resolution_count = 0

    async def resolve(_: str, __: int) -> tuple[str, ...]:
        nonlocal resolution_count
        resolution_count += 1
        return ("93.184.216.34",)

    def handle(_: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        return httpx.Response(
            200,
            headers={
                "Content-Type": "application/json",
                "Cache-Control": "public, max-age=999999",
            },
            json={
                "client_id": client_id,
                "client_name": "Cached MCP Client",
                "redirect_uris": ["https://client.example.com/callback"],
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as http_client:
        fetcher = ClientIdMetadataDocumentFetcher(
            http_client=http_client,
            address_resolver=resolve,
            time_provider=lambda: now[0],
        )
        first = await fetcher.fetch(client_id)
        now[0] += 86_399
        second = await fetcher.fetch(client_id)
        now[0] += 1
        third = await fetcher.fetch(client_id)

    assert first is second
    assert third == first
    assert request_count == 2
    assert resolution_count == 2


@pytest.mark.parametrize("secret_field", ["client_secret", "client_secret_expires_at"])
def test_metadata_rejects_symmetric_secret_fields(secret_field: str) -> None:
    """A self-published client document cannot establish shared secret material."""
    with pytest.raises(ValidationError, match="secret"):
        ClientIdMetadataDocument.model_validate(
            {
                "client_id": "https://client.example.com/oauth/client.json",
                "client_name": "Example MCP Client",
                "redirect_uris": ["https://client.example.com"],
                secret_field: "forbidden",
            }
        )


def test_metadata_accepts_an_https_origin_as_a_redirect_uri() -> None:
    """Redirect URLs, unlike Client Identifier URLs, may use a root path."""
    document = ClientIdMetadataDocument.model_validate(
        {
            "client_id": "https://client.example.com/oauth/client.json",
            "client_name": "Example MCP Client",
            "redirect_uris": ["https://client.example.com"],
        }
    )
    assert document.redirect_uris == ("https://client.example.com",)


@pytest.mark.parametrize(
    "client_id",
    [
        "http://client.example.com/oauth/client.json",
        "https://client.example.com",
        "https://client.example.com/",
        "https://client.example.com/oauth/../client.json",
        "https://client.example.com/oauth/%2e%2e/client.json",
        "https://client.example.com/oauth/client.json#fragment",
        "https://client.example.com/oauth/client.json?tenant=one",
        "https://user@client.example.com/oauth/client.json",
        "https:///oauth/client.json",
        " https://client.example.com/oauth/client.json",
        "https://client.example.com/oauth/client.json\x00",
    ],
)
@pytest.mark.asyncio
async def test_rejects_invalid_client_identifier_urls_before_dns(client_id: str) -> None:
    """Malformed and unsafe Client Identifier URLs never reach the network boundary."""
    resolved = False

    async def resolve(_: str, __: int) -> tuple[str, ...]:
        nonlocal resolved
        resolved = True
        return ("93.184.216.34",)

    def unexpected_request(_: httpx.Request) -> httpx.Response:
        raise AssertionError("invalid Client Identifier URL reached HTTP")

    async with httpx.AsyncClient(transport=httpx.MockTransport(unexpected_request)) as http_client:
        fetcher = ClientIdMetadataDocumentFetcher(
            http_client=http_client,
            address_resolver=resolve,
        )
        with pytest.raises(ClientIdMetadataDocumentError, match="Identifier"):
            await fetcher.fetch(client_id)

    assert resolved is False


@pytest.mark.parametrize(
    "address",
    ["127.0.0.1", "10.0.0.8", "169.254.169.254", "::1", "fc00::1"],
)
@pytest.mark.asyncio
async def test_rejects_special_use_dns_destinations(address: str) -> None:
    """DNS answers cannot route metadata fetches to loopback or private services."""
    requested = False

    async def resolve(_: str, __: int) -> tuple[str, ...]:
        return (address,)

    def handle(_: httpx.Request) -> httpx.Response:
        nonlocal requested
        requested = True
        return httpx.Response(500)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as http_client:
        fetcher = ClientIdMetadataDocumentFetcher(
            http_client=http_client,
            address_resolver=resolve,
        )
        with pytest.raises(ClientIdMetadataDocumentError, match="not public"):
            await fetcher.fetch("https://client.example.com/oauth/client.json")

    assert requested is False


@pytest.mark.parametrize(
    ("case", "expected_message"),
    [
        ("redirect", "fetch failed"),
        ("non_json_media_type", "not JSON"),
        ("invalid_json", "document is invalid"),
        ("json_array", "document is invalid"),
        ("declared_oversize", "too large"),
        ("streamed_oversize", "too large"),
        ("wrong_client_id", "does not match"),
        ("missing_client_name", "document is invalid"),
        ("missing_redirects", "document is invalid"),
        ("secret", "document is invalid"),
        ("shared_secret_auth", "document is invalid"),
    ],
)
@pytest.mark.asyncio
async def test_rejects_untrusted_http_and_document_shapes(
    case: str,
    expected_message: str,
) -> None:
    """Only bounded, successful JSON with exact safe metadata is accepted."""
    client_id = "https://client.example.com/oauth/client.json"

    def handle(_: httpx.Request) -> httpx.Response:
        payload = _metadata_payload(client_id)
        if case == "redirect":
            return httpx.Response(302, headers={"Location": "https://other.example/client.json"})
        if case == "non_json_media_type":
            return httpx.Response(200, headers={"Content-Type": "text/plain"}, text="{}")
        if case == "invalid_json":
            return httpx.Response(
                200,
                headers={"Content-Type": "application/json"},
                content=b"{",
            )
        if case == "json_array":
            return httpx.Response(200, headers={"Content-Type": "application/json"}, json=[])
        if case == "declared_oversize":
            return httpx.Response(
                200,
                headers={"Content-Type": "application/json"},
                content=b"x" * 5_121,
            )
        if case == "streamed_oversize":
            return httpx.Response(
                200,
                headers={"Content-Type": "application/json"},
                stream=_ChunkedBody(),
            )
        if case == "wrong_client_id":
            payload["client_id"] = "https://CLIENT.example.com/oauth/client.json"
        elif case == "missing_client_name":
            del payload["client_name"]
        elif case == "missing_redirects":
            del payload["redirect_uris"]
        elif case == "secret":
            payload["client_secret"] = "forbidden"
        elif case == "shared_secret_auth":
            payload["token_endpoint_auth_method"] = "client_secret_basic"
        return httpx.Response(200, headers={"Content-Type": "application/json"}, json=payload)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as http_client:
        fetcher = ClientIdMetadataDocumentFetcher(
            http_client=http_client,
            address_resolver=_public_address,
        )
        with pytest.raises(ClientIdMetadataDocumentError, match=expected_message):
            await fetcher.fetch(client_id)


@pytest.mark.parametrize(
    "payload_update",
    [
        {"client_id": 1},
        {"client_name": " "},
        {"redirect_uris": []},
        {"redirect_uris": "https://client.example.com/callback"},
        {"redirect_uris": [1]},
        {"redirect_uris": ["http://client.example.com/callback"]},
        {"redirect_uris": ["https://user@client.example.com/callback"]},
        {"redirect_uris": ["https://client.example.com/callback#fragment"]},
        {"scope": ["followupboss:mcp"]},
        {"token_endpoint_auth_method": "private_key_jwt"},
        {"jwks": {"keys": [{"kty": "RSA", "d": "private-material"}]}},
    ],
)
def test_rejects_invalid_or_unsupported_metadata_values(
    payload_update: dict[str, object],
) -> None:
    """Required fields, redirect safety, and credential restrictions fail closed."""
    payload = _metadata_payload("https://client.example.com/oauth/client.json")
    payload.update(payload_update)
    with pytest.raises(ValidationError):
        ClientIdMetadataDocument.model_validate(payload)


@pytest.mark.asyncio
async def test_invalid_documents_and_no_store_successes_are_not_cached() -> None:
    """Failures and explicit no-store responses are fetched again instead of being trusted."""
    client_id = "https://client.example.com/oauth/client.json"
    responses = ["wrong", "valid", "valid"]
    request_count = 0

    def handle(_: httpx.Request) -> httpx.Response:
        nonlocal request_count
        case = responses[request_count]
        request_count += 1
        payload = _metadata_payload(client_id)
        if case == "wrong":
            payload["client_id"] = "https://other.example.com/oauth/client.json"
        return httpx.Response(
            200,
            headers={"Content-Type": "application/json", "Cache-Control": "no-store, max-age=60"},
            json=payload,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as http_client:
        fetcher = ClientIdMetadataDocumentFetcher(
            http_client=http_client,
            address_resolver=_public_address,
        )
        with pytest.raises(ClientIdMetadataDocumentError):
            await fetcher.fetch(client_id)
        assert (await fetcher.fetch(client_id)).client_id == client_id
        assert (await fetcher.fetch(client_id)).client_id == client_id

    assert request_count == 3


@pytest.mark.asyncio
async def test_concurrent_cache_misses_share_one_valid_fetch() -> None:
    """Concurrent authorization callbacks for one client do not stampede its origin."""
    client_id = "https://client.example.com/oauth/client.json"
    request_count = 0

    async def handle(_: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        await asyncio.sleep(0)
        return httpx.Response(
            200,
            headers={"Content-Type": "application/json", "Cache-Control": "max-age=60"},
            json=_metadata_payload(client_id),
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as http_client:
        fetcher = ClientIdMetadataDocumentFetcher(
            http_client=http_client,
            address_resolver=_public_address,
        )
        first, second = await asyncio.gather(fetcher.fetch(client_id), fetcher.fetch(client_id))

    assert first is second
    assert request_count == 1


@pytest.mark.asyncio
async def test_uncached_fetches_have_a_global_admission_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unique URL clients cannot create an unbounded outbound-fetch workload."""
    monkeypatch.setattr(cimd, "_MAX_UNCACHED_FETCHES_PER_WINDOW", 1)
    request_count = 0

    def handle(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        path = request.url.path
        client_id = f"https://client.example.com{path}"
        return httpx.Response(
            200,
            headers={"Content-Type": "application/json", "Cache-Control": "no-store"},
            json=_metadata_payload(client_id),
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as http_client:
        fetcher = ClientIdMetadataDocumentFetcher(
            http_client=http_client,
            address_resolver=_public_address,
        )
        await fetcher.fetch("https://client.example.com/oauth/one.json")
        with pytest.raises(ClientIdMetadataDocumentError, match="rate limited"):
            await fetcher.fetch("https://client.example.com/oauth/two.json")

    assert request_count == 1


@pytest.mark.asyncio
async def test_uncached_fetch_admission_discards_expired_timestamps() -> None:
    """Expired admissions leave the rolling window before a new fetch is counted."""
    fetcher = ClientIdMetadataDocumentFetcher(address_resolver=_public_address)
    fetcher._uncached_fetch_timestamps.append(  # noqa: SLF001 - exercise window cleanup
        monotonic() - cimd._FETCH_ADMISSION_WINDOW_SECONDS - 1
    )

    try:
        await fetcher._admit_uncached_fetch()  # noqa: SLF001 - focused admission test
        assert len(fetcher._uncached_fetch_timestamps) == 1  # noqa: SLF001
    finally:
        await fetcher.aclose()


@pytest.mark.asyncio
async def test_cache_miss_has_one_wall_clock_deadline(monkeypatch: pytest.MonkeyPatch) -> None:
    """DNS, lock wait, connection, and response reading share a bounded deadline."""
    monkeypatch.setattr(cimd, "_DEFAULT_FETCH_TIMEOUT_SECONDS", 0.001)

    async def slow_resolve(_: str, __: int) -> tuple[str, ...]:
        await asyncio.sleep(1)
        return ("93.184.216.34",)

    fetcher = ClientIdMetadataDocumentFetcher(address_resolver=slow_resolve)
    try:
        with pytest.raises(ClientIdMetadataDocumentError, match="timed out"):
            await fetcher.fetch("https://client.example.com/oauth/client.json")
    finally:
        await fetcher.aclose()


def test_metadata_normalizes_duplicates_and_explicit_empty_scope() -> None:
    """Metadata validation rejects non-objects and preserves exact redirect membership."""
    with pytest.raises(ValidationError):
        ClientIdMetadataDocument.model_validate("not-a-document")

    document = ClientIdMetadataDocument.model_validate(
        {
            "client_id": "https://client.example.com/oauth/client.json",
            "client_name": "Example MCP Client",
            "redirect_uris": [
                "https://client.example.com/callback",
                "https://client.example.com/callback",
            ],
            "scope": None,
        }
    )

    assert document.redirect_uris == ("https://client.example.com/callback",)
    assert document.scope == ()
    assert document.allows_redirect_uri("https://client.example.com/callback") is True
    assert document.allows_redirect_uri("https://client.example.com/other") is False


@pytest.mark.asyncio
async def test_default_dns_resolver_deduplicates_socket_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The production resolver returns stable unique address strings from getaddrinfo."""
    loop = asyncio.get_running_loop()

    async def getaddrinfo(
        host: str,
        port: int,
        *,
        type: int,
    ) -> list[tuple[int, int, int, str, tuple[str, int]]]:
        assert (host, port, type) == ("client.example.com", 443, socket.SOCK_STREAM)
        return [
            (2, 1, 6, "", ("93.184.216.34", 443)),
            (2, 1, 6, "", ("93.184.216.34", 443)),
            (10, 1, 6, "", ("2606:4700:4700::1111", 443)),
        ]

    monkeypatch.setattr(loop, "getaddrinfo", getaddrinfo)

    assert await cimd._resolve_addresses("client.example.com", 443) == (
        "93.184.216.34",
        "2606:4700:4700::1111",
    )


def test_redirect_validation_covers_ports_and_loopback_policy() -> None:
    """Redirect validation accepts localhost but rejects malformed and public HTTP URLs."""
    cimd.validate_oauth_redirect_uri("http://localhost/callback")
    cimd.validate_oauth_redirect_uri("http://127.0.0.1/callback")
    with pytest.raises(ValueError, match="invalid"):
        cimd.validate_oauth_redirect_uri("https://client.example.com:bad/callback")
    with pytest.raises(ValueError, match="invalid"):
        cimd.validate_oauth_redirect_uri("https:///callback")
    with pytest.raises(ValueError, match="loopback"):
        cimd.validate_oauth_redirect_uri("ftp://client.example.com/callback")
    with pytest.raises(ValueError, match="loopback"):
        cimd.validate_oauth_redirect_uri("http://8.8.8.8/callback")


def test_public_client_id_validator_fails_closed_on_normalizer_contract_drift(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The public validator accepts a valid URL and rejects an untyped normalizer result."""
    client_id = "https://client.example.com/oauth/client.json"
    cimd.validate_client_id_metadata_document_url(client_id)
    monkeypatch.setattr(cimd, "normalize_public_http_url", lambda *_args, **_kwargs: client_id)

    with pytest.raises(ClientIdMetadataDocumentError, match="Identifier"):
        cimd.validate_client_id_metadata_document_url(client_id)


@pytest.mark.parametrize("addresses", [("not-an-ip",), ()])
@pytest.mark.asyncio
async def test_rejects_invalid_or_empty_dns_answers(addresses: tuple[str, ...]) -> None:
    """Unparseable and empty DNS results fail before an HTTP request can start."""

    async def resolve(_: str, __: int) -> tuple[str, ...]:
        return addresses

    fetcher = ClientIdMetadataDocumentFetcher(address_resolver=resolve)
    try:
        with pytest.raises(ClientIdMetadataDocumentError, match="DNS resolution failed"):
            await fetcher.fetch("https://client.example.com/oauth/client.json")
    finally:
        await fetcher.aclose()


@pytest.mark.asyncio
async def test_deduplicates_public_dns_answers_before_fetching() -> None:
    """Repeated public DNS records remain safe and produce one pinned request."""
    client_id = "https://client.example.com/oauth/client.json"
    request_count = 0

    async def resolve(_: str, __: int) -> tuple[str, ...]:
        return ("93.184.216.34", "93.184.216.34")

    def handle(_: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        return httpx.Response(
            200,
            headers={"Content-Type": "application/json"},
            json=_metadata_payload(client_id),
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as http_client:
        fetcher = ClientIdMetadataDocumentFetcher(
            http_client=http_client,
            address_resolver=resolve,
        )
        assert (await fetcher.fetch(client_id)).client_id == client_id

    assert request_count == 1


@pytest.mark.asyncio
async def test_pins_an_explicit_port_ipv6_client_identifier() -> None:
    """IPv6 Client Identifier URLs preserve brackets, port, Host, and SNI."""
    client_id = "https://[2606:4700:4700::1111]:8443/oauth/client.json"

    async def resolve(host: str, port: int) -> tuple[str, ...]:
        assert (host, port) == ("2606:4700:4700::1111", 8443)
        return ("2606:4700:4700::1111",)

    def handle(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == client_id
        assert request.headers["host"] == "[2606:4700:4700::1111]:8443"
        assert request.extensions["sni_hostname"] == "2606:4700:4700::1111"
        return httpx.Response(
            200,
            headers={"Content-Type": "application/vnd.example+json"},
            json=_metadata_payload(client_id),
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as http_client:
        fetcher = ClientIdMetadataDocumentFetcher(
            http_client=http_client,
            address_resolver=resolve,
        )
        assert (await fetcher.fetch(client_id)).client_id == client_id


@pytest.mark.asyncio
async def test_invalid_cache_age_is_not_reused() -> None:
    """Malformed cache lifetime metadata cannot make a client document trusted."""
    client_id = "https://client.example.com/oauth/client.json"
    request_count = 0

    def handle(_: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        return httpx.Response(
            200,
            headers={"Content-Type": "application/json", "Cache-Control": "max-age=invalid"},
            json=_metadata_payload(client_id),
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as http_client:
        fetcher = ClientIdMetadataDocumentFetcher(
            http_client=http_client,
            address_resolver=_public_address,
        )
        await fetcher.fetch(client_id)
        await fetcher.fetch(client_id)

    assert request_count == 2


@pytest.mark.asyncio
async def test_bounded_cache_evicts_the_oldest_client(monkeypatch: pytest.MonkeyPatch) -> None:
    """The success cache cannot grow without bound across distinct client identities."""
    monkeypatch.setattr(cimd, "_MAX_CACHE_ENTRIES", 1)
    request_count = 0

    def handle(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        host = request.headers["host"]
        client_id = f"https://{host}/oauth/client.json"
        return httpx.Response(
            200,
            headers={"Content-Type": "application/json", "Cache-Control": "max-age=60"},
            json=_metadata_payload(client_id),
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as http_client:
        fetcher = ClientIdMetadataDocumentFetcher(
            http_client=http_client,
            address_resolver=_public_address,
        )
        await fetcher.fetch("https://one.example/oauth/client.json")
        await fetcher.fetch("https://two.example/oauth/client.json")
        await fetcher.fetch("https://one.example/oauth/client.json")

    assert request_count == 3


@pytest.mark.asyncio
async def test_dns_and_http_transport_errors_fail_closed() -> None:
    """Resolver and connection failures become safe client-metadata errors."""

    async def failing_resolver(_: str, __: int) -> tuple[str, ...]:
        raise OSError("DNS unavailable")

    dns_fetcher = ClientIdMetadataDocumentFetcher(address_resolver=failing_resolver)
    try:
        with pytest.raises(ClientIdMetadataDocumentError, match="DNS resolution failed"):
            await dns_fetcher.fetch("https://client.example.com/oauth/client.json")
    finally:
        await dns_fetcher.aclose()

    def failing_transport(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(failing_transport)) as http_client:
        http_fetcher = ClientIdMetadataDocumentFetcher(
            http_client=http_client,
            address_resolver=_public_address,
        )
        with pytest.raises(ClientIdMetadataDocumentError, match="fetch failed"):
            await http_fetcher.fetch("https://client.example.com/oauth/client.json")
        await http_fetcher.aclose()
        assert http_client.is_closed is False


@pytest.mark.asyncio
async def test_rejects_a_non_numeric_content_length() -> None:
    """Malformed response size metadata fails closed and still closes the response."""

    def handle(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"Content-Type": "application/json", "Content-Length": "invalid"},
            content=b"{}",
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handle)) as http_client:
        fetcher = ClientIdMetadataDocumentFetcher(
            http_client=http_client,
            address_resolver=_public_address,
        )
        with pytest.raises(ClientIdMetadataDocumentError, match="response is invalid"):
            await fetcher.fetch("https://client.example.com/oauth/client.json")
