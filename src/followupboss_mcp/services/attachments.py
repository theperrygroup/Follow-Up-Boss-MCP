"""Attachment services."""

from __future__ import annotations

from followupboss_mcp.http_client import FollowUpBossClientProtocol
from followupboss_mcp.models.attachments import (
    CreateDealAttachmentRequest,
    CreatePersonAttachmentRequest,
    DealAttachmentRecord,
    PersonAttachmentRecord,
    UpdateDealAttachmentRequest,
    UpdatePersonAttachmentRequest,
)


class DealAttachmentsService:
    """Typed deal attachment operations."""

    def __init__(self, client: FollowUpBossClientProtocol) -> None:
        """Initialize the service.

        Args:
            client: The shared Follow Up Boss HTTP client protocol.
        """
        self._client = client

    async def get_deal_attachment(self, deal_attachment_id: int) -> DealAttachmentRecord:
        """Fetch a deal attachment by ID.

        Args:
            deal_attachment_id: The Follow Up Boss deal attachment identifier.

        Returns:
            The typed deal attachment record returned by Follow Up Boss.

        Raises:
            ValueError: If the API returns an unexpected payload shape.
        """
        payload = await self._client.request_json("GET", f"/dealAttachments/{deal_attachment_id}")
        if not isinstance(payload, dict):
            raise ValueError("Unexpected deal attachment response.")
        return DealAttachmentRecord.model_validate(payload)

    async def create_deal_attachment(
        self,
        request: CreateDealAttachmentRequest,
    ) -> DealAttachmentRecord:
        """Create a deal attachment.

        Args:
            request: The typed deal attachment creation request.

        Returns:
            The created deal attachment record.

        Raises:
            ValueError: If the API returns an unexpected payload shape.
        """
        payload = request.model_dump(mode="json", by_alias=True, exclude_none=True)
        response = await self._client.request_json("POST", "/dealAttachments", json_body=payload)
        if not isinstance(response, dict):
            raise ValueError("Unexpected deal attachment response.")
        return DealAttachmentRecord.model_validate(response)

    async def update_deal_attachment(
        self,
        deal_attachment_id: int,
        request: UpdateDealAttachmentRequest,
    ) -> DealAttachmentRecord:
        """Update a deal attachment.

        Args:
            deal_attachment_id: The Follow Up Boss deal attachment identifier.
            request: The typed deal attachment update request.

        Returns:
            The updated deal attachment record.

        Raises:
            ValueError: If the API returns an unexpected payload shape.
        """
        payload = request.model_dump(mode="json", by_alias=True, exclude_none=True)
        response = await self._client.request_json(
            "PUT",
            f"/dealAttachments/{deal_attachment_id}",
            json_body=payload,
        )
        if not isinstance(response, dict):
            raise ValueError("Unexpected deal attachment response.")
        return DealAttachmentRecord.model_validate(response)

    async def delete_deal_attachment(self, deal_attachment_id: int) -> None:
        """Delete a deal attachment.

        Args:
            deal_attachment_id: The Follow Up Boss deal attachment identifier.
        """
        await self._client.request_json("DELETE", f"/dealAttachments/{deal_attachment_id}")


class PersonAttachmentsService:
    """Typed person attachment operations."""

    def __init__(self, client: FollowUpBossClientProtocol) -> None:
        """Initialize the service.

        Args:
            client: The shared Follow Up Boss HTTP client protocol.
        """
        self._client = client

    async def get_person_attachment(self, person_attachment_id: int) -> PersonAttachmentRecord:
        """Fetch a person attachment by ID.

        Args:
            person_attachment_id: The Follow Up Boss person attachment identifier.

        Returns:
            The typed person attachment record returned by Follow Up Boss.

        Raises:
            ValueError: If the API returns an unexpected payload shape.
        """
        payload = await self._client.request_json(
            "GET", f"/personAttachments/{person_attachment_id}"
        )
        if not isinstance(payload, dict):
            raise ValueError("Unexpected person attachment response.")
        return PersonAttachmentRecord.model_validate(payload)

    async def create_person_attachment(
        self,
        request: CreatePersonAttachmentRequest,
    ) -> PersonAttachmentRecord:
        """Create a person attachment.

        Args:
            request: The typed person attachment creation request.

        Returns:
            The created person attachment record.

        Raises:
            ValueError: If the API returns an unexpected payload shape.
        """
        payload = request.model_dump(mode="json", by_alias=True, exclude_none=True)
        response = await self._client.request_json("POST", "/personAttachments", json_body=payload)
        if not isinstance(response, dict):
            raise ValueError("Unexpected person attachment response.")
        return PersonAttachmentRecord.model_validate(response)

    async def update_person_attachment(
        self,
        person_attachment_id: int,
        request: UpdatePersonAttachmentRequest,
    ) -> PersonAttachmentRecord:
        """Update a person attachment.

        Args:
            person_attachment_id: The Follow Up Boss person attachment identifier.
            request: The typed person attachment update request.

        Returns:
            The updated person attachment record.

        Raises:
            ValueError: If the API returns an unexpected payload shape.
        """
        payload = request.model_dump(mode="json", by_alias=True, exclude_none=True)
        response = await self._client.request_json(
            "PUT",
            f"/personAttachments/{person_attachment_id}",
            json_body=payload,
        )
        if not isinstance(response, dict):
            raise ValueError("Unexpected person attachment response.")
        return PersonAttachmentRecord.model_validate(response)

    async def delete_person_attachment(self, person_attachment_id: int) -> None:
        """Delete a person attachment.

        Args:
            person_attachment_id: The Follow Up Boss person attachment identifier.
        """
        await self._client.request_json("DELETE", f"/personAttachments/{person_attachment_id}")
