"""Identity models."""

from __future__ import annotations

from pydantic import Field

from followupboss_mcp.models.common import ResponseModel


class IdentityResponse(ResponseModel):
    """Identity response for the authenticated caller."""

    account_id: int | None = Field(default=None, alias="accountId")
    email: str | None = None
    id: int | None = None
    is_owner: bool | None = Field(default=None, alias="isOwner")
    name: str | None = None
    system: str | None = None
