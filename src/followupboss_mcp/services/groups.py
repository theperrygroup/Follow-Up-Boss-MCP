"""Groups service."""

from __future__ import annotations

from followupboss_mcp.http_client import FollowUpBossClientProtocol
from followupboss_mcp.models.groups import (
    CreateGroupRequest,
    GroupListRequest,
    GroupRecord,
    UpdateGroupRequest,
)
from followupboss_mcp.pagination import PageResult, parse_pagination_metadata


class GroupsService:
    """Typed group operations."""

    def __init__(self, client: FollowUpBossClientProtocol) -> None:
        """Initialize the service.

        Args:
            client: The shared Follow Up Boss HTTP client protocol.
        """
        self._client = client

    async def list_groups(self, request: GroupListRequest | None = None) -> PageResult[GroupRecord]:
        """List groups.

        Args:
            request: Optional group collection filters.

        Returns:
            A paginated group result set.

        Raises:
            ValueError: If the API returns an unexpected payload shape.
        """
        return await self._list_group_collection("/groups", request=request)

    async def list_round_robin_groups(
        self,
        request: GroupListRequest | None = None,
    ) -> PageResult[GroupRecord]:
        """List groups with round-robin details.

        Args:
            request: Optional round-robin group collection filters.

        Returns:
            A paginated group result set including round-robin metadata.

        Raises:
            ValueError: If the API returns an unexpected payload shape.
        """
        return await self._list_group_collection("/groups/roundRobin", request=request)

    async def get_group(self, group_id: int) -> GroupRecord:
        """Fetch a group by ID.

        Args:
            group_id: The Follow Up Boss group identifier.

        Returns:
            The typed group record returned by Follow Up Boss.
        """
        payload = await self._client.request_json("GET", f"/groups/{group_id}")
        return GroupRecord.model_validate(payload)

    async def create_group(self, request: CreateGroupRequest) -> GroupRecord:
        """Create a group.

        Args:
            request: The typed group creation request.

        Returns:
            The created group record.
        """
        payload = request.model_dump(mode="json", by_alias=True, exclude_none=True)
        response = await self._client.request_json("POST", "/groups", json_body=payload)
        return GroupRecord.model_validate(response)

    async def update_group(self, group_id: int, request: UpdateGroupRequest) -> GroupRecord:
        """Update a group.

        Args:
            group_id: The Follow Up Boss group identifier.
            request: The typed group update request.

        Returns:
            The updated group record.
        """
        payload = request.model_dump(mode="json", by_alias=True, exclude_none=True)
        response = await self._client.request_json("PUT", f"/groups/{group_id}", json_body=payload)
        return GroupRecord.model_validate(response)

    async def delete_group(self, group_id: int) -> None:
        """Delete a group.

        Args:
            group_id: The Follow Up Boss group identifier.
        """
        await self._client.request_json("DELETE", f"/groups/{group_id}")

    async def _list_group_collection(
        self,
        path: str,
        *,
        request: GroupListRequest | None = None,
    ) -> PageResult[GroupRecord]:
        """List one of the group collection endpoints.

        Args:
            path: The Follow Up Boss group collection endpoint path.
            request: Optional collection filters.

        Returns:
            A paginated group result set.

        Raises:
            ValueError: If the API returns an unexpected payload shape.
        """
        query = request.to_query_params() if request is not None else None
        payload = await self._client.request_json("GET", path, params=query)
        if not isinstance(payload, dict):
            raise ValueError("Unexpected groups response.")
        items_raw = payload.get("groups", [])
        if not isinstance(items_raw, list):
            raise ValueError("Unexpected groups response.")
        items = [GroupRecord.model_validate(item) for item in items_raw if isinstance(item, dict)]
        metadata = parse_pagination_metadata(payload, item_count=len(items))
        return PageResult(items=items, metadata=metadata)
