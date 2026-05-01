---
name: writing-documentation
description: Write, revise, and review software documentation including READMEs, architecture docs, API docs, examples, troubleshooting guides, and release notes. Use when the user asks to create docs, update docs after code changes, improve documentation clarity, or document project workflows.
---

# Writing Documentation

## Core Workflow

1. Identify the audience, purpose, and maintenance owner before writing.
2. Read nearby documentation and the relevant source code before making technical claims.
3. Preserve repository terminology, command style, environment variable names, and file path conventions.
4. Prefer short, actionable sections over broad explanations.
5. Include examples when they remove ambiguity or make a workflow easier to verify.
6. Keep claims tied to current code, tests, configuration, or linked official documentation.

## Documentation Types

- **README updates**: Lead with what the project does, how to install it, how to run it, and where deeper docs live.
- **Architecture docs**: Explain responsibilities, boundaries, dependencies, and data flow. Use diagrams only when they clarify relationships.
- **API docs**: Document inputs, outputs, auth, errors, pagination, rate limits, and examples from the implemented behavior.
- **Examples and guides**: Favor copy-pasteable commands and explain expected outcomes.
- **Troubleshooting docs**: Start with symptoms, then likely causes, then concrete fixes.
- **Release notes and changelogs**: Group by user-visible impact, compatibility notes, migrations, and verification steps.

## Style Rules

- Use plain engineering prose and concise headings.
- Prefer active voice and specific nouns.
- Avoid unsupported marketing language, vague guarantees, and stale roadmap claims.
- Use fenced code blocks for commands or multi-line examples.
- Wrap commands, environment variables, paths, and identifiers in backticks.
- Keep tables only when comparison or scanning is meaningfully easier than prose.
- Do not expose secrets, `.env` values, tokens, API keys, or customer data.

## Accuracy Checks

Before editing docs:

1. Search for existing docs covering the same topic.
2. Read the source code, tests, scripts, or configuration that prove the documented behavior.
3. Prefer official upstream docs as authority for third-party behavior.
4. If behavior is uncertain, inspect or run the relevant command instead of guessing.

After editing docs:

1. Re-read changed sections for broken links, stale file paths, and unsupported claims.
2. Confirm commands match the repository's package manager and Makefile conventions.
3. Verify examples do not require hidden local state unless explicitly documented.

## Repository Checks

For this repository:

- Run `make docs-check` for documentation-only changes.
- Run `make validate` when documentation changes are coupled to code, examples, scripts, or package behavior.
- Keep references consistent with `README.md`, `docs/architecture.md`, `docs/testing.md`, and `docs/security.md` when those topics are involved.
- Treat official Follow Up Boss API documentation and official MCP documentation as source-of-truth references for external behavior.
