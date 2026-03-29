"""Call models."""

from __future__ import annotations

from pydantic import Field

from followupboss_mcp.models.common import QueryModel, RequestModel, ResponseModel


class CallListRequest(QueryModel):
    """Search filters for the calls collection."""

    from_number: str | None = Field(default=None, serialization_alias="fromNumber")
    limit: int | None = None
    offset: int | None = None
    person_id: int | None = Field(default=None, serialization_alias="personId")
    phone: str | None = None
    to_number: str | None = Field(default=None, serialization_alias="toNumber")


class CallWriteRequest(RequestModel):
    """Common writable call fields shared by create and update requests."""

    duration: int | None = None
    from_number: str | None = Field(default=None, serialization_alias="fromNumber")
    is_incoming: bool | None = Field(default=None, serialization_alias="isIncoming")
    note: str | None = None
    outcome: str | None = None
    person_id: int | None = Field(default=None, serialization_alias="personId")
    phone: str | None = None
    recording_url: str | None = Field(default=None, serialization_alias="recordingUrl")
    to_number: str | None = Field(default=None, serialization_alias="toNumber")
    user_id: int | None = Field(default=None, serialization_alias="userId")


class CreateCallRequest(CallWriteRequest):
    """Strict request model for creating a call."""

    is_incoming: bool = Field(serialization_alias="isIncoming")
    person_id: int = Field(serialization_alias="personId")
    phone: str


class UpdateCallRequest(CallWriteRequest):
    """Strict request model for updating a call."""


class CallRecord(ResponseModel):
    """Call resource returned by the API."""

    created: str | None = None
    created_by_id: int | None = Field(default=None, alias="createdById")
    duration: int | None = None
    id: int
    is_incoming: bool | None = Field(default=None, alias="isIncoming")
    note: str | None = None
    outcome: str | None = None
    person_id: int | None = Field(default=None, alias="personId")
    phone: str | None = None
    recording_url: str | None = Field(default=None, alias="recordingUrl")
    ring_duration: int | None = Field(default=None, alias="ringDuration")
    updated: str | None = None
    updated_by_id: int | None = Field(default=None, alias="updatedById")
    user_id: int | None = Field(default=None, alias="userId")
    user_name: str | None = Field(default=None, alias="userName")
