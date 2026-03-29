"""Calls service."""

from __future__ import annotations

from followupboss_mcp.http_client import FollowUpBossClientProtocol
from followupboss_mcp.models.calls import (
    CallListRequest,
    CallRecord,
    CreateCallRequest,
    UpdateCallRequest,
)
from followupboss_mcp.pagination import PageResult, parse_pagination_metadata


class CallsService:
    """Typed call operations."""

    def __init__(self, client: FollowUpBossClientProtocol) -> None:
        """Initialize the service.

        Args:
            client: The shared Follow Up Boss HTTP client protocol.
        """
        self._client = client

    async def list_calls(self, request: CallListRequest | None = None) -> PageResult[CallRecord]:
        """List calls.

        Args:
            request: Optional call collection filters.

        Returns:
            A paginated call result set.

        Raises:
            ValueError: If the API returns an unexpected payload shape.
        """
        query = request.to_query_params() if request is not None else None
        payload = await self._client.request_json("GET", "/calls", params=query)
        if not isinstance(payload, dict):
            raise ValueError("Unexpected calls response.")
        items_raw = payload.get("calls", [])
        if not isinstance(items_raw, list):
            raise ValueError("Unexpected calls response.")
        items = [CallRecord.model_validate(item) for item in items_raw if isinstance(item, dict)]
        metadata = parse_pagination_metadata(payload, item_count=len(items))
        return PageResult(items=items, metadata=metadata)

    async def get_call(self, call_id: int) -> CallRecord:
        """Fetch a call by ID.

        Args:
            call_id: The Follow Up Boss call identifier.

        Returns:
            The typed call record returned by Follow Up Boss.
        """
        payload = await self._client.request_json("GET", f"/calls/{call_id}")
        return CallRecord.model_validate(payload)

    async def create_call(self, request: CreateCallRequest) -> CallRecord:
        """Create a call.

        Args:
            request: The typed call creation request.

        Returns:
            The created call record.
        """
        payload = request.model_dump(mode="json", by_alias=True, exclude_none=True)
        response = await self._client.request_json("POST", "/calls", json_body=payload)
        return CallRecord.model_validate(response)

    async def update_call(self, call_id: int, request: UpdateCallRequest) -> CallRecord:
        """Update a call.

        Args:
            call_id: The Follow Up Boss call identifier.
            request: The typed call update request.

        Returns:
            The updated call record.
        """
        payload = request.model_dump(mode="json", by_alias=True, exclude_none=True)
        response = await self._client.request_json("PUT", f"/calls/{call_id}", json_body=payload)
        return CallRecord.model_validate(response)
