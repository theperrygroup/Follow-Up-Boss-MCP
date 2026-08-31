"""People relationship models."""

from __future__ import annotations

from collections.abc import Mapping

from pydantic import Field, field_validator, model_validator

from followupboss_mcp.models.common import (
    EmailAddress,
    JsonValue,
    MailingAddress,
    PhoneNumber,
    QueryModel,
    RequestModel,
    ResourcePicture,
    ResponseModel,
)


class PeopleRelationshipListRequest(QueryModel):
    """Search filters for the people relationships collection."""

    first_name: str | None = Field(default=None, serialization_alias="firstName")
    last_name: str | None = Field(default=None, serialization_alias="lastName")
    name: str | None = None
    person_id: int | None = Field(default=None, serialization_alias="personId")
    sort: str | None = None


class CreatePeopleRelationshipRequest(RequestModel):
    """Strict request model for creating a relationship for a person."""

    addresses: list[MailingAddress] | None = None
    emails: list[EmailAddress] | None = None
    first_name: str | None = Field(default=None, serialization_alias="firstName")
    last_name: str | None = Field(default=None, serialization_alias="lastName")
    person_id: int = Field(serialization_alias="personId")
    phones: list[PhoneNumber] | None = None
    type: str | None = None


class UpdatePeopleRelationshipRequest(RequestModel):
    """Strict request model for updating a people relationship."""

    addresses: list[MailingAddress] | None = None
    emails: list[EmailAddress] | None = None
    first_name: str | None = Field(default=None, serialization_alias="firstName")
    last_name: str | None = Field(default=None, serialization_alias="lastName")
    phones: list[PhoneNumber] | None = None
    type: str | None = None

    @model_validator(mode="after")
    def _require_mutation(self) -> UpdatePeopleRelationshipRequest:
        """Require at least one mutation field.

        Returns:
            The validated request instance.

        Raises:
            ValueError: If no update fields are provided.
        """
        if all(
            value is None
            for value in (
                self.first_name,
                self.last_name,
                self.type,
                self.emails,
                self.phones,
                self.addresses,
            )
        ):
            raise ValueError("At least one people relationship field must be provided.")
        return self


class PeopleRelationshipRecord(ResponseModel):
    """People relationship resource returned by the API."""

    addresses: list[MailingAddress] = Field(default_factory=list)
    created: str | None = None
    created_by_id: int | None = Field(default=None, alias="createdById")
    emails: list[EmailAddress] = Field(default_factory=list)
    first_name: str | None = Field(default=None, alias="firstName")
    id: int | None = None
    is_priority: bool | None = Field(default=None, alias="isPriority")
    last_name: str | None = Field(default=None, alias="lastName")
    name: str | None = None
    person_id: int | None = Field(default=None, alias="personId")
    phones: list[PhoneNumber] = Field(default_factory=list)
    picture: ResourcePicture | str | None = None
    social_data: list[JsonValue] = Field(default_factory=list, alias="socialData")
    type: str | None = None
    updated: str | None = None
    updated_by_id: int | None = Field(default=None, alias="updatedById")

    @field_validator("social_data", mode="before")
    @classmethod
    def _normalize_social_data(cls, value: object) -> object:
        """Wrap the API's singleton socialData object in its canonical list shape."""
        if isinstance(value, Mapping):
            return [dict(value)]
        return value
