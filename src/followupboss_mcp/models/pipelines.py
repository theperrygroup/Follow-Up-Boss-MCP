"""Pipeline models."""

from __future__ import annotations

from pydantic import Field, model_validator

from followupboss_mcp.models.common import QueryModel, RequestModel, ResponseModel


class PipelineListRequest(QueryModel):
    """Search filters for the pipelines collection."""

    name: str | None = None


class PipelineStageInput(RequestModel):
    """Stage payload for pipeline create and update requests."""

    closed_stage: bool | None = Field(default=None, serialization_alias="closedStage")
    color: str | None = None
    description: str | None = None
    id: int | None = None
    name: str | None = None
    order_weight: int | None = Field(default=None, serialization_alias="orderWeight")


class CreatePipelineRequest(RequestModel):
    """Strict request model for creating a pipeline."""

    description: str | None = None
    name: str
    order_weight: int | None = Field(default=None, serialization_alias="orderWeight")
    stages: list[PipelineStageInput] | None = None


class UpdatePipelineRequest(RequestModel):
    """Strict request model for updating a pipeline."""

    description: str | None = None
    name: str | None = None
    order_weight: int | None = Field(default=None, serialization_alias="orderWeight")
    stages: list[PipelineStageInput] | None = None

    @model_validator(mode="after")
    def _require_mutation(self) -> UpdatePipelineRequest:
        """Require at least one writable pipeline field.

        Returns:
            The validated request instance.

        Raises:
            ValueError: If no pipeline fields are provided for the update.
        """
        if (
            self.description is None
            and self.name is None
            and self.order_weight is None
            and self.stages is None
        ):
            raise ValueError("At least one pipeline field must be provided.")
        return self


class PipelineStageRecord(ResponseModel):
    """Pipeline stage resource returned by the API."""

    closed_stage: bool | None = Field(default=None, alias="closedStage")
    color: str | None = None
    description: str | None = None
    id: int | None = None
    name: str | None = None
    order_weight: int | None = Field(default=None, alias="orderWeight")


class PipelineRecord(ResponseModel):
    """Pipeline resource returned by the API."""

    description: str | None = None
    id: int
    name: str | None = None
    order_weight: int | None = Field(default=None, alias="orderWeight")
    stages: list[PipelineStageRecord] = Field(default_factory=list)
