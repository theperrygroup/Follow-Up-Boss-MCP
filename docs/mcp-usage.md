# MCP Usage

## Operating Modes

The repository now supports two intentionally different runtime shapes:

| Mode | Transport | Intended use | Follow Up Boss credential source |
| --- | --- | --- | --- |
| Local single-tenant | `stdio` or `streamable-http` | local development, MCP Inspector, focused tests | `FollowUpBossSettings` loaded from environment variables |
| Hosted multi-tenant | `streamable-http` only | shared customer-facing deployment | `TenantStore` lookup on each authenticated call |

`stdio` remains an explicit local-development-only path. Hosted deployments should expose only
`streamable-http`.

## Local Development

Run the local server with:

```bash
uv run python -m followupboss_mcp.cli stdio
uv run python -m followupboss_mcp.cli streamable-http --host 127.0.0.1 --port 8000 --path /mcp
```

These CLI commands still create one local single-tenant runtime from `FollowUpBossSettings`. They
are useful for manual inspection and development tooling, but they do not represent the hosted
multi-tenant contract.

## Hosted Authentication Contract

Hosted `streamable-http` deployments add a separate inbound bearer-token layer in front of the
Follow Up Boss client:

- Every hosted request to tools, resources, and prompts must send `Authorization: Bearer <token>`.
- FastMCP resource-server settings come from `HostedAuthSettings`.
- Actual token verification is delegated to a deployment-specific `HostedIdentityVerifier`.
- The verifier may be backed by signed JWTs, opaque token lookup, or another auth system, as long
  as it returns the canonical `HostedVerifiedIdentity` payload.
- Required verified identity fields are `tenant_id`, `subject`, and `client_id`.
- Optional verified identity fields are `scopes`, `expires_at`, `token_id`, and `credential_id`.
- `tenant_id` is always resolved through `TenantStore` before any `FollowUpBossAsyncClient` is
  created.
- When `credential_id` is present, it must match the tenant's currently active stored credential.
- Hosted mode exposes no intentionally public tools, resources, or prompts.

When auth fails, the hosted endpoint fails closed before any upstream Follow Up Boss credential is
used. The common client-visible response is:

```json
{"error":"invalid_token","error_description":"Authentication required"}
```

When hosted endpoint rate limiting is configured in fail-closed mode and the limiter backend is
unavailable, the client receives `503 temporarily_unavailable` with `Retry-After` instead of
falling through to tenant runtime creation.

## Hosted Runtime Model

Hosted runtime wiring is request-scoped rather than session-scoped:

1. FastMCP auth middleware verifies the inbound bearer token.
2. `HostedTenantTokenVerifier` resolves the token's `tenant_id` to one active tenant and
   credential pair in `TenantStore`.
3. FastMCP stores a `HostedAccessToken` containing the verified identity and an auth-safe tenant
   context.
4. For each tool, resource, or prompt call, `TenantRuntimeFactory` re-resolves the current tenant
   from `TenantStore`.
5. The runtime factory projects the stored credential into `FollowUpBossTenantSettings` while
   inheriting shared `base_url`, `timeout_seconds`, and `max_retries` defaults.
6. A fresh `FollowUpBossAsyncClient` and typed service bundle are created for that call and closed
   afterward.

This makes bearer-token revocation and tenant credential rotation visible on the next request, and
it prevents one caller from reusing another tenant's Follow Up Boss client state.

## Runtime Configuration

The runtime settings are split deliberately:

- `FollowUpBossServerSettings` owns bootstrap-only fields such as `transport`, `host`, `port`,
  `streamable_http_path`, and `log_level`.
- `HostedAuthSettings` owns the FastMCP resource-server auth configuration for hosted deployments:
  `issuer_url`, `resource_server_url`, and optional `required_scopes`.
- `FollowUpBossTenantRuntimeDefaults` owns the shared non-secret hosted HTTP-client defaults:
  `base_url`, `timeout_seconds`, and `max_retries`.
- `FollowUpBossTenantSettings` owns one tenant's Follow Up Boss credential and HTTP-client fields
  such as `auth_mode`, `api_key`, `access_token`, `system_name`, `system_key`, plus the inherited
  `base_url`, `timeout_seconds`, and `max_retries` values used by the actual upstream client.
- `FollowUpBossSettings` remains as the backward-compatible composite model used by the local CLI
  and examples.

The server-only environment variables are:

- `FOLLOWUPBOSS_TRANSPORT`
- `FOLLOWUPBOSS_HOST`
- `FOLLOWUPBOSS_PORT`
- `FOLLOWUPBOSS_STREAMABLE_HTTP_PATH`
- `FOLLOWUPBOSS_LOG_LEVEL`

When hosted auth is enabled and no explicit `FollowUpBossTenantRuntimeDefaults` object is passed,
the server uses built-in Follow Up Boss client defaults rather than reading process-wide tenant
credential environment variables.

The current local single-tenant runtime variables remain:

- `FOLLOWUPBOSS_AUTH_MODE`
- `FOLLOWUPBOSS_API_KEY`
- `FOLLOWUPBOSS_ACCESS_TOKEN`
- `FOLLOWUPBOSS_SYSTEM_NAME`
- `FOLLOWUPBOSS_SYSTEM_KEY`
- `FOLLOWUPBOSS_X_SYSTEM`
- `FOLLOWUPBOSS_X_SYSTEM_KEY`
- `FOLLOWUPBOSS_BASE_URL`
- `FOLLOWUPBOSS_TIMEOUT_SECONDS`
- `FOLLOWUPBOSS_MAX_RETRIES`

Hosted deployments should use the server-only environment variables for process bootstrap.
Customer-specific Follow Up Boss credentials should come from `TenantStore`, not process-wide
environment variables.

`FOLLOWUPBOSS_SYSTEM_NAME` and `FOLLOWUPBOSS_SYSTEM_KEY` map to the outbound `X-System` and
`X-System-Key` headers. The `FOLLOWUPBOSS_X_SYSTEM` and `FOLLOWUPBOSS_X_SYSTEM_KEY` aliases are
also accepted, along with the legacy `FOLLOW_UP_BOSS_*` forms. Those values come from the Follow Up
Boss system-registration flow described in
[Registration and Identification](https://docs.followupboss.com/reference/identification). Some
Follow Up Boss endpoints, especially integration-specific attachment or webhook paths, can require
those headers even when basic account auth succeeds.

For local hosted-style testing, `DevelopmentTenantStore.from_local_dev_settings(...)` and
`DevelopmentHostedTokenVerifier` provide a development-safe bridge without changing the local CLI
contract.

## Tool Namespace

All tools are namespaced with the `followupboss_` prefix.

| Tool | Purpose |
| --- | --- |
| `followupboss_get_identity` | Return identity information for the authenticated Follow Up Boss account and user. |
| `followupboss_get_me` | Retrieve the current Follow Up Boss user profile with sensitive keys redacted. |
| `followupboss_search_people` | Search people with documented filters and pagination metadata. |
| `followupboss_get_person` | Retrieve one person by ID. |
| `followupboss_create_person` | Create a person directly. |
| `followupboss_update_person` | Update a person directly. |
| `followupboss_delete_person` | Delete a person by ID and return a structured confirmation. |
| `followupboss_check_duplicate_person` | Check whether a person already exists by email or phone. |
| `followupboss_list_unclaimed_people` | List unclaimed leads available to the authenticated user. |
| `followupboss_claim_person` | Claim an unclaimed lead by person ID. |
| `followupboss_ignore_unclaimed_person` | Ignore an unclaimed lead offer by person ID and return a structured confirmation. |
| `followupboss_search_events` | Search events with pagination metadata and supported event filters. |
| `followupboss_get_event` | Retrieve one event by ID. |
| `followupboss_send_event` | Send a canonical `POST /events` lead or lead-activity payload. |
| `followupboss_list_users` | List users with pagination metadata. |
| `followupboss_get_user` | Retrieve one user by ID. |
| `followupboss_delete_user` | Delete a user by ID, require a reassignment target, and return a structured confirmation. |
| `followupboss_list_custom_fields` | List available Follow Up Boss custom fields. |
| `followupboss_get_custom_field` | Retrieve one custom field by ID. |
| `followupboss_create_custom_field` | Create a custom field. |
| `followupboss_update_custom_field` | Update one custom field by ID. |
| `followupboss_delete_custom_field` | Delete one custom field by ID and return a structured confirmation. |
| `followupboss_list_email_campaigns` | List email marketing campaigns. |
| `followupboss_create_email_campaign` | Create an email marketing campaign. |
| `followupboss_update_email_campaign` | Update one email marketing campaign by ID. |
| `followupboss_list_email_events` | List email marketing events. |
| `followupboss_send_email_events` | Post batched email marketing events. |
| `followupboss_list_deals` | List deals with documented filters and pagination metadata. |
| `followupboss_get_deal` | Retrieve one deal by ID. |
| `followupboss_create_deal` | Create a deal. |
| `followupboss_update_deal` | Update one deal by ID. |
| `followupboss_delete_deal` | Delete one deal by ID and return a structured confirmation. |
| `followupboss_list_deal_custom_fields` | List deal custom fields with pagination metadata for valid write-time field names. |
| `followupboss_get_deal_custom_field` | Retrieve one deal custom field by ID. |
| `followupboss_create_deal_custom_field` | Create a deal custom field. |
| `followupboss_update_deal_custom_field` | Update one deal custom field by ID. |
| `followupboss_delete_deal_custom_field` | Delete one deal custom field by ID and return a structured confirmation. |
| `followupboss_list_pipelines` | List pipelines with exact-name filtering and pagination metadata. |
| `followupboss_get_pipeline` | Retrieve one pipeline by ID. |
| `followupboss_create_pipeline` | Create a pipeline. |
| `followupboss_update_pipeline` | Update one pipeline by ID. |
| `followupboss_delete_pipeline` | Delete one pipeline by ID and return a structured confirmation. |
| `followupboss_list_ponds` | List ponds with pagination metadata. |
| `followupboss_get_pond` | Retrieve one pond by ID. |
| `followupboss_create_pond` | Create a pond. |
| `followupboss_update_pond` | Update one pond by ID. |
| `followupboss_delete_pond` | Delete one pond by ID, require a reassignment target, and return a structured confirmation. |
| `followupboss_list_smart_lists` | List smart lists with documented filters and pagination metadata. |
| `followupboss_get_smart_list` | Retrieve one smart list by ID. |
| `followupboss_list_stages` | List stages with documented filters and pagination metadata. |
| `followupboss_get_stage` | Retrieve one stage by ID. |
| `followupboss_create_stage` | Create a stage. |
| `followupboss_update_stage` | Update one stage by ID. |
| `followupboss_delete_stage` | Delete one stage by ID, require a reassignment target, and return a structured confirmation. |
| `followupboss_list_appointment_outcomes` | List appointment outcomes with pagination metadata. |
| `followupboss_get_appointment_outcome` | Retrieve one appointment outcome by ID. |
| `followupboss_create_appointment_outcome` | Create an appointment outcome. |
| `followupboss_update_appointment_outcome` | Update one appointment outcome by ID. |
| `followupboss_delete_appointment_outcome` | Delete one appointment outcome by ID, require a reassignment target, and return a structured confirmation. |
| `followupboss_list_appointment_types` | List appointment types with pagination metadata. |
| `followupboss_get_appointment_type` | Retrieve one appointment type by ID. |
| `followupboss_create_appointment_type` | Create an appointment type. |
| `followupboss_update_appointment_type` | Update one appointment type by ID. |
| `followupboss_delete_appointment_type` | Delete one appointment type by ID, require a reassignment target, and return a structured confirmation. |
| `followupboss_list_automations` | List automations with documented filters and pagination metadata. |
| `followupboss_get_automation` | Retrieve one automation by ID. |
| `followupboss_list_automation_people` | List automation-person pairings with documented filters. |
| `followupboss_get_automation_person` | Retrieve one automation-person pairing by ID. |
| `followupboss_trigger_automation` | Trigger an automation for a specific person. |
| `followupboss_update_automation_person` | Pause or resume one automation-person pairing by ID. |
| `followupboss_list_inbox_app_installations` | List installed inbox app installations for a published inbox app. |
| `followupboss_install_inbox_app` | Install an inbox app for an account or user scope. |
| `followupboss_deactivate_inbox_app` | Deactivate an inbox app installation by ID. |
| `followupboss_add_inbox_app_message` | Add a message to an inbox app conversation. |
| `followupboss_add_inbox_app_note` | Add a note to an inbox app conversation. |
| `followupboss_list_inbox_app_participants` | List participants in an inbox app conversation. |
| `followupboss_add_inbox_app_participant` | Add a participant to an inbox app conversation. |
| `followupboss_update_inbox_app_conversation` | Update an inbox app conversation by external conversation ID. |
| `followupboss_update_inbox_app_message` | Update an inbox app message by ID or external message ID. |
| `followupboss_remove_inbox_app_participant` | Remove a participant from an inbox app conversation. |
| `followupboss_list_people_relationships` | List people relationships. |
| `followupboss_get_people_relationship` | Retrieve one people relationship by ID. |
| `followupboss_create_people_relationship` | Create a people relationship for a person. |
| `followupboss_update_people_relationship` | Update one people relationship by ID. |
| `followupboss_delete_people_relationship` | Delete one people relationship by ID and return a structured confirmation. |
| `followupboss_get_person_attachment` | Retrieve one person attachment by ID. |
| `followupboss_create_person_attachment` | Create a person attachment record. |
| `followupboss_update_person_attachment` | Update one person attachment by ID. |
| `followupboss_delete_person_attachment` | Delete one person attachment by ID and return a structured confirmation. |
| `followupboss_get_deal_attachment` | Retrieve one deal attachment by ID. |
| `followupboss_create_deal_attachment` | Create a deal attachment record. |
| `followupboss_update_deal_attachment` | Update one deal attachment by ID. |
| `followupboss_delete_deal_attachment` | Delete one deal attachment by ID and return a structured confirmation. |
| `followupboss_get_reaction` | Retrieve one reaction by ID. |
| `followupboss_add_reaction` | Add a reaction to a note, call, or threaded reply. |
| `followupboss_delete_reaction` | Delete a reaction from a note, call, or threaded reply. |
| `followupboss_get_threaded_reply` | Retrieve one threaded reply by ID. |
| `followupboss_list_action_plans` | List action plans with documented filters and pagination metadata. |
| `followupboss_list_action_plan_people` | List action-plan-person relationships with documented filters. |
| `followupboss_apply_action_plan` | Apply an action plan to a specific person. |
| `followupboss_update_action_plan_person` | Pause or resume one action-plan-person relationship by ID. |
| `followupboss_list_groups` | List groups with documented filters and pagination metadata. |
| `followupboss_list_round_robin_groups` | List groups including round-robin assignment details. |
| `followupboss_get_group` | Retrieve one group by ID. |
| `followupboss_create_group` | Create a group. |
| `followupboss_update_group` | Update one group by ID. |
| `followupboss_delete_group` | Delete one group by ID and return a structured confirmation. |
| `followupboss_list_teams` | List teams with pagination metadata. |
| `followupboss_get_team` | Retrieve one team by ID. |
| `followupboss_create_team` | Create a team. |
| `followupboss_update_team` | Update one team by ID. |
| `followupboss_delete_team` | Delete one team by ID, optionally move members first, and return a structured confirmation. |
| `followupboss_list_team_inboxes` | List team inboxes with pagination metadata. |
| `followupboss_list_timeframes` | List valid Follow Up Boss timeframes with pagination metadata. |
| `followupboss_list_appointments` | List appointments with documented filters and pagination metadata. |
| `followupboss_get_appointment` | Retrieve one appointment by ID. |
| `followupboss_create_appointment` | Create an appointment. |
| `followupboss_update_appointment` | Update one appointment by ID. |
| `followupboss_delete_appointment` | Delete one appointment by ID and return a structured confirmation. |
| `followupboss_list_calls` | List calls with documented filters and pagination metadata. |
| `followupboss_get_call` | Retrieve one call by ID. |
| `followupboss_create_call` | Create a call log entry. |
| `followupboss_update_call` | Update one call by ID. |
| `followupboss_list_tasks` | List tasks with documented filters and pagination metadata. |
| `followupboss_get_task` | Retrieve one task by ID. |
| `followupboss_create_task` | Create a task for a person. |
| `followupboss_update_task` | Update one task by ID. |
| `followupboss_delete_task` | Delete one task by ID and return a structured confirmation. |
| `followupboss_list_templates` | List email templates with pagination metadata. |
| `followupboss_get_template` | Retrieve one email template by ID. |
| `followupboss_merge_template` | Merge an email template with recipients. |
| `followupboss_create_template` | Create an email template. |
| `followupboss_update_template` | Update one email template by ID. |
| `followupboss_delete_template` | Delete one email template by ID and return a structured confirmation. |
| `followupboss_list_text_messages` | List text messages with documented filters and pagination metadata. |
| `followupboss_get_text_message` | Retrieve one text message by ID. |
| `followupboss_create_text_message` | Record an externally sent text message log entry. |
| `followupboss_list_text_message_templates` | List text message templates with pagination metadata. |
| `followupboss_get_text_message_template` | Retrieve one text message template by ID. |
| `followupboss_merge_text_message_template` | Merge a text message template with recipients. |
| `followupboss_create_text_message_template` | Create a text message template. |
| `followupboss_update_text_message_template` | Update one text message template by ID. |
| `followupboss_delete_text_message_template` | Delete one text message template by ID and return a structured confirmation. |
| `followupboss_add_note` | Add a note to a person, optionally waiting for person visibility first. |
| `followupboss_get_note` | Retrieve one note by ID. |
| `followupboss_update_note` | Update one note by ID. |
| `followupboss_delete_note` | Delete one note by ID and return a structured confirmation. |
| `followupboss_list_webhooks` | List registered webhooks with pagination metadata. |
| `followupboss_get_webhook` | Retrieve one webhook by ID. |
| `followupboss_get_webhook_event` | Retrieve one webhook event by ID. |
| `followupboss_create_webhook` | Create a webhook subscription. |
| `followupboss_update_webhook` | Update one webhook by ID. |
| `followupboss_delete_webhook` | Delete a webhook by ID and return a structured confirmation. |

## MCP Resource

- `followupboss://api-coverage-matrix`

This resource returns the repository's current API coverage matrix so MCP clients can inspect what the server implements versus what was discovered in the official Follow Up Boss docs.

## MCP Prompt

- `followupboss_compose_lead_event`

This prompt helps a caller compose a canonical `POST /events` payload using the lead-ingestion path documented by Follow Up Boss.

## Response Shape

Collection tools return:

- a top-level collection key such as `people`, `events`, `users`, `customfields`, or `webhooks`
- a `_metadata` object containing normalized pagination metadata

Single-object tools return a JSON-serializable representation of the typed response model.

Delete tools return a confirmation payload shaped like:

```json
{
  "deleted": true,
  "noteId": 123
}
```

or:

```json
{
  "deleted": true,
  "webhookId": 456
}
```

## Error Behavior

MCP tools do not perform raw HTTP calls. They call the typed service layer, which means:

- auth failures, validation errors, not-found errors, rate-limit errors, and retryable server errors are mapped in one place
- MCP callers receive predictable safe messages
- `Retry-After` information is surfaced in the error message for rate limits when Follow Up Boss includes it

## Inspector Workflow

The official MCP Inspector is the easiest way to explore the tool surface during development.

```bash
npx @modelcontextprotocol/inspector uv run followupboss-mcp stdio
```

For streamable HTTP:

1. start the server with the `streamable-http` transport
2. point Inspector at the configured HTTP endpoint
3. add `Authorization: Bearer <token>` when you are testing the hosted multi-tenant flow
4. exercise tools, resources, and prompts through the Inspector UI

Hosted tools, resources, and prompts all share the same auth boundary. If the bearer token is
missing, invalid, expired, or mapped to a disabled tenant, Inspector should receive the same
fail-closed auth response rather than a partial or anonymous surface.

## Debugging Notes

- In stdio mode, do not emit logs to stdout.
- The server uses Python logging rather than mixing diagnostics into the MCP transport channel.
- Debugging is easiest with `FOLLOWUPBOSS_LOG_LEVEL=DEBUG` plus MCP Inspector or another compliant client; request logs now include attempt counts, retry decisions, and request-shape summaries without dumping raw query or JSON values.
- When testing webhook flows, verify the signature using the exact raw request body bytes before parsing JSON.
