"""Distribution contracts for the shared Codex and Claude Code plugin."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import cast
from urllib.parse import urlsplit

import pytest

from followupboss_mcp.mcp_registration import register_server_surface
from followupboss_mcp.mcp_tools import FollowUpBossToolAdapter
from mcp.server.mcpserver import MCPServer

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_PLUGIN_ROOT = _PROJECT_ROOT / "plugins" / "follow-up-boss"
_MANIFESTS = (".codex-plugin/plugin.json", ".claude-plugin/plugin.json")


def _read_json(path: Path) -> dict[str, object]:
    return cast(dict[str, object], json.loads(path.read_text(encoding="utf-8")))


def _resolve_package_path(root: Path, reference: object) -> Path:
    assert isinstance(reference, str), f"Expected a package path, got {reference!r}"
    assert reference.startswith("./"), f"Package path must start with './': {reference}"
    resolved = (root / reference).resolve()
    assert resolved.is_relative_to(root.resolve()), f"Path escapes package: {reference}"
    assert resolved.exists(), f"Missing packaged path: {reference}"
    return resolved


@pytest.fixture
def standalone_plugin(tmp_path: Path) -> Path:
    """Preserve symlinks so references outside the cached package cannot pass."""
    destination = tmp_path / "installed plugin"
    return Path(shutil.copytree(_PLUGIN_ROOT, destination, symlinks=True))


def test_native_manifests_and_marketplace_identify_the_same_release() -> None:
    manifests = [_read_json(_PLUGIN_ROOT / path) for path in _MANIFESTS]
    names = {manifest["name"] for manifest in manifests}
    versions = {manifest["version"] for manifest in manifests}
    assert len(names) == len(versions) == 1
    name = names.pop()
    version = versions.pop()
    assert isinstance(name, str) and re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name)
    assert isinstance(version, str) and re.fullmatch(r"\d+\.\d+\.\d+", version)

    marketplace = _read_json(_PROJECT_ROOT / ".claude-plugin" / "marketplace.json")
    entries = cast(list[dict[str, object]], marketplace["plugins"])
    matching_entries = [entry for entry in entries if entry["name"] == name]
    assert len(matching_entries) == 1
    entry = matching_entries[0]
    assert _resolve_package_path(_PROJECT_ROOT, entry["source"]) == _PLUGIN_ROOT
    # Versionless catalog entries inherit the plugin version; duplicated versions must agree.
    assert entry.get("version", version) == version


@pytest.mark.parametrize("manifest_path", _MANIFESTS)
def test_manifest_paths_work_from_a_standalone_copy(
    standalone_plugin: Path, manifest_path: str
) -> None:
    manifest = _read_json(standalone_plugin / manifest_path)
    skills = _resolve_package_path(standalone_plugin, manifest.get("skills", "./skills/"))
    mcp = _resolve_package_path(standalone_plugin, manifest.get("mcpServers", "./.mcp.json"))
    assert skills.is_dir()
    assert list(skills.glob("*/SKILL.md")), "No workflow skill in the installed package"
    assert mcp.is_file()
    assert _read_json(mcp)["mcpServers"]

    interface = cast(dict[str, object], manifest.get("interface", {}))
    for key in ("composerIcon", "logo"):
        if key in interface:
            asset = _resolve_package_path(standalone_plugin, interface[key])
            assert asset.is_file() and asset.stat().st_size > 0

    for path in standalone_plugin.rglob("*"):
        assert path.resolve().is_relative_to(standalone_plugin), f"External symlink: {path}"


def test_mcp_connection_uses_hosted_oauth_without_packaged_credentials(
    standalone_plugin: Path,
) -> None:
    config = _read_json(standalone_plugin / ".mcp.json")
    servers = cast(dict[str, dict[str, object]], config["mcpServers"])
    assert set(servers) == {"follow_up_boss"}
    server = servers["follow_up_boss"]
    # No local process, token environment, headers, or bundled OAuth client secrets.
    assert set(server) == {"type", "url"}
    assert server["type"] == "http"
    url = urlsplit(cast(str, server["url"]))
    assert url.scheme == "https"
    assert url.netloc == "fub.theperry.group"
    assert url.path == "/mcp"
    assert url.username is None and url.password is None
    assert not url.query and not url.fragment


@pytest.mark.asyncio
async def test_workflow_tool_references_exist_in_the_registered_mcp_surface(
    standalone_plugin: Path,
) -> None:
    skill_files = list((standalone_plugin / "skills").glob("*/SKILL.md"))
    referenced_tools = {
        name
        for path in skill_files
        for name in re.findall(r"\bfollowupboss_[a-z0-9_]+\b", path.read_text(encoding="utf-8"))
    }
    assert referenced_tools, "The workflow must name the tools it relies on"
    server = MCPServer("plugin-contract-test")
    # Registration only binds closures. No adapter method or network call is executed.
    register_server_surface(server, cast(FollowUpBossToolAdapter, object()))
    registered_tools = {tool.name for tool in await server.list_tools()}
    assert referenced_tools <= registered_tools, (
        f"Workflow references unregistered tools: {sorted(referenced_tools - registered_tools)}"
    )
