\if :{?mcp_resource}
\else
\echo 'mcp_resource is required'
\quit 2
\endif
\if :{?lock_timeout_seconds}
\else
\echo 'lock_timeout_seconds is required'
\quit 2
\endif
\if :{?statement_timeout_seconds}
\else
\echo 'statement_timeout_seconds is required'
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
SELECT set_config('followupboss.mcp_resource', :'mcp_resource', true) AS configured \gset

\ir 20260831_oauth_resource_receipt.sql

COMMIT;
