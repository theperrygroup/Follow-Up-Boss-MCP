"""Timeframe service."""

from __future__ import annotations

from followupboss_mcp.http_client import FollowUpBossClientProtocol
from followupboss_mcp.models.timeframes import TimeframeListRequest, TimeframeRecord
from followupboss_mcp.pagination import PageResult, parse_pagination_metadata


class TimeframesService:
    """Typed timeframe operations."""

    def __init__(self, client: FollowUpBossClientProtocol) -> None:
        """Initialize the service.

        Args:
            client: The shared Follow Up Boss HTTP client protocol.
        """
        self._client = client

    async def list_timeframes(
        self,
        request: TimeframeListRequest | None = None,
    ) -> PageResult[TimeframeRecord]:
        """List timeframes.

        Args:
            request: Optional timeframe collection filters.

        Returns:
            A paginated timeframe result set.

        Raises:
            ValueError: If the API returns an unexpected payload shape.
        """
        query = request.to_query_params() if request is not None else None
        payload = await self._client.request_json("GET", "/timeframes", params=query)
        if not isinstance(payload, dict):
            raise ValueError("Unexpected timeframes response.")
        items_raw = payload.get("timeframes", [])
        if not isinstance(items_raw, list):
            raise ValueError("Unexpected timeframes response.")
        items = [
            TimeframeRecord.model_validate(item) for item in items_raw if isinstance(item, dict)
        ]
        metadata = parse_pagination_metadata(payload, item_count=len(items))
        return PageResult(items=items, metadata=metadata)
