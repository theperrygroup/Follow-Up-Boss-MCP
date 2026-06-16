"""Tests for the reference hosted deployment backends and CLI."""

from __future__ import annotations

import hashlib
import json
from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, cast

import pytest
from pydantic import SecretStr, ValidationError

import followupboss_mcp.hosted_reference as hosted_reference
from followupboss_mcp.config import FollowUpBossServerSettings, FollowUpBossTenantRuntimeDefaults
from followupboss_mcp.errors import TenantSecretStoreUnavailableError, TenantStoreUnavailableError
from followupboss_mcp.hosted_oauth import (
    FollowUpBossOAuthIdentity,
    FollowUpBossOAuthTokenPayload,
    HostedOAuthAccessTokenMetadata,
    HostedOAuthAuthorizationCode,
    HostedOAuthDynamicClient,
    HostedOAuthPendingAuthorization,
    HostedOAuthRefreshToken,
)
from followupboss_mcp.hosted_rate_limits import HostedRateLimitKey
from followupboss_mcp.hosted_reference import (
    AwsSecretsManagerHostedOAuthSecretWriter,
    AwsSecretsManagerTenantSecretStore,
    FollowUpBossHostedDeploymentSettings,
    FollowUpBossTenantOAuthRefresher,
    PostgresAwsHostedOAuthTenantProvisioner,
    PostgresAwsTenantStore,
    PostgresHostedTokenVerifier,
    PostgresRedisHostedOAuthStore,
    RedisHostedRateLimitBackend,
    ReferenceHostedSecretPayload,
    build_parser,
    create_reference_hosted_server,
    hash_hosted_bearer_token,
    main,
)


class FakeSecretsClient:
    """Secrets Manager client stub used by hosted-reference tests."""

    def __init__(
        self,
        *,
        response: object | None = None,
        error: Exception | None = None,
        put_error: Exception | None = None,
    ) -> None:
        """Initialize the fake Secrets Manager client.

        Args:
            response: Optional response payload to return.
            error: Optional error to raise instead of returning a payload.
            put_error: Optional error to raise on put before create fallback.
        """
        self._response = response
        self._error = error
        self._put_error = put_error
        self.secret_ids: list[str] = []
        self.put_calls: list[dict[str, object]] = []
        self.create_calls: list[dict[str, object]] = []

    def get_secret_value(self, **kwargs: object) -> object:
        """Return the configured secret payload or raise the configured error.

        Args:
            **kwargs: Keyword arguments forwarded by the production code.

        Returns:
            The configured response payload.

        Raises:
            Exception: The configured error when one is present.
        """
        self.secret_ids.append(str(kwargs["SecretId"]))
        if self._error is not None:
            raise self._error
        return self._response

    def put_secret_value(self, **kwargs: object) -> object:
        """Record a put-secret request."""
        self.put_calls.append(dict(kwargs))
        if self._put_error is not None:
            raise self._put_error
        return {}

    def create_secret(self, **kwargs: object) -> object:
        """Record a create-secret request."""
        self.create_calls.append(dict(kwargs))
        return {}


class FakeSecretStore:
    """Secret-store stub used by the PostgreSQL tenant-store tests."""

    def __init__(self, payload: ReferenceHostedSecretPayload) -> None:
        """Initialize the fake secret store.

        Args:
            payload: The payload returned for every secret reference.
        """
        self._payload = payload
        self.secret_refs: list[str] = []

    async def get_secret_payload(self, secret_ref: str) -> ReferenceHostedSecretPayload:
        """Return the configured payload and record the secret reference.

        Args:
            secret_ref: The secret reference requested by the tenant store.

        Returns:
            The configured tenant secret payload.
        """
        self.secret_refs.append(secret_ref)
        return self._payload


class FakeCursor:
    """Async cursor stub that returns one configured row."""

    def __init__(
        self,
        *,
        row: Mapping[str, object] | None,
        execute_calls: list[tuple[str, tuple[object, ...]]],
    ) -> None:
        """Initialize the fake cursor.

        Args:
            row: The row returned by `fetchone()`.
            execute_calls: Shared list used to record executed queries.
        """
        self._row = row
        self._execute_calls = execute_calls

    async def __aenter__(self) -> FakeCursor:
        """Enter the async context manager for the fake cursor."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: object | None,
    ) -> None:
        """Exit the async context manager for the fake cursor."""
        del exc_type, exc, tb

    async def execute(self, query: str, params: tuple[object, ...]) -> None:
        """Record the executed query and parameters.

        Args:
            query: The executed SQL query.
            params: The bound parameter tuple.
        """
        self._execute_calls.append((query.strip(), params))

    async def fetchone(self) -> Mapping[str, object] | None:
        """Return the configured single row result."""
        return self._row


class FakeConnection:
    """Async connection stub that exposes one fake cursor."""

    def __init__(
        self,
        *,
        row: Mapping[str, object] | None,
        execute_calls: list[tuple[str, tuple[object, ...]]],
    ) -> None:
        """Initialize the fake connection.

        Args:
            row: The row returned by the cursor's `fetchone()`.
            execute_calls: Shared list used to record executed queries.
        """
        self._row = row
        self._execute_calls = execute_calls

    async def __aenter__(self) -> FakeConnection:
        """Enter the async context manager for the fake connection."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: object | None,
    ) -> None:
        """Exit the async context manager for the fake connection."""
        del exc_type, exc, tb

    def cursor(self, *, row_factory: object | None = None) -> FakeCursor:
        """Return one fake cursor.

        Args:
            row_factory: The requested row factory when one is supplied.

        Returns:
            The fake cursor bound to this connection.
        """
        del row_factory
        return FakeCursor(row=self._row, execute_calls=self._execute_calls)


class FakeConnectionFactory:
    """Factory stub that can act as a fake PostgreSQL pool."""

    def __init__(self, results: list[Mapping[str, object] | None | Exception]) -> None:
        """Initialize the fake connection factory.

        Args:
            results: Per-connect results. Exceptions raise during connect, while
                row mappings and `None` values are returned by `fetchone()`.
        """
        self._results = list(results)
        self.connection_strings: list[str] = []
        self.execute_calls: list[tuple[str, tuple[object, ...]]] = []
        self.connection_requests = 0
        self.open_calls = 0
        self.closed = False

    def _next_connection(self) -> FakeConnection:
        """Return the next fake connection or raise the next configured error.

        Returns:
            A fake async connection object.

        Raises:
            Exception: The next configured exception result.
        """
        self.connection_requests += 1
        next_result = self._results.pop(0)
        if isinstance(next_result, Exception):
            raise next_result
        return FakeConnection(row=next_result, execute_calls=self.execute_calls)

    async def connect(self, connection_string: str, **kwargs: object) -> FakeConnection:
        """Return the next fake connection for direct psycopg connect calls.

        Args:
            connection_string: The PostgreSQL connection string supplied by the
                production code.
            **kwargs: Additional connection keyword arguments.

        Returns:
            A fake async connection object.
        """
        del kwargs
        self.connection_strings.append(connection_string)
        return self._next_connection()

    async def open(self) -> None:
        """Record that the fake pool was opened."""
        self.open_calls += 1

    @asynccontextmanager
    async def connection(self) -> AsyncIterator[FakeConnection]:
        """Yield the next fake connection through the pool interface."""
        yield self._next_connection()

    async def aclose(self) -> None:
        """Mark the fake pool as closed."""
        self.closed = True


class FakeAsyncConnectionManager:
    """Async context manager stub used by pool-wrapper tests."""

    async def __aenter__(self) -> FakeConnection:
        """Return one empty fake connection."""
        return FakeConnection(row=None, execute_calls=[])

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: object | None,
    ) -> None:
        """Exit the async context manager for the fake pooled connection."""
        del exc_type, exc, tb


class FakeAsyncConnectionPool:
    """Minimal async pool stub used by `ReferenceHostedPostgresPool` tests."""

    def __init__(self) -> None:
        """Initialize the fake async pool."""
        self.connection_calls = 0
        self.connection_manager = FakeAsyncConnectionManager()
        self.open_calls = 0
        self.close_calls = 0

    async def open(self) -> None:
        """Record one pool-open request."""
        self.open_calls += 1

    def connection(self) -> FakeAsyncConnectionManager:
        """Return the configured async connection manager."""
        self.connection_calls += 1
        return self.connection_manager

    async def close(self) -> None:
        """Record one pool-close request."""
        self.close_calls += 1


class FakeRedisClient:
    """Redis client stub for the reference hosted rate-limit backend."""

    def __init__(self, results: list[object]) -> None:
        """Initialize the fake Redis client.

        Args:
            results: Per-call `EVAL` return values.
        """
        self._results = list(results)
        self.eval_calls: list[tuple[str, int, tuple[str, ...]]] = []
        self.get_calls: list[str] = []
        self.values: dict[str, str] = {}
        self.set_calls: list[tuple[str, str, int]] = []
        self.deleted_keys: list[str] = []
        self.closed = False

    async def get(self, name: str) -> object:
        """Return one stored Redis value."""
        self.get_calls.append(name)
        return self.values.get(name)

    async def set(self, name: str, value: str, *, ex: int) -> object:
        """Set one Redis value."""
        self.values[name] = value
        self.set_calls.append((name, value, ex))
        return True

    async def delete(self, name: str) -> object:
        """Delete one Redis value."""
        self.deleted_keys.append(name)
        self.values.pop(name, None)
        return 1

    async def eval(self, script: str, numkeys: int, *args: str) -> object:
        """Return the next configured Lua-script result.

        Args:
            script: The Lua script executed by the backend.
            numkeys: The number of keys supplied to the script.
            *args: The keys and arguments supplied to the script.

        Returns:
            The configured Redis response payload.
        """
        self.eval_calls.append((script, numkeys, args))
        if script == hosted_reference._REDIS_GET_DELETE_SCRIPT:
            value = self.values.get(args[0])
            if value is not None:
                self.values.pop(args[0], None)
            return value
        return self._results.pop(0)

    async def aclose(self) -> None:
        """Mark the fake Redis client as closed."""
        self.closed = True


class FakeFollowUpBossOAuthClient:
    """Follow Up Boss OAuth client stub for refresh tests."""

    def __init__(self, *, expires_in: int | None = 3600) -> None:
        """Initialize the fake client.

        Args:
            expires_in: Expiry returned by refresh calls.
        """
        self._expires_in = expires_in

    async def refresh_token(self, *, refresh_token: str) -> FollowUpBossOAuthTokenPayload:
        """Return a deterministic refreshed token payload."""
        assert refresh_token == "old-refresh"
        return FollowUpBossOAuthTokenPayload.model_validate(
            {
                "access_token": "new-access",
                "refresh_token": "new-refresh",
                "expires_in": self._expires_in,
            }
        )


def test_hash_hosted_bearer_token_and_secret_payload_validation() -> None:
    """Hosted token hashes and secret payloads should validate the staged contract."""
    expected_hash = "sha256:" + hashlib.sha256(b"hosted-token").hexdigest()
    assert hash_hosted_bearer_token("  hosted-token  ") == expected_hash

    payload = ReferenceHostedSecretPayload.model_validate({"api_key": "secret-key"})
    assert payload.api_key is not None
    assert payload.api_key.get_secret_value() == "secret-key"
    oauth_payload = ReferenceHostedSecretPayload.model_validate(
        {
            "access_token": "oauth-token",
            "refresh_token": "refresh-token",
            "access_token_expires_at": 1100,
        }
    )
    assert oauth_payload.needs_oauth_refresh(now=1000, refresh_buffer_seconds=200) is True
    assert oauth_payload.needs_oauth_refresh(now=1000, refresh_buffer_seconds=10) is False
    assert (
        ReferenceHostedSecretPayload.model_validate(
            {"access_token": "oauth-token", "refresh_token": "refresh-token"}
        ).needs_oauth_refresh(now=1000)
        is True
    )
    assert (
        ReferenceHostedSecretPayload.model_validate(
            {"access_token": "oauth-token"}
        ).needs_oauth_refresh(now=1000)
        is False
    )

    with pytest.raises(
        ValidationError, match="Exactly one of api_key or access_token must be present."
    ):
        ReferenceHostedSecretPayload.model_validate({})
    with pytest.raises(
        ValidationError, match="Exactly one of api_key or access_token must be present."
    ):
        ReferenceHostedSecretPayload.model_validate(
            {
                "api_key": "secret-key",
                "access_token": "oauth-token",
            }
        )


@pytest.mark.asyncio
async def test_reference_hosted_postgres_pool_wraps_pool_methods(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The managed PostgreSQL pool wrapper should proxy open, connection, and close calls."""
    captured: dict[str, object] = {}
    fake_pool = FakeAsyncConnectionPool()

    def fake_async_connection_pool(
        *, conninfo: str, kwargs: dict[str, object], open: bool
    ) -> FakeAsyncConnectionPool:
        captured["conninfo"] = conninfo
        captured["kwargs"] = kwargs
        captured["open"] = open
        return fake_pool

    monkeypatch.setattr(
        "followupboss_mcp.hosted_reference.AsyncConnectionPool",
        fake_async_connection_pool,
    )

    pool = hosted_reference.ReferenceHostedPostgresPool(
        "postgresql://app:secret@db.example.com:5432/fub"
    )
    await pool.open()
    pool.connection()
    await pool.aclose()

    assert hosted_reference._secret_value("plain-secret") == "plain-secret"
    assert captured["conninfo"] == "postgresql://app:secret@db.example.com:5432/fub"
    assert captured["open"] is False
    kwargs = cast(dict[str, object], captured["kwargs"])
    assert set(kwargs) == {"row_factory"}
    assert fake_pool.open_calls == 1
    assert fake_pool.connection_calls == 1
    assert fake_pool.close_calls == 1


@pytest.mark.asyncio
async def test_reference_hosted_postgres_pool_skips_close_for_injected_pool() -> None:
    """Injected async pools should not be closed by the wrapper."""
    fake_pool = FakeAsyncConnectionPool()
    pool = hosted_reference.ReferenceHostedPostgresPool(
        "postgresql://app:secret@db.example.com:5432/fub",
        pool=cast(Any, fake_pool),
    )

    await pool.open()
    pool.connection()
    await pool.aclose()

    assert fake_pool.open_calls == 1
    assert fake_pool.connection_calls == 1
    assert fake_pool.close_calls == 0


@pytest.mark.asyncio
async def test_oauth_secret_writer_puts_and_creates_secret_payloads() -> None:
    """OAuth secret writer should persist raw secret values under the allowed prefix."""
    fake_client = FakeSecretsClient(put_error=RuntimeError("missing"))
    writer = AwsSecretsManagerHostedOAuthSecretWriter(
        region_name="us-east-1",
        secret_prefix="followupboss/prod/tenants/",
        secrets_client=fake_client,
    )
    payload = ReferenceHostedSecretPayload.model_validate(
        {
            "access_token": "access-token",
            "refresh_token": "refresh-token",
            "access_token_expires_at": 1234,
            "system_key": "system-key",
        }
    )

    await writer.put_oauth_secret(
        secret_ref="followupboss/prod/tenants/credential-1",
        payload=payload,
    )

    assert writer.secret_ref_for_credential("credential-1") == (
        "followupboss/prod/tenants/credential-1"
    )
    assert fake_client.put_calls
    created_payload = json.loads(str(fake_client.create_calls[0]["SecretString"]))
    assert created_payload["access_token"] == "access-token"
    assert created_payload["refresh_token"] == "refresh-token"
    assert created_payload["system_key"] == "system-key"

    api_payload = ReferenceHostedSecretPayload.model_validate({"api_key": "secret-key"})
    await writer.put_oauth_secret(
        secret_ref="followupboss/prod/tenants/api-credential",
        payload=api_payload,
    )
    put_payload = json.loads(str(fake_client.put_calls[-1]["SecretString"]))
    assert put_payload["api_key"] == "secret-key"

    with pytest.raises(TenantSecretStoreUnavailableError):
        await writer.put_oauth_secret(
            secret_ref="other-prefix/credential-1",
            payload=payload,
        )

    class FailingWriteSecretsClient(FakeSecretsClient):
        """Secrets client that fails both update and create."""

        def create_secret(self, **kwargs: object) -> object:
            """Raise from create-secret."""
            del kwargs
            raise RuntimeError("create down")

    failing_client = FailingWriteSecretsClient(put_error=RuntimeError("missing"))
    failing_writer = AwsSecretsManagerHostedOAuthSecretWriter(
        region_name="us-east-1",
        secret_prefix="followupboss/prod/tenants/",
        secrets_client=failing_client,
    )
    with pytest.raises(TenantSecretStoreUnavailableError):
        await failing_writer.put_oauth_secret(
            secret_ref="followupboss/prod/tenants/credential-1",
            payload=payload,
        )


@pytest.mark.asyncio
async def test_oauth_refresher_updates_near_expiry_payload() -> None:
    """Tenant OAuth refresher should update Secrets Manager when access is near expiry."""
    fake_client = FakeSecretsClient()
    writer = AwsSecretsManagerHostedOAuthSecretWriter(
        region_name="us-east-1",
        secret_prefix="followupboss/prod/tenants/",
        secrets_client=fake_client,
    )
    refresher = FollowUpBossTenantOAuthRefresher(
        fub_client=cast(Any, FakeFollowUpBossOAuthClient()),
        secret_writer=writer,
        time_provider=lambda: 1000,
    )
    current_payload = ReferenceHostedSecretPayload.model_validate(
        {
            "access_token": "old-access",
            "refresh_token": "old-refresh",
            "access_token_expires_at": 1001,
            "system_key": "system-key",
        }
    )

    refreshed = await refresher.refresh_if_needed(
        secret_ref="followupboss/prod/tenants/credential-1",
        payload=current_payload,
    )

    assert refreshed.access_token is not None
    assert refreshed.access_token.get_secret_value() == "new-access"
    assert refreshed.refresh_token is not None
    assert refreshed.refresh_token.get_secret_value() == "new-refresh"
    assert fake_client.put_calls
    fresh_payload = ReferenceHostedSecretPayload.model_validate(
        {
            "access_token": "still-valid",
            "refresh_token": "old-refresh",
            "access_token_expires_at": 2000,
        }
    )
    assert (
        await refresher.refresh_if_needed(
            secret_ref="followupboss/prod/tenants/credential-1",
            payload=fresh_payload,
        )
        is fresh_payload
    )

    class InconsistentPayload:
        """Payload shim that requests refresh without a refresh token."""

        refresh_token = None

        def needs_oauth_refresh(self, *, now: int, refresh_buffer_seconds: int) -> bool:
            """Return true to cover defensive refresh-token absence handling."""
            del now, refresh_buffer_seconds
            return True

    assert (
        await refresher.refresh_if_needed(
            secret_ref="followupboss/prod/tenants/credential-1",
            payload=cast(ReferenceHostedSecretPayload, InconsistentPayload()),
        )
        is not None
    )

    no_expiry_refresher = FollowUpBossTenantOAuthRefresher(
        fub_client=cast(Any, FakeFollowUpBossOAuthClient(expires_in=None)),
        secret_writer=writer,
        time_provider=lambda: 1000,
    )
    no_expiry = await no_expiry_refresher.refresh_if_needed(
        secret_ref="followupboss/prod/tenants/credential-1",
        payload=current_payload,
    )
    assert no_expiry.access_token_expires_at is None


@pytest.mark.asyncio
async def test_oauth_tenant_provisioner_upserts_metadata_and_secret() -> None:
    """OAuth tenant provisioner should store FUB tokens and metadata rows."""
    with pytest.raises(ValueError, match="database_url is required"):
        PostgresAwsHostedOAuthTenantProvisioner(
            secret_writer=AwsSecretsManagerHostedOAuthSecretWriter(
                region_name="us-east-1",
                secret_prefix="followupboss/prod/tenants/",
                secrets_client=FakeSecretsClient(),
            )
        )

    fake_pool = FakeConnectionFactory([None, None])
    fake_client = FakeSecretsClient()
    writer = AwsSecretsManagerHostedOAuthSecretWriter(
        region_name="us-east-1",
        secret_prefix="followupboss/prod/tenants/",
        secrets_client=fake_client,
    )
    provisioner = PostgresAwsHostedOAuthTenantProvisioner(
        pool=cast(Any, fake_pool),
        secret_writer=writer,
        system_name="The-Perry-Group",
        system_key=SecretStr("system-key"),
        time_provider=lambda: 1000,
    )

    provisioned = await provisioner.provision_tenant(
        identity=FollowUpBossOAuthIdentity.model_validate(
            {
                "account_id": "1746230763",
                "account_name": "j-26",
                "user_id": "456",
            }
        ),
        token_payload=FollowUpBossOAuthTokenPayload.model_validate(
            {
                "access_token": "fub-access",
                "refresh_token": "fub-refresh",
                "expires_in": 3600,
            }
        ),
    )

    assert provisioned.tenant_id == "fub-account-1746230763"
    assert provisioned.credential_id == "cred-fub-account-1746230763-fub-user-456-oauth"
    assert fake_client.put_calls
    assert len(fake_pool.execute_calls) == 2
    assert "INSERT INTO tenants" in fake_pool.execute_calls[0][0]
    assert "INSERT INTO tenant_credentials" in fake_pool.execute_calls[1][0]
    await provisioner.aclose()
    assert fake_pool.closed is False


@pytest.mark.asyncio
async def test_postgres_redis_hosted_oauth_store_round_trips_state_and_tokens() -> None:
    """Hosted OAuth store should split short-lived Redis state from PostgreSQL metadata."""
    client_row = {
        "client_id": "client-1",
        "client_name": "Cursor",
        "redirect_uris": ["http://127.0.0.1/callback"],
        "scope": ["followupboss:mcp"],
        "token_endpoint_auth_method": "none",
    }
    refresh_row = {
        "token_hash": "refresh-hash",
        "tenant_id": "tenant-1",
        "subject": "subject-1",
        "client_id": "client-1",
        "scopes": ["followupboss:mcp"],
        "credential_id": "credential-1",
        "expires_at": 2000,
        "revoked_at": None,
    }
    fake_pool = FakeConnectionFactory([None, client_row, None, None, None, None, refresh_row, None])
    fake_redis = FakeRedisClient(results=[])
    store = PostgresRedisHostedOAuthStore(
        pool=cast(Any, fake_pool),
        redis_client=fake_redis,
    )

    await store.save_client(
        HostedOAuthDynamicClient.model_validate(
            {
                "client_id": "client-1",
                "client_name": "Cursor",
                "redirect_uris": ["http://127.0.0.1/callback"],
                "scope": "followupboss:mcp",
            }
        )
    )
    assert (await store.get_client("client-1")) is not None
    assert await store.get_client("missing-client") is None

    pending = HostedOAuthPendingAuthorization.model_validate(
        {
            "fub_state": "state-1",
            "client_id": "client-1",
            "redirect_uri": "http://127.0.0.1/callback",
            "code_challenge": "challenge",
            "code_challenge_method": "plain",
            "scopes": "followupboss:mcp",
            "expires_at": 2000,
        }
    )
    await store.save_pending_authorization(pending)
    assert fake_redis.set_calls[0][2] > 0
    assert await store.consume_pending_authorization("state-1") == pending
    assert await store.consume_pending_authorization("state-1") is None

    code = HostedOAuthAuthorizationCode.model_validate(
        {
            "code_hash": "code-hash",
            "client_id": "client-1",
            "redirect_uri": "http://127.0.0.1/callback",
            "code_challenge": "challenge",
            "code_challenge_method": "plain",
            "scopes": "followupboss:mcp",
            "tenant_id": "tenant-1",
            "subject": "subject-1",
            "credential_id": "credential-1",
            "expires_at": 2000,
        }
    )
    await store.save_authorization_code(code)
    assert await store.consume_authorization_code("code-hash") == code
    assert await store.consume_authorization_code("code-hash") is None
    atomic_eval_calls = [
        call
        for call in fake_redis.eval_calls
        if call[0] == hosted_reference._REDIS_GET_DELETE_SCRIPT
    ]
    assert len(atomic_eval_calls) == 4
    assert fake_redis.get_calls == []
    assert fake_redis.deleted_keys == []

    await store.save_access_token(
        HostedOAuthAccessTokenMetadata.model_validate(
            {
                "token_id": "token-1",
                "token_hash": "token-hash",
                "tenant_id": "tenant-1",
                "subject": "subject-1",
                "client_id": "client-1",
                "scopes": "followupboss:mcp",
                "credential_id": "credential-1",
                "expires_at": 2000,
            }
        )
    )
    await store.save_refresh_token(HostedOAuthRefreshToken.model_validate(refresh_row))
    assert await store.get_refresh_token("missing-refresh") is None
    assert await store.get_refresh_token("refresh-hash") == HostedOAuthRefreshToken.model_validate(
        refresh_row
    )
    await store.revoke_refresh_token("refresh-hash", revoked_at=1500)
    await store.aclose()
    assert fake_redis.closed is False
    assert "INSERT INTO hosted_access_tokens" in fake_pool.execute_calls[3][0]
    assert hosted_reference._coerce_json_mapping(b'{"ok": true}') == {"ok": True}
    assert hosted_reference._coerce_json_mapping("[1]") is None


def test_postgres_redis_hosted_oauth_store_requires_backends() -> None:
    """Hosted OAuth store should require both PostgreSQL and Redis configuration."""
    with pytest.raises(ValueError, match="database_url is required"):
        PostgresRedisHostedOAuthStore(redis_client=FakeRedisClient(results=[]))
    with pytest.raises(ValueError, match="redis_url is required"):
        PostgresRedisHostedOAuthStore(pool=cast(Any, FakeConnectionFactory([])))


@pytest.mark.asyncio
async def test_postgres_redis_hosted_oauth_store_closes_owned_backends(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Hosted OAuth store should close owned Redis and PostgreSQL clients."""

    class RecordingPool:
        """Owned pool stub."""

        def __init__(self, database_url: SecretStr | str) -> None:
            """Record construction."""
            del database_url
            self.closed = False

        async def aclose(self) -> None:
            """Record close calls."""
            self.closed = True

    fake_redis = FakeRedisClient(results=[])
    created_pools: list[RecordingPool] = []

    def make_pool(database_url: SecretStr | str) -> RecordingPool:
        """Create and remember one fake pool."""
        pool = RecordingPool(database_url)
        created_pools.append(pool)
        return pool

    monkeypatch.setattr("followupboss_mcp.hosted_reference.ReferenceHostedPostgresPool", make_pool)
    monkeypatch.setattr("followupboss_mcp.hosted_reference.redis_from_url", lambda _: fake_redis)
    store = PostgresRedisHostedOAuthStore(
        SecretStr("postgresql://app:secret@db.example.com:5432/fub"),
        redis_url=SecretStr("redis://cache.example.com:6379/0"),
    )

    await store.aclose()

    assert created_pools[0].closed is True
    assert fake_redis.closed is True


def test_hosted_deployment_settings_normalize_and_project_models() -> None:
    """Hosted deployment settings should normalize input and build auth and limiter settings."""
    settings = FollowUpBossHostedDeploymentSettings.model_validate(
        {
            "issuer_url": "issuer.example.com/",
            "resource_server_url": "mcp.example.com/mcp/",
            "required_scopes": "followupboss:mcp followupboss:mcp tools:read",
            "tenant_database_url": "postgresql://app:secret@db.example.com:5432/fub",
            "tenant_secret_prefix": "followupboss/prod/tenants",
            "tenant_secret_region": " us-east-1 ",
            "redis_url": "redis://cache.example.com:6379/0",
            "rate_limit_requests_per_window": 450,
            "rate_limit_window_seconds": 90,
            "rate_limit_include_client_ip": True,
        }
    )

    assert settings.required_scopes == ("followupboss:mcp", "tools:read")
    assert settings.tenant_secret_prefix == "followupboss/prod/tenants/"
    assert settings.tenant_secret_region == "us-east-1"
    hosted_auth_settings = settings.hosted_auth_settings()
    assert str(hosted_auth_settings.issuer_url) == "https://issuer.example.com/"
    assert str(hosted_auth_settings.resource_server_url) == "https://mcp.example.com/mcp"
    assert hosted_auth_settings.required_scopes == ("followupboss:mcp", "tools:read")
    rate_limit_settings = settings.hosted_rate_limit_settings()
    assert rate_limit_settings.requests_per_window == 450
    assert rate_limit_settings.window_seconds == 90
    assert rate_limit_settings.include_client_ip is True
    assert rate_limit_settings.backend_failure_mode == "closed"
    assert settings.hosted_oauth_settings() is None

    oauth_settings = FollowUpBossHostedDeploymentSettings.model_validate(
        {
            "issuer_url": "https://issuer.example.com/",
            "resource_server_url": "https://mcp.example.com/mcp/",
            "tenant_database_url": "postgresql://app:secret@db.example.com:5432/fub",
            "tenant_secret_prefix": "followupboss/prod/tenants",
            "tenant_secret_region": "us-east-1",
            "redis_url": "redis://cache.example.com:6379/0",
            "oauth_enabled": True,
            "fub_oauth_client_id": "fub-client",
            "fub_oauth_client_secret": "fub-secret",
            "fub_oauth_authorize_url": "app.followupboss.com/oauth/authorize/",
            "fub_oauth_token_url": "app.followupboss.com/oauth/token/",
            "fub_oauth_callback_url": "mcp.example.com/oauth/follow-up-boss/callback/",
            "fub_oauth_system_name": "The-Perry-Group",
            "fub_oauth_system_key": "system-key",
        }
    ).hosted_oauth_settings()
    assert oauth_settings is not None
    assert oauth_settings.fub_client_id == "fub-client"
    assert oauth_settings.system_name == "The-Perry-Group"
    assert oauth_settings.resource_server == "https://mcp.example.com/mcp"
    assert str(oauth_settings.fub_authorize_url) == (
        "https://app.followupboss.com/oauth/authorize"
    )
    assert str(oauth_settings.fub_token_url) == "https://app.followupboss.com/oauth/token"
    assert str(oauth_settings.fub_callback_url) == (
        "https://mcp.example.com/oauth/follow-up-boss/callback"
    )

    with pytest.raises(ValidationError):
        FollowUpBossHostedDeploymentSettings.model_validate(
            {
                "issuer_url": "https://issuer.example.com",
                "resource_server_url": "https://mcp.example.com/mcp",
                "tenant_database_url": "postgresql://app:secret@db.example.com:5432/fub",
                "tenant_secret_prefix": "followupboss/prod/tenants",
                "tenant_secret_region": " ",
                "redis_url": "redis://cache.example.com:6379/0",
            }
        )
    with pytest.raises(ValueError, match="FUB OAuth client id"):
        FollowUpBossHostedDeploymentSettings.model_validate(
            {
                "issuer_url": "https://issuer.example.com",
                "resource_server_url": "https://mcp.example.com/mcp",
                "tenant_database_url": "postgresql://app:secret@db.example.com:5432/fub",
                "tenant_secret_prefix": "followupboss/prod/tenants",
                "tenant_secret_region": "us-east-1",
                "redis_url": "redis://cache.example.com:6379/0",
                "oauth_enabled": True,
            }
        ).hosted_oauth_settings()
    with pytest.raises(ValidationError, match="query string"):
        FollowUpBossHostedDeploymentSettings.model_validate(
            {
                "issuer_url": "https://issuer.example.com",
                "resource_server_url": "https://mcp.example.com/mcp?bad=true",
                "tenant_database_url": "postgresql://app:secret@db.example.com:5432/fub",
                "tenant_secret_prefix": "followupboss/prod/tenants",
                "tenant_secret_region": "us-east-1",
                "redis_url": "redis://cache.example.com:6379/0",
            }
        )


def test_hosted_reference_private_helpers_cover_edge_cases() -> None:
    """Private hosted-reference helpers should preserve unsupported values safely."""
    unsupported_scope_value = object()
    invalid_scope_sequence: tuple[object, ...] = ("followupboss:mcp", 1)

    assert hosted_reference._normalize_scopes(None) == ()
    assert hosted_reference._normalize_scopes(unsupported_scope_value) is unsupported_scope_value
    assert hosted_reference._normalize_scopes(invalid_scope_sequence) is invalid_scope_sequence
    assert hosted_reference._coerce_redis_integer(True) == 1
    assert hosted_reference._coerce_redis_integer("2") == 2
    assert hosted_reference._coerce_redis_integer(b"3") == 3
    with pytest.raises(TypeError, match="non-integer"):
        hosted_reference._coerce_redis_integer(memoryview(b"4"))


@pytest.mark.asyncio
async def test_aws_secret_store_accepts_secret_string_and_arn_prefix() -> None:
    """The AWS secret store should accept ARN references within the configured prefix."""
    client = FakeSecretsClient(response={"SecretString": '{"api_key":"secret-key"}'})
    store = AwsSecretsManagerTenantSecretStore(
        region_name="us-east-1",
        secret_prefix="followupboss/prod/tenants/",
        secrets_client=client,
    )

    payload = await store.get_secret_payload(
        "arn:aws:secretsmanager:us-east-1:123456789012:secret:"
        "followupboss/prod/tenants/tenant-a/cred-1"
    )

    assert client.secret_ids == [
        "arn:aws:secretsmanager:us-east-1:123456789012:secret:"
        "followupboss/prod/tenants/tenant-a/cred-1"
    ]
    assert payload.api_key is not None
    assert payload.api_key.get_secret_value() == "secret-key"


@pytest.mark.asyncio
async def test_aws_secret_store_accepts_binary_payload_and_rejects_invalid_inputs() -> None:
    """The AWS secret store should accept binary payloads and fail closed on invalid inputs."""
    binary_client = FakeSecretsClient(
        response={"SecretBinary": memoryview(b'{"access_token":"oauth-token"}')}
    )
    binary_store = AwsSecretsManagerTenantSecretStore(
        region_name="us-east-1",
        secret_prefix="followupboss/prod/tenants",
        secrets_client=binary_client,
    )
    binary_payload = await binary_store.get_secret_payload(
        "followupboss/prod/tenants/tenant-a/cred-2"
    )
    assert binary_payload.access_token is not None
    assert binary_payload.access_token.get_secret_value() == "oauth-token"

    mismatched_store = AwsSecretsManagerTenantSecretStore(
        region_name="us-east-1",
        secret_prefix="followupboss/prod/tenants/",
        secrets_client=FakeSecretsClient(response={"SecretString": '{"api_key":"secret-key"}'}),
    )
    with pytest.raises(TenantSecretStoreUnavailableError):
        await mismatched_store.get_secret_payload("other/prefix/tenant-a/cred-1")

    error_store = AwsSecretsManagerTenantSecretStore(
        region_name="us-east-1",
        secret_prefix="followupboss/prod/tenants/",
        secrets_client=FakeSecretsClient(error=RuntimeError("boom")),
    )
    with pytest.raises(TenantSecretStoreUnavailableError):
        await error_store.get_secret_payload("followupboss/prod/tenants/tenant-a/cred-1")

    invalid_store = AwsSecretsManagerTenantSecretStore(
        region_name="us-east-1",
        secret_prefix="followupboss/prod/tenants/",
        secrets_client=FakeSecretsClient(
            response={"SecretString": '{"api_key":"secret-key","access_token":"oauth-token"}'}
        ),
    )
    with pytest.raises(TenantSecretStoreUnavailableError):
        await invalid_store.get_secret_payload("followupboss/prod/tenants/tenant-a/cred-1")


@pytest.mark.asyncio
async def test_aws_secret_store_accepts_bytes_payload_and_rejects_missing_payload() -> None:
    """The AWS secret store should accept raw bytes and reject missing secret values."""
    bytes_store = AwsSecretsManagerTenantSecretStore(
        region_name="us-east-1",
        secret_prefix="followupboss/prod/tenants/",
        secrets_client=FakeSecretsClient(response={"SecretBinary": b'{"api_key":"secret-key"}'}),
    )
    payload = await bytes_store.get_secret_payload("followupboss/prod/tenants/tenant-a/cred-3")
    assert payload.api_key is not None
    assert payload.api_key.get_secret_value() == "secret-key"

    missing_payload_store = AwsSecretsManagerTenantSecretStore(
        region_name="us-east-1",
        secret_prefix="followupboss/prod/tenants/",
        secrets_client=FakeSecretsClient(response={}),
    )
    with pytest.raises(TenantSecretStoreUnavailableError):
        await missing_payload_store.get_secret_payload("followupboss/prod/tenants/tenant-a/cred-3")


@pytest.mark.asyncio
async def test_postgres_hosted_token_verifier_hashes_tokens_and_returns_identity() -> None:
    """The PostgreSQL hosted token verifier should hash tokens and return matching identities."""
    factory = FakeConnectionFactory(
        [
            {
                "tenant_id": "tenant-1",
                "subject": "user-1",
                "client_id": "portal-app",
                "scopes": ["followupboss:mcp"],
                "expires_at": 200,
                "token_id": "token-1",
                "credential_id": "credential-1",
            },
            None,
        ]
    )
    verifier = PostgresHostedTokenVerifier(
        pool=cast(hosted_reference.ReferenceHostedPostgresPool, factory),
        time_provider=lambda: 123,
    )

    identity = await verifier.verify_token("  hosted-token  ")
    missing_identity = await verifier.verify_token("missing-token")

    assert identity is not None
    assert identity.tenant_id == "tenant-1"
    assert identity.scopes == ("followupboss:mcp",)
    assert identity.credential_id == "credential-1"
    assert missing_identity is None
    assert factory.open_calls == 2
    assert factory.connection_requests == 2
    assert factory.execute_calls[0][1] == (hash_hosted_bearer_token("hosted-token"), 123)


def test_postgres_hosted_components_require_database_url_without_injected_pool() -> None:
    """Hosted PostgreSQL components should reject missing database URLs without a pool."""
    with pytest.raises(ValueError, match="database_url is required when pool is not provided."):
        PostgresHostedTokenVerifier()
    with pytest.raises(ValueError, match="database_url is required when pool is not provided."):
        PostgresAwsTenantStore(
            secret_store=FakeSecretStore(
                ReferenceHostedSecretPayload.model_validate({"api_key": "secret-key"})
            )
        )


@pytest.mark.asyncio
async def test_postgres_aws_tenant_store_resolves_tenant_with_string_system_name() -> None:
    """The PostgreSQL and AWS-backed tenant store should assemble tenant credentials."""
    factory = FakeConnectionFactory(
        [
            {
                "tenant_id": "tenant-1",
                "tenant_slug": "tenant-one",
                "display_name": "Tenant One",
                "credential_id": "credential-1",
                "status": "active",
            },
            {
                "credential_id": "credential-1",
                "tenant_id": "tenant-1",
                "auth_mode": "api_key",
                "system_name": " Managed System ",
                "secret_ref": "followupboss/prod/tenants/tenant-1/credential-1",
                "status": "active",
            },
        ]
    )
    secret_store = FakeSecretStore(
        ReferenceHostedSecretPayload.model_validate({"api_key": "secret-key"})
    )
    store = PostgresAwsTenantStore(
        secret_store=secret_store,
        pool=cast(hosted_reference.ReferenceHostedPostgresPool, factory),
    )

    resolved = await store.resolve_tenant("tenant-1")

    assert resolved.tenant.tenant_slug == "tenant-one"
    assert resolved.credential.system_name == "Managed System"
    assert resolved.credential.api_key is not None
    assert resolved.credential.api_key.get_secret_value() == "secret-key"
    assert secret_store.secret_refs == ["followupboss/prod/tenants/tenant-1/credential-1"]
    assert factory.open_calls == 2
    assert factory.connection_requests == 2


@pytest.mark.asyncio
async def test_postgres_aws_tenant_store_supports_missing_rows_and_optional_system_name() -> None:
    """The PostgreSQL and AWS-backed tenant store should pass through missing rows safely."""
    factory = FakeConnectionFactory(
        [
            None,
            {
                "credential_id": "credential-2",
                "tenant_id": "tenant-2",
                "auth_mode": "oauth",
                "system_name": None,
                "secret_ref": "followupboss/prod/tenants/tenant-2/credential-2",
                "status": "active",
            },
            None,
        ]
    )
    secret_store = FakeSecretStore(
        ReferenceHostedSecretPayload.model_validate({"access_token": "oauth-token"})
    )
    store = PostgresAwsTenantStore(
        secret_store=secret_store,
        pool=cast(hosted_reference.ReferenceHostedPostgresPool, factory),
    )

    missing_tenant = await store.get_tenant("missing-tenant")
    credential = await store.get_credential("credential-2")
    missing_credential = await store.get_credential("missing-credential")

    assert missing_tenant is None
    assert credential is not None
    assert credential.system_name is None
    assert credential.access_token is not None
    assert credential.access_token.get_secret_value() == "oauth-token"
    assert missing_credential is None


@pytest.mark.asyncio
async def test_postgres_aws_tenant_store_refreshes_oauth_credentials() -> None:
    """The tenant store should refresh OAuth secret payloads before returning credentials."""

    class FakeOAuthRefresher:
        """OAuth refresher that returns a replacement access token."""

        async def refresh_if_needed(
            self,
            *,
            secret_ref: str,
            payload: ReferenceHostedSecretPayload,
        ) -> ReferenceHostedSecretPayload:
            """Return refreshed credential material."""
            assert secret_ref == "followupboss/prod/tenants/tenant-2/credential-2"
            assert payload.access_token is not None
            return ReferenceHostedSecretPayload.model_validate({"access_token": "refreshed-token"})

    factory = FakeConnectionFactory(
        [
            {
                "credential_id": "credential-2",
                "tenant_id": "tenant-2",
                "auth_mode": "oauth",
                "system_name": None,
                "secret_ref": "followupboss/prod/tenants/tenant-2/credential-2",
                "status": "active",
            },
        ]
    )
    store = PostgresAwsTenantStore(
        secret_store=FakeSecretStore(
            ReferenceHostedSecretPayload.model_validate({"access_token": "old-token"})
        ),
        pool=cast(hosted_reference.ReferenceHostedPostgresPool, factory),
        oauth_refresher=cast(FollowUpBossTenantOAuthRefresher, FakeOAuthRefresher()),
    )

    credential = await store.get_credential("credential-2")

    assert credential is not None
    assert credential.access_token is not None
    assert credential.access_token.get_secret_value() == "refreshed-token"


@pytest.mark.asyncio
async def test_postgres_aws_tenant_store_uses_current_oauth_on_refresh_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failed proactive OAuth refresh should not block tenant credential resolution."""
    captured: list[tuple[Exception, Mapping[str, object] | None, Mapping[str, object] | None]] = []

    def fake_capture_sentry_exception(
        exc: Exception,
        *,
        tags: Mapping[str, object] | None = None,
        extras: Mapping[str, object] | None = None,
    ) -> str:
        """Record captured refresh failures."""
        captured.append((exc, tags, extras))
        return "event-id"

    monkeypatch.setattr(
        hosted_reference,
        "capture_sentry_exception",
        fake_capture_sentry_exception,
    )

    class FailingOAuthRefresher:
        """OAuth refresher that simulates a transient upstream refresh failure."""

        def __init__(self) -> None:
            """Initialize the fake refresher call recorder."""
            self.secret_refs: list[str] = []

        async def refresh_if_needed(
            self,
            *,
            secret_ref: str,
            payload: ReferenceHostedSecretPayload,
        ) -> ReferenceHostedSecretPayload:
            """Raise after recording the refresh attempt."""
            del payload
            self.secret_refs.append(secret_ref)
            raise RuntimeError("temporary FUB outage")

    oauth_refresher = FailingOAuthRefresher()
    factory = FakeConnectionFactory(
        [
            {
                "tenant_id": "tenant-2",
                "tenant_slug": "tenant-two",
                "display_name": "Tenant Two",
                "credential_id": "credential-2",
                "status": "active",
            },
            {
                "credential_id": "credential-2",
                "tenant_id": "tenant-2",
                "auth_mode": "oauth",
                "system_name": None,
                "secret_ref": "followupboss/prod/tenants/tenant-2/credential-2",
                "status": "active",
            },
        ]
    )
    store = PostgresAwsTenantStore(
        secret_store=FakeSecretStore(
            ReferenceHostedSecretPayload.model_validate(
                {
                    "access_token": "current-token",
                    "refresh_token": "refresh-token",
                    "access_token_expires_at": 1240,
                }
            )
        ),
        pool=cast(hosted_reference.ReferenceHostedPostgresPool, factory),
        oauth_refresher=cast(FollowUpBossTenantOAuthRefresher, oauth_refresher),
    )

    resolved = await store.resolve_tenant("tenant-2")

    assert resolved.credential.access_token is not None
    assert resolved.credential.access_token.get_secret_value() == "current-token"
    assert oauth_refresher.secret_refs == ["followupboss/prod/tenants/tenant-2/credential-2"]
    assert len(captured) == 1
    assert captured[0][1] == {
        "component": "hosted_reference",
        "oauth_phase": "refresh",
    }
    assert captured[0][2] == {"credential_id": "credential-2", "tenant_id": "tenant-2"}


@pytest.mark.asyncio
async def test_postgres_aws_tenant_store_wraps_database_failures() -> None:
    """The PostgreSQL and AWS-backed tenant store should map database failures to safe errors."""
    tenant_factory = FakeConnectionFactory([RuntimeError("db down")])
    tenant_store = PostgresAwsTenantStore(
        secret_store=FakeSecretStore(
            ReferenceHostedSecretPayload.model_validate({"api_key": "secret-key"})
        ),
        pool=cast(hosted_reference.ReferenceHostedPostgresPool, tenant_factory),
    )
    with pytest.raises(TenantStoreUnavailableError, match="Tenant store is unavailable."):
        await tenant_store.get_tenant("tenant-1")

    credential_factory = FakeConnectionFactory([RuntimeError("db down")])
    credential_store = PostgresAwsTenantStore(
        secret_store=FakeSecretStore(
            ReferenceHostedSecretPayload.model_validate({"api_key": "secret-key"})
        ),
        pool=cast(hosted_reference.ReferenceHostedPostgresPool, credential_factory),
    )
    with pytest.raises(TenantStoreUnavailableError, match="Tenant store is unavailable."):
        await credential_store.get_credential("credential-1")


@pytest.mark.asyncio
async def test_postgres_hosted_components_close_owned_pools(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Hosted PostgreSQL components should close pools they construct themselves."""
    created_pools: list[object] = []

    class RecordingPool:
        def __init__(self, database_url: SecretStr | str) -> None:
            self.database_url = database_url
            self.closed = False
            created_pools.append(self)

        async def open(self) -> None:
            """Reject unexpected open requests in this close-path test."""
            raise AssertionError("open() should not be called in this test.")

        def connection(self) -> FakeAsyncConnectionManager:
            """Reject unexpected connection requests in this close-path test."""
            raise AssertionError("connection() should not be called in this test.")

        async def aclose(self) -> None:
            """Record that the fake owned pool was closed."""
            self.closed = True

    monkeypatch.setattr(
        "followupboss_mcp.hosted_reference.ReferenceHostedPostgresPool", RecordingPool
    )

    verifier = PostgresHostedTokenVerifier(
        SecretStr("postgresql://app:secret@db.example.com:5432/fub")
    )
    store = PostgresAwsTenantStore(
        SecretStr("postgresql://app:secret@db.example.com:5432/fub"),
        secret_store=FakeSecretStore(
            ReferenceHostedSecretPayload.model_validate({"api_key": "secret-key"})
        ),
    )
    provisioner = PostgresAwsHostedOAuthTenantProvisioner(
        SecretStr("postgresql://app:secret@db.example.com:5432/fub"),
        secret_writer=AwsSecretsManagerHostedOAuthSecretWriter(
            region_name="us-east-1",
            secret_prefix="followupboss/prod/tenants/",
            secrets_client=FakeSecretsClient(),
        ),
    )

    await verifier.aclose()
    await store.aclose()
    await provisioner.aclose()

    assert len(created_pools) == 3
    assert all(getattr(pool, "closed", False) for pool in created_pools)


@pytest.mark.asyncio
async def test_postgres_hosted_components_skip_close_for_injected_pools() -> None:
    """Injected PostgreSQL pools should not be closed by hosted components."""
    verifier_pool = FakeConnectionFactory([])
    credential_pool = FakeConnectionFactory([])
    verifier = PostgresHostedTokenVerifier(
        pool=cast(hosted_reference.ReferenceHostedPostgresPool, verifier_pool)
    )
    store = PostgresAwsTenantStore(
        secret_store=FakeSecretStore(
            ReferenceHostedSecretPayload.model_validate({"api_key": "secret-key"})
        ),
        pool=cast(hosted_reference.ReferenceHostedPostgresPool, credential_pool),
    )

    await verifier.aclose()
    await store.aclose()

    assert verifier_pool.closed is False
    assert credential_pool.closed is False


@pytest.mark.asyncio
async def test_redis_hosted_rate_limit_backend_consumes_results_and_closes_owned_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The Redis rate-limit backend should translate Lua results and close owned clients."""
    fake_client = FakeRedisClient(results=[[1, 2, -1], [0, 0, 2500]])
    monkeypatch.setattr("followupboss_mcp.hosted_reference.redis_from_url", lambda url: fake_client)
    backend = RedisHostedRateLimitBackend(SecretStr("redis://cache.example.com:6379/0"))

    allowed = await backend.consume(
        HostedRateLimitKey(tenant_id="tenant-1", client_id="portal-app"),
        limit=3,
        window_seconds=60.0,
    )
    denied = await backend.consume(
        HostedRateLimitKey(tenant_id="tenant-1", client_id="portal-app", client_ip="203.0.113.10"),
        limit=3,
        window_seconds=60.0,
    )
    await backend.aclose()

    assert allowed.allowed is True
    assert allowed.remaining_requests == 2
    assert allowed.retry_after_seconds is None
    assert denied.allowed is False
    assert denied.retry_after_seconds == 2.5
    assert fake_client.eval_calls[0][1] == 1
    assert fake_client.eval_calls[0][2][0] == "followupboss:hosted_rate_limit:tenant-1:portal-app"
    assert (
        fake_client.eval_calls[1][2][0]
        == "followupboss:hosted_rate_limit:tenant-1:portal-app:203.0.113.10"
    )
    assert fake_client.closed is True


@pytest.mark.asyncio
async def test_redis_hosted_rate_limit_backend_skips_close_for_injected_client() -> None:
    """The Redis rate-limit backend should skip injected-client shutdown."""
    with pytest.raises(
        ValueError, match="redis_url is required when redis_client is not provided."
    ):
        RedisHostedRateLimitBackend()

    injected_client = FakeRedisClient(results=[[1, 0, -1]])
    backend = RedisHostedRateLimitBackend(redis_client=injected_client, key_prefix="custom:prefix:")
    decision = await backend.consume(
        HostedRateLimitKey(tenant_id="tenant-2", client_id="other-client"),
        limit=1,
        window_seconds=10.0,
    )
    await backend.aclose()

    assert decision.allowed is True
    assert decision.remaining_requests == 0
    assert injected_client.eval_calls[0][2][0] == "custom:prefix:tenant-2:other-client"
    assert injected_client.closed is False


def test_create_reference_hosted_server_builds_reference_components(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The reference hosted factory should assemble concrete staging collaborators."""
    captured: dict[str, Any] = {}

    class FakeSecretStore:
        def __init__(self, *, region_name: str, secret_prefix: str) -> None:
            captured["secret_store"] = {
                "region_name": region_name,
                "secret_prefix": secret_prefix,
            }

    class FakeTenantStore:
        def __init__(
            self,
            database_url: SecretStr,
            *,
            secret_store: object,
            pool: object | None = None,
            oauth_refresher: object | None = None,
        ) -> None:
            captured["tenant_store"] = {
                "database_url": database_url.get_secret_value(),
                "secret_store": secret_store,
                "pool": pool,
                "oauth_refresher": oauth_refresher,
            }

    class FakeRedisBackend:
        def __init__(self, redis_url: SecretStr) -> None:
            captured["redis_backend"] = redis_url.get_secret_value()

    class FakeTokenVerifier:
        def __init__(self, database_url: SecretStr, *, pool: object | None = None) -> None:
            captured["token_verifier"] = {
                "database_url": database_url.get_secret_value(),
                "pool": pool,
            }

    class FakeServer:
        pass

    def fake_create_server(settings: object, **kwargs: object) -> FakeServer:
        captured["create_server"] = {"settings": settings, "kwargs": kwargs}
        return FakeServer()

    monkeypatch.setattr(
        "followupboss_mcp.hosted_reference.AwsSecretsManagerTenantSecretStore", FakeSecretStore
    )
    monkeypatch.setattr("followupboss_mcp.hosted_reference.PostgresAwsTenantStore", FakeTenantStore)
    monkeypatch.setattr(
        "followupboss_mcp.hosted_reference.RedisHostedRateLimitBackend", FakeRedisBackend
    )
    monkeypatch.setattr(
        "followupboss_mcp.hosted_reference.PostgresHostedTokenVerifier", FakeTokenVerifier
    )
    monkeypatch.setattr("followupboss_mcp.hosted_reference.create_server", fake_create_server)

    hosted_settings = FollowUpBossHostedDeploymentSettings.model_validate(
        {
            "issuer_url": "https://issuer.example.com",
            "resource_server_url": "https://mcp.example.com/mcp",
            "tenant_database_url": "postgresql://app:secret@db.example.com:5432/fub",
            "tenant_secret_prefix": "followupboss/prod/tenants/",
            "tenant_secret_region": "us-east-1",
            "redis_url": "redis://cache.example.com:6379/0",
        }
    )
    server_settings = FollowUpBossServerSettings.model_validate(
        {
            "transport": "streamable-http",
            "host": "0.0.0.0",
            "port": 9000,
            "streamable_http_path": "/tenant",
        }
    )
    runtime_defaults = FollowUpBossTenantRuntimeDefaults.model_validate(
        {
            "base_url": "https://api.example.com/v1/",
            "timeout_seconds": 12,
            "max_retries": 4,
        }
    )

    server = create_reference_hosted_server(
        hosted_settings=hosted_settings,
        server_settings=server_settings,
        tenant_runtime_defaults=runtime_defaults,
    )

    assert isinstance(server, FakeServer)
    assert captured["secret_store"] == {
        "region_name": "us-east-1",
        "secret_prefix": "followupboss/prod/tenants/",
    }
    assert (
        captured["tenant_store"]["database_url"]
        == "postgresql://app:secret@db.example.com:5432/fub"
    )
    assert captured["redis_backend"] == "redis://cache.example.com:6379/0"
    assert (
        captured["token_verifier"]["database_url"]
        == "postgresql://app:secret@db.example.com:5432/fub"
    )
    assert captured["tenant_store"]["pool"] is captured["token_verifier"]["pool"]
    created_kwargs = captured["create_server"]["kwargs"]
    assert created_kwargs["server_settings"].transport == "streamable-http"
    assert created_kwargs["hosted_auth"].required_scopes == ("followupboss:mcp",)
    assert created_kwargs["hosted_rate_limiter"].settings.requests_per_window == 300
    assert captured["create_server"]["settings"] == runtime_defaults

    with pytest.raises(
        ValueError,
        match="Reference hosted deployment only supports streamable-http transport.",
    ):
        create_reference_hosted_server(
            hosted_settings=hosted_settings,
            server_settings=FollowUpBossServerSettings.model_validate({"transport": "stdio"}),
        )


def test_create_reference_hosted_server_builds_oauth_components(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The reference factory should wire hosted OAuth collaborators when enabled."""
    captured: dict[str, Any] = {}

    class FakeSecretStore:
        def __init__(self, *, region_name: str, secret_prefix: str) -> None:
            captured["secret_store"] = (region_name, secret_prefix)

    class FakeSecretWriter:
        def __init__(self, *, region_name: str, secret_prefix: str) -> None:
            captured["secret_writer"] = (region_name, secret_prefix)

    class FakeFubOAuthClient:
        def __init__(self, settings: object) -> None:
            captured["fub_client"] = settings

    class FakeOAuthRefresher:
        def __init__(self, *, fub_client: object, secret_writer: object) -> None:
            captured["oauth_refresher"] = (fub_client, secret_writer)

    class FakeOAuthStore:
        def __init__(
            self,
            database_url: SecretStr,
            *,
            redis_url: SecretStr,
            pool: object | None = None,
        ) -> None:
            captured["oauth_store"] = (database_url.get_secret_value(), redis_url, pool)

    class FakeOAuthProvisioner:
        def __init__(
            self,
            database_url: SecretStr,
            *,
            pool: object | None,
            secret_writer: object,
            system_name: str | None,
            system_key: SecretStr | None,
        ) -> None:
            captured["oauth_provisioner"] = (
                database_url.get_secret_value(),
                pool,
                secret_writer,
                system_name,
                system_key,
            )

    class FakeOAuthApplication:
        def __init__(
            self,
            *,
            settings: object,
            store: object,
            tenant_provisioner: object,
            fub_client: object,
        ) -> None:
            captured["oauth_application"] = (settings, store, tenant_provisioner, fub_client)

    class FakeTenantStore:
        def __init__(
            self,
            database_url: SecretStr,
            *,
            secret_store: object,
            pool: object | None,
            oauth_refresher: object | None,
        ) -> None:
            captured["tenant_store"] = (database_url, secret_store, pool, oauth_refresher)

    class FakeRedisBackend:
        def __init__(self, redis_url: SecretStr) -> None:
            captured["redis_backend"] = redis_url

    class FakeTokenVerifier:
        def __init__(self, database_url: SecretStr, *, pool: object | None) -> None:
            captured["token_verifier"] = (database_url, pool)

    class FakeServer:
        pass

    def fake_create_server(settings: object, **kwargs: object) -> FakeServer:
        captured["create_server"] = kwargs
        return FakeServer()

    monkeypatch.setattr(
        "followupboss_mcp.hosted_reference.AwsSecretsManagerTenantSecretStore", FakeSecretStore
    )
    monkeypatch.setattr(
        "followupboss_mcp.hosted_reference.AwsSecretsManagerHostedOAuthSecretWriter",
        FakeSecretWriter,
    )
    monkeypatch.setattr(
        "followupboss_mcp.hosted_reference.FollowUpBossOAuthClient",
        FakeFubOAuthClient,
    )
    monkeypatch.setattr(
        "followupboss_mcp.hosted_reference.FollowUpBossTenantOAuthRefresher",
        FakeOAuthRefresher,
    )
    monkeypatch.setattr(
        "followupboss_mcp.hosted_reference.PostgresRedisHostedOAuthStore",
        FakeOAuthStore,
    )
    monkeypatch.setattr(
        "followupboss_mcp.hosted_reference.PostgresAwsHostedOAuthTenantProvisioner",
        FakeOAuthProvisioner,
    )
    monkeypatch.setattr(
        "followupboss_mcp.hosted_reference.HostedOAuthApplication",
        FakeOAuthApplication,
    )
    monkeypatch.setattr("followupboss_mcp.hosted_reference.PostgresAwsTenantStore", FakeTenantStore)
    monkeypatch.setattr(
        "followupboss_mcp.hosted_reference.RedisHostedRateLimitBackend", FakeRedisBackend
    )
    monkeypatch.setattr(
        "followupboss_mcp.hosted_reference.PostgresHostedTokenVerifier", FakeTokenVerifier
    )
    monkeypatch.setattr("followupboss_mcp.hosted_reference.create_server", fake_create_server)

    server = create_reference_hosted_server(
        hosted_settings=FollowUpBossHostedDeploymentSettings.model_validate(
            {
                "issuer_url": "https://issuer.example.com",
                "resource_server_url": "https://mcp.example.com/mcp",
                "tenant_database_url": "postgresql://app:secret@db.example.com:5432/fub",
                "tenant_secret_prefix": "followupboss/prod/tenants/",
                "tenant_secret_region": "us-east-1",
                "redis_url": "redis://cache.example.com:6379/0",
                "oauth_enabled": True,
                "fub_oauth_client_id": "fub-client",
                "fub_oauth_client_secret": "fub-secret",
                "fub_oauth_callback_url": "https://mcp.example.com/oauth/follow-up-boss/callback",
            }
        )
    )

    assert isinstance(server, FakeServer)
    assert "oauth_application" in captured
    assert captured["tenant_store"][3] is not None
    assert captured["create_server"]["hosted_oauth_application"] is not None


def test_create_reference_hosted_server_loads_hosted_settings_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The hosted factory should load hosted deployment settings from environment variables."""
    captured: dict[str, Any] = {}

    class FakeSecretStore:
        def __init__(self, *, region_name: str, secret_prefix: str) -> None:
            captured["secret_store"] = (region_name, secret_prefix)

    class FakeTenantStore:
        def __init__(
            self,
            database_url: SecretStr,
            *,
            secret_store: object,
            pool: object | None = None,
            oauth_refresher: object | None = None,
        ) -> None:
            captured["tenant_store"] = (
                database_url.get_secret_value(),
                secret_store,
                pool,
                oauth_refresher,
            )

    class FakeRedisBackend:
        def __init__(self, redis_url: SecretStr) -> None:
            captured["redis_backend"] = redis_url.get_secret_value()

    class FakeTokenVerifier:
        def __init__(self, database_url: SecretStr, *, pool: object | None = None) -> None:
            captured["token_verifier"] = (database_url.get_secret_value(), pool)

    class FakeServer:
        pass

    def fake_create_server(settings: object, **kwargs: object) -> FakeServer:
        captured["create_server"] = {"settings": settings, "kwargs": kwargs}
        return FakeServer()

    monkeypatch.setenv("FOLLOWUPBOSS_HOSTED_ISSUER_URL", "https://issuer.example.com")
    monkeypatch.setenv("FOLLOWUPBOSS_HOSTED_RESOURCE_SERVER_URL", "https://mcp.example.com/mcp")
    monkeypatch.setenv("FOLLOWUPBOSS_HOSTED_REQUIRED_SCOPES", "followupboss:mcp")
    monkeypatch.setenv(
        "FOLLOWUPBOSS_TENANT_DATABASE_URL", "postgresql://app:secret@db.example.com:5432/fub"
    )
    monkeypatch.setenv("FOLLOWUPBOSS_TENANT_SECRET_PREFIX", "followupboss/prod/tenants/")
    monkeypatch.setenv("FOLLOWUPBOSS_TENANT_SECRET_REGION", "us-east-1")
    monkeypatch.setenv("FOLLOWUPBOSS_REDIS_URL", "redis://cache.example.com:6379/0")
    monkeypatch.setattr(
        "followupboss_mcp.hosted_reference.AwsSecretsManagerTenantSecretStore",
        FakeSecretStore,
    )
    monkeypatch.setattr("followupboss_mcp.hosted_reference.PostgresAwsTenantStore", FakeTenantStore)
    monkeypatch.setattr(
        "followupboss_mcp.hosted_reference.RedisHostedRateLimitBackend",
        FakeRedisBackend,
    )
    monkeypatch.setattr(
        "followupboss_mcp.hosted_reference.PostgresHostedTokenVerifier",
        FakeTokenVerifier,
    )
    monkeypatch.setattr("followupboss_mcp.hosted_reference.create_server", fake_create_server)

    server = create_reference_hosted_server(
        server_settings=FollowUpBossServerSettings.model_validate({"transport": "streamable-http"})
    )

    assert isinstance(server, FakeServer)
    assert captured["secret_store"] == ("us-east-1", "followupboss/prod/tenants/")
    assert captured["tenant_store"][0] == "postgresql://app:secret@db.example.com:5432/fub"
    assert captured["redis_backend"] == "redis://cache.example.com:6379/0"
    assert captured["tenant_store"][2] is captured["token_verifier"][1]
    assert captured["create_server"]["kwargs"]["hosted_auth"].required_scopes == (
        "followupboss:mcp",
    )


def test_hosted_reference_cli_parser_and_main(monkeypatch: pytest.MonkeyPatch) -> None:
    """The hosted reference CLI should pass streamable HTTP settings through to the factory."""
    parser = build_parser()
    assert parser.prog == "followupboss-mcp-hosted"

    created_settings: list[Any] = []
    runs: list[str] = []

    @dataclass
    class FakeServerSettings:
        transport: str = "stdio"
        host: str = "127.0.0.1"
        port: int = 8000
        streamable_http_path: str = "/mcp"

        def model_copy(self, *, update: dict[str, Any]) -> FakeServerSettings:
            return FakeServerSettings(
                transport=update.get("transport", self.transport),
                host=update.get("host", self.host),
                port=update.get("port", self.port),
                streamable_http_path=update.get(
                    "streamable_http_path",
                    self.streamable_http_path,
                ),
            )

    class FakeServer:
        def run(self, transport: str) -> None:
            runs.append(transport)

    def fake_create_reference_hosted_server(*, server_settings: object) -> FakeServer:
        created_settings.append(server_settings)
        return FakeServer()

    monkeypatch.setattr(
        "followupboss_mcp.hosted_reference.FollowUpBossServerSettings",
        lambda: FakeServerSettings(),
    )
    monkeypatch.setattr(
        "followupboss_mcp.hosted_reference.create_reference_hosted_server",
        fake_create_reference_hosted_server,
    )

    assert main(["--host", "0.0.0.0", "--port", "9000", "--path", "/alt"]) == 0
    assert main([]) == 0
    assert created_settings[0].transport == "streamable-http"
    assert created_settings[0].host == "0.0.0.0"
    assert created_settings[0].port == 9000
    assert created_settings[0].streamable_http_path == "/alt"
    assert created_settings[1].host == "127.0.0.1"
    assert created_settings[1].port == 8000
    assert created_settings[1].streamable_http_path == "/mcp"
    assert runs == ["streamable-http", "streamable-http"]
