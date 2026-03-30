"""Follow Up Boss MCP package."""

from followupboss_mcp.config import (
    FollowUpBossServerSettings,
    FollowUpBossSettings,
    FollowUpBossTenantRuntimeDefaults,
    FollowUpBossTenantSettings,
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
from followupboss_mcp.hosted_rate_limits import (
    HostedEndpointRateLimiter,
    HostedRateLimitDecision,
    HostedRateLimitKey,
    HostedRateLimitSettings,
    InMemoryHostedRateLimitBackend,
)
from followupboss_mcp.hosted_reference import (
    AwsSecretsManagerTenantSecretStore,
    FollowUpBossHostedDeploymentSettings,
    PostgresAwsTenantStore,
    PostgresHostedTokenVerifier,
    RedisHostedRateLimitBackend,
    ReferenceHostedSecretPayload,
    create_reference_hosted_server,
    hash_hosted_bearer_token,
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

__all__ = [
    "DevelopmentTenantStore",
    "DevelopmentHostedTokenRecord",
    "DevelopmentHostedTokenVerifier",
    "FollowUpBossAsyncClient",
    "FollowUpBossHostedDeploymentSettings",
    "FollowUpBossServerSettings",
    "FollowUpBossSettings",
    "FollowUpBossTenantRuntimeDefaults",
    "FollowUpBossTenantSettings",
    "AwsSecretsManagerTenantSecretStore",
    "HostedAccessToken",
    "HostedAuthenticatedTenant",
    "HostedAuthSettings",
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
