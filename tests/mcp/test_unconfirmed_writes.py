"""Server and transport errors on writes Follow Up Boss may have saved reach callers once."""

from __future__ import annotations

import json
from collections.abc import Callable

import httpx
import pytest

from followupboss_mcp import mcp_tools
from followupboss_mcp.config import FollowUpBossSettings
from followupboss_mcp.errors import (
    FollowUpBossRetryableServerError,
    FollowUpBossUnconfirmedTransportError,
    FollowUpBossUnconfirmedWriteError,
)
from followupboss_mcp.http_client import FollowUpBossAsyncClient
from followupboss_mcp.mcp_server import create_server
from followupboss_mcp.observability import SentryExtra, SentryTags
from mcp.server.mcpserver.exceptions import ToolError, UnexpectedToolError

type Upstream = Callable[[httpx.Request], httpx.Response]
type CapturedEvents = list[tuple[BaseException, SentryTags | None]]

_SAVED_GUIDANCE = (
    "Follow Up Boss may have saved this request before the error, so it was not sent again. "
    "If it creates or changes a record, look that record up before trying again."
)


async def _no_sleep(delay: float) -> None:
    """Skip retry backoff so the tests stay fast and deterministic."""
    del delay


async def _call_tool(tool_name: str, arguments: dict[str, object], upstream: Upstream) -> None:
    """Call one registered tool through the real adapter, service, and HTTP client.

    Args:
        tool_name: The registered MCP tool name.
        arguments: Tool arguments sent by the MCP caller.
        upstream: Fake Follow Up Boss HTTP handler.
    """
    settings = FollowUpBossSettings.model_validate({"api_key": "test-key", "max_retries": 3})
    async with httpx.AsyncClient(
        base_url=str(settings.base_url), transport=httpx.MockTransport(upstream)
    ) as http_client:
        client = FollowUpBossAsyncClient(settings, http_client=http_client, sleep=_no_sleep)
        server = create_server(settings, client=client)
        await server.call_tool(tool_name, arguments)


def _server_error_upstream(requests: list[httpx.Request], status_code: int) -> Upstream:
    """Return a fake upstream that answers every request with one server error.

    Args:
        requests: List that records every upstream request.
        status_code: The HTTP 5xx status Follow Up Boss returns.

    Returns:
        The fake upstream handler.
    """

    def upstream(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(status_code, json={"errorMessage": "Internal Server Error"})

    return upstream


def _lost_response_upstream(
    requests: list[httpx.Request],
    error_type: type[httpx.TransportError],
) -> Upstream:
    """Return a fake upstream that receives every request but loses each response.

    Args:
        requests: List that records every upstream request.
        error_type: The httpx transport error raised after the request arrives.

    Returns:
        The fake upstream handler.
    """

    def upstream(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        raise error_type("lost", request=request)

    return upstream


def _record_sentry_captures(
    monkeypatch: pytest.MonkeyPatch,
) -> CapturedEvents:
    """Replace the Sentry capture helper with a recorder.

    Args:
        monkeypatch: Pytest fixture used to patch the helper.

    Returns:
        The list that receives each captured exception and its tags.
    """
    captured: CapturedEvents = []

    def capture(
        exc: BaseException,
        *,
        tags: SentryTags | None = None,
        extras: SentryExtra | None = None,
    ) -> str | None:
        del extras
        captured.append((exc, tags))
        return None

    monkeypatch.setattr(mcp_tools, "capture_sentry_exception", capture)
    return captured


def _cause_chain(exc: BaseException) -> list[BaseException]:
    """Return an exception followed by every exception it was raised from.

    Args:
        exc: The outermost exception.

    Returns:
        The exception chain, outermost first.
    """
    chain: list[BaseException] = []
    current: BaseException | None = exc
    while current is not None:
        chain.append(current)
        current = current.__cause__
    return chain


@pytest.mark.asyncio
@pytest.mark.parametrize("status_code", [500, 504])
async def test_create_pipeline_server_error_is_sent_once_with_lookup_guidance(
    monkeypatch: pytest.MonkeyPatch,
    status_code: int,
) -> None:
    """A create that gets a 5xx is sent once, tells the caller to check, and stays in Sentry."""
    requests: list[httpx.Request] = []
    captured = _record_sentry_captures(monkeypatch)

    with pytest.raises(ToolError) as exc_info:
        await _call_tool(
            "followupboss_create_pipeline",
            {"name": "Buyers", "stages": [{"name": "Lead", "closed_stage": False}]},
            _server_error_upstream(requests, status_code),
        )

    assert not isinstance(exc_info.value, UnexpectedToolError)
    assert str(exc_info.value).endswith(f": Internal Server Error. {_SAVED_GUIDANCE}")
    assert any(
        isinstance(cause, FollowUpBossUnconfirmedWriteError)
        for cause in _cause_chain(exc_info.value)
    )
    assert [(request.method, request.url.path) for request in requests] == [
        ("POST", "/v1/pipelines")
    ]
    assert json.loads(requests[0].content) == {
        "name": "Buyers",
        "stages": [{"closedStage": False, "name": "Lead"}],
    }
    assert len(captured) == 1
    captured_error, captured_tags = captured[0]
    assert isinstance(captured_error, FollowUpBossUnconfirmedWriteError)
    assert captured_error.status_code == status_code
    assert captured_tags == {"component": "mcp_tools", "followupboss_status_code": status_code}


@pytest.mark.asyncio
async def test_update_pipeline_server_error_keeps_retries_and_stays_unexpected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A PUT keeps its 5xx retries, and running out of them is still an unexpected error."""
    requests: list[httpx.Request] = []
    captured = _record_sentry_captures(monkeypatch)

    with pytest.raises(UnexpectedToolError) as exc_info:
        await _call_tool(
            "followupboss_update_pipeline",
            {"pipeline_id": 63, "name": "Sellers"},
            _server_error_upstream(requests, 503),
        )

    assert any(
        isinstance(cause, FollowUpBossRetryableServerError)
        for cause in _cause_chain(exc_info.value)
    )
    assert [(request.method, request.url.path) for request in requests] == [
        ("PUT", "/v1/pipelines/63")
    ] * 4
    assert captured == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error_type", [httpx.ReadTimeout, httpx.ReadError, httpx.RemoteProtocolError]
)
async def test_create_pipeline_lost_response_is_sent_once_with_lookup_guidance(
    monkeypatch: pytest.MonkeyPatch,
    error_type: type[httpx.TransportError],
) -> None:
    """A create that loses its response is sent once, gets the guidance, and stays in Sentry."""
    requests: list[httpx.Request] = []
    captured = _record_sentry_captures(monkeypatch)

    with pytest.raises(ToolError) as exc_info:
        await _call_tool(
            "followupboss_create_pipeline",
            {"name": "Buyers", "stages": [{"name": "Lead", "closed_stage": False}]},
            _lost_response_upstream(requests, error_type),
        )

    assert not isinstance(exc_info.value, UnexpectedToolError)
    assert str(exc_info.value).endswith(
        f": Transport error while calling Follow Up Boss. {_SAVED_GUIDANCE}"
    )
    assert any(
        isinstance(cause, FollowUpBossUnconfirmedTransportError)
        for cause in _cause_chain(exc_info.value)
    )
    assert [(request.method, request.url.path) for request in requests] == [
        ("POST", "/v1/pipelines")
    ]
    assert len(captured) == 1
    captured_error, captured_tags = captured[0]
    assert isinstance(captured_error, FollowUpBossUnconfirmedTransportError)
    assert isinstance(captured_error.__cause__, error_type)
    assert captured_tags == {"component": "mcp_tools", "followupboss_status_code": None}


@pytest.mark.asyncio
async def test_update_pipeline_that_adds_a_stage_server_error_is_sent_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A pipeline update that adds a stage is not resent after a 5xx, since it may exist now."""
    requests: list[httpx.Request] = []
    captured = _record_sentry_captures(monkeypatch)

    with pytest.raises(ToolError) as exc_info:
        await _call_tool(
            "followupboss_update_pipeline",
            {"pipeline_id": 63, "stages": [{"id": 5, "name": "Lead"}, {"name": "Showing"}]},
            _server_error_upstream(requests, 503),
        )

    assert not isinstance(exc_info.value, UnexpectedToolError)
    assert str(exc_info.value).endswith(f": Internal Server Error. {_SAVED_GUIDANCE}")
    assert [(request.method, request.url.path) for request in requests] == [
        ("PUT", "/v1/pipelines/63")
    ]
    assert json.loads(requests[0].content) == {
        "stages": [{"id": 5, "name": "Lead"}, {"name": "Showing"}]
    }
    assert len(captured) == 1
    assert captured[0][1] == {"component": "mcp_tools", "followupboss_status_code": 503}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error_type", [httpx.ReadTimeout, httpx.ReadError, httpx.RemoteProtocolError]
)
async def test_update_pipeline_that_adds_a_stage_lost_response_is_sent_once(
    monkeypatch: pytest.MonkeyPatch,
    error_type: type[httpx.TransportError],
) -> None:
    """A pipeline update that adds a stage is not resent after it loses its response."""
    requests: list[httpx.Request] = []
    captured = _record_sentry_captures(monkeypatch)

    with pytest.raises(ToolError) as exc_info:
        await _call_tool(
            "followupboss_update_pipeline",
            {"pipeline_id": 63, "stages": [{"name": "Showing"}]},
            _lost_response_upstream(requests, error_type),
        )

    assert not isinstance(exc_info.value, UnexpectedToolError)
    assert str(exc_info.value).endswith(
        f": Transport error while calling Follow Up Boss. {_SAVED_GUIDANCE}"
    )
    assert [(request.method, request.url.path) for request in requests] == [
        ("PUT", "/v1/pipelines/63")
    ]
    assert len(captured) == 1


@pytest.mark.asyncio
async def test_update_pipeline_with_existing_stage_ids_keeps_retries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A pipeline update whose stages all have ids creates nothing, so it keeps its retries."""
    requests: list[httpx.Request] = []
    captured = _record_sentry_captures(monkeypatch)

    with pytest.raises(UnexpectedToolError):
        await _call_tool(
            "followupboss_update_pipeline",
            {"pipeline_id": 63, "stages": [{"id": 5, "name": "Lead"}]},
            _server_error_upstream(requests, 503),
        )

    assert [(request.method, request.url.path) for request in requests] == [
        ("PUT", "/v1/pipelines/63")
    ] * 4
    assert captured == []
