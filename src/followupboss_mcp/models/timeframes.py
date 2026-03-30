"""Timeframe models."""

from __future__ import annotations

from followupboss_mcp.models.common import QueryModel, ResponseModel


class TimeframeListRequest(QueryModel):
    """Search filters for the timeframes collection."""


class TimeframeRecord(ResponseModel):
    """Timeframe resource returned by the API."""

    id: int
    timeframe: str | None = None
