---
name: sentry-triage-autofix
description: Check this Follow Up Boss MCP repo's Sentry project for unresolved issues, inspect issue details and stack traces, verify the real failing code path, fix actionable issues by default, run fail-fast parallel verification, and mark verified code fixes as resolved in the next release. Use when the user mentions Sentry, unresolved issues, Sentry triage, a Sentry stack trace or URL, or asks to launch the repo's autofix flow.
---

# Sentry Triage Autofix

## Use This Skill

Use this as the default repo-local workflow when the user wants Sentry issues
checked, triaged, or fixed for this repository. Unless the user explicitly asks
for report-only triage, a single issue, or agent launching, the default outcome
is: every actionable unresolved issue found by the configured query is fixed
locally, verified, or reduced to a clearly documented non-code/configuration
condition with an explicit follow-up owner.

Prefer Sentry MCP tools over the Sentry web UI. This repo currently does not
ship `scripts/review_sentry_issues.py`, `scripts/inspect_sentry_issue.py`, or
`scripts/resolve_sentry_issues.py`, so do not use those commands unless they are
added later. Never paste or commit Sentry DSNs, API keys, `.env` contents,
Follow Up Boss credentials, tenant payloads, or customer data.

## Read First

Before acting, read the files that own the Sentry and verification surface:

- `pyproject.toml`
- `Makefile`
- `docs/testing.md`
- `docs/planning/sentry-observability/trackers/readiness-overview.md`
- `src/followupboss_mcp/observability.py`
- `src/followupboss_mcp/config.py`
- `tests/unit/test_observability.py`

For runtime entrypoint failures, also read the stack-frame owner such as
`src/followupboss_mcp/mcp_server.py`, `src/followupboss_mcp/hosted_reference.py`,
or the named service/model module.

## Repo Defaults

- Repo: `jp26jp/Follow-Up-Boss-MCP`
- Package: `followupboss-mcp`
- Python package path: `src/followupboss_mcp`
- Sentry SDK: `sentry-sdk` for Python
- Sentry initialization path: `followupboss_mcp.observability.configure_sentry`
- Sentry settings path: `followupboss_mcp.config.SentrySettings`
- Privacy hook: `followupboss_mcp.observability.before_send`
- Default Sentry query: `is:unresolved level:error`
- Preferred production environment filters, in order: `environment:production`,
  `environment:prod`, then `environment:PROD`

The Sentry org/project are not hard-coded in this repo. Discover them from the
user's issue URL, Sentry MCP project search, or explicit user input. Prefer a
project whose name or slug matches `followupboss-mcp`, `follow-up-boss-mcp`, or
`Follow Up Boss MCP`. If no matching Sentry project is configured, report that
as the current blocker and keep any local Sentry instrumentation fixes scoped to
the code path the user provided.

## Sentry MCP Workflow

Before calling any Sentry MCP tool, read that tool's descriptor from
`mcps/plugin-sentry-sentry/tools/<tool>.json`.

Use these tools by default:

- `find_organizations`: discover accessible org slugs when the user did not
  provide one.
- `find_projects`: find the project slug or numeric project ID for this repo.
- `search_issues`: list grouped unresolved issues.
- `search_issue_events`: inspect recent events inside a grouped issue.
- `get_sentry_resource`: fetch issue or event details when search output lacks
  the stack trace, exception values, release, environment, tags, or breadcrumbs.
- `analyze_issue_with_seer`: optional second opinion only; treat it as input,
  not proof.
- `update_issue`: mark verified fixes `resolvedInNextRelease` after local
  verification passes.

When issue URLs are available, prefer passing the URL directly to event/detail
tools. Otherwise use `organizationSlug`, `projectSlugOrId`, and issue ID.

## Pick The Mode

- Full-fix mode: default when the user says "Sentry", invokes this skill without
  qualifiers, asks what is broken, asks if everything is fixed, or asks to
  check/fix unresolved issues.
- Overview mode: only when the user explicitly asks for report-only triage, a
  summary, ranking, or "do not fix".
- Issue mode: the user gives a Sentry issue ID, short ID, URL, stack trace, or
  asks to fix one issue.
- Batch autofix mode: the user explicitly wants multiple Cursor agents launched
  for multiple eligible Sentry issues.
- Resolution mode: the user explicitly wants matching issues marked resolved, or
  Issue/Full-Fix Mode produced verified code changes.

## Full-Fix Mode

1. Discover the Sentry org/project if the user did not provide them. If discovery
   returns multiple plausible projects, inspect the top candidates and choose the
   Follow Up Boss MCP project. If no project is discoverable, stop and report the
   missing org/project configuration.

2. Search unresolved issues with the default query. Try the preferred production
   environment filters first. If no production-filtered issue is found, run the
   default query without an environment filter and note that production scoping is
   not configured or not observable.

3. Create a working queue from every issue returned by the query. Sort by impact
   and fixability using event count, affected users, recency, culprit quality,
   and whether the failure maps to repo-owned code.

4. For each issue, run Issue Mode. Do not stop after listing issues or fixing
   the first issue.

5. Keep working until every found issue is in one of these states:

- fixed locally with tests/lints run
- already fixed in the current local code, with deployment/resolution status
  noted
- not actionable in code because it is external service behavior, invalid
  third-party input, credential/configuration failure, missing Sentry project
  configuration, or infrastructure capacity

6. After each verified code fix, run Resolution Mode for the exact matching
   issue. Prefer `resolvedInNextRelease`; never immediately hide unrelated
   groups.

## Overview Mode

Use Sentry MCP `search_issues` with the default query and a limit of 20. Rank by:

- event volume
- affected users
- recency
- culprit and stack-frame quality
- whether the error looks like a clear code regression versus configuration,
  deployment, credentials, Follow Up Boss upstream behavior, or Sentry rollout
  incompleteness

If the user did not explicitly request report-only triage, switch to Full-Fix
Mode instead of stopping at recommendations.

## Issue Mode

1. Inspect the issue and recent events. Gather:

- issue ID or URL
- title, status, level, project, environment, release, first seen, last seen
- event count and user count
- exception type and value
- top in-app stack frames
- transaction, culprit, tags, request metadata, breadcrumbs, and spans when
  relevant

2. Treat Sentry RCA, culprit, and stack traces as leads, not proof. Verify the
   real failing path in code with high-signal identifiers from the issue:

- exception type
- top in-app function and file
- transaction or entrypoint
- setting name, model, service, MCP tool, endpoint, or transport tag
- release or deployment metadata

3. Prefer the smallest production-safe fix that addresses the reported failure
   mode. Preserve observability: do not remove Sentry capture, disable
   initialization, weaken `before_send`, or downgrade real operational failures
   just to quiet an alert.

4. Preserve this repo's privacy posture. New Sentry context must go through safe
   structured tags or sanitized payloads. Keep `send_default_pii=False`,
   `include_local_variables=False`, `max_request_body_size="never"`, and the
   customer-data redaction behavior unless the user explicitly asks for a design
   change.

5. Add Google-style docstrings and thorough type hints for any new production
   functions, classes, or helpers.

6. Run the narrowest relevant fail-fast verification first. Use parallel tool
   calls for independent commands when possible. This repo does not currently
   depend on `pytest-xdist`, so use `uv run pytest -x ...` unless xdist is
   already installed.

Common focused commands:

```bash
uv run pytest -x tests/unit/test_observability.py
uv run pytest -x tests/unit/test_mcp_server.py
uv run pytest -x tests/unit/test_hosted_reference.py
uv run pytest -x path/to/test_file.py::test_name
```

For production-code changes, expand verification:

```bash
uv run ruff format --check .
uv run ruff check .
uv run mypy src tests
uv run coverage run --branch -m pytest
uv run coverage report --fail-under=100
```

Use `make validate` when risk or blast radius justifies the full gate. Use
`make build-smoke` for packaging, entrypoint, metadata, or artifact changes.

7. Check lints on touched files after substantive edits.

8. If code changed and verification passed, use Resolution Mode. In Full-Fix
   Mode, continue to the next queued issue.

## Batch Autofix Mode

Use this only when the user explicitly asks for multi-issue autofix or agent
launching.

1. Run Overview Mode and build an issue queue.
2. Launch isolated subagents only for issues with clear repo-owned stack frames.
3. Give each subagent one issue, the issue details, exact stack frames, relevant
   files, expected verification commands, and the instruction not to resolve the
   issue in Sentry.
4. Review every returned patch locally, run verification, and perform Resolution
   Mode only from the parent agent after the fix is verified.

Do not merge, push, publish, deploy, or mark unverified issues resolved from this
workflow.

## Resolution Mode

Use this mode after code changes have been made and verified, or when the user
explicitly asks to mark matching issues resolved.

Before changing Sentry status:

- Re-open or re-search the exact issue ID/URL.
- Confirm the local fix maps to the same exception, stack frame, and project.
- Confirm tests, lint, typing, and coverage appropriate to the change passed.

For verified local code fixes, call Sentry MCP `update_issue` with
`status="resolvedInNextRelease"`. Use `status="resolved"` only when the user
explicitly asks for immediate resolution and the fix is already deployed.

Never resolve noisy issues just to hide them. Prefer code fixes, narrow
filtering, safer configuration, or a runbook update.

## Output Requirements

When responding after using this skill, include:

- which Sentry issue, URL, or query was inspected
- the ranked root-cause hypothesis
- the exact code path verified
- the fix made or proposed
- tests, lint, typing, coverage, and build checks run
- whether any Sentry issue was marked `resolvedInNextRelease`, immediately
  resolved, or intentionally left unresolved
- remaining risk or follow-up work
- in Full-Fix Mode, a complete outcome summary for every issue found; never
  imply "everything is fixed" unless every found issue has a fixed,
  already-fixed, or non-code outcome with verification status

## Suggested User Triggers

This skill should activate for prompts like:

- "Check Sentry"
- "What unresolved Sentry issues do we have?"
- "Fix this Sentry error"
- "Investigate this Sentry URL"
- "Triage the top Sentry issues"
- "Launch Cursor autofix for Sentry"
- "Resolve the fixed Sentry issues"
