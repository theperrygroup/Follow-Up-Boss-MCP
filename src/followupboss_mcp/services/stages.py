"""Stages service."""

from __future__ import annotations

from followupboss_mcp.http_client import FollowUpBossClientProtocol
from followupboss_mcp.models.stages import (
    CreateStageRequest,
    DeleteStageRequest,
    StageListRequest,
    StageRecord,
    UpdateStageRequest,
)
from followupboss_mcp.pagination import PageResult, parse_pagination_metadata


class StagesService:
    """Typed stage operations."""

    def __init__(self, client: FollowUpBossClientProtocol) -> None:
        """Initialize the service.

        Args:
            client: The shared Follow Up Boss HTTP client protocol.
        """
        self._client = client

    async def list_stages(self, request: StageListRequest | None = None) -> PageResult[StageRecord]:
        """List stages.

        Args:
            request: Optional stage collection filters.

        Returns:
            A paginated stage result set.

        Raises:
            ValueError: If the API returns an unexpected payload shape.
        """
        query = request.to_query_params() if request is not None else None
        payload = await self._client.request_json("GET", "/stages", params=query)
        if not isinstance(payload, dict):
            raise ValueError("Unexpected stages response.")
        items_raw = payload.get("stages", [])
        if not isinstance(items_raw, list):
            raise ValueError("Unexpected stages response.")
        items = [StageRecord.model_validate(item) for item in items_raw if isinstance(item, dict)]
        metadata = parse_pagination_metadata(payload, item_count=len(items))
        return PageResult(items=items, metadata=metadata)

    async def get_stage(self, stage_id: int) -> StageRecord:
        """Fetch a stage by ID.

        Args:
            stage_id: The Follow Up Boss stage identifier.

        Returns:
            The typed stage record returned by Follow Up Boss.
        """
        payload = await self._client.request_json("GET", f"/stages/{stage_id}")
        return StageRecord.model_validate(payload)

    async def create_stage(self, request: CreateStageRequest) -> StageRecord:
        """Create a stage.

        Args:
            request: The typed stage creation request.

        Returns:
            The created stage record.
        """
        payload = request.model_dump(mode="json", by_alias=True, exclude_none=True)
        response = await self._client.request_json("POST", "/stages", json_body=payload)
        return StageRecord.model_validate(response)

    async def update_stage(self, stage_id: int, request: UpdateStageRequest) -> StageRecord:
        """Update a stage.

        Args:
            stage_id: The Follow Up Boss stage identifier.
            request: The typed stage update request.

        Returns:
            The updated stage record.
        """
        payload = request.model_dump(mode="json", by_alias=True, exclude_none=True)
        response = await self._client.request_json("PUT", f"/stages/{stage_id}", json_body=payload)
        return StageRecord.model_validate(response)

    async def delete_stage(self, stage_id: int, request: DeleteStageRequest) -> None:
        """Delete a stage.

        Args:
            stage_id: The Follow Up Boss stage identifier.
            request: The typed stage deletion query parameters.
        """
        await self._client.request_json(
            "DELETE",
            f"/stages/{stage_id}",
            params=request.to_query_params(),
        )
