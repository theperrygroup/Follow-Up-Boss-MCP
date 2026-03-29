"""Custom field service."""

from __future__ import annotations

from collections.abc import Mapping

from followupboss_mcp.errors import FollowUpBossValidationError
from followupboss_mcp.http_client import FollowUpBossClientProtocol
from followupboss_mcp.models.common import JsonValue
from followupboss_mcp.models.custom_fields import CustomFieldListRequest, CustomFieldRecord
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
        """Return configured custom fields."""
        query = request.to_query_params() if request is not None else None
        payload = await self._client.request_json("GET", "/customFields", params=query)
        if not isinstance(payload, dict):
            raise FollowUpBossValidationError(
                "Unexpected custom fields response shape.",
                status_code=500,
            )
        items_raw = payload.get("customfields", [])
        if not isinstance(items_raw, list):
            raise FollowUpBossValidationError(
                "Unexpected custom fields response shape.",
                status_code=500,
            )
        items = [
            CustomFieldRecord.model_validate(item) for item in items_raw if isinstance(item, dict)
        ]
        metadata = parse_pagination_metadata(payload, item_count=len(items))
        return PageResult(items=items, metadata=metadata)

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
        return {field.label: field.name for field in custom_fields}
