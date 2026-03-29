.DEFAULT_GOAL := help

.PHONY: help sync audit format-check lint typecheck test coverage cli-help live-identity-check validate build build-smoke release-validate

help:
	@printf "%s\n" \
		"make sync             Install locked project dependencies with uv" \
		"make audit            Run the dependency audit" \
		"make format-check     Check Ruff formatting" \
		"make lint             Run Ruff lint checks" \
		"make typecheck        Run mypy" \
		"make test             Run pytest" \
		"make coverage         Run branch coverage and enforce 100%%" \
		"make cli-help         Check the CLI entrypoint" \
		"make live-identity-check Run the optional live identity sandbox check" \
		"make validate         Run the full local validation stack" \
		"make build            Build sdist and wheel artifacts" \
		"make build-smoke      Build artifacts and validate wheel install/CLI" \
		"make release-validate Run validation plus build smoke checks"

sync:
	uv sync --frozen

audit:
	uv export --format requirements.txt --all-groups --locked --no-editable --no-emit-project --output-file /tmp/followupboss-mcp-requirements.txt
	uvx --from pip-audit pip-audit -r /tmp/followupboss-mcp-requirements.txt --strict --disable-pip --no-deps --ignore-vuln CVE-2026-4539

format-check:
	uv run ruff format --check .

lint:
	uv run ruff check .

typecheck:
	uv run mypy src tests

test:
	uv run pytest

coverage:
	uv run coverage run --branch -m pytest
	uv run coverage report --fail-under=100

cli-help:
	uv run python -m followupboss_mcp.cli --help

live-identity-check:
	uv run pytest tests/live/test_identity_sandbox.py -m live

validate:
	$(MAKE) sync
	$(MAKE) audit
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
