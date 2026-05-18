"""Tests for auth, config, logging, and package exports."""

from __future__ import annotations

import base64
import importlib
import io
import logging
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

import followupboss_mcp
from followupboss_mcp.auth import (
    AuthMode,
    BasicAuthStrategy,
    BearerAuthStrategy,
    build_auth_strategy,
    inject_authorization,
)
from followupboss_mcp.config import (
    FollowUpBossServerSettings,
    FollowUpBossSettings,
    FollowUpBossTenantRuntimeDefaults,
    FollowUpBossTenantSettings,
)
from followupboss_mcp.errors import (
    FollowUpBossConfigError,
    TenantCredentialRevokedError,
    TenantStoreError,
)
from followupboss_mcp.logging import (
    configure_logging,
    emit_audit_event,
    redact_headers,
    redact_value,
    tenant_store_error_reason,
)


def test_package_exports() -> None:
    """The package root should expose the documented exports."""
    assert followupboss_mcp.__version__ == "0.1.0"
    assert "DevelopmentTenantStore" in followupboss_mcp.__all__
    assert "DevelopmentHostedTokenRecord" in followupboss_mcp.__all__
    assert "DevelopmentHostedTokenVerifier" in followupboss_mcp.__all__
    assert "FollowUpBossAsyncClient" in followupboss_mcp.__all__
    assert "FollowUpBossHostedDeploymentSettings" in followupboss_mcp.__all__
    assert "FollowUpBossServerSettings" in followupboss_mcp.__all__
    assert "FollowUpBossSettings" in followupboss_mcp.__all__
    assert "FollowUpBossTenantRuntimeDefaults" in followupboss_mcp.__all__
    assert "FollowUpBossTenantSettings" in followupboss_mcp.__all__
    assert "AwsSecretsManagerTenantSecretStore" in followupboss_mcp.__all__
    assert "HostedAccessToken" in followupboss_mcp.__all__
    assert "HostedAuthenticatedTenant" in followupboss_mcp.__all__
    assert "HostedAuthSettings" in followupboss_mcp.__all__
    assert "HostedIdentityVerifier" in followupboss_mcp.__all__
    assert "HostedTenantTokenVerifier" in followupboss_mcp.__all__
    assert "HostedVerifiedIdentity" in followupboss_mcp.__all__
    assert "PostgresAwsTenantStore" in followupboss_mcp.__all__
    assert "PostgresHostedTokenVerifier" in followupboss_mcp.__all__
    assert "RedisHostedRateLimitBackend" in followupboss_mcp.__all__
    assert "ReferenceHostedSecretPayload" in followupboss_mcp.__all__
    assert "ResolvedTenantCredentials" in followupboss_mcp.__all__
    assert "SentrySettings" in followupboss_mcp.__all__
    assert "TenantCredentialRecord" in followupboss_mcp.__all__
    assert "TenantCredentialStatus" in followupboss_mcp.__all__
    assert "TenantRecord" in followupboss_mcp.__all__
    assert "TenantStatus" in followupboss_mcp.__all__
    assert "TenantStore" in followupboss_mcp.__all__
    assert "create_reference_hosted_server" in followupboss_mcp.__all__
    assert "get_hosted_access_token" in followupboss_mcp.__all__
    assert "get_hosted_authenticated_tenant" in followupboss_mcp.__all__
    assert "get_hosted_verified_identity" in followupboss_mcp.__all__
    assert "hash_hosted_bearer_token" in followupboss_mcp.__all__


def test_package_lazy_hosted_reference_exports(monkeypatch: pytest.MonkeyPatch) -> None:
    """Hosted reference exports should load lazily from the package root."""
    monkeypatch.delattr(followupboss_mcp, "hash_hosted_bearer_token", raising=False)

    def fake_import_module(module_name: str) -> SimpleNamespace:
        """Return a hosted-reference stand-in for lazy export resolution."""
        assert module_name == "followupboss_mcp.hosted_reference"
        return SimpleNamespace(hash_hosted_bearer_token=lambda token: f"hashed:{token}")

    monkeypatch.setattr(importlib, "import_module", fake_import_module)

    resolved = followupboss_mcp.__getattr__("hash_hosted_bearer_token")

    assert resolved("token") == "hashed:token"
    assert followupboss_mcp.hash_hosted_bearer_token("other") == "hashed:other"
    with pytest.raises(AttributeError, match="missing_export"):
        followupboss_mcp.__getattr__("missing_export")


def test_basic_auth_strategy_and_injection() -> None:
    """API key auth should use HTTP Basic auth with an empty password."""
    strategy = BasicAuthStrategy(api_key="secret-key")
    header = strategy.authorization_header()
    encoded = base64.b64encode(b"secret-key:").decode("ascii")
    assert header == f"Basic {encoded}"
    assert "***redacted***" in repr(strategy)

    headers = inject_authorization({"Accept": "application/json"}, strategy)
    assert headers["Authorization"] == header


def test_bearer_auth_strategy() -> None:
    """OAuth auth should use a bearer token."""
    strategy = BearerAuthStrategy(access_token="token-123")
    assert strategy.authorization_header() == "Bearer token-123"
    assert "***redacted***" in repr(strategy)


def test_build_auth_strategy_success_and_errors() -> None:
    """The auth strategy builder should validate credential presence."""
    assert isinstance(
        build_auth_strategy(auth_mode=AuthMode.API_KEY, api_key="key", access_token=None),
        BasicAuthStrategy,
    )
    assert isinstance(
        build_auth_strategy(auth_mode=AuthMode.OAUTH, api_key=None, access_token="token"),
        BearerAuthStrategy,
    )
    with pytest.raises(FollowUpBossConfigError):
        build_auth_strategy(auth_mode=AuthMode.API_KEY, api_key=None, access_token=None)
    with pytest.raises(FollowUpBossConfigError):
        build_auth_strategy(auth_mode=AuthMode.OAUTH, api_key=None, access_token=None)


def test_tenant_settings_validation_and_normalization(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Tenant settings should normalize and validate auth runtime fields."""
    for key in (
        "FOLLOWUPBOSS_API_KEY",
        "FOLLOWUPBOSS_ACCESS_TOKEN",
        "FOLLOWUPBOSS_AUTH_MODE",
        "FOLLOW_UP_BOSS_API_KEY",
        "FOLLOW_UP_BOSS_ACCESS_TOKEN",
        "FOLLOW_UP_BOSS_AUTH_MODE",
    ):
        monkeypatch.delenv(key, raising=False)

    settings = FollowUpBossTenantSettings.model_validate(
        {
            "api_key": "key",
            "auth_mode": AuthMode.API_KEY,
            "base_url": "https://api.followupboss.com/v1/",
            "timeout_seconds": 12,
            "max_retries": 2,
            "system_key": "system-secret",
        }
    )
    assert str(settings.base_url) == "https://api.followupboss.com/v1"
    assert settings.system_key_value() == "system-secret"
    assert settings.auth_strategy().authorization_header().startswith("Basic ")

    oauth_settings = FollowUpBossTenantSettings.model_validate(
        {"auth_mode": AuthMode.OAUTH, "access_token": "token"}
    )
    assert oauth_settings.auth_strategy().authorization_header() == "Bearer token"

    with pytest.raises(ValidationError):
        FollowUpBossTenantSettings(auth_mode=AuthMode.API_KEY)
    with pytest.raises(ValidationError):
        FollowUpBossTenantSettings(auth_mode=AuthMode.OAUTH)
    with pytest.raises(ValidationError):
        FollowUpBossTenantSettings.model_validate({"api_key": "key", "timeout_seconds": 0})
    with pytest.raises(ValidationError):
        FollowUpBossTenantSettings.model_validate({"api_key": "key", "max_retries": -1})


def test_server_settings_validation_and_normalization() -> None:
    """Server settings should normalize and validate bootstrap-only fields."""
    settings = FollowUpBossServerSettings.model_validate(
        {
            "transport": "streamable-http",
            "host": "0.0.0.0",
            "port": 9000,
            "streamable_http_path": "/mcp/",
            "log_level": "debug",
        }
    )
    assert settings.transport == "streamable-http"
    assert settings.host == "0.0.0.0"
    assert settings.port == 9000
    assert settings.streamable_http_path == "/mcp"
    assert settings.log_level == "DEBUG"

    with pytest.raises(ValidationError):
        FollowUpBossServerSettings.model_validate({"host": "   "})
    with pytest.raises(TypeError, match="log_level must be a string"):
        FollowUpBossServerSettings.model_validate({"log_level": 1})
    with pytest.raises(ValidationError):
        FollowUpBossServerSettings.model_validate({"port": 0})
    with pytest.raises(ValidationError):
        FollowUpBossServerSettings.model_validate({"log_level": "verbose"})
    with pytest.raises(ValidationError):
        FollowUpBossServerSettings.model_validate({"streamable_http_path": "mcp"})


def test_tenant_runtime_defaults_validation_and_normalization() -> None:
    """Hosted runtime defaults should normalize and validate shared HTTP fields."""
    defaults = FollowUpBossTenantRuntimeDefaults.model_validate(
        {
            "base_url": "https://api.followupboss.com/v1/",
            "timeout_seconds": 15,
            "max_retries": 4,
        }
    )

    assert str(defaults.base_url) == "https://api.followupboss.com/v1"
    assert defaults.timeout_seconds == 15
    assert defaults.max_retries == 4

    with pytest.raises(ValidationError):
        FollowUpBossTenantRuntimeDefaults.model_validate({"timeout_seconds": 0})
    with pytest.raises(ValidationError):
        FollowUpBossTenantRuntimeDefaults.model_validate({"max_retries": -1})


def test_composite_settings_project_split_models(monkeypatch: pytest.MonkeyPatch) -> None:
    """The legacy composite settings should project into split server and tenant models."""
    for key in (
        "FOLLOWUPBOSS_AUTH_MODE",
        "FOLLOWUPBOSS_API_KEY",
        "FOLLOWUPBOSS_ACCESS_TOKEN",
        "FOLLOWUPBOSS_SYSTEM_NAME",
        "FOLLOWUPBOSS_SYSTEM_KEY",
        "FOLLOWUPBOSS_X_SYSTEM",
        "FOLLOWUPBOSS_X_SYSTEM_KEY",
        "FOLLOW_UP_BOSS_AUTH_MODE",
        "FOLLOW_UP_BOSS_API_KEY",
        "FOLLOW_UP_BOSS_ACCESS_TOKEN",
        "FOLLOW_UP_BOSS_SYSTEM_NAME",
        "FOLLOW_UP_BOSS_SYSTEM_KEY",
        "FOLLOW_UP_BOSS_X_SYSTEM",
        "FOLLOW_UP_BOSS_X_SYSTEM_KEY",
    ):
        monkeypatch.delenv(key, raising=False)

    settings = FollowUpBossSettings.model_validate(
        {
            "api_key": "key",
            "transport": "streamable-http",
            "host": "0.0.0.0",
            "port": 9001,
            "streamable_http_path": "/tenant/",
            "log_level": "debug",
            "timeout_seconds": 12,
            "max_retries": 2,
        }
    )

    server_settings = settings.server_settings()
    tenant_settings = settings.tenant_settings()
    tenant_runtime_defaults = settings.tenant_runtime_defaults()

    assert server_settings.transport == "streamable-http"
    assert server_settings.host == "0.0.0.0"
    assert server_settings.port == 9001
    assert server_settings.streamable_http_path == "/tenant"
    assert server_settings.log_level == "DEBUG"
    assert tenant_settings.max_retries == 2
    assert tenant_settings.timeout_seconds == 12
    assert "log_level" not in tenant_settings.model_dump()
    assert "host" not in tenant_settings.model_dump()
    assert tenant_settings.system_key_value() is None
    assert tenant_runtime_defaults.max_retries == 2
    assert tenant_runtime_defaults.timeout_seconds == 12
    assert "api_key" not in tenant_runtime_defaults.model_dump()
    assert "auth_mode" not in tenant_runtime_defaults.model_dump()


def test_composite_settings_validate_bootstrap_fields() -> None:
    """Composite settings should validate mirrored server bootstrap fields."""
    with pytest.raises(ValidationError):
        FollowUpBossSettings.model_validate({"api_key": "key", "host": "   "})
    with pytest.raises(ValidationError):
        FollowUpBossSettings.model_validate({"api_key": "key", "port": 0})
    with pytest.raises(ValidationError):
        FollowUpBossSettings.model_validate({"api_key": "key", "streamable_http_path": "mcp"})
    with pytest.raises(TypeError, match="log_level must be a string"):
        FollowUpBossSettings.model_validate({"api_key": "key", "log_level": 1})
    with pytest.raises(
        ValidationError,
        match="log_level must be one of DEBUG, INFO, WARNING, ERROR, CRITICAL.",
    ):
        FollowUpBossSettings.model_validate({"api_key": "key", "log_level": "verbose"})


def test_tenant_settings_support_follow_up_boss_env_aliases(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Legacy `FOLLOW_UP_BOSS_*` environment variables should still load settings."""
    for key in (
        "FOLLOWUPBOSS_AUTH_MODE",
        "FOLLOWUPBOSS_API_KEY",
        "FOLLOWUPBOSS_ACCESS_TOKEN",
        "FOLLOWUPBOSS_SYSTEM_NAME",
        "FOLLOWUPBOSS_SYSTEM_KEY",
        "FOLLOW_UP_BOSS_AUTH_MODE",
        "FOLLOW_UP_BOSS_API_KEY",
        "FOLLOW_UP_BOSS_ACCESS_TOKEN",
        "FOLLOW_UP_BOSS_X_SYSTEM",
        "FOLLOW_UP_BOSS_X_SYSTEM_KEY",
    ):
        monkeypatch.delenv(key, raising=False)

    monkeypatch.setenv("FOLLOW_UP_BOSS_AUTH_MODE", "api_key")
    monkeypatch.setenv("FOLLOW_UP_BOSS_API_KEY", "legacy-key")
    monkeypatch.setenv("FOLLOW_UP_BOSS_X_SYSTEM", "Legacy System")
    monkeypatch.setenv("FOLLOW_UP_BOSS_X_SYSTEM_KEY", "legacy-system-secret")

    settings = FollowUpBossTenantSettings()
    assert settings.auth_mode is AuthMode.API_KEY
    assert settings.api_key is not None
    assert settings.api_key.get_secret_value() == "legacy-key"
    assert settings.system_name == "Legacy System"
    assert settings.system_key_value() == "legacy-system-secret"

    monkeypatch.setenv("FOLLOW_UP_BOSS_AUTH_MODE", "oauth")
    monkeypatch.delenv("FOLLOW_UP_BOSS_API_KEY", raising=False)
    monkeypatch.setenv("FOLLOW_UP_BOSS_ACCESS_TOKEN", "legacy-token")

    oauth_settings = FollowUpBossTenantSettings()
    assert oauth_settings.auth_mode is AuthMode.OAUTH
    assert oauth_settings.access_token is not None
    assert oauth_settings.access_token.get_secret_value() == "legacy-token"


def test_server_settings_support_follow_up_boss_env_aliases(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Legacy server-side environment aliases should still load bootstrap settings."""
    for key in (
        "FOLLOWUPBOSS_TRANSPORT",
        "FOLLOWUPBOSS_HOST",
        "FOLLOWUPBOSS_PORT",
        "FOLLOWUPBOSS_STREAMABLE_HTTP_PATH",
        "FOLLOWUPBOSS_LOG_LEVEL",
        "FOLLOW_UP_BOSS_TRANSPORT",
        "FOLLOW_UP_BOSS_HOST",
        "FOLLOW_UP_BOSS_PORT",
        "FOLLOW_UP_BOSS_MCP_PATH",
        "FOLLOW_UP_BOSS_LOG_LEVEL",
    ):
        monkeypatch.delenv(key, raising=False)

    monkeypatch.setenv("FOLLOW_UP_BOSS_TRANSPORT", "streamable-http")
    monkeypatch.setenv("FOLLOW_UP_BOSS_HOST", "0.0.0.0")
    monkeypatch.setenv("FOLLOW_UP_BOSS_PORT", "9002")
    monkeypatch.setenv("FOLLOW_UP_BOSS_MCP_PATH", "/tenant/")
    monkeypatch.setenv("FOLLOW_UP_BOSS_LOG_LEVEL", "warning")

    settings = FollowUpBossServerSettings()
    assert settings.transport == "streamable-http"
    assert settings.host == "0.0.0.0"
    assert settings.port == 9002
    assert settings.streamable_http_path == "/tenant"
    assert settings.log_level == "WARNING"


def test_tenant_runtime_defaults_support_follow_up_boss_env_aliases(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Legacy runtime-default environment aliases should still load settings."""
    for key in (
        "FOLLOWUPBOSS_BASE_URL",
        "FOLLOWUPBOSS_TIMEOUT_SECONDS",
        "FOLLOWUPBOSS_MAX_RETRIES",
        "FOLLOW_UP_BOSS_BASE_URL",
        "FOLLOW_UP_BOSS_TIMEOUT_SECONDS",
        "FOLLOW_UP_BOSS_MAX_RETRIES",
    ):
        monkeypatch.delenv(key, raising=False)

    monkeypatch.setenv("FOLLOW_UP_BOSS_BASE_URL", "https://api.example.com/v1/")
    monkeypatch.setenv("FOLLOW_UP_BOSS_TIMEOUT_SECONDS", "7")
    monkeypatch.setenv("FOLLOW_UP_BOSS_MAX_RETRIES", "5")

    defaults = FollowUpBossTenantRuntimeDefaults()
    assert str(defaults.base_url) == "https://api.example.com/v1"
    assert defaults.timeout_seconds == 7
    assert defaults.max_retries == 5


def test_redaction_helpers_and_logger_configuration() -> None:
    """Sensitive values should be redacted and logging should reuse handlers."""
    logger = logging.getLogger("followupboss_mcp")
    logger.handlers.clear()
    configured = configure_logging("INFO")
    assert configured.handlers
    assert configured.propagate is False

    second = configure_logging("DEBUG")
    assert second is configured

    headers = {
        "Authorization": "top-secret",
        "X-System-Key": "sys-secret",
        "Accept": "application/json",
    }
    assert redact_headers(headers) == {
        "Authorization": "***redacted***",
        "X-System-Key": "***redacted***",
        "Accept": "application/json",
    }
    assert redact_value(
        {
            "Authorization": "a",
            "items": [{"X-System-Key": "b"}, {"token": "secret-token"}],
            "currentUser": {
                "apiKey": "secret-api-key",
                "algoliaKey": "secret-algolia-key",
                "callingCapabilityToken": "secret-calling-token",
                "user_hash": "secret-hash",
            },
            "error": "Runtime failed token=super-secret-token with Bearer oauth-secret",
            "next_token": "page-token",
            "ok": 1,
        }
    ) == {
        "Authorization": "***redacted***",
        "items": [
            {"X-System-Key": "***redacted***"},
            {"token": "***redacted***"},
        ],
        "currentUser": {
            "apiKey": "***redacted***",
            "algoliaKey": "***redacted***",
            "callingCapabilityToken": "***redacted***",
            "user_hash": "***redacted***",
        },
        "error": "Runtime failed token=***redacted*** with Bearer ***redacted***",
        "next_token": "page-token",
        "ok": 1,
    }
    assert redact_value(["x", {"y": "z"}]) == ["x", {"y": "z"}]

    audit_stream = io.StringIO()
    audit_logger = logging.getLogger("followupboss_mcp_test_logging")
    audit_logger.handlers.clear()
    audit_logger.setLevel("INFO")
    audit_logger.propagate = False
    audit_logger.addHandler(logging.StreamHandler(audit_stream))
    emit_audit_event(
        audit_logger,
        event="tenant_resolution_failed",
        fields={
            "tenant_id": "tenant-1",
            "token": "super-secret-token",
        },
    )
    audit_output = audit_stream.getvalue()
    assert "AUDIT " in audit_output
    assert '"event": "tenant_resolution_failed"' in audit_output
    assert '"tenant_id": "tenant-1"' in audit_output
    assert "super-secret-token" not in audit_output
    assert "***redacted***" in audit_output
    emit_audit_event(audit_logger, event="tenant_resolution_succeeded")
    audit_output = audit_stream.getvalue()
    assert '"event": "tenant_resolution_succeeded"' in audit_output

    assert tenant_store_error_reason(TenantCredentialRevokedError()) == "credential_revoked"
    assert tenant_store_error_reason(TenantStoreError()) == "tenant_store_error"
