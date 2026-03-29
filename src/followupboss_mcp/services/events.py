"""Events service."""

from __future__ import annotations

from followupboss_mcp.http_client import FollowUpBossClientProtocol
from followupboss_mcp.models.events import CreateEventRequest, EventRecord, EventSearchRequest
from followupboss_mcp.pagination import PageResult, parse_pagination_metadata
from followupboss_mcp.services.custom_fields import CustomFieldsService


class EventsService:
    """Typed event operations."""

    def __init__(self, client: FollowUpBossClientProtocol) -> None:
        """Initialize the service."""
        self._client = client
        self._custom_fields = CustomFieldsService(client)

    async def search_events(
        self, request: EventSearchRequest | None = None
    ) -> PageResult[EventRecord]:
        """Search events."""
        query = request.to_query_params() if request is not None else None
        payload = await self._client.request_json("GET", "/events", params=query)
        if not isinstance(payload, dict):
            raise ValueError("Unexpected events response.")
        items_raw = payload.get("events", [])
        if not isinstance(items_raw, list):
            raise ValueError("Unexpected events response.")
        items = [EventRecord.model_validate(item) for item in items_raw if isinstance(item, dict)]
        metadata = parse_pagination_metadata(payload, item_count=len(items))
        return PageResult(items=items, metadata=metadata)

    async def get_event(self, event_id: int) -> EventRecord:
        """Fetch an event by ID.

        Args:
            event_id: The Follow Up Boss event identifier.

        Returns:
            The typed event record returned by Follow Up Boss.
        """
        payload = await self._client.request_json("GET", f"/events/{event_id}")
        return EventRecord.model_validate(payload)

    async def send_event(self, request: CreateEventRequest) -> EventRecord:
        """Send a lead or lead activity event."""
        payload = request.model_dump(by_alias=True, exclude_none=True)
        person_payload = payload.get("person")
        if isinstance(person_payload, dict) and request.person.custom_fields is not None:
            person_payload.update(
                self._custom_fields.validate_custom_field_names(request.person.custom_fields)
            )
            person_payload.pop("custom_fields", None)
        response = await self._client.request_json("POST", "/events", json_body=payload)
        return EventRecord.model_validate(response)
