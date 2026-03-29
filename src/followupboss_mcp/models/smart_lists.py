"""Smart list models."""

from __future__ import annotations

from pydantic import Field

from followupboss_mcp.models.common import QueryModel, ResponseModel


class SmartListListRequest(QueryModel):
    """Search filters for the smart lists collection."""

    fub2: bool | None = None
    include_all: bool | None = Field(default=None, serialization_alias="all")
    limit: int | None = None
    offset: int | None = None


class SmartListRecord(ResponseModel):
    """Smart list resource returned by the API."""

    default_smart_list_id: int | None = Field(default=None, alias="defaultSmartListId")
    description: str | None = None
    id: int
    is_fub2: bool | None = Field(default=None, alias="isFub2")
    name: str | None = None
