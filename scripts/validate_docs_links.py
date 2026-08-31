"""Validate repository markdown links and MCP docs coverage."""

from __future__ import annotations

import re
from dataclasses import dataclass
from os import walk
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MCP_REGISTRATION_PATH = PROJECT_ROOT / "src" / "followupboss_mcp" / "mcp_registration.py"
MCP_USAGE_PATH = PROJECT_ROOT / "docs" / "mcp-usage.md"
README_PATH = PROJECT_ROOT / "README.md"

_MARKDOWN_LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
_TOOL_NAME_RE = re.compile(r'name="(followupboss_[^"]+)"')
_RESOURCE_NAME_RE = re.compile(r'"(followupboss://[^"]+)"')
_PROMPT_NAME_RE = re.compile(r'name="(followupboss_[^"]+)"')
_SKIP_SCHEMES = ("http://", "https://", "mailto:", "followupboss://", "mcp://")
_SKIPPED_MARKDOWN_DIRS = (Path("docs/planning"),)


@dataclass(frozen=True)
class ValidationIssue:
    """A docs validation issue."""

    message: str
    source: Path


def _iter_markdown_files(project_root: Path) -> list[Path]:
    """Return repository markdown files in stable order.

    Args:
        project_root: The repository root.

    Returns:
        Sorted markdown paths, excluding private planning trees.
    """
    markdown_files: list[Path] = []
    for directory, dirnames, filenames in walk(project_root):
        directory_path = Path(directory)
        dirnames[:] = sorted(
            dirname
            for dirname in dirnames
            if not _is_skipped_markdown_dir(directory_path / dirname, project_root)
        )
        markdown_files.extend(
            directory_path / filename for filename in sorted(filenames) if filename.endswith(".md")
        )
    return sorted(markdown_files)


def _is_skipped_markdown_dir(directory_path: Path, project_root: Path) -> bool:
    """Return whether a directory should be excluded from docs validation.

    Args:
        directory_path: The directory being considered for traversal.
        project_root: The repository root.

    Returns:
        `True` when the directory is private validation input and should not be read.
    """
    relative_path = directory_path.relative_to(project_root)
    return any(
        relative_path == skipped_dir or skipped_dir in relative_path.parents
        for skipped_dir in _SKIPPED_MARKDOWN_DIRS
    )


def _strip_code_blocks(text: str) -> str:
    """Remove fenced code block contents before scanning markdown links.

    Args:
        text: Raw markdown file contents.

    Returns:
        Markdown with fenced code block bodies removed.
    """
    lines: list[str] = []
    in_fence = False
    for line in text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            lines.append("")
            continue
        if not in_fence:
            lines.append(line)
    return "\n".join(lines)


def _slugify_heading(text: str) -> str:
    """Convert a heading into a GitHub-style anchor slug.

    Args:
        text: The raw heading text.

    Returns:
        A normalized anchor slug.
    """
    slug = text.strip().lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"\s+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")


def _extract_heading_slugs(markdown_path: Path) -> set[str]:
    """Collect heading anchors from a markdown file.

    Args:
        markdown_path: The markdown file to scan.

    Returns:
        All heading slugs defined in the file.
    """
    slugs: set[str] = set()
    for line in markdown_path.read_text(encoding="utf-8").splitlines():
        match = _HEADING_RE.match(line)
        if match is None:
            continue
        slugs.add(_slugify_heading(match.group(2)))
    return slugs


def _resolve_link_target(source_path: Path, target: str) -> tuple[Path, str | None]:
    """Resolve a markdown link target against the source file.

    Args:
        source_path: The markdown file containing the link.
        target: The raw link target.

    Returns:
        The resolved filesystem path and optional anchor fragment.
    """
    path_part, _, fragment = target.partition("#")
    resolved = (source_path.parent / path_part).resolve() if path_part else source_path.resolve()
    return resolved, fragment or None


def _validate_markdown_links(project_root: Path) -> list[ValidationIssue]:
    """Validate repository-local markdown links.

    Args:
        project_root: The repository root.

    Returns:
        All discovered markdown link validation issues.
    """
    issues: list[ValidationIssue] = []
    for markdown_path in _iter_markdown_files(project_root):
        visible_text = _strip_code_blocks(markdown_path.read_text(encoding="utf-8"))
        for match in _MARKDOWN_LINK_RE.finditer(visible_text):
            target = match.group(1).strip()
            if not target or target.startswith(_SKIP_SCHEMES):
                continue
            resolved_path, fragment = _resolve_link_target(markdown_path, target)
            if not resolved_path.exists():
                issues.append(
                    ValidationIssue(
                        message=f"Missing linked path: {target}",
                        source=markdown_path,
                    )
                )
                continue
            if fragment is None:
                continue
            if resolved_path.suffix.lower() != ".md":
                continue
            slugs = _extract_heading_slugs(resolved_path)
            if fragment not in slugs:
                issues.append(
                    ValidationIssue(
                        message=f"Missing heading fragment '{fragment}' for link: {target}",
                        source=markdown_path,
                    )
                )
    return issues


def _extract_registered_mcp_names(registration_path: Path) -> tuple[set[str], set[str], set[str]]:
    """Extract MCP tool, resource, and prompt names from the registration file.

    Args:
        registration_path: The server registration module.

    Returns:
        A tuple of tool names, resource names, and prompt names.
    """
    text = registration_path.read_text(encoding="utf-8")
    tool_names = set(_TOOL_NAME_RE.findall(text))
    resource_names = set(_RESOURCE_NAME_RE.findall(text))
    prompt_names = {
        name for name in _PROMPT_NAME_RE.findall(text) if name == "followupboss_compose_lead_event"
    }
    return tool_names, resource_names, prompt_names


def _validate_mcp_usage_coverage(
    registration_path: Path, usage_path: Path
) -> list[ValidationIssue]:
    """Ensure `docs/mcp-usage.md` mentions every registered MCP asset.

    Args:
        registration_path: The server registration module.
        usage_path: The MCP usage documentation file.

    Returns:
        Any missing MCP asset mentions in the usage doc.
    """
    issues: list[ValidationIssue] = []
    usage_text = usage_path.read_text(encoding="utf-8")
    tool_names, resource_names, prompt_names = _extract_registered_mcp_names(registration_path)

    for tool_name in sorted(tool_names):
        if f"`{tool_name}`" not in usage_text:
            issues.append(
                ValidationIssue(
                    message=f"MCP usage doc is missing tool entry: {tool_name}",
                    source=usage_path,
                )
            )

    for resource_name in sorted(resource_names):
        if f"`{resource_name}`" not in usage_text:
            issues.append(
                ValidationIssue(
                    message=f"MCP usage doc is missing resource entry: {resource_name}",
                    source=usage_path,
                )
            )

    for prompt_name in sorted(prompt_names):
        if f"`{prompt_name}`" not in usage_text:
            issues.append(
                ValidationIssue(
                    message=f"MCP usage doc is missing prompt entry: {prompt_name}",
                    source=usage_path,
                )
            )

    return issues


def _validate_readme_docs_links(readme_path: Path) -> list[ValidationIssue]:
    """Ensure the README still references the core documentation set.

    Args:
        readme_path: The repository README file.

    Returns:
        Missing core-doc link issues.
    """
    required_links = {
        "docs/architecture.md",
        "docs/api-coverage-matrix.md",
        "docs/mcp-usage.md",
        "docs/testing.md",
        "docs/security.md",
        "docs/release-checklist.md",
        "docs/final-validation-report.md",
    }
    readme_text = readme_path.read_text(encoding="utf-8")
    link_targets = {
        target.strip() for target in _MARKDOWN_LINK_RE.findall(_strip_code_blocks(readme_text))
    }
    canonical_docs_prefix = "https://github.com/theperrygroup/Follow-Up-Boss-MCP/blob/main/"
    issues: list[ValidationIssue] = []
    for link in sorted(required_links):
        if link not in link_targets and f"{canonical_docs_prefix}{link}" not in link_targets:
            issues.append(
                ValidationIssue(
                    message=f"README is missing documentation link: {link}",
                    source=readme_path,
                )
            )
    return issues


def validate_docs(project_root: Path) -> list[ValidationIssue]:
    """Run all repository docs validation checks.

    Args:
        project_root: The repository root.

    Returns:
        Every docs validation issue found.
    """
    issues: list[ValidationIssue] = []
    issues.extend(_validate_markdown_links(project_root))
    issues.extend(_validate_mcp_usage_coverage(MCP_REGISTRATION_PATH, MCP_USAGE_PATH))
    issues.extend(_validate_readme_docs_links(README_PATH))
    return issues


def main() -> int:
    """Run docs validation and return a shell exit code.

    Returns:
        `0` when validation succeeds, otherwise `1`.
    """
    issues = validate_docs(PROJECT_ROOT)
    if not issues:
        print("Docs validation passed.")
        return 0

    print("Docs validation failed:")
    for issue in issues:
        relative_source = issue.source.relative_to(PROJECT_ROOT)
        print(f"- {relative_source}: {issue.message}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
