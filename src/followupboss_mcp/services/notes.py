"""Notes service."""

from __future__ import annotations

from followupboss_mcp.http_client import FollowUpBossClientProtocol
from followupboss_mcp.models.notes import CreateNoteRequest, NoteRecord, UpdateNoteRequest
from followupboss_mcp.models.people import PersonLookupRequest
from followupboss_mcp.services.people import PeopleService


class NotesService:
    """Typed note operations."""

    def __init__(
        self, client: FollowUpBossClientProtocol, people_service: PeopleService | None = None
    ) -> None:
        """Initialize the service."""
        self._client = client
        self._people_service = people_service or PeopleService(client)

    async def add_note(
        self,
        request: CreateNoteRequest,
        *,
        wait_for_person: bool = False,
    ) -> NoteRecord:
        """Create a note."""
        if wait_for_person:
            await self._people_service.wait_for_person(
                request.person_id,
                request=PersonLookupRequest(fields=["id"]),
            )
        payload = request.model_dump(by_alias=True, exclude_none=True)
        response = await self._client.request_json("POST", "/notes", json_body=payload)
        return NoteRecord.model_validate(response)

    async def get_note(self, note_id: int) -> NoteRecord:
        """Fetch a note by ID."""
        payload = await self._client.request_json("GET", f"/notes/{note_id}")
        return NoteRecord.model_validate(payload)

    async def update_note(self, note_id: int, request: UpdateNoteRequest) -> NoteRecord:
        """Update a note by ID."""
        payload = request.model_dump(by_alias=True, exclude_none=True)
        response = await self._client.request_json("PUT", f"/notes/{note_id}", json_body=payload)
        return NoteRecord.model_validate(response)

    async def delete_note(self, note_id: int) -> None:
        """Delete a note by ID."""
        await self._client.request_json("DELETE", f"/notes/{note_id}")
