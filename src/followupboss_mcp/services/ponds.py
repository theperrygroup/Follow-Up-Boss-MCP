"""Ponds service."""

from __future__ import annotations

from followupboss_mcp.http_client import FollowUpBossClientProtocol
from followupboss_mcp.models.ponds import (
    CreatePondRequest,
    DeletePondRequest,
    PondListRequest,
    PondRecord,
    UpdatePondRequest,
)
from followupboss_mcp.pagination import PageResult, parse_pagination_metadata


class PondsService:
    """Typed pond operations."""

    def __init__(self, client: FollowUpBossClientProtocol) -> None:
        """Initialize the service.

        Args:
            client: The shared Follow Up Boss HTTP client protocol.
        """
        self._client = client

    async def list_ponds(self, request: PondListRequest | None = None) -> PageResult[PondRecord]:
        """List ponds.

        Args:
            request: Optional pond collection filters.

        Returns:
            A paginated pond result set.

        Raises:
            ValueError: If the API returns an unexpected payload shape.
        """
        query = request.to_query_params() if request is not None else None
        payload = await self._client.request_json("GET", "/ponds", params=query)
        if not isinstance(payload, dict):
            raise ValueError("Unexpected ponds response.")
        items_raw = payload.get("ponds", [])
        if not isinstance(items_raw, list):
            raise ValueError("Unexpected ponds response.")
        items = [PondRecord.model_validate(item) for item in items_raw if isinstance(item, dict)]
        metadata = parse_pagination_metadata(payload, item_count=len(items))
        return PageResult(items=items, metadata=metadata)

    async def get_pond(self, pond_id: int) -> PondRecord:
        """Fetch a pond by ID.

        Args:
            pond_id: The Follow Up Boss pond identifier.

        Returns:
            The typed pond record returned by Follow Up Boss.
        """
        payload = await self._client.request_json("GET", f"/ponds/{pond_id}")
        return PondRecord.model_validate(payload)

    async def create_pond(self, request: CreatePondRequest) -> PondRecord:
        """Create a pond.

        Args:
            request: The typed pond creation request.

        Returns:
            The created pond record.
        """
        payload = request.model_dump(mode="json", by_alias=True, exclude_none=True)
        response = await self._client.request_json("POST", "/ponds", json_body=payload)
        return PondRecord.model_validate(response)

    async def update_pond(self, pond_id: int, request: UpdatePondRequest) -> PondRecord:
        """Update a pond.

        Args:
            pond_id: The Follow Up Boss pond identifier.
            request: The typed pond update request.

        Returns:
            The updated pond record.
        """
        payload = request.model_dump(mode="json", by_alias=True, exclude_none=True)
        response = await self._client.request_json("PUT", f"/ponds/{pond_id}", json_body=payload)
        return PondRecord.model_validate(response)

    async def delete_pond(self, pond_id: int, request: DeletePondRequest) -> None:
        """Delete a pond.

        Args:
            pond_id: The Follow Up Boss pond identifier.
            request: The typed pond deletion query parameters.
        """
        await self._client.request_json(
            "DELETE",
            f"/ponds/{pond_id}",
            params=request.to_query_params(),
        )
