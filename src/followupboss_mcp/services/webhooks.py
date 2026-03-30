"""Webhooks service."""

from __future__ import annotations

from followupboss_mcp.http_client import FollowUpBossClientProtocol
from followupboss_mcp.models.webhooks import (
    CreateWebhookRequest,
    UpdateWebhookRequest,
    WebhookEventRecord,
    WebhookListRequest,
    WebhookRecord,
)
from followupboss_mcp.pagination import PageResult, parse_pagination_metadata


class WebhooksService:
    """Typed webhook operations."""

    def __init__(self, client: FollowUpBossClientProtocol) -> None:
        """Initialize the service."""
        self._client = client

    async def list_webhooks(
        self,
        request: WebhookListRequest | None = None,
    ) -> PageResult[WebhookRecord]:
        """List registered webhooks."""
        query = request.to_query_params() if request is not None else None
        payload = await self._client.request_json("GET", "/webhooks", params=query)
        if not isinstance(payload, dict):
            raise ValueError("Unexpected webhooks response.")
        items_raw = payload.get("webhooks", [])
        if not isinstance(items_raw, list):
            raise ValueError("Unexpected webhooks response.")
        items = [WebhookRecord.model_validate(item) for item in items_raw if isinstance(item, dict)]
        metadata = parse_pagination_metadata(payload, item_count=len(items))
        return PageResult(items=items, metadata=metadata)

    async def get_webhook(self, webhook_id: int) -> WebhookRecord:
        """Fetch a webhook by ID.

        Args:
            webhook_id: The Follow Up Boss webhook identifier.

        Returns:
            The typed webhook record returned by Follow Up Boss.
        """
        payload = await self._client.request_json("GET", f"/webhooks/{webhook_id}")
        return WebhookRecord.model_validate(payload)

    async def get_webhook_event(self, webhook_event_id: str) -> WebhookEventRecord:
        """Fetch a webhook event by ID.

        Args:
            webhook_event_id: The Follow Up Boss webhook event identifier.

        Returns:
            The typed webhook event record returned by Follow Up Boss.

        Raises:
            ValueError: If the API returns an unexpected payload shape.
        """
        payload = await self._client.request_json("GET", f"/webhookEvents/{webhook_event_id}")
        if not isinstance(payload, dict):
            raise ValueError("Unexpected webhook events response.")
        return WebhookEventRecord.model_validate(payload)

    async def create_webhook(self, request: CreateWebhookRequest) -> WebhookRecord:
        """Create a webhook."""
        payload = request.model_dump(by_alias=True, exclude_none=True)
        response = await self._client.request_json("POST", "/webhooks", json_body=payload)
        return WebhookRecord.model_validate(response)

    async def update_webhook(self, webhook_id: int, request: UpdateWebhookRequest) -> WebhookRecord:
        """Update a webhook.

        Args:
            webhook_id: The Follow Up Boss webhook identifier.
            request: The typed webhook update request.

        Returns:
            The updated webhook record.
        """
        payload = request.model_dump(by_alias=True, exclude_none=True)
        response = await self._client.request_json(
            "PUT",
            f"/webhooks/{webhook_id}",
            json_body=payload,
        )
        return WebhookRecord.model_validate(response)

    async def delete_webhook(self, webhook_id: int) -> None:
        """Delete a webhook."""
        await self._client.request_json("DELETE", f"/webhooks/{webhook_id}")
