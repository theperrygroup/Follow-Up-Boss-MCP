"""Hosted inbound-auth models and FastMCP verifier adapters."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Protocol, Self

from pydantic import (
    AnyHttpUrl,
    BaseModel,
    ConfigDict,
    SecretStr,
    ValidationInfo,
    field_validator,
    model_validator,
)

from followupboss_mcp.errors import TenantStoreError
from followupboss_mcp.tenant_store import ResolvedTenantCredentials, TenantStore
from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.provider import AccessToken, TokenVerifier
from mcp.server.auth.settings import AuthSettings


def _normalize_required_string(value: str, *, field_name: str) -> str:
    """Normalize one required string field.

    Args:
        value: The raw string value supplied to the model.
        field_name: The field currently being validated.

    Returns:
        The trimmed string value.

    Raises:
        ValueError: If the string is empty after trimming whitespace.
    """
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be empty.")
    return normalized


def _normalize_optional_string(value: object) -> object:
    """Normalize one optional string field.

    Args:
        value: The raw field value supplied to the model.

    Returns:
        The trimmed string when a non-empty string is provided, `None` when the
        string is blank, or the original non-string value for downstream
        validation.
    """
    if not isinstance(value, str):
        return value
    normalized = value.strip()
    return normalized or None


def _normalize_scopes(value: object) -> object:
    """Normalize scope input into a stable tuple.

    Args:
        value: The raw scope field supplied to the model.

    Returns:
        A tuple of unique, trimmed scopes when a supported scope input is
        provided, or the original value for downstream validation.
    """
    if value is None:
        return ()

    raw_scopes: Sequence[object]
    if isinstance(value, str):
        raw_scopes = tuple(part for part in value.replace(",", " ").split(" ") if part.strip())
    elif isinstance(value, Sequence) and not isinstance(value, bytes | bytearray):
        raw_scopes = value
    else:
        return value

    normalized_scopes: list[str] = []
    for scope in raw_scopes:
        if not isinstance(scope, str):
            return value
        normalized_scope = _normalize_required_string(scope, field_name="scope")
        if normalized_scope not in normalized_scopes:
            normalized_scopes.append(normalized_scope)
    return tuple(normalized_scopes)


def _duplicate_values(values: Sequence[str]) -> tuple[str, ...]:
    """Return duplicate values while preserving first-seen order.

    Args:
        values: The values that should be unique.

    Returns:
        A tuple containing each duplicated value once, in first-seen order.
    """
    seen: set[str] = set()
    duplicates: list[str] = []
    for value in values:
        if value in seen and value not in duplicates:
            duplicates.append(value)
        seen.add(value)
    return tuple(duplicates)


class HostedVerifiedIdentity(BaseModel):
    """Verified bearer-token identity for one hosted caller."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    tenant_id: str
    subject: str
    client_id: str
    scopes: tuple[str, ...] = ()
    expires_at: int | None = None
    token_id: str | None = None
    credential_id: str | None = None

    @field_validator("tenant_id", "subject", "client_id")
    @classmethod
    def _validate_required_identifiers(cls, value: str, info: ValidationInfo) -> str:
        """Require non-empty hosted-identity identifiers.

        Args:
            value: The raw field value.
            info: Validation context for the current field.

        Returns:
            The normalized identifier.
        """
        return _normalize_required_string(value, field_name=info.field_name or "field")

    @field_validator("token_id", "credential_id", mode="before")
    @classmethod
    def _validate_optional_identifiers(cls, value: object) -> object:
        """Normalize optional hosted-identity identifiers.

        Args:
            value: The raw field value.

        Returns:
            The normalized identifier or `None`.
        """
        return _normalize_optional_string(value)

    @field_validator("scopes", mode="before")
    @classmethod
    def _validate_scopes(cls, value: object) -> object:
        """Normalize scope collections to a unique tuple.

        Args:
            value: The raw scope value.

        Returns:
            The normalized scope tuple.
        """
        return _normalize_scopes(value)

    @field_validator("expires_at")
    @classmethod
    def _validate_expiration(cls, value: int | None) -> int | None:
        """Require positive Unix timestamps when an expiration is provided.

        Args:
            value: The token expiration timestamp.

        Returns:
            The validated expiration timestamp.

        Raises:
            ValueError: If the expiration timestamp is not positive.
        """
        if value is not None and value <= 0:
            raise ValueError("expires_at must be greater than zero.")
        return value


class HostedAuthenticatedTenant(BaseModel):
    """Non-secret tenant context captured during hosted authentication."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    tenant_id: str
    tenant_slug: str
    display_name: str | None = None
    credential_id: str

    @field_validator("tenant_id", "tenant_slug", "credential_id")
    @classmethod
    def _validate_required_identifiers(cls, value: str, info: ValidationInfo) -> str:
        """Require non-empty tenant-context identifiers.

        Args:
            value: The raw field value.
            info: Validation context for the current field.

        Returns:
            The normalized identifier.
        """
        return _normalize_required_string(value, field_name=info.field_name or "field")

    @field_validator("display_name", mode="before")
    @classmethod
    def _validate_display_name(cls, value: object) -> object:
        """Normalize optional tenant display names.

        Args:
            value: The raw display-name value.

        Returns:
            The normalized display name or `None`.
        """
        return _normalize_optional_string(value)

    @classmethod
    def from_resolved_tenant(cls, resolved: ResolvedTenantCredentials) -> Self:
        """Project resolved tenant records into auth-safe tenant context.

        Args:
            resolved: The resolved tenant and credential pair.

        Returns:
            The non-secret tenant context stored on the authenticated token.
        """
        return cls.model_validate(
            {
                "tenant_id": resolved.tenant.tenant_id,
                "tenant_slug": resolved.tenant.tenant_slug,
                "display_name": resolved.tenant.display_name,
                "credential_id": resolved.credential.credential_id,
            }
        )


class HostedAccessToken(AccessToken):
    """FastMCP access token carrying hosted identity and tenant context."""

    identity: HostedVerifiedIdentity
    tenant: HostedAuthenticatedTenant

    @classmethod
    def from_verified_identity(
        cls,
        *,
        token: str,
        identity: HostedVerifiedIdentity,
        tenant: HostedAuthenticatedTenant,
    ) -> Self:
        """Build the access token object stored in FastMCP auth context.

        Args:
            token: The raw bearer token that was verified.
            identity: The verified hosted identity extracted from the token.
            tenant: The active tenant context resolved from the tenant store.

        Returns:
            The access token object used by FastMCP's auth middleware.
        """
        return cls.model_validate(
            {
                "token": token,
                "client_id": identity.client_id,
                "scopes": list(identity.scopes),
                "expires_at": identity.expires_at,
                "identity": identity,
                "tenant": tenant,
            }
        )


class HostedIdentityVerifier(Protocol):
    """Protocol for verifying hosted bearer tokens into tenant identity."""

    async def verify_token(self, token: str) -> HostedVerifiedIdentity | None:
        """Verify a bearer token and return hosted identity when valid.

        Args:
            token: The raw bearer token from the inbound request.

        Returns:
            The verified hosted identity when the token is valid, otherwise
            `None`.
        """


class HostedAuthSettings(BaseModel):
    """FastMCP-compatible resource-server settings for hosted auth."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    issuer_url: AnyHttpUrl
    resource_server_url: AnyHttpUrl
    required_scopes: tuple[str, ...] = ()

    @field_validator("required_scopes", mode="before")
    @classmethod
    def _validate_required_scopes(cls, value: object) -> object:
        """Normalize required scopes to a unique tuple.

        Args:
            value: The raw required-scope value.

        Returns:
            The normalized scope tuple.
        """
        return _normalize_scopes(value)

    def to_mcp_auth_settings(self) -> AuthSettings:
        """Return the FastMCP auth settings model.

        Returns:
            The auth settings expected by FastMCP's streamable HTTP transport.
        """
        return AuthSettings(
            issuer_url=self.issuer_url,
            resource_server_url=self.resource_server_url,
            required_scopes=list(self.required_scopes) or None,
        )


class DevelopmentHostedTokenRecord(BaseModel):
    """One development-only bearer token and its verified identity payload."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    token: SecretStr
    identity: HostedVerifiedIdentity

    @field_validator("token", mode="before")
    @classmethod
    def _validate_token(cls, value: object) -> object:
        """Require non-empty development bearer tokens.

        Args:
            value: The raw token value.

        Returns:
            The normalized token string for `SecretStr` validation.
        """
        if isinstance(value, SecretStr):
            return value
        if not isinstance(value, str):
            return value
        return _normalize_required_string(value, field_name="token")

    def token_value(self) -> str:
        """Return the raw development token string.

        Returns:
            The unwrapped bearer token value.
        """
        return self.token.get_secret_value()


class DevelopmentHostedTokenDocument(BaseModel):
    """Serialized seed data for the development hosted-token verifier."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    tokens: tuple[DevelopmentHostedTokenRecord, ...] = ()

    @model_validator(mode="after")
    def _validate_unique_tokens(self) -> Self:
        """Ensure development token values remain unique.

        Returns:
            The validated development-token document.

        Raises:
            ValueError: If the document contains duplicate token values.
        """
        duplicate_tokens = _duplicate_values([record.token_value() for record in self.tokens])
        if duplicate_tokens:
            raise ValueError(
                "Duplicate hosted bearer tokens are not allowed: "
                + ", ".join(duplicate_tokens)
                + "."
            )
        return self


class DevelopmentHostedTokenVerifier(HostedIdentityVerifier):
    """Development-safe hosted token verifier backed by in-memory seed data."""

    def __init__(self, *, tokens: Sequence[DevelopmentHostedTokenRecord]) -> None:
        """Initialize the development hosted-token verifier.

        Args:
            tokens: The development token records accepted by the verifier.
        """
        self._document = DevelopmentHostedTokenDocument.model_validate({"tokens": list(tokens)})
        self._identities_by_token = {
            record.token_value(): record.identity for record in self._document.tokens
        }

    async def verify_token(self, token: str) -> HostedVerifiedIdentity | None:
        """Resolve one known development token.

        Args:
            token: The raw bearer token from the inbound request.

        Returns:
            The verified hosted identity when the token is recognized, otherwise
            `None`.
        """
        return self._identities_by_token.get(token)

    def snapshot(self) -> DevelopmentHostedTokenDocument:
        """Return the validated development-token document.

        Returns:
            The immutable development-token document backing this verifier.
        """
        return self._document

    @classmethod
    def from_mapping(cls, tokens: Mapping[str, HostedVerifiedIdentity]) -> Self:
        """Build a development verifier from a token-to-identity mapping.

        Args:
            tokens: Mapping of raw bearer token to verified hosted identity.

        Returns:
            A development hosted-token verifier built from the mapping.
        """
        return cls(
            tokens=[
                DevelopmentHostedTokenRecord.model_validate(
                    {
                        "token": token,
                        "identity": identity,
                    }
                )
                for token, identity in tokens.items()
            ]
        )


class HostedTenantTokenVerifier(TokenVerifier):
    """FastMCP token verifier that resolves active tenant context."""

    def __init__(
        self,
        *,
        identity_verifier: HostedIdentityVerifier,
        tenant_store: TenantStore,
    ) -> None:
        """Initialize the tenant-resolving FastMCP token verifier.

        Args:
            identity_verifier: The hosted token verifier that validates inbound
                bearer tokens and returns verified identity claims.
            tenant_store: The tenant store used to resolve the canonical
                `tenant_id` claim into one active tenant.
        """
        self._identity_verifier = identity_verifier
        self._tenant_store = tenant_store

    async def verify_token(self, token: str) -> HostedAccessToken | None:
        """Verify a hosted token and resolve active tenant context.

        Args:
            token: The raw bearer token from the inbound request.

        Returns:
            The hosted access token stored in FastMCP auth context when the
            request is authorized, otherwise `None`.
        """
        identity = await self._identity_verifier.verify_token(token)
        if identity is None:
            return None

        try:
            resolved = await self._tenant_store.resolve_tenant(identity.tenant_id)
        except TenantStoreError:
            return None

        if (
            identity.credential_id is not None
            and identity.credential_id != resolved.credential.credential_id
        ):
            return None

        tenant = HostedAuthenticatedTenant.from_resolved_tenant(resolved)
        return HostedAccessToken.from_verified_identity(
            token=token,
            identity=identity,
            tenant=tenant,
        )


def get_hosted_access_token() -> HostedAccessToken | None:
    """Return the current FastMCP access token when hosted auth is active.

    Returns:
        The hosted access token stored in auth context, otherwise `None`.
    """
    access_token = get_access_token()
    if isinstance(access_token, HostedAccessToken):
        return access_token
    return None


def get_hosted_verified_identity() -> HostedVerifiedIdentity | None:
    """Return the verified hosted identity from the current auth context.

    Returns:
        The verified hosted identity when hosted auth is active, otherwise
        `None`.
    """
    access_token = get_hosted_access_token()
    if access_token is None:
        return None
    return access_token.identity


def get_hosted_authenticated_tenant() -> HostedAuthenticatedTenant | None:
    """Return the authenticated tenant context from the current auth context.

    Returns:
        The authenticated tenant context when hosted auth is active, otherwise
        `None`.
    """
    access_token = get_hosted_access_token()
    if access_token is None:
        return None
    return access_token.tenant
