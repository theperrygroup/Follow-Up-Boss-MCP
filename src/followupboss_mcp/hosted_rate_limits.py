"""Hosted endpoint rate limiting and abuse-control helpers."""

from __future__ import annotations

import logging
import math
import time
from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from threading import Lock
from typing import Literal, Protocol, cast

from pydantic import BaseModel, ConfigDict, field_validator
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from followupboss_mcp.hosted_auth import HostedAccessToken, get_hosted_access_token
from followupboss_mcp.logging import emit_audit_event
from followupboss_mcp.observability import capture_sentry_exception

type HostedRateLimitFailureMode = Literal["closed", "open"]

_DEFAULT_REQUESTS_PER_WINDOW = 300
_DEFAULT_WINDOW_SECONDS = 60.0


@dataclass(frozen=True)
class HostedRateLimitKey:
    """Stable budget key for one hosted caller."""

    tenant_id: str
    client_id: str
    client_ip: str | None = None


@dataclass(frozen=True)
class HostedRateLimitDecision:
    """Result of checking one hosted rate-limit budget."""

    allowed: bool
    remaining_requests: int
    retry_after_seconds: float | None = None


class HostedRateLimitSettings(BaseModel):
    """Configuration for hosted endpoint rate limiting."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    requests_per_window: int = _DEFAULT_REQUESTS_PER_WINDOW
    window_seconds: float = _DEFAULT_WINDOW_SECONDS
    include_client_ip: bool = False
    backend_failure_mode: HostedRateLimitFailureMode = "closed"

    @field_validator("requests_per_window")
    @classmethod
    def _validate_requests_per_window(cls, value: int) -> int:
        """Require a positive request budget.

        Args:
            value: The configured number of requests allowed per window.

        Returns:
            The validated request budget.

        Raises:
            ValueError: If the request budget is not positive.
        """
        if value <= 0:
            raise ValueError("requests_per_window must be greater than zero.")
        return value

    @field_validator("window_seconds")
    @classmethod
    def _validate_window_seconds(cls, value: float) -> float:
        """Require a positive window duration.

        Args:
            value: The configured window duration in seconds.

        Returns:
            The validated window duration.

        Raises:
            ValueError: If the window duration is not positive.
        """
        if value <= 0:
            raise ValueError("window_seconds must be greater than zero.")
        return value


class HostedRateLimitBackend(Protocol):
    """Protocol for hosted rate-limit backends."""

    async def consume(
        self,
        key: HostedRateLimitKey,
        *,
        limit: int,
        window_seconds: float,
    ) -> HostedRateLimitDecision:
        """Consume one request from the rate-limit budget.

        Args:
            key: The stable caller budget key.
            limit: Maximum requests allowed within the window.
            window_seconds: Duration of the rolling window in seconds.

        Returns:
            The rate-limit decision for the current request.
        """


class InMemoryHostedRateLimitBackend:
    """Sliding-window in-memory backend for hosted rate limiting."""

    def __init__(self, *, clock: Callable[[], float] | None = None) -> None:
        """Initialize the in-memory rate-limit backend.

        Args:
            clock: Optional monotonic clock used to timestamp requests.
        """
        self._clock = clock or time.monotonic
        self._lock = Lock()
        self._timestamps_by_key: dict[HostedRateLimitKey, deque[float]] = {}

    async def consume(
        self,
        key: HostedRateLimitKey,
        *,
        limit: int,
        window_seconds: float,
    ) -> HostedRateLimitDecision:
        """Consume one request from the in-memory sliding window.

        Args:
            key: The stable caller budget key.
            limit: Maximum requests allowed within the window.
            window_seconds: Duration of the rolling window in seconds.

        Returns:
            The rate-limit decision for the current request.
        """
        now = self._clock()
        oldest_allowed_timestamp = now - window_seconds

        with self._lock:
            timestamps = self._timestamps_by_key.setdefault(key, deque())
            while timestamps and timestamps[0] <= oldest_allowed_timestamp:
                timestamps.popleft()

            if len(timestamps) >= limit:
                retry_after_seconds = max(timestamps[0] + window_seconds - now, 0.0)
                return HostedRateLimitDecision(
                    allowed=False,
                    remaining_requests=0,
                    retry_after_seconds=retry_after_seconds,
                )

            timestamps.append(now)
            return HostedRateLimitDecision(
                allowed=True,
                remaining_requests=max(limit - len(timestamps), 0),
            )


def _rate_limit_fields(
    key: HostedRateLimitKey,
    *,
    settings: HostedRateLimitSettings,
    retry_after_seconds: float | None = None,
) -> dict[str, object]:
    """Build audit fields for one rate-limit decision.

    Args:
        key: The stable caller budget key.
        settings: The active rate-limit configuration.
        retry_after_seconds: Optional retry hint in seconds.

    Returns:
        Non-secret audit fields describing the rate-limit decision.
    """
    fields: dict[str, object] = {
        "tenant_id": key.tenant_id,
        "client_id": key.client_id,
        "requests_per_window": settings.requests_per_window,
        "window_seconds": settings.window_seconds,
        "backend_failure_mode": settings.backend_failure_mode,
    }
    if key.client_ip is not None:
        fields["client_ip"] = key.client_ip
    if retry_after_seconds is not None:
        fields["retry_after_seconds"] = retry_after_seconds
    return fields


def _client_ip_from_scope(scope: Scope) -> str | None:
    """Return the peer IP address captured by ASGI, when available.

    Args:
        scope: The ASGI request scope for the current HTTP request.

    Returns:
        The peer IP address from the ASGI client tuple, or `None` when the
        server does not expose one.
    """
    client = scope.get("client")
    if not isinstance(client, tuple) or len(client) < 1:
        return None
    host = client[0]
    return host if isinstance(host, str) and host else None


class HostedEndpointRateLimiter:
    """Coordinator for hosted endpoint rate limiting."""

    def __init__(
        self,
        *,
        settings: HostedRateLimitSettings | None = None,
        backend: HostedRateLimitBackend | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        """Initialize the hosted endpoint rate limiter.

        Args:
            settings: Optional rate-limit configuration. When omitted, a
                conservative default in-memory budget is used.
            backend: Optional backend that tracks caller budgets.
            logger: Optional logger used for audit events.
        """
        self._settings = settings or HostedRateLimitSettings()
        self._backend = backend or InMemoryHostedRateLimitBackend()
        self._logger = logger

    @property
    def settings(self) -> HostedRateLimitSettings:
        """Return the active hosted rate-limit settings.

        Returns:
            The active rate-limit configuration.
        """
        return self._settings

    @property
    def logger(self) -> logging.Logger | None:
        """Return the logger used for audit events.

        Returns:
            The optional logger configured for audit events.
        """
        return self._logger

    def key_for_access_token(
        self,
        access_token: HostedAccessToken,
        *,
        client_ip: str | None = None,
    ) -> HostedRateLimitKey:
        """Build the stable rate-limit key for one authenticated request.

        Args:
            access_token: The authenticated hosted access token.
            client_ip: Optional peer IP address for the current request.

        Returns:
            The stable caller budget key for the request.
        """
        resolved_client_ip = client_ip if self._settings.include_client_ip else None
        return HostedRateLimitKey(
            tenant_id=access_token.tenant.tenant_id,
            client_id=access_token.client_id,
            client_ip=resolved_client_ip,
        )

    async def check_request(
        self,
        access_token: HostedAccessToken,
        *,
        client_ip: str | None = None,
    ) -> HostedRateLimitDecision:
        """Check whether one authenticated request can proceed.

        Args:
            access_token: The authenticated hosted access token.
            client_ip: Optional peer IP address for the current request.

        Returns:
            The rate-limit decision for the request.
        """
        return await self._backend.consume(
            self.key_for_access_token(access_token, client_ip=client_ip),
            limit=self._settings.requests_per_window,
            window_seconds=self._settings.window_seconds,
        )

    async def aclose(self) -> None:
        """Close the backend when it exposes an async shutdown hook."""
        close = getattr(self._backend, "aclose", None)
        if close is None:
            return
        await cast(Callable[[], Awaitable[None]], close)()


class HostedRateLimitMiddleware:
    """ASGI middleware that enforces hosted request budgets."""

    def __init__(self, app: ASGIApp, *, rate_limiter: HostedEndpointRateLimiter) -> None:
        """Initialize the hosted rate-limit middleware.

        Args:
            app: The downstream ASGI application.
            rate_limiter: The hosted endpoint rate limiter that enforces budgets.
        """
        self.app = app
        self._rate_limiter = rate_limiter

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Enforce the hosted rate-limit budget for the current request.

        Args:
            scope: The ASGI request scope.
            receive: The ASGI receive callable.
            send: The ASGI send callable.
        """
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        access_token = get_hosted_access_token()
        if access_token is None:
            await self.app(scope, receive, send)
            return

        client_ip = _client_ip_from_scope(scope)
        key = self._rate_limiter.key_for_access_token(access_token, client_ip=client_ip)
        try:
            decision = await self._rate_limiter.check_request(access_token, client_ip=client_ip)
        except Exception as exc:  # pragma: no cover - exercised via focused HTTP tests
            capture_sentry_exception(
                exc,
                tags={
                    "component": "hosted_rate_limits",
                    "rate_limit_failure_mode": self._rate_limiter.settings.backend_failure_mode,
                },
                extras=_rate_limit_fields(key, settings=self._rate_limiter.settings),
            )
            emit_audit_event(
                self._rate_limiter.logger,
                event="hosted_rate_limit_backend_failed",
                fields={
                    **_rate_limit_fields(key, settings=self._rate_limiter.settings),
                    "action": (
                        "allow"
                        if self._rate_limiter.settings.backend_failure_mode == "open"
                        else "deny"
                    ),
                    "error_type": type(exc).__name__,
                },
            )
            if self._rate_limiter.settings.backend_failure_mode == "open":
                await self.app(scope, receive, send)
                return

            response = JSONResponse(
                {
                    "error": "temporarily_unavailable",
                    "error_description": "Hosted rate limiting is temporarily unavailable",
                },
                status_code=503,
            )
            response.headers["Retry-After"] = str(
                max(1, math.ceil(self._rate_limiter.settings.window_seconds))
            )
            await response(scope, receive, send)
            return

        if decision.allowed:
            await self.app(scope, receive, send)
            return

        emit_audit_event(
            self._rate_limiter.logger,
            event="hosted_rate_limit_exceeded",
            fields=_rate_limit_fields(
                key,
                settings=self._rate_limiter.settings,
                retry_after_seconds=decision.retry_after_seconds,
            ),
        )
        response = JSONResponse(
            {
                "error": "rate_limited",
                "error_description": "Rate limit exceeded",
            },
            status_code=429,
        )
        if decision.retry_after_seconds is not None:
            response.headers["Retry-After"] = str(max(1, math.ceil(decision.retry_after_seconds)))
        await response(scope, receive, send)
