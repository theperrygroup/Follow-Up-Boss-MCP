"""Threaded reply service."""

from __future__ import annotations

from followupboss_mcp.http_client import FollowUpBossClientProtocol
from followupboss_mcp.models.threaded_replies import ThreadedReplyRecord


class ThreadedRepliesService:
    """Typed threaded reply operations."""

    def __init__(self, client: FollowUpBossClientProtocol) -> None:
        """Initialize the service.

        Args:
            client: The shared Follow Up Boss HTTP client protocol.
        """
        self._client = client

    async def get_threaded_reply(self, threaded_reply_id: int) -> ThreadedReplyRecord:
        """Fetch a threaded reply by ID.

        Args:
            threaded_reply_id: The Follow Up Boss threaded reply identifier.

        Returns:
            The typed threaded reply record returned by Follow Up Boss.

        Raises:
            ValueError: If the API returns an unexpected payload shape.
        """
        payload = await self._client.request_json("GET", f"/threadedReplies/{threaded_reply_id}")
        if not isinstance(payload, dict):
            raise ValueError("Unexpected threaded replies response.")
        return ThreadedReplyRecord.model_validate(payload)
