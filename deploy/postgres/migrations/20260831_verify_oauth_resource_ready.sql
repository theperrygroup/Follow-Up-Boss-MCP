\if :{?mcp_resource}
\else
\echo 'mcp_resource is required'
\quit 2
\endif

BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY;

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

DO $migration$
DECLARE
    target_resource TEXT := current_setting('followupboss.mcp_resource');
    access_unbound BIGINT;
    refresh_unbound BIGINT;
    access_foreign BIGINT;
    refresh_foreign BIGINT;
    access_nullable TEXT;
    refresh_nullable TEXT;
    access_default TEXT;
    refresh_default TEXT;
    expected_default TEXT := quote_literal(target_resource) || '::text';
BEGIN
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

    IF access_unbound <> 0 OR refresh_unbound <> 0 THEN
        RAISE EXCEPTION
            'deployment gate rejected unbound rows; access=%, refresh=%',
            access_unbound,
            refresh_unbound;
    END IF;
    IF access_foreign <> 0 OR refresh_foreign <> 0 THEN
        RAISE EXCEPTION
            'deployment gate rejected foreign resource rows; access=%, refresh=%',
            access_foreign,
            refresh_foreign;
    END IF;
    IF NOT (
        (
            access_nullable = 'YES'
            AND refresh_nullable = 'YES'
            AND access_default = expected_default
            AND refresh_default = expected_default
        )
        OR
        (
            access_nullable = 'NO'
            AND refresh_nullable = 'NO'
            AND access_default IS NULL
            AND refresh_default IS NULL
        )
    ) THEN
        RAISE EXCEPTION
            'deployment gate requires either the rolling or finalized resource schema';
    END IF;
END
$migration$;

\ir 20260831_oauth_resource_receipt.sql

COMMIT;
