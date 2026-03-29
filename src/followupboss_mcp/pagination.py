"""Pagination helpers and async iterators."""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from dataclasses import dataclass, replace
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class PaginationRequest:
    """A normalized pagination request."""

    limit: int = 10
    offset: int = 0
    next_token: str | None = None


@dataclass(frozen=True)
class PaginationMetadata:
    """Normalized response pagination metadata."""

    count: int
    limit: int
    next_token: str | None
    next_link: str | None
    offset: int
    total: int | None

    def has_next(self) -> bool:
        """Return whether another page is available."""
        if self.next_token:
            return True
        if self.total is None:
            return False
        return self.offset + self.count < self.total


@dataclass(frozen=True)
class PageResult(Generic[T]):
    """A page of items plus normalized metadata."""

    items: list[T]
    metadata: PaginationMetadata


def parse_pagination_metadata(payload: dict[str, object], *, item_count: int) -> PaginationMetadata:
    """Parse Follow Up Boss pagination metadata from a JSON payload."""
    metadata = payload.get("_metadata")
    if not isinstance(metadata, dict):
        return PaginationMetadata(
            count=item_count,
            limit=item_count,
            next_token=None,
            next_link=None,
            offset=0,
            total=item_count,
        )

    total = metadata.get("total")
    if isinstance(total, int):
        normalized_total = total
    elif isinstance(total, str) and total.isdigit():
        normalized_total = int(total)
    else:
        normalized_total = None
    limit = metadata.get("limit")
    normalized_limit = limit if isinstance(limit, int) else item_count
    offset = metadata.get("offset")
    normalized_offset = offset if isinstance(offset, int) else 0
    next_token = metadata.get("next")
    next_link = metadata.get("nextLink")
    return PaginationMetadata(
        count=item_count,
        limit=normalized_limit,
        next_token=next_token if isinstance(next_token, str) and next_token else None,
        next_link=next_link if isinstance(next_link, str) and next_link else None,
        offset=normalized_offset,
        total=normalized_total,
    )


class AsyncPaginator(Generic[T]):
    """Reusable paginator supporting next-token and offset flows."""

    def __init__(
        self,
        initial_request: PaginationRequest,
        fetch_page: Callable[[PaginationRequest], Awaitable[PageResult[T]]],
    ) -> None:
        """Initialize the paginator."""
        self._initial_request = initial_request
        self._fetch_page = fetch_page

    async def pages(self) -> AsyncIterator[PageResult[T]]:
        """Yield all pages."""
        request = self._initial_request
        while True:
            page = await self._fetch_page(request)
            yield page
            if not page.metadata.has_next():
                return
            if page.metadata.next_token:
                request = replace(request, next_token=page.metadata.next_token)
                continue
            request = replace(
                request,
                next_token=None,
                offset=page.metadata.offset + page.metadata.count,
            )

    async def items(self) -> AsyncIterator[T]:
        """Yield items across all pages."""
        async for page in self.pages():
            for item in page.items:
                yield item
