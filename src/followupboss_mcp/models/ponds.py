"""Pond models."""

from __future__ import annotations

from pydantic import Field, model_validator

from followupboss_mcp.models.common import QueryModel, RequestModel, ResponseModel


class PondListRequest(QueryModel):
    """Search filters for the ponds collection."""

    limit: int | None = None
    offset: int | None = None


class CreatePondRequest(RequestModel):
    """Strict request model for creating a pond."""

    name: str
    user_id: int = Field(serialization_alias="userId")
    user_ids: list[int] = Field(serialization_alias="userIds")


class UpdatePondRequest(RequestModel):
    """Strict request model for updating a pond."""

    name: str | None = None
    user_id: int | None = Field(default=None, serialization_alias="userId")
    user_ids: list[int] | None = Field(default=None, serialization_alias="userIds")

    @model_validator(mode="after")
    def _require_mutation(self) -> UpdatePondRequest:
        """Require at least one writable pond field.

        Returns:
            The validated request instance.

        Raises:
            ValueError: If no pond fields are provided for the update.
        """
        if self.name is None and self.user_id is None and self.user_ids is None:
            raise ValueError("At least one pond field must be provided.")
        return self


class DeletePondRequest(QueryModel):
    """Typed query parameters for deleting a pond."""

    assign_to: int = Field(serialization_alias="assignTo")


class PondRecord(ResponseModel):
    """Pond resource returned by the API."""

    id: int
    name: str | None = None
    user_id: int | None = Field(default=None, alias="userId")
    user_ids: list[int] = Field(default_factory=list, alias="userIds")
