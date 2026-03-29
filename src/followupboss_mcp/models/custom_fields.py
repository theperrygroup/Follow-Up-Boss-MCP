"""Custom field models."""

from __future__ import annotations

from pydantic import Field

from followupboss_mcp.models.common import CommonListQuery, ResponseModel


class CustomFieldListRequest(CommonListQuery):
    """Search filters for the custom fields collection."""

    label: str | None = None


class CustomFieldRecord(ResponseModel):
    """Custom field definition."""

    id: int
    is_recurring: bool | None = Field(default=None, alias="isRecurring")
    label: str
    name: str
    type: str
