\if :{?migration_phase}
\else
\echo 'migration_phase is required'
\quit 2
\endif

\pset format unaligned
\pset tuples_only on

WITH access_status AS (
    SELECT
        COUNT(*)::bigint AS total_rows,
        COUNT(*) FILTER (WHERE resource IS NULL)::bigint AS unbound_rows,
        COUNT(*) FILTER (WHERE resource = :'mcp_resource')::bigint AS expected_resource_rows,
        COUNT(*) FILTER (
            WHERE resource IS NOT NULL AND resource <> :'mcp_resource'
        )::bigint AS foreign_resource_rows
    FROM hosted_access_tokens
),
refresh_status AS (
    SELECT
        COUNT(*)::bigint AS total_rows,
        COUNT(*) FILTER (WHERE resource IS NULL)::bigint AS unbound_rows,
        COUNT(*) FILTER (WHERE resource = :'mcp_resource')::bigint AS expected_resource_rows,
        COUNT(*) FILTER (
            WHERE resource IS NOT NULL AND resource <> :'mcp_resource'
        )::bigint AS foreign_resource_rows
    FROM hosted_oauth_refresh_tokens
),
column_status AS (
    SELECT
        table_name,
        is_nullable,
        COALESCE(
            column_default = quote_literal(:'mcp_resource') || '::text',
            false
        ) AS has_canonical_default
    FROM information_schema.columns
    WHERE table_schema = current_schema()
      AND table_name IN ('hosted_access_tokens', 'hosted_oauth_refresh_tokens')
      AND column_name = 'resource'
)
SELECT 'MIGRATION_RECEIPT=' || json_build_object(
    'phase', :'migration_phase',
    'resource', :'mcp_resource',
    'access', json_build_object(
        'total_rows', access_status.total_rows,
        'unbound_rows', access_status.unbound_rows,
        'expected_resource_rows', access_status.expected_resource_rows,
        'foreign_resource_rows', access_status.foreign_resource_rows,
        'is_nullable', access_column.is_nullable,
        'has_canonical_default', access_column.has_canonical_default
    ),
    'refresh', json_build_object(
        'total_rows', refresh_status.total_rows,
        'unbound_rows', refresh_status.unbound_rows,
        'expected_resource_rows', refresh_status.expected_resource_rows,
        'foreign_resource_rows', refresh_status.foreign_resource_rows,
        'is_nullable', refresh_column.is_nullable,
        'has_canonical_default', refresh_column.has_canonical_default
    )
)::text
FROM access_status
CROSS JOIN refresh_status
LEFT JOIN column_status AS access_column
    ON access_column.table_name = 'hosted_access_tokens'
LEFT JOIN column_status AS refresh_column
    ON refresh_column.table_name = 'hosted_oauth_refresh_tokens';
