"""Retry policy helpers."""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from math import pow

from followupboss_mcp.constants import (
    DEFAULT_MAX_RETRY_BACKOFF_SECONDS,
    RETRYABLE_SERVER_ERROR_METHODS,
    RETRYABLE_STATUS_CODES,
)

_PIPELINE_UPDATE_PATH = re.compile(r"/?pipelines/\d+/?")


@dataclass(frozen=True)
class RetryPolicy:
    """Truncated exponential backoff policy with jitter."""

    max_retries: int
    max_backoff_seconds: float = DEFAULT_MAX_RETRY_BACKOFF_SECONDS
    jitter_max_seconds: float = 1.0

    def can_retry(self, attempt: int) -> bool:
        """Return whether another retry is allowed."""
        return attempt < self.max_retries

    def is_retryable_status(self, status_code: int) -> bool:
        """Return whether an HTTP status should be retried."""
        return status_code in RETRYABLE_STATUS_CODES

    def is_retryable_method(self, method: str) -> bool:
        """Return whether a server error may be retried for an HTTP method.

        Only idempotent methods qualify. Follow Up Boss may already have saved a
        POST or PATCH that failed with a server error, so resending it could
        create a duplicate record.
        """
        return method.upper() in RETRYABLE_SERVER_ERROR_METHODS

    def is_retryable_request(
        self,
        method: str,
        path: str,
        json_body: Mapping[str, object] | None = None,
    ) -> bool:
        """Return whether a request may be resent after Follow Up Boss may have saved it.

        This covers server errors and the transport errors that can happen after the
        request reached Follow Up Boss. POST and PATCH never qualify. A pipeline update
        that lists a stage without an id does not qualify either, because Follow Up Boss
        creates a new stage for each such entry.
        """
        return self.is_retryable_method(method) and not _adds_pipeline_stages(
            method, path, json_body
        )

    def backoff_seconds(
        self,
        *,
        attempt: int,
        jitter_source: Callable[[], float],
        retry_after_seconds: float | None = None,
    ) -> float:
        """Return the delay before the next retry."""
        if retry_after_seconds is not None:
            return retry_after_seconds

        jitter = jitter_source()
        bounded_jitter = min(max(jitter, 0.0), 1.0) * self.jitter_max_seconds
        return min(pow(2.0, attempt) + bounded_jitter, self.max_backoff_seconds)


def _adds_pipeline_stages(
    method: str,
    path: str,
    json_body: Mapping[str, object] | None,
) -> bool:
    """Return whether a request is a pipeline update that creates stages.

    Follow Up Boss creates a new stage for every entry in a pipeline update's
    stages that has no id.
    """
    if method.upper() != "PUT" or json_body is None:
        return False
    if _PIPELINE_UPDATE_PATH.fullmatch(path) is None:
        return False
    stages = json_body.get("stages")
    if not isinstance(stages, list | tuple):
        return False
    return any(not isinstance(stage, Mapping) or stage.get("id") is None for stage in stages)
