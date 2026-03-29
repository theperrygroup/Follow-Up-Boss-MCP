"""Grouped FastMCP registration helpers for the Follow Up Boss server."""

from __future__ import annotations

from pathlib import Path

from followupboss_mcp.mcp_tools import (
    DeleteAppointmentToolInput,
    DeleteDealToolInput,
    DeleteNoteToolInput,
    DeletePipelineToolInput,
    DeleteTaskToolInput,
    DeleteTemplateToolInput,
    DeleteTextMessageTemplateToolInput,
    DeleteWebhookToolInput,
    FollowUpBossToolAdapter,
    GetAppointmentToolInput,
    GetCallToolInput,
    GetDealToolInput,
    GetEventToolInput,
    GetNoteToolInput,
    GetPersonToolInput,
    GetPipelineToolInput,
    GetTaskToolInput,
    GetTemplateToolInput,
    GetTextMessageTemplateToolInput,
    GetTextMessageToolInput,
    GetUserToolInput,
    GetWebhookToolInput,
    UpdateAppointmentToolInput,
    UpdateCallToolInput,
    UpdateDealToolInput,
    UpdateNoteToolInput,
    UpdatePersonToolInput,
    UpdatePipelineToolInput,
    UpdateTaskToolInput,
    UpdateTemplateToolInput,
    UpdateTextMessageTemplateToolInput,
)
from followupboss_mcp.models.appointments import AppointmentListRequest, CreateAppointmentRequest
from followupboss_mcp.models.calls import CallListRequest, CreateCallRequest
from followupboss_mcp.models.custom_fields import CustomFieldListRequest
from followupboss_mcp.models.deals import (
    CreateDealRequest,
    DealCustomFieldListRequest,
    DealListRequest,
)
from followupboss_mcp.models.events import CreateEventRequest, EventSearchRequest
from followupboss_mcp.models.notes import CreateNoteRequest
from followupboss_mcp.models.people import CreatePersonRequest, PeopleSearchRequest
from followupboss_mcp.models.pipelines import (
    CreatePipelineRequest,
    PipelineListRequest,
    PipelineStageInput,
)
from followupboss_mcp.models.tasks import CreateTaskRequest, TaskListRequest
from followupboss_mcp.models.templates import CreateTemplateRequest, TemplateListRequest
from followupboss_mcp.models.text_messages import (
    CreateTextMessageTemplateRequest,
    TextMessageListRequest,
    TextMessageTemplateListRequest,
)
from followupboss_mcp.models.users import UserListRequest
from followupboss_mcp.models.webhooks import CreateWebhookRequest, WebhookListRequest
from mcp.server.fastmcp import FastMCP


def register_server_surface(
    mcp: FastMCP,
    adapter: FollowUpBossToolAdapter,
    *,
    project_root: Path,
) -> None:
    """Register the complete Follow Up Boss MCP surface.

    Args:
        mcp: The FastMCP server instance to extend.
        adapter: The typed MCP adapter that delegates to domain services.
        project_root: The repository root used for resource-backed content.
    """
    _register_identity_tools(mcp, adapter)
    _register_people_tools(mcp, adapter)
    _register_event_tools(mcp, adapter)
    _register_user_tools(mcp, adapter)
    _register_custom_field_tools(mcp, adapter)
    _register_deal_tools(mcp, adapter)
    _register_appointment_tools(mcp, adapter)
    _register_call_tools(mcp, adapter)
    _register_pipeline_tools(mcp, adapter)
    _register_task_tools(mcp, adapter)
    _register_template_tools(mcp, adapter)
    _register_text_message_tools(mcp, adapter)
    _register_note_tools(mcp, adapter)
    _register_webhook_tools(mcp, adapter)
    _register_resources_and_prompts(mcp, project_root=project_root)


def _register_identity_tools(mcp: FastMCP, adapter: FollowUpBossToolAdapter) -> None:
    """Register identity-related MCP tools.

    Args:
        mcp: The FastMCP server instance.
        adapter: The typed Follow Up Boss tool adapter.
    """

    @mcp.tool(
        name="followupboss_get_identity",
        description=(
            "Return identity information for the authenticated Follow Up Boss user and account."
        ),
    )
    async def followupboss_get_identity() -> dict[str, object]:
        return await adapter.get_identity()


def _register_people_tools(mcp: FastMCP, adapter: FollowUpBossToolAdapter) -> None:
    """Register people-related MCP tools.

    Args:
        mcp: The FastMCP server instance.
        adapter: The typed Follow Up Boss tool adapter.
    """

    @mcp.tool(
        name="followupboss_search_people",
        description=(
            "Search Follow Up Boss people with documented query parameters and pagination metadata."
        ),
    )
    async def followupboss_search_people(
        *,
        fields: list[str] | None = None,
        id: int | None = None,
        ids: list[int] | None = None,
        id_greater_than: int | None = None,
        id_less_than: int | None = None,
        limit: int | None = None,
        next_token: str | None = None,
        offset: int | None = None,
        sort: str | None = None,
        assigned_user_id: int | None = None,
        email: str | None = None,
        first_name: str | None = None,
        include_trash: bool | None = None,
        last_name: str | None = None,
        name: str | None = None,
        phone: str | None = None,
        source: str | None = None,
        stage: str | None = None,
        custom_field_filters: dict[str, str] | None = None,
    ) -> dict[str, object]:
        tool_input = PeopleSearchRequest(
            fields=fields,
            id=id,
            ids=ids,
            id_greater_than=id_greater_than,
            id_less_than=id_less_than,
            limit=limit,
            next_token=next_token,
            offset=offset,
            sort=sort,
            assigned_user_id=assigned_user_id,
            email=email,
            first_name=first_name,
            include_trash=include_trash,
            last_name=last_name,
            name=name,
            phone=phone,
            source=source,
            stage=stage,
            custom_field_filters=custom_field_filters,
        )
        return await adapter.search_people(tool_input)

    @mcp.tool(
        name="followupboss_get_person",
        description="Fetch a single Follow Up Boss person by ID.",
    )
    async def followupboss_get_person(
        person_id: int,
        *,
        fields: list[str] | None = None,
    ) -> dict[str, object]:
        return await adapter.get_person(GetPersonToolInput(person_id=person_id, fields=fields))

    @mcp.tool(
        name="followupboss_create_person",
        description=(
            "Create a Follow Up Boss person directly. "
            "Use followupboss_send_event for canonical lead ingestion."
        ),
    )
    async def followupboss_create_person(
        *,
        addresses: list[dict[str, object]] | None = None,
        assigned_lender_id: int | None = None,
        assigned_lender_name: str | None = None,
        assigned_pond_id: int | None = None,
        assigned_to: str | None = None,
        assigned_user_id: int | None = None,
        background: str | None = None,
        collaborators: list[int] | None = None,
        contacted: bool | None = None,
        created_at: str | None = None,
        custom_fields: dict[str, object] | None = None,
        deduplicate: bool | None = None,
        emails: list[dict[str, object]] | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        phones: list[dict[str, object]] | None = None,
        price: int | None = None,
        source: str | None = None,
        source_url: str | None = None,
        stage: str | None = None,
        tags: list[str] | None = None,
        timeframe_id: int | None = None,
    ) -> dict[str, object]:
        tool_input = CreatePersonRequest.model_validate(
            {
                "addresses": addresses,
                "assigned_lender_id": assigned_lender_id,
                "assigned_lender_name": assigned_lender_name,
                "assigned_pond_id": assigned_pond_id,
                "assigned_to": assigned_to,
                "assigned_user_id": assigned_user_id,
                "background": background,
                "collaborators": collaborators,
                "contacted": contacted,
                "created_at": created_at,
                "custom_fields": custom_fields,
                "deduplicate": deduplicate,
                "emails": emails,
                "first_name": first_name,
                "last_name": last_name,
                "phones": phones,
                "price": price,
                "source": source,
                "source_url": source_url,
                "stage": stage,
                "tags": tags,
                "timeframe_id": timeframe_id,
            }
        )
        return await adapter.create_person(tool_input)

    @mcp.tool(
        name="followupboss_update_person",
        description="Update a single Follow Up Boss person by ID.",
    )
    async def followupboss_update_person(
        person_id: int,
        *,
        addresses: list[dict[str, object]] | None = None,
        assigned_lender_id: int | None = None,
        assigned_lender_name: str | None = None,
        assigned_pond_id: int | None = None,
        assigned_to: str | None = None,
        assigned_user_id: int | None = None,
        background: str | None = None,
        contacted: bool | None = None,
        custom_fields: dict[str, object] | None = None,
        emails: list[dict[str, object]] | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        merge_tags: bool | None = None,
        phones: list[dict[str, object]] | None = None,
        price: int | None = None,
        stage: str | None = None,
        tags: list[str] | None = None,
        timeframe_id: int | None = None,
    ) -> dict[str, object]:
        tool_input = UpdatePersonToolInput.model_validate(
            {
                "person_id": person_id,
                "addresses": addresses,
                "assigned_lender_id": assigned_lender_id,
                "assigned_lender_name": assigned_lender_name,
                "assigned_pond_id": assigned_pond_id,
                "assigned_to": assigned_to,
                "assigned_user_id": assigned_user_id,
                "background": background,
                "contacted": contacted,
                "custom_fields": custom_fields,
                "emails": emails,
                "first_name": first_name,
                "last_name": last_name,
                "merge_tags": merge_tags,
                "phones": phones,
                "price": price,
                "stage": stage,
                "tags": tags,
                "timeframe_id": timeframe_id,
            }
        )
        return await adapter.update_person(tool_input)


def _register_event_tools(mcp: FastMCP, adapter: FollowUpBossToolAdapter) -> None:
    """Register event-related MCP tools.

    Args:
        mcp: The FastMCP server instance.
        adapter: The typed Follow Up Boss tool adapter.
    """

    @mcp.tool(
        name="followupboss_search_events",
        description="Search Follow Up Boss events with pagination metadata.",
    )
    async def followupboss_search_events(
        *,
        limit: int | None = None,
        next_token: str | None = None,
        offset: int | None = None,
        person_id: int | None = None,
        type: list[str] | None = None,
        has_property: bool | None = None,
        property_address: str | None = None,
    ) -> dict[str, object]:
        return await adapter.search_events(
            EventSearchRequest(
                limit=limit,
                next_token=next_token,
                offset=offset,
                person_id=person_id,
                type=type,
                has_property=has_property,
                property_address=property_address,
            )
        )

    @mcp.tool(
        name="followupboss_get_event",
        description="Fetch a single Follow Up Boss event by ID.",
    )
    async def followupboss_get_event(event_id: int) -> dict[str, object]:
        return await adapter.get_event(GetEventToolInput(event_id=event_id))

    @mcp.tool(
        name="followupboss_send_event",
        description=(
            "Send a canonical Follow Up Boss lead or lead-activity event through POST /events."
        ),
    )
    async def followupboss_send_event(
        source: str,
        system: str,
        type: str,
        person: dict[str, object],
        *,
        campaign: dict[str, object] | None = None,
        description: str | None = None,
        message: str | None = None,
        occurred_at: str | None = None,
        page_duration: int | None = None,
        page_referrer: str | None = None,
        page_title: str | None = None,
        page_url: str | None = None,
        property: dict[str, object] | None = None,
        property_search: dict[str, object] | None = None,
    ) -> dict[str, object]:
        tool_input = CreateEventRequest.model_validate(
            {
                "source": source,
                "system": system,
                "type": type,
                "person": person,
                "campaign": campaign,
                "description": description,
                "message": message,
                "occurred_at": occurred_at,
                "page_duration": page_duration,
                "page_referrer": page_referrer,
                "page_title": page_title,
                "page_url": page_url,
                "property": property,
                "property_search": property_search,
            }
        )
        return await adapter.send_event(tool_input)


def _register_user_tools(mcp: FastMCP, adapter: FollowUpBossToolAdapter) -> None:
    """Register user-related MCP tools.

    Args:
        mcp: The FastMCP server instance.
        adapter: The typed Follow Up Boss tool adapter.
    """

    @mcp.tool(
        name="followupboss_list_users",
        description="List Follow Up Boss users with pagination metadata.",
    )
    async def followupboss_list_users(
        *,
        fields: list[str] | None = None,
        id: int | None = None,
        ids: list[int] | None = None,
        id_greater_than: int | None = None,
        id_less_than: int | None = None,
        limit: int | None = None,
        next_token: str | None = None,
        offset: int | None = None,
        sort: str | None = None,
        email: str | None = None,
        include_deleted: bool | None = None,
        name: str | None = None,
        role: str | None = None,
    ) -> dict[str, object]:
        return await adapter.list_users(
            UserListRequest(
                fields=fields,
                id=id,
                ids=ids,
                id_greater_than=id_greater_than,
                id_less_than=id_less_than,
                limit=limit,
                next_token=next_token,
                offset=offset,
                sort=sort,
                email=email,
                include_deleted=include_deleted,
                name=name,
                role=role,
            )
        )

    @mcp.tool(
        name="followupboss_get_user",
        description="Fetch a single Follow Up Boss user by ID.",
    )
    async def followupboss_get_user(user_id: int) -> dict[str, object]:
        return await adapter.get_user(GetUserToolInput(user_id=user_id))


def _register_custom_field_tools(mcp: FastMCP, adapter: FollowUpBossToolAdapter) -> None:
    """Register custom-field-related MCP tools.

    Args:
        mcp: The FastMCP server instance.
        adapter: The typed Follow Up Boss tool adapter.
    """

    @mcp.tool(
        name="followupboss_list_custom_fields",
        description="List custom fields for the authenticated Follow Up Boss account.",
    )
    async def followupboss_list_custom_fields(
        *,
        fields: list[str] | None = None,
        id: int | None = None,
        ids: list[int] | None = None,
        id_greater_than: int | None = None,
        id_less_than: int | None = None,
        label: str | None = None,
        limit: int | None = None,
        next_token: str | None = None,
        offset: int | None = None,
        sort: str | None = None,
    ) -> dict[str, object]:
        return await adapter.list_custom_fields(
            CustomFieldListRequest(
                fields=fields,
                id=id,
                ids=ids,
                id_greater_than=id_greater_than,
                id_less_than=id_less_than,
                label=label,
                limit=limit,
                next_token=next_token,
                offset=offset,
                sort=sort,
            )
        )


def _register_deal_tools(mcp: FastMCP, adapter: FollowUpBossToolAdapter) -> None:
    """Register deal-related MCP tools.

    Args:
        mcp: The FastMCP server instance.
        adapter: The typed Follow Up Boss tool adapter.
    """

    @mcp.tool(
        name="followupboss_list_deals",
        description="List Follow Up Boss deals with documented filters and pagination metadata.",
    )
    async def followupboss_list_deals(
        *,
        include_archived: bool | None = None,
        include_deleted: bool | None = None,
        person_id: int | None = None,
        pipeline_id: int | None = None,
        status: str | None = None,
        user_id: int | None = None,
    ) -> dict[str, object]:
        return await adapter.list_deals(
            DealListRequest(
                include_archived=include_archived,
                include_deleted=include_deleted,
                person_id=person_id,
                pipeline_id=pipeline_id,
                status=status,
                user_id=user_id,
            )
        )

    @mcp.tool(
        name="followupboss_get_deal",
        description="Fetch a single Follow Up Boss deal by ID.",
    )
    async def followupboss_get_deal(deal_id: int) -> dict[str, object]:
        return await adapter.get_deal(GetDealToolInput(deal_id=deal_id))

    @mcp.tool(
        name="followupboss_create_deal",
        description="Create a Follow Up Boss deal.",
    )
    async def followupboss_create_deal(
        name: str,
        stage_id: int,
        *,
        agent_commission: int | None = None,
        commission_value: int | None = None,
        custom_fields: dict[str, object] | None = None,
        description: str | None = None,
        due_diligence_date: str | None = None,
        earnest_money_due_date: str | None = None,
        final_walk_through_date: str | None = None,
        mutual_acceptance_date: str | None = None,
        order_weight: int | None = None,
        people_ids: list[int] | None = None,
        possession_date: str | None = None,
        price: int | None = None,
        projected_close_date: str | None = None,
        team_commission: int | None = None,
        user_ids: list[int] | None = None,
    ) -> dict[str, object]:
        return await adapter.create_deal(
            CreateDealRequest.model_validate(
                {
                    "name": name,
                    "stage_id": stage_id,
                    "agent_commission": agent_commission,
                    "commission_value": commission_value,
                    "custom_fields": custom_fields,
                    "description": description,
                    "due_diligence_date": due_diligence_date,
                    "earnest_money_due_date": earnest_money_due_date,
                    "final_walk_through_date": final_walk_through_date,
                    "mutual_acceptance_date": mutual_acceptance_date,
                    "order_weight": order_weight,
                    "people_ids": people_ids,
                    "possession_date": possession_date,
                    "price": price,
                    "projected_close_date": projected_close_date,
                    "team_commission": team_commission,
                    "user_ids": user_ids,
                }
            )
        )

    @mcp.tool(
        name="followupboss_update_deal",
        description="Update a Follow Up Boss deal by ID.",
    )
    async def followupboss_update_deal(
        deal_id: int,
        *,
        agent_commission: int | None = None,
        commission_value: int | None = None,
        custom_fields: dict[str, object] | None = None,
        description: str | None = None,
        due_diligence_date: str | None = None,
        earnest_money_due_date: str | None = None,
        final_walk_through_date: str | None = None,
        mutual_acceptance_date: str | None = None,
        name: str | None = None,
        people_ids: list[int] | None = None,
        possession_date: str | None = None,
        price: int | None = None,
        projected_close_date: str | None = None,
        stage_id: int | None = None,
        team_commission: int | None = None,
        user_ids: list[int] | None = None,
    ) -> dict[str, object]:
        return await adapter.update_deal(
            UpdateDealToolInput.model_validate(
                {
                    "deal_id": deal_id,
                    "agent_commission": agent_commission,
                    "commission_value": commission_value,
                    "custom_fields": custom_fields,
                    "description": description,
                    "due_diligence_date": due_diligence_date,
                    "earnest_money_due_date": earnest_money_due_date,
                    "final_walk_through_date": final_walk_through_date,
                    "mutual_acceptance_date": mutual_acceptance_date,
                    "name": name,
                    "people_ids": people_ids,
                    "possession_date": possession_date,
                    "price": price,
                    "projected_close_date": projected_close_date,
                    "stage_id": stage_id,
                    "team_commission": team_commission,
                    "user_ids": user_ids,
                }
            )
        )

    @mcp.tool(
        name="followupboss_delete_deal",
        description="Delete a Follow Up Boss deal by ID.",
    )
    async def followupboss_delete_deal(deal_id: int) -> dict[str, object]:
        return await adapter.delete_deal(DeleteDealToolInput(deal_id=deal_id))

    @mcp.tool(
        name="followupboss_list_deal_custom_fields",
        description="List Follow Up Boss deal custom fields with pagination metadata.",
    )
    async def followupboss_list_deal_custom_fields(
        *,
        label: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
        sort: str | None = None,
    ) -> dict[str, object]:
        return await adapter.list_deal_custom_fields(
            DealCustomFieldListRequest(
                label=label,
                limit=limit,
                offset=offset,
                sort=sort,
            )
        )


def _register_appointment_tools(mcp: FastMCP, adapter: FollowUpBossToolAdapter) -> None:
    """Register appointment-related MCP tools.

    Args:
        mcp: The FastMCP server instance.
        adapter: The typed Follow Up Boss tool adapter.
    """

    @mcp.tool(
        name="followupboss_list_appointments",
        description=(
            "List Follow Up Boss appointments with documented filters and pagination metadata."
        ),
    )
    async def followupboss_list_appointments(
        *,
        end: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
        person_id: int | list[int] | None = None,
        start: str | None = None,
        user_id: int | None = None,
    ) -> dict[str, object]:
        return await adapter.list_appointments(
            AppointmentListRequest.model_validate(
                {
                    "end": end,
                    "limit": limit,
                    "offset": offset,
                    "person_id": person_id,
                    "start": start,
                    "user_id": user_id,
                }
            )
        )

    @mcp.tool(
        name="followupboss_get_appointment",
        description="Fetch a single Follow Up Boss appointment by ID.",
    )
    async def followupboss_get_appointment(appointment_id: int) -> dict[str, object]:
        return await adapter.get_appointment(GetAppointmentToolInput(appointment_id=appointment_id))

    @mcp.tool(
        name="followupboss_create_appointment",
        description="Create a Follow Up Boss appointment.",
    )
    async def followupboss_create_appointment(
        title: str,
        start: str,
        end: str,
        *,
        all_day: bool | None = None,
        created_by_id: int | None = None,
        description: str | None = None,
        invitees: list[dict[str, object]] | None = None,
        location: str | None = None,
        outcome_id: int | None = None,
        send_invitation: bool | None = None,
        type_id: int | None = None,
    ) -> dict[str, object]:
        return await adapter.create_appointment(
            CreateAppointmentRequest.model_validate(
                {
                    "title": title,
                    "start": start,
                    "end": end,
                    "all_day": all_day,
                    "created_by_id": created_by_id,
                    "description": description,
                    "invitees": invitees,
                    "location": location,
                    "outcome_id": outcome_id,
                    "send_invitation": send_invitation,
                    "type_id": type_id,
                }
            )
        )

    @mcp.tool(
        name="followupboss_update_appointment",
        description="Update a Follow Up Boss appointment by ID.",
    )
    async def followupboss_update_appointment(
        appointment_id: int,
        *,
        title: str,
        start: str,
        end: str,
        all_day: bool | None = None,
        description: str | None = None,
        invitees: list[dict[str, object]] | None = None,
        location: str | None = None,
        outcome_id: int | None = None,
        send_invitation: bool | None = None,
        type_id: int | None = None,
    ) -> dict[str, object]:
        return await adapter.update_appointment(
            UpdateAppointmentToolInput.model_validate(
                {
                    "appointment_id": appointment_id,
                    "title": title,
                    "start": start,
                    "end": end,
                    "all_day": all_day,
                    "description": description,
                    "invitees": invitees,
                    "location": location,
                    "outcome_id": outcome_id,
                    "send_invitation": send_invitation,
                    "type_id": type_id,
                }
            )
        )

    @mcp.tool(
        name="followupboss_delete_appointment",
        description="Delete a Follow Up Boss appointment by ID.",
    )
    async def followupboss_delete_appointment(appointment_id: int) -> dict[str, object]:
        return await adapter.delete_appointment(
            DeleteAppointmentToolInput(appointment_id=appointment_id)
        )


def _register_call_tools(mcp: FastMCP, adapter: FollowUpBossToolAdapter) -> None:
    """Register call-related MCP tools.

    Args:
        mcp: The FastMCP server instance.
        adapter: The typed Follow Up Boss tool adapter.
    """

    @mcp.tool(
        name="followupboss_list_calls",
        description="List Follow Up Boss calls with documented filters and pagination metadata.",
    )
    async def followupboss_list_calls(
        *,
        from_number: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
        person_id: int | None = None,
        phone: str | None = None,
        to_number: str | None = None,
    ) -> dict[str, object]:
        return await adapter.list_calls(
            CallListRequest(
                from_number=from_number,
                limit=limit,
                offset=offset,
                person_id=person_id,
                phone=phone,
                to_number=to_number,
            )
        )

    @mcp.tool(
        name="followupboss_get_call",
        description="Fetch a single Follow Up Boss call by ID.",
    )
    async def followupboss_get_call(call_id: int) -> dict[str, object]:
        return await adapter.get_call(GetCallToolInput(call_id=call_id))

    @mcp.tool(
        name="followupboss_create_call",
        description="Create a Follow Up Boss call log entry.",
    )
    async def followupboss_create_call(
        person_id: int,
        phone: str,
        is_incoming: bool,
        *,
        duration: int | None = None,
        from_number: str | None = None,
        note: str | None = None,
        outcome: str | None = None,
        recording_url: str | None = None,
        to_number: str | None = None,
        user_id: int | None = None,
    ) -> dict[str, object]:
        return await adapter.create_call(
            CreateCallRequest(
                person_id=person_id,
                phone=phone,
                is_incoming=is_incoming,
                duration=duration,
                from_number=from_number,
                note=note,
                outcome=outcome,
                recording_url=recording_url,
                to_number=to_number,
                user_id=user_id,
            )
        )

    @mcp.tool(
        name="followupboss_update_call",
        description="Update a Follow Up Boss call log entry by ID.",
    )
    async def followupboss_update_call(
        call_id: int,
        *,
        duration: int | None = None,
        from_number: str | None = None,
        is_incoming: bool | None = None,
        note: str | None = None,
        outcome: str | None = None,
        person_id: int | None = None,
        phone: str | None = None,
        recording_url: str | None = None,
        to_number: str | None = None,
        user_id: int | None = None,
    ) -> dict[str, object]:
        return await adapter.update_call(
            UpdateCallToolInput(
                call_id=call_id,
                duration=duration,
                from_number=from_number,
                is_incoming=is_incoming,
                note=note,
                outcome=outcome,
                person_id=person_id,
                phone=phone,
                recording_url=recording_url,
                to_number=to_number,
                user_id=user_id,
            )
        )


def _register_pipeline_tools(mcp: FastMCP, adapter: FollowUpBossToolAdapter) -> None:
    """Register pipeline-related MCP tools.

    Args:
        mcp: The FastMCP server instance.
        adapter: The typed Follow Up Boss tool adapter.
    """

    @mcp.tool(
        name="followupboss_list_pipelines",
        description=(
            "List Follow Up Boss pipelines with exact-name filtering and pagination metadata."
        ),
    )
    async def followupboss_list_pipelines(*, name: str | None = None) -> dict[str, object]:
        return await adapter.list_pipelines(PipelineListRequest(name=name))

    @mcp.tool(
        name="followupboss_get_pipeline",
        description="Fetch a single Follow Up Boss pipeline by ID.",
    )
    async def followupboss_get_pipeline(pipeline_id: int) -> dict[str, object]:
        return await adapter.get_pipeline(GetPipelineToolInput(pipeline_id=pipeline_id))

    @mcp.tool(
        name="followupboss_create_pipeline",
        description="Create a Follow Up Boss pipeline. Owner permissions are required upstream.",
    )
    async def followupboss_create_pipeline(
        name: str,
        *,
        description: str | None = None,
        order_weight: int | None = None,
        stages: list[dict[str, object]] | None = None,
    ) -> dict[str, object]:
        stage_inputs = (
            [PipelineStageInput.model_validate(stage) for stage in stages]
            if stages is not None
            else None
        )
        return await adapter.create_pipeline(
            CreatePipelineRequest(
                name=name,
                description=description,
                order_weight=order_weight,
                stages=stage_inputs,
            )
        )

    @mcp.tool(
        name="followupboss_update_pipeline",
        description=(
            "Update a Follow Up Boss pipeline by ID. Owner permissions are required upstream."
        ),
    )
    async def followupboss_update_pipeline(
        pipeline_id: int,
        *,
        description: str | None = None,
        name: str | None = None,
        order_weight: int | None = None,
        stages: list[dict[str, object]] | None = None,
    ) -> dict[str, object]:
        stage_inputs = (
            [PipelineStageInput.model_validate(stage) for stage in stages]
            if stages is not None
            else None
        )
        return await adapter.update_pipeline(
            UpdatePipelineToolInput(
                pipeline_id=pipeline_id,
                name=name,
                description=description,
                order_weight=order_weight,
                stages=stage_inputs,
            )
        )

    @mcp.tool(
        name="followupboss_delete_pipeline",
        description=(
            "Delete a Follow Up Boss pipeline by ID. Owner permissions are required upstream."
        ),
    )
    async def followupboss_delete_pipeline(pipeline_id: int) -> dict[str, object]:
        return await adapter.delete_pipeline(DeletePipelineToolInput(pipeline_id=pipeline_id))


def _register_task_tools(mcp: FastMCP, adapter: FollowUpBossToolAdapter) -> None:
    """Register task-related MCP tools.

    Args:
        mcp: The FastMCP server instance.
        adapter: The typed Follow Up Boss tool adapter.
    """

    @mcp.tool(
        name="followupboss_list_tasks",
        description="List Follow Up Boss tasks with documented filters and pagination metadata.",
    )
    async def followupboss_list_tasks(
        *,
        fields: list[str] | None = None,
        id: int | None = None,
        ids: list[int] | None = None,
        id_greater_than: int | None = None,
        id_less_than: int | None = None,
        limit: int | None = None,
        next_token: str | None = None,
        offset: int | None = None,
        sort: str | None = None,
        assigned_to: str | None = None,
        assigned_user_id: int | None = None,
        due: str | None = None,
        due_end: str | None = None,
        due_start: str | None = None,
        is_completed: bool | None = None,
        name: str | None = None,
        person_id: int | None = None,
        type: list[str] | None = None,
    ) -> dict[str, object]:
        return await adapter.list_tasks(
            TaskListRequest.model_validate(
                {
                    "fields": fields,
                    "id": id,
                    "ids": ids,
                    "id_greater_than": id_greater_than,
                    "id_less_than": id_less_than,
                    "limit": limit,
                    "next_token": next_token,
                    "offset": offset,
                    "sort": sort,
                    "assigned_to": assigned_to,
                    "assigned_user_id": assigned_user_id,
                    "due": due,
                    "due_end": due_end,
                    "due_start": due_start,
                    "is_completed": is_completed,
                    "name": name,
                    "person_id": person_id,
                    "type": type,
                }
            )
        )

    @mcp.tool(
        name="followupboss_get_task",
        description="Fetch a single Follow Up Boss task by ID.",
    )
    async def followupboss_get_task(task_id: int) -> dict[str, object]:
        return await adapter.get_task(GetTaskToolInput(task_id=task_id))

    @mcp.tool(
        name="followupboss_create_task",
        description="Create a Follow Up Boss task.",
    )
    async def followupboss_create_task(
        person_id: int,
        *,
        assigned_to: str | None = None,
        assigned_user_id: int | None = None,
        due_date: str | None = None,
        due_date_time: str | None = None,
        is_completed: bool | None = None,
        name: str | None = None,
        remind_seconds_before: int | None = None,
        type: str | None = None,
    ) -> dict[str, object]:
        tool_input = CreateTaskRequest.model_validate(
            {
                "person_id": person_id,
                "assigned_to": assigned_to,
                "assigned_user_id": assigned_user_id,
                "due_date": due_date,
                "due_date_time": due_date_time,
                "is_completed": is_completed,
                "name": name,
                "remind_seconds_before": remind_seconds_before,
                "type": type,
            }
        )
        return await adapter.create_task(tool_input)

    @mcp.tool(
        name="followupboss_update_task",
        description="Update a Follow Up Boss task by ID.",
    )
    async def followupboss_update_task(
        task_id: int,
        *,
        assigned_to: str | None = None,
        assigned_user_id: int | None = None,
        due_date: str | None = None,
        due_date_time: str | None = None,
        is_completed: bool | None = None,
        name: str | None = None,
        person_id: int | None = None,
        type: str | None = None,
    ) -> dict[str, object]:
        return await adapter.update_task(
            UpdateTaskToolInput.model_validate(
                {
                    "task_id": task_id,
                    "assigned_to": assigned_to,
                    "assigned_user_id": assigned_user_id,
                    "due_date": due_date,
                    "due_date_time": due_date_time,
                    "is_completed": is_completed,
                    "name": name,
                    "person_id": person_id,
                    "type": type,
                }
            )
        )

    @mcp.tool(
        name="followupboss_delete_task",
        description="Delete a Follow Up Boss task by ID.",
    )
    async def followupboss_delete_task(task_id: int) -> dict[str, object]:
        return await adapter.delete_task(DeleteTaskToolInput(task_id=task_id))


def _register_template_tools(mcp: FastMCP, adapter: FollowUpBossToolAdapter) -> None:
    """Register template-related MCP tools.

    Args:
        mcp: The FastMCP server instance.
        adapter: The typed Follow Up Boss tool adapter.
    """

    @mcp.tool(
        name="followupboss_list_templates",
        description="List Follow Up Boss email templates with pagination metadata.",
    )
    async def followupboss_list_templates(
        *,
        limit: int | None = None,
        offset: int | None = None,
    ) -> dict[str, object]:
        return await adapter.list_templates(
            TemplateListRequest(
                limit=limit,
                offset=offset,
            )
        )

    @mcp.tool(
        name="followupboss_get_template",
        description="Fetch a single Follow Up Boss email template by ID.",
    )
    async def followupboss_get_template(
        template_id: int,
        *,
        merge_person_id: int | None = None,
    ) -> dict[str, object]:
        return await adapter.get_template(
            GetTemplateToolInput(template_id=template_id, merge_person_id=merge_person_id)
        )

    @mcp.tool(
        name="followupboss_create_template",
        description="Create a Follow Up Boss email template.",
    )
    async def followupboss_create_template(
        name: str,
        subject: str,
        body: str,
        *,
        is_shared: bool | None = None,
    ) -> dict[str, object]:
        return await adapter.create_template(
            CreateTemplateRequest(
                name=name,
                subject=subject,
                body=body,
                is_shared=is_shared,
            )
        )

    @mcp.tool(
        name="followupboss_update_template",
        description="Update a Follow Up Boss email template by ID.",
    )
    async def followupboss_update_template(
        template_id: int,
        *,
        name: str,
        subject: str,
        body: str,
    ) -> dict[str, object]:
        return await adapter.update_template(
            UpdateTemplateToolInput(
                template_id=template_id,
                name=name,
                subject=subject,
                body=body,
            )
        )

    @mcp.tool(
        name="followupboss_delete_template",
        description="Delete a Follow Up Boss email template by ID.",
    )
    async def followupboss_delete_template(template_id: int) -> dict[str, object]:
        return await adapter.delete_template(DeleteTemplateToolInput(template_id=template_id))


def _register_text_message_tools(mcp: FastMCP, adapter: FollowUpBossToolAdapter) -> None:
    """Register text message and text message template MCP tools.

    Args:
        mcp: The FastMCP server instance.
        adapter: The typed Follow Up Boss tool adapter.
    """

    @mcp.tool(
        name="followupboss_list_text_messages",
        description=(
            "List Follow Up Boss text messages with documented filters and pagination metadata."
        ),
    )
    async def followupboss_list_text_messages(
        *,
        from_number: str | None = None,
        person_id: int | None = None,
        to_number: str | None = None,
    ) -> dict[str, object]:
        return await adapter.list_text_messages(
            TextMessageListRequest(
                from_number=from_number,
                person_id=person_id,
                to_number=to_number,
            )
        )

    @mcp.tool(
        name="followupboss_get_text_message",
        description="Fetch a single Follow Up Boss text message by ID.",
    )
    async def followupboss_get_text_message(text_message_id: int) -> dict[str, object]:
        return await adapter.get_text_message(
            GetTextMessageToolInput(text_message_id=text_message_id)
        )

    @mcp.tool(
        name="followupboss_list_text_message_templates",
        description="List Follow Up Boss text message templates with pagination metadata.",
    )
    async def followupboss_list_text_message_templates(
        *,
        limit: int | None = None,
        offset: int | None = None,
    ) -> dict[str, object]:
        return await adapter.list_text_message_templates(
            TextMessageTemplateListRequest(limit=limit, offset=offset)
        )

    @mcp.tool(
        name="followupboss_get_text_message_template",
        description="Fetch a single Follow Up Boss text message template by ID.",
    )
    async def followupboss_get_text_message_template(template_id: int) -> dict[str, object]:
        return await adapter.get_text_message_template(
            GetTextMessageTemplateToolInput(template_id=template_id)
        )

    @mcp.tool(
        name="followupboss_create_text_message_template",
        description="Create a Follow Up Boss text message template.",
    )
    async def followupboss_create_text_message_template(
        name: str,
        message: str,
        *,
        is_shared: bool | None = None,
    ) -> dict[str, object]:
        return await adapter.create_text_message_template(
            CreateTextMessageTemplateRequest(
                name=name,
                message=message,
                is_shared=is_shared,
            )
        )

    @mcp.tool(
        name="followupboss_update_text_message_template",
        description="Update a Follow Up Boss text message template by ID.",
    )
    async def followupboss_update_text_message_template(
        template_id: int,
        *,
        name: str,
        message: str,
        is_shared: bool | None = None,
    ) -> dict[str, object]:
        return await adapter.update_text_message_template(
            UpdateTextMessageTemplateToolInput(
                template_id=template_id,
                name=name,
                message=message,
                is_shared=is_shared,
            )
        )

    @mcp.tool(
        name="followupboss_delete_text_message_template",
        description="Delete a Follow Up Boss text message template by ID.",
    )
    async def followupboss_delete_text_message_template(template_id: int) -> dict[str, object]:
        return await adapter.delete_text_message_template(
            DeleteTextMessageTemplateToolInput(template_id=template_id)
        )


def _register_note_tools(mcp: FastMCP, adapter: FollowUpBossToolAdapter) -> None:
    """Register note-related MCP tools.

    Args:
        mcp: The FastMCP server instance.
        adapter: The typed Follow Up Boss tool adapter.
    """

    @mcp.tool(
        name="followupboss_add_note",
        description=(
            "Create a Follow Up Boss note for a person, optionally waiting "
            "for person visibility first."
        ),
    )
    async def followupboss_add_note(
        person_id: int,
        *,
        body: str | None = None,
        is_html: bool | None = None,
        subject: str | None = None,
        wait_for_person: bool = False,
    ) -> dict[str, object]:
        return await adapter.add_note(
            CreateNoteRequest(
                body=body,
                is_html=is_html,
                person_id=person_id,
                subject=subject,
            ),
            wait_for_person=wait_for_person,
        )

    @mcp.tool(
        name="followupboss_get_note",
        description="Fetch a Follow Up Boss note by ID.",
    )
    async def followupboss_get_note(note_id: int) -> dict[str, object]:
        return await adapter.get_note(GetNoteToolInput(note_id=note_id))

    @mcp.tool(
        name="followupboss_update_note",
        description="Update a Follow Up Boss note by ID.",
    )
    async def followupboss_update_note(
        note_id: int,
        *,
        body: str | None = None,
        is_html: bool | None = None,
        subject: str | None = None,
    ) -> dict[str, object]:
        return await adapter.update_note(
            UpdateNoteToolInput(
                note_id=note_id,
                body=body,
                is_html=is_html,
                subject=subject,
            )
        )

    @mcp.tool(
        name="followupboss_delete_note",
        description="Delete a Follow Up Boss note by ID.",
    )
    async def followupboss_delete_note(note_id: int) -> dict[str, object]:
        return await adapter.delete_note(DeleteNoteToolInput(note_id=note_id))


def _register_webhook_tools(mcp: FastMCP, adapter: FollowUpBossToolAdapter) -> None:
    """Register webhook-related MCP tools.

    Args:
        mcp: The FastMCP server instance.
        adapter: The typed Follow Up Boss tool adapter.
    """

    @mcp.tool(
        name="followupboss_list_webhooks",
        description="List registered Follow Up Boss webhooks with pagination metadata.",
    )
    async def followupboss_list_webhooks(
        *,
        fields: list[str] | None = None,
        id: int | None = None,
        ids: list[int] | None = None,
        id_greater_than: int | None = None,
        id_less_than: int | None = None,
        limit: int | None = None,
        next_token: str | None = None,
        offset: int | None = None,
        sort: str | None = None,
        event: str | None = None,
        status: str | None = None,
    ) -> dict[str, object]:
        return await adapter.list_webhooks(
            WebhookListRequest(
                fields=fields,
                id=id,
                ids=ids,
                id_greater_than=id_greater_than,
                id_less_than=id_less_than,
                limit=limit,
                next_token=next_token,
                offset=offset,
                sort=sort,
                event=event,
                status=status,
            )
        )

    @mcp.tool(
        name="followupboss_get_webhook",
        description="Fetch a single Follow Up Boss webhook by ID.",
    )
    async def followupboss_get_webhook(webhook_id: int) -> dict[str, object]:
        return await adapter.get_webhook(GetWebhookToolInput(webhook_id=webhook_id))

    @mcp.tool(
        name="followupboss_create_webhook",
        description="Create a Follow Up Boss webhook for a documented event name.",
    )
    async def followupboss_create_webhook(event: str, url: str) -> dict[str, object]:
        return await adapter.create_webhook(CreateWebhookRequest(event=event, url=url))

    @mcp.tool(
        name="followupboss_delete_webhook",
        description="Delete a Follow Up Boss webhook by ID.",
    )
    async def followupboss_delete_webhook(webhook_id: int) -> dict[str, object]:
        return await adapter.delete_webhook(DeleteWebhookToolInput(webhook_id=webhook_id))


def _register_resources_and_prompts(mcp: FastMCP, *, project_root: Path) -> None:
    """Register MCP resources and prompts.

    Args:
        mcp: The FastMCP server instance.
        project_root: The repository root used for file-backed resources.
    """

    @mcp.resource(
        "followupboss://api-coverage-matrix",
        title="Follow Up Boss API Coverage Matrix",
        description="Repository API coverage matrix for Follow Up Boss endpoints.",
        mime_type="text/markdown",
    )
    def followupboss_api_coverage_matrix() -> str:
        return (project_root / "docs" / "api-coverage-matrix.md").read_text(encoding="utf-8")

    @mcp.prompt(
        name="followupboss_compose_lead_event",
        description="Compose a canonical POST /events payload for a new lead or lead activity.",
    )
    def followupboss_compose_lead_event(
        source: str,
        type: str,
        message: str,
        email: str,
        *,
        first_name: str = "",
        last_name: str = "",
    ) -> str:
        return (
            "Create a Follow Up Boss POST /events payload using the canonical "
            "lead-ingestion path.\n\n"
            f"source: {source}\n"
            f"type: {type}\n"
            f"message: {message}\n"
            f"email: {email}\n"
            f"first_name: {first_name}\n"
            f"last_name: {last_name}\n\n"
            "Return JSON with top-level source, system, type, message, and a nested person object."
        )
