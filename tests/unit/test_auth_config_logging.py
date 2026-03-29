"""Tests for auth, config, logging, and package exports."""

from __future__ import annotations

import base64
import logging

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
from followupboss_mcp.config import FollowUpBossSettings
from followupboss_mcp.errors import FollowUpBossConfigError
from followupboss_mcp.logging import configure_logging, redact_headers, redact_value


def test_package_exports() -> None:
    """The package root should expose the documented exports."""
    assert followupboss_mcp.__version__ == "0.1.0"
    assert "FollowUpBossAsyncClient" in followupboss_mcp.__all__
    assert "FollowUpBossSettings" in followupboss_mcp.__all__


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


def test_settings_validation_and_normalization() -> None:
    """Settings should normalize and validate important fields."""
    settings = FollowUpBossSettings.model_validate(
        {
            "api_key": "key",
            "auth_mode": AuthMode.API_KEY,
            "base_url": "https://api.followupboss.com/v1/",
            "timeout_seconds": 12,
            "max_retries": 2,
            "log_level": "debug",
            "system_key": "system-secret",
        }
    )
    assert str(settings.base_url) == "https://api.followupboss.com/v1"
    assert settings.log_level == "DEBUG"
    assert settings.system_key_value() == "system-secret"
    assert settings.auth_strategy().authorization_header().startswith("Basic ")

    oauth_settings = FollowUpBossSettings.model_validate(
        {"auth_mode": AuthMode.OAUTH, "access_token": "token"}
    )
    assert oauth_settings.auth_strategy().authorization_header() == "Bearer token"

    with pytest.raises(ValidationError):
        FollowUpBossSettings(auth_mode=AuthMode.API_KEY)
    with pytest.raises(ValidationError):
        FollowUpBossSettings(auth_mode=AuthMode.OAUTH)
    with pytest.raises(ValidationError):
        FollowUpBossSettings.model_validate({"api_key": "key", "timeout_seconds": 0})
    with pytest.raises(ValidationError):
        FollowUpBossSettings.model_validate({"api_key": "key", "max_retries": -1})


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
    assert redact_value({"Authorization": "a", "items": [{"X-System-Key": "b"}], "ok": 1}) == {
        "Authorization": "***redacted***",
        "items": [{"X-System-Key": "***redacted***"}],
        "ok": 1,
    }
    assert redact_value(["x", {"y": "z"}]) == ["x", {"y": "z"}]
