"""A write Follow Up Boss may have saved stays visible in Sentry while the caller gets guidance."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any, cast

import pytest
import sentry_sdk
from sentry_sdk.envelope import Envelope
from sentry_sdk.transport import Transport

from followupboss_mcp import observability
from followupboss_mcp.config import FollowUpBossSettings, SentrySettings
from followupboss_mcp.errors import FollowUpBossUnconfirmedWriteError
from followupboss_mcp.mcp_server import create_server
from followupboss_mcp.observability import configure_sentry
from mcp.client._memory import InMemoryTransport as MCPInMemoryTransport
from mcp.client.session import ClientSession


class UnconfirmedWriteClient:
    """Fail every request the way the HTTP client reports a POST that got a 5xx."""

    def __init__(self) -> None:
        """Capture every request so the test proves it was sent once."""
        self.calls: list[tuple[str, str]] = []

    async def aclose(self) -> None:
        """Implement the client lifecycle expected by the project server."""
        return None

    async def request_json(
        self,
        method: str,
        path: str,
        *,
        headers: Mapping[str, str] | None = None,
        json_body: Mapping[str, object] | None = None,
        params: Mapping[str, str] | None = None,
    ) -> dict[str, object] | list[object]:
        """Raise the error the HTTP client raises for a POST that got a server error."""
        del headers, json_body, params
        self.calls.append((method, path))
        raise FollowUpBossUnconfirmedWriteError(
            "Follow Up Boss returned HTTP 500.", status_code=500
        )


@pytest.mark.asyncio
async def test_unconfirmed_write_reaches_sentry_once_and_the_caller_with_guidance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The caller reads the lookup guidance, and Sentry still gets one error event."""
    captured_envelopes: list[Envelope] = []
    original_init = cast(Callable[..., object], sentry_sdk.init)

    class InMemorySentryTransport(Transport):
        """Keep test telemetry local rather than sending it to Sentry."""

        def capture_envelope(self, envelope: Envelope) -> None:
            """Record one local envelope without an HTTP request."""
            captured_envelopes.append(envelope)

    def init_with_in_memory_transport(*args: object, **kwargs: Any) -> object:
        """Initialize the real SDK with only an in-memory transport."""
        kwargs["transport"] = InMemorySentryTransport
        return original_init(*args, **kwargs)

    monkeypatch.setattr(observability, "_SENTRY_INITIALIZED", False)
    monkeypatch.setattr(sentry_sdk, "init", init_with_in_memory_transport)
    sentry_settings = SentrySettings.model_validate({"dsn": "https://public@example.invalid/1"})

    try:
        assert configure_sentry(sentry_settings, entrypoint="sentry-unconfirmed-write-test")
        client = UnconfirmedWriteClient()
        server = create_server(
            FollowUpBossSettings.model_validate({"api_key": "offline-test-key"}),
            client=client,
            sentry_settings=sentry_settings,
        )

        async with MCPInMemoryTransport(server) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.call_tool("followupboss_create_pipeline", {"name": "Buyers"})

        assert result.is_error is True
        assert len(result.content) == 1
        content = result.content[0]
        assert content.type == "text"
        assert "Follow Up Boss returned HTTP 500. Follow Up Boss may have saved" in content.text
        assert content.text.endswith("look that record up before trying again.")
        assert client.calls == [("POST", "/pipelines")]

        sentry_sdk.flush()
        events = [
            item.payload.json
            for envelope in captured_envelopes
            for item in envelope.items
            if item.headers.get("type") == "event"
        ]
        assert len(events) == 1
        event = events[0]
        assert isinstance(event, dict)
        assert event["level"] == "error"
        assert [value["type"] for value in event["exception"]["values"]] == [
            "FollowUpBossUnconfirmedWriteError"
        ]
        assert event["tags"]["component"] == "mcp_tools"
        assert event["tags"]["followupboss_status_code"] == "500"
    finally:
        sentry_sdk.get_client().close()
        original_init(dsn=None)
