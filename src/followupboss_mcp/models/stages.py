"""Stage models."""

from __future__ import annotations

from pydantic import Field, model_validator

from followupboss_mcp.models.common import QueryModel, RequestModel, ResponseModel


class StageListRequest(QueryModel):
    """Search filters for the stages collection."""

    limit: int | None = None
    offset: int | None = None
    sort: str | None = None


class CreateStageRequest(RequestModel):
    """Strict request model for creating a stage."""

    name: str
    order_weight: int | None = Field(default=None, serialization_alias="orderWeight")


class UpdateStageRequest(RequestModel):
    """Strict request model for updating a stage."""

    name: str | None = None
    order_weight: int | None = Field(default=None, serialization_alias="orderWeight")

    @model_validator(mode="after")
    def _require_mutation(self) -> UpdateStageRequest:
        """Require at least one writable stage field.

        Returns:
            The validated request instance.

        Raises:
            ValueError: If no stage fields are provided for the update.
        """
        if self.name is None and self.order_weight is None:
            raise ValueError("At least one stage field must be provided.")
        return self


class DeleteStageRequest(QueryModel):
    """Typed query parameters for deleting a stage."""

    assign_stage_id: int = Field(serialization_alias="assignStageId")


class StageRecord(ResponseModel):
    """Stage resource returned by the API."""

    id: int
    is_protected: bool | None = Field(default=None, alias="isProtected")
    name: str | None = None
    order_weight: int | None = Field(default=None, alias="orderWeight")
    people_count: int | None = Field(default=None, alias="peopleCount")
