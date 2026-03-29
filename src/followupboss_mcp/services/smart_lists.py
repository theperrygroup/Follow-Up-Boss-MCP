"""Smart lists service."""

from __future__ import annotations

from followupboss_mcp.http_client import FollowUpBossClientProtocol
from followupboss_mcp.models.smart_lists import SmartListListRequest, SmartListRecord
from followupboss_mcp.pagination import PageResult, parse_pagination_metadata


class SmartListsService:
    """Typed smart list operations."""

    def __init__(self, client: FollowUpBossClientProtocol) -> None:
        """Initialize the service.

        Args:
            client: The shared Follow Up Boss HTTP client protocol.
        """
        self._client = client

    async def list_smart_lists(
        self,
        request: SmartListListRequest | None = None,
    ) -> PageResult[SmartListRecord]:
        """List smart lists.

        Args:
            request: Optional smart list collection filters.

        Returns:
            A paginated smart list result set.

        Raises:
            ValueError: If the API returns an unexpected payload shape.
        """
        query = request.to_query_params() if request is not None else None
        payload = await self._client.request_json("GET", "/smartLists", params=query)
        if not isinstance(payload, dict):
            raise ValueError("Unexpected smart lists response.")
        items_raw = payload.get("smartlists", [])
        if not isinstance(items_raw, list):
            raise ValueError("Unexpected smart lists response.")
        items = [
            SmartListRecord.model_validate(item) for item in items_raw if isinstance(item, dict)
        ]
        metadata = parse_pagination_metadata(payload, item_count=len(items))
        return PageResult(items=items, metadata=metadata)

    async def get_smart_list(self, smart_list_id: int) -> SmartListRecord:
        """Fetch a smart list by ID.

        Args:
            smart_list_id: The Follow Up Boss smart list identifier.

        Returns:
            The typed smart list record returned by Follow Up Boss.
        """
        payload = await self._client.request_json("GET", f"/smartLists/{smart_list_id}")
        return SmartListRecord.model_validate(payload)
