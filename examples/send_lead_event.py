"""Send a canonical Follow Up Boss lead event."""

from __future__ import annotations

import asyncio
import json

from followupboss_mcp.config import FollowUpBossSettings
from followupboss_mcp.http_client import FollowUpBossAsyncClient
from followupboss_mcp.models.events import CreateEventRequest, EventPersonInput
from followupboss_mcp.services.events import EventsService


async def main() -> None:
    """Run the example."""
    settings = FollowUpBossSettings()
    request = CreateEventRequest(
        source="Example Website",
        system=settings.system_name or "Example Website",
        type="Inquiry",
        message="Interested in learning more about this property.",
        person=EventPersonInput(
            first_name="Example",
            last_name="Lead",
            emails=[{"type": "home", "value": "example.lead@example.com"}],
            phones=[{"type": "mobile", "value": "(555) 111-2222"}],
        ),
    )
    async with FollowUpBossAsyncClient(settings) as client:
        service = EventsService(client)
        event = await service.send_event(request)
    print(json.dumps(event.model_dump(mode="json", by_alias=True), indent=2))


if __name__ == "__main__":
    asyncio.run(main())
