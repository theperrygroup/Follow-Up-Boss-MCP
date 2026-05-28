"""Task models."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import AliasChoices, Field, model_validator

from followupboss_mcp.datetimes import normalize_local_datetime
from followupboss_mcp.models.common import CommonListQuery, JsonValue, RequestModel, ResponseModel


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
    def _localize_naive_datetimes(self) -> TaskListRequest:
        """Localize naive `due_start`/`due_end` filters to the default timezone.

        Follow Up Boss treats offset-less datetimes as UTC, so a naive local time
        would query the wrong due-date window. Naive values are localized only
        when a default timezone is configured; aware values are left untouched.

        Returns:
            The normalized request instance.
        """
        self.due_start = normalize_local_datetime(self.due_start)
        self.due_end = normalize_local_datetime(self.due_end)
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
    def _localize_naive_due_date_time(self) -> TaskWriteRequest:
        """Localize a naive `due_date_time` to the configured default timezone.

        Follow Up Boss interprets the offset-less `dueDateTime` as UTC, which
        would shift a spoken local due time to the wrong instant. The value is
        localized only when a default timezone is configured; a value that
        already carries an offset is preserved exactly.

        Returns:
            The normalized request instance.
        """
        self.due_date_time = normalize_local_datetime(self.due_date_time)
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
