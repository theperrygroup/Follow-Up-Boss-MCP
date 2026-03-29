"""Appointments service."""

from __future__ import annotations

from followupboss_mcp.http_client import FollowUpBossClientProtocol
from followupboss_mcp.models.appointments import (
    AppointmentListRequest,
    AppointmentRecord,
    CreateAppointmentRequest,
    UpdateAppointmentRequest,
)
from followupboss_mcp.pagination import PageResult, parse_pagination_metadata


class AppointmentsService:
    """Typed appointment operations."""

    def __init__(self, client: FollowUpBossClientProtocol) -> None:
        """Initialize the service.

        Args:
            client: The shared Follow Up Boss HTTP client protocol.
        """
        self._client = client

    async def list_appointments(
        self,
        request: AppointmentListRequest | None = None,
    ) -> PageResult[AppointmentRecord]:
        """List appointments.

        Args:
            request: Optional appointment collection filters.

        Returns:
            A paginated appointment result set.

        Raises:
            ValueError: If the API returns an unexpected payload shape.
        """
        query = request.to_query_params() if request is not None else None
        payload = await self._client.request_json("GET", "/appointments", params=query)
        if not isinstance(payload, dict):
            raise ValueError("Unexpected appointments response.")
        items_raw = payload.get("appointments", [])
        if not isinstance(items_raw, list):
            raise ValueError("Unexpected appointments response.")
        items = [
            AppointmentRecord.model_validate(item) for item in items_raw if isinstance(item, dict)
        ]
        metadata = parse_pagination_metadata(payload, item_count=len(items))
        return PageResult(items=items, metadata=metadata)

    async def get_appointment(self, appointment_id: int) -> AppointmentRecord:
        """Fetch an appointment by ID.

        Args:
            appointment_id: The Follow Up Boss appointment identifier.

        Returns:
            The typed appointment record returned by Follow Up Boss.
        """
        payload = await self._client.request_json("GET", f"/appointments/{appointment_id}")
        return AppointmentRecord.model_validate(payload)

    async def create_appointment(self, request: CreateAppointmentRequest) -> AppointmentRecord:
        """Create an appointment.

        Args:
            request: The typed appointment creation request.

        Returns:
            The created appointment record.
        """
        payload = request.model_dump(mode="json", by_alias=True, exclude_none=True)
        send_invitation = payload.pop("sendInvitation", None)
        query = (
            {"sendInvitation": "true" if send_invitation else "false"}
            if isinstance(send_invitation, bool)
            else None
        )
        response = await self._client.request_json(
            "POST", "/appointments", json_body=payload, params=query
        )
        return AppointmentRecord.model_validate(response)

    async def update_appointment(
        self,
        appointment_id: int,
        request: UpdateAppointmentRequest,
    ) -> AppointmentRecord:
        """Update an appointment.

        Args:
            appointment_id: The Follow Up Boss appointment identifier.
            request: The typed appointment update request.

        Returns:
            The updated appointment record.
        """
        payload = request.model_dump(mode="json", by_alias=True, exclude_none=True)
        send_invitation = payload.pop("sendInvitation", None)
        query = (
            {"sendInvitation": "true" if send_invitation else "false"}
            if isinstance(send_invitation, bool)
            else None
        )
        response = await self._client.request_json(
            "PUT",
            f"/appointments/{appointment_id}",
            json_body=payload,
            params=query,
        )
        return AppointmentRecord.model_validate(response)

    async def delete_appointment(self, appointment_id: int) -> None:
        """Delete an appointment.

        Args:
            appointment_id: The Follow Up Boss appointment identifier.
        """
        await self._client.request_json("DELETE", f"/appointments/{appointment_id}")
