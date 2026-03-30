# Release Checklist

## Before Tagging

1. Regenerate the Follow Up Boss docs artifacts:

   ```bash
   uv run python scripts/ingest_followupboss_docs.py
   uv run python scripts/validate_api_coverage.py
   ```

2. Confirm the generated artifacts changed only in ways explained by official docs updates:

   - `docs/followupboss-endpoint-manifest.json`
   - `docs/followupboss-doc-ingestion.md`
   - `docs/api-coverage-matrix.md`

3. Run the complete quality gate:

   ```bash
   make validate
   ```

   For release artifacts:

   ```bash
   make build-smoke
   ```

   For broader upstream contract confidence when sandbox credentials are available:

   ```bash
   FOLLOWUPBOSS_RUN_LIVE_TESTS=1 make live-contract-check
   ```

## Security Checks

4. Confirm no secrets or real customer payloads are present in tracked files.
5. Confirm logging still redacts `Authorization` and `X-System-Key`.
6. Confirm webhook verification still uses the exact raw request body bytes.
7. Review [security-incident-playbook.md](security-incident-playbook.md) if any credential or webhook key changed during the release cycle.

## Documentation Checks

8. Run the automated docs validation gate:

   ```bash
   make docs-check
   ```

9. Verify `README.md` matches the current tool surface, examples, and commands.
10. Verify `docs/mcp-usage.md` matches the registered MCP tools, resource, and prompt.
11. Verify `docs/final-validation-report.md` reflects the latest validation run.
12. Verify `CONTRIBUTING.md` still matches the current development workflow and package layout.

## Release Readiness

13. Confirm the API coverage matrix still marks deferred endpoints explicitly, or states clearly that none remain in scope.
14. Confirm examples still execute against the current package layout.
15. Confirm CI is green on the release candidate commit.
