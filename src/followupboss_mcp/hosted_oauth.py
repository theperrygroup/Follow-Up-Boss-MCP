"""Hosted OAuth authorization-server helpers for the MCP deployment."""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import time
from collections.abc import Mapping, Sequence
from typing import Any, Protocol, Self, cast
from urllib.parse import parse_qs, urlencode

import httpx
from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, SecretStr, field_validator
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse, RedirectResponse, Response
from starlette.routing import Route

from followupboss_mcp.config import FollowUpBossTenantRuntimeDefaults
from followupboss_mcp.models.identity import IdentityResponse

_DEFAULT_ACCESS_TOKEN_SECONDS = 3600
_DEFAULT_AUTHORIZATION_CODE_SECONDS = 300
_DEFAULT_REFRESH_TOKEN_SECONDS = 60 * 60 * 24 * 30
_DEFAULT_STATE_SECONDS = 600
_DEFAULT_TOKEN_BYTES = 32
_SUPPORTED_CODE_CHALLENGE_METHODS = ("S256", "plain")


def _normalize_required_string(value: str, *, field_name: str) -> str:
    """Normalize a required string.

    Args:
        value: Raw string value.
        field_name: Name used in validation messages.

    Returns:
        Trimmed string value.

    Raises:
        ValueError: If the string is blank.
    """
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be empty.")
    return normalized


def _normalize_optional_string(value: object) -> object:
    """Normalize an optional string field.

    Args:
        value: Raw field value.

    Returns:
        Trimmed string, `None` for blank strings, or the original value.
    """
    if not isinstance(value, str):
        return value
    return value.strip() or None


def _normalize_scopes(value: object) -> object:
    """Normalize an OAuth scope value into a tuple.

    Args:
        value: Raw scope value.

    Returns:
        Tuple of unique scopes, or the original unsupported value.
    """
    if value is None:
        return ()
    raw_scopes: Sequence[object]
    if isinstance(value, str):
        raw_scopes = tuple(part for part in value.replace(",", " ").split(" ") if part.strip())
    elif isinstance(value, Sequence) and not isinstance(value, bytes | bytearray):
        raw_scopes = value
    else:
        return value

    normalized_scopes: list[str] = []
    for scope in raw_scopes:
        if not isinstance(scope, str):
            return value
        normalized_scope = _normalize_required_string(scope, field_name="scope")
        if normalized_scope not in normalized_scopes:
            normalized_scopes.append(normalized_scope)
    return tuple(normalized_scopes)


def _base64_url_sha256(value: str) -> str:
    """Return the base64url SHA-256 digest for one PKCE verifier.

    Args:
        value: Raw verifier value.

    Returns:
        Base64url digest without padding.
    """
    digest = hashlib.sha256(value.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def _hash_secret(value: str) -> str:
    """Hash a secret token for persistent lookup.

    Args:
        value: Raw secret token.

    Returns:
        Canonical `sha256:` hash value.
    """
    normalized = _normalize_required_string(value, field_name="token")
    return "sha256:" + hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _new_secret_token(prefix: str) -> str:
    """Create an opaque URL-safe OAuth token.

    Args:
        prefix: Human-readable token prefix.

    Returns:
        Opaque token value.
    """
    return f"{prefix}_{secrets.token_urlsafe(_DEFAULT_TOKEN_BYTES)}"


def _json_error(
    error: str,
    description: str,
    *,
    status_code: int = 400,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    """Build a standard OAuth-style JSON error response.

    Args:
        error: OAuth error code.
        description: Human-readable description.
        status_code: HTTP status code.
        headers: Optional response headers.

    Returns:
        JSON error response.
    """
    return JSONResponse(
        {"error": error, "error_description": description},
        status_code=status_code,
        headers=dict(headers or {}),
    )


def _redirect_error(
    redirect_uri: str,
    error: str,
    *,
    state: str | None,
    description: str | None = None,
) -> RedirectResponse:
    """Redirect an OAuth error to a client callback.

    Args:
        redirect_uri: Client callback URL.
        error: OAuth error code.
        state: Optional client state to echo.
        description: Optional human-readable description.

    Returns:
        Redirect response.
    """
    params: dict[str, str] = {"error": error}
    if description:
        params["error_description"] = description
    if state:
        params["state"] = state
    separator = "&" if "?" in redirect_uri else "?"
    return RedirectResponse(f"{redirect_uri}{separator}{urlencode(params)}", status_code=302)


async def _form_payload(request: Request) -> dict[str, str]:
    """Parse an OAuth form request without requiring multipart dependencies.

    Args:
        request: Incoming Starlette request.

    Returns:
        Mapping of the first value for each submitted form key.
    """
    body = (await request.body()).decode("utf-8")
    parsed = parse_qs(body, keep_blank_values=True)
    return {key: values[0] if values else "" for key, values in parsed.items()}


class HostedOAuthSettings(BaseModel):
    """Configuration for the hosted MCP OAuth authorization layer."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    issuer_url: AnyHttpUrl
    resource_server_url: AnyHttpUrl
    required_scopes: tuple[str, ...] = ()
    fub_client_id: str
    fub_client_secret: SecretStr
    fub_authorize_url: AnyHttpUrl | str = Field(
        default="https://app.followupboss.com/oauth/authorize"
    )
    fub_token_url: AnyHttpUrl | str = Field(default="https://app.followupboss.com/oauth/token")
    fub_callback_url: AnyHttpUrl
    fub_base_url: AnyHttpUrl | str = Field(default="https://api.followupboss.com/v1")
    token_secret_prefix: str
    system_name: str | None = None
    system_key: SecretStr | None = None
    access_token_seconds: int = _DEFAULT_ACCESS_TOKEN_SECONDS
    authorization_code_seconds: int = _DEFAULT_AUTHORIZATION_CODE_SECONDS
    refresh_token_seconds: int = _DEFAULT_REFRESH_TOKEN_SECONDS
    state_seconds: int = _DEFAULT_STATE_SECONDS

    @field_validator("required_scopes", mode="before")
    @classmethod
    def _validate_required_scopes(cls, value: object) -> object:
        """Normalize required scopes.

        Args:
            value: Raw scope value.

        Returns:
            Normalized scope tuple.
        """
        return _normalize_scopes(value)

    @field_validator("fub_client_id", "token_secret_prefix")
    @classmethod
    def _validate_required_strings(cls, value: str, info: Any) -> str:
        """Require non-empty OAuth settings fields.

        Args:
            value: Raw string value.
            info: Pydantic field context.

        Returns:
            Trimmed string value.
        """
        return _normalize_required_string(value, field_name=str(info.field_name))

    @field_validator("system_name", mode="before")
    @classmethod
    def _validate_optional_system_name(cls, value: object) -> object:
        """Normalize optional system names.

        Args:
            value: Raw system-name value.

        Returns:
            Normalized system name.
        """
        return _normalize_optional_string(value)

    @field_validator(
        "access_token_seconds",
        "authorization_code_seconds",
        "refresh_token_seconds",
        "state_seconds",
    )
    @classmethod
    def _validate_positive_ttl(cls, value: int, info: Any) -> int:
        """Require positive TTL settings.

        Args:
            value: Raw TTL value.
            info: Pydantic field context.

        Returns:
            Positive TTL value.
        """
        if value <= 0:
            raise ValueError(f"{info.field_name} must be greater than zero.")
        return value

    @property
    def issuer(self) -> str:
        """Return the normalized issuer URL without a trailing slash.

        Returns:
            OAuth issuer URL.
        """
        return str(self.issuer_url).rstrip("/")

    @property
    def resource_server(self) -> str:
        """Return the normalized protected resource URL.

        Returns:
            MCP resource-server URL.
        """
        return str(self.resource_server_url)

    @property
    def scope_string(self) -> str:
        """Return the default MCP scope string.

        Returns:
            Space-delimited scopes.
        """
        return " ".join(self.required_scopes)

    def endpoint_url(self, path: str) -> str:
        """Build an absolute OAuth endpoint URL.

        Args:
            path: Absolute path below the issuer URL.

        Returns:
            Absolute endpoint URL.
        """
        normalized_path = "/" + path.lstrip("/")
        return f"{self.issuer}{normalized_path}"


class HostedOAuthDynamicClient(BaseModel):
    """OAuth client metadata accepted by the hosted MCP authorization server."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    client_id: str
    redirect_uris: tuple[str, ...]
    client_name: str = "MCP Client"
    scope: tuple[str, ...] = ()
    token_endpoint_auth_method: str = "none"

    @field_validator("client_id", "client_name", "token_endpoint_auth_method")
    @classmethod
    def _validate_required_strings(cls, value: str, info: Any) -> str:
        """Require non-empty client metadata strings."""
        return _normalize_required_string(value, field_name=str(info.field_name))

    @field_validator("redirect_uris", mode="before")
    @classmethod
    def _validate_redirect_uris(cls, value: object) -> object:
        """Normalize redirect URI lists."""
        if not isinstance(value, Sequence) or isinstance(value, str | bytes | bytearray):
            return value
        normalized: list[str] = []
        for uri in value:
            if not isinstance(uri, str):
                return value
            normalized_uri = _normalize_required_string(uri, field_name="redirect_uri")
            if normalized_uri not in normalized:
                normalized.append(normalized_uri)
        return tuple(normalized)

    @field_validator("scope", mode="before")
    @classmethod
    def _validate_scope(cls, value: object) -> object:
        """Normalize client scopes."""
        return _normalize_scopes(value)

    def allows_redirect_uri(self, redirect_uri: str) -> bool:
        """Return whether a redirect URI is registered for this client.

        Args:
            redirect_uri: Redirect URI supplied by the OAuth request.

        Returns:
            `True` when the URI is registered.
        """
        return redirect_uri in self.redirect_uris


class HostedOAuthPendingAuthorization(BaseModel):
    """Short-lived state for one in-progress delegated OAuth authorization."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    fub_state: str
    client_state: str | None = None
    client_id: str
    redirect_uri: str
    code_challenge: str
    code_challenge_method: str
    scopes: tuple[str, ...]
    resource: str | None = None
    expires_at: int

    @field_validator(
        "fub_state",
        "client_id",
        "redirect_uri",
        "code_challenge",
        "code_challenge_method",
    )
    @classmethod
    def _validate_required_strings(cls, value: str, info: Any) -> str:
        """Require non-empty pending authorization strings."""
        return _normalize_required_string(value, field_name=str(info.field_name))

    @field_validator("client_state", "resource", mode="before")
    @classmethod
    def _validate_optional_strings(cls, value: object) -> object:
        """Normalize optional state fields."""
        return _normalize_optional_string(value)

    @field_validator("scopes", mode="before")
    @classmethod
    def _validate_scopes(cls, value: object) -> object:
        """Normalize requested scopes."""
        return _normalize_scopes(value)


class HostedOAuthAuthorizationCode(BaseModel):
    """One-time MCP authorization code created after Follow Up Boss consent."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    code_hash: str
    client_id: str
    redirect_uri: str
    code_challenge: str
    code_challenge_method: str
    scopes: tuple[str, ...]
    tenant_id: str
    subject: str
    credential_id: str
    expires_at: int

    @field_validator(
        "code_hash",
        "client_id",
        "redirect_uri",
        "code_challenge",
        "code_challenge_method",
        "tenant_id",
        "subject",
        "credential_id",
    )
    @classmethod
    def _validate_required_strings(cls, value: str, info: Any) -> str:
        """Require non-empty authorization-code strings."""
        return _normalize_required_string(value, field_name=str(info.field_name))

    @field_validator("scopes", mode="before")
    @classmethod
    def _validate_scopes(cls, value: object) -> object:
        """Normalize authorization-code scopes."""
        return _normalize_scopes(value)


class HostedOAuthRefreshToken(BaseModel):
    """Durable MCP refresh token metadata."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    token_hash: str
    tenant_id: str
    subject: str
    client_id: str
    scopes: tuple[str, ...]
    credential_id: str
    expires_at: int
    revoked_at: int | None = None

    @field_validator("token_hash", "tenant_id", "subject", "client_id", "credential_id")
    @classmethod
    def _validate_required_strings(cls, value: str, info: Any) -> str:
        """Require non-empty refresh-token strings."""
        return _normalize_required_string(value, field_name=str(info.field_name))

    @field_validator("scopes", mode="before")
    @classmethod
    def _validate_scopes(cls, value: object) -> object:
        """Normalize refresh-token scopes."""
        return _normalize_scopes(value)


class HostedOAuthAccessTokenMetadata(BaseModel):
    """Metadata persisted for an MCP access token."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    token_id: str
    token_hash: str
    tenant_id: str
    subject: str
    client_id: str
    scopes: tuple[str, ...]
    credential_id: str
    expires_at: int

    @field_validator(
        "token_id",
        "token_hash",
        "tenant_id",
        "subject",
        "client_id",
        "credential_id",
    )
    @classmethod
    def _validate_required_strings(cls, value: str, info: Any) -> str:
        """Require non-empty access-token metadata strings."""
        return _normalize_required_string(value, field_name=str(info.field_name))

    @field_validator("scopes", mode="before")
    @classmethod
    def _validate_scopes(cls, value: object) -> object:
        """Normalize access-token scopes."""
        return _normalize_scopes(value)


class FollowUpBossOAuthTokenPayload(BaseModel):
    """Token payload returned by Follow Up Boss OAuth."""

    model_config = ConfigDict(extra="allow", frozen=True)

    access_token: SecretStr
    refresh_token: SecretStr | None = None
    token_type: str = "Bearer"
    expires_in: int | None = None


class FollowUpBossOAuthIdentity(BaseModel):
    """Stable identity fields derived from Follow Up Boss `/identity`."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    account_id: str
    account_name: str | None = None
    user_id: str
    user_email: str | None = None
    user_name: str | None = None

    @field_validator("account_id", "user_id")
    @classmethod
    def _validate_required_strings(cls, value: str, info: Any) -> str:
        """Require non-empty identity strings."""
        return _normalize_required_string(value, field_name=str(info.field_name))

    @field_validator("account_name", "user_email", "user_name", mode="before")
    @classmethod
    def _validate_optional_strings(cls, value: object) -> object:
        """Normalize optional identity strings."""
        return _normalize_optional_string(value)

    @classmethod
    def from_identity_response(cls, identity: IdentityResponse) -> Self:
        """Build OAuth identity metadata from the typed FUB identity response.

        Args:
            identity: Typed Follow Up Boss identity response.

        Returns:
            Normalized OAuth identity metadata.

        Raises:
            ValueError: If required account or user identifiers are absent.
        """
        account_id = identity.account_id
        user_id = identity.id
        if account_id is None:
            raise ValueError("Follow Up Boss identity did not include an account id.")
        if user_id is None:
            raise ValueError("Follow Up Boss identity did not include a user id.")
        return cls.model_validate(
            {
                "account_id": str(account_id),
                "account_name": identity.account.name if identity.account is not None else None,
                "user_id": str(user_id),
                "user_email": identity.email,
                "user_name": identity.name,
            }
        )

    @property
    def tenant_id(self) -> str:
        """Return the canonical hosted tenant id for this FUB account.

        Returns:
            Stable hosted tenant id.
        """
        return f"fub-account-{self.account_id}"

    @property
    def credential_id(self) -> str:
        """Return the canonical hosted credential id for this FUB account.

        Returns:
            Stable hosted credential id.
        """
        return f"cred-{self.tenant_id}-oauth-primary"

    @property
    def subject(self) -> str:
        """Return the subject stored in hosted MCP token metadata.

        Returns:
            Stable subject string.
        """
        return f"fub-user-{self.user_id}"


class ProvisionedHostedTenant(BaseModel):
    """Tenant and credential identifiers provisioned for OAuth login."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    tenant_id: str
    credential_id: str
    subject: str


class HostedOAuthStore(Protocol):
    """Storage boundary for hosted MCP OAuth state and tokens."""

    async def save_client(self, client: HostedOAuthDynamicClient) -> None:
        """Persist OAuth client metadata."""

    async def get_client(self, client_id: str) -> HostedOAuthDynamicClient | None:
        """Return OAuth client metadata when known."""

    async def save_pending_authorization(
        self,
        authorization: HostedOAuthPendingAuthorization,
    ) -> None:
        """Persist short-lived delegated authorization state."""

    async def consume_pending_authorization(
        self,
        fub_state: str,
    ) -> HostedOAuthPendingAuthorization | None:
        """Consume delegated authorization state once."""

    async def save_authorization_code(self, code: HostedOAuthAuthorizationCode) -> None:
        """Persist a one-time MCP authorization code."""

    async def consume_authorization_code(
        self,
        code_hash: str,
    ) -> HostedOAuthAuthorizationCode | None:
        """Consume a one-time MCP authorization code."""

    async def save_access_token(self, token: HostedOAuthAccessTokenMetadata) -> None:
        """Persist MCP access-token metadata."""

    async def save_refresh_token(self, token: HostedOAuthRefreshToken) -> None:
        """Persist MCP refresh-token metadata."""

    async def get_refresh_token(self, token_hash: str) -> HostedOAuthRefreshToken | None:
        """Return refresh-token metadata when active."""

    async def revoke_refresh_token(self, token_hash: str, *, revoked_at: int) -> None:
        """Mark a refresh token as revoked."""


class HostedOAuthTenantProvisioner(Protocol):
    """Provision or update hosted tenant records after FUB OAuth succeeds."""

    async def provision_tenant(
        self,
        *,
        identity: FollowUpBossOAuthIdentity,
        token_payload: FollowUpBossOAuthTokenPayload,
    ) -> ProvisionedHostedTenant:
        """Provision tenant metadata and secret material."""


class FollowUpBossOAuthClient:
    """Async client for the Follow Up Boss OAuth delegation flow."""

    def __init__(
        self,
        settings: HostedOAuthSettings,
        *,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        """Initialize the Follow Up Boss OAuth client.

        Args:
            settings: Hosted OAuth settings.
            http_client: Optional injected HTTP client used by tests.
        """
        self._settings = settings
        self._http_client = http_client
        self._owns_client = http_client is None

    def build_authorize_url(self, *, fub_state: str) -> str:
        """Build the Follow Up Boss authorization URL.

        Args:
            fub_state: Internal state value to validate on callback.

        Returns:
            Fully-qualified FUB authorization URL.
        """
        query = urlencode(
            {
                "response_type": "auth_code",
                "client_id": self._settings.fub_client_id,
                "redirect_uri": str(self._settings.fub_callback_url),
                "state": fub_state,
                "prompt": "login",
            }
        )
        return f"{self._settings.fub_authorize_url}?{query}"

    async def exchange_code(
        self,
        *,
        auth_code: str,
        fub_state: str,
    ) -> FollowUpBossOAuthTokenPayload:
        """Exchange a FUB authorization code for tokens.

        Args:
            auth_code: Authorization code returned by FUB.
            fub_state: State value echoed by FUB.

        Returns:
            Validated token payload.
        """
        client = self._client()
        response = await client.post(
            str(self._settings.fub_token_url),
            headers=self._basic_auth_headers(),
            data={
                "grant_type": "authorization_code",
                "code": auth_code,
                "redirect_uri": str(self._settings.fub_callback_url),
                "state": fub_state,
            },
        )
        response.raise_for_status()
        return FollowUpBossOAuthTokenPayload.model_validate(response.json())

    async def refresh_token(self, *, refresh_token: str) -> FollowUpBossOAuthTokenPayload:
        """Refresh Follow Up Boss OAuth tokens.

        Args:
            refresh_token: Raw FUB refresh token.

        Returns:
            Validated token payload.
        """
        client = self._client()
        response = await client.post(
            str(self._settings.fub_token_url),
            headers=self._basic_auth_headers(),
            data={"grant_type": "refresh_token", "refresh_token": refresh_token},
        )
        response.raise_for_status()
        return FollowUpBossOAuthTokenPayload.model_validate(response.json())

    async def get_identity(
        self,
        *,
        access_token: str,
        defaults: FollowUpBossTenantRuntimeDefaults | None = None,
    ) -> FollowUpBossOAuthIdentity:
        """Fetch identity metadata with a FUB access token.

        Args:
            access_token: FUB access token.
            defaults: Optional runtime defaults overriding the configured base URL.

        Returns:
            Follow Up Boss OAuth identity metadata.
        """
        base_url = str(defaults.base_url if defaults is not None else self._settings.fub_base_url)
        headers = {"Authorization": f"Bearer {access_token}"}
        if self._settings.system_name is not None:
            headers["X-System"] = self._settings.system_name
        if self._settings.system_key is not None:
            headers["X-System-Key"] = self._settings.system_key.get_secret_value()
        response = await self._client().get(
            f"{base_url.rstrip('/')}/identity",
            headers=headers,
        )
        response.raise_for_status()
        return FollowUpBossOAuthIdentity.from_identity_response(
            IdentityResponse.model_validate(response.json())
        )

    async def aclose(self) -> None:
        """Close the owned HTTP client."""
        if self._owns_client and self._http_client is not None:
            await self._http_client.aclose()

    def _client(self) -> httpx.AsyncClient:
        """Return an async HTTP client.

        Returns:
            HTTP client for FUB OAuth calls.
        """
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=30.0)
        return self._http_client

    def _basic_auth_headers(self) -> dict[str, str]:
        """Return FUB OAuth token endpoint auth headers.

        Returns:
            HTTP Basic auth header for the FUB OAuth app.
        """
        client_secret = self._settings.fub_client_secret.get_secret_value()
        encoded = base64.b64encode(
            f"{self._settings.fub_client_id}:{client_secret}".encode("ISO-8859-1")
        ).decode("ascii")
        return {"Authorization": f"Basic {encoded}"}


class HostedOAuthApplication:
    """Starlette route provider for the hosted MCP OAuth authorization flow."""

    def __init__(
        self,
        *,
        settings: HostedOAuthSettings,
        store: HostedOAuthStore,
        tenant_provisioner: HostedOAuthTenantProvisioner,
        fub_client: FollowUpBossOAuthClient | None = None,
        time_provider: Any | None = None,
    ) -> None:
        """Initialize the hosted OAuth route provider.

        Args:
            settings: Hosted OAuth settings.
            store: OAuth state and token store.
            tenant_provisioner: Tenant provisioning boundary.
            fub_client: Optional injected FUB OAuth client.
            time_provider: Optional Unix timestamp provider.
        """
        self._settings = settings
        self._store = store
        self._tenant_provisioner = tenant_provisioner
        self._fub_client = fub_client or FollowUpBossOAuthClient(settings)
        self._time_provider = time_provider or (lambda: int(time.time()))

    def routes(self) -> tuple[Route, ...]:
        """Return Starlette routes for OAuth endpoints.

        Returns:
            Route tuple to mount on the hosted streamable HTTP app.
        """
        return (
            Route("/.well-known/oauth-authorization-server", self.authorization_server_metadata),
            Route("/.well-known/openid-configuration", self.authorization_server_metadata),
            Route("/oauth/register", self.register_client, methods=["POST"]),
            Route("/oauth/authorize", self.authorize),
            Route("/oauth/follow-up-boss/callback", self.follow_up_boss_callback),
            Route("/oauth/token", self.token, methods=["POST"]),
        )

    async def aclose(self) -> None:
        """Close owned resources for the hosted OAuth route provider."""
        await self._fub_client.aclose()
        for resource in (self._store, self._tenant_provisioner):
            maybe_aclose = getattr(resource, "aclose", None)
            if callable(maybe_aclose):
                await maybe_aclose()

    async def authorization_server_metadata(self, _: Request) -> JSONResponse:
        """Return OAuth authorization-server metadata.

        Args:
            _: Incoming request.

        Returns:
            OAuth metadata JSON response.
        """
        issuer = self._settings.issuer
        return JSONResponse(
            {
                "issuer": issuer,
                "authorization_endpoint": self._settings.endpoint_url("/oauth/authorize"),
                "token_endpoint": self._settings.endpoint_url("/oauth/token"),
                "registration_endpoint": self._settings.endpoint_url("/oauth/register"),
                "response_types_supported": ["code"],
                "grant_types_supported": ["authorization_code", "refresh_token"],
                "code_challenge_methods_supported": list(_SUPPORTED_CODE_CHALLENGE_METHODS),
                "token_endpoint_auth_methods_supported": ["none"],
                "scopes_supported": list(self._settings.required_scopes),
            },
            headers={"Cache-Control": "public, max-age=3600"},
        )

    async def register_client(self, request: Request) -> JSONResponse:
        """Register one public OAuth client using RFC 7591-style metadata.

        Args:
            request: Incoming registration request.

        Returns:
            Client metadata response.
        """
        try:
            payload = cast(Mapping[str, object], await request.json())
            redirect_uris = payload.get("redirect_uris")
            client_name = str(payload.get("client_name") or "MCP Client")
            raw_scope = payload.get("scope") or self._settings.scope_string
            client = HostedOAuthDynamicClient.model_validate(
                {
                    "client_id": _new_secret_token("mcp_client"),
                    "redirect_uris": redirect_uris,
                    "client_name": client_name,
                    "scope": raw_scope,
                    "token_endpoint_auth_method": "none",
                }
            )
        except Exception:
            return _json_error("invalid_client_metadata", "Invalid client metadata.")

        await self._store.save_client(client)
        return JSONResponse(
            {
                "client_id": client.client_id,
                "client_name": client.client_name,
                "redirect_uris": list(client.redirect_uris),
                "grant_types": ["authorization_code", "refresh_token"],
                "response_types": ["code"],
                "scope": " ".join(client.scope),
                "token_endpoint_auth_method": client.token_endpoint_auth_method,
            },
            status_code=201,
        )

    async def authorize(self, request: Request) -> Response:
        """Handle an MCP OAuth authorization request by delegating to FUB.

        Args:
            request: Incoming authorization request.

        Returns:
            Redirect to FUB or an OAuth error.
        """
        query = request.query_params
        client_id = str(query.get("client_id") or "")
        redirect_uri = str(query.get("redirect_uri") or "")
        client_state = query.get("state")
        code_challenge = str(query.get("code_challenge") or "")
        code_challenge_method = str(query.get("code_challenge_method") or "plain")
        if query.get("response_type") != "code":
            return _json_error("unsupported_response_type", "Only response_type=code is supported.")
        if code_challenge_method not in _SUPPORTED_CODE_CHALLENGE_METHODS:
            return _json_error("invalid_request", "Unsupported code_challenge_method.")
        if not code_challenge:
            return _json_error("invalid_request", "code_challenge is required.")

        client = await self._store.get_client(client_id)
        if client is None:
            return _json_error("invalid_client", "Unknown OAuth client.", status_code=401)
        if not client.allows_redirect_uri(redirect_uri):
            return _json_error("invalid_request", "redirect_uri is not registered.")

        requested_scopes = cast(tuple[str, ...], _normalize_scopes(query.get("scope")))
        if not requested_scopes:
            requested_scopes = self._settings.required_scopes or client.scope
        if self._settings.required_scopes and not set(self._settings.required_scopes).issubset(
            set(requested_scopes)
        ):
            return _redirect_error(
                redirect_uri,
                "invalid_scope",
                state=client_state,
                description="Required MCP scope was not requested.",
            )

        fub_state = _new_secret_token("fub_state")
        authorization = HostedOAuthPendingAuthorization.model_validate(
            {
                "fub_state": fub_state,
                "client_state": client_state,
                "client_id": client.client_id,
                "redirect_uri": redirect_uri,
                "code_challenge": code_challenge,
                "code_challenge_method": code_challenge_method,
                "scopes": requested_scopes,
                "resource": query.get("resource"),
                "expires_at": self._time_provider() + self._settings.state_seconds,
            }
        )
        await self._store.save_pending_authorization(authorization)
        return RedirectResponse(self._fub_client.build_authorize_url(fub_state=fub_state))

    async def follow_up_boss_callback(self, request: Request) -> Response:
        """Handle the Follow Up Boss OAuth redirect.

        Args:
            request: Incoming FUB OAuth callback.

        Returns:
            Redirect back to the original MCP client callback.
        """
        fub_state = str(request.query_params.get("state") or "")
        pending = await self._store.consume_pending_authorization(fub_state)
        if pending is None:
            return PlainTextResponse("Invalid or expired OAuth state.", status_code=400)
        if pending.expires_at <= self._time_provider():
            return _redirect_error(
                pending.redirect_uri,
                "invalid_request",
                state=pending.client_state,
                description="OAuth state expired.",
            )
        if request.query_params.get("response") == "denied":
            return _redirect_error(
                pending.redirect_uri,
                "access_denied",
                state=pending.client_state,
                description="Follow Up Boss consent was denied.",
            )
        auth_code = str(request.query_params.get("code") or "")
        if not auth_code:
            return _redirect_error(
                pending.redirect_uri,
                "invalid_request",
                state=pending.client_state,
                description="Follow Up Boss authorization code was missing.",
            )

        try:
            token_payload = await self._fub_client.exchange_code(
                auth_code=auth_code,
                fub_state=fub_state,
            )
            fub_identity = await self._fub_client.get_identity(
                access_token=token_payload.access_token.get_secret_value()
            )
            provisioned = await self._tenant_provisioner.provision_tenant(
                identity=fub_identity,
                token_payload=token_payload,
            )
        except Exception:
            return _redirect_error(
                pending.redirect_uri,
                "server_error",
                state=pending.client_state,
                description="Follow Up Boss OAuth exchange failed.",
            )

        raw_code = _new_secret_token("mcp_code")
        code_record = HostedOAuthAuthorizationCode.model_validate(
            {
                "code_hash": _hash_secret(raw_code),
                "client_id": pending.client_id,
                "redirect_uri": pending.redirect_uri,
                "code_challenge": pending.code_challenge,
                "code_challenge_method": pending.code_challenge_method,
                "scopes": pending.scopes,
                "tenant_id": provisioned.tenant_id,
                "subject": provisioned.subject,
                "credential_id": provisioned.credential_id,
                "expires_at": self._time_provider() + self._settings.authorization_code_seconds,
            }
        )
        await self._store.save_authorization_code(code_record)

        params = {"code": raw_code}
        if pending.client_state:
            params["state"] = pending.client_state
        separator = "&" if "?" in pending.redirect_uri else "?"
        return RedirectResponse(f"{pending.redirect_uri}{separator}{urlencode(params)}")

    async def token(self, request: Request) -> JSONResponse:
        """Handle OAuth token requests.

        Args:
            request: Incoming token request.

        Returns:
            OAuth token response.
        """
        payload = await _form_payload(request)
        grant_type = payload.get("grant_type")
        if grant_type == "authorization_code":
            return await self._authorization_code_token(payload)
        if grant_type == "refresh_token":
            return await self._refresh_token(payload)
        return _json_error("unsupported_grant_type", "Unsupported grant_type.")

    async def _authorization_code_token(self, payload: Mapping[str, str]) -> JSONResponse:
        """Exchange one MCP authorization code for tokens.

        Args:
            payload: Parsed OAuth token request form fields.

        Returns:
            OAuth token response.
        """
        code = payload.get("code")
        if code is None or not code.strip():
            return _json_error("invalid_grant", "Authorization code is invalid.")
        code_record = await self._store.consume_authorization_code(_hash_secret(code))
        if code_record is None:
            return _json_error("invalid_grant", "Authorization code is invalid.")
        if code_record.expires_at <= self._time_provider():
            return _json_error("invalid_grant", "Authorization code expired.")
        if payload.get("client_id") != code_record.client_id:
            return _json_error("invalid_grant", "client_id does not match authorization code.")
        if payload.get("redirect_uri") != code_record.redirect_uri:
            return _json_error("invalid_grant", "redirect_uri does not match authorization code.")
        if not _verify_pkce(
            verifier=payload.get("code_verifier", ""),
            challenge=code_record.code_challenge,
            method=code_record.code_challenge_method,
        ):
            return _json_error("invalid_grant", "PKCE verification failed.")
        return await self._issue_token_pair(
            tenant_id=code_record.tenant_id,
            subject=code_record.subject,
            client_id=code_record.client_id,
            scopes=code_record.scopes,
            credential_id=code_record.credential_id,
        )

    async def _refresh_token(self, payload: Mapping[str, str]) -> JSONResponse:
        """Exchange one MCP refresh token for a new token pair.

        Args:
            payload: Parsed OAuth token request form fields.

        Returns:
            OAuth token response.
        """
        raw_refresh_token = payload.get("refresh_token")
        if raw_refresh_token is None or not raw_refresh_token.strip():
            return _json_error("invalid_grant", "Refresh token is invalid.")
        token_record = await self._store.get_refresh_token(_hash_secret(raw_refresh_token))
        if token_record is None or token_record.revoked_at is not None:
            return _json_error("invalid_grant", "Refresh token is invalid.")
        if token_record.expires_at <= self._time_provider():
            return _json_error("invalid_grant", "Refresh token expired.")
        if payload.get("client_id") != token_record.client_id:
            return _json_error("invalid_grant", "client_id does not match refresh token.")
        await self._store.revoke_refresh_token(
            token_record.token_hash,
            revoked_at=self._time_provider(),
        )
        return await self._issue_token_pair(
            tenant_id=token_record.tenant_id,
            subject=token_record.subject,
            client_id=token_record.client_id,
            scopes=token_record.scopes,
            credential_id=token_record.credential_id,
        )

    async def _issue_token_pair(
        self,
        *,
        tenant_id: str,
        subject: str,
        client_id: str,
        scopes: tuple[str, ...],
        credential_id: str,
    ) -> JSONResponse:
        """Issue and persist one MCP access/refresh token pair."""
        now = self._time_provider()
        raw_access_token = _new_secret_token("mcp_at")
        raw_refresh_token = _new_secret_token("mcp_rt")
        access_record = HostedOAuthAccessTokenMetadata.model_validate(
            {
                "token_id": _new_secret_token("tok"),
                "token_hash": _hash_secret(raw_access_token),
                "tenant_id": tenant_id,
                "subject": subject,
                "client_id": client_id,
                "scopes": scopes,
                "credential_id": credential_id,
                "expires_at": now + self._settings.access_token_seconds,
            }
        )
        refresh_record = HostedOAuthRefreshToken.model_validate(
            {
                "token_hash": _hash_secret(raw_refresh_token),
                "tenant_id": tenant_id,
                "subject": subject,
                "client_id": client_id,
                "scopes": scopes,
                "credential_id": credential_id,
                "expires_at": now + self._settings.refresh_token_seconds,
            }
        )
        await self._store.save_access_token(access_record)
        await self._store.save_refresh_token(refresh_record)
        return JSONResponse(
            {
                "access_token": raw_access_token,
                "token_type": "Bearer",
                "expires_in": self._settings.access_token_seconds,
                "refresh_token": raw_refresh_token,
                "scope": " ".join(scopes),
            }
        )


def _verify_pkce(*, verifier: str, challenge: str, method: str) -> bool:
    """Return whether a PKCE verifier matches the stored challenge.

    Args:
        verifier: Raw verifier from the token request.
        challenge: Stored challenge from the authorization request.
        method: Stored challenge method.

    Returns:
        `True` when the verifier matches.
    """
    if not verifier:
        return False
    if method == "plain":
        expected = verifier
    elif method == "S256":
        expected = _base64_url_sha256(verifier)
    else:
        return False
    return hmac.compare_digest(expected, challenge)


__all__ = [
    "FollowUpBossOAuthClient",
    "FollowUpBossOAuthIdentity",
    "FollowUpBossOAuthTokenPayload",
    "HostedOAuthAccessTokenMetadata",
    "HostedOAuthApplication",
    "HostedOAuthAuthorizationCode",
    "HostedOAuthDynamicClient",
    "HostedOAuthPendingAuthorization",
    "HostedOAuthRefreshToken",
    "HostedOAuthSettings",
    "HostedOAuthStore",
    "HostedOAuthTenantProvisioner",
    "ProvisionedHostedTenant",
]
