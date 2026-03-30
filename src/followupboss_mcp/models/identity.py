"""Identity models."""

from __future__ import annotations

from pydantic import Field, model_validator

from followupboss_mcp.models.common import ResponseModel


class IdentityAccountOwner(ResponseModel):
    """Owner summary nested inside a live identity account payload."""

    email: str | None = None
    name: str | None = None


class IdentityAccountRecord(ResponseModel):
    """Account summary nested inside a live identity payload."""

    domain: str | None = None
    id: int | None = None
    name: str | None = None
    owner: IdentityAccountOwner | None = None


class IdentityUserRecord(ResponseModel):
    """User summary nested inside a live identity payload."""

    email: str | None = None
    fuid: str | None = None
    id: int | None = None
    is_admin: bool | None = Field(default=None, alias="isAdmin")
    is_lender: bool | None = Field(default=None, alias="isLender")
    is_owner: bool | None = Field(default=None, alias="isOwner")
    name: str | None = None
    role: str | None = None


class IdentityResponse(ResponseModel):
    """Identity response for the authenticated caller."""

    account: IdentityAccountRecord | None = None
    account_id: int | None = Field(default=None, alias="accountId")
    email: str | None = None
    id: int | None = None
    is_owner: bool | None = Field(default=None, alias="isOwner")
    name: str | None = None
    system: str | None = None
    user: IdentityUserRecord | None = None

    @model_validator(mode="after")
    def _hydrate_top_level_fields(self) -> IdentityResponse:
        """Backfill legacy top-level fields from nested account and user payloads.

        Returns:
            The normalized identity response.
        """
        if self.account_id is None and self.account is not None:
            self.account_id = self.account.id
        if self.id is None:
            if self.user is not None and self.user.id is not None:
                self.id = self.user.id
            elif self.account is not None:
                self.id = self.account.id
        if self.name is None:
            if self.user is not None and self.user.name:
                self.name = self.user.name
            elif self.account is not None:
                self.name = self.account.name
        if self.email is None:
            if self.user is not None and self.user.email:
                self.email = self.user.email
            elif self.account is not None and self.account.owner is not None:
                self.email = self.account.owner.email
        if self.is_owner is None and self.user is not None:
            self.is_owner = self.user.is_owner
        if self.system is None and self.account is not None:
            self.system = self.account.domain
        return self
