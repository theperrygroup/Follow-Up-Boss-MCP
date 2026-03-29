"""Teams service."""

from __future__ import annotations

from followupboss_mcp.http_client import FollowUpBossClientProtocol
from followupboss_mcp.models.teams import (
    CreateTeamRequest,
    DeleteTeamRequest,
    TeamListRequest,
    TeamRecord,
    UpdateTeamRequest,
)
from followupboss_mcp.pagination import PageResult, parse_pagination_metadata


class TeamsService:
    """Typed team operations."""

    def __init__(self, client: FollowUpBossClientProtocol) -> None:
        """Initialize the service.

        Args:
            client: The shared Follow Up Boss HTTP client protocol.
        """
        self._client = client

    async def list_teams(self, request: TeamListRequest | None = None) -> PageResult[TeamRecord]:
        """List teams.

        Args:
            request: Optional team collection filters.

        Returns:
            A paginated team result set.

        Raises:
            ValueError: If the API returns an unexpected payload shape.
        """
        query = request.to_query_params() if request is not None else None
        payload = await self._client.request_json("GET", "/teams", params=query)
        if not isinstance(payload, dict):
            raise ValueError("Unexpected teams response.")
        items_raw = payload.get("teams", [])
        if not isinstance(items_raw, list):
            raise ValueError("Unexpected teams response.")
        items = [TeamRecord.model_validate(item) for item in items_raw if isinstance(item, dict)]
        metadata = parse_pagination_metadata(payload, item_count=len(items))
        return PageResult(items=items, metadata=metadata)

    async def get_team(self, team_id: int) -> TeamRecord:
        """Fetch a team by ID.

        Args:
            team_id: The Follow Up Boss team identifier.

        Returns:
            The typed team record returned by Follow Up Boss.
        """
        payload = await self._client.request_json("GET", f"/teams/{team_id}")
        return TeamRecord.model_validate(payload)

    async def create_team(self, request: CreateTeamRequest) -> TeamRecord:
        """Create a team.

        Args:
            request: The typed team creation request.

        Returns:
            The created team record.
        """
        payload = request.model_dump(mode="json", by_alias=True, exclude_none=True)
        response = await self._client.request_json("POST", "/teams", json_body=payload)
        return TeamRecord.model_validate(response)

    async def update_team(self, team_id: int, request: UpdateTeamRequest) -> TeamRecord:
        """Update a team.

        Args:
            team_id: The Follow Up Boss team identifier.
            request: The typed team update request.

        Returns:
            The updated team record.
        """
        payload = request.model_dump(mode="json", by_alias=True, exclude_none=True)
        response = await self._client.request_json("PUT", f"/teams/{team_id}", json_body=payload)
        return TeamRecord.model_validate(response)

    async def delete_team(self, team_id: int, request: DeleteTeamRequest | None = None) -> None:
        """Delete a team.

        Args:
            team_id: The Follow Up Boss team identifier.
            request: Optional typed team deletion query parameters.
        """
        query = request.to_query_params() if request is not None else None
        await self._client.request_json("DELETE", f"/teams/{team_id}", params=query)
