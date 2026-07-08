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
    ResourcePicture,
    ResponseModel,
)

type PeopleProjectionFieldsInput = list[str] | str | None

_PEOPLE_RESPONSE_FIELDS = frozenset(
    {
        "addresses",
        "assignedLenderId",
        "assignedLenderName",
        "assignedTo",
        "assignedUserId",
        "claimed",
        "contacted",
        "created",
        "createdVia",
        "delayed",
        "emails",
        "firstName",
        "id",
        "lastActivity",
        "lastCommunication",
        "lastName",
        "name",
        "phones",
        "picture",
        "price",
        "source",
        "sourceId",
        "sourceUrl",
        "stage",
        "stageId",
        "tags",
        "updated",
    }
)
_PEOPLE_FIELD_CORRECTIONS = {
    "email": "Use 'emails' for returned email addresses.",
    "phone": "Use 'phones' for returned phone numbers.",
    "notes": (
        "'notes' is not a people projection; use followupboss_list_person_activity "
        "for note and activity history."
    ),
}


def normalize_people_projection_fields(value: object) -> object:
    """Normalize people projection fields from MCP and Python callers.

    Args:
        value: Raw people projection field input. MCP clients sometimes send
            the Follow Up Boss-documented comma-separated string form, while
            Python callers commonly use a list.

    Returns:
        A list of field names for string inputs, ``None`` for blank strings, or
        the original value so Pydantic can report unsupported shapes.
    """
    if not isinstance(value, str):
        return value
    fields = [field.strip() for field in value.split(",") if field.strip()]
    return fields or None


def validate_people_projection_fields(value: list[str] | None) -> list[str] | None:
    """Validate Follow Up Boss people response projection fields.

    Args:
        value: Optional field names requested by the caller.

    Returns:
        The original field list when every field is supported.

    Raises:
        ValueError: If one or more projection fields are not known people
            response fields.
    """
    if value is None:
        return None
    invalid_fields = sorted(set(value) - _PEOPLE_RESPONSE_FIELDS)
    if invalid_fields:
        corrections = [
            _PEOPLE_FIELD_CORRECTIONS[field]
            for field in invalid_fields
            if field in _PEOPLE_FIELD_CORRECTIONS
        ]
        correction_text = f" {' '.join(corrections)}" if corrections else ""
        allowed_fields = ", ".join(sorted(_PEOPLE_RESPONSE_FIELDS))
        invalid = ", ".join(invalid_fields)
        raise ValueError(
            f"Invalid people fields: {invalid}. Allowed fields: {allowed_fields}.{correction_text}"
        )
    return value


class PeopleSearchRequest(CommonListQuery):
    """Search filters for the people collection."""

    fields: list[str] | None = Field(
        default=None,
        description=(
            "Optional people response fields. Use emails/phones for contact values; "
            "notes is not a people projection."
        ),
    )
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
    custom_field_filters: dict[str, str] | None = Field(
        default=None,
        exclude=True,
        description="Custom field filters keyed by Follow Up Boss API names starting with custom.",
    )
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

    @field_validator("fields", mode="before")
    @classmethod
    def _normalize_fields(cls, value: object) -> object:
        """Normalize comma-separated people projection fields before list validation."""
        return normalize_people_projection_fields(value)

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

    @field_validator("fields")
    @classmethod
    def _validate_fields(cls, value: list[str] | None) -> list[str] | None:
        """Validate people projection fields."""
        return validate_people_projection_fields(value)


class PersonLookupRequest(QueryModel):
    """Fields selection for a person lookup."""

    fields: list[str] | None = Field(
        default=None,
        description=(
            "Optional people response fields. Use emails/phones for contact values; "
            "notes is not a people projection."
        ),
    )

    @field_validator("fields", mode="before")
    @classmethod
    def _normalize_fields(cls, value: object) -> object:
        """Normalize comma-separated person projection fields before list validation."""
        return normalize_people_projection_fields(value)

    @field_validator("fields")
    @classmethod
    def _validate_fields(cls, value: list[str] | None) -> list[str] | None:
        """Validate people projection fields."""
        return validate_people_projection_fields(value)


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
    last_communication: dict[str, object] | str | int | None = Field(
        default=None,
        alias="lastCommunication",
    )
    last_name: str | None = Field(default=None, alias="lastName")
    name: str | None = None
    picture: ResourcePicture | str | None = None
    phones: list[PhoneNumber] = Field(default_factory=list)
    price: int | None = None
    source: str | None = None
    source_id: int | None = Field(default=None, alias="sourceId")
    source_url: str | None = Field(default=None, alias="sourceUrl")
    stage: str | None = None
    stage_id: int | None = Field(default=None, alias="stageId")
    tags: list[str] = Field(default_factory=list)
    updated: str | None = None
