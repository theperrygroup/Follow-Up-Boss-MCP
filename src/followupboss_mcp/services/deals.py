"""Deals service."""

from __future__ import annotations

from collections.abc import Mapping

from followupboss_mcp.errors import FollowUpBossValidationError
from followupboss_mcp.http_client import FollowUpBossClientProtocol
from followupboss_mcp.models.common import JsonValue
from followupboss_mcp.models.deals import (
    CreateDealCustomFieldRequest,
    CreateDealRequest,
    DealCustomFieldListRequest,
    DealCustomFieldRecord,
    DealListRequest,
    DealRecord,
    UpdateDealCustomFieldRequest,
    UpdateDealRequest,
)
from followupboss_mcp.pagination import PageResult, parse_pagination_metadata


class DealsService:
    """Typed deal operations."""

    def __init__(self, client: FollowUpBossClientProtocol) -> None:
        """Initialize the service.

        Args:
            client: The shared Follow Up Boss HTTP client protocol.
        """
        self._client = client

    async def list_deals(self, request: DealListRequest | None = None) -> PageResult[DealRecord]:
        """List deals.

        Args:
            request: Optional deals collection filters.

        Returns:
            A paginated deals result set.

        Raises:
            ValueError: If the API returns an unexpected payload shape.
        """
        query = request.to_query_params() if request is not None else None
        payload = await self._client.request_json("GET", "/deals", params=query)
        if not isinstance(payload, dict):
            raise ValueError("Unexpected deals response.")
        items_raw = payload.get("deals", [])
        if not isinstance(items_raw, list):
            raise ValueError("Unexpected deals response.")
        items = [DealRecord.model_validate(item) for item in items_raw if isinstance(item, dict)]
        metadata = parse_pagination_metadata(payload, item_count=len(items))
        return PageResult(items=items, metadata=metadata)

    async def get_deal(self, deal_id: int) -> DealRecord:
        """Fetch a deal by ID.

        Args:
            deal_id: The Follow Up Boss deal identifier.

        Returns:
            The typed deal record returned by Follow Up Boss.
        """
        payload = await self._client.request_json("GET", f"/deals/{deal_id}")
        return DealRecord.model_validate(payload)

    async def create_deal(self, request: CreateDealRequest) -> DealRecord:
        """Create a deal.

        Args:
            request: The typed deal creation request.

        Returns:
            The created deal record.
        """
        payload = request.model_dump(mode="json", by_alias=True, exclude_none=True)
        payload.update(self.validate_deal_custom_field_names(request.custom_fields))
        payload.pop("custom_fields", None)
        response = await self._client.request_json("POST", "/deals", json_body=payload)
        return DealRecord.model_validate(response)

    async def update_deal(self, deal_id: int, request: UpdateDealRequest) -> DealRecord:
        """Update a deal.

        Args:
            deal_id: The Follow Up Boss deal identifier.
            request: The typed deal update request.

        Returns:
            The updated deal record.
        """
        payload = request.model_dump(mode="json", by_alias=True, exclude_none=True)
        payload.update(self.validate_deal_custom_field_names(request.custom_fields))
        payload.pop("custom_fields", None)
        response = await self._client.request_json("PUT", f"/deals/{deal_id}", json_body=payload)
        return DealRecord.model_validate(response)

    async def delete_deal(self, deal_id: int) -> None:
        """Delete a deal.

        Args:
            deal_id: The Follow Up Boss deal identifier.
        """
        await self._client.request_json("DELETE", f"/deals/{deal_id}")

    async def list_deal_custom_fields(
        self,
        request: DealCustomFieldListRequest | None = None,
    ) -> PageResult[DealCustomFieldRecord]:
        """Return configured deal custom fields.

        Args:
            request: Optional deal custom field collection filters.

        Returns:
            A paginated deal custom field result set.

        Raises:
            FollowUpBossValidationError: If the API returns an unexpected payload shape.
        """
        query = request.to_query_params() if request is not None else None
        payload = await self._client.request_json("GET", "/dealCustomFields", params=query)
        payload = self._require_deal_custom_field_payload(payload)
        items_raw = payload.get("dealCustomfields", [])
        if not isinstance(items_raw, list):
            raise FollowUpBossValidationError(
                "Unexpected deal custom fields response shape.",
                status_code=500,
            )
        items = [
            DealCustomFieldRecord.model_validate(item)
            for item in items_raw
            if isinstance(item, dict)
        ]
        metadata = parse_pagination_metadata(payload, item_count=len(items))
        return PageResult(items=items, metadata=metadata)

    async def get_deal_custom_field(self, deal_custom_field_id: int) -> DealCustomFieldRecord:
        """Fetch a deal custom field by ID.

        Args:
            deal_custom_field_id: The Follow Up Boss deal custom field identifier.

        Returns:
            The typed deal custom field record returned by Follow Up Boss.

        Raises:
            FollowUpBossValidationError: If the API returns an unexpected payload shape.
        """
        payload = await self._client.request_json("GET", f"/dealCustomFields/{deal_custom_field_id}")
        payload = self._require_deal_custom_field_payload(payload)
        return DealCustomFieldRecord.model_validate(payload)

    async def create_deal_custom_field(
        self,
        request: CreateDealCustomFieldRequest,
    ) -> DealCustomFieldRecord:
        """Create a deal custom field.

        Args:
            request: The typed deal custom field creation request.

        Returns:
            The created deal custom field record.

        Raises:
            FollowUpBossValidationError: If the API returns an unexpected payload shape.
        """
        payload = request.model_dump(mode="json", by_alias=True, exclude_none=True)
        response = await self._client.request_json("POST", "/dealCustomFields", json_body=payload)
        response = self._require_deal_custom_field_payload(response)
        return DealCustomFieldRecord.model_validate(response)

    async def update_deal_custom_field(
        self,
        deal_custom_field_id: int,
        request: UpdateDealCustomFieldRequest,
    ) -> DealCustomFieldRecord:
        """Update a deal custom field.

        Args:
            deal_custom_field_id: The Follow Up Boss deal custom field identifier.
            request: The typed deal custom field update request.

        Returns:
            The updated deal custom field record.

        Raises:
            FollowUpBossValidationError: If the API returns an unexpected payload shape.
        """
        payload = request.model_dump(mode="json", by_alias=True, exclude_none=True)
        response = await self._client.request_json(
            "PUT",
            f"/dealCustomFields/{deal_custom_field_id}",
            json_body=payload,
        )
        response = self._require_deal_custom_field_payload(response)
        return DealCustomFieldRecord.model_validate(response)

    async def delete_deal_custom_field(self, deal_custom_field_id: int) -> None:
        """Delete a deal custom field.

        Args:
            deal_custom_field_id: The Follow Up Boss deal custom field identifier.
        """
        await self._client.request_json("DELETE", f"/dealCustomFields/{deal_custom_field_id}")

    @staticmethod
    def validate_deal_custom_field_names(
        custom_fields: Mapping[str, JsonValue] | None,
    ) -> dict[str, JsonValue]:
        """Require outgoing deal custom field keys to use Follow Up Boss field names.

        Args:
            custom_fields: The outgoing deal custom field mapping.

        Returns:
            A normalized copy of the custom field mapping.

        Raises:
            FollowUpBossValidationError: If any custom field key does not use a
                Follow Up Boss field name.
        """
        if custom_fields is None:
            return {}
        invalid_names = sorted(name for name in custom_fields if not name.startswith("custom"))
        if invalid_names:
            raise FollowUpBossValidationError(
                (
                    "Deal custom field keys must use Follow Up Boss "
                    "field names that start with 'custom'."
                ),
                status_code=400,
                payload={"invalidKeys": invalid_names},
            )
        return dict(custom_fields)

    @staticmethod
    def _require_deal_custom_field_payload(payload: object) -> dict[str, object]:
        """Normalize deal-custom-field payloads that should be JSON objects.

        Args:
            payload: The raw payload returned by the HTTP client.

        Returns:
            The normalized dictionary payload.

        Raises:
            FollowUpBossValidationError: If the payload is not a dictionary.
        """
        if not isinstance(payload, dict):
            raise FollowUpBossValidationError(
                "Unexpected deal custom fields response shape.",
                status_code=500,
            )
        return payload
