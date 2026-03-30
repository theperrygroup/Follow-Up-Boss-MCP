"""Email marketing models."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import Field, field_validator, model_validator

from followupboss_mcp.models.common import QueryModel, RequestModel, ResponseModel

type EmailEventType = Literal[
    "delivered",
    "open",
    "click",
    "bounced",
    "soft-bounce",
    "hard-bounce",
    "unsubscribe",
    "spamreport",
    "dropped",
]


class EmailCampaignListRequest(QueryModel):
    """Search filters for the email marketing campaigns collection."""

    origin: str | None = None
    origin_id: str | None = Field(default=None, serialization_alias="originId")


class CreateEmailCampaignRequest(RequestModel):
    """Strict request model for creating an email marketing campaign."""

    body_html: str | None = Field(default=None, serialization_alias="bodyHtml")
    name: str | None = None
    origin: str
    origin_id: str = Field(serialization_alias="originId")
    subject: str | None = None


class UpdateEmailCampaignRequest(RequestModel):
    """Strict request model for updating an email marketing campaign."""

    body_html: str | None = Field(default=None, serialization_alias="bodyHtml")
    name: str | None = None
    subject: str | None = None

    @model_validator(mode="after")
    def _require_mutation(self) -> UpdateEmailCampaignRequest:
        """Require at least one campaign field to update.

        Returns:
            The validated request instance.

        Raises:
            ValueError: If no update fields are provided.
        """
        if self.name is None and self.subject is None and self.body_html is None:
            raise ValueError("At least one email campaign field must be provided.")
        return self


class EmailCampaignRecord(ResponseModel):
    """Email marketing campaign resource returned by the API."""

    body_html: str | None = Field(default=None, alias="bodyHtml")
    id: int
    name: str | None = None
    origin: str | None = None
    origin_id: str | None = Field(default=None, alias="originId")
    subject: str | None = None


class EmailEventListRequest(QueryModel):
    """Search filters for the email marketing events collection."""

    limit: int | None = None
    offset: int | None = None
    person_id: int | None = Field(default=None, serialization_alias="personId")
    type: EmailEventType | None = None
    updated_after: datetime | None = Field(default=None, serialization_alias="updatedAfter")


class CreateEmailEventRequest(RequestModel):
    """One email marketing event submitted to Follow Up Boss."""

    campaign_id: int | str = Field(serialization_alias="campaignId")
    occurred: datetime
    person_id: int | None = Field(default=None, serialization_alias="personId")
    recipient: str
    type: EmailEventType
    url: str | None = None
    user_id: int | None = Field(default=None, serialization_alias="userId")


class CreateEmailEventsBatchRequest(RequestModel):
    """Strict request model for posting batched email marketing events."""

    em_events: list[CreateEmailEventRequest] = Field(serialization_alias="emEvents")

    @field_validator("em_events")
    @classmethod
    def _validate_event_count(
        cls,
        value: list[CreateEmailEventRequest],
    ) -> list[CreateEmailEventRequest]:
        """Require at least one event and cap batches at the documented maximum.

        Args:
            value: The submitted email marketing events.

        Returns:
            The validated event list.

        Raises:
            ValueError: If the batch is empty or exceeds the documented limit.
        """
        if not value:
            raise ValueError("At least one email marketing event must be provided.")
        if len(value) > 1000:
            raise ValueError("Email marketing event batches cannot exceed 1000 events.")
        return value


class EmailEventRecord(ResponseModel):
    """Email marketing event resource returned by the API."""

    campaign_id: int | str | None = Field(default=None, alias="campaignId")
    campaign_name: str | None = Field(default=None, alias="campaignName")
    count: int | None = None
    created: str | None = None
    person_id: int | None = Field(default=None, alias="personId")
    type: str | None = None
    updated: str | None = None


class EmailEventsBatchResult(ResponseModel):
    """Result returned after posting email marketing events."""

    em_event_ids: list[int] = Field(default_factory=list, alias="emEventIds")
    recipients_not_found: list[str] = Field(default_factory=list, alias="recipientsNotFound")
