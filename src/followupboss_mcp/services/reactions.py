"""Reaction services."""

from __future__ import annotations

from followupboss_mcp.http_client import FollowUpBossClientProtocol
from followupboss_mcp.models.reactions import (
    CreateReactionRequest,
    DeleteReactionRequest,
    ReactionAckRecord,
    ReactionRecord,
    ReactionRefType,
)


class ReactionsService:
    """Typed reaction operations."""

    def __init__(self, client: FollowUpBossClientProtocol) -> None:
        """Initialize the service.

        Args:
            client: The shared Follow Up Boss HTTP client protocol.
        """
        self._client = client

    async def get_reaction(self, reaction_id: int) -> ReactionRecord:
        """Fetch a reaction by ID.

        Args:
            reaction_id: The Follow Up Boss reaction identifier.

        Returns:
            The typed reaction record returned by Follow Up Boss.

        Raises:
            ValueError: If the API returns an unexpected payload shape.
        """
        payload = await self._client.request_json("GET", f"/reactions/{reaction_id}")
        if not isinstance(payload, dict):
            raise ValueError("Unexpected reactions response.")
        return ReactionRecord.model_validate(payload)

    async def add_reaction(
        self,
        ref_type: ReactionRefType,
        ref_id: int,
        request: CreateReactionRequest,
    ) -> ReactionAckRecord:
        """Add a reaction to a note, call, or threaded reply.

        Args:
            ref_type: The supported Follow Up Boss reference type.
            ref_id: The identifier of the object being reacted to.
            request: The typed reaction creation request.

        Returns:
            An acknowledgement record for the mutation.

        Raises:
            ValueError: If the API returns an unexpected payload shape.
        """
        payload = request.model_dump(mode="json", by_alias=True, exclude_none=True)
        response = await self._client.request_json(
            "POST",
            f"/reactions/{ref_type}/{ref_id}",
            json_body=payload,
        )
        if isinstance(response, list):
            if response:
                raise ValueError("Unexpected reactions response.")
            return ReactionAckRecord()
        if not isinstance(response, dict):
            raise ValueError("Unexpected reactions response.")
        return ReactionAckRecord.model_validate(response)

    async def delete_reaction(
        self,
        ref_type: ReactionRefType,
        ref_id: int,
        request: DeleteReactionRequest | None = None,
    ) -> None:
        """Delete a reaction from a note, call, or threaded reply.

        Args:
            ref_type: The supported Follow Up Boss reference type.
            ref_id: The identifier of the object being reacted to.
            request: Optional emoji query parameters for targeted deletion.
        """
        query = request.to_query_params() if request is not None else None
        await self._client.request_json(
            "DELETE",
            f"/reactions/{ref_type}/{ref_id}",
            params=query,
        )
