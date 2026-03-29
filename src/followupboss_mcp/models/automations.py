"""Automation and automation-person models."""

from __future__ import annotations

from typing import Literal

from pydantic import Field

from followupboss_mcp.models.common import QueryModel, RequestModel, ResponseModel

type AutomationRunStatus = Literal["Initial", "Running", "Paused", "Completed"]
type AutomationPauseStatus = Literal["Running", "Paused"]


class AutomationListRequest(QueryModel):
    """Search filters for the automations collection."""

    enabled_only: bool | None = Field(default=None, serialization_alias="enabledOnly")
    limit: int | None = None
    manual_only: bool | None = Field(default=None, serialization_alias="manualOnly")
    offset: int | None = None
    status: str | None = None


class AutomationRecord(ResponseModel):
    """Automation resource returned by the API."""

    id: int
    name: str | None = None
    status: str | None = None


class AutomationPeopleListRequest(QueryModel):
    """Search filters for the automationsPeople collection."""

    automation_id: int | None = Field(default=None, serialization_alias="automationId")
    person_id: int | None = Field(default=None, serialization_alias="personId")
    status: AutomationRunStatus | None = None


class CreateAutomationPersonRequest(RequestModel):
    """Strict request model for triggering an automation for a person."""

    automation_id: int = Field(serialization_alias="automationId")
    person_id: int = Field(serialization_alias="personId")


class UpdateAutomationPersonRequest(RequestModel):
    """Strict request model for pausing or resuming an automation-person pairing."""

    status: AutomationPauseStatus


class AutomationPersonRecord(ResponseModel):
    """Automation-person pairing returned by the API."""

    automation_id: int | None = Field(default=None, alias="automationId")
    automation_name: str | None = Field(default=None, alias="automationName")
    created: str | None = None
    created_by: str | None = Field(default=None, alias="createdBy")
    created_by_id: int | None = Field(default=None, alias="createdById")
    id: int
    person_id: int | None = Field(default=None, alias="personId")
    status: str | None = None
    updated: str | None = None
    updated_by: str | None = Field(default=None, alias="updatedBy")
    updated_by_id: int | None = Field(default=None, alias="updatedById")
