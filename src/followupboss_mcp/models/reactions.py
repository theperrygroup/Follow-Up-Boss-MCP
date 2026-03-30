"""Reaction models."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from followupboss_mcp.models.common import QueryModel, RequestModel, ResponseModel

type ReactionRefType = Literal["Note", "Call", "ThreadedReply"]


class CreateReactionRequest(RequestModel):
    """Strict request model for adding a reaction."""

    body: str


class DeleteReactionRequest(QueryModel):
    """Query parameters for deleting a reaction."""

    emoji: str | None = None


class ReactionRecord(ResponseModel):
    """Reaction resource returned by the API."""

    body: str | None = None
    created: str | None = None
    created_by: str | None = Field(default=None, alias="createdBy")
    created_by_id: int | None = Field(default=None, alias="createdById")
    id: int
    ref_id: int | None = Field(default=None, alias="refId")
    ref_type: str | None = Field(default=None, alias="refType")


class ReactionAckRecord(ResponseModel):
    """Empty acknowledgement returned by mutation reaction endpoints."""
