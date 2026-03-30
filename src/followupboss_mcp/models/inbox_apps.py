"""Inbox app models."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, model_validator

from followupboss_mcp.models.common import RequestModel, ResponseModel

type InboxAppMessageDeliveryStatus = Literal[
    "Sent",
    "Delivered",
    "Read",
    "Not Delivered",
]


class InstallInboxAppRequest(RequestModel):
    """Strict request model for installing an inbox app."""

    published_inbox_app_id: int = Field(serialization_alias="publishedInboxAppId")
    subscription_url: str = Field(serialization_alias="subscriptionUrl")
    user_id: int = Field(serialization_alias="userId")


class InboxAppInstallationSummary(ResponseModel):
    """Inbox app installation summary returned by installation lookups."""

    created: str | None = None
    inbox_app_id: int = Field(alias="inboxAppId")
    user_id: int | None = Field(default=None, alias="userId")


class InboxAppInstallationRecord(ResponseModel):
    """Inbox app installation resource returned by install calls."""

    can_reply: bool | None = Field(default=None, alias="canReply")
    created: str | None = None
    created_by_id: int | None = Field(default=None, alias="createdById")
    id: int
    name: str | None = None
    published_inbox_app_id: int | None = Field(default=None, alias="publishedInboxAppId")
    status: int | None = None
    updated: str | None = None
    updated_by_id: int | None = Field(default=None, alias="updatedById")
    user_id: int | None = Field(default=None, alias="userId")


class CreateInboxAppParticipantRequest(RequestModel):
    """Strict request model for adding an inbox app conversation participant."""

    email: str | None = None
    is_automation: bool | None = Field(default=None, serialization_alias="isAutomation")
    name: str | None = None
    person_id: int | None = Field(default=None, serialization_alias="personId")
    phone: str | None = None
    relationship_id: int | None = Field(default=None, serialization_alias="relationshipId")
    user_id: int | None = Field(default=None, serialization_alias="userId")

    @model_validator(mode="after")
    def _require_identity(self) -> CreateInboxAppParticipantRequest:
        """Require at least one participant identity field.

        Returns:
            The validated request instance.

        Raises:
            ValueError: If no participant identity fields are provided.
        """
        if all(
            value is None
            for value in (
                self.person_id,
                self.user_id,
                self.relationship_id,
                self.name,
                self.email,
                self.phone,
            )
        ):
            raise ValueError("At least one inbox app participant identity field must be provided.")
        return self


class InboxAppParticipantRecord(ResponseModel):
    """Inbox app conversation participant returned by the API."""

    email: str | None = None
    id: int
    is_automation: bool | None = Field(default=None, alias="isAutomation")
    name: str | None = None
    person_id: int | None = Field(default=None, alias="personId")
    phone: str | None = None
    status: str | None = None
    user_id: int | None = Field(default=None, alias="userId")


class InboxAppAttachmentRequest(RequestModel):
    """Attachment payload for inbox app message creation."""

    filename: str
    url: str


class InboxAppAttachmentRecord(ResponseModel):
    """Attachment returned on an inbox app message response."""

    filename: str | None = None
    url: str | None = None


class InboxAppConversationPersonRequest(RequestModel):
    """Person reference used in inbox app message and conversation mutations."""

    email: str | None = None
    id: int | None = None
    name: str | None = None
    phone: str | None = None

    @model_validator(mode="after")
    def _require_identity(self) -> InboxAppConversationPersonRequest:
        """Require at least one person reference field.

        Returns:
            The validated request instance.

        Raises:
            ValueError: If no person reference fields are provided.
        """
        if all(value is None for value in (self.id, self.name, self.email, self.phone)):
            raise ValueError("At least one inbox app person reference field must be provided.")
        return self


class InboxAppConversationPersonRecord(ResponseModel):
    """Person reference returned on inbox app conversation responses."""

    email: str | None = None
    id: int | None = None
    name: str | None = None
    phone: str | None = None


class InboxAppConversationOwnerRequest(RequestModel):
    """Owner reference used when creating an inbox app conversation message."""

    inbox_id: int | str | None = Field(default=None, alias="inboxId")
    user_id: int | None = Field(default=None, alias="userId")

    @model_validator(mode="after")
    def _require_owner(self) -> InboxAppConversationOwnerRequest:
        """Require either a user or inbox owner.

        Returns:
            The validated request instance.

        Raises:
            ValueError: If neither an inbox nor user owner is provided.
        """
        if self.user_id is None and self.inbox_id is None:
            raise ValueError("At least one inbox app owner field must be provided.")
        return self


class InboxAppNoteUserRequest(RequestModel):
    """User reference used when creating an inbox app note."""

    email: str | None = None
    id: int | str | None = None
    name: str | None = None

    @model_validator(mode="after")
    def _require_user(self) -> InboxAppNoteUserRequest:
        """Require at least one note-user reference field.

        Returns:
            The validated request instance.

        Raises:
            ValueError: If no note-user reference fields are provided.
        """
        if all(value is None for value in (self.id, self.name, self.email)):
            raise ValueError("At least one inbox app note user field must be provided.")
        return self


class InboxAppMessageSenderRequest(RequestModel):
    """Sender reference used when creating an inbox app message."""

    email: str | None = None
    name: str | None = None
    participant_id: int | None = Field(default=None, alias="participantId")
    person_id: int | None = Field(default=None, alias="personId")
    phone: str | None = None
    relationship_id: int | None = Field(default=None, alias="relationshipId")
    user_id: int | None = Field(default=None, alias="userId")

    @model_validator(mode="after")
    def _require_sender(self) -> InboxAppMessageSenderRequest:
        """Require at least one sender reference field.

        Returns:
            The validated request instance.

        Raises:
            ValueError: If no sender reference fields are provided.
        """
        if all(
            value is None
            for value in (
                self.user_id,
                self.person_id,
                self.relationship_id,
                self.participant_id,
                self.name,
                self.email,
                self.phone,
            )
        ):
            raise ValueError("At least one inbox app sender field must be provided.")
        return self


class CreateInboxAppMessageRequest(RequestModel):
    """Strict request model for creating an inbox app message."""

    attachments: list[InboxAppAttachmentRequest] | None = None
    delivery_status: InboxAppMessageDeliveryStatus | None = Field(
        default=None,
        serialization_alias="deliveryStatus",
    )
    delivery_status_error_message: str | None = Field(
        default=None,
        serialization_alias="deliveryStatusErrorMessage",
    )
    external_conversation_id: str = Field(serialization_alias="externalConversationId")
    external_message_id: str = Field(serialization_alias="externalMessageId")
    is_automation: bool | None = Field(default=None, serialization_alias="isAutomation")
    is_incoming: bool = Field(serialization_alias="isIncoming")
    message: str
    owner: InboxAppConversationOwnerRequest | None = None
    person: InboxAppConversationPersonRequest | None = None
    rich_objects: list[str] | None = Field(default=None, serialization_alias="richObjects")
    sender: InboxAppMessageSenderRequest
    sent_at: str | None = Field(default=None, serialization_alias="sentAt")
    subject: str | None = None


class UpdateInboxAppMessageRequest(RequestModel):
    """Strict request model for updating an inbox app message."""

    delivery_status: InboxAppMessageDeliveryStatus | None = Field(
        default=None,
        serialization_alias="deliveryStatus",
    )
    delivery_status_error_message: str | None = Field(
        default=None,
        serialization_alias="deliveryStatusErrorMessage",
    )
    external_message_id: str | None = Field(default=None, serialization_alias="externalMessageId")
    id: int | None = None

    @model_validator(mode="after")
    def _require_identifier_and_mutation(self) -> UpdateInboxAppMessageRequest:
        """Require enough fields to identify and mutate a message.

        Returns:
            The validated request instance.

        Raises:
            ValueError: If the request lacks an identifier or mutation field.
        """
        if self.id is None and self.external_message_id is None:
            raise ValueError(
                "Either an inbox app message id or external_message_id must be provided."
            )
        if (
            self.delivery_status is None
            and self.delivery_status_error_message is None
            and not (self.id is not None and self.external_message_id is not None)
        ):
            raise ValueError("Update inbox app message requests must include a mutation field.")
        return self


class InboxAppMessageSenderRecord(ResponseModel):
    """Sender reference returned by the inbox app message API."""

    avatar: str | None = None
    email: str | None = None
    name: str | None = None
    person_id: int | None = Field(default=None, alias="personId")
    phone: str | None = None


class InboxAppMessageRecord(ResponseModel):
    """Inbox app message resource returned by the API."""

    attachments: list[InboxAppAttachmentRecord] = Field(default_factory=list)
    conversation_deep_link_url: str | None = Field(default=None, alias="conversationDeepLinkUrl")
    created: str | None = None
    created_by_id: int | None = Field(default=None, alias="createdById")
    delivery_status: str | None = Field(default=None, alias="deliveryStatus")
    delivery_status_error_message: str | None = Field(
        default=None,
        alias="deliveryStatusErrorMessage",
    )
    id: int
    is_incoming: bool | None = Field(default=None, alias="isIncoming")
    message: str | None = None
    person_id: int | None = Field(default=None, alias="personId")
    sender: InboxAppMessageSenderRecord | None = None
    sent_at: str | None = Field(default=None, alias="sentAt")
    updated: str | None = None
    updated_by_id: int | None = Field(default=None, alias="updatedById")
    user_id: int | None = Field(default=None, alias="userId")


class CreateInboxAppNoteRequest(RequestModel):
    """Strict request model for creating an inbox app note."""

    body: str
    external_conversation_id: str = Field(serialization_alias="externalConversationId")
    user: InboxAppNoteUserRequest


class InboxAppNoteRecord(ResponseModel):
    """Inbox app conversation note returned by the API."""

    body: str | None = None
    conversation_deep_link_url: str | None = Field(default=None, alias="conversationDeepLinkUrl")
    conversation_id: int | None = Field(default=None, alias="conversationId")
    created: str | None = None
    created_by: str | None = Field(default=None, alias="createdBy")
    created_by_id: int | None = Field(default=None, alias="createdById")
    id: int
    is_html: bool | None = Field(default=None, alias="isHtml")
    type: str | None = None
    updated: str | None = None
    updated_by: str | None = Field(default=None, alias="updatedBy")
    updated_by_id: int | None = Field(default=None, alias="updatedById")


class UpdateInboxAppConversationRequest(RequestModel):
    """Strict request model for updating an inbox app conversation."""

    archived: bool | None = None
    assigned_inbox_id: int | None = Field(default=None, serialization_alias="assignedInboxId")
    assigned_user_id: int | None = Field(default=None, serialization_alias="assignedUserId")
    permanently_archived: bool | None = Field(
        default=None,
        serialization_alias="permanentlyArchived",
    )
    person: InboxAppConversationPersonRequest | None = None
    subject: str | None = None

    @model_validator(mode="after")
    def _require_mutation(self) -> UpdateInboxAppConversationRequest:
        """Require at least one conversation mutation field.

        Returns:
            The validated request instance.

        Raises:
            ValueError: If no conversation mutation fields are provided.
        """
        if all(
            value is None
            for value in (
                self.subject,
                self.archived,
                self.permanently_archived,
                self.person,
                self.assigned_user_id,
                self.assigned_inbox_id,
            )
        ):
            raise ValueError("At least one inbox app conversation field must be provided.")
        return self


class InboxAppConversationRecord(ResponseModel):
    """Inbox app conversation resource returned by the API."""

    archived: bool | None = None
    assigned_shared_inbox_id: int | None = Field(default=None, alias="assignedSharedInboxId")
    assigned_user_id: int | None = Field(default=None, alias="assignedUserId")
    conversation_deep_link_url: str | None = Field(default=None, alias="conversationDeepLinkUrl")
    created: str | None = None
    created_by_id: int | str | None = Field(default=None, alias="createdById")
    external_conversation_id: str | None = Field(default=None, alias="externalConversationId")
    owner_shared_inbox_id: int | None = Field(default=None, alias="ownerSharedInboxId")
    owner_user_id: int | None = Field(default=None, alias="ownerUserId")
    person: InboxAppConversationPersonRecord | None = None
    subject: str | None = None
    updated: str | None = None
    updated_by_id: int | str | None = Field(default=None, alias="updatedById")
