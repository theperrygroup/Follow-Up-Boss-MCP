"""Async HTTP client for the Follow Up Boss API."""

from __future__ import annotations

import asyncio
import logging
import random
import time
from collections.abc import Awaitable, Callable, Mapping
from typing import Any, Protocol, cast

import httpx

from followupboss_mcp.auth import AuthStrategy, inject_authorization
from followupboss_mcp.config import FollowUpBossSettings
from followupboss_mcp.constants import (
    DEFAULT_USER_AGENT,
    HEADER_ACCEPT,
    HEADER_AUTHORIZATION,
    HEADER_CONTENT_TYPE,
    HEADER_SYSTEM,
    HEADER_SYSTEM_KEY,
    JSON_CONTENT_TYPE,
    RATE_LIMIT_STATUS_CODE,
)
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
from followupboss_mcp.logging import configure_logging, redact_headers
from followupboss_mcp.rate_limits import parse_retry_after
from followupboss_mcp.retry import RetryPolicy

JsonPayload = dict[str, object] | list[object]
_PROTECTED_REQUEST_HEADERS = frozenset(
    {
        HEADER_AUTHORIZATION.lower(),
        HEADER_CONTENT_TYPE.lower(),
        HEADER_SYSTEM.lower(),
        HEADER_SYSTEM_KEY.lower(),
    }
)


class FollowUpBossClientProtocol(Protocol):
    """Protocol shared by the HTTP client and deterministic test doubles."""

    async def aclose(self) -> None:
        """Close any underlying resources."""

    async def request_json(
        self,
        method: str,
        path: str,
        *,
        headers: Mapping[str, str] | None = None,
        json_body: Mapping[str, object] | None = None,
        params: Mapping[str, str] | None = None,
    ) -> JsonPayload:
        """Send a request and return a decoded JSON payload."""


class FollowUpBossAsyncClient:
    """Centralized async Follow Up Boss HTTP client."""

    def __init__(
        self,
        settings: FollowUpBossSettings | None = None,
        *,
        auth_strategy: AuthStrategy | None = None,
        http_client: httpx.AsyncClient | None = None,
        jitter_source: Callable[[], float] | None = None,
        logger: logging.Logger | None = None,
        clock: Callable[[], float] | None = None,
        sleep: Callable[[float], Awaitable[None]] | None = None,
    ) -> None:
        """Initialize the client."""
        self.settings = settings or FollowUpBossSettings()
        self._auth_strategy = auth_strategy or self.settings.auth_strategy()
        self._logger = logger or configure_logging(self.settings.log_level)
        self._retry_policy = RetryPolicy(max_retries=self.settings.max_retries)
        self._clock = clock or time.perf_counter
        self._jitter_source = jitter_source or random.random
        self._sleep = sleep or asyncio.sleep
        self._owns_client = http_client is None
        self._client = http_client or httpx.AsyncClient(
            base_url=str(self.settings.base_url),
            follow_redirects=False,
            headers={
                HEADER_ACCEPT: JSON_CONTENT_TYPE,
                "User-Agent": DEFAULT_USER_AGENT,
            },
            timeout=self.settings.timeout_seconds,
        )

    async def __aenter__(self) -> FollowUpBossAsyncClient:
        """Enter the async context manager."""
        return self

    async def __aexit__(self, *_: object) -> None:
        """Exit the async context manager."""
        await self.aclose()

    def __repr__(self) -> str:
        """Return a safe representation."""
        return f"FollowUpBossAsyncClient(base_url={self.settings.base_url!s}, auth=***redacted***)"

    async def aclose(self) -> None:
        """Close the underlying httpx client if owned."""
        if self._owns_client:
            await self._client.aclose()

    async def request_json(
        self,
        method: str,
        path: str,
        *,
        headers: Mapping[str, str] | None = None,
        json_body: Mapping[str, object] | None = None,
        params: Mapping[str, str] | None = None,
    ) -> JsonPayload:
        """Send a request and return the decoded JSON payload."""
        response = await self._send_with_retries(
            method,
            path,
            headers=headers,
            json_body=json_body,
            params=params,
        )
        if response.status_code == 204 or not response.content:
            return {}

        try:
            payload = cast(JsonPayload, response.json())
        except ValueError as exc:
            raise FollowUpBossHTTPError(
                "Follow Up Boss returned a non-JSON response.",
                status_code=response.status_code,
            ) from exc
        return payload

    async def _send_with_retries(
        self,
        method: str,
        path: str,
        *,
        headers: Mapping[str, str] | None,
        json_body: Mapping[str, object] | None,
        params: Mapping[str, str] | None,
    ) -> httpx.Response:
        """Send a request with rate-limit and retry handling."""
        attempt = 0
        while True:
            request_headers = self._build_headers(
                headers=headers, has_json_body=json_body is not None
            )
            request_started_at = self._clock()
            self._logger.debug(
                "Sending Follow Up Boss request %s %s headers=%s params=%s",
                method.upper(),
                path,
                redact_headers(request_headers),
                params,
            )
            try:
                response = await self._client.request(
                    method=method.upper(),
                    url=path,
                    headers=request_headers,
                    json=json_body,
                    params=params,
                )
            except httpx.HTTPError as exc:
                if self._retry_policy.can_retry(attempt):
                    delay = self._retry_policy.backoff_seconds(
                        attempt=attempt,
                        jitter_source=self._jitter_source,
                    )
                    attempt += 1
                    await self._sleep(delay)
                    continue
                raise FollowUpBossError("Transport error while calling Follow Up Boss.") from exc
            elapsed_ms = int((self._clock() - request_started_at) * 1000)
            self._logger.info(
                "Follow Up Boss response %s %s status=%s elapsed_ms=%s",
                method.upper(),
                path,
                response.status_code,
                elapsed_ms,
            )

            if response.status_code == RATE_LIMIT_STATUS_CODE:
                retry_after = parse_retry_after(response.headers.get("Retry-After"))
                if self._retry_policy.can_retry(attempt):
                    delay = self._retry_policy.backoff_seconds(
                        attempt=attempt,
                        jitter_source=self._jitter_source,
                        retry_after_seconds=retry_after,
                    )
                    attempt += 1
                    await self._sleep(delay)
                    continue
                payload = self._error_payload(response)
                raise FollowUpBossRateLimitError(
                    self._error_message(response, payload),
                    status_code=response.status_code,
                    retry_after_seconds=retry_after,
                    payload=payload,
                )

            if self._retry_policy.is_retryable_status(response.status_code):
                if self._retry_policy.can_retry(attempt):
                    delay = self._retry_policy.backoff_seconds(
                        attempt=attempt,
                        jitter_source=self._jitter_source,
                    )
                    attempt += 1
                    await self._sleep(delay)
                    continue
                payload = self._error_payload(response)
                raise FollowUpBossRetryableServerError(
                    self._error_message(response, payload),
                    status_code=response.status_code,
                    payload=payload,
                )

            if response.status_code >= 400:
                raise self._map_http_error(response)
            return response

    def _build_headers(
        self,
        *,
        headers: Mapping[str, str] | None,
        has_json_body: bool,
    ) -> dict[str, str]:
        """Build request headers for the API call."""
        merged_headers = {
            HEADER_ACCEPT: JSON_CONTENT_TYPE,
            "User-Agent": DEFAULT_USER_AGENT,
        }
        if has_json_body:
            merged_headers[HEADER_CONTENT_TYPE] = JSON_CONTENT_TYPE
        if self.settings.system_name:
            merged_headers[HEADER_SYSTEM] = self.settings.system_name
        system_key = self.settings.system_key_value()
        if system_key:
            merged_headers[HEADER_SYSTEM_KEY] = system_key
        merged_headers = inject_authorization(merged_headers, self._auth_strategy)
        if headers is not None:
            self._validate_caller_headers(headers)
            merged_headers.update(headers)
        return merged_headers

    def _validate_caller_headers(self, headers: Mapping[str, str]) -> None:
        """Reject caller-supplied overrides for protected request headers."""
        blocked_headers = sorted(
            {key for key in headers if key.lower() in _PROTECTED_REQUEST_HEADERS}
        )
        if blocked_headers:
            blocked_list = ", ".join(blocked_headers)
            raise ValueError(
                f"Caller-supplied headers cannot override protected headers: {blocked_list}."
            )

    def _map_http_error(self, response: httpx.Response) -> FollowUpBossHTTPError:
        """Map a response into a domain exception."""
        payload = self._error_payload(response)
        message = self._error_message(response, payload)
        if response.status_code == 400:
            return FollowUpBossValidationError(
                message, status_code=response.status_code, payload=payload
            )
        if response.status_code == 401:
            return FollowUpBossAuthError(message, status_code=response.status_code, payload=payload)
        if response.status_code == 403:
            return FollowUpBossForbiddenError(
                message, status_code=response.status_code, payload=payload
            )
        if response.status_code == 404:
            return FollowUpBossNotFoundError(
                message, status_code=response.status_code, payload=payload
            )
        return FollowUpBossHTTPError(message, status_code=response.status_code, payload=payload)

    def _error_message(
        self,
        response: httpx.Response,
        payload: Mapping[str, Any] | None,
    ) -> str:
        """Resolve the most helpful error message available."""
        if payload is not None:
            error_message = payload.get("errorMessage")
            if isinstance(error_message, str) and error_message:
                return error_message
        return f"Follow Up Boss returned HTTP {response.status_code}."

    def _error_payload(self, response: httpx.Response) -> Mapping[str, Any] | None:
        """Best-effort parse the error payload."""
        if not response.content:
            return None
        try:
            payload = response.json()
        except ValueError:
            return None
        return payload if isinstance(payload, dict) else None
