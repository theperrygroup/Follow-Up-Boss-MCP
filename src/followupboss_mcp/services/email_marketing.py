"""Email marketing services."""

from __future__ import annotations

from followupboss_mcp.http_client import FollowUpBossClientProtocol
from followupboss_mcp.models.email_marketing import (
    CreateEmailCampaignRequest,
    CreateEmailEventsBatchRequest,
    EmailCampaignListRequest,
    EmailCampaignRecord,
    EmailEventListRequest,
    EmailEventRecord,
    EmailEventsBatchResult,
    UpdateEmailCampaignRequest,
)
from followupboss_mcp.pagination import PageResult, parse_pagination_metadata


class EmailMarketingService:
    """Typed email marketing campaign and event operations."""

    def __init__(self, client: FollowUpBossClientProtocol) -> None:
        """Initialize the service.

        Args:
            client: The shared Follow Up Boss HTTP client protocol.
        """
        self._client = client

    async def list_email_campaigns(
        self,
        request: EmailCampaignListRequest | None = None,
    ) -> PageResult[EmailCampaignRecord]:
        """List email marketing campaigns.

        Args:
            request: Optional email campaign collection filters.

        Returns:
            A paginated email campaign result set.

        Raises:
            ValueError: If the API returns an unexpected payload shape.
        """
        query = request.to_query_params() if request is not None else None
        payload = await self._client.request_json("GET", "/emCampaigns", params=query)
        if not isinstance(payload, dict):
            raise ValueError("Unexpected email campaigns response.")
        items_raw = payload.get("emCampaigns", [])
        if not isinstance(items_raw, list):
            raise ValueError("Unexpected email campaigns response.")
        items = [
            EmailCampaignRecord.model_validate(item) for item in items_raw if isinstance(item, dict)
        ]
        metadata = parse_pagination_metadata(payload, item_count=len(items))
        return PageResult(items=items, metadata=metadata)

    async def create_email_campaign(
        self,
        request: CreateEmailCampaignRequest,
    ) -> EmailCampaignRecord:
        """Create an email marketing campaign.

        Args:
            request: The typed campaign creation request.

        Returns:
            The created email campaign record.

        Raises:
            ValueError: If the API returns an unexpected payload shape.
        """
        payload = request.model_dump(mode="json", by_alias=True, exclude_none=True)
        response = await self._client.request_json("POST", "/emCampaigns", json_body=payload)
        if not isinstance(response, dict):
            raise ValueError("Unexpected email campaigns response.")
        return EmailCampaignRecord.model_validate(response)

    async def update_email_campaign(
        self,
        email_campaign_id: int,
        request: UpdateEmailCampaignRequest,
    ) -> EmailCampaignRecord:
        """Update an email marketing campaign.

        Args:
            email_campaign_id: The Follow Up Boss email campaign identifier.
            request: The typed campaign update request.

        Returns:
            The updated email campaign record.

        Raises:
            ValueError: If the API returns an unexpected payload shape.
        """
        payload = request.model_dump(mode="json", by_alias=True, exclude_none=True)
        response = await self._client.request_json(
            "PUT",
            f"/emCampaigns/{email_campaign_id}",
            json_body=payload,
        )
        if not isinstance(response, dict):
            raise ValueError("Unexpected email campaigns response.")
        return EmailCampaignRecord.model_validate(response)

    async def list_email_events(
        self,
        request: EmailEventListRequest | None = None,
    ) -> PageResult[EmailEventRecord]:
        """List email marketing events.

        Args:
            request: Optional email event collection filters.

        Returns:
            A paginated email event result set.

        Raises:
            ValueError: If the API returns an unexpected payload shape.
        """
        query = request.to_query_params() if request is not None else None
        payload = await self._client.request_json("GET", "/emEvents", params=query)
        if not isinstance(payload, dict):
            raise ValueError("Unexpected email events response.")
        items_raw = payload.get("emEvents", [])
        if not isinstance(items_raw, list):
            raise ValueError("Unexpected email events response.")
        items = [
            EmailEventRecord.model_validate(item) for item in items_raw if isinstance(item, dict)
        ]
        metadata = parse_pagination_metadata(payload, item_count=len(items))
        return PageResult(items=items, metadata=metadata)

    async def send_email_events(
        self,
        request: CreateEmailEventsBatchRequest,
    ) -> EmailEventsBatchResult:
        """Notify Follow Up Boss about email marketing events.

        Args:
            request: The typed batch email event request.

        Returns:
            The batch result including accepted event IDs and skipped recipients.

        Raises:
            ValueError: If the API returns an unexpected payload shape.
        """
        payload = request.model_dump(mode="json", by_alias=True, exclude_none=True)
        response = await self._client.request_json("POST", "/emEvents", json_body=payload)
        if not isinstance(response, dict):
            raise ValueError("Unexpected email events response.")
        return EmailEventsBatchResult.model_validate(response)
