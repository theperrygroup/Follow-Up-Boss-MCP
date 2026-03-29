"""People models."""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from followupboss_mcp.models.common import (
    CommonListQuery,
    EmailAddress,
    JsonValue,
    MailingAddress,
    PhoneNumber,
    QueryModel,
    RequestModel,
    ResponseModel,
)


class PeopleSearchRequest(CommonListQuery):
    """Search filters for the people collection."""

    assigned_user_id: int | None = Field(default=None, serialization_alias="assignedUserId")
    created_after: datetime | None = Field(default=None, serialization_alias="createdAfter")
    created_before: datetime | None = Field(default=None, serialization_alias="createdBefore")
    custom_field_filters: dict[str, str] | None = Field(default=None, exclude=True)
    email: str | None = None
    first_name: str | None = Field(default=None, serialization_alias="firstName")
    include_trash: bool | None = Field(default=None, serialization_alias="includeTrash")
    last_name: str | None = Field(default=None, serialization_alias="lastName")
    name: str | None = None
    phone: str | None = None
    source: str | None = None
    stage: str | None = None
    updated_after: datetime | None = Field(default=None, serialization_alias="updatedAfter")
    updated_before: datetime | None = Field(default=None, serialization_alias="updatedBefore")


class PersonLookupRequest(QueryModel):
    """Fields selection for a person lookup."""

    fields: list[str] | None = None


class CreatePersonRequest(RequestModel):
    """Strict request model for creating a person."""

    addresses: list[MailingAddress] | None = None
    assigned_lender_id: int | None = Field(default=None, serialization_alias="assignedLenderId")
    assigned_lender_name: str | None = Field(default=None, serialization_alias="assignedLenderName")
    assigned_pond_id: int | None = Field(default=None, serialization_alias="assignedPondId")
    assigned_to: str | None = Field(default=None, serialization_alias="assignedTo")
    assigned_user_id: int | None = Field(default=None, serialization_alias="assignedUserId")
    background: str | None = None
    collaborators: list[int] | None = None
    contacted: bool | None = None
    created_at: datetime | None = Field(default=None, serialization_alias="createdAt")
    custom_fields: dict[str, JsonValue] | None = None
    deduplicate: bool | None = None
    emails: list[EmailAddress] | None = None
    first_name: str | None = Field(default=None, serialization_alias="firstName")
    last_name: str | None = Field(default=None, serialization_alias="lastName")
    phones: list[PhoneNumber] | None = None
    price: int | None = None
    source: str | None = None
    source_url: str | None = Field(default=None, serialization_alias="sourceUrl")
    stage: str | None = None
    tags: list[str] | None = None
    timeframe_id: int | None = Field(default=None, serialization_alias="timeframeId")


class UpdatePersonRequest(RequestModel):
    """Strict request model for updating a person."""

    addresses: list[MailingAddress] | None = None
    assigned_lender_id: int | None = Field(default=None, serialization_alias="assignedLenderId")
    assigned_lender_name: str | None = Field(default=None, serialization_alias="assignedLenderName")
    assigned_pond_id: int | None = Field(default=None, serialization_alias="assignedPondId")
    assigned_to: str | None = Field(default=None, serialization_alias="assignedTo")
    assigned_user_id: int | None = Field(default=None, serialization_alias="assignedUserId")
    background: str | None = None
    contacted: bool | None = None
    custom_fields: dict[str, JsonValue] | None = None
    emails: list[EmailAddress] | None = None
    first_name: str | None = Field(default=None, serialization_alias="firstName")
    last_name: str | None = Field(default=None, serialization_alias="lastName")
    merge_tags: bool | None = Field(default=None, serialization_alias="mergeTags")
    phones: list[PhoneNumber] | None = None
    price: int | None = None
    stage: str | None = None
    tags: list[str] | None = None
    timeframe_id: int | None = Field(default=None, serialization_alias="timeframeId")


class PersonRecord(ResponseModel):
    """Person resource returned by the API."""

    addresses: list[MailingAddress] = Field(default_factory=list)
    assigned_lender_id: int | None = Field(default=None, alias="assignedLenderId")
    assigned_user_id: int | None = Field(default=None, alias="assignedUserId")
    contacted: bool | None = None
    created: str | None = None
    created_via: str | None = Field(default=None, alias="createdVia")
    emails: list[EmailAddress] = Field(default_factory=list)
    first_name: str | None = Field(default=None, alias="firstName")
    id: int
    last_activity: str | None = Field(default=None, alias="lastActivity")
    last_name: str | None = Field(default=None, alias="lastName")
    name: str | None = None
    phones: list[PhoneNumber] = Field(default_factory=list)
    price: int | None = None
    source: str | None = None
    source_url: str | None = Field(default=None, alias="sourceUrl")
    stage: str | None = None
    stage_id: int | None = Field(default=None, alias="stageId")
    updated: str | None = None
