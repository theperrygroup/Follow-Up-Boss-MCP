"""Secure OAuth Client ID Metadata Document discovery.

The fetcher in this module deliberately resolves and validates DNS itself, then
connects HTTPX to the selected public IP while preserving the original Host and
TLS SNI values. That closes the DNS-rebinding gap created by validating a name
and then allowing the HTTP stack to resolve it a second time.
"""

from __future__ import annotations

import asyncio
import ipaddress
import json
import socket
import time
import weakref
from collections import OrderedDict, deque
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol, cast
from urllib.parse import SplitResult, unquote, urlsplit, urlunsplit

import httpx
from pydantic import AnyHttpUrl, BaseModel, ConfigDict, field_validator, model_validator

from followupboss_mcp.url_validation import normalize_public_http_url

_DEFAULT_FETCH_TIMEOUT_SECONDS = 5.0
_MAX_DOCUMENT_BYTES = 5 * 1024
_MAX_CACHE_ENTRIES = 1024
_MAX_CACHE_SECONDS = 60 * 60 * 24
_MAX_CONCURRENT_FETCHES = 4
_MAX_UNCACHED_FETCHES_PER_WINDOW = 32
_FETCH_ADMISSION_WINDOW_SECONDS = 60.0

type AddressResolver = Callable[[str, int], Awaitable[Sequence[str]]]


@dataclass(frozen=True, slots=True)
class _CachedDocument:
    """One validated document and its bounded freshness lifetime."""

    document: ClientIdMetadataDocument
    expires_at: int


class ClientIdMetadataDocumentError(ValueError):
    """Raised when a Client ID Metadata Document cannot be trusted."""


class ClientIdMetadataResolver(Protocol):
    """Boundary used by the authorization flow to resolve URL client metadata."""

    async def fetch(self, client_id: str) -> ClientIdMetadataDocument:
        """Return validated metadata for one exact Client Identifier URL."""

    async def aclose(self) -> None:
        """Close any owned network resources."""


class ClientIdMetadataDocument(BaseModel):
    """Validated client metadata consumed by the hosted authorization server."""

    model_config = ConfigDict(extra="allow", frozen=True)

    client_id: str
    client_name: str
    redirect_uris: tuple[str, ...]
    scope: tuple[str, ...] = ()
    token_endpoint_auth_method: str = "none"

    @model_validator(mode="before")
    @classmethod
    def _reject_secret_fields(cls, value: object) -> object:
        """Reject symmetric credentials that a self-asserted document cannot establish."""
        if isinstance(value, Mapping):
            if any(field in value for field in ("client_secret", "client_secret_expires_at")):
                raise ValueError("Client metadata documents must not contain secret fields.")
            jwks = value.get("jwks")
            keys = jwks.get("keys") if isinstance(jwks, Mapping) else None
            if isinstance(keys, list) and any(
                isinstance(key, Mapping)
                and not {"d", "p", "q", "dp", "dq", "qi", "oth", "k"}.isdisjoint(key)
                for key in keys
            ):
                raise ValueError("Client metadata documents must not contain private key material.")
        return value

    @field_validator("client_id", "client_name", "token_endpoint_auth_method", mode="before")
    @classmethod
    def _validate_required_strings(cls, value: object, info: Any) -> str:
        """Require exact, non-empty string metadata values."""
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{info.field_name} must be a non-empty string.")
        return value if info.field_name == "client_id" else value.strip()

    @field_validator("redirect_uris", mode="before")
    @classmethod
    def _validate_redirect_uris(cls, value: object) -> tuple[str, ...]:
        """Require a non-empty JSON array of safe redirect URLs."""
        if not isinstance(value, list) or not value:
            raise ValueError("redirect_uris must be a non-empty JSON array.")
        redirects: list[str] = []
        for redirect_uri in value:
            if not isinstance(redirect_uri, str) or not redirect_uri.strip():
                raise ValueError("redirect_uris entries must be non-empty strings.")
            validate_oauth_redirect_uri(redirect_uri)
            if redirect_uri not in redirects:
                redirects.append(redirect_uri)
        return tuple(redirects)

    @field_validator("scope", mode="before")
    @classmethod
    def _validate_scope(cls, value: object) -> tuple[str, ...]:
        """Normalize the RFC 7591 space-delimited scope string."""
        if value is None:
            return ()
        if not isinstance(value, str):
            raise ValueError("scope must be a string.")
        return tuple(dict.fromkeys(part for part in value.split(" ") if part))

    @field_validator("token_endpoint_auth_method")
    @classmethod
    def _validate_token_endpoint_auth_method(cls, value: str) -> str:
        """Accept only the public-client method implemented by this server."""
        if value != "none":
            raise ValueError("token_endpoint_auth_method is not supported.")
        return value

    def allows_redirect_uri(self, redirect_uri: str) -> bool:
        """Match a registered URI, allowing native HTTP loopback port selection."""
        return oauth_redirect_uri_matches(redirect_uri, self.redirect_uris)


def _loopback_redirect_without_port(redirect_uri: str) -> str | None:
    """Remove only a valid HTTP loopback port, preserving all other URI bytes."""
    if not redirect_uri.startswith("http://") or any(
        ord(character) <= 0x20 or ord(character) == 0x7F or character == "\\"
        for character in redirect_uri
    ):
        return None
    try:
        # This validator accepts HTTP only for literal loopback IPs or localhost.
        validate_oauth_redirect_uri(redirect_uri)
        parsed = urlsplit(redirect_uri)
        port = parsed.port
        if _port_is_explicit(parsed) and not port:
            return None
    except ValueError:
        return None
    authority = parsed.netloc if port is None else parsed.netloc.rsplit(":", 1)[0]
    # Do not URL-normalize the path/query: even an empty '?' must remain distinct.
    suffix = redirect_uri[len("http://") + len(parsed.netloc) :]
    return f"http://{authority}{suffix}"


def oauth_redirect_uri_matches(redirect_uri: str, registered_uris: Sequence[str]) -> bool:
    """Apply exact registration matching except RFC 8252 native loopback ports.

    This exception applies only to registration checks. Authorization codes must
    remain bound to the exact requested URI, including the selected port.
    """
    if redirect_uri in registered_uris:
        return True
    loopback_uri = _loopback_redirect_without_port(redirect_uri)
    return loopback_uri is not None and any(
        loopback_uri == _loopback_redirect_without_port(registered_uri)
        for registered_uri in registered_uris
    )


async def _resolve_addresses(host: str, port: int) -> tuple[str, ...]:
    """Resolve a hostname without blocking the authorization-server event loop."""
    records = await asyncio.get_running_loop().getaddrinfo(
        host,
        port,
        type=socket.SOCK_STREAM,
    )
    return tuple(dict.fromkeys(str(record[4][0]) for record in records))


def _validate_client_identifier_url(client_id: str) -> tuple[SplitResult, str, int]:
    """Validate a Client Identifier URL while preserving its exact string identity."""
    if client_id != client_id.strip() or any(ord(character) < 0x20 for character in client_id):
        raise ClientIdMetadataDocumentError("Invalid Client Identifier URL.")
    try:
        normalized = normalize_public_http_url(
            client_id,
            field_name="client_id",
            strip_trailing_slash=False,
            allow_loopback_http=False,
        )
        parsed = urlsplit(client_id)
        port = parsed.port or 443
    except (TypeError, ValueError) as exc:
        raise ClientIdMetadataDocumentError("Invalid Client Identifier URL.") from exc
    if not isinstance(normalized, AnyHttpUrl) or parsed.scheme.lower() != "https":
        raise ClientIdMetadataDocumentError("Invalid Client Identifier URL.")
    if parsed.username is not None or parsed.password is not None:
        raise ClientIdMetadataDocumentError("Invalid Client Identifier URL.")
    if not parsed.hostname or not parsed.path or parsed.path == "/":
        raise ClientIdMetadataDocumentError("Invalid Client Identifier URL.")
    if any(unquote(segment) in {".", ".."} for segment in parsed.path.split("/")):
        raise ClientIdMetadataDocumentError("Invalid Client Identifier URL.")
    return parsed, parsed.hostname, port


def validate_client_id_metadata_document_url(client_id: str) -> None:
    """Reject strings that cannot identify a supported metadata document."""
    _validate_client_identifier_url(client_id)


def validate_oauth_redirect_uri(redirect_uri: str) -> None:
    """Require HTTPS redirects, except for native-client loopback callbacks."""
    try:
        parsed = urlsplit(redirect_uri)
        _ = parsed.port
    except ValueError as exc:
        raise ValueError("redirect URI is invalid.") from exc
    if "#" in redirect_uri or parsed.username is not None or parsed.password is not None:
        raise ValueError("redirect URI is invalid.")
    host = parsed.hostname
    if not host:
        raise ValueError("redirect URI is invalid.")
    if parsed.scheme == "https":
        return
    if parsed.scheme != "http":
        raise ValueError("redirect URI must use HTTPS or a loopback HTTP address.")
    if host.lower() == "localhost":
        return
    try:
        address = ipaddress.ip_address(host)
    except ValueError as exc:
        raise ValueError("redirect URI must use HTTPS or a loopback HTTP address.") from exc
    if not address.is_loopback:
        raise ValueError("redirect URI must use HTTPS or a loopback HTTP address.")


def _validated_public_addresses(addresses: Sequence[str]) -> tuple[str, ...]:
    """Reject empty DNS answers and every special-use destination."""
    validated: list[str] = []
    for raw_address in addresses:
        try:
            address = ipaddress.ip_address(raw_address)
        except ValueError as exc:
            raise ClientIdMetadataDocumentError("Client metadata DNS resolution failed.") from exc
        if not address.is_global:
            raise ClientIdMetadataDocumentError("Client metadata target is not public.")
        rendered = str(address)
        if rendered not in validated:
            validated.append(rendered)
    if not validated:
        raise ClientIdMetadataDocumentError("Client metadata DNS resolution failed.")
    return tuple(validated)


def _port_is_explicit(parsed: SplitResult) -> bool:
    """Return whether the URL authority explicitly includes a port."""
    authority = parsed.netloc
    if authority.startswith("["):
        return "]:" in authority
    return authority.count(":") == 1


def _authority(host: str, port: int, *, include_port: bool) -> str:
    """Build an HTTP authority for a DNS name or IP address."""
    rendered_host = f"[{host}]" if ":" in host else host
    return f"{rendered_host}:{port}" if include_port else rendered_host


def _cache_lifetime_seconds(headers: httpx.Headers) -> int:
    """Return a bounded freshness lifetime from RFC 9111 Cache-Control metadata."""
    directives: dict[str, str | None] = {}
    for part in headers.get("Cache-Control", "").split(","):
        name, separator, value = part.strip().partition("=")
        if name:
            directives[name.lower()] = value.strip().strip('"') if separator else None
    if "no-store" in directives or "no-cache" in directives:
        return 0
    raw_max_age = directives.get("max-age")
    if raw_max_age is None:
        return 0
    try:
        max_age = max(int(raw_max_age), 0)
        age = max(int(headers.get("Age", "0")), 0)
    except ValueError:
        return 0
    return min(max(max_age - age, 0), _MAX_CACHE_SECONDS)


class ClientIdMetadataDocumentFetcher:
    """Fetch and validate public Client ID Metadata Documents."""

    def __init__(
        self,
        *,
        http_client: httpx.AsyncClient | None = None,
        address_resolver: AddressResolver | None = None,
        time_provider: Callable[[], int] | None = None,
    ) -> None:
        """Initialize the secure CIMD fetch boundary."""
        self._http_client = http_client or httpx.AsyncClient(
            follow_redirects=False,
            timeout=_DEFAULT_FETCH_TIMEOUT_SECONDS,
            trust_env=False,
            limits=httpx.Limits(max_keepalive_connections=0),
        )
        self._owns_client = http_client is None
        self._address_resolver = address_resolver or _resolve_addresses
        self._time_provider = time_provider or (lambda: int(time.time()))
        self._cache: OrderedDict[str, _CachedDocument] = OrderedDict()
        self._fetch_locks: weakref.WeakValueDictionary[str, asyncio.Lock] = (
            weakref.WeakValueDictionary()
        )
        self._fetch_semaphore = asyncio.Semaphore(_MAX_CONCURRENT_FETCHES)
        self._admission_lock = asyncio.Lock()
        self._uncached_fetch_timestamps: deque[float] = deque()

    async def _admit_uncached_fetch(self) -> None:
        """Admit one bounded outbound fetch or fail fast under global abuse."""
        async with self._admission_lock:
            now = time.monotonic()
            window_start = now - _FETCH_ADMISSION_WINDOW_SECONDS
            while (
                self._uncached_fetch_timestamps
                and self._uncached_fetch_timestamps[0] <= window_start
            ):
                self._uncached_fetch_timestamps.popleft()
            if len(self._uncached_fetch_timestamps) >= _MAX_UNCACHED_FETCHES_PER_WINDOW:
                raise ClientIdMetadataDocumentError(
                    "Client metadata discovery is temporarily rate limited."
                )
            self._uncached_fetch_timestamps.append(now)

    async def fetch(self, client_id: str) -> ClientIdMetadataDocument:
        """Fetch one metadata document after validating and pinning its destination."""
        parsed, host, port = _validate_client_identifier_url(client_id)
        now = self._time_provider()
        cached = self._cache.get(client_id)
        if cached is not None and cached.expires_at > now:
            self._cache.move_to_end(client_id)
            return cached.document
        if cached is not None:
            del self._cache[client_id]

        fetch_lock = self._fetch_locks.get(client_id)
        if fetch_lock is None:
            fetch_lock = asyncio.Lock()
            self._fetch_locks[client_id] = fetch_lock
        try:
            async with asyncio.timeout(_DEFAULT_FETCH_TIMEOUT_SECONDS):
                async with fetch_lock:
                    now = self._time_provider()
                    cached = self._cache.get(client_id)
                    if cached is not None and cached.expires_at > now:
                        self._cache.move_to_end(client_id)
                        return cached.document
                    await self._admit_uncached_fetch()
                    async with self._fetch_semaphore:
                        document, cache_lifetime = await self._fetch_uncached(
                            client_id=client_id,
                            parsed=parsed,
                            host=host,
                            port=port,
                        )
                    if cache_lifetime > 0:
                        self._cache[client_id] = _CachedDocument(
                            document=document,
                            expires_at=now + cache_lifetime,
                        )
                        self._cache.move_to_end(client_id)
                        while len(self._cache) > _MAX_CACHE_ENTRIES:
                            self._cache.popitem(last=False)
                    return document
        except TimeoutError as exc:
            raise ClientIdMetadataDocumentError("Client metadata fetch timed out.") from exc

    async def _fetch_uncached(
        self,
        *,
        client_id: str,
        parsed: SplitResult,
        host: str,
        port: int,
    ) -> tuple[ClientIdMetadataDocument, int]:
        """Fetch, parse, and validate one uncached document."""
        try:
            resolved = await self._address_resolver(host, port)
        except (OSError, TimeoutError) as exc:
            raise ClientIdMetadataDocumentError("Client metadata DNS resolution failed.") from exc
        addresses = _validated_public_addresses(resolved)
        response = await self._request_pinned(
            parsed=parsed,
            host=host,
            port=port,
            address=addresses[0],
        )
        cache_lifetime = _cache_lifetime_seconds(response.headers)
        payload = await self._read_document(response)
        try:
            raw_document = json.loads(payload)
            if not isinstance(raw_document, Mapping):
                raise ValueError("metadata document must be a JSON object")
            document = ClientIdMetadataDocument.model_validate(
                cast(Mapping[str, object], raw_document)
            )
        except (TypeError, ValueError) as exc:
            raise ClientIdMetadataDocumentError("Client metadata document is invalid.") from exc
        if document.client_id != client_id:
            raise ClientIdMetadataDocumentError("Client metadata client_id does not match.")
        return document, cache_lifetime

    async def aclose(self) -> None:
        """Close the internally owned HTTP client."""
        if self._owns_client:
            await self._http_client.aclose()

    async def _request_pinned(
        self,
        *,
        parsed: SplitResult,
        host: str,
        port: int,
        address: str,
    ) -> httpx.Response:
        """Connect to one validated IP while retaining the original TLS identity."""
        include_port = _port_is_explicit(parsed)
        pinned_url = urlunsplit(
            (
                "https",
                _authority(address, port, include_port=include_port),
                parsed.path,
                parsed.query,
                "",
            )
        )
        ascii_host = host.encode("idna").decode("ascii")
        request = self._http_client.build_request(
            "GET",
            pinned_url,
            headers={
                "Accept": "application/json",
                "Connection": "close",
                "Host": _authority(ascii_host, port, include_port=include_port),
            },
        )
        request.extensions["sni_hostname"] = ascii_host
        try:
            return await self._http_client.send(request, stream=True, follow_redirects=False)
        except httpx.HTTPError as exc:
            raise ClientIdMetadataDocumentError("Client metadata fetch failed.") from exc

    async def _read_document(self, response: httpx.Response) -> bytes:
        """Read one successful JSON response without exceeding the 5 KiB cap."""
        try:
            if response.status_code != 200:
                raise ClientIdMetadataDocumentError("Client metadata fetch failed.")
            media_type = response.headers.get("Content-Type", "").split(";", maxsplit=1)[0].lower()
            if media_type != "application/json" and not (
                media_type.startswith("application/") and media_type.endswith("+json")
            ):
                raise ClientIdMetadataDocumentError("Client metadata response is not JSON.")
            content_length = response.headers.get("Content-Length")
            if content_length is not None:
                try:
                    declared_length = int(content_length)
                except ValueError as exc:
                    raise ClientIdMetadataDocumentError(
                        "Client metadata response is invalid."
                    ) from exc
                if declared_length > _MAX_DOCUMENT_BYTES:
                    raise ClientIdMetadataDocumentError("Client metadata document is too large.")
            content = bytearray()
            async for chunk in response.aiter_bytes():
                content.extend(chunk)
                if len(content) > _MAX_DOCUMENT_BYTES:
                    raise ClientIdMetadataDocumentError("Client metadata document is too large.")
            return bytes(content)
        finally:
            await response.aclose()


__all__ = [
    "ClientIdMetadataDocument",
    "ClientIdMetadataDocumentError",
    "ClientIdMetadataDocumentFetcher",
    "ClientIdMetadataResolver",
    "oauth_redirect_uri_matches",
    "validate_oauth_redirect_uri",
    "validate_client_id_metadata_document_url",
]
