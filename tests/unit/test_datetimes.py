"""Tests for timezone normalization of appointment and task datetimes."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from followupboss_mcp.datetimes import (
    normalize_datetime,
    normalize_optional_datetime,
    resolve_default_timezone,
)
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


def test_create_appointment_localizes_naive_start_end(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Naive appointment times should serialize with the configured offset.

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
    assert payload["start"] == "2026-05-28T15:30:00-06:00"
    assert payload["end"] == "2026-05-28T16:00:00-06:00"


def test_create_appointment_preserves_explicit_offset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An explicit offset should win over the configured default timezone.

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
    assert payload["start"] == "2026-05-28T15:30:00-05:00"
    assert payload["end"] == "2026-05-28T16:00:00-05:00"


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


def test_update_appointment_localizes_naive_start_end(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Update requests should localize naive times like create requests.

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
    assert payload["start"] == "2026-05-28T15:30:00-06:00"
    assert payload["end"] == "2026-05-28T16:00:00-06:00"


def test_appointment_list_request_localizes_naive_filters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Naive appointment list filters should serialize with the offset.

    Args:
        monkeypatch: Fixture used to set the configured timezone env var.
    """
    monkeypatch.setenv("FOLLOWUPBOSS_DEFAULT_TIMEZONE", "America/Denver")
    request = AppointmentListRequest.model_validate(
        {"start": "2026-05-28T00:00:00", "end": "2026-05-28T23:59:59"}
    )
    params = request.to_query_params()
    assert params["start"] == "2026-05-28T00:00:00-06:00"
    assert params["end"] == "2026-05-28T23:59:59-06:00"


def test_create_task_localizes_naive_due_date_time(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A naive task due time should serialize with the configured offset.

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
    assert payload["dueDateTime"] == "2026-05-28T15:30:00-06:00"


def test_update_task_preserves_explicit_offset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An explicit task due offset should be preserved over the default.

    Args:
        monkeypatch: Fixture used to set the configured timezone env var.
    """
    monkeypatch.setenv("FOLLOWUPBOSS_DEFAULT_TIMEZONE", "America/Denver")
    request = UpdateTaskRequest.model_validate(
        {"person_id": 99, "due_date_time": "2026-05-28T15:30:00+02:00"}
    )
    payload = request.model_dump(mode="json", by_alias=True, exclude_none=True)
    assert payload["dueDateTime"] == "2026-05-28T15:30:00+02:00"


def test_task_list_request_localizes_naive_due_range(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Naive task due-range filters should serialize with the offset.

    Args:
        monkeypatch: Fixture used to set the configured timezone env var.
    """
    monkeypatch.setenv("FOLLOWUPBOSS_DEFAULT_TIMEZONE", "America/Denver")
    request = TaskListRequest.model_validate(
        {"due_start": "2026-05-28T00:00:00", "due_end": "2026-05-28T23:59:59"}
    )
    params = request.to_query_params()
    assert params["dueStart"] == "2026-05-28T00:00:00-06:00"
    assert params["dueEnd"] == "2026-05-28T23:59:59-06:00"


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
