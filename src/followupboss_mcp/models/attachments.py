"""Attachment models."""

from __future__ import annotations

from pydantic import Field

from followupboss_mcp.models.common import RequestModel, ResponseModel


class AttachmentRequest(RequestModel):
    """Common request fields shared by deal and person attachments."""

    file_name: str = Field(serialization_alias="fileName")
    file_size: int | None = Field(default=None, serialization_alias="fileSize")
    uri: str


class CreateDealAttachmentRequest(AttachmentRequest):
    """Strict request model for creating a deal attachment."""

    deal_id: int = Field(serialization_alias="dealId")


class UpdateDealAttachmentRequest(AttachmentRequest):
    """Strict request model for updating a deal attachment."""

    deal_id: int = Field(serialization_alias="dealId")


class CreatePersonAttachmentRequest(AttachmentRequest):
    """Strict request model for creating a person attachment."""

    person_id: int = Field(serialization_alias="personId")


class UpdatePersonAttachmentRequest(AttachmentRequest):
    """Strict request model for updating a person attachment."""

    person_id: int = Field(serialization_alias="personId")


class AttachmentRecord(ResponseModel):
    """Common attachment resource fields returned by Follow Up Boss."""

    created_at: str | None = Field(default=None, alias="createdAt")
    created_by_id: int | None = Field(default=None, alias="createdById")
    created_by_name: str | None = Field(default=None, alias="createdByName")
    file_name: str | None = Field(default=None, alias="fileName")
    file_size: int | None = Field(default=None, alias="fileSize")
    id: int
    mime_type: str | None = Field(default=None, alias="mimeType")
    status: str | None = None
    thumbnail_uri: str | None = Field(default=None, alias="thumbnailUri")
    uri: str | None = None


class DealAttachmentRecord(AttachmentRecord):
    """Deal attachment resource returned by Follow Up Boss."""

    deal_id: int | None = Field(default=None, alias="dealId")


class PersonAttachmentRecord(AttachmentRecord):
    """Person attachment resource returned by Follow Up Boss."""

    is_external: int | bool | None = Field(default=None, alias="is_external")
    person_id: int | None = Field(default=None, alias="personId")
    system_id: int | None = Field(default=None, alias="system_id")
