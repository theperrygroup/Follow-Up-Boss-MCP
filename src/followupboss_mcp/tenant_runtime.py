"""Tenant runtime models and request-scoped service-bundle factories."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from dataclasses import dataclass
from typing import Protocol

from pydantic import BaseModel, ConfigDict

from followupboss_mcp.config import (
    FollowUpBossSettings,
    FollowUpBossTenantRuntimeDefaults,
    FollowUpBossTenantSettings,
)
from followupboss_mcp.errors import TenantStoreError
from followupboss_mcp.hosted_auth import (
    HostedAuthenticatedTenant,
    get_hosted_authenticated_tenant,
)
from followupboss_mcp.http_client import FollowUpBossAsyncClient, FollowUpBossClientProtocol
from followupboss_mcp.logging import emit_audit_event
from followupboss_mcp.services.action_plans import ActionPlansService
from followupboss_mcp.services.appointment_metadata import (
    AppointmentOutcomesService,
    AppointmentTypesService,
)
from followupboss_mcp.services.appointments import AppointmentsService
from followupboss_mcp.services.attachments import (
    DealAttachmentsService,
    PersonAttachmentsService,
)
from followupboss_mcp.services.automations import (
    AutomationPeopleService,
    AutomationsService,
)
from followupboss_mcp.services.calls import CallsService
from followupboss_mcp.services.custom_fields import CustomFieldsService
from followupboss_mcp.services.deals import DealsService
from followupboss_mcp.services.email_marketing import EmailMarketingService
from followupboss_mcp.services.events import EventsService
from followupboss_mcp.services.groups import GroupsService
from followupboss_mcp.services.identity import IdentityService
from followupboss_mcp.services.inbox_apps import InboxAppsService
from followupboss_mcp.services.notes import NotesService
from followupboss_mcp.services.people import PeopleService
from followupboss_mcp.services.people_relationships import PeopleRelationshipsService
from followupboss_mcp.services.pipelines import PipelinesService
from followupboss_mcp.services.ponds import PondsService
from followupboss_mcp.services.reactions import ReactionsService
from followupboss_mcp.services.smart_lists import SmartListsService
from followupboss_mcp.services.stages import StagesService
from followupboss_mcp.services.tasks import TasksService
from followupboss_mcp.services.team_inboxes import TeamInboxesService
from followupboss_mcp.services.teams import TeamsService
from followupboss_mcp.services.templates import TemplatesService
from followupboss_mcp.services.text_messages import (
    TextMessagesService,
    TextMessageTemplatesService,
)
from followupboss_mcp.services.threaded_replies import ThreadedRepliesService
from followupboss_mcp.services.timeframes import TimeframesService
from followupboss_mcp.services.users import UsersService
from followupboss_mcp.services.webhooks import WebhooksService
from followupboss_mcp.tenant_store import (
    ResolvedTenantCredentials,
    TenantCredentialRecord,
    TenantStore,
)

type TenantClientFactory = Callable[
    [FollowUpBossTenantSettings, logging.Logger | None],
    FollowUpBossClientProtocol,
]


@dataclass(frozen=True)
class ServiceBundle:
    """Service bundle used by the MCP tool adapter."""

    action_plans: ActionPlansService
    appointments: AppointmentsService
    appointment_outcomes: AppointmentOutcomesService
    appointment_types: AppointmentTypesService
    automation_people: AutomationPeopleService
    automations: AutomationsService
    calls: CallsService
    custom_fields: CustomFieldsService
    deal_attachments: DealAttachmentsService
    deals: DealsService
    email_marketing: EmailMarketingService
    events: EventsService
    groups: GroupsService
    identity: IdentityService
    inbox_apps: InboxAppsService
    notes: NotesService
    people: PeopleService
    person_attachments: PersonAttachmentsService
    people_relationships: PeopleRelationshipsService
    ponds: PondsService
    pipelines: PipelinesService
    reactions: ReactionsService
    smart_lists: SmartListsService
    stages: StagesService
    tasks: TasksService
    team_inboxes: TeamInboxesService
    teams: TeamsService
    text_message_templates: TextMessageTemplatesService
    text_messages: TextMessagesService
    templates: TemplatesService
    threaded_replies: ThreadedRepliesService
    timeframes: TimeframesService
    users: UsersService
    webhooks: WebhooksService


class TenantRuntime(BaseModel):
    """Resolved tenant identity plus client settings for one tool call."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    tenant: HostedAuthenticatedTenant
    settings: FollowUpBossTenantSettings


def _upstream_usage_audit_fields(runtime: TenantRuntime) -> dict[str, object]:
    """Return non-secret audit fields for upstream credential usage.

    Args:
        runtime: The request-scoped tenant runtime being used to build an
            upstream client.

    Returns:
        A dictionary of stable, non-secret audit fields describing which tenant
        credential is being used to access Follow Up Boss.
    """
    return {
        "tenant_id": runtime.tenant.tenant_id,
        "tenant_slug": runtime.tenant.tenant_slug,
        "credential_id": runtime.tenant.credential_id,
        "auth_mode": runtime.settings.auth_mode,
        "system_name": runtime.settings.system_name,
        "has_system_key": runtime.settings.system_key is not None,
    }


def build_service_bundle(client: FollowUpBossClientProtocol) -> ServiceBundle:
    """Create the typed service bundle used by the MCP adapter.

    Args:
        client: The Follow Up Boss client implementation backing every service.

    Returns:
        A fully wired service bundle that shares the same transport client.
    """
    people_service = PeopleService(client)
    return ServiceBundle(
        action_plans=ActionPlansService(client),
        appointments=AppointmentsService(client),
        appointment_outcomes=AppointmentOutcomesService(client),
        appointment_types=AppointmentTypesService(client),
        automation_people=AutomationPeopleService(client),
        automations=AutomationsService(client),
        calls=CallsService(client),
        custom_fields=CustomFieldsService(client),
        deal_attachments=DealAttachmentsService(client),
        deals=DealsService(client),
        email_marketing=EmailMarketingService(client),
        events=EventsService(client),
        groups=GroupsService(client),
        identity=IdentityService(client),
        inbox_apps=InboxAppsService(client),
        notes=NotesService(client, people_service=people_service),
        people=people_service,
        person_attachments=PersonAttachmentsService(client),
        people_relationships=PeopleRelationshipsService(client),
        ponds=PondsService(client),
        pipelines=PipelinesService(client),
        reactions=ReactionsService(client),
        smart_lists=SmartListsService(client),
        stages=StagesService(client),
        tasks=TasksService(client),
        team_inboxes=TeamInboxesService(client),
        teams=TeamsService(client),
        text_message_templates=TextMessageTemplatesService(client),
        text_messages=TextMessagesService(client),
        templates=TemplatesService(client),
        threaded_replies=ThreadedRepliesService(client),
        timeframes=TimeframesService(client),
        users=UsersService(client),
        webhooks=WebhooksService(client),
    )


class ServiceBundleResolver(Protocol):
    """Protocol for resolving the active service bundle on demand."""

    def service_bundle(self) -> AbstractAsyncContextManager[ServiceBundle]:
        """Return a context manager yielding the active service bundle.

        Returns:
            An async context manager that yields one usable service bundle.
        """


class StaticServiceBundleResolver:
    """Resolver that always returns the same prebuilt service bundle."""

    def __init__(self, services: ServiceBundle) -> None:
        """Initialize the static service-bundle resolver.

        Args:
            services: The shared service bundle returned for every resolution.
        """
        self._services = services

    @asynccontextmanager
    async def service_bundle(self) -> AsyncIterator[ServiceBundle]:
        """Yield the shared service bundle without creating new clients.

        Yields:
            The same prebuilt service bundle for every call.
        """
        yield self._services


class TenantRuntimeFactory:
    """Build request-scoped tenant runtimes from hosted auth context."""

    def __init__(
        self,
        *,
        default_settings: (
            FollowUpBossTenantRuntimeDefaults | FollowUpBossTenantSettings | FollowUpBossSettings
        ),
        tenant_store: TenantStore,
        logger: logging.Logger | None = None,
        client_factory: TenantClientFactory | None = None,
    ) -> None:
        """Initialize the tenant runtime factory.

        Args:
            default_settings: Non-secret Follow Up Boss client defaults whose
                `base_url`, `timeout_seconds`, and `max_retries` are inherited by
                every tenant runtime while credentials come from the tenant
                store.
            tenant_store: Store used to re-resolve active tenant credentials for
                each authenticated call.
            logger: Optional logger forwarded to created HTTP clients.
            client_factory: Optional client factory used mainly by focused tests.
        """
        if isinstance(default_settings, FollowUpBossTenantSettings):
            resolved_default_settings = default_settings.tenant_runtime_defaults()
        else:
            resolved_default_settings = default_settings
        self._default_settings = resolved_default_settings
        self._tenant_store = tenant_store
        self._logger = logger
        self._client_factory = client_factory or self._default_client_factory

    def settings_from_credential(
        self,
        credential: TenantCredentialRecord,
    ) -> FollowUpBossTenantSettings:
        """Project one stored credential into client settings.

        Args:
            credential: The stored tenant credential record.

        Returns:
            Tenant-specific client settings combining the stored credential
            material with the shared transport defaults.
        """
        return FollowUpBossTenantSettings.model_validate(
            {
                "auth_mode": credential.auth_mode,
                "api_key": credential.api_key,
                "access_token": credential.access_token,
                "system_name": credential.system_name,
                "system_key": credential.system_key,
                "base_url": self._default_settings.base_url,
                "timeout_seconds": self._default_settings.timeout_seconds,
                "max_retries": self._default_settings.max_retries,
            }
        )

    def runtime_from_resolved_tenant(
        self,
        resolved: ResolvedTenantCredentials,
        *,
        authenticated_tenant: HostedAuthenticatedTenant | None = None,
    ) -> TenantRuntime:
        """Build one runtime model from a resolved tenant record.

        Args:
            resolved: The resolved tenant and credential pair.
            authenticated_tenant: Optional tenant context already stored in the
                auth middleware. When omitted, a fresh auth-safe tenant context is
                projected from the resolved records.

        Returns:
            The request-scoped tenant runtime model.
        """
        return TenantRuntime.model_validate(
            {
                "tenant": (
                    authenticated_tenant or HostedAuthenticatedTenant.from_resolved_tenant(resolved)
                ),
                "settings": self.settings_from_credential(resolved.credential),
            }
        )

    async def runtime_from_authenticated_tenant(
        self,
        authenticated_tenant: HostedAuthenticatedTenant,
    ) -> TenantRuntime:
        """Re-resolve a hosted tenant context into a request-scoped runtime.

        Args:
            authenticated_tenant: The non-secret tenant context stored by hosted
                authentication.

        Returns:
            The request-scoped tenant runtime model for the current call.

        Raises:
            TenantStoreError: If the tenant or its credential can no longer be
                resolved.
        """
        resolved = await self._tenant_store.resolve_tenant_credential(
            tenant_id=authenticated_tenant.tenant_id,
            credential_id=authenticated_tenant.credential_id,
        )
        return self.runtime_from_resolved_tenant(
            resolved,
            authenticated_tenant=authenticated_tenant,
        )

    async def runtime_for_current_tenant(self) -> TenantRuntime:
        """Resolve the request-scoped tenant runtime for the current auth context.

        Returns:
            The request-scoped tenant runtime model for the current hosted call.

        Raises:
            RuntimeError: If hosted tenant context is unavailable or can no longer
                be resolved safely.
        """
        authenticated_tenant = get_hosted_authenticated_tenant()
        if authenticated_tenant is None:
            raise RuntimeError("Hosted tenant runtime is unavailable.")
        try:
            return await self.runtime_from_authenticated_tenant(authenticated_tenant)
        except TenantStoreError as exc:
            raise RuntimeError("Hosted tenant runtime is unavailable.") from exc

    def create_client(self, runtime: TenantRuntime) -> FollowUpBossClientProtocol:
        """Create one Follow Up Boss client for the resolved tenant runtime.

        Args:
            runtime: The request-scoped tenant runtime model.

        Returns:
            A Follow Up Boss client configured for the tenant.
        """
        emit_audit_event(
            self._logger,
            event="upstream_credential_usage",
            fields=_upstream_usage_audit_fields(runtime),
        )
        return self._client_factory(runtime.settings, self._logger)

    @asynccontextmanager
    async def service_bundle_for_tenant(
        self,
        authenticated_tenant: HostedAuthenticatedTenant,
    ) -> AsyncIterator[ServiceBundle]:
        """Create and clean up one tenant-specific service bundle.

        Args:
            authenticated_tenant: The authenticated tenant context for the
                current tool call.

        Yields:
            A freshly built service bundle backed by a tenant-specific client.
        """
        runtime = await self.runtime_from_authenticated_tenant(authenticated_tenant)
        client = self.create_client(runtime)
        try:
            yield build_service_bundle(client)
        finally:
            await client.aclose()

    @asynccontextmanager
    async def service_bundle_for_current_tenant(self) -> AsyncIterator[ServiceBundle]:
        """Resolve and yield the service bundle for the current auth context.

        Yields:
            A freshly built service bundle for the authenticated tenant.

        Raises:
            RuntimeError: If hosted tenant context is unavailable or can no
                longer be resolved safely.
        """
        runtime = await self.runtime_for_current_tenant()
        client = self.create_client(runtime)
        try:
            yield build_service_bundle(client)
        finally:
            await client.aclose()

    @staticmethod
    def _default_client_factory(
        settings: FollowUpBossTenantSettings,
        logger: logging.Logger | None,
    ) -> FollowUpBossClientProtocol:
        """Build the default Follow Up Boss async client implementation.

        Args:
            settings: The tenant-specific client settings.
            logger: Optional logger forwarded to the HTTP client.

        Returns:
            The default async Follow Up Boss client.
        """
        return FollowUpBossAsyncClient(settings, logger=logger)


class RequestScopedTenantServiceBundleResolver:
    """Resolver that creates one tenant-specific bundle per tool call."""

    def __init__(self, runtime_factory: TenantRuntimeFactory) -> None:
        """Initialize the request-scoped resolver.

        Args:
            runtime_factory: Factory used to resolve and create tenant-specific
                service bundles for each call.
        """
        self._runtime_factory = runtime_factory

    @asynccontextmanager
    async def service_bundle(self) -> AsyncIterator[ServiceBundle]:
        """Yield one request-scoped tenant service bundle.

        Yields:
            A tenant-specific service bundle for the current call.
        """
        async with self._runtime_factory.service_bundle_for_current_tenant() as services:
            yield services
