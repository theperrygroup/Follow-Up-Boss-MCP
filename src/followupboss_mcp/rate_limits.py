"""Rate-limit helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from email.utils import parsedate_to_datetime


def parse_retry_after(value: str | None, *, now: datetime | None = None) -> float | None:
    """Parse a Retry-After header as either delta-seconds or HTTP date."""
    if value is None:
        return None

    stripped = value.strip()
    if not stripped:
        return None

    if stripped.isdigit():
        return float(stripped)

    try:
        parsed = parsedate_to_datetime(stripped)
    except (TypeError, ValueError):
        return None
    reference_time = now or datetime.now(tz=UTC)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return max((parsed - reference_time).total_seconds(), 0.0)
