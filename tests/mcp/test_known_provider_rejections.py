"""Known Follow Up Boss request rejections reach callers as actionable tool errors."""

from __future__ import annotations

import json
from collections.abc import Callable

import httpx
import pytest
from pydantic import ValidationError

from followupboss_mcp.config import FollowUpBossSettings
from followupboss_mcp.errors import FollowUpBossValidationError
from followupboss_mcp.http_client import FollowUpBossAsyncClient
from followupboss_mcp.mcp_server import create_server
from followupboss_mcp.models.custom_fields import CustomFieldListRequest
from followupboss_mcp.models.tasks import TaskRecord
from followupboss_mcp.task_intents import task_projection_fields
from mcp.server.mcpserver.exceptions import ToolError, UnexpectedToolError

type Upstream = Callable[[httpx.Request], httpx.Response]

_DEEP_PAGINATION_MESSAGE = "Deep pagination disabled, use 'nextLink' url"
_NO_SUCH_SMART_LIST_MESSAGE = "Invalid value for 'smartListId' parameter, no such list."
_NO_SUCH_LENDER_MESSAGE = "Invalid value for 'assignedLenderName' field, no such user."
_CLOSED_STAGE_MESSAGE = "You cannot delete a closed stage from a pipeline"
_ZILLOW_SYNC_STAGE_MESSAGE = "Provided stage is not a valid Zillow Sync Stage"
_FOLLOWUPBOSS_DOCS_LINK = "https://docs.followupboss.com/pagination-guide"
_ZILLOW_SYNC_STAGE_TEXT = (
    "Provided stage is not a valid Zillow Sync Stage. Follow Up Boss accepts only a Zillow "
    "sync stage (a stage that matches a Zillow contact status) for a person who syncs with "
    "Zillow. Call followupboss_list_stages for the exact stage names, then pass a Zillow "
    "sync stage or leave stage out."
)
_DEEP_PAGINATION_TEXT = (
    "Deep pagination disabled, use 'nextLink' url. Follow Up Boss does not allow offset "
    "paging this deep. Narrow the request with filters (for example a person or phone "
    "number, or a date range where the tool has one) instead of paging deeper."
)
_TASK_TOOLS = (
    "followupboss_list_tasks",
    "followupboss_list_my_overdue_tasks",
    "followupboss_list_my_tasks_due_today",
    "followupboss_list_my_upcoming_tasks",
)


async def _call_tool(
    tool_name: str,
    arguments: dict[str, object],
    upstream: Upstream,
) -> dict[str, object]:
    """Call one registered tool through the real adapter, service, and HTTP client.

    Args:
        tool_name: The registered MCP tool name.
        arguments: Tool arguments sent by the MCP caller.
        upstream: Fake Follow Up Boss HTTP handler.

    Returns:
        The structured tool result.
    """
    settings = FollowUpBossSettings.model_validate({"api_key": "test-key", "max_retries": 0})
    async with httpx.AsyncClient(
        base_url=str(settings.base_url), transport=httpx.MockTransport(upstream)
    ) as http_client:
        client = FollowUpBossAsyncClient(settings, http_client=http_client)
        server = create_server(settings, client=client)
        result = await server.call_tool(tool_name, arguments)
    structured_content = getattr(result, "structured_content", None)
    assert isinstance(structured_content, dict)
    return structured_content


def _rejecting_upstream(requests: list[httpx.Request], error_message: str) -> Upstream:
    """Return a fake upstream that knows the caller and rejects everything else.

    Args:
        requests: List that records every upstream request.
        error_message: The Follow Up Boss ``errorMessage`` for the HTTP 400.

    Returns:
        The fake upstream handler.
    """

    def upstream(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path.endswith("/identity"):
            return httpx.Response(200, json={"id": 1})
        return httpx.Response(400, json={"errorMessage": error_message})

    return upstream


def _task_upstream(requests: list[httpx.Request], task: dict[str, object]) -> Upstream:
    """Return a fake upstream that serves the caller identity and one task row.

    Args:
        requests: List that records every upstream request.
        task: The task row Follow Up Boss returns.

    Returns:
        The fake upstream handler.
    """

    def upstream(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path.endswith(("/identity", "/me")):
            return httpx.Response(200, json={"id": 1})
        assert request.url.path.endswith("/tasks")
        return httpx.Response(
            200,
            json={"_metadata": {"limit": 25, "offset": 0, "total": 1}, "tasks": [task]},
        )

    return upstream


def _cause_chain(exc: BaseException) -> list[BaseException]:
    """Return an exception followed by every exception it was raised from.

    Args:
        exc: The outermost exception.

    Returns:
        The exception chain, outermost first.
    """
    chain: list[BaseException] = []
    current: BaseException | None = exc
    while current is not None:
        chain.append(current)
        current = current.__cause__
    return chain


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error_message",
    [_DEEP_PAGINATION_MESSAGE, f"{_DEEP_PAGINATION_MESSAGE}.", f" {_DEEP_PAGINATION_MESSAGE}. "],
)
async def test_list_calls_deep_pagination_returns_filter_guidance(error_message: str) -> None:
    """FUB's deep-offset rejection names the fix instead of an opaque crash."""
    requests: list[httpx.Request] = []

    with pytest.raises(ToolError) as exc_info:
        await _call_tool(
            "followupboss_list_calls",
            {"offset": 5000},
            _rejecting_upstream(requests, error_message),
        )

    assert not isinstance(exc_info.value, UnexpectedToolError)
    message = str(exc_info.value)
    assert f"{_DEEP_PAGINATION_MESSAGE}. Follow Up Boss does not allow offset paging" in message
    assert "Narrow the request with filters" in message
    assert "next_token" not in message
    assert any(isinstance(exc, FollowUpBossValidationError) for exc in _cause_chain(exc_info.value))
    assert len(requests) == 1
    assert requests[0].url.path.endswith("/calls")
    assert requests[0].url.params["offset"] == "5000"


@pytest.mark.asyncio
async def test_search_people_unknown_smart_list_points_to_list_smart_lists() -> None:
    """FUB's unknown smartListId rejection tells callers where to get a current id."""
    requests: list[httpx.Request] = []

    with pytest.raises(ToolError) as exc_info:
        await _call_tool(
            "followupboss_search_people",
            {"smart_list_id": 987654},
            _rejecting_upstream(requests, _NO_SUCH_SMART_LIST_MESSAGE),
        )

    assert not isinstance(exc_info.value, UnexpectedToolError)
    message = str(exc_info.value)
    assert (
        "Invalid value for 'smartListId' parameter, no such list. "
        "Call followupboss_list_smart_lists to get a current smart list id."
    ) in message
    assert any(isinstance(exc, FollowUpBossValidationError) for exc in _cause_chain(exc_info.value))
    assert [request.url.path.rsplit("/", 1)[-1] for request in requests] == ["identity", "people"]
    assert requests[1].url.params["smartListId"] == "987654"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("tool_name", "arguments", "method", "path_suffix"),
    [
        (
            "followupboss_update_person",
            {"person_id": 101, "assigned_lender_name": "Pat Example"},
            "PUT",
            "/people/101",
        ),
        (
            "followupboss_create_person",
            {"first_name": "Sam", "assigned_lender_name": "Pat Example"},
            "POST",
            "/people",
        ),
    ],
)
async def test_person_write_unknown_lender_name_points_to_list_users(
    tool_name: str,
    arguments: dict[str, object],
    method: str,
    path_suffix: str,
) -> None:
    """FUB's unknown lender-name rejection tells callers how to find the lender."""
    requests: list[httpx.Request] = []

    with pytest.raises(ToolError) as exc_info:
        await _call_tool(
            tool_name,
            arguments,
            _rejecting_upstream(requests, _NO_SUCH_LENDER_MESSAGE),
        )

    assert not isinstance(exc_info.value, UnexpectedToolError)
    assert (
        "Invalid value for 'assignedLenderName' field, no such user. "
        "Call followupboss_list_users (role Lender lists lenders) to get the lender's "
        "exact full name, or pass the lender's user id as assigned_lender_id."
    ) in str(exc_info.value)
    assert any(isinstance(exc, FollowUpBossValidationError) for exc in _cause_chain(exc_info.value))
    writes = [request for request in requests if request.method == method]
    assert len(writes) == 1
    assert writes[0].url.path.endswith(path_suffix)
    assert json.loads(writes[0].content)["assignedLenderName"] == "Pat Example"


@pytest.mark.asyncio
@pytest.mark.parametrize("error_message", [_CLOSED_STAGE_MESSAGE, f"{_CLOSED_STAGE_MESSAGE}."])
async def test_update_pipeline_closed_stage_removal_points_to_get_pipeline(
    error_message: str,
) -> None:
    """FUB's closed-stage rejection tells callers to keep the pipeline's closed stages."""
    requests: list[httpx.Request] = []

    with pytest.raises(ToolError) as exc_info:
        await _call_tool(
            "followupboss_update_pipeline",
            {"pipeline_id": 63, "stages": [{"id": 401, "name": "Lead", "closed_stage": False}]},
            _rejecting_upstream(requests, error_message),
        )

    assert not isinstance(exc_info.value, UnexpectedToolError)
    assert (
        "You cannot delete a closed stage from a pipeline. Follow Up Boss does not allow "
        "deleting a closed stage. Before updating a pipeline's stages, call "
        "followupboss_get_pipeline and keep every closed stage in stages (same id, "
        "name, and closed_stage true)."
    ) in str(exc_info.value)
    assert any(isinstance(exc, FollowUpBossValidationError) for exc in _cause_chain(exc_info.value))
    writes = [request for request in requests if request.method == "PUT"]
    assert len(writes) == 1
    assert writes[0].url.path.endswith("/pipelines/63")
    assert json.loads(writes[0].content)["stages"] == [
        {"closedStage": False, "id": 401, "name": "Lead"}
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error_message", [_ZILLOW_SYNC_STAGE_MESSAGE, f"{_ZILLOW_SYNC_STAGE_MESSAGE}."]
)
@pytest.mark.parametrize(
    ("tool_name", "arguments", "method", "path_suffix"),
    [
        (
            "followupboss_update_person",
            {"person_id": 101, "stage": "Hot Prospect"},
            "PUT",
            "/people/101",
        ),
        (
            "followupboss_create_person",
            {"first_name": "Sam", "stage": "Hot Prospect"},
            "POST",
            "/people",
        ),
    ],
)
async def test_person_write_non_zillow_sync_stage_points_to_list_stages(
    tool_name: str,
    arguments: dict[str, object],
    method: str,
    path_suffix: str,
    error_message: str,
) -> None:
    """FUB's Zillow sync stage rejection tells callers how to pick a stage it accepts."""
    requests: list[httpx.Request] = []

    with pytest.raises(ToolError) as exc_info:
        await _call_tool(tool_name, arguments, _rejecting_upstream(requests, error_message))

    assert not isinstance(exc_info.value, UnexpectedToolError)
    assert _ZILLOW_SYNC_STAGE_TEXT in str(exc_info.value)
    assert any(isinstance(exc, FollowUpBossValidationError) for exc in _cause_chain(exc_info.value))
    writes = [request for request in requests if request.method == method]
    assert len(writes) == 1
    assert writes[0].url.path.endswith(path_suffix)
    assert json.loads(writes[0].content)["stage"] == "Hot Prospect"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error_message",
    [
        f"{_DEEP_PAGINATION_MESSAGE} {_FOLLOWUPBOSS_DOCS_LINK}",
        f"{_DEEP_PAGINATION_MESSAGE} {_FOLLOWUPBOSS_DOCS_LINK}.",
        f" {_DEEP_PAGINATION_MESSAGE}.\n{_FOLLOWUPBOSS_DOCS_LINK} ",
    ],
)
async def test_search_people_deep_pagination_with_docs_link_returns_filter_guidance(
    error_message: str,
) -> None:
    """FUB's deep-offset rejection with a trailing docs link gets the same guidance."""
    requests: list[httpx.Request] = []

    with pytest.raises(ToolError) as exc_info:
        await _call_tool(
            "followupboss_search_people",
            {"offset": 5000},
            _rejecting_upstream(requests, error_message),
        )

    assert not isinstance(exc_info.value, UnexpectedToolError)
    message = str(exc_info.value)
    assert message.endswith(
        f"{_DEEP_PAGINATION_TEXT} Follow Up Boss docs: {_FOLLOWUPBOSS_DOCS_LINK}"
    )
    assert message.count(_FOLLOWUPBOSS_DOCS_LINK) == 1
    assert any(isinstance(exc, FollowUpBossValidationError) for exc in _cause_chain(exc_info.value))
    assert [request.url.path.rsplit("/", 1)[-1] for request in requests] == ["identity", "people"]
    assert requests[1].url.params["offset"] == "5000"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("error_message", "expected_text"),
    [
        (
            f"{_NO_SUCH_SMART_LIST_MESSAGE} {_FOLLOWUPBOSS_DOCS_LINK}",
            "Invalid value for 'smartListId' parameter, no such list. "
            "Call followupboss_list_smart_lists to get a current smart list id.",
        ),
        (
            f"{_NO_SUCH_LENDER_MESSAGE} {_FOLLOWUPBOSS_DOCS_LINK}",
            "Invalid value for 'assignedLenderName' field, no such user. "
            "Call followupboss_list_users (role Lender lists lenders) to get the lender's "
            "exact full name, or pass the lender's user id as assigned_lender_id.",
        ),
        (
            f"{_CLOSED_STAGE_MESSAGE} {_FOLLOWUPBOSS_DOCS_LINK}.",
            "You cannot delete a closed stage from a pipeline. Follow Up Boss does not allow "
            "deleting a closed stage. Before updating a pipeline's stages, call "
            "followupboss_get_pipeline and keep every closed stage in stages (same id, "
            "name, and closed_stage true).",
        ),
        (f"{_ZILLOW_SYNC_STAGE_MESSAGE} {_FOLLOWUPBOSS_DOCS_LINK}", _ZILLOW_SYNC_STAGE_TEXT),
    ],
)
async def test_known_rejections_with_docs_link_keep_their_guidance(
    error_message: str,
    expected_text: str,
) -> None:
    """Every known message keeps its guidance, and the docs link comes last."""
    requests: list[httpx.Request] = []

    with pytest.raises(ToolError) as exc_info:
        await _call_tool(
            "followupboss_list_calls",
            {"phone": "555-0100"},
            _rejecting_upstream(requests, error_message),
        )

    assert not isinstance(exc_info.value, UnexpectedToolError)
    assert str(exc_info.value).endswith(
        f"{expected_text} Follow Up Boss docs: {_FOLLOWUPBOSS_DOCS_LINK}"
    )
    assert any(isinstance(exc, FollowUpBossValidationError) for exc in _cause_chain(exc_info.value))
    assert len(requests) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error_message",
    [
        f"{_DEEP_PAGINATION_MESSAGE} https://example.com/pagination-guide",
        f"{_DEEP_PAGINATION_MESSAGE} http://docs.followupboss.com/pagination-guide",
        f"{_DEEP_PAGINATION_MESSAGE} {_FOLLOWUPBOSS_DOCS_LINK} for more detail",
        f"{_DEEP_PAGINATION_MESSAGE}{_FOLLOWUPBOSS_DOCS_LINK}",
        f"{_DEEP_PAGINATION_MESSAGE}.{_FOLLOWUPBOSS_DOCS_LINK}",
        f"{_DEEP_PAGINATION_MESSAGE} https://docs.followupboss.com.example.net/pagination-guide",
        f"{_DEEP_PAGINATION_MESSAGE} {_FOLLOWUPBOSS_DOCS_LINK} {_FOLLOWUPBOSS_DOCS_LINK}",
        f"Request failed: {_DEEP_PAGINATION_MESSAGE} {_FOLLOWUPBOSS_DOCS_LINK}",
        _FOLLOWUPBOSS_DOCS_LINK,
    ],
)
async def test_known_message_with_other_trailing_text_stays_unexpected(error_message: str) -> None:
    """Only one trailing https Follow Up Boss docs link is set aside; other text alerts."""
    requests: list[httpx.Request] = []

    with pytest.raises(UnexpectedToolError) as exc_info:
        await _call_tool(
            "followupboss_search_people",
            {"offset": 5000},
            _rejecting_upstream(requests, error_message),
        )

    chain = _cause_chain(exc_info.value)
    assert any(type(exc) is RuntimeError and str(exc) == error_message for exc in chain)
    assert any(isinstance(exc, FollowUpBossValidationError) for exc in chain)
    assert [request.url.path.rsplit("/", 1)[-1] for request in requests] == ["identity", "people"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error_message",
    [
        "Invalid value for 'phone' parameter",
        f"Request failed: {_DEEP_PAGINATION_MESSAGE}",
        "Deep pagination disabled for this account, contact support",
        f"{_NO_SUCH_SMART_LIST_MESSAGE} Also bad sort",
        "Invalid value for 'assignedTo' field, no such user.",
        "You cannot delete the last stage from a pipeline",
        "Provided stage is not a valid stage",
        f"{_ZILLOW_SYNC_STAGE_MESSAGE} for this person",
    ],
)
async def test_other_validation_errors_stay_unexpected(error_message: str) -> None:
    """Only the known messages change; every other 400 keeps its error-level path."""
    requests: list[httpx.Request] = []

    with pytest.raises(UnexpectedToolError) as exc_info:
        await _call_tool(
            "followupboss_list_calls",
            {"phone": "555-0100"},
            _rejecting_upstream(requests, error_message),
        )

    chain = _cause_chain(exc_info.value)
    assert any(type(exc) is RuntimeError and str(exc) == error_message for exc in chain)
    assert any(isinstance(exc, FollowUpBossValidationError) for exc in chain)
    assert len(requests) == 1


def test_task_projection_fields_always_includes_id() -> None:
    """A task projection without id gains it; others pass through unchanged."""
    fields_with_id = ["name", "id"]
    fields_without_id = ["name", "dueDate"]

    empty_fields: list[str] = []

    assert task_projection_fields(None) is None
    assert task_projection_fields(empty_fields) is empty_fields
    assert task_projection_fields(fields_with_id) is fields_with_id
    assert task_projection_fields(fields_without_id) == ["name", "dueDate", "id"]
    assert fields_without_id == ["name", "dueDate"]


@pytest.mark.asyncio
@pytest.mark.parametrize("tool_name", _TASK_TOOLS)
@pytest.mark.parametrize(
    ("fields", "expected_query_fields"),
    [
        (["name", "dueDate"], "name,dueDate,id"),
        (["id", "name"], "id,name"),
        ([], ""),
        (None, None),
    ],
)
async def test_task_tools_always_request_task_ids(
    tool_name: str,
    fields: list[str] | None,
    expected_query_fields: str | None,
) -> None:
    """Task tools add id to a fields projection so returned rows stay actionable."""
    requests: list[httpx.Request] = []
    arguments: dict[str, object] = {} if fields is None else {"fields": fields}

    result = await _call_tool(
        tool_name,
        arguments,
        _task_upstream(requests, {"id": 31, "name": "Call back", "dueDate": "2026-10-21"}),
    )

    tasks = result["tasks"]
    assert isinstance(tasks, list)
    assert tasks[0]["id"] == 31
    task_requests = [request for request in requests if request.url.path.endswith("/tasks")]
    assert len(task_requests) == 1
    assert task_requests[0].url.params.get("fields") == expected_query_fields


@pytest.mark.asyncio
async def test_task_rows_without_id_no_longer_fail_validation() -> None:
    """A task row that FUB returns without id still comes back instead of crashing."""
    requests: list[httpx.Request] = []

    result = await _call_tool(
        "followupboss_list_my_overdue_tasks",
        {"fields": ["name", "dueDate"]},
        _task_upstream(requests, {"name": "Call back", "dueDate": "2026-10-21"}),
    )

    tasks = result["tasks"]
    assert isinstance(tasks, list)
    assert tasks[0]["id"] is None
    assert tasks[0]["name"] == "Call back"
    assert TaskRecord.model_validate({"name": "Call back"}).id is None
    assert TaskRecord.model_validate({"id": 31, "name": "Call back"}).id == 31


def test_custom_field_list_request_rejects_only_the_choices_projection() -> None:
    """The collection request rejects choices and keeps every other projection."""
    assert CustomFieldListRequest().fields is None
    assert CustomFieldListRequest(fields=["id", "label", "name", "type"]).fields == [
        "id",
        "label",
        "name",
        "type",
    ]
    with pytest.raises(ValidationError, match="followupboss_get_custom_field"):
        CustomFieldListRequest(fields=["id", "choices"])


@pytest.mark.asyncio
async def test_list_custom_fields_rejects_choices_before_http() -> None:
    """A choices projection fails locally as a ToolError with zero upstream calls."""
    requests: list[httpx.Request] = []

    with pytest.raises(ToolError, match="followupboss_get_custom_field") as exc_info:
        await _call_tool(
            "followupboss_list_custom_fields",
            {"fields": ["id", "choices"]},
            _rejecting_upstream(requests, "Invalid field(s) in the fields parameter: choices"),
        )

    assert not isinstance(exc_info.value, UnexpectedToolError)
    assert requests == []


@pytest.mark.asyncio
async def test_list_custom_fields_sends_other_projections_upstream() -> None:
    """Valid custom field projections still reach Follow Up Boss unchanged."""
    requests: list[httpx.Request] = []

    def upstream(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "_metadata": {"limit": 25, "offset": 0, "total": 1},
                "customfields": [{"id": 5, "label": "Closing Date", "type": "date"}],
            },
        )

    result = await _call_tool(
        "followupboss_list_custom_fields",
        {"fields": ["id", "label", "type"]},
        upstream,
    )

    custom_fields = result["customfields"]
    assert isinstance(custom_fields, list)
    assert custom_fields[0]["id"] == 5
    assert len(requests) == 1
    assert requests[0].url.params["fields"] == "id,label,type"
