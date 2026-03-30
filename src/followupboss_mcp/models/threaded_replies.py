"""Threaded reply models."""

from __future__ import annotations

from pydantic import Field

from followupboss_mcp.models.common import ResponseModel
from followupboss_mcp.models.reactions import ReactionRecord


class ThreadedReplyRecord(ResponseModel):
    """Threaded reply resource returned by the API."""

    body: str | None = None
    created: str | None = None
    created_by_id: int | None = Field(default=None, alias="createdById")
    id: int
    reactions: ReactionRecord | list[ReactionRecord] | None = None
    ref_id: int | None = Field(default=None, alias="refId")
    ref_type: str | None = Field(default=None, alias="refType")
    updated: str | None = None
