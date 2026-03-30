"""Optional live sandbox validation for representative multi-domain contracts."""

from __future__ import annotations

import asyncio
import os
from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from followupboss_mcp.config import FollowUpBossSettings
from followupboss_mcp.errors import FollowUpBossForbiddenError, FollowUpBossNotFoundError
from followupboss_mcp.http_client import FollowUpBossAsyncClient
from followupboss_mcp.mcp_server import build_service_bundle
from followupboss_mcp.mcp_tools import FollowUpBossToolAdapter, ServiceBundle
from followupboss_mcp.models.appointments import (
    AppointmentInviteeInput,
    AppointmentRecord,
    CreateAppointmentRequest,
    UpdateAppointmentRequest,
)
from followupboss_mcp.models.attachments import (
    CreatePersonAttachmentRequest,
    PersonAttachmentRecord,
    UpdatePersonAttachmentRequest,
)
from followupboss_mcp.models.common import EmailAddress
from followupboss_mcp.models.notes import CreateNoteRequest, UpdateNoteRequest
from followupboss_mcp.models.people import (
    CreatePersonRequest,
    PeopleSearchRequest,
    PersonDuplicateCheckRequest,
    PersonRecord,
    UpdatePersonRequest,
)
from followupboss_mcp.models.reactions import CreateReactionRequest, DeleteReactionRequest
from followupboss_mcp.models.tasks import CreateTaskRequest, TaskRecord, UpdateTaskRequest
from followupboss_mcp.models.timeframes import TimeframeListRequest
from followupboss_mcp.models.users import CurrentUserRecord, UserListRequest
from followupboss_mcp.models.webhooks import (
    CreateWebhookRequest,
    UpdateWebhookRequest,
    WebhookRecord,
)

pytestmark = [pytest.mark.live]

_REDACTED = "***redacted***"


def _require_live_validation_enabled() -> None:
    """Skip the current test unless live validation was explicitly enabled."""
    if os.getenv("FOLLOWUPBOSS_RUN_LIVE_TESTS") != "1":
        pytest.skip("Live Follow Up Boss validation is disabled.")


@asynccontextmanager
async def _live_bundle(
    settings: FollowUpBossSettings | None = None,
) -> AsyncIterator[tuple[ServiceBundle, FollowUpBossToolAdapter]]:
    """Yield a live service bundle plus the MCP-safe adapter.

    Args:
        settings: Optional explicit settings for the live bundle. When omitted,
            the default environment-backed settings are used.

    Yields:
        The typed service bundle and MCP adapter that share one live HTTP client.
    """
    _require_live_validation_enabled()
    resolved_settings = settings or FollowUpBossSettings()
    async with FollowUpBossAsyncClient(resolved_settings) as client:
        services = build_service_bundle(client)
        yield services, FollowUpBossToolAdapter(services)


def _env_override_value(*names: str) -> str | None:
    """Return the first non-empty environment override value.

    Args:
        *names: Environment variable names to inspect in precedence order.

    Returns:
        The first non-empty value found, otherwise `None`.
    """
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return None


def _settings_as_init_values(settings: FollowUpBossSettings) -> dict[str, object]:
    """Convert runtime settings into model-validate input values.

    Args:
        settings: The resolved application settings.

    Returns:
        A plain dictionary suitable for `FollowUpBossSettings.model_validate()`.
    """
    return {
        "auth_mode": settings.auth_mode,
        "api_key": settings.api_key.get_secret_value() if settings.api_key is not None else None,
        "access_token": (
            settings.access_token.get_secret_value() if settings.access_token is not None else None
        ),
        "system_name": settings.system_name,
        "system_key": settings.system_key_value(),
        "base_url": str(settings.base_url),
        "timeout_seconds": settings.timeout_seconds,
        "max_retries": settings.max_retries,
        "log_level": settings.log_level,
    }


def _owner_live_settings() -> tuple[FollowUpBossSettings, bool]:
    """Resolve owner-capable live settings when optional overrides are configured.

    Returns:
        The resolved owner-capable settings plus a flag indicating whether
        owner-specific authentication overrides were supplied.
    """
    base_settings = FollowUpBossSettings()
    settings_data = _settings_as_init_values(base_settings)

    owner_auth_mode = _env_override_value(
        "FOLLOWUPBOSS_OWNER_AUTH_MODE",
        "FOLLOW_UP_BOSS_OWNER_AUTH_MODE",
    )
    owner_api_key = _env_override_value(
        "FOLLOWUPBOSS_OWNER_API_KEY",
        "FOLLOW_UP_BOSS_OWNER_API_KEY",
    )
    owner_access_token = _env_override_value(
        "FOLLOWUPBOSS_OWNER_ACCESS_TOKEN",
        "FOLLOW_UP_BOSS_OWNER_ACCESS_TOKEN",
    )
    owner_system_name = _env_override_value(
        "FOLLOWUPBOSS_OWNER_SYSTEM_NAME",
        "FOLLOW_UP_BOSS_OWNER_SYSTEM_NAME",
        "FOLLOWUPBOSS_OWNER_X_SYSTEM",
        "FOLLOW_UP_BOSS_OWNER_X_SYSTEM",
    )
    owner_system_key = _env_override_value(
        "FOLLOWUPBOSS_OWNER_SYSTEM_KEY",
        "FOLLOW_UP_BOSS_OWNER_SYSTEM_KEY",
        "FOLLOWUPBOSS_OWNER_X_SYSTEM_KEY",
        "FOLLOW_UP_BOSS_OWNER_X_SYSTEM_KEY",
    )

    using_owner_auth_override = any(
        value is not None for value in (owner_auth_mode, owner_api_key, owner_access_token)
    )

    if owner_api_key is not None:
        settings_data["api_key"] = owner_api_key
        settings_data["access_token"] = None
    if owner_access_token is not None:
        settings_data["access_token"] = owner_access_token
        settings_data["api_key"] = None
    if owner_auth_mode is not None:
        settings_data["auth_mode"] = owner_auth_mode
    elif owner_access_token is not None and owner_api_key is None:
        settings_data["auth_mode"] = "oauth"
    elif owner_api_key is not None:
        settings_data["auth_mode"] = "api_key"
    if owner_system_name is not None:
        settings_data["system_name"] = owner_system_name
    if owner_system_key is not None:
        settings_data["system_key"] = owner_system_key

    return FollowUpBossSettings.model_validate(settings_data), using_owner_auth_override


def _assert_redacted_field(
    payload: Mapping[str, object],
    *,
    key: str,
    raw_value: str | None,
) -> None:
    """Assert that one secret-like MCP field is redacted when present.

    Args:
        payload: The MCP-safe current-user payload.
        key: The aliased field name expected in the payload.
        raw_value: The original field value returned by the typed service call.
    """
    if raw_value is None:
        assert key not in payload or payload[key] is None
        return
    assert payload[key] == _REDACTED


def _assert_current_user_redaction(
    current_user: CurrentUserRecord,
    safe_payload: Mapping[str, object],
) -> None:
    """Assert MCP redaction behavior for the live current-user payload.

    Args:
        current_user: The raw typed current-user record from the service layer.
        safe_payload: The MCP-safe payload returned by the adapter layer.
    """
    _assert_redacted_field(safe_payload, key="apiKey", raw_value=current_user.api_key)
    _assert_redacted_field(safe_payload, key="algoliaKey", raw_value=current_user.algolia_key)
    _assert_redacted_field(
        safe_payload,
        key="callingCapabilityToken",
        raw_value=current_user.calling_capability_token,
    )

    if current_user.intercom_settings is None or current_user.intercom_settings.user_hash is None:
        return

    intercom_settings = safe_payload.get("intercomSettings")
    assert isinstance(intercom_settings, dict)
    assert intercom_settings["user_hash"] == _REDACTED


def _assert_page_payload_contract(
    payload: Mapping[str, object],
    *,
    collection_key: str,
    limit_upper_bound: int | None = None,
) -> list[Mapping[str, object]]:
    """Assert the normalized MCP page shape and return the item mappings.

    Args:
        payload: The MCP page payload returned by the adapter.
        collection_key: The top-level collection key expected in the payload.
        limit_upper_bound: An optional maximum allowed `_metadata.limit` value.

    Returns:
        The normalized item mappings from the collection payload.
    """
    metadata = payload.get("_metadata")
    assert isinstance(metadata, dict)

    limit_value = metadata.get("limit")
    assert isinstance(limit_value, int)
    if limit_upper_bound is not None:
        assert limit_value <= limit_upper_bound

    items = payload.get(collection_key)
    assert isinstance(items, list)
    normalized_items: list[Mapping[str, object]] = []
    for item in items:
        assert isinstance(item, dict)
        normalized_items.append(item)
    return normalized_items


def _build_positive_duplicate_request(person: PersonRecord) -> PersonDuplicateCheckRequest | None:
    """Build a duplicate-check request from a live person when possible.

    Args:
        person: The live person record returned by the API.

    Returns:
        A positive duplicate-check request if the record has an email or phone value,
        otherwise `None`.
    """
    for email in person.emails:
        if email.value:
            return PersonDuplicateCheckRequest(email=email.value)

    for phone in person.phones:
        if phone.value:
            return PersonDuplicateCheckRequest(phone=phone.value)

    return None


def _missing_duplicate_email() -> str:
    """Return a unique fake email for the negative duplicate-check path.

    Returns:
        A unique email address that should not match an existing live person.
    """
    return f"mcp-live-miss-{uuid4().hex}@example.com"


def _disposable_person_email() -> str:
    """Return a unique disposable email for live write-and-rollback tests.

    Returns:
        A unique email address safe to use for disposable sandbox records.
    """
    return f"mcp-live-person-{uuid4().hex[:12]}@example.com"


def _disposable_webhook_url() -> str:
    """Return a unique disposable webhook URL for live owner-only tests.

    Returns:
        A unique HTTPS URL safe to use as a disposable webhook target.
    """
    return f"https://example.com/followupboss-live-webhook/{uuid4().hex}"


async def _delete_note_reaction_if_present(
    services: ServiceBundle,
    note_id: int | None,
    *,
    reaction_emoji: str | None,
) -> None:
    """Delete a note reaction during live cleanup when it may still exist.

    Args:
        services: The live service bundle.
        note_id: The optional note identifier hosting the reaction.
        reaction_emoji: The optional reaction body used for targeted deletion.
    """
    if note_id is None or reaction_emoji is None:
        return
    try:
        await services.reactions.delete_reaction(
            "Note",
            note_id,
            DeleteReactionRequest(emoji=reaction_emoji),
        )
    except FollowUpBossNotFoundError:
        return


async def _delete_note_if_present(services: ServiceBundle, note_id: int | None) -> None:
    """Delete a note during live cleanup when it still exists.

    Args:
        services: The live service bundle.
        note_id: The optional note identifier to delete.
    """
    if note_id is None:
        return
    try:
        await services.notes.delete_note(note_id)
    except FollowUpBossNotFoundError:
        return


async def _delete_person_if_present(services: ServiceBundle, person_id: int | None) -> None:
    """Delete a person during live cleanup when it still exists.

    Args:
        services: The live service bundle.
        person_id: The optional person identifier to delete.
    """
    if person_id is None:
        return
    try:
        await services.people.delete_person(person_id)
    except FollowUpBossNotFoundError:
        return


async def _delete_person_attachment_if_present(
    services: ServiceBundle, person_attachment_id: int | None
) -> None:
    """Delete a person attachment during live cleanup when it still exists.

    Args:
        services: The live service bundle.
        person_attachment_id: The optional person attachment identifier to delete.
    """
    if person_attachment_id is None:
        return
    try:
        await services.person_attachments.delete_person_attachment(person_attachment_id)
    except FollowUpBossNotFoundError:
        return


async def _wait_for_person_deletion(
    services: ServiceBundle,
    person_id: int,
    *,
    attempts: int = 5,
    delay_seconds: float = 1.0,
) -> None:
    """Poll until a deleted person is no longer retrievable.

    Args:
        services: The live service bundle.
        person_id: The person identifier expected to disappear.
        attempts: The maximum number of read attempts.
        delay_seconds: The sleep duration between attempts.

    Raises:
        AssertionError: If the person still exists after the final poll.
    """
    for attempt in range(attempts):
        try:
            await services.people.get_person(person_id)
        except FollowUpBossNotFoundError:
            return
        if attempt == attempts - 1:
            raise AssertionError(f"Expected person {person_id} to be deleted.")
        await asyncio.sleep(delay_seconds)


async def _delete_task_if_present(services: ServiceBundle, task_id: int | None) -> None:
    """Delete a task during live cleanup when it still exists.

    Args:
        services: The live service bundle.
        task_id: The optional task identifier to delete.
    """
    if task_id is None:
        return
    try:
        await services.tasks.delete_task(task_id)
    except FollowUpBossNotFoundError:
        return


async def _delete_appointment_if_present(
    services: ServiceBundle, appointment_id: int | None
) -> None:
    """Delete an appointment during live cleanup when it still exists.

    Args:
        services: The live service bundle.
        appointment_id: The optional appointment identifier to delete.
    """
    if appointment_id is None:
        return
    try:
        await services.appointments.delete_appointment(appointment_id)
    except FollowUpBossNotFoundError:
        return


async def _delete_webhook_if_present(services: ServiceBundle, webhook_id: int | None) -> None:
    """Delete a webhook during live cleanup when it still exists.

    Args:
        services: The live service bundle.
        webhook_id: The optional webhook identifier to delete.
    """
    if webhook_id is None:
        return
    try:
        await services.webhooks.delete_webhook(webhook_id)
    except FollowUpBossNotFoundError:
        return


async def _wait_for_task(
    services: ServiceBundle,
    task_id: int,
    *,
    attempts: int = 5,
    delay_seconds: float = 1.0,
) -> TaskRecord:
    """Poll until a created task is visible.

    Args:
        services: The live service bundle.
        task_id: The task identifier to retrieve.
        attempts: The maximum number of read attempts.
        delay_seconds: The sleep duration between attempts.

    Returns:
        The visible task record.

    Raises:
        FollowUpBossNotFoundError: If the task never becomes visible.
    """
    for attempt in range(attempts):
        try:
            return await services.tasks.get_task(task_id)
        except FollowUpBossNotFoundError:
            if attempt == attempts - 1:
                raise
            await asyncio.sleep(delay_seconds)
    raise AssertionError("Unreachable")


async def _wait_for_person_attachment(
    services: ServiceBundle,
    person_attachment_id: int,
    *,
    attempts: int = 5,
    delay_seconds: float = 1.0,
) -> PersonAttachmentRecord:
    """Poll until a created person attachment is visible.

    Args:
        services: The live service bundle.
        person_attachment_id: The person attachment identifier to retrieve.
        attempts: The maximum number of read attempts.
        delay_seconds: The sleep duration between attempts.

    Returns:
        The visible person attachment record.

    Raises:
        FollowUpBossNotFoundError: If the attachment never becomes visible.
    """
    for attempt in range(attempts):
        try:
            return await services.person_attachments.get_person_attachment(person_attachment_id)
        except FollowUpBossNotFoundError:
            if attempt == attempts - 1:
                raise
            await asyncio.sleep(delay_seconds)
    raise AssertionError("Unreachable")


async def _wait_for_appointment(
    services: ServiceBundle,
    appointment_id: int,
    *,
    attempts: int = 5,
    delay_seconds: float = 1.0,
) -> AppointmentRecord:
    """Poll until a created appointment is visible.

    Args:
        services: The live service bundle.
        appointment_id: The appointment identifier to retrieve.
        attempts: The maximum number of read attempts.
        delay_seconds: The sleep duration between attempts.

    Returns:
        The visible appointment record.

    Raises:
        FollowUpBossNotFoundError: If the appointment never becomes visible.
    """
    for attempt in range(attempts):
        try:
            return await services.appointments.get_appointment(appointment_id)
        except FollowUpBossNotFoundError:
            if attempt == attempts - 1:
                raise
            await asyncio.sleep(delay_seconds)
    raise AssertionError("Unreachable")


async def _wait_for_webhook(
    services: ServiceBundle,
    webhook_id: int,
    *,
    attempts: int = 5,
    delay_seconds: float = 1.0,
) -> WebhookRecord:
    """Poll until a created webhook is visible.

    Args:
        services: The live service bundle.
        webhook_id: The webhook identifier to retrieve.
        attempts: The maximum number of read attempts.
        delay_seconds: The sleep duration between attempts.

    Returns:
        The visible webhook record.

    Raises:
        FollowUpBossNotFoundError: If the webhook never becomes visible.
    """
    for attempt in range(attempts):
        try:
            return await services.webhooks.get_webhook(webhook_id)
        except FollowUpBossNotFoundError:
            if attempt == attempts - 1:
                raise
            await asyncio.sleep(delay_seconds)
    raise AssertionError("Unreachable")


async def _wait_for_task_deletion(
    services: ServiceBundle,
    task_id: int,
    *,
    attempts: int = 5,
    delay_seconds: float = 1.0,
) -> None:
    """Poll until a deleted task is no longer retrievable.

    Args:
        services: The live service bundle.
        task_id: The task identifier expected to disappear.
        attempts: The maximum number of read attempts.
        delay_seconds: The sleep duration between attempts.

    Raises:
        AssertionError: If the task still exists after the final poll.
    """
    for attempt in range(attempts):
        try:
            await services.tasks.get_task(task_id)
        except FollowUpBossNotFoundError:
            return
        if attempt == attempts - 1:
            raise AssertionError(f"Expected task {task_id} to be deleted.")
        await asyncio.sleep(delay_seconds)


async def _wait_for_person_attachment_deletion(
    services: ServiceBundle,
    person_attachment_id: int,
    *,
    attempts: int = 5,
    delay_seconds: float = 1.0,
) -> None:
    """Poll until a deleted person attachment is no longer retrievable.

    Args:
        services: The live service bundle.
        person_attachment_id: The person attachment identifier expected to disappear.
        attempts: The maximum number of read attempts.
        delay_seconds: The sleep duration between attempts.

    Raises:
        AssertionError: If the attachment still exists after the final poll.
    """
    for attempt in range(attempts):
        try:
            await services.person_attachments.get_person_attachment(person_attachment_id)
        except FollowUpBossNotFoundError:
            return
        if attempt == attempts - 1:
            raise AssertionError(
                f"Expected person attachment {person_attachment_id} to be deleted."
            )
        await asyncio.sleep(delay_seconds)


async def _wait_for_appointment_deletion(
    services: ServiceBundle,
    appointment_id: int,
    *,
    attempts: int = 5,
    delay_seconds: float = 1.0,
) -> None:
    """Poll until a deleted appointment is no longer retrievable.

    Args:
        services: The live service bundle.
        appointment_id: The appointment identifier expected to disappear.
        attempts: The maximum number of read attempts.
        delay_seconds: The sleep duration between attempts.

    Raises:
        AssertionError: If the appointment still exists after the final poll.
    """
    for attempt in range(attempts):
        try:
            await services.appointments.get_appointment(appointment_id)
        except FollowUpBossNotFoundError:
            return
        if attempt == attempts - 1:
            raise AssertionError(f"Expected appointment {appointment_id} to be deleted.")
        await asyncio.sleep(delay_seconds)


async def _wait_for_webhook_deletion(
    services: ServiceBundle,
    webhook_id: int,
    *,
    attempts: int = 5,
    delay_seconds: float = 1.0,
) -> None:
    """Poll until a deleted webhook is no longer retrievable.

    Args:
        services: The live service bundle.
        webhook_id: The webhook identifier expected to disappear.
        attempts: The maximum number of read attempts.
        delay_seconds: The sleep duration between attempts.

    Raises:
        AssertionError: If the webhook still exists after the final poll.
    """
    for attempt in range(attempts):
        try:
            await services.webhooks.get_webhook(webhook_id)
        except FollowUpBossNotFoundError:
            return
        if attempt == attempts - 1:
            raise AssertionError(f"Expected webhook {webhook_id} to be deleted.")
        await asyncio.sleep(delay_seconds)


@pytest.mark.asyncio
async def test_live_identity_and_user_contracts() -> None:
    """Validate representative live identity, user, and MCP redaction contracts."""
    async with _live_bundle() as (services, adapter):
        health = await services.identity.health_check()
        current_user = await services.users.get_me()
        safe_current_user = await adapter.get_me()
        users_page = await services.users.list_users(UserListRequest(limit=1))
        listed_user_id = users_page.items[0].id if users_page.items else current_user.id
        listed_user = await services.users.get_user(listed_user_id)

    assert health.ok is True
    assert health.identity.account_id is not None
    assert health.identity.account_id > 0
    assert current_user.id > 0
    if health.identity.user is not None and health.identity.user.id is not None:
        assert health.identity.user.id == current_user.id
    assert safe_current_user["id"] == current_user.id
    _assert_current_user_redaction(current_user, safe_current_user)
    assert users_page.metadata.count <= 1
    assert users_page.metadata.limit <= 1
    assert listed_user.id == listed_user_id


@pytest.mark.asyncio
async def test_live_people_timeframe_and_duplicate_contracts() -> None:
    """Validate representative live people, timeframe, and duplicate-check contracts."""
    async with _live_bundle() as (services, adapter):
        people_payload = await adapter.search_people(PeopleSearchRequest(limit=1))
        timeframe_payload = await adapter.list_timeframes(TimeframeListRequest())
        duplicate_miss = await services.people.check_duplicate_person(
            PersonDuplicateCheckRequest(email=_missing_duplicate_email())
        )

        people_items = _assert_page_payload_contract(
            people_payload,
            collection_key="people",
            limit_upper_bound=1,
        )
        timeframe_items = _assert_page_payload_contract(
            timeframe_payload,
            collection_key="timeframes",
        )

        positive_duplicate = None
        fetched_person_id = None
        if people_items:
            first_person_id = people_items[0].get("id")
            assert isinstance(first_person_id, int)
            person = await services.people.get_person(first_person_id)
            positive_duplicate_request = _build_positive_duplicate_request(person)
            if positive_duplicate_request is not None:
                positive_duplicate = await services.people.check_duplicate_person(
                    positive_duplicate_request
                )
            fetched_person_id = person.id

    assert duplicate_miss.found is False
    assert timeframe_items
    for timeframe in timeframe_items:
        timeframe_id = timeframe.get("id")
        assert isinstance(timeframe_id, int)
        assert timeframe_id > 0

    if people_items:
        assert fetched_person_id is not None
        assert fetched_person_id > 0
    if positive_duplicate is not None:
        assert positive_duplicate.found is True


@pytest.mark.asyncio
async def test_live_person_and_note_write_contracts() -> None:
    """Validate disposable live person and note write flows with cleanup."""
    person_id: int | None = None
    note_id: int | None = None
    task_id: int | None = None
    appointment_id: int | None = None
    note_reaction_emoji: str | None = None
    disposable_email = _disposable_person_email()

    async with _live_bundle() as (services, _adapter):
        try:
            current_user = await services.users.get_me()
            created_person = await services.people.create_person(
                CreatePersonRequest(
                    first_name="MCP",
                    last_name="Validation Person",
                    emails=[EmailAddress(value=disposable_email, type="work")],
                    source="MCP Live Contract",
                    deduplicate=True,
                )
            )
            person_id = created_person.id
            assert created_person.id > 0

            waited_person = await services.people.wait_for_person(created_person.id)
            assert waited_person.id == created_person.id

            updated_person = await services.people.update_person(
                created_person.id,
                UpdatePersonRequest(
                    first_name="MCP Updated",
                    tags=["mcp-live-updated"],
                ),
            )
            assert updated_person.id == created_person.id
            assert updated_person.first_name == "MCP Updated"

            looked_up_person = await services.people.get_person(created_person.id)
            assert looked_up_person.id == created_person.id
            assert looked_up_person.first_name == "MCP Updated"

            duplicate_result = await services.people.check_duplicate_person(
                PersonDuplicateCheckRequest(email=disposable_email)
            )
            assert duplicate_result.found is True

            created_note = await services.notes.add_note(
                CreateNoteRequest(
                    person_id=created_person.id,
                    subject="MCP Live Validation",
                    body="Created by the optional live write-and-rollback suite.",
                ),
                wait_for_person=True,
            )
            note_id = created_note.id
            assert created_note.id > 0
            assert created_note.person_id == created_person.id

            loaded_note = await services.notes.get_note(created_note.id)
            assert loaded_note.id == created_note.id
            assert loaded_note.person_id == created_person.id

            updated_note = await services.notes.update_note(
                created_note.id,
                UpdateNoteRequest(body="Updated by the optional live write-and-rollback suite."),
            )
            assert updated_note.id == created_note.id
            assert updated_note.body == "Updated by the optional live write-and-rollback suite."

            note_reaction_emoji = "👏"
            reaction_ack = await services.reactions.add_reaction(
                "Note",
                created_note.id,
                CreateReactionRequest(body=note_reaction_emoji),
            )
            assert reaction_ack.model_dump(mode="json", exclude_none=True) == {}

            await services.reactions.delete_reaction(
                "Note",
                created_note.id,
                DeleteReactionRequest(emoji=note_reaction_emoji),
            )
            note_reaction_emoji = None

            created_task = await services.tasks.create_task(
                CreateTaskRequest(
                    person_id=created_person.id,
                    assigned_user_id=current_user.id,
                    name="MCP Live Task",
                    type="Call",
                )
            )
            task_id = created_task.id
            assert created_task.id > 0
            assert created_task.person_id == created_person.id

            loaded_task = await _wait_for_task(services, created_task.id)
            assert loaded_task.id == created_task.id
            assert loaded_task.person_id == created_person.id

            updated_task = await services.tasks.update_task(
                created_task.id,
                UpdateTaskRequest(
                    name="MCP Live Task Updated",
                    is_completed=True,
                ),
            )
            assert updated_task.id == created_task.id
            assert updated_task.name == "MCP Live Task Updated"
            assert updated_task.is_completed is True

            start_time = datetime.now(UTC).replace(microsecond=0) + timedelta(days=1)
            end_time = start_time + timedelta(hours=1)
            created_appointment = await services.appointments.create_appointment(
                CreateAppointmentRequest(
                    title="MCP Live Appointment",
                    start=start_time,
                    end=end_time,
                    invitees=[
                        AppointmentInviteeInput(
                            person_id=created_person.id,
                            name="MCP Updated",
                            user_id=current_user.id,
                        )
                    ],
                )
            )
            appointment_id = created_appointment.id
            assert created_appointment.id > 0

            loaded_appointment = await _wait_for_appointment(services, created_appointment.id)
            assert loaded_appointment.id == created_appointment.id
            assert loaded_appointment.title == "MCP Live Appointment"

            updated_appointment = await services.appointments.update_appointment(
                created_appointment.id,
                UpdateAppointmentRequest(
                    title="MCP Live Appointment Updated",
                    start=start_time,
                    end=end_time,
                    invitees=[
                        AppointmentInviteeInput(
                            person_id=created_person.id,
                            name="MCP Updated",
                            user_id=current_user.id,
                        )
                    ],
                ),
            )
            assert updated_appointment.id == created_appointment.id
            assert updated_appointment.title == "MCP Live Appointment Updated"

        finally:
            await _delete_note_reaction_if_present(
                services,
                note_id,
                reaction_emoji=note_reaction_emoji,
            )
            await _delete_appointment_if_present(services, appointment_id)
            await _delete_task_if_present(services, task_id)
            await _delete_note_if_present(services, note_id)
            await _delete_person_if_present(services, person_id)

            if appointment_id is not None:
                await _wait_for_appointment_deletion(services, appointment_id)
            if task_id is not None:
                await _wait_for_task_deletion(services, task_id)
            if person_id is not None:
                await _wait_for_person_deletion(services, person_id)


@pytest.mark.asyncio
async def test_live_person_attachment_write_contracts() -> None:
    """Validate disposable person attachment CRUD with registered-system headers."""
    settings = FollowUpBossSettings()
    if settings.system_name is None or settings.system_key_value() is None:
        pytest.skip("Registered system headers are required for live attachment CRUD.")

    person_id: int | None = None
    person_attachment_id: int | None = None
    disposable_email = _disposable_person_email()

    async with _live_bundle() as (services, _adapter):
        try:
            created_person = await services.people.create_person(
                CreatePersonRequest(
                    first_name="MCP Attachment",
                    last_name="Validation Person",
                    emails=[EmailAddress(value=disposable_email, type="work")],
                    source="MCP Live Attachment Contract",
                    deduplicate=True,
                )
            )
            person_id = created_person.id
            assert created_person.id > 0

            await services.people.wait_for_person(created_person.id)

            created_attachment = await services.person_attachments.create_person_attachment(
                CreatePersonAttachmentRequest(
                    person_id=created_person.id,
                    uri="https://example.com/",
                    file_name="mcp-live-attachment.txt",
                    file_size=128,
                )
            )
            person_attachment_id = created_attachment.id
            assert created_attachment.id > 0
            assert created_attachment.person_id == created_person.id

            loaded_attachment = await _wait_for_person_attachment(services, created_attachment.id)
            assert loaded_attachment.id == created_attachment.id
            assert loaded_attachment.person_id == created_person.id

            updated_attachment = await services.person_attachments.update_person_attachment(
                created_attachment.id,
                UpdatePersonAttachmentRequest(
                    person_id=created_person.id,
                    uri="https://example.com/?mcp-live-attachment=updated",
                    file_name="mcp-live-attachment-updated.txt",
                    file_size=256,
                ),
            )
            assert updated_attachment.id == created_attachment.id
            assert updated_attachment.file_name == "mcp-live-attachment-updated.txt"

        finally:
            await _delete_person_attachment_if_present(services, person_attachment_id)
            await _delete_person_if_present(services, person_id)

            if person_attachment_id is not None:
                await _wait_for_person_attachment_deletion(services, person_attachment_id)
            if person_id is not None:
                await _wait_for_person_deletion(services, person_id)


@pytest.mark.asyncio
async def test_live_webhook_write_contracts() -> None:
    """Validate owner-only live webhook CRUD when credentials allow it."""
    owner_settings, using_owner_auth_override = _owner_live_settings()
    if owner_settings.system_name is None or owner_settings.system_key_value() is None:
        pytest.skip("Registered system headers are required for live webhook CRUD.")

    webhook_id: int | None = None
    webhook_url = _disposable_webhook_url()

    async with _live_bundle(owner_settings) as (services, _adapter):
        try:
            try:
                webhooks_page = await services.webhooks.list_webhooks()
            except FollowUpBossForbiddenError:
                if not using_owner_auth_override:
                    pytest.skip(
                        "Owner-level webhook access is unavailable for the current credential. "
                        "Set FOLLOWUPBOSS_OWNER_API_KEY or FOLLOWUPBOSS_OWNER_ACCESS_TOKEN "
                        "to exercise this path."
                    )
                raise

            assert webhooks_page.metadata.count >= 0

            try:
                created_webhook = await services.webhooks.create_webhook(
                    CreateWebhookRequest(event="peopleCreated", url=webhook_url)
                )
                webhook_id = created_webhook.id
                assert created_webhook.id > 0
                assert created_webhook.event == "peopleCreated"
                assert created_webhook.url == webhook_url

                loaded_webhook = await _wait_for_webhook(services, created_webhook.id)
                assert loaded_webhook.id == created_webhook.id
                assert loaded_webhook.url == webhook_url

                updated_webhook = await services.webhooks.update_webhook(
                    created_webhook.id,
                    UpdateWebhookRequest(status="Disabled"),
                )
                assert updated_webhook.id == created_webhook.id
                assert updated_webhook.status == "Disabled"
            except FollowUpBossForbiddenError:
                if not using_owner_auth_override:
                    pytest.skip(
                        "Owner-level webhook mutations are unavailable for the current credential. "
                        "Set FOLLOWUPBOSS_OWNER_API_KEY or FOLLOWUPBOSS_OWNER_ACCESS_TOKEN "
                        "to exercise this path."
                    )
                raise

        finally:
            await _delete_webhook_if_present(services, webhook_id)
            if webhook_id is not None:
                await _wait_for_webhook_deletion(services, webhook_id)
