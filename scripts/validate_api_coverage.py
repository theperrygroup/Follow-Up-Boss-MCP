#!/usr/bin/env python3
"""Validate and regenerate the Follow Up Boss API coverage matrix."""

from __future__ import annotations

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = PROJECT_ROOT / "docs" / "followupboss-endpoint-manifest.json"
MATRIX_PATH = PROJECT_ROOT / "docs" / "api-coverage-matrix.md"

COVERAGE_MAP: dict[str, dict[str, str]] = {
    "GET /identity": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Used as the health check path.",
        "tests": "Yes",
    },
    "GET /people": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Supports next-token and offset pagination.",
        "tests": "Yes",
    },
    "POST /people": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Documented as non-canonical for lead ingestion; prefer POST /events.",
        "tests": "Yes",
    },
    "GET /people/:id": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Supports fields selection.",
        "tests": "Yes",
    },
    "PUT /people/:id": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Supports mergeTags query semantics.",
        "tests": "Yes",
    },
    "DELETE /people/:id": {
        "implementation": "Deferred",
        "mcp": "No",
        "models": "No",
        "notes": "Not part of the requested MCP tool surface.",
        "tests": "No",
    },
    "GET /events": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Supports next-token pagination.",
        "tests": "Yes",
    },
    "POST /events": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Canonical external lead and lead-activity ingestion path.",
        "tests": "Yes",
    },
    "GET /events/:id": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Single-event lookup.",
        "tests": "Yes",
    },
    "GET /users": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Collection query coverage included.",
        "tests": "Yes",
    },
    "GET /users/:id": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Single-user lookup.",
        "tests": "Yes",
    },
    "DELETE /users/:id": {
        "implementation": "Deferred",
        "mcp": "No",
        "models": "No",
        "notes": "Deferred until explicitly needed.",
        "tests": "No",
    },
    "GET /customFields": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Supports custom field name validation helpers.",
        "tests": "Yes",
    },
    "GET /deals": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Supports documented deal filters and pagination metadata.",
        "tests": "Yes",
    },
    "GET /deals/{id}": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Single-deal lookup with dynamic custom field support.",
        "tests": "Yes",
    },
    "POST /deals": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Creates a deal and supports dynamic deal custom field values.",
        "tests": "Yes",
    },
    "PUT /deals/{id}": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Updates a deal and preserves documented custom field semantics.",
        "tests": "Yes",
    },
    "DELETE /deals/{id}": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Input only",
        "notes": "Delete returns structured deletion confirmation.",
        "tests": "Yes",
    },
    "GET /dealCustomFields": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Lists deal custom fields for write-time field-name discovery.",
        "tests": "Yes",
    },
    "GET /calls": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Supports documented call filters and pagination metadata.",
        "tests": "Yes",
    },
    "GET /calls/:id": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Single-call lookup.",
        "tests": "Yes",
    },
    "GET /appointments": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Supports documented appointment filters and pagination metadata.",
        "tests": "Yes",
    },
    "GET /appointments/:id": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Single-appointment lookup.",
        "tests": "Yes",
    },
    "POST /appointments": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Creates an appointment with optional invitees and sendInvitation support.",
        "tests": "Yes",
    },
    "PUT /appointments/:id": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Updates an appointment and supports sendInvitation query semantics.",
        "tests": "Yes",
    },
    "DELETE /appointments/:id": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Input only",
        "notes": "Delete returns structured deletion confirmation.",
        "tests": "Yes",
    },
    "POST /calls": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Creates a call log entry for a related person.",
        "tests": "Yes",
    },
    "PUT /calls/:id": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Updates a call log entry.",
        "tests": "Yes",
    },
    "POST /customFields": {
        "implementation": "Deferred",
        "mcp": "No",
        "models": "No",
        "notes": "Deferred until explicit custom field admin support is requested.",
        "tests": "No",
    },
    "GET /customFields/:id": {
        "implementation": "Deferred",
        "mcp": "No",
        "models": "No",
        "notes": "Deferred until explicit custom field admin support is requested.",
        "tests": "No",
    },
    "PUT /customFields/:id": {
        "implementation": "Deferred",
        "mcp": "No",
        "models": "No",
        "notes": "Deferred until explicit custom field admin support is requested.",
        "tests": "No",
    },
    "DELETE /customFields/:id": {
        "implementation": "Deferred",
        "mcp": "No",
        "models": "No",
        "notes": "Deferred until explicit custom field admin support is requested.",
        "tests": "No",
    },
    "POST /notes": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Supports optional person-availability wait flow.",
        "tests": "Yes",
    },
    "GET /notes/:id": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Single-note lookup.",
        "tests": "Yes",
    },
    "PUT /notes/:id": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Single-note update.",
        "tests": "Yes",
    },
    "DELETE /notes/:id": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Input only",
        "notes": "Delete returns structured deletion confirmation.",
        "tests": "Yes",
    },
    "GET /webhooks": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Requires registered system headers.",
        "tests": "Yes",
    },
    "POST /webhooks": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Requires registered system headers and owner-level permissions.",
        "tests": "Yes",
    },
    "GET /webhooks/:id": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Single-webhook lookup.",
        "tests": "Yes",
    },
    "PUT /webhooks/:id": {
        "implementation": "Deferred",
        "mcp": "No",
        "models": "No",
        "notes": "Deferred until explicitly needed.",
        "tests": "No",
    },
    "DELETE /webhooks/:id": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Input only",
        "notes": "Delete endpoint exposed through MCP.",
        "tests": "Yes",
    },
    "GET /templates": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Lists email templates with pagination metadata.",
        "tests": "Yes",
    },
    "GET /templates/:id": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Single-template lookup with optional mergePersonId support.",
        "tests": "Yes",
    },
    "POST /templates": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Creates a new email template.",
        "tests": "Yes",
    },
    "PUT /templates/:id": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Updates template name, subject, and body.",
        "tests": "Yes",
    },
    "DELETE /templates/:id": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Input only",
        "notes": "Delete returns structured deletion confirmation.",
        "tests": "Yes",
    },
    "GET /pipelines": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Lists pipelines with exact-name filtering and pagination metadata.",
        "tests": "Yes",
    },
    "GET /pipelines/{id}": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Single-pipeline lookup including stage definitions.",
        "tests": "Yes",
    },
    "POST /pipelines": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Creates a pipeline with optional ordered stages.",
        "tests": "Yes",
    },
    "PUT /pipelines/{id}": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Updates pipeline metadata and supports stage create-or-update semantics.",
        "tests": "Yes",
    },
    "DELETE /pipelines/:id": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Input only",
        "notes": "Delete returns structured deletion confirmation.",
        "tests": "Yes",
    },
    "GET /textMessages": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Lists text messages for a person or phone number.",
        "tests": "Yes",
    },
    "GET /textMessages/{id}": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Single-text-message lookup.",
        "tests": "Yes",
    },
    "GET /textMessageTemplates": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Lists text message templates with pagination metadata.",
        "tests": "Yes",
    },
    "GET /textMessageTemplates/{id}": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Single text message template lookup.",
        "tests": "Yes",
    },
    "POST /textMessageTemplates": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Creates a new text message template.",
        "tests": "Yes",
    },
    "PUT /textMessageTemplates/:id": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Updates text message template content and sharing state.",
        "tests": "Yes",
    },
    "DELETE /textMessageTemplates/:id": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Input only",
        "notes": "Delete returns structured deletion confirmation.",
        "tests": "Yes",
    },
    "GET /tasks": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Supports documented task filters and pagination metadata.",
        "tests": "Yes",
    },
    "GET /tasks/:id": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Single-task lookup.",
        "tests": "Yes",
    },
    "POST /tasks": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Requires a related person and an assignee.",
        "tests": "Yes",
    },
    "PUT /tasks/:id": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Supports task completion and due-date updates.",
        "tests": "Yes",
    },
    "DELETE /tasks/:id": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Input only",
        "notes": "Delete returns structured deletion confirmation.",
        "tests": "Yes",
    },
}


def _load_manifest() -> dict[str, object]:
    """Load the generated endpoint manifest from disk.

    Returns:
        The decoded manifest payload.

    Raises:
        SystemExit: If the manifest is missing or has an unexpected top-level shape.
    """
    if not MANIFEST_PATH.exists():
        raise SystemExit(f"Manifest not found: {MANIFEST_PATH}")
    payload = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit("Manifest payload is invalid.")
    return {str(key): value for key, value in payload.items()}


def _normalize_endpoint_path(path: str) -> str:
    """Normalize endpoint paths so generated coverage keys stay stable.

    Args:
        path: The raw endpoint path extracted from documentation.

    Returns:
        A normalized endpoint path with exactly one leading slash and no
        duplicate interior slashes.
    """
    normalized = "/" + path.strip().lstrip("/")
    while "//" in normalized:
        normalized = normalized.replace("//", "/")
    return normalized


def _endpoint_key(page: dict[str, object]) -> str | None:
    """Build a normalized coverage key for a manifest page.

    Args:
        page: A manifest page entry.

    Returns:
        The normalized `<METHOD> <PATH>` key, or `None` when the page does not
        represent a documented endpoint.
    """
    method = page.get("http_method")
    path = page.get("endpoint_path")
    if not isinstance(method, str) or not isinstance(path, str):
        return None
    return f"{method.strip().upper()} {_normalize_endpoint_path(path)}"


def write_matrix(manifest: dict[str, object]) -> None:
    """Write the explicit coverage matrix."""
    pages = manifest.get("pages", [])
    if not isinstance(pages, list):
        raise SystemExit("Manifest pages payload is invalid.")
    endpoint_keys = sorted(
        {key for page in pages if isinstance(page, dict) for key in [_endpoint_key(page)] if key}
    )

    lines = [
        "# API Coverage Matrix",
        "",
        "Generated from the official Follow Up Boss doc-ingestion manifest and an explicit "
        "repository coverage declaration.",
        "",
        "| Endpoint | Implementation | Models | MCP | Tests | Notes |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for endpoint in endpoint_keys:
        status = COVERAGE_MAP.get(
            endpoint,
            {
                "implementation": "Deferred",
                "mcp": "No",
                "models": "No",
                "notes": (
                    "Discovered during the official docs crawl and intentionally "
                    "deferred from the current repository scope."
                ),
                "tests": "No",
            },
        )
        lines.append(
            f"| `{endpoint}` | {status['implementation']} | {status['models']} | "
            f"{status['mcp']} | {status['tests']} | {status['notes']} |"
        )
    MATRIX_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    """Validate the manifest and regenerate the matrix."""
    manifest = _load_manifest()
    write_matrix(manifest)
    print(f"Wrote {MATRIX_PATH}")


if __name__ == "__main__":
    main()
