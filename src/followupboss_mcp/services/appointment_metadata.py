"""Appointment outcome and appointment type services."""

from __future__ import annotations

from followupboss_mcp.http_client import FollowUpBossClientProtocol
from followupboss_mcp.models.appointment_metadata import (
    AppointmentOutcomeListRequest,
    AppointmentOutcomeRecord,
    AppointmentTypeListRequest,
    AppointmentTypeRecord,
    CreateAppointmentOutcomeRequest,
    CreateAppointmentTypeRequest,
    DeleteAppointmentOutcomeRequest,
    DeleteAppointmentTypeRequest,
    UpdateAppointmentOutcomeRequest,
    UpdateAppointmentTypeRequest,
)
from followupboss_mcp.pagination import PageResult, parse_pagination_metadata


class AppointmentOutcomesService:
    """Typed appointment outcome operations."""

    def __init__(self, client: FollowUpBossClientProtocol) -> None:
        """Initialize the service.

        Args:
            client: The shared Follow Up Boss HTTP client protocol.
        """
        self._client = client

    async def list_appointment_outcomes(
        self,
        request: AppointmentOutcomeListRequest | None = None,
    ) -> PageResult[AppointmentOutcomeRecord]:
        """List appointment outcomes.

        Args:
            request: Optional appointment outcome collection filters.

        Returns:
            A paginated appointment outcome result set.

        Raises:
            ValueError: If the API returns an unexpected payload shape.
        """
        query = request.to_query_params() if request is not None else None
        payload = await self._client.request_json("GET", "/appointmentOutcomes", params=query)
        if not isinstance(payload, dict):
            raise ValueError("Unexpected appointment outcomes response.")
        items_raw = payload.get("appointmentoutcomes", [])
        if not isinstance(items_raw, list):
            raise ValueError("Unexpected appointment outcomes response.")
        items = [
            AppointmentOutcomeRecord.model_validate(item)
            for item in items_raw
            if isinstance(item, dict)
        ]
        metadata = parse_pagination_metadata(payload, item_count=len(items))
        return PageResult(items=items, metadata=metadata)

    async def get_appointment_outcome(self, outcome_id: int) -> AppointmentOutcomeRecord:
        """Fetch an appointment outcome by ID.

        Args:
            outcome_id: The Follow Up Boss appointment outcome identifier.

        Returns:
            The typed appointment outcome record returned by Follow Up Boss.
        """
        payload = await self._client.request_json("GET", f"/appointmentOutcomes/{outcome_id}")
        return AppointmentOutcomeRecord.model_validate(payload)

    async def create_appointment_outcome(
        self,
        request: CreateAppointmentOutcomeRequest,
    ) -> AppointmentOutcomeRecord:
        """Create an appointment outcome.

        Args:
            request: The typed appointment outcome creation request.

        Returns:
            The created appointment outcome record.
        """
        payload = request.model_dump(mode="json", by_alias=True, exclude_none=True)
        response = await self._client.request_json(
            "POST",
            "/appointmentOutcomes",
            json_body=payload,
        )
        return AppointmentOutcomeRecord.model_validate(response)

    async def update_appointment_outcome(
        self,
        outcome_id: int,
        request: UpdateAppointmentOutcomeRequest,
    ) -> AppointmentOutcomeRecord:
        """Update an appointment outcome.

        Args:
            outcome_id: The Follow Up Boss appointment outcome identifier.
            request: The typed appointment outcome update request.

        Returns:
            The updated appointment outcome record.
        """
        payload = request.model_dump(mode="json", by_alias=True, exclude_none=True)
        response = await self._client.request_json(
            "PUT",
            f"/appointmentOutcomes/{outcome_id}",
            json_body=payload,
        )
        return AppointmentOutcomeRecord.model_validate(response)

    async def delete_appointment_outcome(
        self,
        outcome_id: int,
        request: DeleteAppointmentOutcomeRequest,
    ) -> None:
        """Delete an appointment outcome.

        Args:
            outcome_id: The Follow Up Boss appointment outcome identifier.
            request: The typed appointment outcome deletion query parameters.
        """
        await self._client.request_json(
            "DELETE",
            f"/appointmentOutcomes/{outcome_id}",
            params=request.to_query_params(),
        )


class AppointmentTypesService:
    """Typed appointment type operations."""

    def __init__(self, client: FollowUpBossClientProtocol) -> None:
        """Initialize the service.

        Args:
            client: The shared Follow Up Boss HTTP client protocol.
        """
        self._client = client

    async def list_appointment_types(
        self,
        request: AppointmentTypeListRequest | None = None,
    ) -> PageResult[AppointmentTypeRecord]:
        """List appointment types.

        Args:
            request: Optional appointment type collection filters.

        Returns:
            A paginated appointment type result set.

        Raises:
            ValueError: If the API returns an unexpected payload shape.
        """
        query = request.to_query_params() if request is not None else None
        payload = await self._client.request_json("GET", "/appointmentTypes", params=query)
        if not isinstance(payload, dict):
            raise ValueError("Unexpected appointment types response.")
        items_raw = payload.get("appointmenttypes", [])
        if not isinstance(items_raw, list):
            raise ValueError("Unexpected appointment types response.")
        items = [
            AppointmentTypeRecord.model_validate(item)
            for item in items_raw
            if isinstance(item, dict)
        ]
        metadata = parse_pagination_metadata(payload, item_count=len(items))
        return PageResult(items=items, metadata=metadata)

    async def get_appointment_type(self, type_id: int) -> AppointmentTypeRecord:
        """Fetch an appointment type by ID.

        Args:
            type_id: The Follow Up Boss appointment type identifier.

        Returns:
            The typed appointment type record returned by Follow Up Boss.
        """
        payload = await self._client.request_json("GET", f"/appointmentTypes/{type_id}")
        return AppointmentTypeRecord.model_validate(payload)

    async def create_appointment_type(
        self,
        request: CreateAppointmentTypeRequest,
    ) -> AppointmentTypeRecord:
        """Create an appointment type.

        Args:
            request: The typed appointment type creation request.

        Returns:
            The created appointment type record.
        """
        payload = request.model_dump(mode="json", by_alias=True, exclude_none=True)
        response = await self._client.request_json(
            "POST",
            "/appointmentTypes",
            json_body=payload,
        )
        return AppointmentTypeRecord.model_validate(response)

    async def update_appointment_type(
        self,
        type_id: int,
        request: UpdateAppointmentTypeRequest,
    ) -> AppointmentTypeRecord:
        """Update an appointment type.

        Args:
            type_id: The Follow Up Boss appointment type identifier.
            request: The typed appointment type update request.

        Returns:
            The updated appointment type record.
        """
        payload = request.model_dump(mode="json", by_alias=True, exclude_none=True)
        response = await self._client.request_json(
            "PUT",
            f"/appointmentTypes/{type_id}",
            json_body=payload,
        )
        return AppointmentTypeRecord.model_validate(response)

    async def delete_appointment_type(
        self,
        type_id: int,
        request: DeleteAppointmentTypeRequest,
    ) -> None:
        """Delete an appointment type.

        Args:
            type_id: The Follow Up Boss appointment type identifier.
            request: The typed appointment type deletion query parameters.
        """
        await self._client.request_json(
            "DELETE",
            f"/appointmentTypes/{type_id}",
            params=request.to_query_params(),
        )
