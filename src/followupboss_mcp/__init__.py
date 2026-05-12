"""Follow Up Boss MCP package."""

import importlib
from typing import Any

from followupboss_mcp.config import (
    FollowUpBossServerSettings,
    FollowUpBossSettings,
    FollowUpBossTenantRuntimeDefaults,
    FollowUpBossTenantSettings,
    SentrySettings,
)
from followupboss_mcp.hosted_auth import (
    DevelopmentHostedTokenRecord,
    DevelopmentHostedTokenVerifier,
    HostedAccessToken,
    HostedAuthenticatedTenant,
    HostedAuthSettings,
    HostedIdentityVerifier,
    HostedTenantTokenVerifier,
    HostedVerifiedIdentity,
    get_hosted_access_token,
    get_hosted_authenticated_tenant,
    get_hosted_verified_identity,
)
from followupboss_mcp.hosted_oauth import (
    FollowUpBossOAuthClient,
    HostedOAuthApplication,
    HostedOAuthSettings,
)
from followupboss_mcp.hosted_rate_limits import (
    HostedEndpointRateLimiter,
    HostedRateLimitDecision,
    HostedRateLimitKey,
    HostedRateLimitSettings,
    InMemoryHostedRateLimitBackend,
)
from followupboss_mcp.http_client import FollowUpBossAsyncClient
from followupboss_mcp.tenant_store import (
    DevelopmentTenantStore,
    ResolvedTenantCredentials,
    TenantCredentialRecord,
    TenantCredentialStatus,
    TenantRecord,
    TenantStatus,
    TenantStore,
)

_HOSTED_REFERENCE_EXPORTS = {
    "AwsSecretsManagerTenantSecretStore",
    "FollowUpBossHostedDeploymentSettings",
    "PostgresAwsTenantStore",
    "PostgresHostedTokenVerifier",
    "RedisHostedRateLimitBackend",
    "ReferenceHostedSecretPayload",
    "create_reference_hosted_server",
    "hash_hosted_bearer_token",
}

__all__ = [
    "DevelopmentTenantStore",
    "DevelopmentHostedTokenRecord",
    "DevelopmentHostedTokenVerifier",
    "FollowUpBossAsyncClient",
    "FollowUpBossHostedDeploymentSettings",
    "FollowUpBossOAuthClient",
    "FollowUpBossServerSettings",
    "FollowUpBossSettings",
    "FollowUpBossTenantRuntimeDefaults",
    "FollowUpBossTenantSettings",
    "AwsSecretsManagerTenantSecretStore",
    "HostedAccessToken",
    "HostedAuthenticatedTenant",
    "HostedAuthSettings",
    "HostedOAuthApplication",
    "HostedOAuthSettings",
    "HostedIdentityVerifier",
    "HostedEndpointRateLimiter",
    "HostedRateLimitDecision",
    "HostedRateLimitKey",
    "HostedRateLimitSettings",
    "HostedTenantTokenVerifier",
    "HostedVerifiedIdentity",
    "InMemoryHostedRateLimitBackend",
    "PostgresAwsTenantStore",
    "PostgresHostedTokenVerifier",
    "RedisHostedRateLimitBackend",
    "ReferenceHostedSecretPayload",
    "ResolvedTenantCredentials",
    "SentrySettings",
    "TenantCredentialRecord",
    "TenantCredentialStatus",
    "TenantRecord",
    "TenantStatus",
    "TenantStore",
    "create_reference_hosted_server",
    "get_hosted_access_token",
    "get_hosted_authenticated_tenant",
    "get_hosted_verified_identity",
    "hash_hosted_bearer_token",
]

__version__ = "0.1.0"


def __getattr__(name: str) -> Any:
    """Lazily load hosted reference exports when package users request them.

    Args:
        name: The package-level attribute name being resolved.

    Returns:
        The requested hosted reference export.

    Raises:
        AttributeError: If `name` is not a known package export.
    """
    if name in _HOSTED_REFERENCE_EXPORTS:
        hosted_reference = importlib.import_module("followupboss_mcp.hosted_reference")
        value = getattr(hosted_reference, name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
