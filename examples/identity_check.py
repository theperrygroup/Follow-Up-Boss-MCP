"""Run a Follow Up Boss identity-based health check."""

from __future__ import annotations

import asyncio
import json

from followupboss_mcp.config import FollowUpBossSettings
from followupboss_mcp.http_client import FollowUpBossAsyncClient
from followupboss_mcp.services.identity import IdentityService


async def main() -> None:
    """Run the example."""
    settings = FollowUpBossSettings()
    async with FollowUpBossAsyncClient(settings) as client:
        service = IdentityService(client)
        result = await service.health_check()
    print(
        json.dumps(
            {"ok": result.ok, "identity": result.identity.model_dump(mode="json", by_alias=True)},
            indent=2,
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
