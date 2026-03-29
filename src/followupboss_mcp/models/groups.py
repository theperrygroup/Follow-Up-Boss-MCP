"""Group models."""

from __future__ import annotations

from pydantic import Field, model_validator

from followupboss_mcp.models.common import QueryModel, RequestModel, ResponseModel


class GroupListRequest(QueryModel):
    """Search filters for the groups collection."""

    sort: str | None = None
    type: str | None = None


class GroupUserSummary(ResponseModel):
    """Minimal user summary nested inside a group record."""

    first_name: str | None = Field(default=None, alias="firstName")
    id: int
    last_name: str | None = Field(default=None, alias="lastName")
    name: str | None = None
    pause_lead_distribution: bool | None = Field(default=None, alias="pauseLeadDistribution")
    role: str | None = None


class CreateGroupRequest(RequestModel):
    """Strict request model for creating a group."""

    claim_window: int | None = Field(default=None, serialization_alias="claimWindow")
    default_group_id: int | None = Field(default=None, serialization_alias="defaultGroupId")
    default_pond_id: int | None = Field(default=None, serialization_alias="defaultPondId")
    default_user_id: int | None = Field(default=None, serialization_alias="defaultUserId")
    distribution: str | None = None
    name: str
    type: str | None = None
    users: list[int]


class UpdateGroupRequest(RequestModel):
    """Strict request model for updating a group."""

    claim_window: int | None = Field(default=None, serialization_alias="claimWindow")
    default_group_id: int | None = Field(default=None, serialization_alias="defaultGroupId")
    default_pond_id: int | None = Field(default=None, serialization_alias="defaultPondId")
    default_user_id: int | None = Field(default=None, serialization_alias="defaultUserId")
    distribution: str | None = None
    name: str | None = None
    type: str | None = None
    users: list[int] | None = None

    @model_validator(mode="after")
    def _require_mutation(self) -> UpdateGroupRequest:
        """Require at least one writable group field.

        Returns:
            The validated request instance.

        Raises:
            ValueError: If no group fields are provided for the update.
        """
        if (
            self.name is None
            and self.distribution is None
            and self.users is None
            and self.type is None
            and self.claim_window is None
            and self.default_group_id is None
            and self.default_pond_id is None
            and self.default_user_id is None
        ):
            raise ValueError("At least one group field must be provided.")
        return self


class GroupRecord(ResponseModel):
    """Group resource returned by the API."""

    claim_window: int | None = Field(default=None, alias="claimWindow")
    default_group_id: int | None = Field(default=None, alias="defaultGroupId")
    default_pond_id: int | None = Field(default=None, alias="defaultPondId")
    default_user_id: int | None = Field(default=None, alias="defaultUserId")
    distribution: str | None = None
    id: int
    is_primary: bool | None = Field(default=None, alias="isPrimary")
    name: str | None = None
    next_round_robin_user: int | None = Field(default=None, alias="nextRoundRobinUser")
    type: str | None = None
    users: list[GroupUserSummary] = Field(default_factory=list)
