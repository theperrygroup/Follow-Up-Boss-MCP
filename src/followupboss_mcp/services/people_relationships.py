"""People relationship service."""

from __future__ import annotations

from followupboss_mcp.http_client import FollowUpBossClientProtocol
from followupboss_mcp.models.people_relationships import (
    CreatePeopleRelationshipRequest,
    PeopleRelationshipListRequest,
    PeopleRelationshipRecord,
    UpdatePeopleRelationshipRequest,
)
from followupboss_mcp.pagination import PageResult, parse_pagination_metadata


class PeopleRelationshipsService:
    """Typed people relationship operations."""

    def __init__(self, client: FollowUpBossClientProtocol) -> None:
        """Initialize the service.

        Args:
            client: The shared Follow Up Boss HTTP client protocol.
        """
        self._client = client

    async def list_people_relationships(
        self,
        request: PeopleRelationshipListRequest | None = None,
    ) -> PageResult[PeopleRelationshipRecord]:
        """List people relationships.

        Args:
            request: Optional people relationship collection filters.

        Returns:
            A people relationship result set with synthetic pagination metadata.

        Raises:
            ValueError: If the API returns an unexpected payload shape.
        """
        query = request.to_query_params() if request is not None else None
        payload = await self._client.request_json("GET", "/peopleRelationships", params=query)
        metadata_source: dict[str, object]
        if isinstance(payload, list):
            items_raw = payload
            metadata_source = {}
        elif isinstance(payload, dict):
            items_value = payload.get("peopleRelationships")
            if not isinstance(items_value, list):
                items_value = payload.get("peoplerelationships")
            if not isinstance(items_value, list):
                raise ValueError("Unexpected people relationships response.")
            items_raw = items_value
            metadata_source = payload
        else:
            raise ValueError("Unexpected people relationships response.")
        items = [
            PeopleRelationshipRecord.model_validate(item)
            for item in items_raw
            if isinstance(item, dict)
        ]
        metadata = parse_pagination_metadata(metadata_source, item_count=len(items))
        return PageResult(items=items, metadata=metadata)

    async def get_people_relationship(
        self, people_relationship_id: int
    ) -> PeopleRelationshipRecord:
        """Fetch a people relationship by ID.

        Args:
            people_relationship_id: The Follow Up Boss people relationship identifier.

        Returns:
            The typed people relationship record returned by Follow Up Boss.

        Raises:
            ValueError: If the API returns an unexpected payload shape.
        """
        payload = await self._client.request_json(
            "GET",
            f"/peopleRelationships/{people_relationship_id}",
        )
        if not isinstance(payload, dict):
            raise ValueError("Unexpected people relationship response.")
        return PeopleRelationshipRecord.model_validate(payload)

    async def create_people_relationship(
        self,
        request: CreatePeopleRelationshipRequest,
    ) -> PeopleRelationshipRecord:
        """Create a people relationship.

        Args:
            request: The typed relationship creation request.

        Returns:
            The created or acknowledged people relationship record.

        Raises:
            ValueError: If the API returns an unexpected payload shape.
        """
        payload = request.model_dump(mode="json", by_alias=True, exclude_none=True)
        response = await self._client.request_json(
            "POST",
            "/peopleRelationships",
            json_body=payload,
        )
        if not isinstance(response, dict):
            raise ValueError("Unexpected people relationship response.")
        return PeopleRelationshipRecord.model_validate(response)

    async def update_people_relationship(
        self,
        people_relationship_id: int,
        request: UpdatePeopleRelationshipRequest,
    ) -> PeopleRelationshipRecord:
        """Update a people relationship.

        Args:
            people_relationship_id: The Follow Up Boss people relationship identifier.
            request: The typed relationship update request.

        Returns:
            The updated or acknowledged people relationship record.

        Raises:
            ValueError: If the API returns an unexpected payload shape.
        """
        payload = request.model_dump(mode="json", by_alias=True, exclude_none=True)
        response = await self._client.request_json(
            "PUT",
            f"/peopleRelationships/{people_relationship_id}",
            json_body=payload,
        )
        if not isinstance(response, dict):
            raise ValueError("Unexpected people relationship response.")
        return PeopleRelationshipRecord.model_validate(response)

    async def delete_people_relationship(self, people_relationship_id: int) -> None:
        """Delete a people relationship.

        Args:
            people_relationship_id: The Follow Up Boss people relationship identifier.
        """
        await self._client.request_json("DELETE", f"/peopleRelationships/{people_relationship_id}")
