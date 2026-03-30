"""Users service."""

from __future__ import annotations

from followupboss_mcp.http_client import FollowUpBossClientProtocol
from followupboss_mcp.models.users import (
    CurrentUserRecord,
    DeleteUserRequest,
    UserListRequest,
    UserRecord,
)
from followupboss_mcp.pagination import PageResult, parse_pagination_metadata


class UsersService:
    """Typed user operations."""

    def __init__(self, client: FollowUpBossClientProtocol) -> None:
        """Initialize the service."""
        self._client = client

    async def list_users(self, request: UserListRequest | None = None) -> PageResult[UserRecord]:
        """List users."""
        query = request.to_query_params() if request is not None else None
        payload = await self._client.request_json("GET", "/users", params=query)
        if not isinstance(payload, dict):
            raise ValueError("Unexpected users response.")
        items_raw = payload.get("users", [])
        if not isinstance(items_raw, list):
            raise ValueError("Unexpected users response.")
        items = [UserRecord.model_validate(item) for item in items_raw if isinstance(item, dict)]
        metadata = parse_pagination_metadata(payload, item_count=len(items))
        return PageResult(items=items, metadata=metadata)

    async def get_user(self, user_id: int) -> UserRecord:
        """Fetch a user by ID."""
        payload = await self._client.request_json("GET", f"/users/{user_id}")
        return UserRecord.model_validate(payload)

    async def delete_user(self, user_id: int, request: DeleteUserRequest) -> None:
        """Delete a user by ID and reassign their leads.

        Args:
            user_id: The Follow Up Boss user identifier.
            request: The typed user-deletion query parameters.
        """
        await self._client.request_json(
            "DELETE",
            f"/users/{user_id}",
            params=request.to_query_params(),
        )

    async def get_me(self) -> CurrentUserRecord:
        """Fetch the currently authenticated user.

        Returns:
            The typed current-user record returned by Follow Up Boss.

        Raises:
            ValueError: If the API returns an unexpected payload shape.
        """
        payload = await self._client.request_json("GET", "/me")
        if not isinstance(payload, dict):
            raise ValueError("Unexpected current user response.")
        return CurrentUserRecord.model_validate(payload)
