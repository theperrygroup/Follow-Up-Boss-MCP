"""Tenant-store abstractions and local-development implementations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from enum import StrEnum
from pathlib import Path
from typing import Self

from pydantic import (
    BaseModel,
    ConfigDict,
    SecretStr,
    ValidationInfo,
    field_validator,
    model_validator,
)

from followupboss_mcp.auth import AuthMode, AuthStrategy, build_auth_strategy
from followupboss_mcp.config import FollowUpBossSettings, FollowUpBossTenantSettings
from followupboss_mcp.errors import (
    TenantCredentialNotFoundError,
    TenantCredentialRevokedError,
    TenantDisabledError,
    TenantNotFoundError,
)

_DEFAULT_LOCAL_DEV_CREDENTIAL_ID = "local-dev-credential"
_DEFAULT_LOCAL_DEV_DISPLAY_NAME = "Local Development"
_DEFAULT_LOCAL_DEV_TENANT_ID = "local-dev"
_DEFAULT_LOCAL_DEV_TENANT_SLUG = "local-dev"


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


class TenantStatus(StrEnum):
    """Lifecycle states for hosted tenant records."""

    ACTIVE = "active"
    DISABLED = "disabled"


class TenantCredentialStatus(StrEnum):
    """Lifecycle states for stored tenant credentials."""

    ACTIVE = "active"
    REVOKED = "revoked"


class TenantRecord(BaseModel):
    """Stable tenant metadata used to resolve hosted callers safely."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    tenant_id: str
    tenant_slug: str
    display_name: str | None = None
    credential_id: str
    status: TenantStatus = TenantStatus.ACTIVE

    @field_validator("tenant_id", "tenant_slug", "credential_id")
    @classmethod
    def _validate_identifiers(cls, value: str, info: ValidationInfo) -> str:
        """Require non-empty tenant identifiers.

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
        """Normalize optional display names.

        Args:
            value: The raw display-name value.

        Returns:
            The normalized display name or `None`.
        """
        return _normalize_optional_string(value)


class TenantCredentialRecord(BaseModel):
    """Stored Follow Up Boss credential material for one hosted tenant."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    credential_id: str
    tenant_id: str
    auth_mode: AuthMode
    api_key: SecretStr | None = None
    access_token: SecretStr | None = None
    system_name: str | None = None
    system_key: SecretStr | None = None
    status: TenantCredentialStatus = TenantCredentialStatus.ACTIVE

    @field_validator("credential_id", "tenant_id")
    @classmethod
    def _validate_identifiers(cls, value: str, info: ValidationInfo) -> str:
        """Require non-empty credential identifiers.

        Args:
            value: The raw field value.
            info: Validation context for the current field.

        Returns:
            The normalized identifier.
        """
        return _normalize_required_string(value, field_name=info.field_name or "field")

    @field_validator("system_name", mode="before")
    @classmethod
    def _validate_system_name(cls, value: object) -> object:
        """Normalize optional registered-system names.

        Args:
            value: The raw system-name value.

        Returns:
            The normalized system name or `None`.
        """
        return _normalize_optional_string(value)

    @model_validator(mode="after")
    def _validate_selected_secret(self) -> Self:
        """Ensure the selected auth mode has corresponding secret material.

        Returns:
            The validated credential record.

        Raises:
            ValueError: If the selected auth mode is missing its required secret.
        """
        if self.auth_mode is AuthMode.API_KEY and self.api_key is None:
            raise ValueError("api_key must be provided for api_key auth.")
        if self.auth_mode is AuthMode.OAUTH and self.access_token is None:
            raise ValueError("access_token must be provided for oauth auth.")
        return self

    def auth_strategy(self) -> AuthStrategy:
        """Return the auth strategy implied by this credential record.

        Returns:
            The Follow Up Boss auth strategy derived from the stored secret
            payload.
        """
        return build_auth_strategy(
            auth_mode=self.auth_mode,
            api_key=self.api_key.get_secret_value() if self.api_key is not None else None,
            access_token=self.access_token.get_secret_value()
            if self.access_token is not None
            else None,
        )

    def system_key_value(self) -> str | None:
        """Return the registered-system key, if present.

        Returns:
            The unwrapped system key when configured, otherwise `None`.
        """
        if self.system_key is None:
            return None
        return self.system_key.get_secret_value()

    @classmethod
    def from_tenant_settings(
        cls,
        settings: FollowUpBossTenantSettings | FollowUpBossSettings,
        *,
        credential_id: str,
        tenant_id: str,
        status: TenantCredentialStatus = TenantCredentialStatus.ACTIVE,
    ) -> Self:
        """Build a stored credential record from existing local-dev settings.

        Args:
            settings: The current single-tenant settings object.
            credential_id: The stable identifier to assign to the stored
                credential payload.
            tenant_id: The tenant that owns this credential.
            status: The lifecycle state to assign to the stored credential.

        Returns:
            A credential record compatible with the tenant-store abstraction.
        """
        return cls.model_validate(
            {
                "credential_id": credential_id,
                "tenant_id": tenant_id,
                "auth_mode": settings.auth_mode,
                "api_key": settings.api_key,
                "access_token": settings.access_token,
                "system_name": settings.system_name,
                "system_key": settings.system_key,
                "status": status,
            }
        )


class ResolvedTenantCredentials(BaseModel):
    """Resolved tenant metadata paired with active credential material."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    tenant: TenantRecord
    credential: TenantCredentialRecord


class DevelopmentTenantStoreDocument(BaseModel):
    """Serialized seed data for the development tenant store."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    tenants: tuple[TenantRecord, ...] = ()
    credentials: tuple[TenantCredentialRecord, ...] = ()

    @model_validator(mode="after")
    def _validate_unique_identifiers(self) -> Self:
        """Ensure document-level identifiers remain unique.

        Returns:
            The validated development-store document.

        Raises:
            ValueError: If tenant IDs, tenant slugs, or credential IDs collide.
        """
        duplicate_tenant_ids = _duplicate_values([tenant.tenant_id for tenant in self.tenants])
        if duplicate_tenant_ids:
            raise ValueError(
                "Duplicate tenant_id values are not allowed: "
                + ", ".join(duplicate_tenant_ids)
                + "."
            )

        duplicate_tenant_slugs = _duplicate_values([tenant.tenant_slug for tenant in self.tenants])
        if duplicate_tenant_slugs:
            raise ValueError(
                "Duplicate tenant_slug values are not allowed: "
                + ", ".join(duplicate_tenant_slugs)
                + "."
            )

        duplicate_credential_ids = _duplicate_values(
            [credential.credential_id for credential in self.credentials]
        )
        if duplicate_credential_ids:
            raise ValueError(
                "Duplicate credential_id values are not allowed: "
                + ", ".join(duplicate_credential_ids)
                + "."
            )
        return self


class TenantStore(ABC):
    """Abstract tenant store used by hosted auth and runtime wiring."""

    @abstractmethod
    async def get_tenant(self, tenant_id: str) -> TenantRecord | None:
        """Look up one tenant record by its canonical identifier.

        Args:
            tenant_id: The stable hosted tenant identifier.

        Returns:
            The tenant record when one exists, otherwise `None`.
        """

    @abstractmethod
    async def get_credential(self, credential_id: str) -> TenantCredentialRecord | None:
        """Look up one stored credential record by identifier.

        Args:
            credential_id: The stable identifier for the stored credential.

        Returns:
            The credential record when one exists, otherwise `None`.
        """

    async def resolve_tenant(self, tenant_id: str) -> ResolvedTenantCredentials:
        """Resolve one active tenant and its active credential material.

        Args:
            tenant_id: The canonical hosted tenant identifier.

        Returns:
            The resolved tenant metadata and credential record.

        Raises:
            TenantNotFoundError: If the tenant ID does not exist.
            TenantDisabledError: If the tenant exists but is disabled.
            TenantCredentialNotFoundError: If the tenant's credential record is
                missing or belongs to another tenant.
            TenantCredentialRevokedError: If the tenant's credential exists but
                is revoked.
        """
        tenant = await self.get_tenant(tenant_id)
        if tenant is None:
            raise TenantNotFoundError("Tenant could not be resolved.")
        if tenant.status is TenantStatus.DISABLED:
            raise TenantDisabledError("Tenant is disabled.")

        credential = await self.get_credential(tenant.credential_id)
        if credential is None or credential.tenant_id != tenant.tenant_id:
            raise TenantCredentialNotFoundError("Tenant credentials could not be resolved.")
        if credential.status is TenantCredentialStatus.REVOKED:
            raise TenantCredentialRevokedError("Tenant credentials are revoked.")

        return ResolvedTenantCredentials(tenant=tenant, credential=credential)


class DevelopmentTenantStore(TenantStore):
    """Development-safe tenant store backed by validated in-memory records."""

    def __init__(
        self,
        *,
        tenants: Sequence[TenantRecord],
        credentials: Sequence[TenantCredentialRecord],
    ) -> None:
        """Initialize the development tenant store.

        Args:
            tenants: The tenant records available in the local development
                store.
            credentials: The credential records available in the local
                development store.
        """
        self._document = DevelopmentTenantStoreDocument.model_validate(
            {
                "tenants": list(tenants),
                "credentials": list(credentials),
            }
        )
        self._tenants_by_id = {tenant.tenant_id: tenant for tenant in self._document.tenants}
        self._credentials_by_id = {
            credential.credential_id: credential for credential in self._document.credentials
        }

    async def get_tenant(self, tenant_id: str) -> TenantRecord | None:
        """Look up one tenant record by identifier.

        Args:
            tenant_id: The stable hosted tenant identifier.

        Returns:
            The tenant record when one exists, otherwise `None`.
        """
        return self._tenants_by_id.get(tenant_id)

    async def get_credential(self, credential_id: str) -> TenantCredentialRecord | None:
        """Look up one credential record by identifier.

        Args:
            credential_id: The stable identifier for the stored credential.

        Returns:
            The credential record when one exists, otherwise `None`.
        """
        return self._credentials_by_id.get(credential_id)

    def snapshot(self) -> DevelopmentTenantStoreDocument:
        """Return the validated document backing this store.

        Returns:
            The immutable development-store document.
        """
        return self._document

    @classmethod
    def from_document(cls, document: DevelopmentTenantStoreDocument) -> Self:
        """Build a store from a validated development-store document.

        Args:
            document: The validated development-store document.

        Returns:
            A development tenant store backed by the document data.
        """
        return cls(tenants=document.tenants, credentials=document.credentials)

    @classmethod
    def from_json(cls, document_json: str) -> Self:
        """Build a store from a serialized JSON document.

        Args:
            document_json: The JSON payload representing the development store.

        Returns:
            A development tenant store loaded from the JSON payload.
        """
        document = DevelopmentTenantStoreDocument.model_validate_json(document_json)
        return cls.from_document(document)

    @classmethod
    def from_file(cls, path: str | Path) -> Self:
        """Build a store from a JSON document on disk.

        Args:
            path: The path to the JSON tenant-store document.

        Returns:
            A development tenant store loaded from the file.
        """
        document_path = Path(path).expanduser()
        return cls.from_json(document_path.read_text(encoding="utf-8"))

    @classmethod
    def from_local_dev_settings(
        cls,
        settings: FollowUpBossTenantSettings | FollowUpBossSettings,
        *,
        tenant_id: str = _DEFAULT_LOCAL_DEV_TENANT_ID,
        tenant_slug: str = _DEFAULT_LOCAL_DEV_TENANT_SLUG,
        display_name: str = _DEFAULT_LOCAL_DEV_DISPLAY_NAME,
        credential_id: str = _DEFAULT_LOCAL_DEV_CREDENTIAL_ID,
        tenant_status: TenantStatus = TenantStatus.ACTIVE,
        credential_status: TenantCredentialStatus = TenantCredentialStatus.ACTIVE,
    ) -> Self:
        """Wrap existing single-tenant settings in a development-safe store.

        Args:
            settings: The local single-tenant settings currently used by the
                repository's developer workflows.
            tenant_id: The canonical tenant identifier to expose through the
                development store.
            tenant_slug: The human-friendly tenant slug to expose through the
                development store.
            display_name: The optional display name for the development tenant.
            credential_id: The identifier to assign to the synthesized
                credential record.
            tenant_status: The lifecycle state to assign to the synthesized
                tenant record.
            credential_status: The lifecycle state to assign to the synthesized
                credential record.

        Returns:
            A development tenant store containing one synthesized tenant and one
            synthesized credential record.
        """
        tenant = TenantRecord.model_validate(
            {
                "tenant_id": tenant_id,
                "tenant_slug": tenant_slug,
                "display_name": display_name,
                "credential_id": credential_id,
                "status": tenant_status,
            }
        )
        credential = TenantCredentialRecord.from_tenant_settings(
            settings,
            credential_id=credential_id,
            tenant_id=tenant_id,
            status=credential_status,
        )
        return cls(tenants=[tenant], credentials=[credential])
