-- Expand-only migration for MCP 2026-07-28 OAuth resource indicators.
--
-- Apply this before deploying the resource-aware application. Keeping the new
-- columns nullable makes the migration compatible with the previous release
-- during a rolling deployment. The new verifier rejects NULL resources, while
-- the new issuer always writes the configured canonical MCP resource. The
-- temporary default binds rows inserted by old writers to that same resource.

\if :{?mcp_resource}
\else
\echo 'mcp_resource is required'
\quit 2
\endif

BEGIN;

SELECT set_config(
    'lock_timeout',
    :'lock_timeout_seconds' || 's',
    true
) AS lock_timeout_set \gset
SELECT set_config(
    'statement_timeout',
    :'statement_timeout_seconds' || 's',
    true
) AS statement_timeout_set \gset
SELECT set_config('followupboss.mcp_resource', :'mcp_resource', true) AS resource_set \gset
SELECT pg_advisory_xact_lock(hashtext('followupboss:mcp:oauth-resource-migration:v1'));

-- Hold both writer locks through the state check, any DDL, and the receipt.
-- This makes retry behavior deterministic and prevents a concurrent insert
-- from invalidating the state proved by this transaction.
LOCK TABLE hosted_access_tokens, hosted_oauth_refresh_tokens
    IN ACCESS EXCLUSIVE MODE;

DO $migration$
DECLARE
    target_resource TEXT := current_setting('followupboss.mcp_resource');
    expected_default TEXT := quote_literal(target_resource) || '::text';
    access_exists BOOLEAN;
    refresh_exists BOOLEAN;
    access_nullable TEXT;
    refresh_nullable TEXT;
    access_default TEXT;
    refresh_default TEXT;
    access_unbound BIGINT;
    refresh_unbound BIGINT;
    access_foreign BIGINT;
    refresh_foreign BIGINT;
BEGIN
    SELECT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = 'hosted_access_tokens'
          AND column_name = 'resource'
    ) INTO access_exists;
    SELECT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = current_schema()
          AND table_name = 'hosted_oauth_refresh_tokens'
          AND column_name = 'resource'
    ) INTO refresh_exists;

    IF access_exists <> refresh_exists THEN
        RAISE EXCEPTION 'resource expand rejected a partially applied schema';
    END IF;

    IF NOT access_exists THEN
        -- These constant defaults are intentionally temporary. They preserve
        -- cross-version writes while old application instances omit resource.
        EXECUTE 'ALTER TABLE hosted_access_tokens ADD COLUMN resource TEXT NULL';
        EXECUTE 'ALTER TABLE hosted_oauth_refresh_tokens ADD COLUMN resource TEXT NULL';
        EXECUTE format(
            'ALTER TABLE hosted_access_tokens ALTER COLUMN resource SET DEFAULT %L',
            target_resource
        );
        EXECUTE format(
            'ALTER TABLE hosted_oauth_refresh_tokens ALTER COLUMN resource SET DEFAULT %L',
            target_resource
        );
        RETURN;
    END IF;

    SELECT is_nullable, column_default
    INTO access_nullable, access_default
    FROM information_schema.columns
    WHERE table_schema = current_schema()
      AND table_name = 'hosted_access_tokens'
      AND column_name = 'resource';
    SELECT is_nullable, column_default
    INTO refresh_nullable, refresh_default
    FROM information_schema.columns
    WHERE table_schema = current_schema()
      AND table_name = 'hosted_oauth_refresh_tokens'
      AND column_name = 'resource';

    EXECUTE 'SELECT COUNT(*) FILTER (WHERE resource IS NULL), '
        || 'COUNT(*) FILTER (WHERE resource IS NOT NULL AND resource <> $1) '
        || 'FROM hosted_access_tokens'
    INTO access_unbound, access_foreign
    USING target_resource;
    EXECUTE 'SELECT COUNT(*) FILTER (WHERE resource IS NULL), '
        || 'COUNT(*) FILTER (WHERE resource IS NOT NULL AND resource <> $1) '
        || 'FROM hosted_oauth_refresh_tokens'
    INTO refresh_unbound, refresh_foreign
    USING target_resource;

    IF access_foreign <> 0 OR refresh_foreign <> 0 THEN
        RAISE EXCEPTION
            'resource expand rejected foreign rows; access=%, refresh=%',
            access_foreign,
            refresh_foreign;
    END IF;

    IF access_nullable = 'YES'
       AND refresh_nullable = 'YES'
       AND access_default = expected_default
       AND refresh_default = expected_default THEN
        RETURN;
    END IF;

    IF access_nullable = 'NO'
       AND refresh_nullable = 'NO'
       AND access_default IS NULL
       AND refresh_default IS NULL
       AND access_unbound = 0
       AND refresh_unbound = 0 THEN
        RETURN;
    END IF;

    RAISE EXCEPTION 'resource expand rejected an unexpected existing schema state';
END
$migration$;

\ir 20260831_oauth_resource_receipt.sql

COMMIT;

-- Do not hand-edit or delete legacy rows here. Use
-- scripts/migrate_hosted_oauth_resource.py for the explicit-resource backfill,
-- postcondition checks, final NOT NULL constraint, and reversible constraint
-- rollback.
