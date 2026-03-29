"""Optional live sandbox validation for the identity path."""

from __future__ import annotations

import os

import pytest

from followupboss_mcp.config import FollowUpBossSettings
from followupboss_mcp.http_client import FollowUpBossAsyncClient
from followupboss_mcp.services.identity import IdentityService

pytestmark = [pytest.mark.live]


@pytest.mark.asyncio
async def test_live_identity_health_check() -> None:
    """The live identity path should succeed when explicitly enabled.

    This test is intentionally skipped unless `FOLLOWUPBOSS_RUN_LIVE_TESTS=1`
    is present in the environment. It exercises the same auth and transport
    path used by the normal identity example, but it is never required for the
    default offline suite.
    """
    if os.getenv("FOLLOWUPBOSS_RUN_LIVE_TESTS") != "1":
        pytest.skip("Live Follow Up Boss validation is disabled.")

    settings = FollowUpBossSettings()
    async with FollowUpBossAsyncClient(settings) as client:
        service = IdentityService(client)
        result = await service.health_check()

    assert result.ok is True
    assert result.identity.id is not None
    assert result.identity.id > 0
    assert isinstance(result.identity.name, str)
    assert result.identity.name != ""
