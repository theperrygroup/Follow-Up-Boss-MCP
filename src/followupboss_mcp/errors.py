"""Error hierarchy for the Follow Up Boss client and MCP server."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


class FollowUpBossError(Exception):
    """Base class for Follow Up Boss related failures."""


class FollowUpBossConfigError(FollowUpBossError):
    """Raised for invalid configuration."""


class FollowUpBossHTTPError(FollowUpBossError):
    """Raised for HTTP failures returned by Follow Up Boss."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int,
        payload: Mapping[str, Any] | None = None,
    ) -> None:
        """Initialize the exception."""
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.payload = dict(payload) if payload is not None else None


class FollowUpBossAuthError(FollowUpBossHTTPError):
    """Raised when authentication fails."""


class FollowUpBossForbiddenError(FollowUpBossHTTPError):
    """Raised when the caller does not have access."""


class FollowUpBossNotFoundError(FollowUpBossHTTPError):
    """Raised when a resource is not found."""


class FollowUpBossValidationError(FollowUpBossHTTPError):
    """Raised when the API rejects a request as invalid."""


class FollowUpBossRateLimitError(FollowUpBossHTTPError):
    """Raised when the API rate limits a request."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int,
        retry_after_seconds: float | None,
        payload: Mapping[str, Any] | None = None,
    ) -> None:
        """Initialize the exception."""
        super().__init__(message, status_code=status_code, payload=payload)
        self.retry_after_seconds = retry_after_seconds


class FollowUpBossRetryableServerError(FollowUpBossHTTPError):
    """Raised when a retryable server error is exhausted."""


class FollowUpBossWebhookSignatureError(FollowUpBossError):
    """Raised when webhook signature verification fails."""


class TenantStoreError(FollowUpBossError):
    """Base class for tenant-store related failures."""


class TenantNotFoundError(TenantStoreError):
    """Raised when a tenant record cannot be resolved."""


class TenantDisabledError(TenantStoreError):
    """Raised when a tenant exists but is disabled."""


class TenantCredentialNotFoundError(TenantStoreError):
    """Raised when a tenant credential record cannot be resolved."""


class TenantCredentialRevokedError(TenantStoreError):
    """Raised when a tenant credential exists but is revoked."""
