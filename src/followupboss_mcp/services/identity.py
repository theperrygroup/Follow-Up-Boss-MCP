"""Identity service."""

from __future__ import annotations

from dataclasses import dataclass

from followupboss_mcp.http_client import FollowUpBossClientProtocol
from followupboss_mcp.models.identity import IdentityResponse


@dataclass(frozen=True)
class HealthCheckResult:
    """Health check result based on the `/identity` endpoint."""

    identity: IdentityResponse
    ok: bool


class IdentityService:
    """Typed identity operations."""

    def __init__(self, client: FollowUpBossClientProtocol) -> None:
        """Initialize the service."""
        self._client = client

    async def get_identity(self) -> IdentityResponse:
        """Return identity information for the authenticated caller."""
        payload = await self._client.request_json("GET", "/identity")
        return IdentityResponse.model_validate(payload)

    async def health_check(self) -> HealthCheckResult:
        """Return a health check result backed by `/identity`."""
        identity = await self.get_identity()
        return HealthCheckResult(identity=identity, ok=True)
