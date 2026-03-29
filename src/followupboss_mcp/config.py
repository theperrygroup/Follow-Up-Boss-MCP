"""Configuration models."""

from __future__ import annotations

from typing import Literal, cast

from pydantic import AnyHttpUrl, Field, SecretStr, TypeAdapter, field_validator, model_validator
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


class FollowUpBossSettings(BaseSettings):
    """Environment-backed application settings."""

    model_config = SettingsConfigDict(
        env_prefix="FOLLOWUPBOSS_",
        case_sensitive=False,
        extra="ignore",
    )

    auth_mode: AuthMode = AuthMode.API_KEY
    api_key: SecretStr | None = None
    access_token: SecretStr | None = None
    system_name: str | None = None
    system_key: SecretStr | None = None
    base_url: AnyHttpUrl = Field(default_factory=_default_base_url)
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    max_retries: int = DEFAULT_MAX_RETRIES
    log_level: LogLevel = cast(LogLevel, DEFAULT_LOG_LEVEL)

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
