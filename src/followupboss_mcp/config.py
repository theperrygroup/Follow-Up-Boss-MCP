"""Configuration models."""

from __future__ import annotations

from typing import Literal, cast

from pydantic import (
    AliasChoices,
    AnyHttpUrl,
    Field,
    SecretStr,
    TypeAdapter,
    field_validator,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict

from followupboss_mcp.auth import AuthMode, AuthStrategy, build_auth_strategy
from followupboss_mcp.constants import (
    DEFAULT_BASE_URL,
    DEFAULT_LOG_LEVEL,
    DEFAULT_MAX_RETRIES,
    DEFAULT_TIMEOUT_SECONDS,
)

type LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
type TransportMode = Literal["stdio", "streamable-http"]


def _default_base_url() -> AnyHttpUrl:
    """Return the validated default API base URL."""
    return TypeAdapter(AnyHttpUrl).validate_python(DEFAULT_BASE_URL)


def _settings_env_aliases(canonical_name: str, *legacy_names: str) -> AliasChoices:
    """Return accepted environment variable aliases for one setting field.

    Args:
        canonical_name: The documented canonical environment variable name.
        *legacy_names: Optional backward-compatible or local alternative names.

    Returns:
        The alias choices accepted by `pydantic-settings`.
    """
    return AliasChoices(canonical_name, *legacy_names)


def _normalize_optional_string(value: object) -> object:
    """Normalize optional string settings from environment variables.

    Args:
        value: The raw settings value supplied by pydantic-settings.

    Returns:
        `None` for blank strings, a stripped string for populated strings, or
        the original value for pydantic to validate.
    """
    if isinstance(value, str):
        normalized = value.strip()
        return normalized or None
    return value


def _validate_sample_rate(value: float | None, *, field_name: str) -> float | None:
    """Validate an optional Sentry sample-rate value.

    Args:
        value: The candidate sample rate.
        field_name: The public field name used in the validation error.

    Returns:
        The validated sample rate.

    Raises:
        ValueError: If the value is outside Sentry's accepted `0.0` to `1.0`
            range.
    """
    if value is None:
        return None
    if value < 0 or value > 1:
        raise ValueError(f"{field_name} must be between 0.0 and 1.0.")
    return value


class SentrySettings(BaseSettings):
    """Environment-backed Sentry runtime settings."""

    model_config = SettingsConfigDict(
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )

    dsn: str | None = Field(
        default=None,
        validation_alias=_settings_env_aliases("SENTRY_DSN"),
    )
    environment: str = Field(
        default="local",
        validation_alias=_settings_env_aliases("SENTRY_ENVIRONMENT"),
    )
    release: str | None = Field(
        default=None,
        validation_alias=_settings_env_aliases("SENTRY_RELEASE"),
    )
    error_sample_rate: float = Field(
        default=1.0,
        validation_alias=_settings_env_aliases("SENTRY_SAMPLE_RATE"),
    )
    traces_sample_rate: float | None = Field(
        default=None,
        validation_alias=_settings_env_aliases("SENTRY_TRACES_SAMPLE_RATE"),
    )
    profiles_sample_rate: float | None = Field(
        default=None,
        validation_alias=_settings_env_aliases("SENTRY_PROFILES_SAMPLE_RATE"),
    )
    enable_logs: bool = Field(
        default=False,
        validation_alias=_settings_env_aliases("SENTRY_ENABLE_LOGS"),
    )
    debug: bool = Field(
        default=False,
        validation_alias=_settings_env_aliases("SENTRY_DEBUG"),
    )

    @field_validator("dsn", "release", mode="before")
    @classmethod
    def _normalize_optional_text(cls, value: object) -> object:
        """Normalize optional text settings."""
        return _normalize_optional_string(value)

    @field_validator("traces_sample_rate", "profiles_sample_rate", mode="before")
    @classmethod
    def _normalize_optional_sample_rate(cls, value: object) -> object:
        """Normalize optional sample-rate settings before float validation."""
        return _normalize_optional_string(value)

    @field_validator("environment")
    @classmethod
    def _validate_environment(cls, value: str) -> str:
        """Require a non-empty Sentry environment name."""
        normalized = value.strip()
        if not normalized:
            raise ValueError("environment must not be empty.")
        return normalized

    @field_validator("error_sample_rate")
    @classmethod
    def _validate_error_sample_rate(cls, value: float) -> float:
        """Validate the error-event sample rate."""
        return cast(float, _validate_sample_rate(value, field_name="error_sample_rate"))

    @field_validator("traces_sample_rate")
    @classmethod
    def _validate_traces_sample_rate(cls, value: float | None) -> float | None:
        """Validate the optional trace sample rate."""
        return _validate_sample_rate(value, field_name="traces_sample_rate")

    @field_validator("profiles_sample_rate")
    @classmethod
    def _validate_profiles_sample_rate(cls, value: float | None) -> float | None:
        """Validate the optional profiling sample rate."""
        return _validate_sample_rate(value, field_name="profiles_sample_rate")

    @property
    def enabled(self) -> bool:
        """Return whether Sentry should be initialized."""
        return self.dsn is not None


class FollowUpBossServerSettings(BaseSettings):
    """Environment-backed server-only runtime settings."""

    model_config = SettingsConfigDict(
        env_prefix="FOLLOWUPBOSS_",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )

    transport: TransportMode = Field(
        default="stdio",
        validation_alias=_settings_env_aliases(
            "FOLLOWUPBOSS_TRANSPORT",
            "FOLLOW_UP_BOSS_TRANSPORT",
        ),
    )
    host: str = Field(
        default="127.0.0.1",
        validation_alias=_settings_env_aliases(
            "FOLLOWUPBOSS_HOST",
            "FOLLOW_UP_BOSS_HOST",
        ),
    )
    port: int = Field(
        default=8000,
        validation_alias=_settings_env_aliases(
            "FOLLOWUPBOSS_PORT",
            "FOLLOW_UP_BOSS_PORT",
        ),
    )
    streamable_http_path: str = Field(
        default="/mcp",
        validation_alias=_settings_env_aliases(
            "FOLLOWUPBOSS_STREAMABLE_HTTP_PATH",
            "FOLLOW_UP_BOSS_STREAMABLE_HTTP_PATH",
            "FOLLOWUPBOSS_MCP_PATH",
            "FOLLOW_UP_BOSS_MCP_PATH",
        ),
    )
    log_level: LogLevel = Field(
        default=cast(LogLevel, DEFAULT_LOG_LEVEL),
        validation_alias=_settings_env_aliases(
            "FOLLOWUPBOSS_LOG_LEVEL",
            "FOLLOW_UP_BOSS_LOG_LEVEL",
        ),
    )

    @field_validator("host")
    @classmethod
    def _validate_host(cls, value: str) -> str:
        """Require a non-empty host value."""
        if not value.strip():
            raise ValueError("host must not be empty.")
        return value

    @field_validator("port")
    @classmethod
    def _validate_port(cls, value: int) -> int:
        """Require a valid TCP port."""
        if value <= 0 or value > 65535:
            raise ValueError("port must be between 1 and 65535.")
        return value

    @field_validator("streamable_http_path")
    @classmethod
    def _validate_streamable_http_path(cls, value: str) -> str:
        """Require an absolute HTTP mount path."""
        if not value.startswith("/"):
            raise ValueError("streamable_http_path must start with '/'.")
        return value.rstrip("/") or "/"

    @field_validator("log_level", mode="before")
    @classmethod
    def _normalize_log_level(cls, value: object) -> LogLevel:
        """Normalize log levels to uppercase and validate them."""
        if not isinstance(value, str):
            raise TypeError("log_level must be a string.")
        normalized = value.upper()
        if normalized not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError("log_level must be one of DEBUG, INFO, WARNING, ERROR, CRITICAL.")
        return cast(LogLevel, normalized)


class FollowUpBossTenantRuntimeDefaults(BaseSettings):
    """Environment-backed non-secret HTTP-client defaults for tenant runtimes."""

    model_config = SettingsConfigDict(
        env_prefix="FOLLOWUPBOSS_",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )

    base_url: AnyHttpUrl = Field(
        default_factory=_default_base_url,
        validation_alias=_settings_env_aliases(
            "FOLLOWUPBOSS_BASE_URL",
            "FOLLOW_UP_BOSS_BASE_URL",
        ),
    )
    timeout_seconds: float = Field(
        default=DEFAULT_TIMEOUT_SECONDS,
        validation_alias=_settings_env_aliases(
            "FOLLOWUPBOSS_TIMEOUT_SECONDS",
            "FOLLOW_UP_BOSS_TIMEOUT_SECONDS",
        ),
    )
    max_retries: int = Field(
        default=DEFAULT_MAX_RETRIES,
        validation_alias=_settings_env_aliases(
            "FOLLOWUPBOSS_MAX_RETRIES",
            "FOLLOW_UP_BOSS_MAX_RETRIES",
        ),
    )
    allow_external_text_message_logs: bool = Field(
        default=False,
        validation_alias=_settings_env_aliases(
            "FOLLOWUPBOSS_ALLOW_EXTERNAL_TEXT_MESSAGE_LOGS",
            "FOLLOW_UP_BOSS_ALLOW_EXTERNAL_TEXT_MESSAGE_LOGS",
        ),
    )

    @field_validator("base_url", mode="before")
    @classmethod
    def _normalize_base_url(cls, value: object) -> object:
        """Strip trailing slashes from the configured base URL."""
        if isinstance(value, str):
            return value.rstrip("/")
        return value

    @field_validator("timeout_seconds")
    @classmethod
    def _validate_timeout(cls, value: float) -> float:
        """Require a positive timeout."""
        if value <= 0:
            raise ValueError("timeout_seconds must be greater than zero.")
        return value

    @field_validator("max_retries")
    @classmethod
    def _validate_retries(cls, value: int) -> int:
        """Require a non-negative retry count."""
        if value < 0:
            raise ValueError("max_retries must be greater than or equal to zero.")
        return value

    @classmethod
    def builtin_defaults(cls) -> FollowUpBossTenantRuntimeDefaults:
        """Return validated built-in defaults without consulting environment sources.

        Returns:
            A runtime-defaults model seeded only from repository constants.
        """
        return cls.model_validate(
            {
                "base_url": _default_base_url(),
                "timeout_seconds": DEFAULT_TIMEOUT_SECONDS,
                "max_retries": DEFAULT_MAX_RETRIES,
                "allow_external_text_message_logs": False,
            }
        )


class FollowUpBossTenantSettings(FollowUpBossTenantRuntimeDefaults):
    """Environment-backed credentialed settings for one tenant runtime."""

    auth_mode: AuthMode = Field(
        default=AuthMode.API_KEY,
        validation_alias=_settings_env_aliases(
            "FOLLOWUPBOSS_AUTH_MODE",
            "FOLLOW_UP_BOSS_AUTH_MODE",
        ),
    )
    api_key: SecretStr | None = Field(
        default=None,
        validation_alias=_settings_env_aliases(
            "FOLLOWUPBOSS_API_KEY",
            "FOLLOW_UP_BOSS_API_KEY",
        ),
    )
    access_token: SecretStr | None = Field(
        default=None,
        validation_alias=_settings_env_aliases(
            "FOLLOWUPBOSS_ACCESS_TOKEN",
            "FOLLOW_UP_BOSS_ACCESS_TOKEN",
        ),
    )
    system_name: str | None = Field(
        default=None,
        validation_alias=_settings_env_aliases(
            "FOLLOWUPBOSS_SYSTEM_NAME",
            "FOLLOW_UP_BOSS_SYSTEM_NAME",
            "FOLLOWUPBOSS_X_SYSTEM",
            "FOLLOW_UP_BOSS_X_SYSTEM",
        ),
    )
    system_key: SecretStr | None = Field(
        default=None,
        validation_alias=_settings_env_aliases(
            "FOLLOWUPBOSS_SYSTEM_KEY",
            "FOLLOW_UP_BOSS_SYSTEM_KEY",
            "FOLLOWUPBOSS_X_SYSTEM_KEY",
            "FOLLOW_UP_BOSS_X_SYSTEM_KEY",
        ),
    )

    @model_validator(mode="after")
    def _validate_auth_mode(self) -> FollowUpBossTenantSettings:
        """Ensure credentials match the chosen auth mode."""
        if self.auth_mode is AuthMode.API_KEY and self.api_key is None:
            raise ValueError("FOLLOWUPBOSS_API_KEY must be provided for api_key auth.")
        if self.auth_mode is AuthMode.OAUTH and self.access_token is None:
            raise ValueError("FOLLOWUPBOSS_ACCESS_TOKEN must be provided for oauth auth.")
        return self

    def auth_strategy(self) -> AuthStrategy:
        """Return the configured authentication strategy.

        Returns:
            The auth strategy derived from the configured tenant credentials.
        """
        return build_auth_strategy(
            auth_mode=self.auth_mode,
            api_key=self.api_key.get_secret_value() if self.api_key is not None else None,
            access_token=self.access_token.get_secret_value()
            if self.access_token is not None
            else None,
        )

    def system_key_value(self) -> str | None:
        """Return the raw system key, if configured.

        Returns:
            The unwrapped system key when one is configured, otherwise `None`.
        """
        if self.system_key is None:
            return None
        return self.system_key.get_secret_value()

    def tenant_runtime_defaults(self) -> FollowUpBossTenantRuntimeDefaults:
        """Project the credentialed settings into non-secret runtime defaults.

        Returns:
            A runtime-defaults model containing only the shared HTTP-client
            configuration needed for hosted tenant construction.
        """
        return FollowUpBossTenantRuntimeDefaults.model_validate(
            {
                "base_url": self.base_url,
                "timeout_seconds": self.timeout_seconds,
                "max_retries": self.max_retries,
                "allow_external_text_message_logs": self.allow_external_text_message_logs,
            }
        )


class FollowUpBossSettings(FollowUpBossTenantSettings):
    """Backward-compatible composite settings for single-tenant local development."""

    transport: TransportMode = Field(
        default="stdio",
        validation_alias=_settings_env_aliases(
            "FOLLOWUPBOSS_TRANSPORT",
            "FOLLOW_UP_BOSS_TRANSPORT",
        ),
    )
    host: str = Field(
        default="127.0.0.1",
        validation_alias=_settings_env_aliases(
            "FOLLOWUPBOSS_HOST",
            "FOLLOW_UP_BOSS_HOST",
        ),
    )
    port: int = Field(
        default=8000,
        validation_alias=_settings_env_aliases(
            "FOLLOWUPBOSS_PORT",
            "FOLLOW_UP_BOSS_PORT",
        ),
    )
    streamable_http_path: str = Field(
        default="/mcp",
        validation_alias=_settings_env_aliases(
            "FOLLOWUPBOSS_STREAMABLE_HTTP_PATH",
            "FOLLOW_UP_BOSS_STREAMABLE_HTTP_PATH",
            "FOLLOWUPBOSS_MCP_PATH",
            "FOLLOW_UP_BOSS_MCP_PATH",
        ),
    )
    log_level: LogLevel = Field(
        default=cast(LogLevel, DEFAULT_LOG_LEVEL),
        validation_alias=_settings_env_aliases(
            "FOLLOWUPBOSS_LOG_LEVEL",
            "FOLLOW_UP_BOSS_LOG_LEVEL",
        ),
    )

    @field_validator("host")
    @classmethod
    def _validate_host(cls, value: str) -> str:
        """Require a non-empty host value."""
        if not value.strip():
            raise ValueError("host must not be empty.")
        return value

    @field_validator("port")
    @classmethod
    def _validate_port(cls, value: int) -> int:
        """Require a valid TCP port."""
        if value <= 0 or value > 65535:
            raise ValueError("port must be between 1 and 65535.")
        return value

    @field_validator("streamable_http_path")
    @classmethod
    def _validate_streamable_http_path(cls, value: str) -> str:
        """Require an absolute HTTP mount path."""
        if not value.startswith("/"):
            raise ValueError("streamable_http_path must start with '/'.")
        return value.rstrip("/") or "/"

    @field_validator("log_level", mode="before")
    @classmethod
    def _normalize_log_level(cls, value: object) -> LogLevel:
        """Normalize log levels to uppercase and validate them."""
        if not isinstance(value, str):
            raise TypeError("log_level must be a string.")
        normalized = value.upper()
        if normalized not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError("log_level must be one of DEBUG, INFO, WARNING, ERROR, CRITICAL.")
        return cast(LogLevel, normalized)

    def server_settings(self) -> FollowUpBossServerSettings:
        """Project the composite settings into server-only settings.

        Returns:
            A server-only settings object that excludes tenant credentials.
        """
        return FollowUpBossServerSettings.model_validate(
            {
                "transport": self.transport,
                "host": self.host,
                "port": self.port,
                "streamable_http_path": self.streamable_http_path,
                "log_level": self.log_level,
            }
        )

    def tenant_settings(self) -> FollowUpBossTenantSettings:
        """Project the composite settings into tenant-only settings.

        Returns:
            A tenant runtime settings object without server bootstrap fields.
        """
        return FollowUpBossTenantSettings.model_validate(
            {
                "auth_mode": self.auth_mode,
                "api_key": self.api_key,
                "access_token": self.access_token,
                "system_name": self.system_name,
                "system_key": self.system_key,
                "base_url": self.base_url,
                "timeout_seconds": self.timeout_seconds,
                "max_retries": self.max_retries,
                "allow_external_text_message_logs": self.allow_external_text_message_logs,
            }
        )
