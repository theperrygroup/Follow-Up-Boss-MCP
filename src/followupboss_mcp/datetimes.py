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
* Naive values are localized to the resolved default timezone (when one is
  available) and then converted to UTC. This is what fixes a spoken local time
  such as "3:30pm" that an MCP caller relays without an offset.
* Naive values with no resolved default timezone are returned unchanged, which
  preserves the historical behavior where Follow Up Boss treats them as UTC.

The default timezone is resolved in two layers:

* An explicit ``FOLLOWUPBOSS_DEFAULT_TIMEZONE`` environment override (useful for
  hosted bootstrap or to force a zone).
* Otherwise the authenticated account's timezone, auto-detected from the Follow
  Up Boss ``/me`` endpoint and published into a context variable by the adapter.
  This makes appointments work with zero configuration in clients such as Claude
  where setting environment variables is awkward.
"""

from __future__ import annotations

import os
from contextvars import ContextVar
from datetime import UTC, datetime, tzinfo
from functools import lru_cache
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

DEFAULT_TIMEZONE_ENV_VARS: tuple[str, ...] = (
    "FOLLOWUPBOSS_DEFAULT_TIMEZONE",
    "FOLLOW_UP_BOSS_DEFAULT_TIMEZONE",
)
"""Environment variables consulted, in order, for the default IANA timezone."""

_ACCOUNT_TIMEZONE: ContextVar[tzinfo | None] = ContextVar(
    "followupboss_account_timezone",
    default=None,
)
"""Per-call account timezone auto-detected from Follow Up Boss ``/me``."""


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


def timezone_from_name(name: str | None) -> tzinfo | None:
    """Resolve an IANA timezone name on a best-effort basis.

    Args:
        name: A candidate IANA timezone name (for example from the Follow Up Boss
            ``/me`` payload). May be ``None`` or blank.

    Returns:
        The resolved :class:`~datetime.tzinfo`, or ``None`` when ``name`` is
        missing, blank, or not a recognized IANA zone. This never raises so that
        timezone auto-detection cannot break a request.
    """
    if name is None or not name.strip():
        return None
    try:
        return _load_zoneinfo(name.strip())
    except ValueError:
        return None


def resolve_configured_timezone() -> tzinfo | None:
    """Resolve the explicit environment-configured default timezone.

    Reads the first populated environment variable from
    :data:`DEFAULT_TIMEZONE_ENV_VARS`. The value must be an IANA timezone name.

    Returns:
        The environment-configured :class:`~datetime.tzinfo` when one is set,
        otherwise ``None``.

    Raises:
        ValueError: If the configured timezone name is not a valid IANA zone.
    """
    for env_var in DEFAULT_TIMEZONE_ENV_VARS:
        raw = os.environ.get(env_var)
        if raw is not None and raw.strip():
            return _load_zoneinfo(raw.strip())
    return None


def set_account_timezone(value: tzinfo | None) -> None:
    """Publish the auto-detected account timezone for the current call.

    Args:
        value: The account timezone resolved from Follow Up Boss ``/me``, or
            ``None`` when it could not be determined.
    """
    _ACCOUNT_TIMEZONE.set(value)


def resolve_default_timezone() -> tzinfo | None:
    """Resolve the default timezone used to interpret naive datetimes.

    Resolution precedence:

    1. The explicit ``FOLLOWUPBOSS_DEFAULT_TIMEZONE`` environment override.
    2. The account timezone auto-detected from Follow Up Boss ``/me`` for the
       current call (published via :func:`set_account_timezone`).

    Returns:
        The resolved :class:`~datetime.tzinfo`, or ``None`` when neither layer
        provides one.

    Raises:
        ValueError: If the environment override is not a valid IANA zone.
    """
    configured = resolve_configured_timezone()
    if configured is not None:
        return configured
    return _ACCOUNT_TIMEZONE.get()


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
