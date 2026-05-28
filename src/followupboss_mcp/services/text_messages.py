"""Text message services."""

from __future__ import annotations

from followupboss_mcp.http_client import FollowUpBossClientProtocol
from followupboss_mcp.models.text_messages import (
    CreateTextMessageTemplateRequest,
    MergedTextMessageTemplateRecord,
    MergeTextMessageTemplateRequest,
    TextMessageListRequest,
    TextMessageRecord,
    TextMessageTemplateListRequest,
    TextMessageTemplateRecord,
    UpdateTextMessageTemplateRequest,
)
from followupboss_mcp.pagination import PageResult, parse_pagination_metadata


class TextMessagesService:
    """Typed text message operations."""

    def __init__(self, client: FollowUpBossClientProtocol) -> None:
        """Initialize the service.

        Args:
            client: The shared Follow Up Boss HTTP client protocol.
        """
        self._client = client

    async def list_text_messages(
        self,
        request: TextMessageListRequest | None = None,
    ) -> PageResult[TextMessageRecord]:
        """List text messages.

        Args:
            request: Optional text message collection filters.

        Returns:
            A paginated text message result set.

        Raises:
            ValueError: If the API returns an unexpected payload shape.
        """
        query = request.to_query_params() if request is not None else None
        payload = await self._client.request_json("GET", "/textMessages", params=query)
        if not isinstance(payload, dict):
            raise ValueError("Unexpected text messages response.")
        items_raw = payload.get("textmessages", [])
        if not isinstance(items_raw, list):
            raise ValueError("Unexpected text messages response.")
        items = [
            TextMessageRecord.model_validate(item) for item in items_raw if isinstance(item, dict)
        ]
        metadata = parse_pagination_metadata(payload, item_count=len(items))
        return PageResult(items=items, metadata=metadata)

    async def get_text_message(self, text_message_id: int) -> TextMessageRecord:
        """Fetch a text message by ID.

        Args:
            text_message_id: The Follow Up Boss text message identifier.

        Returns:
            The typed text message record returned by Follow Up Boss.
        """
        payload = await self._client.request_json("GET", f"/textMessages/{text_message_id}")
        return TextMessageRecord.model_validate(payload)


class TextMessageTemplatesService:
    """Typed text message template operations."""

    def __init__(self, client: FollowUpBossClientProtocol) -> None:
        """Initialize the service.

        Args:
            client: The shared Follow Up Boss HTTP client protocol.
        """
        self._client = client

    async def list_text_message_templates(
        self,
        request: TextMessageTemplateListRequest | None = None,
    ) -> PageResult[TextMessageTemplateRecord]:
        """List text message templates.

        Args:
            request: Optional text message template collection filters.

        Returns:
            A paginated template result set.

        Raises:
            ValueError: If the API returns an unexpected payload shape.
        """
        query = request.to_query_params() if request is not None else None
        payload = await self._client.request_json("GET", "/textMessageTemplates", params=query)
        if not isinstance(payload, dict):
            raise ValueError("Unexpected text message templates response.")
        items_raw = payload.get("textmessagetemplates", [])
        if not isinstance(items_raw, list):
            raise ValueError("Unexpected text message templates response.")
        items = [
            TextMessageTemplateRecord.model_validate(item)
            for item in items_raw
            if isinstance(item, dict)
        ]
        metadata = parse_pagination_metadata(payload, item_count=len(items))
        return PageResult(items=items, metadata=metadata)

    async def get_text_message_template(
        self,
        template_id: int,
    ) -> TextMessageTemplateRecord:
        """Fetch a text message template by ID.

        Args:
            template_id: The Follow Up Boss text message template identifier.

        Returns:
            The typed text message template record returned by Follow Up Boss.
        """
        payload = await self._client.request_json("GET", f"/textMessageTemplates/{template_id}")
        return TextMessageTemplateRecord.model_validate(payload)

    async def create_text_message_template(
        self,
        request: CreateTextMessageTemplateRequest,
    ) -> TextMessageTemplateRecord:
        """Create a text message template.

        Args:
            request: The typed template creation request.

        Returns:
            The created template record.
        """
        payload = request.model_dump(mode="json", by_alias=True, exclude_none=True)
        response = await self._client.request_json(
            "POST", "/textMessageTemplates", json_body=payload
        )
        return TextMessageTemplateRecord.model_validate(response)

    async def update_text_message_template(
        self,
        template_id: int,
        request: UpdateTextMessageTemplateRequest,
    ) -> TextMessageTemplateRecord:
        """Update a text message template.

        Args:
            template_id: The Follow Up Boss text message template identifier.
            request: The typed template update request.

        Returns:
            The updated template record.
        """
        payload = request.model_dump(mode="json", by_alias=True, exclude_none=True)
        response = await self._client.request_json(
            "PUT",
            f"/textMessageTemplates/{template_id}",
            json_body=payload,
        )
        return TextMessageTemplateRecord.model_validate(response)

    async def delete_text_message_template(self, template_id: int) -> None:
        """Delete a text message template.

        Args:
            template_id: The Follow Up Boss text message template identifier.
        """
        await self._client.request_json("DELETE", f"/textMessageTemplates/{template_id}")

    async def merge_text_message_template(
        self,
        request: MergeTextMessageTemplateRequest,
    ) -> MergedTextMessageTemplateRecord:
        """Merge a text message template with recipients.

        Args:
            request: The typed template-merge request.

        Returns:
            The merged text message template preview returned by Follow Up Boss.
        """
        payload = request.model_dump(mode="json", by_alias=True, exclude_none=True)
        response = await self._client.request_json(
            "POST",
            "/textMessageTemplates/merge",
            json_body=payload,
        )
        return MergedTextMessageTemplateRecord.model_validate(response)
