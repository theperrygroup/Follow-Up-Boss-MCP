#!/usr/bin/env python3
"""Ingest official Follow Up Boss reference docs into project artifacts."""

from __future__ import annotations

import json
import re
from collections import deque
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = PROJECT_ROOT / "docs" / "followupboss-endpoint-manifest.json"
REPORT_PATH = PROJECT_ROOT / "docs" / "followupboss-doc-ingestion.md"

SEED_URLS = [
    "https://docs.followupboss.com/reference/getting-started",
    "https://docs.followupboss.com/reference/identification",
    "https://docs.followupboss.com/reference/authentication",
    "https://docs.followupboss.com/reference/requests-and-responses",
    "https://docs.followupboss.com/reference/error-responses",
    "https://docs.followupboss.com/reference/searching",
    "https://docs.followupboss.com/reference/pagination",
    "https://docs.followupboss.com/reference/rate-limiting",
    "https://docs.followupboss.com/reference/common-filters",
    "https://docs.followupboss.com/reference/common-issues",
    "https://docs.followupboss.com/reference/webhooks-guide",
    "https://docs.followupboss.com/reference/identity",
    "https://docs.followupboss.com/reference/events-get",
    "https://docs.followupboss.com/reference/events-post",
    "https://docs.followupboss.com/reference/people-get",
    "https://docs.followupboss.com/reference/people-post",
    "https://docs.followupboss.com/reference/people-id-get",
    "https://docs.followupboss.com/reference/people-id-put",
    "https://docs.followupboss.com/reference/users-get",
    "https://docs.followupboss.com/reference/users-id-get",
    "https://docs.followupboss.com/reference/customfields-get",
    "https://docs.followupboss.com/reference/notes-post",
    "https://docs.followupboss.com/reference/webhooks-get",
    "https://docs.followupboss.com/reference/webhooks-post",
]


@dataclass(frozen=True)
class ExtractedPage:
    """Structured endpoint or guide information extracted from the docs."""

    auth: str | None
    body_fields: list[dict[str, str]]
    category: str | None
    endpoint_path: str | None
    header_fields: list[dict[str, str]]
    http_method: str | None
    notable_warnings: list[str]
    page_type: str
    query_params: list[dict[str, str]]
    response_fields: list[str]
    slug: str
    summary: str | None
    title: str
    url: str


def _extract_ssr_doc(html: str) -> dict[str, object]:
    """Extract the SSR document payload from a reference page.

    Args:
        html: The raw HTML document.

    Returns:
        The decoded SSR payload document.

    Raises:
        RuntimeError: If the SSR payload is missing or has an unexpected shape.
    """
    soup = BeautifulSoup(html, "html.parser")
    script = soup.find("script", id="ssr-props")
    if script is None or script.string is None:
        raise RuntimeError("Unable to locate Follow Up Boss ssr-props payload.")
    data = json.loads(script.string)
    if not isinstance(data, dict):
        raise RuntimeError("Unexpected Follow Up Boss ssr-props payload shape.")
    doc = data.get("doc")
    if not isinstance(doc, dict):
        raise RuntimeError("Unexpected Follow Up Boss ssr-props document payload.")
    return {str(key): value for key, value in doc.items()}


def _normalize_reference_url(url: str, *, current_url: str | None = None) -> str:
    """Normalize a Follow Up Boss reference URL by removing fragments and queries."""
    absolute = urljoin(current_url, url) if current_url is not None else url
    parsed = urlparse(absolute)
    path = parsed.path.rstrip("/") or parsed.path
    return f"https://docs.followupboss.com{path}"


def _discover_reference_urls(html: str, current_url: str) -> set[str]:
    """Discover linked Follow Up Boss reference URLs from an HTML page.

    Args:
        html: The raw HTML document.
        current_url: The current page URL used to resolve relative links.

    Returns:
        A set of normalized Follow Up Boss reference URLs.
    """
    soup = BeautifulSoup(html, "html.parser")
    urls: set[str] = set()
    for anchor in soup.find_all("a", href=True):
        href = anchor["href"]
        if not isinstance(href, str):
            continue
        parsed = urlparse(href)
        if parsed.netloc and parsed.netloc != "docs.followupboss.com":
            continue
        absolute = _normalize_reference_url(href, current_url=current_url)
        if absolute.startswith("https://docs.followupboss.com/reference/"):
            urls.add(absolute)
    return urls


def _extract_params(doc: dict[str, object], location: str) -> list[dict[str, str]]:
    api = doc.get("api")
    if not isinstance(api, dict):
        return []
    params = api.get("params")
    if not isinstance(params, list):
        return []
    extracted: list[dict[str, str]] = []
    for param in params:
        if not isinstance(param, dict):
            continue
        if param.get("in") != location:
            continue
        extracted.append(
            {
                "default": str(param.get("default", "")),
                "description": str(param.get("desc", "")),
                "name": str(param.get("name", "")),
                "required": str(bool(param.get("required"))).lower(),
                "type": str(param.get("type", "")),
            }
        )
    return extracted


def _extract_warnings(body: str) -> list[str]:
    warnings: list[str] = []
    pattern = re.compile(
        r"^> (?:🚧|❗️|📘) (.+?)(?:\n> \n> (.+?))(?=\n#|\n> (?:🚧|❗️|📘)|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    for match in pattern.finditer(body):
        heading = match.group(1).strip()
        content = re.sub(r"\n> ?", " ", match.group(2)).strip()
        warnings.append(f"{heading}: {content}")
    return warnings


def _extract_response_fields(doc: dict[str, object]) -> list[str]:
    api = doc.get("api")
    if not isinstance(api, dict):
        return []
    results = api.get("results")
    if not isinstance(results, dict):
        return []
    codes = results.get("codes")
    if not isinstance(codes, list):
        return []
    for code in codes:
        if not isinstance(code, dict):
            continue
        snippet = code.get("code")
        if not isinstance(snippet, str) or not snippet.strip():
            continue
        try:
            payload = json.loads(snippet)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return _flatten_json_keys(payload)
    return []


def _flatten_json_keys(payload: dict[str, object], prefix: str = "", depth: int = 0) -> list[str]:
    fields: list[str] = []
    for key, value in payload.items():
        field_name = f"{prefix}.{key}" if prefix else key
        fields.append(field_name)
        if depth >= 1:
            continue
        if isinstance(value, dict):
            fields.extend(_flatten_json_keys(value, prefix=field_name, depth=depth + 1))
        elif isinstance(value, list) and value and isinstance(value[0], dict):
            fields.extend(_flatten_json_keys(value[0], prefix=f"{field_name}[]", depth=depth + 1))
    return fields


def _normalize_endpoint_path(path: str) -> str:
    """Normalize discovered endpoint paths for stable manifest entries.

    Args:
        path: The raw endpoint path discovered in the official docs payload.

    Returns:
        A normalized endpoint path with one leading slash and no duplicate
        slashes.
    """
    normalized = "/" + path.strip().lstrip("/")
    while "//" in normalized:
        normalized = normalized.replace("//", "/")
    return normalized


def _extract_page(doc: dict[str, object], url: str) -> ExtractedPage:
    api = doc.get("api")
    api_dict = api if isinstance(api, dict) else {}
    body = str(doc.get("body", ""))
    category = doc.get("category")
    category_title = category.get("title") if isinstance(category, dict) else None
    return ExtractedPage(
        auth=str(api_dict.get("auth")) if api_dict.get("auth") is not None else None,
        body_fields=_extract_params(doc, "body"),
        category=str(category_title) if category_title is not None else None,
        endpoint_path=(
            _normalize_endpoint_path(str(api_dict.get("url"))) if api_dict.get("url") else None
        ),
        header_fields=_extract_params(doc, "header"),
        http_method=str(api_dict.get("method")).upper() if api_dict.get("method") else None,
        notable_warnings=_extract_warnings(body),
        page_type=str(doc.get("type", "unknown")),
        query_params=_extract_params(doc, "query"),
        response_fields=_extract_response_fields(doc),
        slug=str(doc.get("slug", "")),
        summary=str(doc.get("excerpt")) if doc.get("excerpt") else None,
        title=str(doc.get("title", "")),
        url=url,
    )


def crawl_reference_pages(client: httpx.Client, seed_urls: Iterable[str]) -> list[ExtractedPage]:
    """Crawl official Follow Up Boss reference pages."""
    queue = deque(_normalize_reference_url(url) for url in seed_urls)
    seen: set[str] = set()
    extracted: dict[str, ExtractedPage] = {}
    while queue:
        url = queue.popleft()
        if url in seen:
            continue
        seen.add(url)
        response = client.get(url)
        response.raise_for_status()
        html = response.text
        doc = _extract_ssr_doc(html)
        page = _extract_page(doc, url)
        extracted[page.slug] = page
        for discovered_url in sorted(_discover_reference_urls(html, url)):
            if discovered_url not in seen:
                queue.append(discovered_url)
    return sorted(extracted.values(), key=lambda page: (page.category or "", page.slug))


def write_manifest(pages: list[ExtractedPage]) -> None:
    """Write the machine-readable manifest."""
    manifest = {
        "generatedAt": datetime.now(tz=UTC).isoformat(),
        "seedUrls": SEED_URLS,
        "pageCount": len(pages),
        "pages": [asdict(page) for page in pages],
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")


def write_report(pages: list[ExtractedPage]) -> None:
    """Write the human-readable ingestion report."""
    endpoint_pages = [page for page in pages if page.endpoint_path]
    guide_pages = [page for page in pages if not page.endpoint_path]
    lines = [
        "# Follow Up Boss Doc Ingestion",
        "",
        "## Sources Ingested",
        "",
        "The ingestion process used only official Follow Up Boss documentation pages under `https://docs.followupboss.com/reference`.",
        "",
        "Seed pages:",
        "",
    ]
    lines.extend(f"- `{url}`" for url in SEED_URLS)
    lines.extend(
        [
            "",
            "## Extraction Output",
            "",
            f"- Total pages discovered: `{len(pages)}`",
            f"- Endpoint/reference pages with documented API paths: `{len(endpoint_pages)}`",
            f"- Guide/reference pages without API paths: `{len(guide_pages)}`",
            "",
            "## Extraction Fields",
            "",
            "- page title",
            "- page slug",
            "- endpoint path",
            "- HTTP method",
            "- short summary",
            "- authentication requirement",
            "- query params",
            "- body fields",
            "- header requirements",
            "- notable warnings and restrictions",
            "- discoverable response fields from official result examples",
            "",
            "## Crawl Notes",
            "",
            "- Discovery is driven by the official rendered navigation links "
            "and limited to `/reference/...` pages on `docs.followupboss.com`.",
            "- The parser reads the official embedded `ssr-props` JSON object "
            "for structured endpoint metadata.",
            "- Warnings and restrictions are derived from markdown callouts in "
            "the official page body.",
            "- Response fields are inferred only when the official result "
            "examples contain valid JSON.",
            "",
            "## Discovered Endpoints",
            "",
            "| Method | Path | Slug | Summary |",
            "| --- | --- | --- | --- |",
        ]
    )
    for page in endpoint_pages:
        lines.append(
            f"| `{page.http_method or ''}` | `{page.endpoint_path or ''}` | "
            f"`{page.slug}` | {page.summary or ''} |"
        )
    lines.extend(
        [
            "",
            "## Limitations",
            "",
            "- Some official pages provide placeholder `{}` response examples "
            "instead of a detailed schema; those pages may have sparse "
            "response-field extraction.",
            "- Some parameter names appear as wildcard patterns such as "
            "`custom*`; those are preserved as documented rather than "
            "expanded into account-specific field names.",
        ]
    )
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    """Run the ingestion process."""
    with httpx.Client(follow_redirects=True, timeout=30.0) as client:
        pages = crawl_reference_pages(client, SEED_URLS)
    write_manifest(pages)
    write_report(pages)
    print(f"Wrote {MANIFEST_PATH}")
    print(f"Wrote {REPORT_PATH}")


if __name__ == "__main__":
    main()
