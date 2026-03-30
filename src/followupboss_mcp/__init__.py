"""Follow Up Boss MCP package."""

from followupboss_mcp.config import (
    FollowUpBossServerSettings,
    FollowUpBossSettings,
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
    "FollowUpBossServerSettings",
    "FollowUpBossSettings",
    "FollowUpBossTenantSettings",
    "HostedAccessToken",
    "HostedAuthenticatedTenant",
    "HostedAuthSettings",
    "HostedIdentityVerifier",
    "HostedTenantTokenVerifier",
    "HostedVerifiedIdentity",
    "ResolvedTenantCredentials",
    "TenantCredentialRecord",
    "TenantCredentialStatus",
    "TenantRecord",
    "TenantStatus",
    "TenantStore",
    "get_hosted_access_token",
    "get_hosted_authenticated_tenant",
    "get_hosted_verified_identity",
]

__version__ = "0.1.0"
