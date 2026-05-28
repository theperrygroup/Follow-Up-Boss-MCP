"""Datetime normalization helpers for Follow Up Boss request models.

Follow Up Boss stores appointment and task datetimes in UTC. In practice it does
not reliably honor a timezone *offset suffix* on the wire: a value such as
``2026-05-28T16:00:00-06:00`` is stored as ``2026-05-28T16:00:00Z`` (the offset
is dropped and the wall-clock is relabeled as UTC). The only representation that
is stored unambiguously is an explicit UTC instant (``...Z``).

These helpers therefore convert datetimes to UTC before serialization so the
correct instant is preserved regardless of the offset quirk:

* Timezone-aware values (any offset, including an explicit UTC) are converted to
  UTC.
* Naive values are localized to the configured default timezone (when one is
  set) and then converted to UTC. This is what fixes a spoken local time such as
  "3:30pm" that an MCP caller relays without an offset.
* Naive values with no configured default timezone are returned unchanged, which
  preserves the historical behavior where Follow Up Boss treats them as UTC.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime, tzinfo
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


def normalize_datetime(value: datetime, *, default_timezone: tzinfo | None) -> datetime:
    """Convert a datetime to the UTC instant Follow Up Boss stores reliably.

    Args:
        value: The datetime to normalize.
        default_timezone: The timezone used to interpret a naive ``value``. When
            ``None``, a naive ``value`` is returned unchanged (Follow Up Boss
            treats it as UTC).

    Returns:
        A UTC-aware datetime when the instant is known (``value`` is already
        aware, or it is naive and ``default_timezone`` is provided); otherwise
        the original naive ``value`` unchanged.
    """
    if value.tzinfo is not None:
        return value.astimezone(UTC)
    if default_timezone is None:
        return value
    return value.replace(tzinfo=default_timezone).astimezone(UTC)


def normalize_optional_datetime(value: datetime | None) -> datetime | None:
    """Normalize an optional datetime using the configured default timezone.

    This is the convenience entry point used by request-model validators for
    optional fields. ``None`` is returned unchanged.

    Args:
        value: The optional datetime to normalize.

    Returns:
        The normalized datetime, or ``None`` when ``value`` is ``None``.

    Raises:
        ValueError: If a default timezone is configured with an invalid name.
    """
    if value is None:
        return None
    return normalize_datetime(value, default_timezone=resolve_default_timezone())
