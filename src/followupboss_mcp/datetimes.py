"""Datetime normalization helpers for Follow Up Boss request models.

Follow Up Boss interprets datetimes sent without a UTC offset as UTC. When an
MCP caller (for example, an LLM relaying a spoken time such as "3:30pm") supplies
a local wall-clock time with no offset, the resulting appointment or task is
silently shifted to the wrong instant. These helpers localize naive datetimes to
a configured default timezone so the serialized payload carries the correct
offset, while leaving timezone-aware datetimes untouched.
"""

from __future__ import annotations

import os
from datetime import datetime, tzinfo
from functools import lru_cache
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

DEFAULT_TIMEZONE_ENV_VARS: tuple[str, ...] = (
    "FOLLOWUPBOSS_DEFAULT_TIMEZONE",
    "FOLLOW_UP_BOSS_DEFAULT_TIMEZONE",
)
"""Environment variables consulted, in order, for the default IANA timezone."""


@lru_cache(maxsize=32)
def _load_zoneinfo(name: str) -> ZoneInfo:
    """Construct and cache a :class:`ZoneInfo` for an IANA timezone name.

    Args:
        name: The IANA timezone name, for example ``"America/Denver"``.

    Returns:
        The resolved :class:`ZoneInfo` instance.

    Raises:
        ValueError: If ``name`` is not a known IANA timezone.
    """
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError) as error:
        accepted = ", ".join(DEFAULT_TIMEZONE_ENV_VARS)
        raise ValueError(
            f"Invalid IANA timezone name {name!r}. Set {accepted} to a value "
            "such as 'America/Denver' or 'America/New_York'."
        ) from error


def resolve_default_timezone() -> tzinfo | None:
    """Resolve the configured default timezone for naive datetimes.

    Reads the first populated environment variable from
    :data:`DEFAULT_TIMEZONE_ENV_VARS`. The value must be an IANA timezone name.

    Returns:
        The configured :class:`~datetime.tzinfo` when one is set, otherwise
        ``None``.

    Raises:
        ValueError: If the configured timezone name is not a valid IANA zone.
    """
    for env_var in DEFAULT_TIMEZONE_ENV_VARS:
        raw = os.environ.get(env_var)
        if raw is not None and raw.strip():
            return _load_zoneinfo(raw.strip())
    return None


def ensure_timezone_aware(value: datetime, *, default_timezone: tzinfo | None) -> datetime:
    """Attach a default timezone to a naive datetime.

    Args:
        value: The datetime to normalize.
        default_timezone: The timezone applied to naive datetimes. When ``None``,
            naive datetimes are returned unchanged (Follow Up Boss treats them as
            UTC).

    Returns:
        A timezone-aware datetime when ``value`` is naive and a default timezone
        applies, otherwise the original ``value`` unchanged.
    """
    if value.tzinfo is not None:
        return value
    if default_timezone is None:
        return value
    return value.replace(tzinfo=default_timezone)


def normalize_local_datetime(value: datetime | None) -> datetime | None:
    """Localize a naive datetime using the configured default timezone.

    This is the convenience entry point used by request-model validators. Aware
    datetimes and ``None`` are returned unchanged.

    Args:
        value: The optional datetime to normalize.

    Returns:
        The normalized datetime, or ``None`` when ``value`` is ``None``.

    Raises:
        ValueError: If a default timezone is configured with an invalid name.
    """
    if value is None:
        return None
    return ensure_timezone_aware(value, default_timezone=resolve_default_timezone())
