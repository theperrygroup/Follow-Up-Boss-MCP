"""Team models."""

from __future__ import annotations

from pydantic import Field, model_validator

from followupboss_mcp.models.common import QueryModel, RequestModel, ResponseModel


class TeamListRequest(QueryModel):
    """Search filters for the teams collection."""

    limit: int | None = None
    offset: int | None = None


class CreateTeamRequest(RequestModel):
    """Strict request model for creating a team."""

    leader_ids: list[int] | None = Field(default=None, serialization_alias="leaderIds")
    name: str
    user_ids: list[int] = Field(serialization_alias="userIds")


class UpdateTeamRequest(RequestModel):
    """Strict request model for updating a team."""

    leader_ids: list[int] | None = Field(default=None, serialization_alias="leaderIds")
    name: str | None = None
    user_ids: list[int] | None = Field(default=None, serialization_alias="userIds")

    @model_validator(mode="after")
    def _require_mutation(self) -> UpdateTeamRequest:
        """Require at least one writable team field.

        Returns:
            The validated request instance.

        Raises:
            ValueError: If no team fields are provided for the update.
        """
        if self.name is None and self.user_ids is None and self.leader_ids is None:
            raise ValueError("At least one team field must be provided.")
        return self


class DeleteTeamRequest(QueryModel):
    """Typed query parameters for deleting a team."""

    move_to_team_id: int | None = Field(default=None, serialization_alias="moveToTeamId")


class TeamRecord(ResponseModel):
    """Team resource returned by the API."""

    id: int
    leader_ids: list[int] = Field(default_factory=list, alias="leaderIds")
    name: str | None = None
    user_ids: list[int] = Field(default_factory=list, alias="userIds")
