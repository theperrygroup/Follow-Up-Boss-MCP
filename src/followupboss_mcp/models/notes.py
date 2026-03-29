"""Note models."""

from __future__ import annotations

from pydantic import Field

from followupboss_mcp.models.common import RequestModel, ResponseModel


class CreateNoteRequest(RequestModel):
    """Strict request model for creating a note."""

    body: str | None = None
    is_html: bool | None = Field(default=None, serialization_alias="isHtml")
    person_id: int = Field(serialization_alias="personId")
    subject: str | None = None


class UpdateNoteRequest(RequestModel):
    """Strict request model for updating a note."""

    body: str | None = None
    is_html: bool | None = Field(default=None, serialization_alias="isHtml")
    subject: str | None = None


class NoteRecord(ResponseModel):
    """Note resource returned by the API."""

    body: str | None = None
    created: str | None = None
    id: int
    is_html: bool | None = Field(default=None, alias="isHtml")
    person_id: int | None = Field(default=None, alias="personId")
    subject: str | None = None
    updated: str | None = None
