"""Tests for the reference hosted deployment backends and CLI."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import pytest
from pydantic import SecretStr, ValidationError

import followupboss_mcp.hosted_reference as hosted_reference
from followupboss_mcp.config import FollowUpBossServerSettings, FollowUpBossTenantRuntimeDefaults
from followupboss_mcp.errors import TenantSecretStoreUnavailableError, TenantStoreUnavailableError
from followupboss_mcp.hosted_rate_limits import HostedRateLimitKey
from followupboss_mcp.hosted_reference import (
    AwsSecretsManagerTenantSecretStore,
    FollowUpBossHostedDeploymentSettings,
    PostgresAwsTenantStore,
    PostgresHostedTokenVerifier,
    RedisHostedRateLimitBackend,
    ReferenceHostedSecretPayload,
    build_parser,
    create_reference_hosted_server,
    hash_hosted_bearer_token,
    main,
)


class FakeSecretsClient:
    """Secrets Manager client stub used by hosted-reference tests."""

    def __init__(self, *, response: object | None = None, error: Exception | None = None) -> None:
        """Initialize the fake Secrets Manager client.

        Args:
            response: Optional response payload to return.
            error: Optional error to raise instead of returning a payload.
        """
        self._response = response
        self._error = error
        self.secret_ids: list[str] = []

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

    def cursor(self, *, row_factory: object) -> FakeCursor:
        """Return one fake cursor.

        Args:
            row_factory: The requested row factory.

        Returns:
            The fake cursor bound to this connection.
        """
        del row_factory
        return FakeCursor(row=self._row, execute_calls=self._execute_calls)


class FakeConnectionFactory:
    """Factory stub for `psycopg.AsyncConnection.connect`."""

    def __init__(self, results: list[Mapping[str, object] | None | Exception]) -> None:
        """Initialize the fake connection factory.

        Args:
            results: Per-connect results. Exceptions raise during connect, while
                row mappings and `None` values are returned by `fetchone()`.
        """
        self._results = list(results)
        self.connection_strings: list[str] = []
        self.execute_calls: list[tuple[str, tuple[object, ...]]] = []

    async def connect(self, connection_string: str) -> FakeConnection:
        """Return the next fake connection or raise the next configured error.

        Args:
            connection_string: The PostgreSQL connection string supplied by the
                production code.

        Returns:
            A fake async connection object.

        Raises:
            Exception: The next configured exception result.
        """
        self.connection_strings.append(connection_string)
        next_result = self._results.pop(0)
        if isinstance(next_result, Exception):
            raise next_result
        return FakeConnection(row=next_result, execute_calls=self.execute_calls)


class FakeRedisClient:
    """Redis client stub for the reference hosted rate-limit backend."""

    def __init__(self, results: list[Sequence[object]]) -> None:
        """Initialize the fake Redis client.

        Args:
            results: Per-call `EVAL` return values.
        """
        self._results = list(results)
        self.eval_calls: list[tuple[str, int, tuple[str, ...]]] = []
        self.closed = False

    async def eval(self, script: str, numkeys: int, *args: str) -> Sequence[object]:
        """Return the next configured Lua-script result.

        Args:
            script: The Lua script executed by the backend.
            numkeys: The number of keys supplied to the script.
            *args: The keys and arguments supplied to the script.

        Returns:
            The configured Redis response sequence.
        """
        self.eval_calls.append((script, numkeys, args))
        return self._results.pop(0)

    async def aclose(self) -> None:
        """Mark the fake Redis client as closed."""
        self.closed = True


def test_hash_hosted_bearer_token_and_secret_payload_validation() -> None:
    """Hosted token hashes and secret payloads should validate the staged contract."""
    expected_hash = "sha256:" + hashlib.sha256(b"hosted-token").hexdigest()
    assert hash_hosted_bearer_token("  hosted-token  ") == expected_hash

    payload = ReferenceHostedSecretPayload.model_validate({"api_key": "secret-key"})
    assert payload.api_key is not None
    assert payload.api_key.get_secret_value() == "secret-key"

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


def test_hosted_deployment_settings_normalize_and_project_models() -> None:
    """Hosted deployment settings should normalize input and build auth and limiter settings."""
    settings = FollowUpBossHostedDeploymentSettings.model_validate(
        {
            "issuer_url": "https://issuer.example.com",
            "resource_server_url": "https://mcp.example.com/mcp",
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
async def test_postgres_hosted_token_verifier_hashes_tokens_and_returns_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
    monkeypatch.setattr(
        "followupboss_mcp.hosted_reference.psycopg.AsyncConnection.connect",
        factory.connect,
    )
    verifier = PostgresHostedTokenVerifier(
        SecretStr("postgresql://app:secret@db.example.com:5432/fub"),
        time_provider=lambda: 123,
    )

    identity = await verifier.verify_token("  hosted-token  ")
    missing_identity = await verifier.verify_token("missing-token")

    assert identity is not None
    assert identity.tenant_id == "tenant-1"
    assert identity.scopes == ("followupboss:mcp",)
    assert identity.credential_id == "credential-1"
    assert missing_identity is None
    assert factory.connection_strings == [
        "postgresql://app:secret@db.example.com:5432/fub",
        "postgresql://app:secret@db.example.com:5432/fub",
    ]
    assert factory.execute_calls[0][1] == (hash_hosted_bearer_token("hosted-token"), 123)


@pytest.mark.asyncio
async def test_postgres_aws_tenant_store_resolves_tenant_with_string_system_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
    monkeypatch.setattr(
        "followupboss_mcp.hosted_reference.psycopg.AsyncConnection.connect",
        factory.connect,
    )
    secret_store = FakeSecretStore(
        ReferenceHostedSecretPayload.model_validate({"api_key": "secret-key"})
    )
    store = PostgresAwsTenantStore(
        SecretStr("postgresql://app:secret@db.example.com:5432/fub"),
        secret_store=secret_store,
    )

    resolved = await store.resolve_tenant("tenant-1")

    assert resolved.tenant.tenant_slug == "tenant-one"
    assert resolved.credential.system_name == "Managed System"
    assert resolved.credential.api_key is not None
    assert resolved.credential.api_key.get_secret_value() == "secret-key"
    assert secret_store.secret_refs == ["followupboss/prod/tenants/tenant-1/credential-1"]
    assert factory.connection_strings == [
        "postgresql://app:secret@db.example.com:5432/fub",
        "postgresql://app:secret@db.example.com:5432/fub",
    ]


@pytest.mark.asyncio
async def test_postgres_aws_tenant_store_supports_missing_rows_and_optional_system_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
    monkeypatch.setattr(
        "followupboss_mcp.hosted_reference.psycopg.AsyncConnection.connect",
        factory.connect,
    )
    secret_store = FakeSecretStore(
        ReferenceHostedSecretPayload.model_validate({"access_token": "oauth-token"})
    )
    store = PostgresAwsTenantStore(
        "postgresql://app:secret@db.example.com:5432/fub", secret_store=secret_store
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
async def test_postgres_aws_tenant_store_wraps_database_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The PostgreSQL and AWS-backed tenant store should map database failures to safe errors."""
    tenant_factory = FakeConnectionFactory([RuntimeError("db down")])
    monkeypatch.setattr(
        "followupboss_mcp.hosted_reference.psycopg.AsyncConnection.connect",
        tenant_factory.connect,
    )
    tenant_store = PostgresAwsTenantStore(
        "postgresql://app:secret@db.example.com:5432/fub",
        secret_store=FakeSecretStore(
            ReferenceHostedSecretPayload.model_validate({"api_key": "secret-key"})
        ),
    )
    with pytest.raises(TenantStoreUnavailableError, match="Tenant store is unavailable."):
        await tenant_store.get_tenant("tenant-1")

    credential_factory = FakeConnectionFactory([RuntimeError("db down")])
    monkeypatch.setattr(
        "followupboss_mcp.hosted_reference.psycopg.AsyncConnection.connect",
        credential_factory.connect,
    )
    credential_store = PostgresAwsTenantStore(
        "postgresql://app:secret@db.example.com:5432/fub",
        secret_store=FakeSecretStore(
            ReferenceHostedSecretPayload.model_validate({"api_key": "secret-key"})
        ),
    )
    with pytest.raises(TenantStoreUnavailableError, match="Tenant store is unavailable."):
        await credential_store.get_credential("credential-1")


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
        def __init__(self, database_url: SecretStr, *, secret_store: object) -> None:
            captured["tenant_store"] = {
                "database_url": database_url.get_secret_value(),
                "secret_store": secret_store,
            }

    class FakeRedisBackend:
        def __init__(self, redis_url: SecretStr) -> None:
            captured["redis_backend"] = redis_url.get_secret_value()

    class FakeTokenVerifier:
        def __init__(self, database_url: SecretStr) -> None:
            captured["token_verifier"] = database_url.get_secret_value()

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
    assert captured["token_verifier"] == "postgresql://app:secret@db.example.com:5432/fub"
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


def test_create_reference_hosted_server_loads_hosted_settings_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The hosted factory should load hosted deployment settings from environment variables."""
    captured: dict[str, Any] = {}

    class FakeSecretStore:
        def __init__(self, *, region_name: str, secret_prefix: str) -> None:
            captured["secret_store"] = (region_name, secret_prefix)

    class FakeTenantStore:
        def __init__(self, database_url: SecretStr, *, secret_store: object) -> None:
            captured["tenant_store"] = (database_url.get_secret_value(), secret_store)

    class FakeRedisBackend:
        def __init__(self, redis_url: SecretStr) -> None:
            captured["redis_backend"] = redis_url.get_secret_value()

    class FakeTokenVerifier:
        def __init__(self, database_url: SecretStr) -> None:
            captured["token_verifier"] = database_url.get_secret_value()

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
