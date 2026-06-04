"""Email template models."""

from __future__ import annotations

from pydantic import Field

from followupboss_mcp.models.common import JsonValue, QueryModel, RequestModel, ResponseModel


class TemplateListRequest(QueryModel):
    """Search filters for the email templates collection."""

    limit: int | None = None
    offset: int | None = None


class TemplateLookupRequest(QueryModel):
    """Query parameters for retrieving an email template by ID."""

    merge_person_id: int | None = Field(default=None, serialization_alias="mergePersonId")


class CreateTemplateRequest(RequestModel):
    """Strict request model for creating an email template."""

    body: str
    is_shared: bool | None = Field(default=None, serialization_alias="isShared")
    name: str
    subject: str


class UpdateTemplateRequest(RequestModel):
    """Strict request model for updating an email template."""

    body: str
    name: str
    subject: str


class EmailTemplateMergeRecipient(RequestModel):
    """One recipient used for email template merge previews."""

    email: str
    name: str | None = None


class EmailTemplateMergeRecipients(RequestModel):
    """Recipient groups used for email template merge previews."""

    bcc: list[EmailTemplateMergeRecipient] | None = None
    cc: list[EmailTemplateMergeRecipient] | None = None
    from_recipients: list[EmailTemplateMergeRecipient] | None = Field(
        default=None,
        serialization_alias="from",
    )
    to: list[EmailTemplateMergeRecipient] | None = None


class MergeTemplateRequest(RequestModel):
    """Strict request model for merging an email template."""

    merge_person_id: int | None = Field(default=None, serialization_alias="mergePersonId")
    recipients: EmailTemplateMergeRecipients | None = None
    template_id: int = Field(serialization_alias="templateId")


class TemplateActionPlanSummary(ResponseModel):
    """Minimal action-plan summary nested inside a template record."""

    id: int
    name: str | None = None


class TemplateRecord(ResponseModel):
    """Email template resource returned by the API."""

    action_plans: list[TemplateActionPlanSummary] = Field(default_factory=list, alias="actionPlans")
    body: str | None = None
    categories: list[JsonValue] = Field(default_factory=list)
    created: str | None = None
    created_by_id: int | None = Field(default=None, alias="createdById")
    id: int
    imported: bool | None = None
    is_deletable: bool | None = Field(default=None, alias="isDeletable")
    is_editable: bool | None = Field(default=None, alias="isEditable")
    is_mobile: bool | None = Field(default=None, alias="isMobile")
    is_shareable: bool | str | None = Field(default=None, alias="isShareable")
    is_shared: bool | None = Field(default=None, alias="isShared")
    name: str | None = None
    subject: str | None = None
    updated: str | None = None
    updated_by_id: int | None = Field(default=None, alias="updatedById")
