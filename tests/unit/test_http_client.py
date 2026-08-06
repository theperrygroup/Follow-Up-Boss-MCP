"""Tests for the async HTTP client."""

from __future__ import annotations

import io
import logging

import httpx
import pytest
import respx

from followupboss_mcp.auth import AuthMode
from followupboss_mcp.config import FollowUpBossSettings
from followupboss_mcp.errors import (
    FollowUpBossAuthError,
    FollowUpBossError,
    FollowUpBossForbiddenError,
    FollowUpBossHTTPError,
    FollowUpBossNotFoundError,
    FollowUpBossRateLimitError,
    FollowUpBossRetryableServerError,
    FollowUpBossValidationError,
)
from followupboss_mcp.http_client import FollowUpBossAsyncClient


async def _record_sleep(calls: list[float], delay: float) -> None:
    calls.append(delay)


def _settings(**overrides: object) -> FollowUpBossSettings:
    data: dict[str, object] = {
        "api_key": "api-key",
        "auth_mode": AuthMode.API_KEY,
        "system_name": "Example System",
        "system_key": "system-key",
        "max_retries": 1,
    }
    data.update(overrides)
    return FollowUpBossSettings.model_validate(data)


@pytest.mark.asyncio
async def test_request_json_success_and_headers() -> None:
    """Successful requests should include auth and registered system headers."""
    sleep_calls: list[float] = []
    settings = _settings()
    with respx.mock(assert_all_called=True) as router:
        route = router.get("https://api.followupboss.com/v1/identity").mock(
            return_value=httpx.Response(200, json={"id": 1, "name": "Jean-Luc Picard"})
        )
        async with FollowUpBossAsyncClient(
            settings,
            jitter_source=lambda: 0.0,
            sleep=lambda delay: _record_sleep(sleep_calls, delay),
        ) as client:
            payload = await client.request_json(
                "GET",
                "/identity",
                headers={"X-Request-Id": "request-123"},
            )
            assert payload == {"id": 1, "name": "Jean-Luc Picard"}
            assert "FollowUpBossAsyncClient" in repr(client)
            assert client._client.follow_redirects is False
        request = route.calls.last.request
    assert request.headers["Authorization"].startswith("Basic ")
    assert request.headers["X-System"] == "Example System"
    assert request.headers["X-System-Key"] == "system-key"
    assert request.headers["X-Request-Id"] == "request-123"
    assert sleep_calls == []


@pytest.mark.asyncio
async def test_request_json_logs_status_and_elapsed_time() -> None:
    """Successful requests should log status and elapsed time."""
    settings = _settings(max_retries=0)
    stream = io.StringIO()
    logger = logging.getLogger("followupboss_mcp_test_http")
    logger.handlers.clear()
    logger.setLevel("INFO")
    logger.propagate = False
    logger.addHandler(logging.StreamHandler(stream))
    clock_values = iter([1.0, 1.25])

    with respx.mock(assert_all_called=True) as router:
        router.get("https://api.followupboss.com/v1/appointments/424242").mock(
            return_value=httpx.Response(200, json={"id": 1})
        )
        async with FollowUpBossAsyncClient(
            settings,
            logger=logger,
            clock=lambda: next(clock_values),
        ) as client:
            assert await client.request_json("GET", "/appointments/424242") == {"id": 1}

    log_output = stream.getvalue()
    assert "Follow Up Boss response method=GET status=200 elapsed_ms=250 attempts=1" in log_output
    assert "424242" not in log_output


@pytest.mark.asyncio
async def test_request_json_debug_logs_request_shape_without_values() -> None:
    """Debug logs should capture request shape without dumping parameter or JSON values."""
    settings = _settings(max_retries=0)
    stream = io.StringIO()
    logger = logging.getLogger("followupboss_mcp_test_http_debug")
    logger.handlers.clear()
    logger.setLevel("DEBUG")
    logger.propagate = False
    logger.addHandler(logging.StreamHandler(stream))

    with respx.mock(assert_all_called=True) as router:
        router.post("https://api.followupboss.com/v1/appointments/424242").mock(
            return_value=httpx.Response(200, json={"id": 1})
        )
        async with FollowUpBossAsyncClient(settings, logger=logger) as client:
            assert await client.request_json(
                "POST",
                "/appointments/424242",
                headers={"X-Request-Id": "request-123"},
                json_body={"firstName": "Tom"},
                params={"source": "Portal"},
            ) == {"id": 1}

    log_output = stream.getvalue()
    assert "Sending Follow Up Boss request method=POST attempt=1" in log_output
    assert "params_keys=['source']" in log_output
    assert "json_keys=['firstName']" in log_output
    assert "Authorization': '***redacted***" in log_output
    assert "X-System-Key': '***redacted***" in log_output
    assert "Portal" not in log_output
    assert "Tom" not in log_output
    assert "424242" not in log_output


@pytest.mark.asyncio
async def test_request_json_supports_bearer_auth_and_204() -> None:
    """OAuth mode should use bearer auth and allow empty 204 responses."""
    settings = _settings(
        auth_mode=AuthMode.OAUTH,
        api_key=None,
        access_token="access-token",
        system_key=None,
        system_name=None,
    )
    with respx.mock(assert_all_called=True) as router:
        route = router.delete("https://api.followupboss.com/v1/notes/1").mock(
            return_value=httpx.Response(204, content=b"")
        )
        async with FollowUpBossAsyncClient(settings) as client:
            payload = await client.request_json("DELETE", "/notes/1")
    assert payload == {}
    assert route.calls.last.request.headers["Authorization"] == "Bearer access-token"
    assert "X-System" not in route.calls.last.request.headers


@pytest.mark.asyncio
async def test_request_json_non_json_and_generic_http_errors() -> None:
    """Unexpected response bodies and unmapped statuses should raise safe errors."""
    settings = _settings(max_retries=0)
    with respx.mock(assert_all_called=True) as router:
        router.get("https://api.followupboss.com/v1/plain").mock(
            return_value=httpx.Response(200, text="not json"),
        )
        router.get("https://api.followupboss.com/v1/teapot").mock(
            return_value=httpx.Response(418, json=["oops"]),
        )
        async with FollowUpBossAsyncClient(settings) as client:
            with pytest.raises(FollowUpBossHTTPError):
                await client.request_json("GET", "/plain")
            with pytest.raises(FollowUpBossHTTPError, match="HTTP 418"):
                await client.request_json("GET", "/teapot")


@pytest.mark.asyncio
async def test_request_json_rejects_protected_header_overrides() -> None:
    """Caller headers should not override protected transport headers."""
    async with FollowUpBossAsyncClient(_settings(max_retries=0)) as client:
        with pytest.raises(ValueError, match="Authorization"):
            await client.request_json("GET", "/identity", headers={"Authorization": "Bearer bad"})
        with pytest.raises(ValueError, match="X-System-Key"):
            await client.request_json("GET", "/identity", headers={"X-System-Key": "bad"})
        with pytest.raises(ValueError, match="Content-Type"):
            await client.request_json(
                "POST",
                "/people",
                headers={"Content-Type": "text/plain"},
                json_body={"firstName": "Tom"},
            )


@pytest.mark.asyncio
async def test_request_json_status_mapping() -> None:
    """4xx responses should map into the documented error hierarchy."""
    settings = _settings(max_retries=0)
    with respx.mock(assert_all_called=True) as router:
        router.get("https://api.followupboss.com/v1/bad").mock(
            return_value=httpx.Response(400, json={"errorMessage": "bad request"}),
        )
        router.get("https://api.followupboss.com/v1/auth").mock(
            return_value=httpx.Response(401, json={"errorMessage": "unauthorized"}),
        )
        router.get("https://api.followupboss.com/v1/forbidden").mock(
            return_value=httpx.Response(403, json={"errorMessage": "forbidden"}),
        )
        router.get("https://api.followupboss.com/v1/missing").mock(
            return_value=httpx.Response(404, json={"errorMessage": "missing"}),
        )
        async with FollowUpBossAsyncClient(settings) as client:
            with pytest.raises(FollowUpBossValidationError, match="bad request"):
                await client.request_json("GET", "/bad")
            with pytest.raises(FollowUpBossAuthError, match="unauthorized"):
                await client.request_json("GET", "/auth")
            with pytest.raises(FollowUpBossForbiddenError, match="forbidden"):
                await client.request_json("GET", "/forbidden")
            with pytest.raises(FollowUpBossNotFoundError, match="missing"):
                await client.request_json("GET", "/missing")


@pytest.mark.asyncio
async def test_request_json_rate_limit_retry_and_exhaustion() -> None:
    """429 responses should respect Retry-After and surface exhaustion details."""
    sleep_calls: list[float] = []
    stream = io.StringIO()
    logger = logging.getLogger("followupboss_mcp_test_http_rate_limit")
    logger.handlers.clear()
    logger.setLevel("INFO")
    logger.propagate = False
    logger.addHandler(logging.StreamHandler(stream))
    with respx.mock(assert_all_called=True) as router:
        router.get("https://api.followupboss.com/v1/appointments/424242").mock(
            side_effect=[
                httpx.Response(
                    429, headers={"Retry-After": "3"}, json={"errorMessage": "slow down"}
                ),
                httpx.Response(200, json={"id": 1}),
            ]
        )
        async with FollowUpBossAsyncClient(
            _settings(max_retries=1),
            jitter_source=lambda: 0.0,
            logger=logger,
            sleep=lambda delay: _record_sleep(sleep_calls, delay),
        ) as client:
            assert await client.request_json("GET", "/appointments/424242") == {"id": 1}
    assert sleep_calls == [3.0]
    log_output = stream.getvalue()
    assert "reason=rate_limit status=429 retry_after_s=3.0 error_type=None" in log_output
    assert "Follow Up Boss response method=GET status=200" in log_output
    assert "attempts=2" in log_output
    assert "424242" not in log_output

    with respx.mock(assert_all_called=True) as router:
        router.get("https://api.followupboss.com/v1/identity").mock(
            return_value=httpx.Response(
                429, headers={"Retry-After": "2"}, json={"errorMessage": "slow down"}
            ),
        )
        async with FollowUpBossAsyncClient(_settings(max_retries=0)) as client:
            with pytest.raises(FollowUpBossRateLimitError) as exc_info:
                await client.request_json("GET", "/identity")
    assert exc_info.value.retry_after_seconds == 2.0


@pytest.mark.asyncio
async def test_request_json_server_retry_and_transport_errors() -> None:
    """Retryable 5xx and transport errors should retry before failing."""
    sleep_calls: list[float] = []
    retry_stream = io.StringIO()
    retry_logger = logging.getLogger("followupboss_mcp_test_http_retryable_status")
    retry_logger.handlers.clear()
    retry_logger.setLevel("INFO")
    retry_logger.propagate = False
    retry_logger.addHandler(logging.StreamHandler(retry_stream))
    with respx.mock(assert_all_called=True) as router:
        router.get("https://api.followupboss.com/v1/identity").mock(
            side_effect=[
                httpx.Response(500, json={"errorMessage": "boom"}),
                httpx.Response(200, json={"id": 1}),
            ]
        )
        async with FollowUpBossAsyncClient(
            _settings(max_retries=1),
            jitter_source=lambda: 0.0,
            logger=retry_logger,
            sleep=lambda delay: _record_sleep(sleep_calls, delay),
        ) as client:
            assert await client.request_json("GET", "/identity") == {"id": 1}
    assert sleep_calls == [1.0]
    retry_log_output = retry_stream.getvalue()
    assert "reason=retryable_status status=500" in retry_log_output
    assert "attempts=2" in retry_log_output

    with respx.mock(assert_all_called=True) as router:
        router.get("https://api.followupboss.com/v1/identity").mock(
            return_value=httpx.Response(500, json={"errorMessage": "boom"}),
        )
        async with FollowUpBossAsyncClient(_settings(max_retries=0)) as client:
            with pytest.raises(FollowUpBossRetryableServerError, match="boom"):
                await client.request_json("GET", "/identity")

    transport_stream = io.StringIO()
    transport_logger = logging.getLogger("followupboss_mcp_test_http_transport_retry")
    transport_logger.handlers.clear()
    transport_logger.setLevel("INFO")
    transport_logger.propagate = False
    transport_logger.addHandler(logging.StreamHandler(transport_stream))
    with respx.mock(assert_all_called=True) as router:
        router.get("https://api.followupboss.com/v1/identity").mock(
            side_effect=[httpx.ConnectError("down"), httpx.Response(200, json={"id": 1})]
        )
        async with FollowUpBossAsyncClient(
            _settings(max_retries=1),
            jitter_source=lambda: 0.0,
            logger=transport_logger,
            sleep=lambda delay: _record_sleep([], delay),
        ) as client:
            assert await client.request_json("GET", "/identity") == {"id": 1}
    transport_log_output = transport_stream.getvalue()
    assert "reason=transport_error status=None retry_after_s=None error_type=ConnectError" in (
        transport_log_output
    )
    assert "attempts=2" in transport_log_output

    with respx.mock(assert_all_called=True) as router:
        router.get("https://api.followupboss.com/v1/identity").mock(
            side_effect=httpx.ConnectError("down")
        )
        async with FollowUpBossAsyncClient(_settings(max_retries=0)) as client:
            with pytest.raises(FollowUpBossError, match="Transport error"):
                await client.request_json("GET", "/identity")


@pytest.mark.asyncio
async def test_aclose_respects_owned_and_external_clients() -> None:
    """Only owned clients should be closed through aclose."""
    external = httpx.AsyncClient()
    client = FollowUpBossAsyncClient(_settings(), http_client=external)
    await client.aclose()
    assert external.is_closed is False
    await external.aclose()
