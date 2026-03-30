"""Reference hosted deployment backends and entrypoint."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import time
import uuid
from collections.abc import Awaitable, Callable, Mapping, Sequence
from contextlib import AbstractAsyncContextManager
from typing import Annotated, Protocol, Self, cast

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
from followupboss_mcp.hosted_rate_limits import (
    HostedEndpointRateLimiter,
    HostedRateLimitBackend,
    HostedRateLimitDecision,
    HostedRateLimitKey,
    HostedRateLimitSettings,
)
from followupboss_mcp.mcp_server import create_server
from followupboss_mcp.tenant_store import (
    TenantCredentialRecord,
    TenantCredentialStatus,
    TenantRecord,
    TenantStore,
)
from mcp.server.fastmcp import FastMCP

_DEFAULT_HOSTED_REQUIRED_SCOPE = "followupboss:mcp"
_DEFAULT_REDIS_KEY_PREFIX = "followupboss:hosted_rate_limit"

_HOSTED_ACCESS_TOKEN_QUERY = """
SELECT tenant_id, subject, client_id, scopes, expires_at, token_id, credential_id
FROM hosted_access_tokens
WHERE token_hash = %s
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
            Hosted auth settings suitable for the FastMCP streamable HTTP
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


class ReferenceHostedSecretPayload(BaseModel):
    """Validated raw Follow Up Boss secret payload from AWS Secrets Manager."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    api_key: SecretStr | None = None
    access_token: SecretStr | None = None
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


class RedisClientProtocol(Protocol):
    """Protocol for the subset of Redis used by this module."""

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


class PostgresHostedTokenVerifier(HostedIdentityVerifier):
    """PostgreSQL-backed verifier for opaque hosted bearer tokens."""

    def __init__(
        self,
        database_url: SecretStr | str | None = None,
        *,
        pool: ReferenceHostedPostgresPool | None = None,
        time_provider: Callable[[], int] | None = None,
    ) -> None:
        """Initialize the PostgreSQL-backed hosted token verifier.

        Args:
            database_url: PostgreSQL connection string for hosted-token metadata
                when no pool is injected.
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
            (hash_hosted_bearer_token(token), self._time_provider()),
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
    ) -> None:
        """Initialize the PostgreSQL and AWS-backed tenant store.

        Args:
            database_url: PostgreSQL connection string for tenant metadata when
                no pool is injected.
            secret_store: Secret-store integration used to resolve raw Follow Up
                Boss credentials.
            pool: Optional shared PostgreSQL pool used to reuse connections
                across hosted token and tenant lookups.

        Raises:
            ValueError: If neither `database_url` nor `pool` is provided.
        """
        if database_url is None and pool is None:
            raise ValueError("database_url is required when pool is not provided.")

        self._pool = pool or ReferenceHostedPostgresPool(cast(SecretStr | str, database_url))
        self._owns_pool = pool is None
        self._secret_store = secret_store

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
        row = cast(Mapping[str, object], raw_row)
        return TenantRecord.model_validate(dict(row))

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

        metadata = _TenantCredentialMetadataRow.model_validate(
            dict(cast(Mapping[str, object], raw_row))
        )
        secret_payload = await self._secret_store.get_secret_payload(metadata.secret_ref)
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
) -> FastMCP:
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
        The configured FastMCP server for the reference hosted deployment.

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
    shared_postgres_pool = ReferenceHostedPostgresPool(
        resolved_hosted_settings.tenant_database_url
    )
    tenant_store = PostgresAwsTenantStore(
        resolved_hosted_settings.tenant_database_url,
        secret_store=secret_store,
        pool=shared_postgres_pool,
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
            pool=shared_postgres_pool,
        ),
        tenant_store=tenant_store,
        hosted_rate_limiter=hosted_rate_limiter,
        managed_resources=(shared_postgres_pool,),
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
    base_server_settings = FollowUpBossServerSettings()
    server_settings = base_server_settings.model_copy(
        update={
            "transport": "streamable-http",
            "host": getattr(args, "host", None) or base_server_settings.host,
            "port": getattr(args, "port", None) or base_server_settings.port,
            "streamable_http_path": getattr(args, "path", None)
            or base_server_settings.streamable_http_path,
        }
    )
    server = create_reference_hosted_server(server_settings=server_settings)
    server.run(transport="streamable-http")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
