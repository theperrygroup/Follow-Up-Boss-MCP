"""Deal and deal custom field models."""

from __future__ import annotations

from datetime import date

from pydantic import Field

from followupboss_mcp.models.common import JsonValue, QueryModel, RequestModel, ResponseModel


class DealListRequest(QueryModel):
    """Search filters for the deals collection."""

    include_archived: bool | None = Field(default=None, serialization_alias="includeArchived")
    include_deleted: bool | None = Field(default=None, serialization_alias="includeDeleted")
    person_id: int | None = Field(default=None, serialization_alias="personId")
    pipeline_id: int | None = Field(default=None, serialization_alias="pipelineId")
    status: str | None = None
    user_id: int | None = Field(default=None, serialization_alias="userId")

    def to_query_params(self) -> dict[str, str]:
        """Serialize the model into HTTP query parameters.

        Returns:
            The serialized query parameters for the deals collection.
        """
        params = super().to_query_params()
        if self.include_archived is not None:
            params["includeArchived"] = "1" if self.include_archived else "0"
        if self.include_deleted is not None:
            params["includeDeleted"] = "1" if self.include_deleted else "0"
        return params


class DealCustomFieldListRequest(QueryModel):
    """Search filters for the deal custom fields collection."""

    label: str | None = None
    limit: int | None = None
    offset: int | None = None
    sort: str | None = None


class CreateDealRequest(RequestModel):
    """Strict request model for creating a deal."""

    agent_commission: int | None = Field(default=None, serialization_alias="agentCommission")
    commission_value: int | None = Field(default=None, serialization_alias="commissionValue")
    custom_fields: dict[str, JsonValue] | None = None
    description: str | None = None
    due_diligence_date: date | None = Field(default=None, serialization_alias="dueDiligenceDate")
    earnest_money_due_date: date | None = Field(
        default=None,
        serialization_alias="earnestMoneyDueDate",
    )
    final_walk_through_date: date | None = Field(
        default=None,
        serialization_alias="finalWalkThroughDate",
    )
    mutual_acceptance_date: date | None = Field(
        default=None,
        serialization_alias="mutualAcceptanceDate",
    )
    name: str
    order_weight: int | None = Field(default=None, serialization_alias="orderWeight")
    people_ids: list[int] | None = Field(default=None, serialization_alias="peopleIds")
    possession_date: date | None = Field(default=None, serialization_alias="possessionDate")
    price: int | None = None
    projected_close_date: date | None = Field(
        default=None, serialization_alias="projectedCloseDate"
    )
    stage_id: int = Field(serialization_alias="stageId")
    team_commission: int | None = Field(default=None, serialization_alias="teamCommission")
    user_ids: list[int] | None = Field(default=None, serialization_alias="userIds")


class UpdateDealRequest(RequestModel):
    """Strict request model for updating a deal."""

    agent_commission: int | None = Field(default=None, serialization_alias="agentCommision")
    commission_value: int | None = Field(default=None, serialization_alias="commissionValue")
    custom_fields: dict[str, JsonValue] | None = None
    description: str | None = None
    due_diligence_date: date | None = Field(default=None, serialization_alias="dueDiligenceDate")
    earnest_money_due_date: date | None = Field(
        default=None,
        serialization_alias="earnestMoneyDueDate",
    )
    final_walk_through_date: date | None = Field(
        default=None,
        serialization_alias="finalWalkThroughDate",
    )
    mutual_acceptance_date: date | None = Field(
        default=None,
        serialization_alias="mutualAcceptanceDate",
    )
    name: str | None = None
    people_ids: list[int] | None = Field(default=None, serialization_alias="peopleIds")
    possession_date: date | None = Field(default=None, serialization_alias="possessionDate")
    price: int | None = None
    projected_close_date: date | None = Field(
        default=None, serialization_alias="projectedCloseDate"
    )
    stage_id: int | None = Field(default=None, serialization_alias="stageId")
    team_commission: int | None = Field(default=None, serialization_alias="teamComission")
    user_ids: list[int] | None = Field(default=None, serialization_alias="userIds")


class DealPersonSummary(ResponseModel):
    """Minimal person summary nested inside a deal record."""

    avatar: str | None = None
    id: int
    name: str | None = None


class DealUserSummary(ResponseModel):
    """Minimal user summary nested inside a deal record."""

    id: int
    name: str | None = None


class DealRecord(ResponseModel):
    """Deal resource returned by the API."""

    agent_commission: int | None = Field(default=None, alias="agentCommission")
    created_at: str | None = Field(default=None, alias="createdAt")
    description: str | None = None
    entered_stage_at: str | None = Field(default=None, alias="enteredStageAt")
    id: int
    name: str | None = None
    order_weight: int | None = Field(default=None, alias="orderWeight")
    people: list[DealPersonSummary] = Field(default_factory=list)
    pipeline_id: int | None = Field(default=None, alias="pipelineId")
    price: int | None = None
    projected_close_date: str | None = Field(default=None, alias="projectedCloseDate")
    stage_id: int | None = Field(default=None, alias="stageId")
    status: str | None = None
    team_commission: int | None = Field(default=None, alias="teamCommission")
    type: str | None = None
    users: list[DealUserSummary] = Field(default_factory=list)


class DealCustomFieldRecord(ResponseModel):
    """Deal custom field definition."""

    hide_if_empty: bool | None = Field(default=None, alias="hideIfEmpty")
    id: int
    label: str
    name: str
    order_weight: int | None = Field(default=None, alias="orderWeight")
    read_only: bool | None = Field(default=None, alias="readOnly")
    type: str
