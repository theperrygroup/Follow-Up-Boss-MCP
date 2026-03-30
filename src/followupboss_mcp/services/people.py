"""People service."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

from followupboss_mcp.errors import FollowUpBossHTTPError, FollowUpBossNotFoundError
from followupboss_mcp.http_client import FollowUpBossClientProtocol
from followupboss_mcp.models.people import (
    ClaimPersonRequest,
    CreatePersonRequest,
    IgnoreUnclaimedPersonRequest,
    PeopleSearchRequest,
    PersonDuplicateCheckRecord,
    PersonDuplicateCheckRequest,
    PersonLookupRequest,
    PersonRecord,
    UnclaimedPeopleListRequest,
    UpdatePersonRequest,
)
from followupboss_mcp.pagination import (
    AsyncPaginator,
    PageResult,
    PaginationRequest,
    parse_pagination_metadata,
)
from followupboss_mcp.services.custom_fields import CustomFieldsService


class PeopleService:
    """Typed people operations."""

    def __init__(
        self,
        client: FollowUpBossClientProtocol,
        *,
        sleep: Callable[[float], Awaitable[None]] | None = None,
    ) -> None:
        """Initialize the service."""
        self._client = client
        self._custom_fields = CustomFieldsService(client)
        self._sleep = sleep or asyncio.sleep

    async def search_people(
        self,
        request: PeopleSearchRequest | None = None,
    ) -> PageResult[PersonRecord]:
        """Search people with documented query parameters."""
        query_request = request or PeopleSearchRequest()
        params = query_request.to_query_params()
        params.update(self._serialize_custom_field_filters(query_request.custom_field_filters))
        payload = await self._client.request_json("GET", "/people", params=params)
        if not isinstance(payload, dict):
            raise ValueError("Unexpected people response.")
        items_raw = payload.get("people", [])
        if not isinstance(items_raw, list):
            raise ValueError("Unexpected people response.")
        items = [PersonRecord.model_validate(item) for item in items_raw if isinstance(item, dict)]
        metadata = parse_pagination_metadata(payload, item_count=len(items))
        return PageResult(items=items, metadata=metadata)

    def paginator(self, request: PeopleSearchRequest | None = None) -> AsyncPaginator[PersonRecord]:
        """Return an async paginator for people search."""
        search_request = request or PeopleSearchRequest()
        pagination_request = PaginationRequest(
            limit=search_request.limit or 10,
            offset=search_request.offset or 0,
            next_token=search_request.next_token,
        )

        async def fetch_page(page_request: PaginationRequest) -> PageResult[PersonRecord]:
            return await self.search_people(
                search_request.model_copy(
                    update={
                        "limit": page_request.limit,
                        "offset": page_request.offset,
                        "next_token": page_request.next_token,
                    }
                )
            )

        return AsyncPaginator(pagination_request, fetch_page)

    async def get_person(
        self,
        person_id: int,
        request: PersonLookupRequest | None = None,
    ) -> PersonRecord:
        """Fetch a person by ID."""
        query = request.to_query_params() if request is not None else None
        payload = await self._client.request_json("GET", f"/people/{person_id}", params=query)
        return PersonRecord.model_validate(payload)

    async def check_duplicate_person(
        self,
        request: PersonDuplicateCheckRequest,
    ) -> PersonDuplicateCheckRecord:
        """Check whether a person already exists in Follow Up Boss.

        Args:
            request: The typed duplicate-check query parameters.

        Returns:
            The duplicate-check result returned by Follow Up Boss.

        Raises:
            ValueError: If the API returns an unexpected payload shape.
        """
        payload = await self._client.request_json(
            "GET",
            "/people/checkDuplicate",
            params=request.to_query_params(),
        )
        if not isinstance(payload, dict):
            raise ValueError("Unexpected people duplicate-check response.")
        return PersonDuplicateCheckRecord.model_validate(payload)

    async def list_unclaimed_people(
        self,
        request: UnclaimedPeopleListRequest | None = None,
    ) -> PageResult[PersonRecord]:
        """List unclaimed leads available to the authenticated user.

        Args:
            request: Optional unclaimed-people collection filters.

        Returns:
            A paginated unclaimed-people result set.

        Raises:
            ValueError: If the API returns an unexpected payload shape.
        """
        query = request.to_query_params() if request is not None else None
        payload = await self._client.request_json("GET", "/people/unclaimed", params=query)
        if not isinstance(payload, dict):
            raise ValueError("Unexpected unclaimed people response.")
        items_raw = payload.get("people", [])
        if not isinstance(items_raw, list):
            raise ValueError("Unexpected unclaimed people response.")
        items = [PersonRecord.model_validate(item) for item in items_raw if isinstance(item, dict)]
        metadata = parse_pagination_metadata(payload, item_count=len(items))
        return PageResult(items=items, metadata=metadata)

    async def claim_person(self, request: ClaimPersonRequest) -> PersonRecord:
        """Claim an offered lead.

        Args:
            request: The typed lead-claim request.

        Returns:
            The claimed person record, or the conflict payload returned by Follow Up Boss
            when the lead was already claimed.

        Raises:
            FollowUpBossHTTPError: If the API returns an unexpected HTTP failure.
            ValueError: If the API returns an unexpected success payload shape.
        """
        payload = request.model_dump(mode="json", by_alias=True, exclude_none=True)
        try:
            response = await self._client.request_json("POST", "/people/claim", json_body=payload)
        except FollowUpBossHTTPError as exc:
            if exc.status_code == 409 and isinstance(exc.payload, dict):
                return PersonRecord.model_validate(exc.payload)
            raise
        if not isinstance(response, dict):
            raise ValueError("Unexpected people claim response.")
        return PersonRecord.model_validate(response)

    async def ignore_unclaimed_person(self, request: IgnoreUnclaimedPersonRequest) -> None:
        """Acknowledge and ignore an offered unclaimed lead.

        Args:
            request: The typed ignore-unclaimed request.
        """
        payload = request.model_dump(mode="json", by_alias=True, exclude_none=True)
        await self._client.request_json("POST", "/people/ignoreUnclaimed", json_body=payload)

    async def create_person(self, request: CreatePersonRequest) -> PersonRecord:
        """Create a person."""
        query: dict[str, str] | None = None
        payload = request.model_dump(by_alias=True, exclude_none=True)
        deduplicate = payload.pop("deduplicate", None)
        if deduplicate is not None:
            query = {"deduplicate": "true" if deduplicate else "false"}
        payload.update(self._custom_fields.validate_custom_field_names(request.custom_fields))
        payload.pop("custom_fields", None)
        response = await self._client.request_json(
            "POST", "/people", json_body=payload, params=query
        )
        return PersonRecord.model_validate(response)

    async def update_person(self, person_id: int, request: UpdatePersonRequest) -> PersonRecord:
        """Update a person."""
        payload = request.model_dump(by_alias=True, exclude_none=True)
        merge_tags = payload.pop("mergeTags", None)
        query = {"mergeTags": str(merge_tags).lower()} if isinstance(merge_tags, bool) else None
        payload.update(self._custom_fields.validate_custom_field_names(request.custom_fields))
        payload.pop("custom_fields", None)
        response = await self._client.request_json(
            "PUT",
            f"/people/{person_id}",
            json_body=payload,
            params=query,
        )
        return PersonRecord.model_validate(response)

    async def wait_for_person(
        self,
        person_id: int,
        *,
        attempts: int = 5,
        delay_seconds: float = 1.0,
        request: PersonLookupRequest | None = None,
    ) -> PersonRecord:
        """Poll until a person is visible for follow-up mutations."""
        if attempts < 1:
            raise ValueError("attempts must be greater than zero.")
        for attempt in range(attempts):
            try:
                return await self.get_person(person_id, request=request)
            except FollowUpBossNotFoundError:
                if attempt == attempts - 1:
                    raise
                await self._sleep(delay_seconds)
        raise AssertionError("Unreachable")  # pragma: no cover

    def _serialize_custom_field_filters(
        self, custom_fields: dict[str, str] | None
    ) -> dict[str, str]:
        """Serialize custom field filters for search requests."""
        validated = self._custom_fields.validate_custom_field_names(custom_fields)
        return {key: str(value) for key, value in validated.items()}
