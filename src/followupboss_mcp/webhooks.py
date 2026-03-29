"""Webhook verification and receiver helpers."""

from __future__ import annotations

import base64
import hashlib
import hmac
from dataclasses import dataclass

from followupboss_mcp.errors import FollowUpBossWebhookSignatureError
from followupboss_mcp.models.webhooks import WebhookEventNotification


@dataclass(frozen=True)
class WebhookAck:
    """A fast-ack response plan for webhook receivers."""

    body: dict[str, str] | None
    status_code: int


def compute_webhook_signature(raw_body: bytes, system_key: str) -> str:
    """Compute the official Follow Up Boss webhook signature."""
    encoded_payload = base64.b64encode(raw_body)
    return hmac.new(
        system_key.encode("utf-8"),
        encoded_payload,
        hashlib.sha256,
    ).hexdigest()


def verify_webhook_signature(raw_body: bytes, signature: str, system_key: str) -> None:
    """Verify a webhook signature against the exact raw request body."""
    expected = compute_webhook_signature(raw_body, system_key)
    if not hmac.compare_digest(expected, signature):
        raise FollowUpBossWebhookSignatureError("Webhook signature verification failed.")


def parse_webhook_notification(payload: dict[str, object]) -> WebhookEventNotification:
    """Parse an inbound webhook notification."""
    return WebhookEventNotification.model_validate(payload)


def build_fast_ack(status_code: int = 204) -> WebhookAck:
    """Build a fast acknowledgment response for webhook receivers."""
    if not 200 <= status_code < 300:
        raise ValueError("Webhook acknowledgments must use a 2xx status code.")
    body = None if status_code == 204 else {"status": "ok"}
    return WebhookAck(body=body, status_code=status_code)


def should_retry_webhook_delivery(status_code: int) -> bool:
    """Return whether Follow Up Boss will retry a webhook delivery."""
    return not 200 <= status_code < 300
