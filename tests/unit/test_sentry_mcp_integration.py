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


class OfflineExpectedErrorClient:
    """Serve only the read endpoints needed by expected-error protocol calls."""

    def __init__(self) -> None:
        """Capture every request so error paths prove their side-effect boundary."""
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
        """Return only deterministic identity or empty-smart-list responses."""
        del headers, json_body, params
        self.calls.append((method, path))
        if path == "/smartLists":
            return {
                "_metadata": {"limit": 100, "offset": 0, "total": 0},
                "smartlists": [],
            }
        if path == "/identity":
            return {"id": 1}
        raise AssertionError(f"Unexpected Follow Up Boss request: {method} {path}")


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
@pytest.mark.parametrize(
    ("tool_name", "arguments", "expected_message", "expected_calls"),
    [
        (
            "followupboss_search_people_in_smart_list",
            {"smart_list_name": "Missing confidential smart list"},
            "Missing confidential smart list",
            [("GET", "/smartLists")],
        ),
        (
            "followupboss_list_uncontacted_leads",
            {"next_token": "scan:1:not-a-number"},
            "Uncontacted lead pagination token is invalid",
            [],
        ),
        (
            "followupboss_list_uncontacted_leads",
            {"next_token": "scan:²:1"},
            "Uncontacted lead pagination token is invalid",
            [],
        ),
        (
            "followupboss_create_pipeline",
            {"name": "Malformed pipeline", "stages": [{"id": "not-an-int"}]},
            "stages.0.id",
            [],
        ),
        (
            "followupboss_update_pipeline",
            {"pipeline_id": 9, "stages": [{"id": "not-an-int"}]},
            "stages.0.id",
            [],
        ),
        (
            "followupboss_create_call",
            {
                "person_id": 99,
                "phone": "555-2222",
                "is_incoming": False,
                "user_id": 999,
            },
            "Call logs must be attributed to the authenticated Follow Up Boss user.",
            [("GET", "/identity")],
        ),
        (
            "followupboss_update_call",
            {"call_id": 12, "user_id": 999},
            "Call logs must remain attributed to the authenticated Follow Up Boss user.",
            [("GET", "/identity")],
        ),
    ],
)
async def test_sentry_mcp_integration_keeps_expected_caller_errors_event_free_over_the_protocol(
    monkeypatch: pytest.MonkeyPatch,
    tool_name: str,
    arguments: dict[str, object],
    expected_message: str,
    expected_calls: list[tuple[str, str]],
) -> None:
    """Expected MCP caller errors stay actionable, event-free, and privacy-safe."""
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
    sentry_settings = SentrySettings.model_validate(
        {
            "dsn": "https://public@example.invalid/1",
            "traces_sample_rate": 1.0,
        }
    )

    try:
        assert configure_sentry(sentry_settings, entrypoint="sentry-mcp-integration-test") is True
        assert sentry_sdk.get_client().get_integration(MCPIntegration) is not None

        client = OfflineExpectedErrorClient()
        server = create_server(
            FollowUpBossSettings.model_validate({"api_key": "offline-test-key"}),
            client=client,
            sentry_settings=sentry_settings,
        )

        async with MCPInMemoryTransport(server) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.call_tool(
                    tool_name,
                    arguments,
                )

        assert result.is_error is True
        assert len(result.content) == 1
        content = result.content[0]
        assert content.type == "text"
        assert expected_message in content.text
        assert client.calls == expected_calls

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
