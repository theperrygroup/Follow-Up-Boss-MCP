"""Automation and automation-person services."""

from __future__ import annotations

from followupboss_mcp.http_client import FollowUpBossClientProtocol
from followupboss_mcp.models.automations import (
    AutomationListRequest,
    AutomationPeopleListRequest,
    AutomationPersonRecord,
    AutomationRecord,
    CreateAutomationPersonRequest,
    UpdateAutomationPersonRequest,
)
from followupboss_mcp.pagination import PageResult, parse_pagination_metadata


class AutomationsService:
    """Typed automation operations."""

    def __init__(self, client: FollowUpBossClientProtocol) -> None:
        """Initialize the service.

        Args:
            client: The shared Follow Up Boss HTTP client protocol.
        """
        self._client = client

    async def list_automations(
        self,
        request: AutomationListRequest | None = None,
    ) -> PageResult[AutomationRecord]:
        """List automations.

        Args:
            request: Optional automation collection filters.

        Returns:
            A paginated automation result set.

        Raises:
            ValueError: If the API returns an unexpected payload shape.
        """
        query = request.to_query_params() if request is not None else None
        payload = await self._client.request_json("GET", "/automations", params=query)
        if not isinstance(payload, dict):
            raise ValueError("Unexpected automations response.")
        items_raw = payload.get("automations", [])
        if not isinstance(items_raw, list):
            raise ValueError("Unexpected automations response.")
        items = [
            AutomationRecord.model_validate(item) for item in items_raw if isinstance(item, dict)
        ]
        metadata = parse_pagination_metadata(payload, item_count=len(items))
        return PageResult(items=items, metadata=metadata)

    async def get_automation(self, automation_id: int) -> AutomationRecord:
        """Fetch an automation by ID.

        Args:
            automation_id: The Follow Up Boss automation identifier.

        Returns:
            The typed automation record returned by Follow Up Boss.
        """
        payload = await self._client.request_json("GET", f"/automations/{automation_id}")
        return AutomationRecord.model_validate(payload)


class AutomationPeopleService:
    """Typed automation-person pairing operations."""

    def __init__(self, client: FollowUpBossClientProtocol) -> None:
        """Initialize the service.

        Args:
            client: The shared Follow Up Boss HTTP client protocol.
        """
        self._client = client

    async def list_automation_people(
        self,
        request: AutomationPeopleListRequest | None = None,
    ) -> PageResult[AutomationPersonRecord]:
        """List automation-person pairings.

        Args:
            request: Optional automation-person collection filters.

        Returns:
            A paginated automation-person result set.

        Raises:
            ValueError: If the API returns an unexpected payload shape.
        """
        query = request.to_query_params() if request is not None else None
        payload = await self._client.request_json("GET", "/automationsPeople", params=query)
        if not isinstance(payload, dict):
            raise ValueError("Unexpected automationsPeople response.")
        items_raw = payload.get("automationsPeople", [])
        if not isinstance(items_raw, list):
            raise ValueError("Unexpected automationsPeople response.")
        items = [
            AutomationPersonRecord.model_validate(item)
            for item in items_raw
            if isinstance(item, dict)
        ]
        metadata = parse_pagination_metadata(payload, item_count=len(items))
        return PageResult(items=items, metadata=metadata)

    async def get_automation_person(self, automation_person_id: int) -> AutomationPersonRecord:
        """Fetch an automation-person pairing by ID.

        Args:
            automation_person_id: The Follow Up Boss automation-person pairing identifier.

        Returns:
            The typed automation-person record returned by Follow Up Boss.
        """
        payload = await self._client.request_json(
            "GET", f"/automationsPeople/{automation_person_id}"
        )
        return AutomationPersonRecord.model_validate(payload)

    async def create_automation_person(
        self,
        request: CreateAutomationPersonRequest,
    ) -> AutomationPersonRecord:
        """Trigger an automation for a person.

        Args:
            request: The typed automation trigger request.

        Returns:
            The created automation-person pairing record.
        """
        payload = request.model_dump(mode="json", by_alias=True, exclude_none=True)
        response = await self._client.request_json("POST", "/automationsPeople", json_body=payload)
        return AutomationPersonRecord.model_validate(response)

    async def update_automation_person(
        self,
        automation_person_id: int,
        request: UpdateAutomationPersonRequest,
    ) -> AutomationPersonRecord:
        """Pause or resume an automation-person pairing.

        Args:
            automation_person_id: The Follow Up Boss automation-person pairing identifier.
            request: The typed pairing update request.

        Returns:
            The updated automation-person pairing record.
        """
        payload = request.model_dump(mode="json", by_alias=True, exclude_none=True)
        response = await self._client.request_json(
            "PUT",
            f"/automationsPeople/{automation_person_id}",
            json_body=payload,
        )
        return AutomationPersonRecord.model_validate(response)
