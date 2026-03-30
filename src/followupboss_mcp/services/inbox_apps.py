"""Inbox app services."""

from __future__ import annotations

from followupboss_mcp.http_client import FollowUpBossClientProtocol
from followupboss_mcp.models.inbox_apps import (
    CreateInboxAppMessageRequest,
    CreateInboxAppNoteRequest,
    CreateInboxAppParticipantRequest,
    InboxAppConversationRecord,
    InboxAppInstallationRecord,
    InboxAppInstallationSummary,
    InboxAppMessageRecord,
    InboxAppNoteRecord,
    InboxAppParticipantRecord,
    InstallInboxAppRequest,
    UpdateInboxAppConversationRequest,
    UpdateInboxAppMessageRequest,
)
from followupboss_mcp.pagination import PageResult, parse_pagination_metadata


class InboxAppsService:
    """Typed inbox app operations."""

    def __init__(self, client: FollowUpBossClientProtocol) -> None:
        """Initialize the service.

        Args:
            client: The shared Follow Up Boss HTTP client protocol.
        """
        self._client = client

    async def list_inbox_app_installations(
        self,
        published_inbox_app_id: int,
    ) -> PageResult[InboxAppInstallationSummary]:
        """List inbox app installations for a published inbox app.

        Args:
            published_inbox_app_id: The Follow Up Boss published inbox app identifier.

        Returns:
            A paginated inbox app installation result set.

        Raises:
            ValueError: If the API returns an unexpected payload shape.
        """
        payload = await self._client.request_json(
            "GET",
            f"/inboxApps/installedApps/{published_inbox_app_id}",
        )
        if not isinstance(payload, dict):
            raise ValueError("Unexpected inbox app installations response.")
        items_raw = payload.get("inboxApps", [])
        if not isinstance(items_raw, list):
            raise ValueError("Unexpected inbox app installations response.")
        items = [
            InboxAppInstallationSummary.model_validate(item)
            for item in items_raw
            if isinstance(item, dict)
        ]
        metadata = parse_pagination_metadata(payload, item_count=len(items))
        return PageResult(items=items, metadata=metadata)

    async def install_inbox_app(
        self, request: InstallInboxAppRequest
    ) -> InboxAppInstallationRecord:
        """Install an inbox app.

        Args:
            request: The typed inbox app installation request.

        Returns:
            The created inbox app installation record.
        """
        payload = request.model_dump(mode="json", by_alias=True, exclude_none=True)
        response = await self._client.request_json("POST", "/inboxApps/install", json_body=payload)
        return InboxAppInstallationRecord.model_validate(response)

    async def deactivate_inbox_app(self, inbox_app_id: int) -> None:
        """Deactivate an inbox app installation.

        Args:
            inbox_app_id: The Follow Up Boss inbox app installation identifier.
        """
        await self._client.request_json("DELETE", f"/inboxApps/{inbox_app_id}")

    async def add_inbox_app_message(
        self,
        inbox_app_id: int,
        request: CreateInboxAppMessageRequest,
    ) -> InboxAppMessageRecord:
        """Add a message to an inbox app conversation.

        Args:
            inbox_app_id: The Follow Up Boss inbox app installation identifier.
            request: The typed inbox app message creation request.

        Returns:
            The created inbox app message record.

        Raises:
            ValueError: If the API returns an unexpected payload shape.
        """
        payload = request.model_dump(mode="json", by_alias=True, exclude_none=True)
        response = await self._client.request_json(
            "POST",
            f"/inboxApps/{inbox_app_id}/message",
            json_body=payload,
        )
        if not isinstance(response, dict):
            raise ValueError("Unexpected inbox app message response.")
        return InboxAppMessageRecord.model_validate(response)

    async def add_inbox_app_note(
        self,
        inbox_app_id: int,
        request: CreateInboxAppNoteRequest,
    ) -> InboxAppNoteRecord:
        """Add a note to an inbox app conversation.

        Args:
            inbox_app_id: The Follow Up Boss inbox app installation identifier.
            request: The typed inbox app note creation request.

        Returns:
            The created inbox app note record.

        Raises:
            ValueError: If the API returns an unexpected payload shape.
        """
        payload = request.model_dump(mode="json", by_alias=True, exclude_none=True)
        response = await self._client.request_json(
            "POST",
            f"/inboxApps/{inbox_app_id}/note",
            json_body=payload,
        )
        if not isinstance(response, dict):
            raise ValueError("Unexpected inbox app note response.")
        return InboxAppNoteRecord.model_validate(response)

    async def list_inbox_app_participants(
        self,
        inbox_app_id: int,
        ext_conversation_id: str,
    ) -> PageResult[InboxAppParticipantRecord]:
        """List inbox app conversation participants.

        Args:
            inbox_app_id: The Follow Up Boss inbox app installation identifier.
            ext_conversation_id: The external conversation identifier.

        Returns:
            A paginated participant result set with synthetic metadata.

        Raises:
            ValueError: If the API returns an unexpected payload shape.
        """
        payload = await self._client.request_json(
            "GET",
            (f"/inboxApps/{inbox_app_id}/conversations/{ext_conversation_id}/participants"),
        )
        if not isinstance(payload, list):
            raise ValueError("Unexpected inbox app participants response.")
        items = [
            InboxAppParticipantRecord.model_validate(item)
            for item in payload
            if isinstance(item, dict)
        ]
        metadata = parse_pagination_metadata({}, item_count=len(items))
        return PageResult(items=items, metadata=metadata)

    async def add_inbox_app_participant(
        self,
        inbox_app_id: int,
        ext_conversation_id: str,
        request: CreateInboxAppParticipantRequest,
    ) -> InboxAppParticipantRecord:
        """Add a participant to an inbox app conversation.

        Args:
            inbox_app_id: The Follow Up Boss inbox app installation identifier.
            ext_conversation_id: The external conversation identifier.
            request: The typed participant creation request.

        Returns:
            The created participant record.
        """
        payload = request.model_dump(mode="json", by_alias=True, exclude_none=True)
        response = await self._client.request_json(
            "POST",
            (f"/inboxApps/{inbox_app_id}/conversations/{ext_conversation_id}/participants"),
            json_body=payload,
        )
        return InboxAppParticipantRecord.model_validate(response)

    async def update_inbox_app_conversation(
        self,
        inbox_app_id: int,
        ext_conversation_id: str,
        request: UpdateInboxAppConversationRequest,
    ) -> InboxAppConversationRecord:
        """Update an inbox app conversation.

        Args:
            inbox_app_id: The Follow Up Boss inbox app installation identifier.
            ext_conversation_id: The external conversation identifier.
            request: The typed inbox app conversation update request.

        Returns:
            The updated inbox app conversation record.

        Raises:
            ValueError: If the API returns an unexpected payload shape.
        """
        payload = request.model_dump(mode="json", by_alias=True, exclude_none=True)
        response = await self._client.request_json(
            "PUT",
            f"/inboxApps/{inbox_app_id}/conversations/{ext_conversation_id}",
            json_body=payload,
        )
        if not isinstance(response, dict):
            raise ValueError("Unexpected inbox app conversation response.")
        return InboxAppConversationRecord.model_validate(response)

    async def update_inbox_app_message(
        self,
        inbox_app_id: int,
        request: UpdateInboxAppMessageRequest,
    ) -> InboxAppMessageRecord:
        """Update an inbox app message.

        Args:
            inbox_app_id: The Follow Up Boss inbox app installation identifier.
            request: The typed inbox app message update request.

        Returns:
            The updated inbox app message record.

        Raises:
            ValueError: If the API returns an unexpected payload shape.
        """
        payload = request.model_dump(mode="json", by_alias=True, exclude_none=True)
        response = await self._client.request_json(
            "PUT",
            f"/inboxApps/{inbox_app_id}/message",
            json_body=payload,
        )
        if not isinstance(response, dict):
            raise ValueError("Unexpected inbox app message response.")
        return InboxAppMessageRecord.model_validate(response)

    async def remove_inbox_app_participant(
        self,
        inbox_app_id: int,
        ext_conversation_id: str,
        participant_id: int,
    ) -> None:
        """Remove a participant from an inbox app conversation.

        Args:
            inbox_app_id: The Follow Up Boss inbox app installation identifier.
            ext_conversation_id: The external conversation identifier.
            participant_id: The participant identifier returned by Follow Up Boss.
        """
        await self._client.request_json(
            "DELETE",
            (
                f"/inboxApps/{inbox_app_id}/conversations/"
                f"{ext_conversation_id}/participants/{participant_id}"
            ),
        )
