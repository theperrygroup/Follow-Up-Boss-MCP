"""Custom field service."""

from __future__ import annotations

from collections.abc import Mapping

from followupboss_mcp.errors import FollowUpBossValidationError
from followupboss_mcp.http_client import FollowUpBossClientProtocol
from followupboss_mcp.models.common import JsonValue
from followupboss_mcp.models.custom_fields import (
    CreateCustomFieldRequest,
    CustomFieldListRequest,
    CustomFieldRecord,
    UpdateCustomFieldRequest,
)
from followupboss_mcp.pagination import PageResult, parse_pagination_metadata


class CustomFieldsService:
    """Typed custom field operations."""

    def __init__(self, client: FollowUpBossClientProtocol) -> None:
        """Initialize the service."""
        self._client = client

    async def list_custom_fields(
        self,
        request: CustomFieldListRequest | None = None,
    ) -> PageResult[CustomFieldRecord]:
        """Return configured custom fields.

        Args:
            request: Optional custom field collection filters.

        Returns:
            A paginated custom field result set.

        Raises:
            FollowUpBossValidationError: If the API returns an unexpected payload shape.
        """
        query = request.to_query_params() if request is not None else None
        payload = await self._client.request_json("GET", "/customFields", params=query)
        payload_dict = self._require_dict_payload(payload)
        items_raw = payload_dict.get("customfields", [])
        if not isinstance(items_raw, list):
            raise FollowUpBossValidationError(
                "Unexpected custom fields response shape.",
                status_code=500,
            )
        items = [
            CustomFieldRecord.model_validate(item) for item in items_raw if isinstance(item, dict)
        ]
        metadata = parse_pagination_metadata(payload_dict, item_count=len(items))
        return PageResult(items=items, metadata=metadata)

    async def get_custom_field(self, custom_field_id: int) -> CustomFieldRecord:
        """Fetch a custom field by ID.

        Args:
            custom_field_id: The Follow Up Boss custom field identifier.

        Returns:
            The typed custom field record returned by Follow Up Boss.

        Raises:
            FollowUpBossValidationError: If the API returns an unexpected payload shape.
        """
        payload = await self._client.request_json("GET", f"/customFields/{custom_field_id}")
        payload_dict = self._require_dict_payload(payload)
        return CustomFieldRecord.model_validate(payload_dict)

    async def create_custom_field(self, request: CreateCustomFieldRequest) -> CustomFieldRecord:
        """Create a custom field.

        Args:
            request: The typed custom field creation request.

        Returns:
            The created custom field record.

        Raises:
            FollowUpBossValidationError: If the API returns an unexpected payload shape.
        """
        payload = request.model_dump(mode="json", by_alias=True, exclude_none=True)
        response = await self._client.request_json("POST", "/customFields", json_body=payload)
        response_dict = self._require_dict_payload(response)
        return CustomFieldRecord.model_validate(response_dict)

    async def update_custom_field(
        self,
        custom_field_id: int,
        request: UpdateCustomFieldRequest,
    ) -> CustomFieldRecord:
        """Update a custom field.

        Args:
            custom_field_id: The Follow Up Boss custom field identifier.
            request: The typed custom field update request.

        Returns:
            The updated custom field record.

        Raises:
            FollowUpBossValidationError: If the API returns an unexpected payload shape.
        """
        payload = request.model_dump(mode="json", by_alias=True, exclude_none=True)
        response = await self._client.request_json(
            "PUT",
            f"/customFields/{custom_field_id}",
            json_body=payload,
        )
        response_dict = self._require_dict_payload(response)
        return CustomFieldRecord.model_validate(response_dict)

    async def delete_custom_field(self, custom_field_id: int) -> None:
        """Delete a custom field.

        Args:
            custom_field_id: The Follow Up Boss custom field identifier.
        """
        await self._client.request_json("DELETE", f"/customFields/{custom_field_id}")

    @staticmethod
    def _require_dict_payload(payload: object) -> dict[str, object]:
        """Normalize custom-field payloads that should be JSON objects.

        Args:
            payload: The raw payload returned by the HTTP client.

        Returns:
            The normalized dictionary payload.

        Raises:
            FollowUpBossValidationError: If the payload is not a dictionary.
        """
        if not isinstance(payload, dict):
            raise FollowUpBossValidationError(
                "Unexpected custom fields response shape.",
                status_code=500,
            )
        return payload

    @staticmethod
    def validate_custom_field_names(
        custom_fields: Mapping[str, JsonValue] | None,
    ) -> dict[str, JsonValue]:
        """Require outgoing custom field keys to use Follow Up Boss field names."""
        if custom_fields is None:
            return {}
        invalid_names = sorted(name for name in custom_fields if not name.startswith("custom"))
        if invalid_names:
            raise FollowUpBossValidationError(
                "Custom field keys must use Follow Up Boss field names that start with 'custom'.",
                status_code=400,
                payload={"invalidKeys": invalid_names},
            )
        return dict(custom_fields)

    @staticmethod
    def resolve_field_names(custom_fields: list[CustomFieldRecord]) -> dict[str, str]:
        """Return a label-to-name lookup table."""
        return {
            field.label: field.name
            for field in custom_fields
            if field.label is not None and field.name is not None
        }
