---
name: github-actions-ci-triage
description: Triage and fix failing GitHub Actions CI, staging deploy, publish, test, coverage, lint, typecheck, audit, build, and workflow runs for this Follow Up Boss MCP Python repo with gh, failed job logs, local uv/make reproduction, strict coverage guardrails, and CI polling. Use when the user says GitHub Actions, CI, workflow, deploy, publish, test, coverage, or release validation is failing or asks to follow CI progress.
---

# GitHub Actions CI Triage

## Use This Skill

Use this as the default repo-local workflow when GitHub Actions, CI, staging
deploy, publish, release validation, tests, linting, typing, audit, build,
coverage, or workflow jobs fail for this repository. The default outcome is:
identify the exact failed workflow/job/step, map it to the smallest repo-owned
root cause, fix actionable local failures, verify with the closest local
`uv`/`make` command, and poll replacement runs when the user asks for progress.

## Read First

Before acting, read the files that own the failing surface:

- Always read `.github/workflows/ci.yml`, `Makefile`, `pyproject.toml`,
  `docs/testing.md`, and `CONTRIBUTING.md`.
- For staging deploy failures, also read `.github/workflows/deploy-staging.yml`,
  `docs/hosted-deployment-guide.md`, and `deploy/ecs/README.md`.
- For publish or tag failures, also read `.github/workflows/publish.yml`,
  `docs/release-checklist.md`, and `README.md`.
- For documentation failures, read `docs/testing.md`, `README.md`, and the
  referenced docs that the failed command names.

If multiple jobs fail, logs are large, or the failure pattern is unclear, use a
read-only subagent such as `ci-investigator` for a specific failed PR check or
`explore` for broad repo context. Ask it to return failing job names, exact
signatures, likely root cause, and local reproduction commands. Do not wait for
the subagent before collecting latest run metadata with `gh`.

## Repo CI Facts

- Default branch and deploy branch: `main`.
- Remote repo: `jp26jp/Follow-Up-Boss-MCP`.
- Main CI workflow: `.github/workflows/ci.yml`, workflow name `ci`.
- CI runs on every push branch and on pull requests.
- CI jobs:
  - `secrets`: installs Gitleaks and scans changed commits using
    `.gitleaks.toml`.
  - `quality`: runs on Ubuntu, macOS, and Windows for Python `3.12` and `3.13`.
    Non-Windows cells run `make validate`; Windows runs the equivalent commands
    inline with Bash.
  - `build`: runs on Ubuntu, macOS, and Windows for Python `3.12` after
    `secrets` and `quality`. Non-Windows cells run `make build-smoke`; Windows
    runs `uv build --clear` and `scripts/validate_build_artifacts.py`.
- Staging deploy workflow: `.github/workflows/deploy-staging.yml`, workflow name
  `deploy-staging`. It runs on pushes to `main` and `workflow_dispatch`, validates
  staging configuration, runs `make release-validate`, builds a multi-arch Docker
  image, pushes to ECR, registers an ECS task definition, and waits for service
  stability.
- Publish workflow: `.github/workflows/publish.yml`, workflow name `publish`. It
  runs on `v*` tags, runs `make release-validate`, verifies the tag matches
  `pyproject.toml` project version, builds artifacts, and publishes to PyPI.
- Package manager and runner command: `uv`.
- Coverage config lives in `pyproject.toml`; there is no `.coveragerc` or
  `.codecov.yml` in the current project. Coverage is blocking and must remain
  `100.00%` line and branch coverage for `src/followupboss_mcp`.
- Tests are deterministic and offline by default. Live Follow Up Boss checks are
  opt-in with `FOLLOWUPBOSS_RUN_LIVE_TESTS=1`.

## Pick The Mode

- Fix mode: default for "GitHub Actions are failing", "CI is red", "workflow
  failed", "deploy failed", "publish failed", or any unqualified failure report.
- Monitor mode: use when the user says "follow progress", "check again", or asks
  whether a current run is done.
- Coverage mode: use when the user mentions coverage percentage, branch
  coverage, missing coverage, Codecov, or stale coverage output.
- Report-only mode: use only when the user explicitly asks not to edit files.

## Fix Mode

1. Identify the workflow run and failed jobs.

```bash
current_branch="$(git branch --show-current)"
gh run list --workflow ci --branch "${current_branch}" --limit 10 --json databaseId,headSha,status,conclusion,createdAt,updatedAt,event,url
gh run list --workflow ci --branch main --limit 10 --json databaseId,headSha,status,conclusion,createdAt,updatedAt,event,url
gh run view <run-id> --json databaseId,status,conclusion,event,headSha,workflowName,url,jobs
gh run view <run-id> --log-failed
```

For staging deploy or publish failures, use the relevant workflow name:

```bash
gh run list --workflow deploy-staging --branch main --limit 10 --json databaseId,headSha,status,conclusion,createdAt,updatedAt,event,url
gh run list --workflow publish --limit 10 --json databaseId,headSha,status,conclusion,createdAt,updatedAt,event,url
```

2. Compare the run SHA with local state before editing.

```bash
git status -sb
git log -1 --oneline
git rev-parse HEAD
git rev-parse origin/main
```

If the fix already exists locally but is not in the failed run SHA, say that
plainly and verify the local fix. Do not overwrite unrelated local changes.

3. Extract the exact failure signature.

- workflow and run URL
- job name, including OS and Python matrix values when present
- failing step
- failing command
- failing test node, lint rule, type error, coverage file/branch, audit finding,
  build artifact, deploy command, or publish check
- assertion/error text
- file paths named by the traceback or log

For long logs, save output to a temp file and inspect it with `ReadFile` and
`rg`; do not use `cat`, `head`, `tail`, or `grep`.

```bash
gh run view <run-id> --log-failed > /tmp/followupboss-mcp-gh-run-<run-id>.log
```

4. Reproduce locally with the narrowest matching command first.

For a failing test node:

```bash
uv run pytest -x path/to/test_file.py::test_name
```

For Python-version-specific failures:

```bash
uv run --python 3.13 pytest -x path/to/test_file.py::test_name
uv run --python 3.12 pytest -x path/to/test_file.py::test_name
```

For quality job steps:

```bash
make audit
make docs-check
make format-check
make lint
make typecheck
make test
make coverage
make cli-help
make validate
```

For build job failures:

```bash
make build-smoke
uv build --clear
uv run python scripts/validate_build_artifacts.py
```

For release, staging deploy validation, or publish validation failures:

```bash
make release-validate
```

For tag/version publish failures, compare the tag to `project.version` in
`pyproject.toml`; do not publish or create tags unless the user explicitly asks.

For Gitleaks failures, treat the log as sensitive even when redacted. Identify
the committed path or pattern, remove the secret from repo-owned files, and tell
the user if credential rotation or incident handling is needed.

5. Fix the smallest verified repo-owned cause.

Prefer updating stale assertions, tests, fixtures, docs, generated artifacts,
workflow configuration, or source behavior based on what the log proves. Do not
weaken strict typing, Ruff, security scanning, build validation, or `100%`
coverage requirements to make CI pass.

Do not run live Follow Up Boss checks unless credentials are already present and
the failure is specifically about live contract behavior. Never print `.env`
contents, API keys, tokens, PyPI tokens, AWS secrets, tenant data, or customer
payloads.

6. Run the prevention-gap review before handoff.

- Explain why the existing local workflow, tests, docs, skill instructions, or
  CI workflow failed to catch the error before GitHub Actions.
- Classify the miss as one or more concrete gaps: missing local reproduction,
  too-narrow verification, stale assertion pattern, missing generated artifact
  check, environment parity gap, OS matrix mismatch, Python version mismatch,
  coverage blind spot, workflow guardrail gap, secret-scanning gap, release/tag
  mismatch, deploy configuration gap, or repo-specific pattern not yet documented.
- If the gap should be prevented for future work, update the closest repo
  guidance file: `docs/testing.md`, `CONTRIBUTING.md`, `docs/release-checklist.md`,
  `docs/hosted-deployment-guide.md`, or this skill. Add a `.cursor/rules/*.mdc`
  rule only if the repository establishes repo rules or the user asks for rules.
- Keep guidance actionable: name the trigger, the required local command or
  check, and the decision boundary for when it applies.
- If no guidance update is needed, state why the miss was one-off, already
  covered, caused by external configuration, or blocked by evidence unavailable
  locally.

7. Verify after the fix.

- Rerun the failing test node or exact local command in fail-fast mode.
- Rerun the matching Make target or `make validate` when risk justifies it.
- Run `make coverage` for production-code changes.
- Run `make build-smoke` for packaging, entrypoint, metadata, or artifact
  changes.
- Run `make release-validate` for workflow, release, staging deploy, or publish
  changes.
- Check lints for touched files with `ReadLints`.
- If workflow YAML changed, re-read the edited YAML and run the closest
  repo-local validation command available.

8. Report the result with the failed run/job, root cause, prevention-gap
analysis, guidance files changed or the reason no guidance change was made,
files changed, exact test commands and outcomes, lints checked, and whether the
fix still needs a commit, push, rerun, deployment, tag, publish, or external
configuration change before GitHub Actions can turn green.

## Monitor Mode

Use `gh run view` on the active run and summarize only jobs that are not
successful:

```bash
gh run view <run-id> --json status,conclusion,jobs
```

If all quality and build matrix jobs are green and only staging deploy, publish,
or an external-service step remains, say so and poll in short intervals when the
user asks you to keep following progress. If a new job turns red, switch to Fix
Mode with the new failed job log.

## Coverage Mode

Trace coverage from local config to CI output:

- read `.github/workflows/ci.yml`, `pyproject.toml`, `docs/testing.md`, and
  `Makefile`
- confirm coverage uses `uv run coverage run --branch -m pytest`
- confirm `coverage report --fail-under=100`
- fetch the failing quality job log and look for missing lines, missing branches,
  omitted source files, or tests skipped unexpectedly

Useful commands:

```bash
gh run view <run-id> --log-failed
make coverage
uv run coverage run --branch -m pytest
uv run coverage report --fail-under=100
uv run coverage report --show-missing
```

If the user mentions Codecov, first confirm whether Codecov was added after this
skill was written. In the current project, no Codecov workflow or `.codecov.yml`
is present, so a stale Codecov UI is not the same as a broken repository CI run.

## Recent Failure Patterns To Remember

- A failed run can be tied to an older remote SHA; always compare the run SHA,
  local `HEAD`, and `origin/main` before editing.
- Windows-only quality failures often point to path, shell, newline, encoding, or
  platform assumptions that may not reproduce perfectly on macOS.
- Python `3.13` failures can be dependency, warning, typing, or stdlib behavior
  differences even when Python `3.12` is green.
- Coverage failures are blocking here. Add focused tests for missing production
  lines or branches rather than lowering `fail_under`.
- Generated documentation or artifact checks can fail when source behavior
  changed but `docs/api-coverage-matrix.md` or build metadata was not refreshed.
- Staging deploy validation failures can be missing GitHub environment variables
  or secrets rather than repo code. Separate external configuration blockers from
  actionable repo fixes.
- Publish failures often come from tag/version mismatch or artifact validation.
  Do not publish, tag, or change credentials without explicit user direction.
- `make audit` (`pip-audit --strict`) can start failing on an unchanged lockfile
  when a new advisory is published against an already-locked dependency. The
  signature is a uniform failure across every `quality` matrix cell (all OSes and
  Python versions) that stops at `Makefile:28: audit` with `Found N known
  vulnerabilities`, while `secrets` passes and the triggering commit is unrelated
  to the flagged package. This is advisory timing, not a code regression. Fix by
  bumping only the affected package to the listed fix version with
  `uv lock --upgrade-package <name>`, then verify with `make audit` and
  `make validate`. Do not add the package to `pyproject.toml` unless `src/`
  imports it directly; a purely transitive dependency only needs the lock bump.

## Final Output

For fixes, return:

- failed workflow/job/run URL
- exact failure signature
- root cause
- why existing docs, tests, local checks, or skill instructions missed it before
  GitHub Actions
- guidance files updated, added, or the reason no guidance update was appropriate
- files changed
- tests and validation commands run, with outcomes
- lints checked
- whether GitHub Actions still needs a commit, push, rerun, deployment, tag,
  publish, or external configuration refresh

For monitoring, return:

- run status and conclusion
- remaining non-green jobs
- whether any failure needs Fix Mode
