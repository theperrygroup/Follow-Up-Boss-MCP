"""Task models."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import AliasChoices, Field, model_validator

from followupboss_mcp.datetimes import normalize_optional_datetime
from followupboss_mcp.models.common import CommonListQuery, JsonValue, RequestModel, ResponseModel

type TaskProjectionField = Literal[
    "assignedTo",
    "assignedUserId",
    "completed",
    "created",
    "createdBy",
    "dueDate",
    "dueDateTime",
    "id",
    "isCompleted",
    "name",
    "person",
    "personId",
    "type",
    "updated",
    "updatedBy",
]


class TaskListRequest(CommonListQuery):
    """Search filters for the tasks collection."""

    assigned_to: str | None = Field(default=None, serialization_alias="assignedTo")
    assigned_user_id: int | None = Field(default=None, serialization_alias="assignedUserId")
    due: str | None = None
    due_end: datetime | None = Field(default=None, serialization_alias="dueEnd")
    due_start: datetime | None = Field(default=None, serialization_alias="dueStart")
    is_completed: bool | None = Field(default=None, serialization_alias="isCompleted")
    name: str | None = None
    person_id: int | None = Field(default=None, serialization_alias="personId")
    type: list[str] | None = None

    @model_validator(mode="after")
    def _normalize_datetimes_to_utc(self) -> TaskListRequest:
        """Convert naive `due_start`/`due_end` filters to the UTC instant to query.

        Follow Up Boss stores times in UTC and does not honor offset suffixes, so
        a naive local time would query the wrong due-date window. Naive values are
        interpreted with the configured default timezone (when set) and converted
        to UTC; aware values are converted to UTC directly.

        Returns:
            The normalized request instance.
        """
        self.due_start = normalize_optional_datetime(self.due_start)
        self.due_end = normalize_optional_datetime(self.due_end)
        return self


class TaskPersonSummary(ResponseModel):
    """Minimal person summary nested inside a task record."""

    id: int
    name: str | None = None


class TaskWriteRequest(RequestModel):
    """Common writable task fields shared by create and update requests."""

    assigned_to: str | None = Field(default=None, serialization_alias="assignedTo")
    assigned_user_id: int | None = Field(default=None, serialization_alias="assignedUserId")
    due_date: date | None = Field(default=None, serialization_alias="dueDate")
    due_date_time: datetime | None = Field(default=None, serialization_alias="dueDateTime")
    is_completed: bool | None = Field(default=None, serialization_alias="isCompleted")
    name: str | None = None
    type: str | None = None

    @model_validator(mode="after")
    def _normalize_due_date_time_to_utc(self) -> TaskWriteRequest:
        """Convert `due_date_time` to the UTC instant Follow Up Boss stores.

        Follow Up Boss stores `dueDateTime` in UTC and does not honor an offset
        suffix on the wire, so a spoken local due time must be converted to UTC.
        A naive value is interpreted with the configured default timezone (when
        set) and converted to UTC; an aware value is converted to UTC directly. A
        naive value with no configured default timezone is left unchanged (Follow
        Up Boss treats it as UTC).

        Returns:
            The normalized request instance.
        """
        self.due_date_time = normalize_optional_datetime(self.due_date_time)
        return self


class CreateTaskRequest(TaskWriteRequest):
    """Strict request model for creating a task."""

    person_id: int = Field(serialization_alias="personId")
    remind_seconds_before: int | None = Field(
        default=None, serialization_alias="remindSecondsBefore"
    )

    @model_validator(mode="after")
    def _require_assignee(self) -> CreateTaskRequest:
        """Require either an assignee name or assignee id.

        Returns:
            The validated request instance.

        Raises:
            ValueError: If neither assignee field is provided.
        """
        if self.assigned_to is None and self.assigned_user_id is None:
            raise ValueError("Either assigned_to or assigned_user_id must be provided.")
        return self


class UpdateTaskRequest(TaskWriteRequest):
    """Strict request model for updating a task."""

    person_id: int | None = Field(default=None, serialization_alias="personId")


class TaskRecord(ResponseModel):
    """Task resource returned by the API."""

    assigned_to: str | None = Field(
        default=None,
        alias="assignedTo",
        validation_alias=AliasChoices("assignedTo", "AssignedTo"),
    )
    assigned_user_id: int | None = Field(default=None, alias="assignedUserId")
    completed: str | None = None
    created: str | None = None
    created_by: JsonValue | None = Field(default=None, alias="createdBy")
    due_date: str | None = Field(default=None, alias="dueDate")
    due_date_time: str | None = Field(default=None, alias="dueDateTime")
    id: int
    is_completed: bool | None = Field(default=None, alias="isCompleted")
    name: str | None = None
    person: TaskPersonSummary | None = None
    person_id: int | None = Field(default=None, alias="personId")
    type: str | None = None
    updated: str | None = None
    updated_by: JsonValue | None = Field(default=None, alias="updatedBy")
