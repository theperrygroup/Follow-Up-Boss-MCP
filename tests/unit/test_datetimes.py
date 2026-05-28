"""Tests for timezone normalization of appointment and task datetimes."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import cast
from zoneinfo import ZoneInfo

import pytest

from followupboss_mcp.datetimes import (
    normalize_datetime,
    normalize_optional_datetime,
    resolve_configured_timezone,
    resolve_default_timezone,
    set_account_timezone,
    timezone_from_name,
)
from followupboss_mcp.errors import FollowUpBossError
from followupboss_mcp.mcp_tools import FollowUpBossToolAdapter
from followupboss_mcp.models.appointments import (
    AppointmentListRequest,
    CreateAppointmentRequest,
    UpdateAppointmentRequest,
)
from followupboss_mcp.models.tasks import (
    CreateTaskRequest,
    TaskListRequest,
    UpdateTaskRequest,
)
from followupboss_mcp.models.users import CurrentUserRecord
from followupboss_mcp.tenant_runtime import ServiceBundle


class _StubUsersService:
    """Minimal users service stub exposing ``get_me`` for timezone detection."""

    def __init__(
        self,
        *,
        time_zone: str | None = None,
        error: Exception | None = None,
    ) -> None:
        """Store the canned ``/me`` timezone or the error to raise.

        Args:
            time_zone: The ``timeZone`` value returned by ``get_me``.
            error: An exception to raise from ``get_me`` instead of returning.
        """
        self._time_zone = time_zone
        self._error = error
        self.calls = 0

    async def get_me(self) -> CurrentUserRecord:
        """Return a canned current user or raise the configured error.

        Returns:
            A current-user record carrying the configured timezone.

        Raises:
            Exception: The configured error, when one was provided.
        """
        self.calls += 1
        if self._error is not None:
            raise self._error
        return CurrentUserRecord.model_validate({"id": 1, "timeZone": self._time_zone})


class _StubBundle:
    """Minimal service bundle exposing only the users service."""

    def __init__(self, users: _StubUsersService) -> None:
        """Store the stub users service.

        Args:
            users: The stub users service used for ``/me`` detection.
        """
        self.users = users


def _adapter_with_users(users: _StubUsersService) -> FollowUpBossToolAdapter:
    """Build an adapter backed by a stub bundle for timezone priming tests.

    Args:
        users: The stub users service exposed by the bundle.

    Returns:
        An adapter whose fixed bundle resolves the stub users service.
    """
    return FollowUpBossToolAdapter(cast(ServiceBundle, _StubBundle(users)))


def test_timezone_from_name_resolves_valid_zone() -> None:
    """A valid IANA name should resolve to the matching zone."""
    assert timezone_from_name("America/Denver") == ZoneInfo("America/Denver")


@pytest.mark.parametrize("name", [None, "", "   "])
def test_timezone_from_name_returns_none_for_missing(name: str | None) -> None:
    """Missing or blank names should resolve to ``None``.

    Args:
        name: The missing or blank candidate timezone name.
    """
    assert timezone_from_name(name) is None


def test_timezone_from_name_returns_none_for_invalid() -> None:
    """An unknown IANA name should resolve to ``None`` rather than raising."""
    assert timezone_from_name("America/Nowhere") is None


def test_resolve_configured_timezone_reads_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The configured resolver should read the environment override.

    Args:
        monkeypatch: Fixture used to set the configured timezone env var.
    """
    monkeypatch.setenv("FOLLOWUPBOSS_DEFAULT_TIMEZONE", "America/Denver")
    assert resolve_configured_timezone() == ZoneInfo("America/Denver")


def test_resolve_default_timezone_uses_account_when_no_env() -> None:
    """Without an env override, the auto-detected account timezone should win."""
    set_account_timezone(ZoneInfo("America/Denver"))
    assert resolve_default_timezone() == ZoneInfo("America/Denver")


def test_resolve_default_timezone_env_overrides_account(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An explicit env override should take precedence over the account timezone.

    Args:
        monkeypatch: Fixture used to set the configured timezone env var.
    """
    set_account_timezone(ZoneInfo("America/Denver"))
    monkeypatch.setenv("FOLLOWUPBOSS_DEFAULT_TIMEZONE", "America/New_York")
    assert resolve_default_timezone() == ZoneInfo("America/New_York")


@pytest.mark.asyncio
async def test_prime_account_timezone_detects_from_me() -> None:
    """Priming should publish the account timezone detected from ``/me``."""
    users = _StubUsersService(time_zone="America/Denver")
    adapter = _adapter_with_users(users)
    await adapter.prime_account_timezone()
    assert resolve_default_timezone() == ZoneInfo("America/Denver")
    assert users.calls == 1


@pytest.mark.asyncio
async def test_prime_account_timezone_caches_me_lookup() -> None:
    """Repeated priming for one bundle should reuse the cached ``/me`` lookup."""
    users = _StubUsersService(time_zone="America/Denver")
    adapter = _adapter_with_users(users)
    await adapter.prime_account_timezone()
    await adapter.prime_account_timezone()
    assert users.calls == 1


@pytest.mark.asyncio
async def test_prime_account_timezone_env_override_skips_lookup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An env override should short-circuit priming without calling ``/me``.

    Args:
        monkeypatch: Fixture used to set the configured timezone env var.
    """
    monkeypatch.setenv("FOLLOWUPBOSS_DEFAULT_TIMEZONE", "America/New_York")
    users = _StubUsersService(time_zone="America/Denver")
    adapter = _adapter_with_users(users)
    await adapter.prime_account_timezone()
    assert users.calls == 0
    assert resolve_default_timezone() == ZoneInfo("America/New_York")


@pytest.mark.asyncio
async def test_prime_account_timezone_handles_missing_zone() -> None:
    """A ``/me`` payload without a timezone should leave the default unset."""
    users = _StubUsersService(time_zone=None)
    adapter = _adapter_with_users(users)
    await adapter.prime_account_timezone()
    assert resolve_default_timezone() is None


@pytest.mark.asyncio
async def test_prime_account_timezone_handles_lookup_error() -> None:
    """A failed ``/me`` lookup should be swallowed and leave the default unset."""
    users = _StubUsersService(error=FollowUpBossError("boom"))
    adapter = _adapter_with_users(users)
    await adapter.prime_account_timezone()
    assert resolve_default_timezone() is None


@pytest.mark.asyncio
async def test_create_appointment_uses_auto_detected_timezone() -> None:
    """An auto-detected account timezone should convert naive appointment times."""
    users = _StubUsersService(time_zone="America/Denver")
    adapter = _adapter_with_users(users)
    await adapter.prime_account_timezone()
    request = CreateAppointmentRequest.model_validate(
        {
            "title": "Follow up",
            "start": "2026-05-28T16:00:00",
            "end": "2026-05-28T16:30:00",
        }
    )
    payload = request.model_dump(mode="json", by_alias=True, exclude_none=True)
    assert payload["start"] == "2026-05-28T22:00:00Z"
    assert payload["end"] == "2026-05-28T22:30:00Z"


def test_resolve_default_timezone_returns_none_when_unset() -> None:
    """No configured timezone should resolve to ``None``."""
    assert resolve_default_timezone() is None


@pytest.mark.parametrize(
    "env_var",
    ["FOLLOWUPBOSS_DEFAULT_TIMEZONE", "FOLLOW_UP_BOSS_DEFAULT_TIMEZONE"],
)
def test_resolve_default_timezone_reads_supported_env_vars(
    monkeypatch: pytest.MonkeyPatch,
    env_var: str,
) -> None:
    """Both canonical and legacy env var names should resolve a timezone.

    Args:
        monkeypatch: Fixture used to set the configured timezone env var.
        env_var: The environment variable name under test.
    """
    monkeypatch.setenv(env_var, "America/Denver")
    resolved = resolve_default_timezone()
    assert resolved == ZoneInfo("America/Denver")


def test_resolve_default_timezone_ignores_blank_value(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A whitespace-only timezone value should be treated as unset.

    Args:
        monkeypatch: Fixture used to set the configured timezone env var.
    """
    monkeypatch.setenv("FOLLOWUPBOSS_DEFAULT_TIMEZONE", "   ")
    assert resolve_default_timezone() is None


def test_resolve_default_timezone_rejects_invalid_zone(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An unknown IANA name should raise an actionable error.

    Args:
        monkeypatch: Fixture used to set the configured timezone env var.
    """
    monkeypatch.setenv("FOLLOWUPBOSS_DEFAULT_TIMEZONE", "America/Nowhere")
    with pytest.raises(ValueError, match="Invalid IANA timezone name"):
        resolve_default_timezone()


def test_normalize_datetime_converts_naive_local_to_utc() -> None:
    """A naive datetime should be interpreted in the default zone and sent as UTC."""
    naive = datetime(2026, 5, 28, 15, 30)
    result = normalize_datetime(naive, default_timezone=ZoneInfo("America/Denver"))
    assert result.utcoffset() == timedelta(0)
    assert result.isoformat() == "2026-05-28T21:30:00+00:00"


def test_normalize_datetime_converts_aware_value_to_utc() -> None:
    """An aware datetime should be converted from its own offset to UTC."""
    aware = datetime(2026, 5, 28, 15, 30, tzinfo=ZoneInfo("America/New_York"))
    result = normalize_datetime(aware, default_timezone=ZoneInfo("America/Denver"))
    assert result.utcoffset() == timedelta(0)
    assert result.isoformat() == "2026-05-28T19:30:00+00:00"


def test_normalize_datetime_without_default_keeps_naive() -> None:
    """Without a default timezone, a naive datetime should remain naive."""
    naive = datetime(2026, 5, 28, 15, 30)
    result = normalize_datetime(naive, default_timezone=None)
    assert result is naive
    assert result.tzinfo is None


def test_normalize_optional_datetime_passthrough_for_none() -> None:
    """``None`` input should return ``None``."""
    assert normalize_optional_datetime(None) is None


def test_normalize_optional_datetime_uses_configured_timezone(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The convenience helper should convert naive values to UTC via the env config.

    Args:
        monkeypatch: Fixture used to set the configured timezone env var.
    """
    monkeypatch.setenv("FOLLOWUPBOSS_DEFAULT_TIMEZONE", "America/New_York")
    result = normalize_optional_datetime(datetime(2026, 5, 28, 15, 30))
    assert result is not None
    assert result.isoformat() == "2026-05-28T19:30:00+00:00"


def test_create_appointment_converts_naive_local_to_utc(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Naive appointment times should serialize as the converted UTC instant.

    Args:
        monkeypatch: Fixture used to set the configured timezone env var.
    """
    monkeypatch.setenv("FOLLOWUPBOSS_DEFAULT_TIMEZONE", "America/Denver")
    request = CreateAppointmentRequest.model_validate(
        {
            "title": "Listing consult",
            "start": "2026-05-28T15:30:00",
            "end": "2026-05-28T16:00:00",
        }
    )
    payload = request.model_dump(mode="json", by_alias=True, exclude_none=True)
    assert payload["start"] == "2026-05-28T21:30:00Z"
    assert payload["end"] == "2026-05-28T22:00:00Z"


def test_create_appointment_converts_explicit_offset_to_utc(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An explicit offset should be converted to UTC (not sent as a suffix).

    Args:
        monkeypatch: Fixture used to set the configured timezone env var.
    """
    monkeypatch.setenv("FOLLOWUPBOSS_DEFAULT_TIMEZONE", "America/Denver")
    request = CreateAppointmentRequest.model_validate(
        {
            "title": "Listing consult",
            "start": "2026-05-28T15:30:00-05:00",
            "end": "2026-05-28T16:00:00-05:00",
        }
    )
    payload = request.model_dump(mode="json", by_alias=True, exclude_none=True)
    assert payload["start"] == "2026-05-28T20:30:00Z"
    assert payload["end"] == "2026-05-28T21:00:00Z"


def test_create_appointment_without_default_keeps_naive() -> None:
    """Without a configured timezone, naive times serialize without an offset."""
    request = CreateAppointmentRequest.model_validate(
        {
            "title": "Listing consult",
            "start": "2026-05-28T15:30:00",
            "end": "2026-05-28T16:00:00",
        }
    )
    payload = request.model_dump(mode="json", by_alias=True, exclude_none=True)
    assert payload["start"] == "2026-05-28T15:30:00"
    assert payload["end"] == "2026-05-28T16:00:00"


def test_update_appointment_converts_naive_local_to_utc(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Update requests should convert naive times to UTC like create requests.

    Args:
        monkeypatch: Fixture used to set the configured timezone env var.
    """
    monkeypatch.setenv("FOLLOWUPBOSS_DEFAULT_TIMEZONE", "America/Denver")
    request = UpdateAppointmentRequest.model_validate(
        {
            "title": "Listing consult",
            "start": "2026-05-28T15:30:00",
            "end": "2026-05-28T16:00:00",
        }
    )
    payload = request.model_dump(mode="json", by_alias=True, exclude_none=True)
    assert payload["start"] == "2026-05-28T21:30:00Z"
    assert payload["end"] == "2026-05-28T22:00:00Z"


def test_appointment_list_request_converts_naive_filters_to_utc(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Naive appointment list filters should serialize as the UTC instant.

    Args:
        monkeypatch: Fixture used to set the configured timezone env var.
    """
    monkeypatch.setenv("FOLLOWUPBOSS_DEFAULT_TIMEZONE", "America/Denver")
    request = AppointmentListRequest.model_validate(
        {"start": "2026-05-28T08:00:00", "end": "2026-05-28T17:00:00"}
    )
    params = request.to_query_params()
    assert params["start"] == "2026-05-28T14:00:00+00:00"
    assert params["end"] == "2026-05-28T23:00:00+00:00"


def test_create_task_converts_naive_due_date_time_to_utc(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A naive task due time should serialize as the converted UTC instant.

    Args:
        monkeypatch: Fixture used to set the configured timezone env var.
    """
    monkeypatch.setenv("FOLLOWUPBOSS_DEFAULT_TIMEZONE", "America/Denver")
    request = CreateTaskRequest.model_validate(
        {
            "person_id": 99,
            "assigned_to": "Agent",
            "name": "Call lead",
            "due_date_time": "2026-05-28T15:30:00",
        }
    )
    payload = request.model_dump(mode="json", by_alias=True, exclude_none=True)
    assert payload["dueDateTime"] == "2026-05-28T21:30:00Z"


def test_update_task_converts_explicit_offset_to_utc(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An explicit task due offset should be converted to UTC.

    Args:
        monkeypatch: Fixture used to set the configured timezone env var.
    """
    monkeypatch.setenv("FOLLOWUPBOSS_DEFAULT_TIMEZONE", "America/Denver")
    request = UpdateTaskRequest.model_validate(
        {"person_id": 99, "due_date_time": "2026-05-28T15:30:00+02:00"}
    )
    payload = request.model_dump(mode="json", by_alias=True, exclude_none=True)
    assert payload["dueDateTime"] == "2026-05-28T13:30:00Z"


def test_task_list_request_converts_naive_due_range_to_utc(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Naive task due-range filters should serialize as the UTC instant.

    Args:
        monkeypatch: Fixture used to set the configured timezone env var.
    """
    monkeypatch.setenv("FOLLOWUPBOSS_DEFAULT_TIMEZONE", "America/Denver")
    request = TaskListRequest.model_validate(
        {"due_start": "2026-05-28T08:00:00", "due_end": "2026-05-28T17:00:00"}
    )
    params = request.to_query_params()
    assert params["dueStart"] == "2026-05-28T14:00:00+00:00"
    assert params["dueEnd"] == "2026-05-28T23:00:00+00:00"


def test_existing_aware_utc_datetime_unaffected() -> None:
    """A UTC-aware datetime should still serialize to the documented ``Z`` form."""
    request = CreateAppointmentRequest.model_validate(
        {
            "title": "Listing consult",
            "start": datetime(2026, 5, 28, 21, 30, tzinfo=UTC),
            "end": datetime(2026, 5, 28, 22, 0, tzinfo=UTC),
        }
    )
    payload = request.model_dump(mode="json", by_alias=True, exclude_none=True)
    assert payload["start"] == "2026-05-28T21:30:00Z"
    assert payload["end"] == "2026-05-28T22:00:00Z"
