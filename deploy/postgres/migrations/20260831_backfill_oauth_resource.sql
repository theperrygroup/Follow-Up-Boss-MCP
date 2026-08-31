\if :{?mcp_resource}
\else
\echo 'mcp_resource is required'
\quit 2
\endif
\if :{?expected_access_unbound}
\else
\echo 'expected_access_unbound is required'
\quit 2
\endif
\if :{?expected_refresh_unbound}
\else
\echo 'expected_refresh_unbound is required'
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
SELECT set_config(
    'followupboss.expected_access_unbound',
    :'expected_access_unbound',
    true
) AS expected_access_set \gset
SELECT set_config(
    'followupboss.expected_refresh_unbound',
    :'expected_refresh_unbound',
    true
) AS expected_refresh_set \gset
SELECT pg_advisory_xact_lock(hashtext('followupboss:mcp:oauth-resource-migration:v1'));
LOCK TABLE hosted_access_tokens, hosted_oauth_refresh_tokens
    IN SHARE ROW EXCLUSIVE MODE;

DO $migration$
DECLARE
    target_resource TEXT := current_setting('followupboss.mcp_resource');
    expected_default TEXT := quote_literal(target_resource) || '::text';
    expected_access BIGINT := current_setting(
        'followupboss.expected_access_unbound'
    )::bigint;
    expected_refresh BIGINT := current_setting(
        'followupboss.expected_refresh_unbound'
    )::bigint;
    access_unbound BIGINT;
    refresh_unbound BIGINT;
    access_foreign BIGINT;
    refresh_foreign BIGINT;
    access_nullable TEXT;
    refresh_nullable TEXT;
    access_default TEXT;
    refresh_default TEXT;
BEGIN
    IF target_resource = '' THEN
        RAISE EXCEPTION 'mcp_resource must not be empty';
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

    IF access_nullable IS DISTINCT FROM 'YES'
       OR refresh_nullable IS DISTINCT FROM 'YES'
       OR access_default IS DISTINCT FROM expected_default
       OR refresh_default IS DISTINCT FROM expected_default THEN
        RAISE EXCEPTION 'backfill requires the canonical rolling schema state';
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

    IF access_foreign <> 0 OR refresh_foreign <> 0 THEN
        RAISE EXCEPTION
            'foreign resource rows found; access=%, refresh=%',
            access_foreign,
            refresh_foreign;
    END IF;
    IF access_unbound <> expected_access OR refresh_unbound <> expected_refresh THEN
        RAISE EXCEPTION
            'unbound counts changed; access expected=% actual=%, refresh expected=% actual=%',
            expected_access,
            access_unbound,
            expected_refresh,
            refresh_unbound;
    END IF;

    UPDATE hosted_access_tokens
    SET resource = target_resource
    WHERE resource IS NULL;

    UPDATE hosted_oauth_refresh_tokens
    SET resource = target_resource
    WHERE resource IS NULL;

    IF EXISTS (SELECT 1 FROM hosted_access_tokens WHERE resource IS NULL)
       OR EXISTS (SELECT 1 FROM hosted_oauth_refresh_tokens WHERE resource IS NULL) THEN
        RAISE EXCEPTION 'resource backfill postcondition failed';
    END IF;
END
$migration$;

\ir 20260831_oauth_resource_receipt.sql

COMMIT;
