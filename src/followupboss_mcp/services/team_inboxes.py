"""Team inbox service."""

from __future__ import annotations

from followupboss_mcp.http_client import FollowUpBossClientProtocol
from followupboss_mcp.models.team_inboxes import TeamInboxListRequest, TeamInboxRecord
from followupboss_mcp.pagination import PageResult, parse_pagination_metadata


class TeamInboxesService:
    """Typed team inbox operations."""

    def __init__(self, client: FollowUpBossClientProtocol) -> None:
        """Initialize the service.

        Args:
            client: The shared Follow Up Boss HTTP client protocol.
        """
        self._client = client

    async def list_team_inboxes(
        self,
        request: TeamInboxListRequest | None = None,
    ) -> PageResult[TeamInboxRecord]:
        """List team inboxes.

        Args:
            request: Optional team inbox collection filters.

        Returns:
            A paginated team inbox result set.

        Raises:
            ValueError: If the API returns an unexpected payload shape.
        """
        query = request.to_query_params() if request is not None else None
        payload = await self._client.request_json("GET", "/teamInboxes", params=query)
        if not isinstance(payload, dict):
            raise ValueError("Unexpected team inboxes response.")
        items_raw = payload.get("teamInboxes", [])
        if not isinstance(items_raw, list):
            raise ValueError("Unexpected team inboxes response.")
        items = [
            TeamInboxRecord.model_validate(item) for item in items_raw if isinstance(item, dict)
        ]
        metadata = parse_pagination_metadata(payload, item_count=len(items))
        return PageResult(items=items, metadata=metadata)
