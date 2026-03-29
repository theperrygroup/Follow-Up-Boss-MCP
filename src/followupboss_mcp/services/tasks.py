"""Tasks service."""

from __future__ import annotations

from followupboss_mcp.http_client import FollowUpBossClientProtocol
from followupboss_mcp.models.tasks import (
    CreateTaskRequest,
    TaskListRequest,
    TaskRecord,
    UpdateTaskRequest,
)
from followupboss_mcp.pagination import PageResult, parse_pagination_metadata


class TasksService:
    """Typed task operations."""

    def __init__(self, client: FollowUpBossClientProtocol) -> None:
        """Initialize the service.

        Args:
            client: The shared Follow Up Boss HTTP client protocol.
        """
        self._client = client

    async def list_tasks(self, request: TaskListRequest | None = None) -> PageResult[TaskRecord]:
        """List tasks.

        Args:
            request: Optional task collection filters.

        Returns:
            A paginated task result set.

        Raises:
            ValueError: If the API returns an unexpected payload shape.
        """
        query = request.to_query_params() if request is not None else None
        payload = await self._client.request_json("GET", "/tasks", params=query)
        if not isinstance(payload, dict):
            raise ValueError("Unexpected tasks response.")
        items_raw = payload.get("tasks", [])
        if not isinstance(items_raw, list):
            raise ValueError("Unexpected tasks response.")
        items = [TaskRecord.model_validate(item) for item in items_raw if isinstance(item, dict)]
        metadata = parse_pagination_metadata(payload, item_count=len(items))
        return PageResult(items=items, metadata=metadata)

    async def get_task(self, task_id: int) -> TaskRecord:
        """Fetch a task by ID.

        Args:
            task_id: The Follow Up Boss task identifier.

        Returns:
            The typed task record returned by Follow Up Boss.
        """
        payload = await self._client.request_json("GET", f"/tasks/{task_id}")
        return TaskRecord.model_validate(payload)

    async def create_task(self, request: CreateTaskRequest) -> TaskRecord:
        """Create a task.

        Args:
            request: The typed task creation request.

        Returns:
            The created task record.
        """
        payload = request.model_dump(mode="json", by_alias=True, exclude_none=True)
        response = await self._client.request_json("POST", "/tasks", json_body=payload)
        return TaskRecord.model_validate(response)

    async def update_task(self, task_id: int, request: UpdateTaskRequest) -> TaskRecord:
        """Update a task.

        Args:
            task_id: The Follow Up Boss task identifier.
            request: The typed task update request.

        Returns:
            The updated task record.
        """
        payload = request.model_dump(mode="json", by_alias=True, exclude_none=True)
        response = await self._client.request_json("PUT", f"/tasks/{task_id}", json_body=payload)
        return TaskRecord.model_validate(response)

    async def delete_task(self, task_id: int) -> None:
        """Delete a task.

        Args:
            task_id: The Follow Up Boss task identifier.
        """
        await self._client.request_json("DELETE", f"/tasks/{task_id}")
