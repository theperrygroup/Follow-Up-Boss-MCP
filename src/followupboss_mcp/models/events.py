"""Event models."""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from followupboss_mcp.models.common import (
    CommonListQuery,
    EmailAddress,
    JsonValue,
    MailingAddress,
    PhoneNumber,
    RequestModel,
    ResponseModel,
)


class EventPersonInput(RequestModel):
    """Person payload for an inbound event."""

    addresses: list[MailingAddress] | None = None
    assigned_lender_id: int | None = Field(
        default=None,
        validation_alias="assignedLenderId",
        serialization_alias="assignedLenderId",
    )
    assigned_lender_name: str | None = Field(
        default=None,
        validation_alias="assignedLenderName",
        serialization_alias="assignedLenderName",
    )
    assigned_to: str | None = Field(
        default=None,
        validation_alias="assignedTo",
        serialization_alias="assignedTo",
    )
    assigned_user_id: int | None = Field(
        default=None,
        validation_alias="assignedUserId",
        serialization_alias="assignedUserId",
    )
    contacted: bool | None = None
    custom_fields: dict[str, JsonValue] | None = None
    emails: list[EmailAddress] | None = None
    first_name: str | None = Field(
        default=None,
        validation_alias="firstName",
        serialization_alias="firstName",
    )
    id: int | None = None
    last_name: str | None = Field(
        default=None,
        validation_alias="lastName",
        serialization_alias="lastName",
    )
    phones: list[PhoneNumber] | None = None
    price: int | None = None
    source: str | None = None
    source_url: str | None = Field(
        default=None,
        validation_alias="sourceUrl",
        serialization_alias="sourceUrl",
    )
    stage: str | None = None
    tags: list[str] | None = None


class EventPropertyInput(RequestModel):
    """Property payload for an inbound event."""

    area: str | None = None
    bathrooms: str | None = None
    bedrooms: str | None = None
    city: str | None = None
    code: str | None = None
    for_rent: bool | None = Field(
        default=None,
        validation_alias="forRent",
        serialization_alias="forRent",
    )
    lot: str | None = None
    mls_number: str | None = Field(
        default=None,
        validation_alias="mlsNumber",
        serialization_alias="mlsNumber",
    )
    price: int | None = None
    state: str | None = None
    street: str | None = None
    type: str | None = None
    url: str | None = None


class PropertySearchInput(RequestModel):
    """Property search preferences attached to an event."""

    city: str | None = None
    code: list[str] | None = None
    max_bathrooms: float | None = Field(
        default=None,
        validation_alias="maxBathrooms",
        serialization_alias="maxBathrooms",
    )
    max_bedrooms: int | None = Field(
        default=None,
        validation_alias="maxBedrooms",
        serialization_alias="maxBedrooms",
    )
    max_price: int | None = Field(
        default=None,
        validation_alias="maxPrice",
        serialization_alias="maxPrice",
    )
    min_bathrooms: float | None = Field(
        default=None,
        validation_alias="minBathrooms",
        serialization_alias="minBathrooms",
    )
    min_bedrooms: int | None = Field(
        default=None,
        validation_alias="minBedrooms",
        serialization_alias="minBedrooms",
    )
    min_price: int | None = Field(
        default=None,
        validation_alias="minPrice",
        serialization_alias="minPrice",
    )
    neighborhood: str | None = None
    state: str | None = None
    type: str | None = None


class CampaignInput(RequestModel):
    """Campaign metadata attached to an event."""

    name: str | None = None
    source: str | None = None


class EventSearchRequest(CommonListQuery):
    """Search filters for the events collection."""

    has_property: bool | None = Field(
        default=None,
        validation_alias="hasProperty",
        serialization_alias="hasProperty",
    )
    person_id: int | None = Field(
        default=None,
        validation_alias="personId",
        serialization_alias="personId",
    )
    property_address: str | None = Field(
        default=None,
        validation_alias="propertyAddress",
        serialization_alias="propertyAddress",
    )
    type: list[str] | None = None


class CreateEventRequest(RequestModel):
    """Strict request model for sending an event to Follow Up Boss."""

    campaign: CampaignInput | None = None
    description: str | None = None
    message: str | None = None
    occurred_at: datetime | None = Field(
        default=None,
        validation_alias="occurredAt",
        serialization_alias="occurredAt",
    )
    page_duration: int | None = Field(
        default=None,
        validation_alias="pageDuration",
        serialization_alias="pageDuration",
    )
    page_referrer: str | None = Field(
        default=None,
        validation_alias="pageReferrer",
        serialization_alias="pageReferrer",
    )
    page_title: str | None = Field(
        default=None,
        validation_alias="pageTitle",
        serialization_alias="pageTitle",
    )
    page_url: str | None = Field(
        default=None,
        validation_alias="pageUrl",
        serialization_alias="pageUrl",
    )
    person: EventPersonInput
    property: EventPropertyInput | None = None
    property_search: PropertySearchInput | None = Field(
        default=None,
        validation_alias="propertySearch",
        serialization_alias="propertySearch",
    )
    source: str
    system: str
    type: str


class EventRecord(ResponseModel):
    """Event resource returned by the API."""

    created: str | None = None
    description: str | None = None
    id: int
    message: str | None = None
    person_id: int | None = Field(default=None, alias="personId")
    source: str | None = None
    type: str | None = None
    updated: str | None = None
