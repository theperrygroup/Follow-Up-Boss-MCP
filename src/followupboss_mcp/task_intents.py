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
