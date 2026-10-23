.DEFAULT_GOAL := help

.PHONY: help sync audit docs-check format-check lint typecheck test auth-test auth-client-check coverage cli-help live-identity-check live-contract-check validate build build-smoke release-validate

help:
	@printf "%s\n" \
		"make sync             Install locked project dependencies with uv" \
		"make audit            Run the dependency audit" \
		"make docs-check       Validate markdown links and MCP usage docs" \
		"make format-check     Check Ruff formatting" \
		"make lint             Run Ruff lint checks" \
		"make typecheck        Run mypy" \
		"make test             Run pytest" \
		"make auth-test        Run deterministic OAuth and authenticated MCP contracts" \
		"make auth-client-check Check current public ChatGPT and Codex client metadata" \
		"make coverage         Run branch coverage and enforce 100%%" \
		"make cli-help         Check the CLI entrypoint" \
		"make live-identity-check Run the optional live identity sandbox check" \
		"make live-contract-check Run the broader optional live contract suite" \
		"make validate         Run the full local validation stack" \
		"make build            Build sdist and wheel artifacts" \
		"make build-smoke      Build artifacts and validate wheel install/CLI" \
		"make release-validate Run validation plus build smoke checks"

sync:
	uv sync --frozen

audit:
	uv export --format requirements.txt --all-groups --locked --no-editable --no-emit-project --output-file /tmp/followupboss-mcp-requirements.txt
	uvx --from pip-audit pip-audit -r /tmp/followupboss-mcp-requirements.txt --strict --disable-pip --no-deps

docs-check:
	uv run python scripts/validate_docs_links.py

format-check:
	uv run ruff format --check .

lint:
	uv run ruff check .

typecheck:
	uv run mypy src tests

test:
	uv run pytest

auth-test:
	uv run --frozen pytest tests/integration/test_oauth_lifecycle.py tests/integration/test_hosted_auth_integration.py tests/unit/test_hosted_oauth.py tests/unit/test_cimd.py tests/unit/test_public_oauth_workflow.py

auth-client-check:
	uv run --frozen python scripts/verify_public_oauth.py --metadata-only

coverage:
	uv run coverage run --branch -m pytest
	uv run coverage report --fail-under=100

cli-help:
	uv run python -m followupboss_mcp.cli --help

live-identity-check:
	if [ -f ".env" ]; then set -a; . ".env"; set +a; fi; uv run pytest tests/live/test_identity_sandbox.py -m live

live-contract-check:
	if [ -f ".env" ]; then set -a; . ".env"; set +a; fi; uv run pytest tests/live -m live

validate:
	$(MAKE) sync
	$(MAKE) audit
	$(MAKE) docs-check
	$(MAKE) format-check
	$(MAKE) lint
	$(MAKE) typecheck
	$(MAKE) test
	$(MAKE) coverage
	$(MAKE) cli-help

build:
	uv build --clear

build-smoke: build
	uv run python scripts/validate_build_artifacts.py

release-validate:
	$(MAKE) validate
	$(MAKE) build-smoke
