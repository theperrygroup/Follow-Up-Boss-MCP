"""User models."""

from __future__ import annotations

from pydantic import Field

from followupboss_mcp.models.common import CommonListQuery, ResponseModel


class UserListRequest(CommonListQuery):
    """Search filters for the users collection."""

    email: str | None = None
    include_deleted: bool | None = Field(default=None, serialization_alias="includeDeleted")
    name: str | None = None
    role: str | None = None


class UserRecord(ResponseModel):
    """User resource returned by the API."""

    created: str | None = None
    email: str | None = None
    first_name: str | None = Field(default=None, alias="firstName")
    id: int
    is_owner: bool | None = Field(default=None, alias="isOwner")
    last_name: str | None = Field(default=None, alias="lastName")
    name: str | None = None
    phone: str | None = None
    role: str | None = None
    status: str | None = None
    updated: str | None = None
