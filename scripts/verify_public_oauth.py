#!/usr/bin/env python3
"""Verify current OAuth client compatibility and deployed authorization starts."""

from __future__ import annotations

import argparse
import asyncio
import base64
import hashlib
import os
import re
import secrets
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qs, urlsplit

import httpx

from followupboss_mcp.cimd import ClientIdMetadataDocumentFetcher, ClientIdMetadataResolver

USER_AGENT = "FollowUpBoss-MCP-Release-Validation/1.0"
REQUIRED_SCOPE = "followupboss:mcp"
DEFAULT_FUB_AUTHORIZE_URL = "https://app.followupboss.com/oauth/authorize"


@dataclass(frozen=True)
class ClientProbe:
    """A supported public client and the callback exercised by its probe."""

    name: str
    client_id: str
    redirect_uri: str


CLIENTS = (
    ClientProbe(
        "ChatGPT",
        "https://chatgpt.com/oauth/client.json",
        "https://chatgpt.com/connector_platform_oauth_redirect",
    ),
    ClientProbe(
        "Codex",
        "https://chatgpt.com/oauth/codex/client.json",
        "http://127.0.0.1:43187/callback",
    ),
)


class OAuthProbeError(ValueError):
    """A sanitized, actionable verification failure without response contents."""


async def verify_client_metadata(
    fetcher: ClientIdMetadataResolver | None = None,
) -> None:
    """Use the production resolver to validate both current public documents."""
    owns_fetcher = fetcher is None
    resolver = fetcher if fetcher is not None else ClientIdMetadataDocumentFetcher()
    try:
        for probe in CLIENTS:
            try:
                document = await resolver.fetch(probe.client_id)
            except Exception:
                raise OAuthProbeError(
                    f"{probe.name} client metadata verification failed."
                ) from None
            if (
                document.client_id != probe.client_id
                or document.token_endpoint_auth_method != "none"
                or not document.allows_redirect_uri(probe.redirect_uri)
            ):
                raise OAuthProbeError(f"{probe.name} client metadata is incompatible.")
    finally:
        if owns_fetcher:
            await resolver.aclose()


def _https_endpoint(value: str, label: str) -> None:
    """Require an unambiguous HTTPS endpoint without embedded credentials."""
    try:
        parsed = urlsplit(value)
        valid = (
            value == value.strip()
            and not any(ord(character) <= 0x20 for character in value)
            and "\\" not in value
            and "?" not in value
            and "#" not in value
            and parsed.scheme == "https"
            and bool(parsed.hostname)
            and parsed.username is None
            and parsed.password is None
            and parsed.port != 0
        )
    except ValueError:
        valid = False
    if not valid:
        raise OAuthProbeError(f"Configured {label} must be a canonical HTTPS URL.")


async def _request(client: httpx.AsyncClient, url: str, phase: str) -> httpx.Response:
    """Make a bounded request without redirects, credentials, or response logging."""
    try:
        return await client.get(
            url,
            headers={"Accept": "application/json", "User-Agent": USER_AGENT},
            follow_redirects=False,
            timeout=15.0,
        )
    except httpx.HTTPError:
        raise OAuthProbeError(f"{phase} request failed.") from None


def _object(response: httpx.Response, phase: str) -> dict[str, Any]:
    """Read only successful JSON objects and never expose remote response bodies."""
    if response.status_code != 200:
        raise OAuthProbeError(f"{phase} returned HTTP {response.status_code}.")
    try:
        payload = response.json()
    except ValueError:
        raise OAuthProbeError(f"{phase} returned invalid JSON.") from None
    if not isinstance(payload, dict):
        raise OAuthProbeError(f"{phase} must be a JSON object.")
    return payload


def _includes(payload: dict[str, Any], key: str, *required: str) -> bool:
    """Check advertised lists without accepting string membership by accident."""
    values = payload.get(key)
    return isinstance(values, list) and all(value in values for value in required)


def _verify_delegation(
    response: httpx.Response, issuer: str, upstream: str, name: str, fub_client_id: str
) -> None:
    """Validate a provider redirect without following or printing its secret state."""
    if response.status_code not in (302, 303, 307):
        raise OAuthProbeError(f"{name} authorization returned HTTP {response.status_code}.")
    location = response.headers.get("location", "")
    try:
        target = urlsplit(location)
        expected = urlsplit(upstream)
        query = parse_qs(target.query, keep_blank_values=True)
        valid = (
            bool(location)
            and not any(ord(character) <= 0x20 for character in location)
            and "\\" not in location
            and "#" not in location
            and target.username is None
            and target.password is None
            and (target.scheme, target.netloc, target.path)
            == (expected.scheme, expected.netloc, expected.path)
            and query.get("response_type") == ["auth_code"]
            and query.get("redirect_uri") == [f"{issuer}oauth/follow-up-boss/callback"]
            and query.get("prompt") == ["login"]
            and query.get("client_id") == [fub_client_id]
            and all(
                len(query.get(key, [])) == 1 and bool(query[key][0].strip())
                for key in ("client_id", "state")
            )
            and not any(key in query for key in ("error", "code", "access_token"))
        )
    except ValueError:
        valid = False
    if not valid:
        raise OAuthProbeError(f"{name} authorization returned an invalid provider redirect.")


async def verify_public_oauth(
    resource: str,
    issuer: str,
    *,
    fub_client_id: str,
    fub_authorize_url: str = DEFAULT_FUB_AUTHORIZE_URL,
    client: httpx.AsyncClient | None = None,
) -> None:
    """Check public metadata and start both clients' real deployed OAuth flows."""
    _https_endpoint(resource, "resource")
    _https_endpoint(issuer, "issuer")
    _https_endpoint(fub_authorize_url, "provider authorization endpoint")
    if not fub_client_id or fub_client_id != fub_client_id.strip():
        raise OAuthProbeError("Configured provider client ID is required.")
    resource_parts = urlsplit(resource)
    issuer_parts = urlsplit(issuer)
    if resource_parts.netloc != issuer_parts.netloc or issuer_parts.path not in ("", "/"):
        raise OAuthProbeError("Configured issuer is not the MCP HTTPS origin.")
    issuer = issuer.rstrip("/") + "/"
    origin = issuer.rstrip("/")
    protected_url = f"{origin}/.well-known/oauth-protected-resource{resource_parts.path}"
    owns_client = client is None
    http = client if client is not None else httpx.AsyncClient(trust_env=False)
    try:
        challenge = await _request(http, resource, "MCP bearer challenge")
        if challenge.status_code != 401:
            raise OAuthProbeError(f"MCP bearer challenge returned HTTP {challenge.status_code}.")
        header = challenge.headers.get("www-authenticate", "")
        advertised = re.search(r'(?:^|[,\s])resource_metadata="([^"]+)"', header)
        if (
            header.split(" ", 1)[0].lower() != "bearer"
            or advertised is None
            or advertised.group(1) != protected_url
        ):
            raise OAuthProbeError("MCP bearer challenge advertised the wrong metadata URL.")
        protected = _object(
            await _request(http, protected_url, "Protected metadata"), "Protected metadata"
        )
        authorization = _object(
            await _request(
                http, f"{issuer}.well-known/oauth-authorization-server", "Authorization metadata"
            ),
            "Authorization metadata",
        )
        if protected.get("resource") != resource or not _includes(
            protected, "authorization_servers", issuer
        ):
            raise OAuthProbeError("Protected metadata advertised the wrong resource or issuer.")
        if (
            authorization.get("issuer") != issuer
            or authorization.get("authorization_endpoint") != f"{issuer}oauth/authorize"
            or authorization.get("token_endpoint") != f"{issuer}oauth/token"
            or authorization.get("authorization_response_iss_parameter_supported") is not True
            or authorization.get("client_id_metadata_document_supported") is not True
            or not _includes(authorization, "response_types_supported", "code")
            or not _includes(
                authorization, "grant_types_supported", "authorization_code", "refresh_token"
            )
            or not _includes(authorization, "code_challenge_methods_supported", "S256")
            or not _includes(authorization, "token_endpoint_auth_methods_supported", "none")
            or not _includes(authorization, "scopes_supported", REQUIRED_SCOPE)
        ):
            raise OAuthProbeError("Authorization metadata violates the supported client contract.")
        for probe in CLIENTS:
            verifier = secrets.token_urlsafe(48)
            challenge_value = (
                base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest())
                .rstrip(b"=")
                .decode()
            )
            url = httpx.URL(
                f"{issuer}oauth/authorize",
                params={
                    "response_type": "code",
                    "client_id": probe.client_id,
                    "redirect_uri": probe.redirect_uri,
                    "scope": REQUIRED_SCOPE,
                    "state": secrets.token_urlsafe(24),
                    "code_challenge": challenge_value,
                    "code_challenge_method": "S256",
                    "resource": resource,
                },
            )
            response = await _request(http, str(url), f"{probe.name} authorization")
            _verify_delegation(response, issuer, fub_authorize_url, probe.name, fub_client_id)
    finally:
        if owns_client:
            await http.aclose()


def main(argv: Sequence[str] | None = None) -> None:
    """Run a credential-free preflight or deployed OAuth authorization check."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata-only", action="store_true")
    parser.add_argument("--resource", default=os.environ.get("HOSTED_RESOURCE_SERVER_URL", ""))
    parser.add_argument("--issuer", default=os.environ.get("HOSTED_ISSUER_URL", ""))
    parser.add_argument("--fub-authorize-url", default=DEFAULT_FUB_AUTHORIZE_URL)
    parser.add_argument("--fub-client-id", default=os.environ.get("FUB_OAUTH_CLIENT_ID", ""))
    args = parser.parse_args(argv)

    async def run() -> None:
        await verify_client_metadata()
        if not args.metadata_only:
            await verify_public_oauth(
                args.resource,
                args.issuer,
                fub_authorize_url=args.fub_authorize_url,
                fub_client_id=args.fub_client_id,
            )

    try:
        asyncio.run(run())
    except OAuthProbeError as exc:
        raise SystemExit(str(exc)) from None
    print(
        "OAuth client metadata verified: ChatGPT and Codex."
        if args.metadata_only
        else "Public OAuth verified: bearer challenge, discovery, both client authorization starts."
    )


if __name__ == "__main__":
    main()
