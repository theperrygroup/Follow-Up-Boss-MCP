"""Text message models."""

from __future__ import annotations

from pydantic import AliasChoices, Field

from followupboss_mcp.models.common import JsonValue, QueryModel, RequestModel, ResponseModel


class TextMessageListRequest(QueryModel):
    """Search filters for the text messages collection."""

    from_number: str | None = Field(default=None, serialization_alias="fromNumber")
    person_id: int | None = Field(default=None, serialization_alias="personId")
    to_number: str | None = Field(default=None, serialization_alias="toNumber")


class CreateTextMessageRequest(RequestModel):
    """Strict request model for recording an externally sent text message."""

    external_label: str | None = Field(default=None, serialization_alias="externalLabel")
    external_url: str | None = Field(default=None, serialization_alias="externalUrl")
    from_number: str = Field(serialization_alias="fromNumber")
    is_incoming: bool | None = Field(default=None, serialization_alias="isIncoming")
    message: str
    person_id: int = Field(serialization_alias="personId")
    to_number: str = Field(serialization_alias="toNumber")


class TextMessageRecord(ResponseModel):
    """Text message resource returned by the API."""

    action_plan_id: int | None = Field(default=None, alias="actionPlanId")
    archived: bool | None = None
    created: str | None = None
    created_by_id: int | None = Field(default=None, alias="createdById")
    external_label: str | None = Field(default=None, alias="externalLabel")
    external_url: str | None = Field(default=None, alias="externalUrl")
    first_name: str | None = Field(default=None, alias="firstName")
    from_number: str | None = Field(default=None, alias="fromNumber")
    group_text_id: int | None = Field(default=None, alias="groupTextId")
    id: int
    is_external: bool | None = Field(default=None, alias="isExternal")
    is_incoming: bool | None = Field(default=None, alias="isIncoming")
    last_name: str | None = Field(default=None, alias="lastName")
    media: list[JsonValue] = Field(default_factory=list)
    message: str | None = None
    name: str | None = None
    participants: list[JsonValue] = Field(default_factory=list)
    person_id: int | None = Field(default=None, alias="personId")
    picture: str | None = None
    read: bool | None = None
    sent: str | None = None
    shared_inbox_id: int | None = Field(default=None, alias="sharedInboxId")
    status: str | None = None
    system_id: int | None = Field(default=None, alias="systemId")
    system_name: str | None = Field(default=None, alias="systemName")
    to_number: str | None = Field(default=None, alias="toNumber")
    updated: str | None = None
    updated_by_id: int | None = Field(default=None, alias="updatedById")
    user_id: int | None = Field(default=None, alias="userId")
    user_name: str | None = Field(default=None, alias="userName")


class TextMessageTemplateMergeRecipient(RequestModel):
    """One recipient used for text message template merge previews."""

    name: str | None = None
    phone: str


class TextMessageTemplateMergeRecipients(RequestModel):
    """Recipient groups used for text message template merge previews."""

    from_recipients: list[TextMessageTemplateMergeRecipient] | None = Field(
        default=None,
        serialization_alias="from",
    )
    to: list[TextMessageTemplateMergeRecipient] | None = None


class MergeTextMessageTemplateRequest(RequestModel):
    """Strict request model for merging a text message template."""

    person_id: int | None = Field(
        default=None,
        serialization_alias="personId",
        validation_alias=AliasChoices("personId", "mergePersonId"),
    )
    recipients: TextMessageTemplateMergeRecipients | None = None
    template_id: int = Field(serialization_alias="templateId")


class MergedTextMessageTemplateRecord(ResponseModel):
    """Merged text message template preview returned by the API."""

    merged_template: str | None = Field(default=None, alias="mergedTemplate")


class TextMessageTemplateListRequest(QueryModel):
    """Search filters for the text message templates collection."""

    limit: int | None = None
    offset: int | None = None


class CreateTextMessageTemplateRequest(RequestModel):
    """Strict request model for creating a text message template."""

    is_shared: bool | None = Field(default=None, serialization_alias="isShared")
    message: str
    name: str


class UpdateTextMessageTemplateRequest(RequestModel):
    """Strict request model for updating a text message template."""

    is_shared: bool | None = Field(default=None, serialization_alias="isShared")
    message: str
    name: str


class TextMessageTemplateRecord(ResponseModel):
    """Text message template resource returned by the API."""

    action_plans: list[JsonValue] = Field(default_factory=list, alias="actionPlans")
    categories: list[JsonValue] = Field(default_factory=list)
    created_by: JsonValue | None = Field(default=None, alias="createdBy")
    effectiveness_score: JsonValue | None = Field(default=None, alias="effectivenessScore")
    id: int
    is_deletable: bool | None = Field(default=None, alias="isDeletable")
    is_editable: bool | None = Field(default=None, alias="isEditable")
    is_shareable: bool | None = Field(default=None, alias="isShareable")
    is_shared: bool | None = Field(default=None, alias="isShared")
    message: str | None = None
    name: str | None = None
    sent_people_count: int | None = Field(default=None, alias="sentPeopleCount")
    sent_people_ids: list[int] = Field(default_factory=list, alias="sentPeopleIds")
    total_opt_out_rate: JsonValue | None = Field(default=None, alias="totalOptOutRate")
    total_replies: int | None = Field(default=None, alias="totalReplies")
    total_sent: int | None = Field(default=None, alias="totalSent")
    windowed_opt_out_rate: JsonValue | None = Field(default=None, alias="windowedOptOutRate")
    windowed_replies: int | None = Field(default=None, alias="windowedReplies")
    windowed_sent: int | None = Field(default=None, alias="windowedSent")
