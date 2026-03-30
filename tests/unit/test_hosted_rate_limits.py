"""Focused unit tests for hosted endpoint rate limiting."""

from __future__ import annotations

from followupboss_mcp.hosted_auth import (
    HostedAccessToken,
    HostedAuthenticatedTenant,
    HostedVerifiedIdentity,
)
from followupboss_mcp.hosted_rate_limits import (
    HostedEndpointRateLimiter,
    HostedRateLimitKey,
    HostedRateLimitSettings,
    InMemoryHostedRateLimitBackend,
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
