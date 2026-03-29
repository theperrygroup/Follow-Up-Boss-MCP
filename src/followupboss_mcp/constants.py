"""Project constants."""

from __future__ import annotations

DEFAULT_BASE_URL = "https://api.followupboss.com/v1"
DEFAULT_LOG_LEVEL = "INFO"
DEFAULT_MAX_RETRIES = 3
DEFAULT_MAX_RETRY_BACKOFF_SECONDS = 32.0
DEFAULT_TIMEOUT_SECONDS = 10.0
DEFAULT_USER_AGENT = "followupboss-mcp/0.1.0"
HEADER_ACCEPT = "Accept"
HEADER_AUTHORIZATION = "Authorization"
HEADER_CONTENT_TYPE = "Content-Type"
HEADER_SYSTEM = "X-System"
HEADER_SYSTEM_KEY = "X-System-Key"
JSON_CONTENT_TYPE = "application/json"
RATE_LIMIT_STATUS_CODE = 429
RETRYABLE_STATUS_CODES = frozenset({500, 502, 503, 504})
WEBHOOK_SIGNATURE_HEADER = "FUB-Signature"
