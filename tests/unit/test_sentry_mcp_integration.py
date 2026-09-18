"""Regression coverage for the Sentry MCP SDK integration."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any, cast

import pytest
import sentry_sdk
from sentry_sdk.envelope import Envelope
from sentry_sdk.integrations.mcp import MCPIntegration
from sentry_sdk.transport import Transport

from followupboss_mcp import observability
from followupboss_mcp.config import FollowUpBossSettings, SentrySettings
from followupboss_mcp.mcp_server import create_server
from followupboss_mcp.observability import configure_sentry
from mcp.client._memory import InMemoryTransport as MCPInMemoryTransport
from mcp.client.session import ClientSession

_REDACTED = "***redacted***"


class OfflineSmartListClient:
    """Return a deterministic empty smart-list collection without network access."""

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
        """Serve the one local lookup request used by this regression."""
        del method, headers, json_body, params
        assert path == "/smartLists"
        return {
            "_metadata": {"limit": 100, "offset": 0, "total": 0},
            "smartlists": [],
        }


def _transaction_payloads(envelopes: list[Envelope]) -> list[dict[str, object]]:
    """Return only transaction payloads captured by the local Sentry transport."""
    payloads: list[dict[str, object]] = []
    for envelope in envelopes:
        for item in envelope.items:
            if item.headers.get("type") != "transaction":
                continue
            payload = item.payload.json
            assert isinstance(payload, dict)
            payloads.append(cast(dict[str, object], payload))
    return payloads


def _mcp_argument_values(payload: object) -> list[object]:
    """Return values attached under Sentry's MCP request-argument keys."""
    values: list[object] = []
    if isinstance(payload, Mapping):
        for key, value in payload.items():
            if isinstance(key, str) and key.casefold().startswith("mcp.request.argument."):
                values.append(value)
            values.extend(_mcp_argument_values(value))
    elif isinstance(payload, list):
        for value in payload:
            values.extend(_mcp_argument_values(value))
    return values


@pytest.mark.asyncio
async def test_sentry_mcp_integration_handles_local_lookup_errors_over_the_protocol(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Expected MCP lookup failures stay actionable, event-free, and privacy-safe."""
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

    missing_smart_list_name = "Missing confidential smart list"
    monkeypatch.setattr(observability, "_SENTRY_INITIALIZED", False)
    monkeypatch.setattr(sentry_sdk, "init", init_with_in_memory_transport)
    sentry_settings = SentrySettings.model_validate(
        {
            "dsn": "https://public@example.invalid/1",
            "traces_sample_rate": 1.0,
        }
    )

    try:
        assert configure_sentry(sentry_settings, entrypoint="sentry-mcp-integration-test") is True
        assert sentry_sdk.get_client().get_integration(MCPIntegration) is not None

        server = create_server(
            FollowUpBossSettings.model_validate({"api_key": "offline-test-key"}),
            client=OfflineSmartListClient(),
            sentry_settings=sentry_settings,
        )

        async with MCPInMemoryTransport(server) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.call_tool(
                    "followupboss_search_people_in_smart_list",
                    {"smart_list_name": missing_smart_list_name},
                )

        assert result.is_error is True
        assert len(result.content) == 1
        content = result.content[0]
        assert content.type == "text"
        assert missing_smart_list_name in content.text
        assert "was not found" in content.text

        sentry_sdk.flush()
        assert all(
            item.headers.get("type") != "event"
            for envelope in captured_envelopes
            for item in envelope.items
        )

        transactions = _transaction_payloads(captured_envelopes)
        assert transactions
        argument_values = [
            value for transaction in transactions for value in _mcp_argument_values(transaction)
        ]
        assert argument_values
        assert all(value == _REDACTED for value in argument_values)
    finally:
        sentry_sdk.get_client().close()
        original_init(dsn=None)
