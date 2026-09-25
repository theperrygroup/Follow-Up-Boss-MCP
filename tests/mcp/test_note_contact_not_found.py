"""Regressions for provider note errors through the public MCP boundary."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, cast

import httpx
import pytest
import sentry_sdk
from sentry_sdk.envelope import Envelope
from sentry_sdk.integrations.mcp import MCPIntegration
from sentry_sdk.transport import Transport

from followupboss_mcp import observability
from followupboss_mcp.config import FollowUpBossSettings, SentrySettings
from followupboss_mcp.errors import FollowUpBossNotFoundError, FollowUpBossValidationError
from followupboss_mcp.http_client import FollowUpBossAsyncClient
from followupboss_mcp.mcp_server import create_server
from followupboss_mcp.models.notes import CreateNoteRequest
from followupboss_mcp.services.notes import NotesService
from mcp.client._memory import InMemoryTransport as MCPInMemoryTransport
from mcp.client.session import ClientSession
from mcp.server.mcpserver.exceptions import ToolError, UnexpectedToolError


@pytest.mark.asyncio
@pytest.mark.parametrize("status_code", [400, 404])
async def test_add_note_contact_not_found_is_anticipated(status_code: int) -> None:
    """A notes-specific missing contact must not become an unexpected crash."""
    calls: list[tuple[str, str]] = []

    def respond(request: httpx.Request) -> httpx.Response:
        calls.append((request.method, request.url.path))
        if request.url.path == "/v1/me":
            return httpx.Response(200, json={"id": 1})
        assert request.method == "POST"
        assert request.url.path == "/v1/notes"
        return httpx.Response(status_code, json={"errorMessage": "Contact not found."})

    settings = FollowUpBossSettings.model_validate({"api_key": "test", "max_retries": 0})
    async with httpx.AsyncClient(
        base_url=str(settings.base_url), transport=httpx.MockTransport(respond)
    ) as http_client:
        client = FollowUpBossAsyncClient(settings, http_client=http_client)
        server = create_server(settings, client=client)
        with pytest.raises(ToolError) as exc_info:
            await server.call_tool(
                "followupboss_add_note", {"person_id": 999, "body": "Example note"}
            )

    assert not isinstance(exc_info.value, UnexpectedToolError)
    assert "Contact not found" in str(exc_info.value)
    if status_code == 400:
        assert "Verify person_id" in str(exc_info.value)
    assert calls.count(("POST", "/v1/notes")) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status_code", "provider_message", "expected_message", "expect_event"),
    [
        (400, "Contact not found.", "Verify person_id", False),
        (400, "Invalid note body.", "Error executing tool", True),
        (500, "Contact not found.", "Error executing tool", True),
    ],
)
async def test_note_error_sentry_behavior_over_protocol(
    monkeypatch: pytest.MonkeyPatch,
    status_code: int,
    provider_message: str,
    expected_message: str,
    expect_event: bool,
) -> None:
    """A missing contact is event-free while unrelated failures stay observable."""
    envelopes: list[Envelope] = []
    calls: list[tuple[str, str]] = []
    original_init = cast(Callable[..., object], sentry_sdk.init)

    class LocalSentryTransport(Transport):
        def capture_envelope(self, envelope: Envelope) -> None:
            envelopes.append(envelope)

    def init_locally(*args: object, **kwargs: Any) -> object:
        kwargs["transport"] = LocalSentryTransport
        return original_init(*args, **kwargs)

    def respond(request: httpx.Request) -> httpx.Response:
        calls.append((request.method, request.url.path))
        assert request.method == "POST"
        assert request.url.path == "/v1/notes"
        return httpx.Response(status_code, json={"errorMessage": provider_message})

    monkeypatch.setattr(observability, "_SENTRY_INITIALIZED", False)
    monkeypatch.setattr(sentry_sdk, "init", init_locally)
    sentry_settings = SentrySettings.model_validate({"dsn": "https://public@example.invalid/1"})
    settings = FollowUpBossSettings.model_validate({"api_key": "test", "max_retries": 0})
    try:
        assert observability.configure_sentry(sentry_settings, entrypoint="notes-error-test")
        assert sentry_sdk.get_client().get_integration(MCPIntegration) is not None
        async with httpx.AsyncClient(
            base_url=str(settings.base_url), transport=httpx.MockTransport(respond)
        ) as http_client:
            client = FollowUpBossAsyncClient(settings, http_client=http_client)
            server = create_server(settings, client=client, sentry_settings=sentry_settings)
            async with MCPInMemoryTransport(server) as (read_stream, write_stream):
                async with ClientSession(read_stream, write_stream) as session:
                    await session.initialize()
                    result = await session.call_tool(
                        "followupboss_add_note", {"person_id": 999, "body": "Example note"}
                    )
        assert result.is_error is True
        assert len(result.content) == 1
        content = result.content[0]
        assert content.type == "text"
        assert expected_message in content.text
        assert calls == [("POST", "/v1/notes")]
        sentry_sdk.flush()
        has_event = any(
            item.headers.get("type") == "event" for envelope in envelopes for item in envelope.items
        )
        assert has_event is expect_event
    finally:
        sentry_sdk.get_client().close()
        original_init(dsn=None)


@pytest.mark.asyncio
async def test_notes_missing_contact_preserves_provider_error_context() -> None:
    settings = FollowUpBossSettings.model_validate({"api_key": "test", "max_retries": 0})
    async with httpx.AsyncClient(
        base_url=str(settings.base_url),
        transport=httpx.MockTransport(
            lambda request: httpx.Response(400, json={"errorMessage": "Contact not found."})
        ),
    ) as http_client:
        client = FollowUpBossAsyncClient(settings, http_client=http_client)
        with pytest.raises(FollowUpBossNotFoundError, match="Verify person_id") as exc_info:
            await NotesService(client).add_note(CreateNoteRequest(person_id=999, body="Example"))
    assert exc_info.value.status_code == 400
    assert exc_info.value.payload == {"errorMessage": "Contact not found."}
    assert isinstance(exc_info.value.__cause__, FollowUpBossValidationError)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status_code", "message"),
    [(400, "Invalid note body."), (422, "Contact not found."), (500, "Contact not found.")],
)
async def test_other_note_failures_remain_unexpected(status_code: int, message: str) -> None:
    calls: list[tuple[str, str]] = []

    def respond(request: httpx.Request) -> httpx.Response:
        calls.append((request.method, request.url.path))
        if request.url.path == "/v1/me":
            return httpx.Response(200, json={"id": 1})
        assert request.method == "POST"
        assert request.url.path == "/v1/notes"
        return httpx.Response(status_code, json={"errorMessage": message})

    settings = FollowUpBossSettings.model_validate({"api_key": "test", "max_retries": 0})
    async with httpx.AsyncClient(
        base_url=str(settings.base_url), transport=httpx.MockTransport(respond)
    ) as http_client:
        client = FollowUpBossAsyncClient(settings, http_client=http_client)
        server = create_server(settings, client=client)
        with pytest.raises(UnexpectedToolError):
            await server.call_tool(
                "followupboss_add_note", {"person_id": 999, "body": "Example note"}
            )
    assert calls.count(("POST", "/v1/notes")) == 1
