"""URL validation helpers for public hosted MCP endpoints."""

from __future__ import annotations

from urllib.parse import unquote

from pydantic import AnyHttpUrl, TypeAdapter

_HTTP_URL_ADAPTER = TypeAdapter(AnyHttpUrl)
_LOOPBACK_HOSTS = {"localhost", "127.0.0.1", "[::1]", "::1"}


def _host_from_authority(authority: str) -> str:
    """Return the host part from a URL authority-like string."""
    host_port = authority.rsplit("@", maxsplit=1)[-1]
    if host_port.startswith("["):
        closing_bracket = host_port.find("]")
        if closing_bracket != -1:
            return host_port[: closing_bracket + 1]
    return host_port.split(":", maxsplit=1)[0]


def _host_looks_loopback(host: str | None) -> bool:
    """Return whether one parsed host is a local development host."""
    if host is None:
        return False
    normalized_host = host.lower()
    return normalized_host in _LOOPBACK_HOSTS or normalized_host.startswith("127.")


def _add_default_scheme(value: str) -> str:
    """Add an HTTP scheme to host-like settings values that omitted one."""
    if "://" in value:
        return value
    if value.startswith("//"):
        return "https:" + value
    authority = value.split("/", maxsplit=1)[0]
    scheme = "http" if _host_looks_loopback(_host_from_authority(authority)) else "https"
    return f"{scheme}://{value}"


def normalize_public_http_url(
    value: object,
    *,
    field_name: str,
    strip_trailing_slash: bool = True,
    allow_loopback_http: bool = True,
) -> object:
    """Normalize and harden public HTTP URL settings.

    Args:
        value: Raw URL setting value.
        field_name: Field name used in validation errors.
        strip_trailing_slash: Whether to strip trailing slash characters from
            non-root paths before final validation.
        allow_loopback_http: Whether `http://localhost` and loopback addresses
            are accepted for local development and tests.

    Returns:
        A validated `AnyHttpUrl`, or the original non-URL-like value so Pydantic
        can report the type error.

    Raises:
        ValueError: If the value is blank, contains URI-hostile characters, or
            violates the hosted MCP public URL contract.
    """
    if isinstance(value, AnyHttpUrl):
        raw_value = str(value)
    elif isinstance(value, str):
        raw_value = value
    else:
        return value

    normalized = raw_value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be empty.")
    if any(character.isspace() for character in normalized):
        raise ValueError(f"{field_name} must not contain whitespace.")
    if "{" in unquote(normalized) or "}" in unquote(normalized):
        raise ValueError(f"{field_name} must not contain unresolved URL template placeholders.")

    parsed = _HTTP_URL_ADAPTER.validate_python(_add_default_scheme(normalized))
    if parsed.query:
        raise ValueError(f"{field_name} must not include a query string.")
    if parsed.fragment:
        raise ValueError(f"{field_name} must not include a fragment.")
    if parsed.scheme == "http" and not (allow_loopback_http and _host_looks_loopback(parsed.host)):
        raise ValueError(f"{field_name} must use HTTPS unless it points to localhost.")

    canonical = str(parsed)
    if strip_trailing_slash:
        canonical = canonical.rstrip("/")
    return _HTTP_URL_ADAPTER.validate_python(canonical)


def validated_public_http_url(
    value: str,
    *,
    field_name: str,
    strip_trailing_slash: bool = True,
    allow_loopback_http: bool = True,
) -> AnyHttpUrl:
    """Return a normalized `AnyHttpUrl` for known string URL values."""
    normalized = normalize_public_http_url(
        value,
        field_name=field_name,
        strip_trailing_slash=strip_trailing_slash,
        allow_loopback_http=allow_loopback_http,
    )
    if not isinstance(normalized, AnyHttpUrl):
        raise TypeError(f"{field_name} must be a URL string.")
    return normalized
