"""Custom field models."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from followupboss_mcp.models.common import CommonListQuery, RequestModel, ResponseModel

type CustomFieldType = Literal["text", "date", "number", "dropdown"]
type DropdownChoiceMap = dict[str, int] | list[int]


class CustomFieldListRequest(CommonListQuery):
    """Search filters for the custom fields collection."""

    label: str | None = None


class CreateCustomFieldRequest(RequestModel):
    """Strict request model for creating a custom field."""

    choices: list[str] | None = None
    hide_if_empty: bool | None = Field(default=None, serialization_alias="hideIfEmpty")
    is_recurring: bool | None = Field(default=None, serialization_alias="isRecurring")
    label: str
    order_weight: int | None = Field(default=None, serialization_alias="orderWeight")
    type: CustomFieldType

    @model_validator(mode="after")
    def _require_dropdown_choices(self) -> CreateCustomFieldRequest:
        """Require dropdown fields to provide choices.

        Returns:
            The validated request instance.

        Raises:
            ValueError: If a dropdown field omits its choices.
        """
        if self.type == "dropdown" and not self.choices:
            raise ValueError("Dropdown custom fields must provide at least one choice.")
        return self


class UpdateCustomFieldRequest(RequestModel):
    """Strict request model for updating a custom field."""

    choices: list[str] | None = None
    dropdown_choice_map: DropdownChoiceMap | None = Field(
        default=None,
        serialization_alias="dropdownChoiceMap",
    )
    hide_if_empty: bool | None = Field(default=None, serialization_alias="hideIfEmpty")
    is_recurring: bool | None = Field(default=None, serialization_alias="isRecurring")
    label: str | None = None
    order_weight: int | None = Field(default=None, serialization_alias="orderWeight")

    @model_validator(mode="after")
    def _require_mutation(self) -> UpdateCustomFieldRequest:
        """Require at least one custom-field mutation.

        Returns:
            The validated request instance.

        Raises:
            ValueError: If no update fields are provided.
        """
        if all(
            value is None
            for value in (
                self.label,
                self.choices,
                self.is_recurring,
                self.hide_if_empty,
                self.order_weight,
                self.dropdown_choice_map,
            )
        ):
            raise ValueError("At least one custom field update field must be provided.")
        return self


class CustomFieldRecord(ResponseModel):
    """Custom field definition."""

    choices: list[str] = Field(default_factory=list)
    hide_if_empty: bool | None = Field(default=None, alias="hideIfEmpty")
    id: int | None = None
    is_recurring: bool | None = Field(default=None, alias="isRecurring")
    label: str | None = None
    name: str | None = None
    order_weight: int | None = Field(default=None, alias="orderWeight")
    type: str | None = None
