"""Shared request and response models."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

type JsonValue = None | bool | int | float | str | list["JsonValue"] | dict[str, "JsonValue"]


class RequestModel(BaseModel):
    """Base class for strict request models."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class QueryModel(RequestModel):
    """Base class for query parameter models."""

    def to_query_params(self) -> dict[str, str]:
        """Serialize the model into HTTP query parameters."""
        serialized: dict[str, str] = {}
        for key, value in self.model_dump(by_alias=True, exclude_none=True).items():
            serialized[key] = serialize_query_value(value)
        return serialized


class ResponseModel(BaseModel):
    """Base class for forward-compatible response models."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class EmailAddress(ResponseModel):
    """An email address attached to a Follow Up Boss resource."""

    type: str | None = None
    value: str


class PhoneNumber(ResponseModel):
    """A phone number attached to a Follow Up Boss resource."""

    type: str | None = None
    value: str


class MailingAddress(ResponseModel):
    """A mailing or property address."""

    city: str | None = None
    code: str | None = None
    state: str | None = None
    street: str | None = None


class ResourcePicture(ResponseModel):
    """A profile picture attached to a Follow Up Boss resource.

    Follow Up Boss returns a resource picture either as a single URL string or as
    an object containing one or more sized image URLs (for example ``small`` or
    ``original``). Response models therefore type picture fields as
    ``ResourcePicture | str | None`` so a string URL, a sized-variant object, or a
    missing value all parse without raising. The forward-compatible base
    configuration preserves any additional sizes the API may add.
    """

    large: str | None = None
    original: str | None = None
    small: str | None = None
    thumb: str | None = None


class CommonListQuery(QueryModel):
    """Common collection query parameters documented by Follow Up Boss."""

    fields: list[str] | None = None
    id: int | None = None
    ids: list[int] | None = None
    id_greater_than: int | None = Field(default=None, serialization_alias="idGreaterThan")
    id_less_than: int | None = Field(default=None, serialization_alias="idLessThan")
    limit: int | None = None
    next_token: str | None = Field(default=None, serialization_alias="next")
    offset: int | None = None
    sort: str | None = None


def serialize_query_value(value: object) -> str:
    """Serialize a query value into a string accepted by httpx."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int | float | str):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, list):
        return ",".join(serialize_query_value(item) for item in value)
    raise TypeError(f"Unsupported query value: {value!r}")
