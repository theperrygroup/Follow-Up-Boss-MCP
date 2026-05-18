"""Focused unit tests for MCP helper surfaces and runtime-bound adapters."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import cast

import pytest

from followupboss_mcp.auth import AuthMode
from followupboss_mcp.config import FollowUpBossTenantSettings
from followupboss_mcp.hosted_auth import HostedAuthenticatedTenant
from followupboss_mcp.mcp_registration import (
    _format_hosted_surface_context,
    _render_api_coverage_matrix_resource,
    _render_compose_lead_event_prompt,
    _resolve_surface_runtime,
    _surface_runtime_resolution_error,
)
from followupboss_mcp.mcp_tools import FollowUpBossToolAdapter
from followupboss_mcp.tenant_runtime import ServiceBundle, TenantRuntime, TenantRuntimeFactory


def _tenant_runtime(*, display_name: str | None = "Tenant One") -> TenantRuntime:
    """Build a representative hosted tenant runtime for surface-helper tests.

    Args:
        display_name: Optional hosted tenant display name.

    Returns:
        A validated hosted tenant runtime.
    """
    return TenantRuntime.model_validate(
        {
            "tenant": HostedAuthenticatedTenant.model_validate(
                {
                    "tenant_id": "tenant-1",
                    "tenant_slug": "tenant-one",
                    "display_name": display_name,
                    "credential_id": "credential-1",
                }
            ),
            "settings": FollowUpBossTenantSettings.model_validate(
                {
                    "auth_mode": AuthMode.API_KEY,
                    "api_key": "secret-key",
                }
            ),
        }
    )


def test_surface_context_renderers_include_hosted_runtime_details() -> None:
    """MCP resource and prompt helpers should append only safe hosted tenant context."""
    runtime = _tenant_runtime(display_name=None)
    context_block = _format_hosted_surface_context(runtime)

    assert (
        context_block == "Hosted tenant context:\ntenant_slug: tenant-one\ndisplay_name: tenant-one"
    )
    assert (
        _render_api_coverage_matrix_resource(resource_text="Coverage", runtime=None) == "Coverage"
    )
    assert _render_api_coverage_matrix_resource(resource_text="Coverage\n", runtime=runtime) == (
        "Coverage\n\n---\n\nHosted tenant context:\n"
        "tenant_slug: tenant-one\ndisplay_name: tenant-one\n"
    )

    rendered_prompt = _render_compose_lead_event_prompt(
        source="Portal",
        type="Inquiry",
        message="Hello there",
        email="lead@example.com",
        first_name="Taylor",
        last_name="Agent",
        runtime=runtime,
    )

    assert "Use the authenticated hosted tenant context below" in rendered_prompt
    assert "tenant_slug: tenant-one" in rendered_prompt
    assert "display_name: tenant-one" in rendered_prompt
    assert _render_compose_lead_event_prompt(
        source="Portal",
        type="Inquiry",
        message="Hello there",
        email="lead@example.com",
        first_name="Taylor",
        last_name="Agent",
        runtime=None,
    ).startswith("Create a Follow Up Boss POST /events payload")


@pytest.mark.asyncio
async def test_resolve_surface_runtime_handles_disabled_public_and_failure_paths() -> None:
    """Surface runtime resolution should fail closed with MCP-safe errors."""

    class StaticRuntimeFactory:
        """Return one fixed runtime for every hosted surface request."""

        async def runtime_for_current_tenant(self) -> TenantRuntime:
            """Return the fixed test runtime."""
            return _tenant_runtime()

    class FailingRuntimeFactory:
        """Raise an unsafe runtime error that should be sanitized."""

        async def runtime_for_current_tenant(self) -> TenantRuntime:
            """Raise an unsafe exception for sanitization coverage."""
            raise RuntimeError("Hosted tenant runtime is unavailable. token=super-secret-token")

    assert _surface_runtime_resolution_error().args == ("Hosted tenant runtime is unavailable.",)
    assert (
        await _resolve_surface_runtime(
            surface_name="followupboss://public",
            public_surface_names=frozenset({"followupboss://public"}),
            tenant_runtime_factory=cast(TenantRuntimeFactory, StaticRuntimeFactory()),
        )
        is None
    )
    assert (
        await _resolve_surface_runtime(
            surface_name="followupboss://private",
            public_surface_names=frozenset(),
            tenant_runtime_factory=None,
        )
        is None
    )
    resolved_runtime = await _resolve_surface_runtime(
        surface_name="followupboss://private",
        public_surface_names=frozenset(),
        tenant_runtime_factory=cast(TenantRuntimeFactory, StaticRuntimeFactory()),
    )
    assert resolved_runtime == _tenant_runtime()

    with pytest.raises(RuntimeError, match="Hosted tenant runtime is unavailable.") as exc_info:
        await _resolve_surface_runtime(
            surface_name="followupboss://private",
            public_surface_names=frozenset(),
            tenant_runtime_factory=cast(TenantRuntimeFactory, FailingRuntimeFactory()),
        )
    assert "super-secret-token" not in str(exc_info.value)
    assert exc_info.value.__cause__ is None


def test_tool_adapter_requires_active_runtime_for_resolver_backed_services() -> None:
    """Resolver-backed tool adapters should fail closed without an active runtime bundle."""

    class UnusedResolver:
        """Resolver stub that should not be entered for this failure path."""

        @asynccontextmanager
        async def service_bundle(self) -> AsyncIterator[ServiceBundle]:
            """Raise if the test accidentally enters the resolver context."""
            raise AssertionError("The resolver should not be used for this test.")
            yield cast(ServiceBundle, object())

    adapter = FollowUpBossToolAdapter(UnusedResolver())

    with pytest.raises(RuntimeError, match="Tenant runtime is unavailable."):
        _ = adapter._services
