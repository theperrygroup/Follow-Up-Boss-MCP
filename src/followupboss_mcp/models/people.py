"""People models."""

from __future__ import annotations

from datetime import datetime

from pydantic import Field, field_validator, model_validator

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

    assigned_lender_id: int | None = Field(default=None, serialization_alias="assignedLenderId")
    assigned_lender_name: str | None = Field(
        default=None,
        serialization_alias="assignedLenderName",
    )
    assigned_pond_id: int | None = Field(default=None, serialization_alias="assignedPondId")
    assigned_to: str | None = Field(default=None, serialization_alias="assignedTo")
    assigned_user_id: int | None = Field(default=None, serialization_alias="assignedUserId")
    contacted: bool | None = None
    created_after: datetime | None = Field(default=None, serialization_alias="createdAfter")
    created_before: datetime | None = Field(default=None, serialization_alias="createdBefore")
    custom_field_filters: dict[str, str] | None = Field(default=None, exclude=True)
    email: str | None = None
    first_name: str | None = Field(default=None, serialization_alias="firstName")
    include_trash: bool | None = Field(default=None, serialization_alias="includeTrash")
    include_unclaimed: bool | None = Field(default=None, serialization_alias="includeUnclaimed")
    include_ponds: bool | None = Field(default=None, exclude=True)
    last_activity_after: datetime | None = Field(
        default=None,
        serialization_alias="lastActivityAfter",
    )
    last_activity_before: datetime | None = Field(
        default=None,
        serialization_alias="lastActivityBefore",
    )
    last_name: str | None = Field(default=None, serialization_alias="lastName")
    name: str | None = None
    phone: str | None = None
    price_above: int | None = Field(default=None, serialization_alias="priceAbove")
    price_below: int | None = Field(default=None, serialization_alias="priceBelow")
    smart_list_id: int | None = Field(default=None, serialization_alias="smartListId")
    source: str | None = None
    stage: str | None = None
    tags: str | None = None
    updated_after: datetime | None = Field(default=None, serialization_alias="updatedAfter")
    updated_before: datetime | None = Field(default=None, serialization_alias="updatedBefore")

    @field_validator("assigned_lender_id", "assigned_pond_id", "assigned_user_id", "smart_list_id")
    @classmethod
    def _validate_positive_ids(cls, value: int | None) -> int | None:
        """Require positive search identifier filters when supplied.

        Args:
            value: Candidate Follow Up Boss identifier.

        Returns:
            The validated identifier or `None`.

        Raises:
            ValueError: If the identifier is not positive.
        """
        if value is not None and value <= 0:
            raise ValueError("People search IDs must be positive.")
        return value


class PersonLookupRequest(QueryModel):
    """Fields selection for a person lookup."""

    fields: list[str] | None = None


class PersonDuplicateCheckRequest(QueryModel):
    """Query parameters for the people duplicate-check endpoint."""

    email: str | None = None
    phone: str | None = None

    @model_validator(mode="after")
    def _require_email_or_phone(self) -> PersonDuplicateCheckRequest:
        """Require at least one duplicate-check identifier.

        Returns:
            The validated request instance.

        Raises:
            ValueError: If neither an email address nor a phone number is supplied.
        """
        if self.email is None and self.phone is None:
            raise ValueError("Duplicate checks must include either email or phone.")
        return self


class UnclaimedPeopleListRequest(QueryModel):
    """Search filters for the unclaimed-people collection."""

    limit: int | None = None
    offset: int | None = None


class ClaimPersonRequest(RequestModel):
    """Strict request model for claiming an unclaimed person."""

    person_id: int = Field(serialization_alias="personId")


class IgnoreUnclaimedPersonRequest(RequestModel):
    """Strict request model for ignoring an unclaimed person."""

    person_id: int = Field(serialization_alias="personId")


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


class PersonPicture(ResponseModel):
    """Minimal picture payload nested under people resources."""

    small: str | None = None


class PersonDuplicateCheckRecord(ResponseModel):
    """Duplicate-check result for a person lookup."""

    assigned_to: str | None = Field(default=None, alias="assignedTo")
    found: bool
    matched_by: str | None = Field(default=None, alias="matchedBy")


class PersonRecord(ResponseModel):
    """Person resource returned by the API."""

    addresses: list[MailingAddress] = Field(default_factory=list)
    assigned_lender_id: int | None = Field(default=None, alias="assignedLenderId")
    assigned_lender_name: str | None = Field(default=None, alias="assignedLenderName")
    assigned_to: str | None = Field(default=None, alias="assignedTo")
    assigned_user_id: int | None = Field(default=None, alias="assignedUserId")
    claimed: bool | None = None
    contacted: bool | None = None
    created: str | None = None
    created_via: str | None = Field(default=None, alias="createdVia")
    delayed: bool | None = None
    emails: list[EmailAddress] = Field(default_factory=list)
    first_name: str | None = Field(default=None, alias="firstName")
    id: int
    last_activity: str | None = Field(default=None, alias="lastActivity")
    last_communication: JsonValue = Field(default=None, alias="lastCommunication")
    last_name: str | None = Field(default=None, alias="lastName")
    name: str | None = None
    picture: PersonPicture | None = None
    phones: list[PhoneNumber] = Field(default_factory=list)
    price: int | None = None
    source: str | None = None
    source_id: int | None = Field(default=None, alias="sourceId")
    source_url: str | None = Field(default=None, alias="sourceUrl")
    stage: str | None = None
    stage_id: int | None = Field(default=None, alias="stageId")
    tags: list[str] = Field(default_factory=list)
    updated: str | None = None
