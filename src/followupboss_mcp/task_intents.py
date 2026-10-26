"""Shared task-intent helpers for MCP tools and battle-test oracles."""

from __future__ import annotations

from datetime import UTC, datetime, time, timedelta


def upcoming_task_due_start() -> datetime:
    """Return the inclusive lower bound for authenticated-user upcoming tasks.

    Returns:
        Midnight UTC tomorrow, matching the MCP helper's "after today" contract.
    """
    tomorrow = datetime.now(UTC).date() + timedelta(days=1)
    return datetime.combine(tomorrow, time.min, tzinfo=UTC)


def task_projection_fields(fields: list[str] | None) -> list[str] | None:
    """Return a task ``fields`` projection that always asks for ``id``.

    Follow Up Boss ``GET /tasks`` returns only the projected fields, so a
    projection without ``id`` returns task rows that callers cannot act on.

    Args:
        fields: Optional caller-requested task projection fields.

    Returns:
        The original value when no projection is requested (``None`` or an
        empty list) or when it already includes ``id``, otherwise the list
        with ``id`` appended.
    """
    if not fields or "id" in fields:
        return fields
    return [*fields, "id"]
