"""User models."""

from __future__ import annotations

from pydantic import Field

from followupboss_mcp.models.common import CommonListQuery, QueryModel, ResponseModel

_REDACTED = "***redacted***"


class UserListRequest(CommonListQuery):
    """Search filters for the users collection."""

    email: str | None = None
    include_deleted: bool | None = Field(default=None, serialization_alias="includeDeleted")
    name: str | None = None
    role: str | None = None


class DeleteUserRequest(QueryModel):
    """Query parameters for deleting a user."""

    assign_to: int = Field(serialization_alias="assignTo")


class UserRecord(ResponseModel):
    """User resource returned by the API."""

    created: str | None = None
    email: str | None = None
    first_name: str | None = Field(default=None, alias="firstName")
    id: int
    is_owner: bool | None = Field(default=None, alias="isOwner")
    last_name: str | None = Field(default=None, alias="lastName")
    name: str | None = None
    phone: str | None = None
    role: str | None = None
    status: str | None = None
    updated: str | None = None


class IntercomSettingsRecord(ResponseModel):
    """Intercom settings nested under the current-user payload."""

    app_id: str | None = None
    created_at: str | None = None
    user_hash: str | None = None
    user_id: str | None = None


class ConnectedEmailRecord(ResponseModel):
    """Connected email settings nested under the current-user payload."""

    email: str | None = None
    has_smtp: bool | None = Field(default=None, alias="hasSmtp")
    imap_lead_processing: bool | None = Field(default=None, alias="imapLeadProcessing")
    oauth_provider: str | None = Field(default=None, alias="oauthProvider")
    share_emails: bool | None = Field(default=None, alias="shareEmails")


class CurrentUserRecord(UserRecord):
    """Current authenticated user returned by the `/me` endpoint."""

    account: int | None = None
    algolia_key: str | None = Field(default=None, alias="algoliaKey")
    api_key: str | None = Field(default=None, alias="apiKey")
    beta: bool | None = None
    beta_only: bool | None = Field(default=None, alias="betaOnly")
    calling_capability_token: str | None = Field(default=None, alias="callingCapabilityToken")
    calling_enabled: bool | None = Field(default=None, alias="callingEnabled")
    connected_email: ConnectedEmailRecord | None = Field(default=None, alias="connectedEmail")
    features: list[str] = Field(default_factory=list)
    intercom_settings: IntercomSettingsRecord | None = Field(
        default=None,
        alias="intercomSettings",
    )
    lead_email_address: str | None = Field(default=None, alias="leadEmailAddress")
    notify_by: str | list[str] | None = Field(default=None, alias="notifyBy")
    raw_signature: str | None = Field(default=None, alias="rawSignature")
    signature: str | None = None
    team_member: object | None = Field(default=None, alias="teamMember")
    time_zone: str | None = Field(default=None, alias="timeZone")
    unread_conversation_count: int | None = Field(default=None, alias="unreadConversationCount")
    voicemail_enabled: bool | None = Field(default=None, alias="voicemailEnabled")
    voicemail_url: str | None = Field(default=None, alias="voicemailUrl")

    def redacted_for_mcp(self) -> CurrentUserRecord:
        """Return a copy safe for MCP tool output.

        Returns:
            A copy of the current-user record with secret-like fields redacted.
        """
        intercom_settings = self.intercom_settings
        if intercom_settings is not None and intercom_settings.user_hash is not None:
            intercom_settings = intercom_settings.model_copy(update={"user_hash": _REDACTED})
        return self.model_copy(
            update={
                "api_key": _REDACTED if self.api_key is not None else None,
                "algolia_key": _REDACTED if self.algolia_key is not None else None,
                "calling_capability_token": (
                    _REDACTED if self.calling_capability_token is not None else None
                ),
                "intercom_settings": intercom_settings,
            }
        )
