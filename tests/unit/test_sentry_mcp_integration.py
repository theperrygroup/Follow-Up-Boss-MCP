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
from followupboss_mcp.errors import FollowUpBossValidationError
from followupboss_mcp.mcp_server import create_server
from followupboss_mcp.observability import configure_sentry
from mcp.client._memory import InMemoryTransport as MCPInMemoryTransport
from mcp.client.session import ClientSession

_REDACTED = "***redacted***"
_DEEP_PAGINATION_MESSAGE = "Deep pagination disabled, use 'nextLink' url"
_FOLLOWUPBOSS_DOCS_LINK = "https://docs.followupboss.com/pagination-guide"


class OfflineExpectedErrorClient:
    """Serve only the read endpoints needed by expected-error protocol calls."""

    def __init__(
        self,
        deep_page_message: str = f"{_DEEP_PAGINATION_MESSAGE} {_FOLLOWUPBOSS_DOCS_LINK}",
    ) -> None:
        """Capture every request so error paths prove their side-effect boundary.

        Args:
            deep_page_message: The Follow Up Boss HTTP 400 message for a people
                search that sends an offset.
        """
        self.calls: list[tuple[str, str]] = []
        self.deep_page_message = deep_page_message

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
        """Return identity or empty-smart-list data, or a known Follow Up Boss 400."""
        del headers, json_body
        self.calls.append((method, path))
        if path == "/smartLists":
            return {
                "_metadata": {"limit": 100, "offset": 0, "total": 0},
                "smartlists": [],
            }
        if path == "/identity":
            return {"id": 1}
        if path == "/calls":
            raise FollowUpBossValidationError(
                "Deep pagination disabled, use 'nextLink' url", status_code=400
            )
        if path == "/people" and params is not None and "offset" in params:
            raise FollowUpBossValidationError(self.deep_page_message, status_code=400)
        if path == "/people":
            raise FollowUpBossValidationError(
                "Invalid value for 'smartListId' parameter, no such list.", status_code=400
            )
        if path == "/pipelines/9":
            raise FollowUpBossValidationError(
                "You cannot delete a closed stage from a pipeline", status_code=400
            )
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


@pytest.mark.parametrize("breadcrumb_count", [1, 11])
def test_sentry_error_envelope_preserves_breadcrumb_data_object(
    monkeypatch: pytest.MonkeyPatch,
    breadcrumb_count: int,
) -> None:
    """The actual SDK envelope keeps redacted breadcrumbs schema-valid."""
    captured_envelopes: list[Envelope] = []
    original_init = cast(Callable[..., object], sentry_sdk.init)

    class InMemorySentryTransport(Transport):
        """Capture scrubbed events without sending any telemetry."""

        def capture_envelope(self, envelope: Envelope) -> None:
            """Keep the event at its real transport boundary."""
            captured_envelopes.append(envelope)

    def init_with_in_memory_transport(*args: object, **kwargs: Any) -> object:
        """Use production initialization but force a local transport."""
        kwargs["transport"] = InMemorySentryTransport
        return original_init(*args, **kwargs)

    monkeypatch.setattr(observability, "_SENTRY_INITIALIZED", False)
    monkeypatch.setattr(sentry_sdk, "init", init_with_in_memory_transport)
    try:
        assert configure_sentry(
            SentrySettings.model_validate({"dsn": "https://public@example.invalid/1"}),
            entrypoint="sentry-breadcrumb-schema-test",
        )
        with sentry_sdk.isolation_scope():
            for attempt in range(breadcrumb_count):
                sentry_sdk.add_breadcrumb(
                    category="followupboss.http.retry",
                    message="Retrying Follow Up Boss request",
                    data={"attempt": attempt, "private_value": "PRIVATE_CUSTOMER_PAYLOAD"},
                )
            sentry_sdk.capture_exception(RuntimeError("Transport error after retries"))
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
        breadcrumbs = event["breadcrumbs"]["values"]
        retry_breadcrumbs = [
            item for item in breadcrumbs if item["category"] == "followupboss.http.retry"
        ]
        assert len(retry_breadcrumbs) == breadcrumb_count
        assert all(item["data"] == {} for item in retry_breadcrumbs)
        assert "PRIVATE_CUSTOMER_PAYLOAD" not in str(event)
    finally:
        sentry_sdk.get_client().close()
        original_init(dsn=None)


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
            "followupboss_list_uncontacted_leads",
            {"next_token": "9" * 5000},
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
            "followupboss_update_pipeline",
            {"pipeline_id": 9, "stages": [{"id": 401, "name": "Lead", "closed_stage": False}]},
            "call followupboss_get_pipeline and keep every closed stage in stages",
            [("PUT", "/pipelines/9")],
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
        (
            "followupboss_list_calls",
            {"offset": 5000},
            "Narrow the request with filters",
            [("GET", "/calls")],
        ),
        (
            "followupboss_search_people",
            {"smart_list_id": 987654},
            "Call followupboss_list_smart_lists to get a current smart list id.",
            [("GET", "/identity"), ("GET", "/people")],
        ),
        (
            "followupboss_search_people",
            {"offset": 5000},
            f"instead of paging deeper. Follow Up Boss docs: {_FOLLOWUPBOSS_DOCS_LINK}",
            [("GET", "/identity"), ("GET", "/people")],
        ),
        (
            "followupboss_list_custom_fields",
            {"fields": ["id", "choices"]},
            "followupboss_get_custom_field",
            [],
        ),
        (
            "followupboss_update_person",
            {"person_id": 101},
            "followupboss_update_person needs at least one field to change.",
            [],
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


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "deep_page_message",
    [
        f"{_DEEP_PAGINATION_MESSAGE} https://example.com/pagination-guide",
        f"{_DEEP_PAGINATION_MESSAGE} http://docs.followupboss.com/pagination-guide",
        f"{_DEEP_PAGINATION_MESSAGE} {_FOLLOWUPBOSS_DOCS_LINK} for more detail",
        f"{_DEEP_PAGINATION_MESSAGE}{_FOLLOWUPBOSS_DOCS_LINK}",
    ],
)
async def test_sentry_mcp_integration_still_captures_unknown_deep_pagination_variants(
    monkeypatch: pytest.MonkeyPatch,
    deep_page_message: str,
) -> None:
    """A deep pagination 400 with any other trailing text still sends an error event."""
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

        client = OfflineExpectedErrorClient(deep_page_message)
        server = create_server(
            FollowUpBossSettings.model_validate({"api_key": "offline-test-key"}),
            client=client,
            sentry_settings=sentry_settings,
        )

        async with MCPInMemoryTransport(server) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.call_tool("followupboss_search_people", {"offset": 5000})

        assert result.is_error is True
        assert len(result.content) == 1
        content = result.content[0]
        assert content.type == "text"
        assert "Narrow the request with filters" not in content.text
        assert client.calls == [("GET", "/identity"), ("GET", "/people")]

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
        exception_types = {value["type"] for value in event["exception"]["values"]}
        assert {"FollowUpBossValidationError", "RuntimeError"} <= exception_types
    finally:
        sentry_sdk.get_client().close()
        original_init(dsn=None)
