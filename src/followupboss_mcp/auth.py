"""Authentication helpers."""

from __future__ import annotations

import base64
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from followupboss_mcp.constants import HEADER_AUTHORIZATION
from followupboss_mcp.errors import FollowUpBossConfigError


class AuthMode(StrEnum):
    """Supported authentication modes."""

    API_KEY = "api_key"
    OAUTH = "oauth"


class AuthStrategy(Protocol):
    """Protocol for auth header injection."""

    def authorization_header(self) -> str:
        """Return a fully formatted authorization header value."""


@dataclass(frozen=True)
class BasicAuthStrategy:
    """HTTP Basic authentication with API key as the username."""

    api_key: str

    def authorization_header(self) -> str:
        """Return a redaction-safe Basic auth header."""
        encoded = base64.b64encode(f"{self.api_key}:".encode()).decode("ascii")
        return f"Basic {encoded}"

    def __repr__(self) -> str:
        """Return a redacted representation."""
        return "BasicAuthStrategy(api_key=***redacted***)"


@dataclass(frozen=True)
class BearerAuthStrategy:
    """OAuth Bearer authentication."""

    access_token: str

    def authorization_header(self) -> str:
        """Return a bearer token authorization header."""
        return f"Bearer {self.access_token}"

    def __repr__(self) -> str:
        """Return a redacted representation."""
        return "BearerAuthStrategy(access_token=***redacted***)"


def build_auth_strategy(
    *,
    auth_mode: AuthMode,
    api_key: str | None,
    access_token: str | None,
) -> AuthStrategy:
    """Build an auth strategy from explicit credential inputs."""
    if auth_mode is AuthMode.API_KEY:
        if not api_key:
            raise FollowUpBossConfigError("FOLLOWUPBOSS_API_KEY is required for api_key auth.")
        return BasicAuthStrategy(api_key=api_key)

    if not access_token:
        raise FollowUpBossConfigError("FOLLOWUPBOSS_ACCESS_TOKEN is required for oauth auth.")
    return BearerAuthStrategy(access_token=access_token)


def inject_authorization(headers: dict[str, str], auth_strategy: AuthStrategy) -> dict[str, str]:
    """Return a new header mapping with the authorization header populated."""
    merged_headers = dict(headers)
    merged_headers[HEADER_AUTHORIZATION] = auth_strategy.authorization_header()
    return merged_headers
