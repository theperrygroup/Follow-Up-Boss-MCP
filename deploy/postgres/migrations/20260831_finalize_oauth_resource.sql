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
LOCK TABLE hosted_access_tokens, hosted_oauth_refresh_tokens
    IN ACCESS EXCLUSIVE MODE;

DO $migration$
DECLARE
    target_resource TEXT := current_setting('followupboss.mcp_resource');
    expected_default TEXT := quote_literal(target_resource) || '::text';
    access_unbound BIGINT;
    refresh_unbound BIGINT;
    access_foreign BIGINT;
    refresh_foreign BIGINT;
    access_nullable TEXT;
    refresh_nullable TEXT;
    access_default TEXT;
    refresh_default TEXT;
    rolling_schema BOOLEAN;
    finalized_schema BOOLEAN;
BEGIN
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

    rolling_schema := access_nullable IS NOT DISTINCT FROM 'YES'
        AND refresh_nullable IS NOT DISTINCT FROM 'YES'
        AND access_default IS NOT DISTINCT FROM expected_default
        AND refresh_default IS NOT DISTINCT FROM expected_default;
    finalized_schema := access_nullable IS NOT DISTINCT FROM 'NO'
        AND refresh_nullable IS NOT DISTINCT FROM 'NO'
        AND access_default IS NULL
        AND refresh_default IS NULL;
    IF NOT (rolling_schema OR finalized_schema) THEN
        RAISE EXCEPTION 'finalize requires the canonical rolling or finalized schema state';
    END IF;

    SELECT
        COUNT(*) FILTER (WHERE resource IS NULL),
        COUNT(*) FILTER (
            WHERE resource IS NOT NULL AND resource <> target_resource
        )
    INTO access_unbound, access_foreign
    FROM hosted_access_tokens;

    SELECT
        COUNT(*) FILTER (WHERE resource IS NULL),
        COUNT(*) FILTER (
            WHERE resource IS NOT NULL AND resource <> target_resource
        )
    INTO refresh_unbound, refresh_foreign
    FROM hosted_oauth_refresh_tokens;

    IF access_unbound <> 0 OR refresh_unbound <> 0 THEN
        RAISE EXCEPTION
            'cannot finalize with unbound rows; access=%, refresh=%',
            access_unbound,
            refresh_unbound;
    END IF;
    IF access_foreign <> 0 OR refresh_foreign <> 0 THEN
        RAISE EXCEPTION
            'cannot finalize with foreign resource rows; access=%, refresh=%',
            access_foreign,
            refresh_foreign;
    END IF;
END
$migration$;

-- New writers always supply resource explicitly. Remove the compatibility
-- default before enforcing the final schema contract.
ALTER TABLE hosted_access_tokens
    ALTER COLUMN resource DROP DEFAULT;
ALTER TABLE hosted_oauth_refresh_tokens
    ALTER COLUMN resource DROP DEFAULT;

ALTER TABLE hosted_access_tokens
    ALTER COLUMN resource SET NOT NULL;
ALTER TABLE hosted_oauth_refresh_tokens
    ALTER COLUMN resource SET NOT NULL;

\ir 20260831_oauth_resource_receipt.sql

COMMIT;
