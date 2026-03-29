"""Retry policy helpers."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from math import pow

from followupboss_mcp.constants import DEFAULT_MAX_RETRY_BACKOFF_SECONDS, RETRYABLE_STATUS_CODES


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
