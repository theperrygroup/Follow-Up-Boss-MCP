"""Templates service."""

from __future__ import annotations

from followupboss_mcp.http_client import FollowUpBossClientProtocol
from followupboss_mcp.models.templates import (
    CreateTemplateRequest,
    TemplateListRequest,
    TemplateLookupRequest,
    TemplateRecord,
    UpdateTemplateRequest,
)
from followupboss_mcp.pagination import PageResult, parse_pagination_metadata


class TemplatesService:
    """Typed email template operations."""

    def __init__(self, client: FollowUpBossClientProtocol) -> None:
        """Initialize the service.

        Args:
            client: The shared Follow Up Boss HTTP client protocol.
        """
        self._client = client

    async def list_templates(
        self,
        request: TemplateListRequest | None = None,
    ) -> PageResult[TemplateRecord]:
        """List email templates.

        Args:
            request: Optional email template collection filters.

        Returns:
            A paginated template result set.

        Raises:
            ValueError: If the API returns an unexpected payload shape.
        """
        query = request.to_query_params() if request is not None else None
        payload = await self._client.request_json("GET", "/templates", params=query)
        if not isinstance(payload, dict):
            raise ValueError("Unexpected templates response.")
        items_raw = payload.get("templates", [])
        if not isinstance(items_raw, list):
            raise ValueError("Unexpected templates response.")
        items = [
            TemplateRecord.model_validate(item) for item in items_raw if isinstance(item, dict)
        ]
        metadata = parse_pagination_metadata(payload, item_count=len(items))
        return PageResult(items=items, metadata=metadata)

    async def get_template(
        self,
        template_id: int,
        request: TemplateLookupRequest | None = None,
    ) -> TemplateRecord:
        """Fetch an email template by ID.

        Args:
            template_id: The Follow Up Boss email template identifier.
            request: Optional merge-person query parameters.

        Returns:
            The typed email template record returned by Follow Up Boss.
        """
        query = request.to_query_params() if request is not None else None
        payload = await self._client.request_json("GET", f"/templates/{template_id}", params=query)
        return TemplateRecord.model_validate(payload)

    async def create_template(self, request: CreateTemplateRequest) -> TemplateRecord:
        """Create an email template.

        Args:
            request: The typed template creation request.

        Returns:
            The created email template record.
        """
        payload = request.model_dump(mode="json", by_alias=True, exclude_none=True)
        response = await self._client.request_json("POST", "/templates", json_body=payload)
        return TemplateRecord.model_validate(response)

    async def update_template(
        self,
        template_id: int,
        request: UpdateTemplateRequest,
    ) -> TemplateRecord:
        """Update an email template.

        Args:
            template_id: The Follow Up Boss email template identifier.
            request: The typed template update request.

        Returns:
            The updated email template record.
        """
        payload = request.model_dump(mode="json", by_alias=True, exclude_none=True)
        response = await self._client.request_json(
            "PUT", f"/templates/{template_id}", json_body=payload
        )
        return TemplateRecord.model_validate(response)

    async def delete_template(self, template_id: int) -> None:
        """Delete an email template.

        Args:
            template_id: The Follow Up Boss email template identifier.
        """
        await self._client.request_json("DELETE", f"/templates/{template_id}")
