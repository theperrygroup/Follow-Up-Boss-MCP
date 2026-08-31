"""Deal and deal custom field models."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from pydantic import Field, field_validator, model_validator

from followupboss_mcp.models.common import JsonValue, QueryModel, RequestModel, ResponseModel
from followupboss_mcp.models.custom_fields import CustomFieldType, DropdownChoiceMap

type DealCustomFieldsInput = Annotated[
    dict[str, JsonValue],
    Field(
        description=(
            "Deal custom fields keyed by Follow Up Boss API names beginning with 'custom'. "
            "Use followupboss_list_deal_custom_fields to discover valid names."
        ),
        json_schema_extra={"propertyNames": {"pattern": "^custom"}},
    ),
]


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


class CreateDealCustomFieldRequest(RequestModel):
    """Strict request model for creating a deal custom field."""

    choices: list[str] | None = None
    hide_if_empty: bool | None = Field(default=None, serialization_alias="hideIfEmpty")
    is_recurring: bool | None = Field(default=None, serialization_alias="isRecurring")
    label: str
    order_weight: int | None = Field(default=None, serialization_alias="orderWeight")
    read_only: bool | None = Field(default=None, serialization_alias="readOnly")
    type: CustomFieldType

    @model_validator(mode="after")
    def _require_dropdown_choices(self) -> CreateDealCustomFieldRequest:
        """Require dropdown fields to provide choices.

        Returns:
            The validated request instance.

        Raises:
            ValueError: If a dropdown field omits its choices.
        """
        if self.type == "dropdown" and not self.choices:
            raise ValueError("Dropdown deal custom fields must provide at least one choice.")
        return self


class UpdateDealCustomFieldRequest(RequestModel):
    """Strict request model for updating a deal custom field."""

    choices: list[str] | None = None
    dropdown_choice_map: DropdownChoiceMap | None = Field(
        default=None,
        serialization_alias="dropdownChoiceMap",
    )
    hide_if_empty: bool | None = Field(default=None, serialization_alias="hideIfEmpty")
    is_recurring: bool | None = Field(default=None, serialization_alias="isRecurring")
    label: str | None = None
    order_weight: int | None = Field(default=None, serialization_alias="orderWeight")
    read_only: bool | None = Field(default=None, serialization_alias="readOnly")
    type: CustomFieldType | None = None

    @model_validator(mode="after")
    def _require_dropdown_choices(self) -> UpdateDealCustomFieldRequest:
        """Require dropdown choices when explicitly changing the field type.

        Returns:
            The validated request instance.

        Raises:
            ValueError: If a dropdown field update omits its choices.
        """
        if self.type == "dropdown" and self.choices is None:
            raise ValueError("Dropdown deal custom field updates must provide choices.")
        return self

    @model_validator(mode="after")
    def _require_mutation(self) -> UpdateDealCustomFieldRequest:
        """Require at least one deal-custom-field mutation.

        Returns:
            The validated request instance.

        Raises:
            ValueError: If no update fields are provided.
        """
        if all(
            value is None
            for value in (
                self.label,
                self.type,
                self.choices,
                self.is_recurring,
                self.hide_if_empty,
                self.order_weight,
                self.read_only,
                self.dropdown_choice_map,
            )
        ):
            raise ValueError("At least one deal custom field update field must be provided.")
        return self


class CreateDealRequest(RequestModel):
    """Strict request model for creating a deal."""

    agent_commission: int | None = Field(default=None, serialization_alias="agentCommission")
    commission_value: int | None = Field(default=None, serialization_alias="commissionValue")
    custom_fields: DealCustomFieldsInput | None = None
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

    @field_validator("custom_fields")
    @classmethod
    def _validate_custom_field_names(
        cls,
        value: dict[str, JsonValue] | None,
    ) -> dict[str, JsonValue] | None:
        """Reject keys that cannot name Follow Up Boss deal custom fields."""
        _require_deal_custom_field_names(value)
        return value


class UpdateDealRequest(RequestModel):
    """Strict request model for updating a deal."""

    agent_commission: int | None = Field(default=None, serialization_alias="agentCommision")
    commission_value: int | None = Field(default=None, serialization_alias="commissionValue")
    custom_fields: DealCustomFieldsInput | None = None
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

    @field_validator("custom_fields")
    @classmethod
    def _validate_custom_field_names(
        cls,
        value: dict[str, JsonValue] | None,
    ) -> dict[str, JsonValue] | None:
        """Reject keys that cannot name Follow Up Boss deal custom fields."""
        _require_deal_custom_field_names(value)
        return value


def _require_deal_custom_field_names(custom_fields: dict[str, JsonValue] | None) -> None:
    """Require API-native deal custom field keys at the request-model boundary."""
    if custom_fields is None:
        return
    if any(not name.startswith("custom") for name in custom_fields):
        raise ValueError(
            "Deal custom field keys must use Follow Up Boss field names that start with 'custom'."
        )


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
    type: str | int | None = None
    users: list[DealUserSummary] = Field(default_factory=list)


class DealCustomFieldRecord(ResponseModel):
    """Deal custom field definition."""

    choices: list[str] = Field(default_factory=list)
    hide_if_empty: bool | None = Field(default=None, alias="hideIfEmpty")
    id: int
    is_recurring: bool | None = Field(default=None, alias="isRecurring")
    label: str
    name: str
    order_weight: int | None = Field(default=None, alias="orderWeight")
    read_only: bool | None = Field(default=None, alias="readOnly")
    type: str
