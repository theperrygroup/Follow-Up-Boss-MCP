"""Exercise the actual production public OAuth probe without network access."""

from __future__ import annotations

import io
import json
import textwrap
from email.message import Message
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request

import pytest

_RESOURCE = "https://mcp.example.com/mcp"
_ISSUER = "https://mcp.example.com/"
_PROTECTED = "https://mcp.example.com/.well-known/oauth-protected-resource/mcp"
_AGENT = "FollowUpBoss-MCP-Release-Validation/1.0"


def _script() -> str:
    workflow = (
        Path(__file__).resolve().parents[2] / ".github/workflows/deploy-production.yml"
    ).read_text()
    step = workflow.split("- name: Verify public OAuth metadata and bearer challenge", 1)[1]
    return textwrap.dedent(step.split("python - <<'PY'\n", 1)[1].split("\n          PY", 1)[0])


@pytest.mark.parametrize("bearer_status", [401, 403])
def test_public_probe_identifies_itself_without_weakening_authentication(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], bearer_status: int
) -> None:
    requests: list[str] = []

    def urlopen(request: Request | str, timeout: int) -> io.BytesIO:
        assert timeout == 15
        if not isinstance(request, Request) or request.get_header("User-agent") != _AGENT:
            raise HTTPError(_RESOURCE, 403, "Unidentified automation", Message(), None)
        assert request.get_header("Accept") == "application/json"
        assert request.get_header("Authorization") is None
        requests.append(request.full_url)
        if request.full_url == _RESOURCE:
            headers = Message()
            headers["WWW-Authenticate"] = f'Bearer resource_metadata="{_PROTECTED}"'
            raise HTTPError(
                _RESOURCE,
                bearer_status,
                "Expected bearer challenge",
                headers,
                None,
            )
        if request.full_url == _PROTECTED:
            payload: dict[str, object] = {
                "resource": _RESOURCE,
                "authorization_servers": [_ISSUER],
            }
        else:
            assert request.full_url == f"{_ISSUER}.well-known/oauth-authorization-server"
            payload = {
                "issuer": _ISSUER,
                "authorization_response_iss_parameter_supported": True,
                "client_id_metadata_document_supported": True,
            }
        return io.BytesIO(json.dumps(payload).encode())

    monkeypatch.setenv("HOSTED_RESOURCE_SERVER_URL", _RESOURCE)
    monkeypatch.setenv("HOSTED_ISSUER_URL", _ISSUER)
    monkeypatch.setattr("urllib.request.urlopen", urlopen)
    if bearer_status == 403:
        with pytest.raises(SystemExit, match="MCP bearer challenge returned HTTP 403"):
            exec(_script(), {})
        assert len(requests) == 1
    else:
        exec(_script(), {})
        assert len(requests) == 3
        assert "resource, issuer, RFC 9207, and CIMD verified" in capsys.readouterr().out
