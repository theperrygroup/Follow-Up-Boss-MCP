"""Reference hosted deployment backends and entrypoint."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import time
import uuid
from collections.abc import Awaitable, Callable, Mapping, Sequence
from contextlib import AbstractAsyncContextManager
from typing import Annotated, Literal, Protocol, Self, cast

import boto3.session  # type: ignore[import-untyped]
import psycopg
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool
from pydantic import (
    AnyHttpUrl,
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    ValidationInfo,
    field_validator,
    model_validator,
)
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict
from redis.asyncio import from_url as redis_from_url

from followupboss_mcp.auth import AuthMode
from followupboss_mcp.config import (
    FollowUpBossServerSettings,
    FollowUpBossTenantRuntimeDefaults,
    _settings_env_aliases,
)
from followupboss_mcp.errors import (
    TenantSecretStoreUnavailableError,
    TenantStoreUnavailableError,
)
from followupboss_mcp.hosted_auth import (
    HostedAuthSettings,
    HostedIdentityVerifier,
    HostedVerifiedIdentity,
)
from followupboss_mcp.hosted_oauth import (
    FollowUpBossOAuthClient,
    FollowUpBossOAuthIdentity,
    FollowUpBossOAuthTokenPayload,
    HostedOAuthAccessTokenMetadata,
    HostedOAuthApplication,
    HostedOAuthAuthorizationCode,
    HostedOAuthDynamicClient,
    HostedOAuthPendingAuthorization,
    HostedOAuthRefreshToken,
    HostedOAuthSettings,
    ProvisionedHostedTenant,
)
from followupboss_mcp.hosted_rate_limits import (
    HostedEndpointRateLimiter,
    HostedRateLimitBackend,
    HostedRateLimitDecision,
    HostedRateLimitKey,
    HostedRateLimitSettings,
)
from followupboss_mcp.mcp_server import create_server
from followupboss_mcp.observability import (
    capture_sentry_exception,
    configure_sentry,
    flush_sentry,
)
from followupboss_mcp.tenant_store import (
    TenantCredentialRecord,
    TenantCredentialStatus,
    TenantRecord,
    TenantStore,
)
from followupboss_mcp.url_validation import normalize_public_http_url, validated_public_http_url
from mcp.server.mcpserver import MCPServer

_DEFAULT_HOSTED_REQUIRED_SCOPE = "followupboss:mcp"
_DEFAULT_REDIS_KEY_PREFIX = "followupboss:hosted_rate_limit"
_LOGGER = logging.getLogger(__name__)

_HOSTED_ACCESS_TOKEN_QUERY = """
SELECT tenant_id, subject, client_id, scopes, expires_at, token_id, credential_id, resource
FROM hosted_access_tokens
WHERE token_hash = %s
  AND resource = %s
  AND revoked_at IS NULL
  AND (expires_at IS NULL OR expires_at > %s)
LIMIT 1
"""

_TENANT_QUERY = """
SELECT tenant_id, tenant_slug, display_name, credential_id, status
FROM tenants
WHERE tenant_id = %s
LIMIT 1
"""

_TENANT_CREDENTIAL_QUERY = """
SELECT credential_id, tenant_id, auth_mode, system_name, secret_ref, status
FROM tenant_credentials
WHERE credential_id = %s
LIMIT 1
"""

_HOSTED_OAUTH_CLIENT_UPSERT = """
INSERT INTO hosted_oauth_clients (
    client_id, client_name, redirect_uris, scope, token_endpoint_auth_method
)
VALUES (%s, %s, %s, %s, %s)
ON CONFLICT (client_id) DO UPDATE SET
    client_name = EXCLUDED.client_name,
    redirect_uris = EXCLUDED.redirect_uris,
    scope = EXCLUDED.scope,
    token_endpoint_auth_method = EXCLUDED.token_endpoint_auth_method
"""

_HOSTED_OAUTH_CLIENT_QUERY = """
SELECT client_id, client_name, redirect_uris, scope, token_endpoint_auth_method
FROM hosted_oauth_clients
WHERE client_id = %s
LIMIT 1
"""

_HOSTED_ACCESS_TOKEN_INSERT = """
INSERT INTO hosted_access_tokens (
    token_id,
    token_hash,
    tenant_id,
    subject,
    client_id,
    scopes,
    resource,
    credential_id,
    expires_at,
    revoked_at
)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NULL)
"""

_HOSTED_OAUTH_REFRESH_TOKEN_UPSERT = """
INSERT INTO hosted_oauth_refresh_tokens (
    token_hash,
    tenant_id,
    subject,
    client_id,
    scopes,
    resource,
    credential_id,
    expires_at,
    revoked_at
)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NULL)
ON CONFLICT (token_hash) DO UPDATE SET
    tenant_id = EXCLUDED.tenant_id,
    subject = EXCLUDED.subject,
    client_id = EXCLUDED.client_id,
    scopes = EXCLUDED.scopes,
    resource = EXCLUDED.resource,
    credential_id = EXCLUDED.credential_id,
    expires_at = EXCLUDED.expires_at,
    revoked_at = NULL
"""

_HOSTED_OAUTH_REFRESH_TOKEN_QUERY = """
SELECT
    token_hash,
    tenant_id,
    subject,
    client_id,
    scopes,
    resource,
    credential_id,
    expires_at,
    revoked_at
FROM hosted_oauth_refresh_tokens
WHERE token_hash = %s
LIMIT 1
"""

_HOSTED_OAUTH_REFRESH_TOKEN_REVOKE = """
UPDATE hosted_oauth_refresh_tokens
SET revoked_at = %s
WHERE token_hash = %s
"""

_TENANT_UPSERT = """
INSERT INTO tenants (tenant_id, tenant_slug, display_name, credential_id, status)
VALUES (%s, %s, %s, %s, 'active')
ON CONFLICT (tenant_id) DO UPDATE SET
    tenant_slug = EXCLUDED.tenant_slug,
    display_name = EXCLUDED.display_name,
    credential_id = EXCLUDED.credential_id,
    status = 'active'
"""

_TENANT_CREDENTIAL_UPSERT = """
INSERT INTO tenant_credentials (
    credential_id, tenant_id, auth_mode, system_name, secret_ref, status
)
VALUES (%s, %s, 'oauth', %s, %s, 'active')
ON CONFLICT (credential_id) DO UPDATE SET
    tenant_id = EXCLUDED.tenant_id,
    auth_mode = 'oauth',
    system_name = EXCLUDED.system_name,
    secret_ref = EXCLUDED.secret_ref,
    status = 'active'
"""

_REDIS_GET_DELETE_SCRIPT = """
local key = KEYS[1]
local value = redis.call("GET", key)
if value then
  redis.call("DEL", key)
end
return value
"""

_REDIS_CONSUME_SCRIPT = """
local key = KEYS[1]
local now_ms = tonumber(ARGV[1])
local window_ms = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])
local member = ARGV[4]
local window_start = now_ms - window_ms

redis.call("ZREMRANGEBYSCORE", key, 0, window_start)

local current = redis.call("ZCARD", key)
if current >= limit then
  local oldest = redis.call("ZRANGE", key, 0, 0, "WITHSCORES")
  local retry_after_ms = 0
  if #oldest >= 2 then
    retry_after_ms = math.max((tonumber(oldest[2]) + window_ms) - now_ms, 0)
  end
  redis.call("PEXPIRE", key, window_ms)
  return {0, 0, retry_after_ms}
end

redis.call("ZADD", key, now_ms, member)
redis.call("PEXPIRE", key, window_ms)
return {1, math.max(limit - current - 1, 0), -1}
"""


def _default_fub_oauth_authorize_url() -> AnyHttpUrl:
    """Return the validated default Follow Up Boss OAuth authorize URL."""
    return validated_public_http_url(
        "https://app.followupboss.com/oauth/authorize",
        field_name="fub_oauth_authorize_url",
    )


def _default_fub_oauth_token_url() -> AnyHttpUrl:
    """Return the validated default Follow Up Boss OAuth token URL."""
    return validated_public_http_url(
        "https://app.followupboss.com/oauth/token",
        field_name="fub_oauth_token_url",
    )


def _normalize_required_string(value: str, *, field_name: str) -> str:
    """Normalize one required string field.

    Args:
        value: The raw string value supplied to the model.
        field_name: The field currently being validated.

    Returns:
        The trimmed string value.

    Raises:
        ValueError: If the string is empty after trimming whitespace.
    """
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be empty.")
    return normalized


def _normalize_optional_string(value: object) -> object:
    """Normalize one optional string field.

    Args:
        value: The raw field value supplied to the model.

    Returns:
        The trimmed string when a non-empty string is provided, `None` when the
        string is blank, or the original non-string value for downstream
        validation.
    """
    if not isinstance(value, str):
        return value
    normalized = value.strip()
    return normalized or None


def _normalize_scopes(value: object) -> object:
    """Normalize one required-scope field into a unique tuple.

    Args:
        value: The raw scope value supplied to the model.

    Returns:
        A normalized tuple of required scopes, or the original unsupported
        value for downstream validation.
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


def _secret_value(value: SecretStr | str) -> str:
    """Return the raw value from a plain string or `SecretStr`.

    Args:
        value: The possibly wrapped secret value.

    Returns:
        The unwrapped string value.
    """
    if isinstance(value, SecretStr):
        return value.get_secret_value()
    return value


def _coerce_redis_integer(value: object) -> int:
    """Coerce one Redis Lua-script field into an integer.

    Args:
        value: The raw Redis Lua-script field.

    Returns:
        The coerced integer value.

    Raises:
        TypeError: If the Redis response field is not integer-like.
    """
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, str | bytes | bytearray):
        return int(value)
    raise TypeError("Redis rate-limit script returned a non-integer field.")


def _normalize_secret_prefix(value: str) -> str:
    """Normalize the configured tenant secret prefix.

    Args:
        value: The raw configured secret prefix.

    Returns:
        The normalized secret prefix with a trailing slash.
    """
    normalized = _normalize_required_string(value, field_name="tenant_secret_prefix")
    return normalized.rstrip("/") + "/"


def _secret_ref_matches_prefix(secret_ref: str, secret_prefix: str) -> bool:
    """Return whether one secret reference belongs to the configured namespace.

    Args:
        secret_ref: The concrete secret reference from the credential row.
        secret_prefix: The configured logical secret prefix.

    Returns:
        `True` when the secret reference matches the configured namespace,
        otherwise `False`.
    """
    normalized_secret_ref = _normalize_required_string(secret_ref, field_name="secret_ref")
    if normalized_secret_ref.startswith(secret_prefix):
        return True
    return f":secret:{secret_prefix}" in normalized_secret_ref


def hash_hosted_bearer_token(token: str) -> str:
    """Hash one raw hosted bearer token for storage and lookup.

    Args:
        token: The raw bearer token value.

    Returns:
        The canonical `sha256:`-prefixed token hash.
    """
    normalized_token = _normalize_required_string(token, field_name="token")
    return "sha256:" + hashlib.sha256(normalized_token.encode("utf-8")).hexdigest()


class FollowUpBossHostedDeploymentSettings(BaseSettings):
    """Environment-backed settings for the reference hosted deployment."""

    model_config = SettingsConfigDict(
        env_prefix="FOLLOWUPBOSS_",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )

    issuer_url: AnyHttpUrl = Field(
        validation_alias=_settings_env_aliases("FOLLOWUPBOSS_HOSTED_ISSUER_URL")
    )
    resource_server_url: AnyHttpUrl = Field(
        validation_alias=_settings_env_aliases("FOLLOWUPBOSS_HOSTED_RESOURCE_SERVER_URL")
    )
    deployment_environment: Literal["production"] = Field(
        default="production",
        validation_alias=_settings_env_aliases("FOLLOWUPBOSS_DEPLOYMENT_ENVIRONMENT"),
    )
    required_scopes: Annotated[tuple[str, ...], NoDecode] = Field(
        default=(_DEFAULT_HOSTED_REQUIRED_SCOPE,),
        validation_alias=_settings_env_aliases("FOLLOWUPBOSS_HOSTED_REQUIRED_SCOPES"),
    )
    tenant_database_url: SecretStr = Field(
        validation_alias=_settings_env_aliases("FOLLOWUPBOSS_TENANT_DATABASE_URL")
    )
    tenant_secret_prefix: str = Field(
        validation_alias=_settings_env_aliases("FOLLOWUPBOSS_TENANT_SECRET_PREFIX")
    )
    tenant_secret_region: str = Field(
        validation_alias=_settings_env_aliases("FOLLOWUPBOSS_TENANT_SECRET_REGION")
    )
    redis_url: SecretStr = Field(validation_alias=_settings_env_aliases("FOLLOWUPBOSS_REDIS_URL"))
    rate_limit_requests_per_window: int = Field(
        default=300,
        validation_alias=_settings_env_aliases("FOLLOWUPBOSS_RATE_LIMIT_REQUESTS_PER_WINDOW"),
    )
    rate_limit_window_seconds: float = Field(
        default=60.0,
        validation_alias=_settings_env_aliases("FOLLOWUPBOSS_RATE_LIMIT_WINDOW_SECONDS"),
    )
    rate_limit_include_client_ip: bool = Field(
        default=False,
        validation_alias=_settings_env_aliases("FOLLOWUPBOSS_RATE_LIMIT_INCLUDE_CLIENT_IP"),
    )
    oauth_enabled: bool = Field(
        default=False,
        validation_alias=_settings_env_aliases("FOLLOWUPBOSS_HOSTED_OAUTH_ENABLED"),
    )
    fub_oauth_client_id: str | None = Field(
        default=None,
        validation_alias=_settings_env_aliases("FOLLOWUPBOSS_FUB_OAUTH_CLIENT_ID"),
    )
    fub_oauth_client_secret: SecretStr | None = Field(
        default=None,
        validation_alias=_settings_env_aliases("FOLLOWUPBOSS_FUB_OAUTH_CLIENT_SECRET"),
    )
    fub_oauth_authorize_url: AnyHttpUrl = Field(
        default_factory=_default_fub_oauth_authorize_url,
        validation_alias=_settings_env_aliases("FOLLOWUPBOSS_FUB_OAUTH_AUTHORIZE_URL"),
    )
    fub_oauth_token_url: AnyHttpUrl = Field(
        default_factory=_default_fub_oauth_token_url,
        validation_alias=_settings_env_aliases("FOLLOWUPBOSS_FUB_OAUTH_TOKEN_URL"),
    )
    fub_oauth_callback_url: AnyHttpUrl | None = Field(
        default=None,
        validation_alias=_settings_env_aliases("FOLLOWUPBOSS_FUB_OAUTH_CALLBACK_URL"),
    )
    fub_oauth_system_name: str | None = Field(
        default=None,
        validation_alias=_settings_env_aliases("FOLLOWUPBOSS_FUB_OAUTH_SYSTEM_NAME"),
    )
    fub_oauth_system_key: SecretStr | None = Field(
        default=None,
        validation_alias=_settings_env_aliases("FOLLOWUPBOSS_FUB_OAUTH_SYSTEM_KEY"),
    )
    hosted_oauth_access_token_seconds: int = Field(
        default=3600,
        validation_alias=_settings_env_aliases("FOLLOWUPBOSS_HOSTED_OAUTH_ACCESS_TOKEN_SECONDS"),
    )
    hosted_oauth_refresh_token_seconds: int = Field(
        default=60 * 60 * 24 * 30,
        validation_alias=_settings_env_aliases("FOLLOWUPBOSS_HOSTED_OAUTH_REFRESH_TOKEN_SECONDS"),
    )

    @field_validator(
        "issuer_url",
        "resource_server_url",
        "fub_oauth_authorize_url",
        "fub_oauth_token_url",
        "fub_oauth_callback_url",
        mode="before",
    )
    @classmethod
    def _validate_public_urls(cls, value: object, info: ValidationInfo) -> object:
        """Normalize hosted deployment URL settings."""
        if value is None:
            return None
        return normalize_public_http_url(value, field_name=info.field_name or "url")

    @field_validator("required_scopes", mode="before")
    @classmethod
    def _validate_required_scopes(cls, value: object) -> object:
        """Normalize required scopes to a unique tuple.

        Args:
            value: The raw required-scope value.

        Returns:
            The normalized required-scope tuple.
        """
        return _normalize_scopes(value)

    @field_validator("tenant_secret_prefix")
    @classmethod
    def _validate_secret_prefix(cls, value: str) -> str:
        """Normalize the tenant secret prefix.

        Args:
            value: The raw configured prefix.

        Returns:
            The normalized prefix with a trailing slash.
        """
        return _normalize_secret_prefix(value)

    @field_validator("tenant_secret_region")
    @classmethod
    def _validate_secret_region(cls, value: str) -> str:
        """Require a non-empty tenant secret region.

        Args:
            value: The raw configured AWS region.

        Returns:
            The normalized region string.
        """
        return _normalize_required_string(value, field_name="tenant_secret_region")

    def hosted_auth_settings(self) -> HostedAuthSettings:
        """Project the deployment settings into hosted-auth settings.

        Returns:
            Hosted auth settings suitable for the MCPServer streamable HTTP
            transport.
        """
        return HostedAuthSettings.model_validate(
            {
                "issuer_url": self.issuer_url,
                "resource_server_url": self.resource_server_url,
                "required_scopes": self.required_scopes,
            }
        )

    def hosted_rate_limit_settings(self) -> HostedRateLimitSettings:
        """Project the deployment settings into hosted rate-limit settings.

        Returns:
            Hosted endpoint rate-limit settings for the shared deployment.
        """
        return HostedRateLimitSettings.model_validate(
            {
                "requests_per_window": self.rate_limit_requests_per_window,
                "window_seconds": self.rate_limit_window_seconds,
                "include_client_ip": self.rate_limit_include_client_ip,
                "backend_failure_mode": "closed",
            }
        )

    def hosted_oauth_settings(self) -> HostedOAuthSettings | None:
        """Project deployment settings into hosted OAuth settings.

        Returns:
            Hosted OAuth settings when OAuth is enabled, otherwise `None`.

        Raises:
            ValueError: If OAuth is enabled without required FUB app settings.
        """
        if not self.oauth_enabled:
            return None
        if (
            self.fub_oauth_client_id is None
            or self.fub_oauth_client_secret is None
            or self.fub_oauth_callback_url is None
        ):
            raise ValueError(
                "FUB OAuth client id, client secret, and callback URL are required "
                "when hosted OAuth is enabled."
            )
        return HostedOAuthSettings.model_validate(
            {
                "issuer_url": self.issuer_url,
                "resource_server_url": self.resource_server_url,
                "required_scopes": self.required_scopes,
                "fub_client_id": self.fub_oauth_client_id,
                "fub_client_secret": self.fub_oauth_client_secret,
                "fub_authorize_url": self.fub_oauth_authorize_url,
                "fub_token_url": self.fub_oauth_token_url,
                "fub_callback_url": self.fub_oauth_callback_url,
                "token_secret_prefix": self.tenant_secret_prefix,
                "system_name": self.fub_oauth_system_name,
                "system_key": self.fub_oauth_system_key,
                "access_token_seconds": self.hosted_oauth_access_token_seconds,
                "refresh_token_seconds": self.hosted_oauth_refresh_token_seconds,
            }
        )


class ReferenceHostedSecretPayload(BaseModel):
    """Validated raw Follow Up Boss secret payload from AWS Secrets Manager."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    api_key: SecretStr | None = None
    access_token: SecretStr | None = None
    refresh_token: SecretStr | None = None
    access_token_expires_at: int | None = None
    system_key: SecretStr | None = None

    @model_validator(mode="after")
    def _validate_auth_secret_count(self) -> Self:
        """Require exactly one credential secret in the secret payload.

        Returns:
            The validated secret payload.

        Raises:
            ValueError: If neither or both primary auth secrets are present.
        """
        has_api_key = self.api_key is not None
        has_access_token = self.access_token is not None
        if has_api_key == has_access_token:
            raise ValueError("Exactly one of api_key or access_token must be present.")
        return self

    def needs_oauth_refresh(
        self,
        *,
        now: int,
        refresh_buffer_seconds: int = 300,
    ) -> bool:
        """Return whether an OAuth access token should be refreshed.

        Args:
            now: Current Unix timestamp.
            refresh_buffer_seconds: Refresh when expiry is within this window.

        Returns:
            `True` when a refresh token exists and the access token is near
            expiry or has no expiry metadata.
        """
        if self.access_token is None or self.refresh_token is None:
            return False
        if self.access_token_expires_at is None:
            return True
        return self.access_token_expires_at <= now + refresh_buffer_seconds


class _TenantCredentialMetadataRow(BaseModel):
    """Validated credential metadata loaded from PostgreSQL."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    credential_id: str
    tenant_id: str
    auth_mode: AuthMode
    system_name: str | None = None
    secret_ref: str
    status: TenantCredentialStatus

    @field_validator("credential_id", "tenant_id", "secret_ref")
    @classmethod
    def _validate_required_identifiers(cls, value: str, info: ValidationInfo) -> str:
        """Require non-empty credential metadata fields.

        Args:
            value: The raw field value.
            info: Validation context for the current field.

        Returns:
            The normalized field value.
        """
        return _normalize_required_string(value, field_name=info.field_name or "field")

    @field_validator("system_name", mode="before")
    @classmethod
    def _validate_optional_system_name(cls, value: object) -> object:
        """Normalize optional registered-system names.

        Args:
            value: The raw system-name value.

        Returns:
            The normalized system name or `None`.
        """
        return _normalize_optional_string(value)


class HostedTenantSecretStore(Protocol):
    """Protocol for fetching raw tenant secret payloads."""

    async def get_secret_payload(self, secret_ref: str) -> ReferenceHostedSecretPayload:
        """Resolve one raw tenant secret payload by reference.

        Args:
            secret_ref: The concrete secret-manager reference to resolve.

        Returns:
            The validated secret payload.
        """


class SecretsManagerClientProtocol(Protocol):
    """Protocol for the subset of Secrets Manager used by this module."""

    def get_secret_value(self, **kwargs: object) -> object:
        """Return one secret payload by identifier.

        Args:
            **kwargs: Keyword arguments forwarded to the Secrets Manager client.

        Returns:
            The raw Secrets Manager response payload.
        """


class SecretsManagerWriterClientProtocol(SecretsManagerClientProtocol, Protocol):
    """Protocol for the Secrets Manager writes used by OAuth provisioning."""

    def put_secret_value(self, **kwargs: object) -> object:
        """Store a new version for an existing secret.

        Args:
            **kwargs: Keyword arguments forwarded to Secrets Manager.

        Returns:
            Raw Secrets Manager response payload.
        """

    def create_secret(self, **kwargs: object) -> object:
        """Create a secret when it does not already exist.

        Args:
            **kwargs: Keyword arguments forwarded to Secrets Manager.

        Returns:
            Raw Secrets Manager response payload.
        """


class RedisClientProtocol(Protocol):
    """Protocol for the subset of Redis used by this module."""

    def get(self, name: str) -> Awaitable[object]:
        """Return one Redis value by key.

        Args:
            name: Redis key.

        Returns:
            Awaitable Redis value.
        """

    def set(self, name: str, value: str, *, ex: int) -> Awaitable[object]:
        """Set one Redis value with an expiry.

        Args:
            name: Redis key.
            value: Serialized value.
            ex: Expiry in seconds.

        Returns:
            Awaitable Redis result.
        """

    def delete(self, name: str) -> Awaitable[object]:
        """Delete one Redis key.

        Args:
            name: Redis key.

        Returns:
            Awaitable Redis result.
        """

    def eval(self, script: str, numkeys: int, *args: str) -> Awaitable[object]:
        """Execute one Lua script against Redis.

        Args:
            script: The Lua script to execute.
            numkeys: Number of Redis keys supplied in `args`.
            *args: The Redis keys and script arguments.

        Returns:
            An awaitable Redis response payload.
        """

    def aclose(self) -> Awaitable[None]:
        """Close the Redis client."""


class AwsSecretsManagerTenantSecretStore:
    """AWS Secrets Manager-backed tenant secret resolver."""

    def __init__(
        self,
        *,
        region_name: str,
        secret_prefix: str,
        secrets_client: SecretsManagerClientProtocol | None = None,
    ) -> None:
        """Initialize the AWS Secrets Manager-backed secret store.

        Args:
            region_name: AWS region used for tenant secrets.
            secret_prefix: Logical namespace that every tenant secret reference
                must match.
            secrets_client: Optional prebuilt Secrets Manager client used mainly
                by focused tests.
        """
        self._region_name = _normalize_required_string(region_name, field_name="region_name")
        self._secret_prefix = _normalize_secret_prefix(secret_prefix)
        self._secrets_client = secrets_client or cast(
            SecretsManagerClientProtocol,
            boto3.session.Session().client(
                "secretsmanager",
                region_name=self._region_name,
            ),
        )

    async def get_secret_payload(self, secret_ref: str) -> ReferenceHostedSecretPayload:
        """Resolve and validate one tenant secret payload.

        Args:
            secret_ref: The concrete secret reference from the credential row.

        Returns:
            The validated secret payload.

        Raises:
            TenantSecretStoreUnavailableError: If the secret cannot be fetched,
                does not match the configured prefix, or contains invalid JSON.
        """
        normalized_secret_ref = _normalize_required_string(secret_ref, field_name="secret_ref")
        if not _secret_ref_matches_prefix(normalized_secret_ref, self._secret_prefix):
            raise TenantSecretStoreUnavailableError("Tenant secret store is unavailable.")

        try:
            raw_response = await asyncio.to_thread(
                self._secrets_client.get_secret_value,
                SecretId=normalized_secret_ref,
            )
        except Exception as exc:
            raise TenantSecretStoreUnavailableError("Tenant secret store is unavailable.") from exc

        response = cast(Mapping[str, object], raw_response)
        secret_string = response.get("SecretString")
        secret_binary = response.get("SecretBinary")
        if isinstance(secret_string, str):
            payload_json = secret_string
        elif isinstance(secret_binary, bytes | bytearray):
            payload_json = bytes(secret_binary).decode("utf-8")
        elif isinstance(secret_binary, memoryview):
            payload_json = secret_binary.tobytes().decode("utf-8")
        else:
            raise TenantSecretStoreUnavailableError("Tenant secret store is unavailable.")

        try:
            return ReferenceHostedSecretPayload.model_validate_json(payload_json)
        except Exception as exc:
            raise TenantSecretStoreUnavailableError("Tenant secret store is unavailable.") from exc


class AwsSecretsManagerHostedOAuthSecretWriter:
    """AWS Secrets Manager writer for OAuth-backed tenant secrets."""

    def __init__(
        self,
        *,
        region_name: str,
        secret_prefix: str,
        secrets_client: SecretsManagerWriterClientProtocol | None = None,
    ) -> None:
        """Initialize the OAuth secret writer.

        Args:
            region_name: AWS region used for tenant secrets.
            secret_prefix: Logical namespace for tenant secret references.
            secrets_client: Optional Secrets Manager client used by tests.
        """
        self._region_name = _normalize_required_string(region_name, field_name="region_name")
        self._secret_prefix = _normalize_secret_prefix(secret_prefix)
        self._secrets_client = secrets_client or cast(
            SecretsManagerWriterClientProtocol,
            boto3.session.Session().client(
                "secretsmanager",
                region_name=self._region_name,
            ),
        )

    def secret_ref_for_credential(self, credential_id: str) -> str:
        """Return the managed secret reference for one credential id.

        Args:
            credential_id: Stable tenant credential id.

        Returns:
            Secrets Manager name below the configured prefix.
        """
        return self._secret_prefix + _normalize_required_string(
            credential_id,
            field_name="credential_id",
        )

    async def put_oauth_secret(
        self,
        *,
        secret_ref: str,
        payload: ReferenceHostedSecretPayload,
    ) -> None:
        """Create or update one OAuth tenant secret.

        Args:
            secret_ref: Secrets Manager name or ARN.
            payload: Validated secret payload.

        Raises:
            TenantSecretStoreUnavailableError: If Secrets Manager cannot persist
                the payload.
        """
        normalized_secret_ref = _normalize_required_string(secret_ref, field_name="secret_ref")
        if not _secret_ref_matches_prefix(normalized_secret_ref, self._secret_prefix):
            raise TenantSecretStoreUnavailableError("Tenant secret store is unavailable.")
        payload_data: dict[str, object] = {}
        if payload.api_key is not None:
            payload_data["api_key"] = payload.api_key.get_secret_value()
        if payload.access_token is not None:
            payload_data["access_token"] = payload.access_token.get_secret_value()
        if payload.refresh_token is not None:
            payload_data["refresh_token"] = payload.refresh_token.get_secret_value()
        if payload.access_token_expires_at is not None:
            payload_data["access_token_expires_at"] = payload.access_token_expires_at
        if payload.system_key is not None:
            payload_data["system_key"] = payload.system_key.get_secret_value()
        payload_json = json.dumps(payload_data, sort_keys=True)
        try:
            await asyncio.to_thread(
                self._secrets_client.put_secret_value,
                SecretId=normalized_secret_ref,
                SecretString=payload_json,
            )
        except Exception:
            try:
                await asyncio.to_thread(
                    self._secrets_client.create_secret,
                    Name=normalized_secret_ref,
                    SecretString=payload_json,
                )
            except Exception as exc:
                raise TenantSecretStoreUnavailableError(
                    "Tenant secret store is unavailable."
                ) from exc


class FollowUpBossTenantOAuthRefresher:
    """Refresh near-expiry FUB OAuth tenant secrets during tenant resolution."""

    def __init__(
        self,
        *,
        fub_client: FollowUpBossOAuthClient,
        secret_writer: AwsSecretsManagerHostedOAuthSecretWriter,
        time_provider: Callable[[], int] | None = None,
        refresh_buffer_seconds: int = 300,
    ) -> None:
        """Initialize the tenant OAuth refresher.

        Args:
            fub_client: Follow Up Boss OAuth client used for refresh calls.
            secret_writer: Secret writer used to persist refreshed tokens.
            time_provider: Optional Unix timestamp provider.
            refresh_buffer_seconds: Refresh when expiry is inside this window.
        """
        self._fub_client = fub_client
        self._secret_writer = secret_writer
        self._time_provider = time_provider or (lambda: int(time.time()))
        self._refresh_buffer_seconds = refresh_buffer_seconds

    async def refresh_if_needed(
        self,
        *,
        secret_ref: str,
        payload: ReferenceHostedSecretPayload,
    ) -> ReferenceHostedSecretPayload:
        """Refresh a tenant OAuth secret when it is near expiry.

        Args:
            secret_ref: Secret reference backing the credential row.
            payload: Current tenant secret payload.

        Returns:
            Current payload when no refresh is required, otherwise refreshed
            payload after persistence.
        """
        if not payload.needs_oauth_refresh(
            now=self._time_provider(),
            refresh_buffer_seconds=self._refresh_buffer_seconds,
        ):
            return payload
        if payload.refresh_token is None:
            return payload
        refreshed = await self._fub_client.refresh_token(
            refresh_token=payload.refresh_token.get_secret_value()
        )
        expires_at = (
            None
            if refreshed.expires_in is None
            else self._time_provider() + int(refreshed.expires_in)
        )
        refreshed_payload = ReferenceHostedSecretPayload.model_validate(
            {
                "access_token": refreshed.access_token,
                "refresh_token": refreshed.refresh_token or payload.refresh_token,
                "access_token_expires_at": expires_at,
                "system_key": payload.system_key,
            }
        )
        await self._secret_writer.put_oauth_secret(
            secret_ref=secret_ref,
            payload=refreshed_payload,
        )
        return refreshed_payload


class PostgresAwsHostedOAuthTenantProvisioner:
    """Provision hosted tenant metadata from a successful FUB OAuth login."""

    def __init__(
        self,
        database_url: SecretStr | str | None = None,
        *,
        pool: ReferenceHostedPostgresPool | None = None,
        secret_writer: AwsSecretsManagerHostedOAuthSecretWriter,
        system_name: str | None = None,
        system_key: SecretStr | None = None,
        time_provider: Callable[[], int] | None = None,
    ) -> None:
        """Initialize the tenant provisioner.

        Args:
            database_url: PostgreSQL connection string when no pool is injected.
            pool: Optional shared PostgreSQL pool.
            secret_writer: Secrets Manager writer for raw FUB OAuth tokens.
            system_name: Optional Follow Up Boss registered-system name.
            system_key: Optional Follow Up Boss registered-system key.
            time_provider: Optional Unix timestamp provider.

        Raises:
            ValueError: If no database source is configured.
        """
        if database_url is None and pool is None:
            raise ValueError("database_url is required when pool is not provided.")
        self._pool = pool or ReferenceHostedPostgresPool(cast(SecretStr | str, database_url))
        self._owns_pool = pool is None
        self._secret_writer = secret_writer
        self._system_name = cast(str | None, _normalize_optional_string(system_name))
        self._system_key = system_key
        self._time_provider = time_provider or (lambda: int(time.time()))

    async def provision_tenant(
        self,
        *,
        identity: FollowUpBossOAuthIdentity,
        token_payload: FollowUpBossOAuthTokenPayload,
    ) -> ProvisionedHostedTenant:
        """Provision tenant metadata and OAuth secret material.

        Args:
            identity: Follow Up Boss account/user identity.
            token_payload: FUB OAuth token payload.

        Returns:
            Provisioned hosted tenant identifiers.
        """
        tenant_id = identity.tenant_id
        credential_id = identity.credential_id
        secret_ref = self._secret_writer.secret_ref_for_credential(credential_id)
        expires_at = (
            None
            if token_payload.expires_in is None
            else self._time_provider() + int(token_payload.expires_in)
        )
        secret_payload = ReferenceHostedSecretPayload.model_validate(
            {
                "access_token": token_payload.access_token,
                "refresh_token": token_payload.refresh_token,
                "access_token_expires_at": expires_at,
                "system_key": self._system_key,
            }
        )
        await self._secret_writer.put_oauth_secret(
            secret_ref=secret_ref,
            payload=secret_payload,
        )
        await _execute_postgres(
            self._pool,
            _TENANT_UPSERT,
            (
                tenant_id,
                tenant_id,
                identity.account_name,
                credential_id,
            ),
        )
        await _execute_postgres(
            self._pool,
            _TENANT_CREDENTIAL_UPSERT,
            (
                credential_id,
                tenant_id,
                self._system_name,
                secret_ref,
            ),
        )
        return ProvisionedHostedTenant.model_validate(
            {
                "tenant_id": tenant_id,
                "credential_id": credential_id,
                "subject": identity.subject,
            }
        )

    async def aclose(self) -> None:
        """Close the owned PostgreSQL pool."""
        if self._owns_pool:
            await self._pool.aclose()


class ReferenceHostedPostgresPool:
    """Managed async PostgreSQL pool for hosted metadata lookups."""

    def __init__(
        self,
        database_url: SecretStr | str,
        *,
        pool: AsyncConnectionPool[psycopg.AsyncConnection[dict[str, object]]] | None = None,
    ) -> None:
        """Initialize the managed PostgreSQL pool.

        Args:
            database_url: PostgreSQL connection string used when no pool is
                injected.
            pool: Optional prebuilt async connection pool used mainly by focused
                tests or shared hosted-server wiring.
        """
        self._owns_pool = pool is None
        self._pool = pool or AsyncConnectionPool(
            conninfo=_secret_value(database_url),
            kwargs={"row_factory": dict_row},
            open=False,
        )

    async def open(self) -> None:
        """Open the pool for hosted metadata queries."""
        await self._pool.open()

    def connection(
        self,
    ) -> AbstractAsyncContextManager[psycopg.AsyncConnection[dict[str, object]]]:
        """Return one pooled async PostgreSQL connection context.

        Returns:
            An async context manager that yields one pooled PostgreSQL
            connection.
        """
        return self._pool.connection()

    async def aclose(self) -> None:
        """Close the owned pool when this wrapper created it."""
        if self._owns_pool:
            await self._pool.close()


async def _fetch_optional_postgres_row(
    pool: ReferenceHostedPostgresPool,
    query: str,
    params: tuple[object, ...],
) -> Mapping[str, object] | None:
    """Fetch one optional row through the shared PostgreSQL pool.

    Args:
        pool: Managed PostgreSQL pool used for the query.
        query: SQL query text to execute.
        params: Bound parameter tuple for the query.

    Returns:
        One mapping row when the query finds a match, otherwise `None`.
    """
    await pool.open()
    async with pool.connection() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(query, params)
            raw_row = await cursor.fetchone()

    if raw_row is None:
        return None
    return cast(Mapping[str, object], raw_row)


async def _execute_postgres(
    pool: ReferenceHostedPostgresPool,
    query: str,
    params: tuple[object, ...],
) -> None:
    """Execute one PostgreSQL statement through the shared pool.

    Args:
        pool: Managed PostgreSQL pool used for the statement.
        query: SQL statement text to execute.
        params: Bound parameter tuple.
    """
    await pool.open()
    async with pool.connection() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(query, params)


def _coerce_json_mapping(value: object) -> Mapping[str, object] | None:
    """Deserialize a Redis JSON payload into a mapping.

    Args:
        value: Raw Redis payload.

    Returns:
        Parsed mapping when available, otherwise `None`.
    """
    if value is None:
        return None
    if isinstance(value, bytes | bytearray):
        raw_text = bytes(value).decode("utf-8")
    else:
        raw_text = str(value)
    parsed = json.loads(raw_text)
    if not isinstance(parsed, Mapping):
        return None
    return cast(Mapping[str, object], parsed)


class PostgresRedisHostedOAuthStore:
    """Redis and PostgreSQL-backed storage for hosted OAuth state."""

    def __init__(
        self,
        database_url: SecretStr | str | None = None,
        *,
        redis_url: SecretStr | str | None = None,
        pool: ReferenceHostedPostgresPool | None = None,
        redis_client: RedisClientProtocol | None = None,
        key_prefix: str = "followupboss:hosted_oauth",
    ) -> None:
        """Initialize the hosted OAuth store.

        Args:
            database_url: PostgreSQL connection string when no pool is injected.
            redis_url: Redis connection string when no client is injected.
            pool: Optional shared PostgreSQL pool.
            redis_client: Optional shared Redis client.
            key_prefix: Redis key namespace for short-lived OAuth state.

        Raises:
            ValueError: If required backing clients are missing.
        """
        if database_url is None and pool is None:
            raise ValueError("database_url is required when pool is not provided.")
        if redis_url is None and redis_client is None:
            raise ValueError("redis_url is required when redis_client is not provided.")
        self._pool = pool or ReferenceHostedPostgresPool(cast(SecretStr | str, database_url))
        self._owns_pool = pool is None
        self._redis = redis_client or cast(
            RedisClientProtocol,
            redis_from_url(_secret_value(cast(SecretStr | str, redis_url))),
        )
        self._owns_redis = redis_client is None
        self._key_prefix = _normalize_required_string(key_prefix, field_name="key_prefix").rstrip(
            ":"
        )

    def _redis_key(self, *parts: str) -> str:
        """Build a Redis key for short-lived OAuth data.

        Args:
            *parts: Key parts below the store prefix.

        Returns:
            Redis key.
        """
        return ":".join([self._key_prefix, *parts])

    async def _consume_redis_json(self, key: str) -> Mapping[str, object] | None:
        """Atomically read and delete one serialized Redis JSON payload.

        Args:
            key: Redis key to consume.

        Returns:
            Parsed JSON mapping when a value existed, otherwise `None`.
        """
        raw_value = await self._redis.eval(_REDIS_GET_DELETE_SCRIPT, 1, key)
        return _coerce_json_mapping(raw_value)

    async def save_client(self, client: HostedOAuthDynamicClient) -> None:
        """Persist OAuth client metadata."""
        await _execute_postgres(
            self._pool,
            _HOSTED_OAUTH_CLIENT_UPSERT,
            (
                client.client_id,
                client.client_name,
                list(client.redirect_uris),
                list(client.scope),
                client.token_endpoint_auth_method,
            ),
        )

    async def get_client(self, client_id: str) -> HostedOAuthDynamicClient | None:
        """Return OAuth client metadata when known."""
        row = await _fetch_optional_postgres_row(
            self._pool,
            _HOSTED_OAUTH_CLIENT_QUERY,
            (_normalize_required_string(client_id, field_name="client_id"),),
        )
        if row is None:
            return None
        return HostedOAuthDynamicClient.model_validate(dict(row))

    async def save_pending_authorization(
        self,
        authorization: HostedOAuthPendingAuthorization,
    ) -> None:
        """Persist short-lived delegated authorization state."""
        ttl = max(authorization.expires_at - int(time.time()), 1)
        await self._redis.set(
            self._redis_key("state", authorization.fub_state),
            json.dumps(authorization.model_dump(mode="json"), sort_keys=True),
            ex=ttl,
        )

    async def consume_pending_authorization(
        self,
        fub_state: str,
    ) -> HostedOAuthPendingAuthorization | None:
        """Consume delegated authorization state once."""
        key = self._redis_key(
            "state",
            _normalize_required_string(fub_state, field_name="fub_state"),
        )
        payload = await self._consume_redis_json(key)
        if payload is None:
            return None
        return HostedOAuthPendingAuthorization.model_validate(payload)

    async def save_authorization_code(self, code: HostedOAuthAuthorizationCode) -> None:
        """Persist a one-time MCP authorization code."""
        ttl = max(code.expires_at - int(time.time()), 1)
        await self._redis.set(
            self._redis_key("code", code.code_hash),
            # Keep the Redis wire shape readable by the previous release during
            # ECS overlap. The new reader binds missing resource to the single
            # configured canonical MCP audience before issuing tokens.
            json.dumps(code.model_dump(mode="json", exclude={"resource"}), sort_keys=True),
            ex=ttl,
        )

    async def consume_authorization_code(
        self,
        code_hash: str,
    ) -> HostedOAuthAuthorizationCode | None:
        """Consume a one-time MCP authorization code."""
        key = self._redis_key("code", _normalize_required_string(code_hash, field_name="code_hash"))
        payload = await self._consume_redis_json(key)
        if payload is None:
            return None
        return HostedOAuthAuthorizationCode.model_validate(payload)

    async def save_access_token(self, token: HostedOAuthAccessTokenMetadata) -> None:
        """Persist MCP access-token metadata."""
        await _execute_postgres(
            self._pool,
            _HOSTED_ACCESS_TOKEN_INSERT,
            (
                token.token_id,
                token.token_hash,
                token.tenant_id,
                token.subject,
                token.client_id,
                list(token.scopes),
                token.resource,
                token.credential_id,
                token.expires_at,
            ),
        )

    async def save_refresh_token(self, token: HostedOAuthRefreshToken) -> None:
        """Persist MCP refresh-token metadata."""
        await _execute_postgres(
            self._pool,
            _HOSTED_OAUTH_REFRESH_TOKEN_UPSERT,
            (
                token.token_hash,
                token.tenant_id,
                token.subject,
                token.client_id,
                list(token.scopes),
                token.resource,
                token.credential_id,
                token.expires_at,
            ),
        )

    async def get_refresh_token(self, token_hash: str) -> HostedOAuthRefreshToken | None:
        """Return refresh-token metadata when active."""
        row = await _fetch_optional_postgres_row(
            self._pool,
            _HOSTED_OAUTH_REFRESH_TOKEN_QUERY,
            (_normalize_required_string(token_hash, field_name="token_hash"),),
        )
        if row is None:
            return None
        return HostedOAuthRefreshToken.model_validate(dict(row))

    async def revoke_refresh_token(self, token_hash: str, *, revoked_at: int) -> None:
        """Mark a refresh token as revoked."""
        await _execute_postgres(
            self._pool,
            _HOSTED_OAUTH_REFRESH_TOKEN_REVOKE,
            (revoked_at, _normalize_required_string(token_hash, field_name="token_hash")),
        )

    async def aclose(self) -> None:
        """Close owned Redis and PostgreSQL clients."""
        if self._owns_pool:
            await self._pool.aclose()
        if self._owns_redis:
            await self._redis.aclose()


class PostgresHostedTokenVerifier(HostedIdentityVerifier):
    """PostgreSQL-backed verifier for opaque hosted bearer tokens."""

    def __init__(
        self,
        database_url: SecretStr | str | None = None,
        *,
        resource_server_url: AnyHttpUrl | str,
        pool: ReferenceHostedPostgresPool | None = None,
        time_provider: Callable[[], int] | None = None,
    ) -> None:
        """Initialize the PostgreSQL-backed hosted token verifier.

        Args:
            database_url: PostgreSQL connection string for hosted-token metadata
                when no pool is injected.
            resource_server_url: Canonical MCP resource identifier accepted by
                this verifier.
            pool: Optional shared PostgreSQL pool used to reuse connections
                across hosted token and tenant lookups.
            time_provider: Optional Unix-timestamp provider used mainly by tests.

        Raises:
            ValueError: If neither `database_url` nor `pool` is provided.
        """
        if database_url is None and pool is None:
            raise ValueError("database_url is required when pool is not provided.")

        self._pool = pool or ReferenceHostedPostgresPool(cast(SecretStr | str, database_url))
        self._owns_pool = pool is None
        normalized_resource = normalize_public_http_url(
            resource_server_url,
            field_name="resource_server_url",
        )
        if not isinstance(normalized_resource, AnyHttpUrl):
            raise TypeError("resource_server_url must be a public HTTP URL.")
        self._resource_server_url = str(normalized_resource)
        self._time_provider = time_provider or (lambda: int(time.time()))

    async def verify_token(self, token: str) -> HostedVerifiedIdentity | None:
        """Resolve one opaque bearer token into hosted identity claims.

        Args:
            token: The raw bearer token supplied by the client.

        Returns:
            The verified hosted identity when the token exists, is not revoked,
            and is not expired, otherwise `None`.
        """
        raw_row = await _fetch_optional_postgres_row(
            self._pool,
            _HOSTED_ACCESS_TOKEN_QUERY,
            (
                hash_hosted_bearer_token(token),
                self._resource_server_url,
                self._time_provider(),
            ),
        )
        if raw_row is None:
            return None
        return HostedVerifiedIdentity.model_validate(dict(raw_row))

    async def aclose(self) -> None:
        """Close the owned PostgreSQL pool when this verifier created it."""
        if self._owns_pool:
            await self._pool.aclose()


class PostgresAwsTenantStore(TenantStore):
    """PostgreSQL metadata store plus AWS Secrets Manager credential resolver."""

    def __init__(
        self,
        database_url: SecretStr | str | None = None,
        *,
        secret_store: HostedTenantSecretStore,
        pool: ReferenceHostedPostgresPool | None = None,
        oauth_refresher: FollowUpBossTenantOAuthRefresher | None = None,
    ) -> None:
        """Initialize the PostgreSQL and AWS-backed tenant store.

        Args:
            database_url: PostgreSQL connection string for tenant metadata when
                no pool is injected.
            secret_store: Secret-store integration used to resolve raw Follow Up
                Boss credentials.
            pool: Optional shared PostgreSQL pool used to reuse connections
                across hosted token and tenant lookups.
            oauth_refresher: Optional refresher for OAuth-backed tenant secrets.

        Raises:
            ValueError: If neither `database_url` nor `pool` is provided.
        """
        if database_url is None and pool is None:
            raise ValueError("database_url is required when pool is not provided.")

        self._pool = pool or ReferenceHostedPostgresPool(cast(SecretStr | str, database_url))
        self._owns_pool = pool is None
        self._secret_store = secret_store
        self._oauth_refresher = oauth_refresher

    async def get_tenant(self, tenant_id: str) -> TenantRecord | None:
        """Look up one tenant metadata row by canonical identifier.

        Args:
            tenant_id: The stable hosted tenant identifier.

        Returns:
            The validated tenant record when one exists, otherwise `None`.

        Raises:
            TenantStoreUnavailableError: If PostgreSQL metadata cannot be queried
                safely.
        """
        try:
            raw_row = await _fetch_optional_postgres_row(self._pool, _TENANT_QUERY, (tenant_id,))
        except Exception as exc:
            raise TenantStoreUnavailableError("Tenant store is unavailable.") from exc

        if raw_row is None:
            return None
        return TenantRecord.model_validate(dict(raw_row))

    async def get_credential(self, credential_id: str) -> TenantCredentialRecord | None:
        """Look up one credential row and resolve its raw secret payload.

        Args:
            credential_id: The stable identifier for the tenant credential.

        Returns:
            The assembled tenant credential record when one exists, otherwise
            `None`.

        Raises:
            TenantStoreUnavailableError: If PostgreSQL metadata cannot be queried
                safely.
            TenantSecretStoreUnavailableError: If the secret store is
                unavailable or the secret payload is invalid.
        """
        try:
            raw_row = await _fetch_optional_postgres_row(
                self._pool,
                _TENANT_CREDENTIAL_QUERY,
                (credential_id,),
            )
        except Exception as exc:
            raise TenantStoreUnavailableError("Tenant store is unavailable.") from exc

        if raw_row is None:
            return None

        metadata = _TenantCredentialMetadataRow.model_validate(dict(raw_row))
        secret_payload = await self._secret_store.get_secret_payload(metadata.secret_ref)
        if self._oauth_refresher is not None and metadata.auth_mode is AuthMode.OAUTH:
            try:
                secret_payload = await self._oauth_refresher.refresh_if_needed(
                    secret_ref=metadata.secret_ref,
                    payload=secret_payload,
                )
            except Exception as exc:
                capture_sentry_exception(
                    exc,
                    tags={
                        "component": "hosted_reference",
                        "oauth_phase": "refresh",
                    },
                    extras={
                        "credential_id": metadata.credential_id,
                        "tenant_id": metadata.tenant_id,
                    },
                )
                _LOGGER.warning(
                    "OAuth credential refresh failed; using current tenant payload. "
                    "credential_id=%s tenant_id=%s error_type=%s",
                    metadata.credential_id,
                    metadata.tenant_id,
                    type(exc).__name__,
                )
        return TenantCredentialRecord.model_validate(
            {
                "credential_id": metadata.credential_id,
                "tenant_id": metadata.tenant_id,
                "auth_mode": metadata.auth_mode,
                "api_key": secret_payload.api_key,
                "access_token": secret_payload.access_token,
                "system_name": metadata.system_name,
                "system_key": secret_payload.system_key,
                "status": metadata.status,
            }
        )

    async def aclose(self) -> None:
        """Close the owned PostgreSQL pool when this store created it."""
        if self._owns_pool:
            await self._pool.aclose()


class RedisHostedRateLimitBackend(HostedRateLimitBackend):
    """Redis-backed hosted rate-limit backend shared across app instances."""

    def __init__(
        self,
        redis_url: SecretStr | str | None = None,
        *,
        redis_client: RedisClientProtocol | None = None,
        key_prefix: str = _DEFAULT_REDIS_KEY_PREFIX,
    ) -> None:
        """Initialize the Redis-backed hosted rate-limit backend.

        Args:
            redis_url: Redis connection string used when no client is injected.
            redis_client: Optional prebuilt async Redis client used mainly by
                focused tests.
            key_prefix: Stable key prefix for hosted rate-limit buckets.

        Raises:
            ValueError: If neither `redis_url` nor `redis_client` is provided.
        """
        if redis_client is None and redis_url is None:
            raise ValueError("redis_url is required when redis_client is not provided.")

        self._owns_client = redis_client is None
        self._redis = redis_client or cast(
            RedisClientProtocol,
            redis_from_url(_secret_value(cast(SecretStr | str, redis_url))),
        )
        self._key_prefix = _normalize_required_string(key_prefix, field_name="key_prefix").rstrip(
            ":"
        )

    def _redis_key(self, key: HostedRateLimitKey) -> str:
        """Build the stable Redis key for one hosted caller budget.

        Args:
            key: The stable tenant and client budget key.

        Returns:
            The Redis key used to track the caller's sliding-window budget.
        """
        key_parts = [self._key_prefix, key.tenant_id, key.client_id]
        if key.client_ip is not None:
            key_parts.append(key.client_ip)
        return ":".join(key_parts)

    async def consume(
        self,
        key: HostedRateLimitKey,
        *,
        limit: int,
        window_seconds: float,
    ) -> HostedRateLimitDecision:
        """Consume one request from the caller's Redis-backed sliding window.

        Args:
            key: The stable caller budget key.
            limit: Maximum requests allowed within the window.
            window_seconds: Duration of the sliding window in seconds.

        Returns:
            The rate-limit decision for the current request.
        """
        now_ms = int(time.time() * 1000)
        window_ms = max(int(window_seconds * 1000), 1)
        member = f"{now_ms}:{uuid.uuid4().hex}"
        raw_result = await self._redis.eval(
            _REDIS_CONSUME_SCRIPT,
            1,
            self._redis_key(key),
            str(now_ms),
            str(window_ms),
            str(limit),
            member,
        )
        result = cast(Sequence[object], raw_result)
        retry_after_milliseconds = _coerce_redis_integer(result[2])
        return HostedRateLimitDecision(
            allowed=bool(_coerce_redis_integer(result[0])),
            remaining_requests=_coerce_redis_integer(result[1]),
            retry_after_seconds=(
                None if retry_after_milliseconds < 0 else retry_after_milliseconds / 1000.0
            ),
        )

    async def aclose(self) -> None:
        """Close the owned Redis client when this backend created it."""
        if self._owns_client:
            await self._redis.aclose()


def _load_hosted_deployment_settings() -> FollowUpBossHostedDeploymentSettings:
    """Load hosted deployment settings from environment-backed defaults.

    Returns:
        The hosted deployment settings loaded from environment sources.
    """
    return FollowUpBossHostedDeploymentSettings()  # type: ignore[call-arg]


def create_reference_hosted_server(
    *,
    hosted_settings: FollowUpBossHostedDeploymentSettings | None = None,
    server_settings: FollowUpBossServerSettings | None = None,
    tenant_runtime_defaults: FollowUpBossTenantRuntimeDefaults | None = None,
) -> MCPServer:
    """Create the reference hosted `streamable-http` server.

    Args:
        hosted_settings: Optional hosted deployment settings model. When omitted,
            environment variables are loaded through
            `FollowUpBossHostedDeploymentSettings`.
        server_settings: Optional server-only bootstrap settings. When omitted,
            environment variables are loaded through
            `FollowUpBossServerSettings`.
        tenant_runtime_defaults: Optional shared non-secret Follow Up Boss client
            defaults. When omitted, environment variables are loaded through
            `FollowUpBossTenantRuntimeDefaults`.

    Returns:
        The configured MCP server for the reference hosted deployment.

    Raises:
        ValueError: If the supplied server settings do not use the
            `streamable-http` transport.
    """
    resolved_hosted_settings = hosted_settings or _load_hosted_deployment_settings()
    base_server_settings = server_settings or FollowUpBossServerSettings()
    if server_settings is not None and server_settings.transport != "streamable-http":
        raise ValueError("Reference hosted deployment only supports streamable-http transport.")
    resolved_server_settings = base_server_settings.model_copy(
        update={"transport": "streamable-http"}
    )

    resolved_runtime_defaults = tenant_runtime_defaults or FollowUpBossTenantRuntimeDefaults()
    secret_store = AwsSecretsManagerTenantSecretStore(
        region_name=resolved_hosted_settings.tenant_secret_region,
        secret_prefix=resolved_hosted_settings.tenant_secret_prefix,
    )
    shared_postgres_pool = ReferenceHostedPostgresPool(resolved_hosted_settings.tenant_database_url)
    oauth_settings = resolved_hosted_settings.hosted_oauth_settings()
    oauth_application: HostedOAuthApplication | None = None
    oauth_refresher: FollowUpBossTenantOAuthRefresher | None = None
    if oauth_settings is not None:
        oauth_secret_writer = AwsSecretsManagerHostedOAuthSecretWriter(
            region_name=resolved_hosted_settings.tenant_secret_region,
            secret_prefix=resolved_hosted_settings.tenant_secret_prefix,
        )
        oauth_fub_client = FollowUpBossOAuthClient(oauth_settings)
        oauth_refresher = FollowUpBossTenantOAuthRefresher(
            fub_client=oauth_fub_client,
            secret_writer=oauth_secret_writer,
        )
        oauth_store = PostgresRedisHostedOAuthStore(
            resolved_hosted_settings.tenant_database_url,
            redis_url=resolved_hosted_settings.redis_url,
            pool=shared_postgres_pool,
        )
        oauth_provisioner = PostgresAwsHostedOAuthTenantProvisioner(
            resolved_hosted_settings.tenant_database_url,
            pool=shared_postgres_pool,
            secret_writer=oauth_secret_writer,
            system_name=oauth_settings.system_name,
            system_key=oauth_settings.system_key,
        )
        oauth_application = HostedOAuthApplication(
            settings=oauth_settings,
            store=oauth_store,
            tenant_provisioner=oauth_provisioner,
            fub_client=oauth_fub_client,
        )
    tenant_store = PostgresAwsTenantStore(
        resolved_hosted_settings.tenant_database_url,
        secret_store=secret_store,
        pool=shared_postgres_pool,
        oauth_refresher=oauth_refresher,
    )
    hosted_rate_limiter = HostedEndpointRateLimiter(
        settings=resolved_hosted_settings.hosted_rate_limit_settings(),
        backend=RedisHostedRateLimitBackend(resolved_hosted_settings.redis_url),
    )
    return create_server(
        resolved_runtime_defaults,
        server_settings=resolved_server_settings,
        hosted_auth=resolved_hosted_settings.hosted_auth_settings(),
        hosted_token_verifier=PostgresHostedTokenVerifier(
            resolved_hosted_settings.tenant_database_url,
            resource_server_url=resolved_hosted_settings.resource_server_url,
            pool=shared_postgres_pool,
        ),
        tenant_store=tenant_store,
        hosted_rate_limiter=hosted_rate_limiter,
        hosted_oauth_application=oauth_application,
        managed_resources=(shared_postgres_pool,),
        sentry_entrypoint="followupboss-mcp-hosted",
    )


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser for the reference hosted server.

    Returns:
        The configured hosted-server CLI parser.
    """
    parser = argparse.ArgumentParser(
        prog="followupboss-mcp-hosted",
        description="Run the reference hosted Follow Up Boss MCP server.",
    )
    parser.add_argument("--host", default=None, help="Optional bind host override.")
    parser.add_argument("--port", default=None, type=int, help="Optional bind port override.")
    parser.add_argument("--path", default=None, help="Optional streamable HTTP path override.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the reference hosted server CLI.

    Args:
        argv: Optional command-line arguments.

    Returns:
        The process exit code.
    """
    parser = build_parser()
    args = parser.parse_args(argv)
    configure_sentry(entrypoint="followupboss-mcp-hosted", transport="streamable-http")
    base_server_settings = FollowUpBossServerSettings()
    configure_sentry(entrypoint="followupboss-mcp-hosted", transport="streamable-http")
    server_settings = base_server_settings.model_copy(
        update={
            "transport": "streamable-http",
            "host": getattr(args, "host", None) or base_server_settings.host,
            "port": getattr(args, "port", None) or base_server_settings.port,
            "streamable_http_path": getattr(args, "path", None)
            or base_server_settings.streamable_http_path,
        }
    )
    try:
        server = create_reference_hosted_server(server_settings=server_settings)
        server.run(
            transport="streamable-http",
            host=server_settings.host,
            port=server_settings.port,
            streamable_http_path=server_settings.streamable_http_path,
            json_response=True,
        )
        return 0
    finally:
        flush_sentry()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
