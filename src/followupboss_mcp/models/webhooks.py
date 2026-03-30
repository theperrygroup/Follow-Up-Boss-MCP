"""Webhook models."""

from __future__ import annotations

from pydantic import Field

from followupboss_mcp.models.common import CommonListQuery, RequestModel, ResponseModel


class WebhookListRequest(CommonListQuery):
    """Search filters for the webhooks collection."""

    event: str | None = None
    status: str | None = None


class CreateWebhookRequest(RequestModel):
    """Strict request model for creating a webhook."""

    event: str
    url: str


class UpdateWebhookRequest(RequestModel):
    """Strict request model for updating a webhook."""

    event: str | None = None
    status: str | None = None
    url: str | None = None


class WebhookRecord(ResponseModel):
    """Webhook resource returned by the API."""

    event: str | None = None
    id: int
    status: str | None = None
    url: str | None = None


class WebhookEventRecord(ResponseModel):
    """Webhook event resource returned by the API."""

    data: dict[str, object] | None = None
    event: str | None = None
    event_created: str | None = Field(default=None, alias="eventCreated")
    event_id: str | None = Field(default=None, alias="eventId")
    id: str
    resource_ids: list[int] = Field(default_factory=list, alias="resourceIds")
    uri: str | None = None


class WebhookEventNotification(ResponseModel):
    """Inbound webhook notification payload."""

    data: dict[str, object] | None = None
    event: str
    event_created: str | None = Field(default=None, alias="eventCreated")
    event_id: str = Field(alias="eventId")
    resource_ids: list[int] = Field(default_factory=list, alias="resourceIds")
    uri: str | None = None
