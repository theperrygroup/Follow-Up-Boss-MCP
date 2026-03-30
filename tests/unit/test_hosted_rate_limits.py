"""Focused unit tests for hosted endpoint rate limiting."""

from __future__ import annotations

import pytest
from pydantic import ValidationError
from starlette.types import Message, Receive, Scope, Send

from followupboss_mcp.hosted_auth import (
    HostedAccessToken,
    HostedAuthenticatedTenant,
    HostedVerifiedIdentity,
)
from followupboss_mcp.hosted_rate_limits import (
    HostedEndpointRateLimiter,
    HostedRateLimitDecision,
    HostedRateLimitKey,
    HostedRateLimitMiddleware,
    HostedRateLimitSettings,
    InMemoryHostedRateLimitBackend,
    _client_ip_from_scope,
    _rate_limit_fields,
)


def _access_token(
    *,
    tenant_id: str = "tenant-1",
    client_id: str = "portal-app",
) -> HostedAccessToken:
    """Build a representative hosted access token for rate-limit tests.

    Args:
        tenant_id: The hosted tenant identifier carried by the token.
        client_id: The hosted OAuth client identifier carried by the token.

    Returns:
        A hosted access token with safe tenant context.
    """
    return HostedAccessToken.from_verified_identity(
        token="dev-token",
        identity=HostedVerifiedIdentity.model_validate(
            {
                "tenant_id": tenant_id,
                "subject": f"user-for-{tenant_id}",
                "client_id": client_id,
                "credential_id": f"credential-for-{tenant_id}",
            }
        ),
        tenant=HostedAuthenticatedTenant.model_validate(
            {
                "tenant_id": tenant_id,
                "tenant_slug": f"{tenant_id}-slug",
                "display_name": f"Display {tenant_id}",
                "credential_id": f"credential-for-{tenant_id}",
            }
        ),
    )


def _http_scope(
    *,
    scope_type: str = "http",
    client: tuple[str, int] | None = ("203.0.113.10", 50000),
) -> Scope:
    """Build a minimal ASGI scope for middleware tests.

    Args:
        scope_type: The ASGI scope type to simulate.
        client: Optional `(host, port)` client tuple.

    Returns:
        A minimal ASGI scope dictionary.
    """
    scope: Scope = {
        "type": scope_type,
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/mcp",
        "raw_path": b"/mcp",
        "query_string": b"",
        "headers": [],
        "server": ("testserver", 80),
    }
    if client is not None:
        scope["client"] = client
    return scope


async def _empty_receive() -> Message:
    """Return one empty ASGI HTTP request event.

    Returns:
        One terminal `http.request` ASGI message.
    """
    return {"type": "http.request", "body": b"", "more_body": False}


async def test_in_memory_hosted_rate_limit_backend_isolates_budget_keys() -> None:
    """The in-memory backend should keep budgets isolated per stable key."""
    current_time = [100.0]
    backend = InMemoryHostedRateLimitBackend(clock=lambda: current_time[0])
    first_key = HostedRateLimitKey(tenant_id="tenant-1", client_id="portal-app")
    second_tenant_key = HostedRateLimitKey(tenant_id="tenant-2", client_id="portal-app")
    second_client_key = HostedRateLimitKey(tenant_id="tenant-1", client_id="other-client")

    first_decision = await backend.consume(first_key, limit=1, window_seconds=60.0)
    second_decision = await backend.consume(first_key, limit=1, window_seconds=60.0)
    second_tenant_decision = await backend.consume(
        second_tenant_key,
        limit=1,
        window_seconds=60.0,
    )
    second_client_decision = await backend.consume(
        second_client_key,
        limit=1,
        window_seconds=60.0,
    )

    assert first_decision.allowed is True
    assert first_decision.remaining_requests == 0
    assert second_decision.allowed is False
    assert second_decision.remaining_requests == 0
    assert second_decision.retry_after_seconds == 60.0
    assert second_tenant_decision.allowed is True
    assert second_client_decision.allowed is True

    current_time[0] = 161.0
    reset_decision = await backend.consume(first_key, limit=1, window_seconds=60.0)
    assert reset_decision.allowed is True


def test_hosted_endpoint_rate_limiter_optionally_adds_client_ip_to_budget_key() -> None:
    """The limiter should ignore client IP unless the setting enables it."""
    access_token = _access_token()
    limiter_without_ip = HostedEndpointRateLimiter(
        settings=HostedRateLimitSettings(
            requests_per_window=1,
            window_seconds=60.0,
            include_client_ip=False,
        )
    )
    limiter_with_ip = HostedEndpointRateLimiter(
        settings=HostedRateLimitSettings(
            requests_per_window=1,
            window_seconds=60.0,
            include_client_ip=True,
        )
    )

    key_without_ip = limiter_without_ip.key_for_access_token(
        access_token,
        client_ip="203.0.113.10",
    )
    key_with_ip = limiter_with_ip.key_for_access_token(
        access_token,
        client_ip="203.0.113.10",
    )

    assert key_without_ip == HostedRateLimitKey(
        tenant_id="tenant-1",
        client_id="portal-app",
        client_ip=None,
    )
    assert key_with_ip == HostedRateLimitKey(
        tenant_id="tenant-1",
        client_id="portal-app",
        client_ip="203.0.113.10",
    )


def test_hosted_rate_limit_settings_validate_positive_values() -> None:
    """Hosted rate-limit settings should reject non-positive budgets and windows."""
    with pytest.raises(ValidationError):
        HostedRateLimitSettings.model_validate({"requests_per_window": 0})
    with pytest.raises(ValidationError):
        HostedRateLimitSettings.model_validate({"window_seconds": 0})


def test_rate_limit_fields_and_client_ip_helpers_cover_edge_cases() -> None:
    """Rate-limit helper functions should preserve non-secret caller metadata safely."""
    key = HostedRateLimitKey(
        tenant_id="tenant-1",
        client_id="portal-app",
        client_ip="203.0.113.10",
    )
    fields = _rate_limit_fields(
        key,
        settings=HostedRateLimitSettings(
            requests_per_window=2,
            window_seconds=30.0,
            include_client_ip=True,
        ),
    )

    assert fields["client_ip"] == "203.0.113.10"
    assert _client_ip_from_scope(_http_scope(client=("203.0.113.10", 50000))) == "203.0.113.10"
    assert _client_ip_from_scope(_http_scope(client=("", 50000))) is None
    assert _client_ip_from_scope(_http_scope(client=None)) is None
    invalid_client_scope = _http_scope()
    invalid_client_scope["client"] = ()
    assert _client_ip_from_scope(invalid_client_scope) is None


@pytest.mark.asyncio
async def test_hosted_rate_limit_middleware_skips_non_http_scopes() -> None:
    """Hosted rate-limit middleware should bypass non-HTTP traffic unchanged."""
    calls: list[str] = []

    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        """Record the incoming ASGI scope type."""
        del receive, send
        calls.append(scope["type"])

    middleware = HostedRateLimitMiddleware(
        app,
        rate_limiter=HostedEndpointRateLimiter(),
    )

    async def send(_: Message) -> None:
        """Ignore emitted ASGI messages for middleware bypass tests."""
        return None

    await middleware(_http_scope(scope_type="websocket"), _empty_receive, send)

    assert calls == ["websocket"]


@pytest.mark.asyncio
async def test_hosted_rate_limit_middleware_omits_retry_after_without_backend_hint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Denied hosted requests should omit `Retry-After` when the backend has no hint."""

    class DenyWithoutRetryBackend:
        """Backend stub that denies requests without a retry hint."""

        async def consume(
            self,
            key: HostedRateLimitKey,
            *,
            limit: int,
            window_seconds: float,
        ) -> HostedRateLimitDecision:
            """Return a denied decision without a retry hint."""
            del key, limit, window_seconds
            return HostedRateLimitDecision(
                allowed=False,
                remaining_requests=0,
                retry_after_seconds=None,
            )

    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        """Fail if the denied request reaches the downstream app."""
        del scope, receive, send
        raise AssertionError("Denied requests should not reach the downstream app.")

    sent_messages: list[Message] = []

    async def send(message: Message) -> None:
        """Capture ASGI messages emitted by the middleware."""
        sent_messages.append(message)

    monkeypatch.setattr(
        "followupboss_mcp.hosted_rate_limits.get_hosted_access_token",
        lambda: _access_token(),
    )
    middleware = HostedRateLimitMiddleware(
        app,
        rate_limiter=HostedEndpointRateLimiter(
            settings=HostedRateLimitSettings(requests_per_window=1, window_seconds=60.0),
            backend=DenyWithoutRetryBackend(),
        ),
    )

    await middleware(_http_scope(), _empty_receive, send)

    response_start = next(
        message for message in sent_messages if message["type"] == "http.response.start"
    )
    response_headers = {
        name.decode("latin-1"): value.decode("latin-1") for name, value in response_start["headers"]
    }
    assert response_start["status"] == 429
    assert "Retry-After" not in response_headers
