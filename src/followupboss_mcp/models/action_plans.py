"""Action plan models."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from followupboss_mcp.models.common import QueryModel, RequestModel, ResponseModel

type ActionPlanPersonStatus = Literal["Running", "Paused"]


class ActionPlanListRequest(QueryModel):
    """Search filters for the action plans collection."""

    ids: list[int] | None = None
    limit: int | None = None
    names: list[str] | None = None
    offset: int | None = None
    sort: str | None = None
    status: str | None = None

    def to_query_params(self) -> dict[str, str]:
        """Serialize the model into HTTP query parameters.

        Returns:
            The serialized query parameters for the action plans collection.
        """
        params = super().to_query_params()
        names = self.names
        if names:
            params.pop("names", None)
            params["names[]"] = ",".join(names)
        return params


class ActionPlanRecord(ResponseModel):
    """Action plan resource returned by the API."""

    created: str | None = None
    id: int
    name: str | None = None
    status: str | None = None
    updated: str | None = None


class ActionPlanPersonListRequest(QueryModel):
    """Search filters for the actionPlansPeople collection."""

    action_plan_id: int | None = Field(default=None, serialization_alias="actionPlanId")
    limit: int | None = None
    offset: int | None = None
    person_id: int | None = Field(default=None, serialization_alias="personId")


class CreateActionPlanPersonRequest(RequestModel):
    """Strict request model for applying an action plan to a person."""

    action_plan_id: int = Field(serialization_alias="actionPlanId")
    person_id: int = Field(serialization_alias="personId")


class UpdateActionPlanPersonRequest(RequestModel):
    """Strict request model for updating an action-plan-person relationship."""

    status: ActionPlanPersonStatus


class ActionPlanPersonRecord(ResponseModel):
    """Action-plan-person relationship returned by the API."""

    action_plan_id: int | None = Field(default=None, alias="actionPlanId")
    created: str | None = None
    id: int | None = None
    person_id: int | None = Field(default=None, alias="personId")
    status: str | None = None
    updated: str | None = None
