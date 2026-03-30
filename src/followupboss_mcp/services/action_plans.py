"""Action plan services."""

from __future__ import annotations

from followupboss_mcp.http_client import FollowUpBossClientProtocol
from followupboss_mcp.models.action_plans import (
    ActionPlanListRequest,
    ActionPlanPersonListRequest,
    ActionPlanPersonRecord,
    ActionPlanRecord,
    CreateActionPlanPersonRequest,
    UpdateActionPlanPersonRequest,
)
from followupboss_mcp.pagination import PageResult, parse_pagination_metadata


class ActionPlansService:
    """Typed action plan operations."""

    def __init__(self, client: FollowUpBossClientProtocol) -> None:
        """Initialize the service.

        Args:
            client: The shared Follow Up Boss HTTP client protocol.
        """
        self._client = client

    async def list_action_plans(
        self,
        request: ActionPlanListRequest | None = None,
    ) -> PageResult[ActionPlanRecord]:
        """List action plans.

        Args:
            request: Optional action plan collection filters.

        Returns:
            A paginated action plan result set.

        Raises:
            ValueError: If the API returns an unexpected payload shape.
        """
        query = request.to_query_params() if request is not None else None
        payload = await self._client.request_json("GET", "/actionPlans", params=query)
        if not isinstance(payload, dict):
            raise ValueError("Unexpected action plans response.")
        items_raw = payload.get("actionPlans", [])
        if not isinstance(items_raw, list):
            raise ValueError("Unexpected action plans response.")
        items = [
            ActionPlanRecord.model_validate(item) for item in items_raw if isinstance(item, dict)
        ]
        metadata = parse_pagination_metadata(payload, item_count=len(items))
        return PageResult(items=items, metadata=metadata)

    async def list_action_plan_people(
        self,
        request: ActionPlanPersonListRequest | None = None,
    ) -> PageResult[ActionPlanPersonRecord]:
        """List action-plan-person relationships.

        Args:
            request: Optional action-plan-person collection filters.

        Returns:
            A paginated action-plan-person result set.

        Raises:
            ValueError: If the API returns an unexpected payload shape.
        """
        query = request.to_query_params() if request is not None else None
        payload = await self._client.request_json("GET", "/actionPlansPeople", params=query)
        if not isinstance(payload, dict):
            raise ValueError("Unexpected actionPlansPeople response.")
        items_raw = payload.get("actionPlansPeople", [])
        if not isinstance(items_raw, list):
            raise ValueError("Unexpected actionPlansPeople response.")
        items = [
            ActionPlanPersonRecord.model_validate(item)
            for item in items_raw
            if isinstance(item, dict)
        ]
        metadata = parse_pagination_metadata(payload, item_count=len(items))
        return PageResult(items=items, metadata=metadata)

    async def apply_action_plan(
        self,
        request: CreateActionPlanPersonRequest,
    ) -> ActionPlanPersonRecord:
        """Apply an action plan to a person.

        Args:
            request: The typed apply request.

        Returns:
            The created or acknowledged action-plan-person relationship.

        Raises:
            ValueError: If the API returns an unexpected payload shape.
        """
        payload = request.model_dump(mode="json", by_alias=True, exclude_none=True)
        response = await self._client.request_json("POST", "/actionPlansPeople", json_body=payload)
        if not isinstance(response, dict):
            raise ValueError("Unexpected actionPlansPeople response.")
        return ActionPlanPersonRecord.model_validate(response)

    async def update_action_plan_person(
        self,
        action_plan_person_id: int,
        request: UpdateActionPlanPersonRequest,
    ) -> ActionPlanPersonRecord:
        """Update an action-plan-person relationship.

        Args:
            action_plan_person_id: The Follow Up Boss action-plan-person identifier.
            request: The typed relationship update request.

        Returns:
            The updated action-plan-person relationship.

        Raises:
            ValueError: If the API returns an unexpected payload shape.
        """
        payload = request.model_dump(mode="json", by_alias=True, exclude_none=True)
        response = await self._client.request_json(
            "PUT",
            f"/actionPlansPeople/{action_plan_person_id}",
            json_body=payload,
        )
        if not isinstance(response, dict):
            raise ValueError("Unexpected actionPlansPeople response.")
        return ActionPlanPersonRecord.model_validate(response)
