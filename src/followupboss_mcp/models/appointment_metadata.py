"""Appointment outcome and appointment type models."""

from __future__ import annotations

from pydantic import Field, model_validator

from followupboss_mcp.models.common import QueryModel, RequestModel, ResponseModel


class AppointmentMetadataListRequest(QueryModel):
    """Search filters shared by appointment metadata collections."""

    limit: int | None = None
    offset: int | None = None
    sort: str | None = None


class AppointmentMetadataWriteRequest(RequestModel):
    """Common writable fields shared by appointment metadata requests."""

    name: str
    order_weight: int | None = Field(default=None, serialization_alias="orderWeight")


class AppointmentMetadataUpdateRequest(RequestModel):
    """Common writable fields shared by appointment metadata update requests."""

    name: str | None = None
    order_weight: int | None = Field(default=None, serialization_alias="orderWeight")

    @model_validator(mode="after")
    def _require_mutation(self) -> AppointmentMetadataUpdateRequest:
        """Require at least one writable field.

        Returns:
            The validated request instance.

        Raises:
            ValueError: If no writable appointment metadata fields are provided.
        """
        if self.name is None and self.order_weight is None:
            raise ValueError("At least one appointment metadata field must be provided.")
        return self


class AppointmentOutcomeListRequest(AppointmentMetadataListRequest):
    """Search filters for the appointment outcomes collection."""


class CreateAppointmentOutcomeRequest(AppointmentMetadataWriteRequest):
    """Strict request model for creating an appointment outcome."""


class UpdateAppointmentOutcomeRequest(AppointmentMetadataUpdateRequest):
    """Strict request model for updating an appointment outcome."""


class DeleteAppointmentOutcomeRequest(QueryModel):
    """Typed query parameters for deleting an appointment outcome."""

    assign_outcome_id: int = Field(serialization_alias="assignOutcomeId")


class AppointmentOutcomeRecord(ResponseModel):
    """Appointment outcome resource returned by the API."""

    id: int
    name: str | None = None
    order_weight: int | None = Field(default=None, alias="orderWeight")


class AppointmentTypeListRequest(AppointmentMetadataListRequest):
    """Search filters for the appointment types collection."""


class CreateAppointmentTypeRequest(AppointmentMetadataWriteRequest):
    """Strict request model for creating an appointment type."""


class UpdateAppointmentTypeRequest(AppointmentMetadataUpdateRequest):
    """Strict request model for updating an appointment type."""


class DeleteAppointmentTypeRequest(QueryModel):
    """Typed query parameters for deleting an appointment type."""

    assign_type_id: int = Field(serialization_alias="assignTypeId")


class AppointmentTypeRecord(ResponseModel):
    """Appointment type resource returned by the API."""

    id: int
    name: str | None = None
    order_weight: int | None = Field(default=None, alias="orderWeight")
