"""Pipelines service."""

from __future__ import annotations

from followupboss_mcp.http_client import FollowUpBossClientProtocol
from followupboss_mcp.models.pipelines import (
    CreatePipelineRequest,
    PipelineListRequest,
    PipelineRecord,
    UpdatePipelineRequest,
)
from followupboss_mcp.pagination import PageResult, parse_pagination_metadata


class PipelinesService:
    """Typed pipeline operations."""

    def __init__(self, client: FollowUpBossClientProtocol) -> None:
        """Initialize the service.

        Args:
            client: The shared Follow Up Boss HTTP client protocol.
        """
        self._client = client

    async def list_pipelines(
        self,
        request: PipelineListRequest | None = None,
    ) -> PageResult[PipelineRecord]:
        """List pipelines.

        Args:
            request: Optional pipeline collection filters.

        Returns:
            A paginated pipeline result set.

        Raises:
            ValueError: If the API returns an unexpected payload shape.
        """
        query = request.to_query_params() if request is not None else None
        payload = await self._client.request_json("GET", "/pipelines", params=query)
        if not isinstance(payload, dict):
            raise ValueError("Unexpected pipelines response.")
        items_raw = payload.get("pipelines", [])
        if not isinstance(items_raw, list):
            raise ValueError("Unexpected pipelines response.")
        items = [
            PipelineRecord.model_validate(item) for item in items_raw if isinstance(item, dict)
        ]
        metadata = parse_pagination_metadata(payload, item_count=len(items))
        return PageResult(items=items, metadata=metadata)

    async def get_pipeline(self, pipeline_id: int) -> PipelineRecord:
        """Fetch a pipeline by ID.

        Args:
            pipeline_id: The Follow Up Boss pipeline identifier.

        Returns:
            The typed pipeline record returned by Follow Up Boss.
        """
        payload = await self._client.request_json("GET", f"/pipelines/{pipeline_id}")
        return PipelineRecord.model_validate(payload)

    async def create_pipeline(self, request: CreatePipelineRequest) -> PipelineRecord:
        """Create a pipeline.

        Args:
            request: The typed pipeline creation request.

        Returns:
            The created pipeline record.
        """
        payload = request.model_dump(mode="json", by_alias=True, exclude_none=True)
        response = await self._client.request_json("POST", "/pipelines", json_body=payload)
        return PipelineRecord.model_validate(response)

    async def update_pipeline(
        self,
        pipeline_id: int,
        request: UpdatePipelineRequest,
    ) -> PipelineRecord:
        """Update a pipeline.

        Args:
            pipeline_id: The Follow Up Boss pipeline identifier.
            request: The typed pipeline update request.

        Returns:
            The updated pipeline record.
        """
        payload = request.model_dump(mode="json", by_alias=True, exclude_none=True)
        response = await self._client.request_json(
            "PUT", f"/pipelines/{pipeline_id}", json_body=payload
        )
        return PipelineRecord.model_validate(response)

    async def delete_pipeline(self, pipeline_id: int) -> None:
        """Delete a pipeline.

        Args:
            pipeline_id: The Follow Up Boss pipeline identifier.
        """
        await self._client.request_json("DELETE", f"/pipelines/{pipeline_id}")
