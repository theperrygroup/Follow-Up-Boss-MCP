"""Appointment models."""

from __future__ import annotations

from datetime import datetime

from pydantic import Field, model_validator

from followupboss_mcp.datetimes import (
    ensure_timezone_aware,
    normalize_local_datetime,
    resolve_default_timezone,
)
from followupboss_mcp.models.common import QueryModel, RequestModel, ResponseModel


class AppointmentListRequest(QueryModel):
    """Search filters for the appointments collection."""

    end: datetime | None = None
    limit: int | None = None
    offset: int | None = None
    person_id: int | list[int] | None = Field(default=None, serialization_alias="personId")
    start: datetime | None = None
    user_id: int | None = Field(default=None, serialization_alias="userId")

    @model_validator(mode="after")
    def _require_start_end_pair(self) -> AppointmentListRequest:
        """Require `start` and `end` to be provided together.

        Returns:
            The validated request instance.

        Raises:
            ValueError: If only one side of the date range is provided.
        """
        if (self.start is None) != (self.end is None):
            raise ValueError("start and end must be provided together.")
        return self

    @model_validator(mode="after")
    def _localize_naive_datetimes(self) -> AppointmentListRequest:
        """Localize naive `start`/`end` filters to the configured default timezone.

        Follow Up Boss treats offset-less datetimes as UTC, so a naive local
        time would query the wrong window. Naive values are localized only when
        a default timezone is configured; aware values are left untouched.

        Returns:
            The normalized request instance.
        """
        self.start = normalize_local_datetime(self.start)
        self.end = normalize_local_datetime(self.end)
        return self


class AppointmentInviteeInput(RequestModel):
    """Invitee payload for appointment create and update requests."""

    email: str | None = None
    name: str | None = None
    person_id: int | None = Field(
        default=None,
        validation_alias="personId",
        serialization_alias="personId",
    )
    picture: str | None = None
    user_id: int | None = Field(
        default=None,
        validation_alias="userId",
        serialization_alias="userId",
    )


class AppointmentWriteRequest(RequestModel):
    """Common writable appointment fields shared by create and update requests."""

    all_day: bool | None = Field(default=None, serialization_alias="allDay")
    description: str | None = None
    end: datetime
    invitees: list[AppointmentInviteeInput] | None = None
    location: str | None = None
    outcome_id: int | None = Field(default=None, serialization_alias="outcomeId")
    send_invitation: bool | None = Field(default=None, serialization_alias="sendInvitation")
    start: datetime
    title: str
    type_id: int | None = Field(default=None, serialization_alias="typeId")

    @model_validator(mode="after")
    def _localize_naive_datetimes(self) -> AppointmentWriteRequest:
        """Localize naive `start`/`end` values to the configured default timezone.

        Follow Up Boss interprets offset-less datetimes as UTC, which would shift
        a spoken local time (such as "3:30pm") to the wrong instant. Naive values
        are localized only when a default timezone is configured; values that
        already carry an offset are preserved exactly.

        Returns:
            The normalized request instance.
        """
        start = normalize_local_datetime(self.start)
        end = normalize_local_datetime(self.end)
        if start is not None:
            self.start = start
        if end is not None:
            self.end = end
        return self


class CreateAppointmentRequest(AppointmentWriteRequest):
    """Strict request model for creating an appointment."""

    created_by_id: int | None = Field(default=None, serialization_alias="createdById")


class UpdateAppointmentRequest(AppointmentWriteRequest):
    """Strict request model for updating an appointment."""


class AppointmentInviteePicture(ResponseModel):
    """Picture payload returned for an appointment invitee."""

    small: str | None = None


class AppointmentInvitee(ResponseModel):
    """Invitee returned on an appointment resource."""

    email: str | None = None
    name: str | None = None
    person_id: int | None = Field(default=None, alias="personId")
    picture: AppointmentInviteePicture | str | None = None
    user_id: int | None = Field(default=None, alias="userId")


class AppointmentRecord(ResponseModel):
    """Appointment resource returned by the API."""

    all_day: bool | None = Field(default=None, alias="allDay")
    created: str | None = None
    created_by_id: int | None = Field(default=None, alias="createdById")
    description: str | None = None
    details_visible: bool | None = Field(default=None, alias="detailsVisible")
    end: str | None = None
    external_calendar_id: str | None = Field(default=None, alias="externalCalendarId")
    external_event_link: str | None = Field(default=None, alias="externalEventLink")
    id: int
    invitees: list[AppointmentInvitee] = Field(default_factory=list)
    is_editable: bool | None = Field(default=None, alias="isEditable")
    location: str | None = None
    origin_fub: bool | None = Field(default=None, alias="originFub")
    outcome: str | None = None
    outcome_id: int | None = Field(default=None, alias="outcomeId")
    start: str | None = None
    title: str | None = None
    type: str | None = None
    type_id: int | None = Field(default=None, alias="typeId")
    updated: str | None = None
    updated_by_id: int | None = Field(default=None, alias="updatedById")
