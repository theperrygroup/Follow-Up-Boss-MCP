"""Tests for retry, rate limits, pagination, shared models, and webhook helpers."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from followupboss_mcp.errors import FollowUpBossValidationError, FollowUpBossWebhookSignatureError
from followupboss_mcp.models.common import CommonListQuery, serialize_query_value
from followupboss_mcp.models.custom_fields import CustomFieldRecord
from followupboss_mcp.models.people import PeopleSearchRequest
from followupboss_mcp.pagination import (
    AsyncPaginator,
    PageResult,
    PaginationMetadata,
    PaginationRequest,
    parse_pagination_metadata,
)
from followupboss_mcp.rate_limits import parse_retry_after
from followupboss_mcp.retry import RetryPolicy
from followupboss_mcp.services.custom_fields import CustomFieldsService
from followupboss_mcp.webhooks import (
    build_fast_ack,
    compute_webhook_signature,
    parse_webhook_notification,
    should_retry_webhook_delivery,
    verify_webhook_signature,
)


def test_retry_policy() -> None:
    """Retry policy should expose retryability and backoff calculations."""
    policy = RetryPolicy(max_retries=2, max_backoff_seconds=5, jitter_max_seconds=1)
    assert policy.can_retry(0) is True
    assert policy.can_retry(2) is False
    assert policy.is_retryable_status(500) is True
    assert policy.is_retryable_status(404) is False
    assert policy.backoff_seconds(attempt=0, jitter_source=lambda: 0.5) == 1.5
    assert policy.backoff_seconds(attempt=3, jitter_source=lambda: 1.0) == 5
    assert policy.backoff_seconds(attempt=0, jitter_source=lambda: -1.0) == 1.0
    assert (
        policy.backoff_seconds(
            attempt=1,
            jitter_source=lambda: 0.25,
            retry_after_seconds=7.0,
        )
        == 7.0
    )


def test_parse_retry_after() -> None:
    """Retry-After should parse delta seconds, HTTP dates, and invalid values."""
    now = datetime(2026, 3, 28, tzinfo=UTC)
    assert parse_retry_after(None) is None
    assert parse_retry_after(" ") is None
    assert parse_retry_after("8") == 8.0
    assert parse_retry_after("Sun, 29 Mar 2026 00:00:00 GMT", now=now) == 86400.0
    assert parse_retry_after("invalid date") is None


def test_shared_query_serialization_and_custom_field_helpers() -> None:
    """Query models and custom field helpers should serialize predictably."""
    assert serialize_query_value(True) == "true"
    assert serialize_query_value(False) == "false"
    assert serialize_query_value(3) == "3"
    assert serialize_query_value(2.5) == "2.5"
    assert serialize_query_value("abc") == "abc"
    assert serialize_query_value(datetime(2026, 3, 28, tzinfo=UTC)) == "2026-03-28T00:00:00+00:00"
    assert serialize_query_value([1, "x", True]) == "1,x,true"
    with pytest.raises(TypeError):
        serialize_query_value({"bad": "value"})

    query = CommonListQuery(fields=["id", "name"], ids=[1, 2], limit=10, next_token="token")
    assert query.to_query_params() == {
        "fields": "id,name",
        "ids": "1,2",
        "limit": "10",
        "next": "token",
    }

    people_query = PeopleSearchRequest(
        custom_field_filters={"customSource": "Zillow"},
        include_ponds=True,
    )
    assert people_query.to_query_params() == {}

    valid = CustomFieldsService.validate_custom_field_names({"customBirthday": "2026-03-28"})
    assert valid == {"customBirthday": "2026-03-28"}
    with pytest.raises(FollowUpBossValidationError):
        CustomFieldsService.validate_custom_field_names({"Birthday": "2026-03-28"})

    fields = [
        CustomFieldRecord(
            id=1, label="Birthday", name="customBirthday", type="date", isRecurring=True
        ),
        CustomFieldRecord(id=2, label="Nickname", name="customNickname", type="text"),
    ]
    assert fields[0].is_recurring is True
    assert CustomFieldsService.resolve_field_names(fields) == {
        "Birthday": "customBirthday",
        "Nickname": "customNickname",
    }


def test_parse_pagination_metadata_and_has_next() -> None:
    """Pagination metadata should normalize totals and next-token behavior."""
    metadata = parse_pagination_metadata(
        {
            "_metadata": {
                "limit": 10,
                "offset": 0,
                "total": "15",
                "next": "abc",
                "nextLink": "https://x",
            }
        },
        item_count=10,
    )
    assert metadata.total == 15
    assert metadata.has_next() is True

    no_next = PaginationMetadata(
        count=5, limit=5, next_token=None, next_link=None, offset=0, total=5
    )
    assert no_next.has_next() is False

    missing = parse_pagination_metadata({}, item_count=3)
    assert missing == PaginationMetadata(
        count=3,
        limit=3,
        next_token=None,
        next_link=None,
        offset=0,
        total=3,
    )


@pytest.mark.asyncio
async def test_async_paginator_next_token_and_offset() -> None:
    """AsyncPaginator should prefer next tokens and fall back to offsets."""
    calls: list[PaginationRequest] = []

    async def fetch_page(request: PaginationRequest) -> PageResult[int]:
        calls.append(request)
        if request.next_token is None and request.offset == 0:
            return PageResult(
                items=[1, 2],
                metadata=PaginationMetadata(
                    count=2,
                    limit=2,
                    next_token="next-1",
                    next_link="https://example.com",
                    offset=0,
                    total=5,
                ),
            )
        if request.next_token == "next-1":
            return PageResult(
                items=[3, 4],
                metadata=PaginationMetadata(
                    count=2,
                    limit=2,
                    next_token=None,
                    next_link=None,
                    offset=2,
                    total=5,
                ),
            )
        return PageResult(
            items=[5],
            metadata=PaginationMetadata(
                count=1,
                limit=2,
                next_token=None,
                next_link=None,
                offset=request.offset,
                total=5,
            ),
        )

    paginator = AsyncPaginator(PaginationRequest(limit=2), fetch_page)
    items = [item async for item in paginator.items()]
    assert items == [1, 2, 3, 4, 5]
    assert calls == [
        PaginationRequest(limit=2, offset=0, next_token=None),
        PaginationRequest(limit=2, offset=0, next_token="next-1"),
        PaginationRequest(limit=2, offset=4, next_token=None),
    ]


def test_webhook_helpers() -> None:
    """Webhook helpers should follow the documented signature and ack behavior."""
    raw = b'{"event":"peopleCreated","resourceIds":[1]}'
    signature = compute_webhook_signature(raw, "system-key")
    assert len(signature) == 64
    verify_webhook_signature(raw, signature, "system-key")
    with pytest.raises(FollowUpBossWebhookSignatureError):
        verify_webhook_signature(raw, "bad", "system-key")

    notification = parse_webhook_notification(
        {
            "eventId": "abc",
            "eventCreated": "2026-03-28T00:00:00Z",
            "event": "peopleCreated",
            "resourceIds": [1, 2],
            "uri": "https://api.followupboss.com/v1/people?id=1,2",
        }
    )
    assert notification.event == "peopleCreated"
    assert notification.resource_ids == [1, 2]

    assert build_fast_ack() == build_fast_ack(204)
    assert build_fast_ack(200).body == {"status": "ok"}
    with pytest.raises(ValueError):
        build_fast_ack(500)
    assert should_retry_webhook_delivery(500) is True
    assert should_retry_webhook_delivery(204) is False
