"""Integration tests for runtime entrypoints and server lifecycle behavior."""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

import pytest

import followupboss_mcp.cli as cli_module
from followupboss_mcp.config import FollowUpBossSettings
from followupboss_mcp.mcp_server import create_server


class ClosingClient:
    """Queue-free client stub that records lifecycle closure."""

    def __init__(self) -> None:
        self.closed = False

    async def aclose(self) -> None:
        """Close the stub client."""
        self.closed = True

    async def request_json(self, method: str, path: str, **_: object) -> dict[str, object]:
        """Return a minimal JSON payload."""
        del method, path
        return {"id": 1}


@pytest.mark.asyncio
async def test_create_server_lifespan_closes_injected_client() -> None:
    """The server lifespan should close the injected client on shutdown."""
    client = ClosingClient()
    server = create_server(FollowUpBossSettings.model_validate({"api_key": "key"}), client=client)
    async with server._mcp_server.lifespan(server._mcp_server):
        assert client.closed is False
    assert client.closed is True


def test_cli_module_runs_main_when_executed_as_script(monkeypatch: pytest.MonkeyPatch) -> None:
    """Executing the CLI module as a script should trigger the `__main__` block."""
    created_settings: list[object] = []
    runs: list[tuple[str, object]] = []

    class FakeServer:
        def run(self, transport: str) -> None:
            runs.append(("run", transport))

    def fake_create_server(settings: object, **kwargs: object) -> FakeServer:
        created_settings.append(settings)
        runs.append(("create", {"kwargs": kwargs, "settings": settings}))
        return FakeServer()

    monkeypatch.setattr("followupboss_mcp.config.FollowUpBossSettings", lambda: object())
    monkeypatch.setattr("followupboss_mcp.mcp_server.create_server", fake_create_server)
    monkeypatch.setattr(sys, "argv", ["followupboss_mcp.cli", "stdio"])

    module_path = Path(cli_module.__file__).resolve()
    with pytest.raises(SystemExit) as exc_info:
        runpy.run_path(str(module_path), run_name="__main__")

    assert exc_info.value.code == 0
    assert runs == [
        ("create", {"kwargs": {}, "settings": created_settings[0]}),
        ("run", "stdio"),
    ]
