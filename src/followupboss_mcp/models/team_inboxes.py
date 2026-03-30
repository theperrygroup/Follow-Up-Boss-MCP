"""Team inbox models."""

from __future__ import annotations

from pydantic import Field

from followupboss_mcp.models.common import QueryModel, ResponseModel


class TeamInboxListRequest(QueryModel):
    """Search filters for the team inboxes collection."""


class TeamInboxUserSummary(ResponseModel):
    """Minimal user summary nested inside a team inbox record."""

    first_name: str | None = Field(default=None, alias="firstName")
    id: int
    last_name: str | None = Field(default=None, alias="lastName")
    name: str | None = None


class TeamInboxRecord(ResponseModel):
    """Team inbox resource returned by the API."""

    id: int
    name: str | None = None
    users: list[TeamInboxUserSummary] = Field(default_factory=list)
