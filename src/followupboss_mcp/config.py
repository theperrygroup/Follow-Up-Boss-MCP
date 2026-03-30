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


class FollowUpBossSettings(BaseSettings):
    """Environment-backed application settings."""

    model_config = SettingsConfigDict(
        env_prefix="FOLLOWUPBOSS_",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )

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
    log_level: LogLevel = Field(
        default=cast(LogLevel, DEFAULT_LOG_LEVEL),
        validation_alias=_settings_env_aliases(
            "FOLLOWUPBOSS_LOG_LEVEL",
            "FOLLOW_UP_BOSS_LOG_LEVEL",
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

    @model_validator(mode="after")
    def _validate_auth_mode(self) -> FollowUpBossSettings:
        """Ensure credentials match the chosen auth mode."""
        if self.auth_mode is AuthMode.API_KEY and self.api_key is None:
            raise ValueError("FOLLOWUPBOSS_API_KEY must be provided for api_key auth.")
        if self.auth_mode is AuthMode.OAUTH and self.access_token is None:
            raise ValueError("FOLLOWUPBOSS_ACCESS_TOKEN must be provided for oauth auth.")
        return self

    def auth_strategy(self) -> AuthStrategy:
        """Return the configured authentication strategy."""
        return build_auth_strategy(
            auth_mode=self.auth_mode,
            api_key=self.api_key.get_secret_value() if self.api_key is not None else None,
            access_token=self.access_token.get_secret_value()
            if self.access_token is not None
            else None,
        )

    def system_key_value(self) -> str | None:
        """Return the raw system key, if configured."""
        if self.system_key is None:
            return None
        return self.system_key.get_secret_value()
