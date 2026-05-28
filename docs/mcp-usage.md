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

Hosted deployments can now expose OAuth authorization-server routes for clients such as Cursor.
That browser flow delegates user consent to Follow Up Boss OAuth, then returns MCP-scoped hosted
tokens to the client. The MCP token is distinct from the raw Follow Up Boss OAuth access token:
raw Follow Up Boss token material is stored only in the tenant secret store and is used solely for
upstream API calls after hosted auth resolves a tenant.

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

`FOLLOWUPBOSS_DEFAULT_TIMEZONE` (legacy alias `FOLLOW_UP_BOSS_DEFAULT_TIMEZONE`) is a process-wide
behavioral setting that controls how appointment and task datetimes are normalized. Follow Up Boss
stores times in UTC and, in practice, does not honor a timezone *offset suffix* on the wire: a value
such as `2026-05-28T16:00:00-06:00` is stored as `2026-05-28T16:00:00Z` (the offset is dropped and
the wall-clock is relabeled as UTC). To land on the correct instant, the server converts appointment
`start`/`end` and task `dueDateTime` to an explicit UTC instant before sending. When this variable is
set to an IANA timezone name (for example `America/Denver`), a naive value such as a spoken `3:30pm`
is interpreted in that zone and converted to UTC; an aware value is converted from its own offset.
When the variable is unset, naive values are sent unchanged and Follow Up Boss treats them as UTC.
Because it is read from the process environment, it applies a single default to every tenant in
hosted multi-tenant deployments.

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

## Intent Routing

Use narrow intent helpers when the user asks for authenticated-user-owned data.
Those helpers resolve the Follow Up Boss user internally and avoid broad search
or list calls when the intent is already clear.

| User intent | Preferred tool | Avoid |
| --- | --- | --- |
| "my latest lead", "newest lead", or "most recent lead I received" | `followupboss_get_latest_lead` | Searching people by name or asking the caller for `assigned_user_id`. |
| "my overdue tasks" or "what am I late on?" | `followupboss_list_my_overdue_tasks` | A broad task list without authenticated-user and incomplete-task scope. |
| "my tasks today" or "what do I need to do today?" | `followupboss_list_my_tasks_due_today` | A broad task list without authenticated-user and incomplete-task scope. |
| "my upcoming tasks" or "what do I have coming up?" | `followupboss_list_my_upcoming_tasks` | A broad task list without authenticated-user and incomplete-task scope. |
| Uncontacted, never-contacted, no-communication, zero-communication, or needs-contact lead filters | `followupboss_list_uncontacted_leads`; omit owner scope for authenticated-user leads, pass `assigned_user_name` for a named owner, or set `mine=false` only for explicit account-wide wording. This uses empty `lastCommunication`, not the raw `contacted=false` field. | Looking up a smart list such as `Needs Contact` unless the user explicitly says "smart list" or "saved list". |
| A named smart-list people search, such as "Zillow leads in Eligible For Transfer" | `followupboss_search_people_in_smart_list` with `smart_list_name`; omit `mine` or set `mine=true` for authenticated-user scope, and set `mine=false` only for explicitly account-wide wording | Broad people search by source without the resolved smart-list boundary. |
| A named smart-list follow-up request using "I", "me", or "my" | `followupboss_search_people_in_smart_list` with `smart_list_name`, default owned scope, and any explicit filters such as `source` | Returning account-wide smart-list people from admin-visible credentials. |
| A named smart-list count | `followupboss_search_people_in_smart_list` with `smart_list_name`, default owned scope unless `mine=false` is explicitly requested, and a small `limit`, then read `_metadata.total` | Inferring the smart-list ID from the name alone or silently choosing account-wide scope. |
| Lead/contact communication or activity history with an explicit `person_id` | `followupboss_list_person_activity` | Broad calls, texts, email events, events, or appointments list tools without the person boundary. |
| Lead/contact communication or activity history without an explicit `person_id` | Ask which Follow Up Boss person ID should scope the history request. | Returning account-wide communication logs or guessing the lead from context. |
| Notes for a lead/person ID | No tool; Follow Up Boss has not made note search by FUB person ID available via the API. Tell the user to ask `support@followupboss.com` to make that search possible. | `followupboss_search_events` or claiming no notes exist from an empty event search. |
| Updating or deleting people and tasks | The explicit-ID mutation tool such as `followupboss_update_person`, `followupboss_delete_person`, `followupboss_update_task`, or `followupboss_delete_task` | Inferring IDs from vague natural-language intent. |

| Tool | Purpose |
| --- | --- |
| `followupboss_get_identity` | Return identity information for the authenticated Follow Up Boss account and user. |
| `followupboss_get_me` | Retrieve the current Follow Up Boss user profile with sensitive keys redacted. |
| `followupboss_search_people` | Search people with documented filters and pagination metadata; defaults to authenticated-user scope, including `smart_list_id` searches, unless `assigned_user_id` or `include_ponds=true` is explicit. Use `followupboss_get_latest_lead` for latest-owned-lead intent. |
| `followupboss_list_uncontacted_leads` | List people with no recorded `lastCommunication`, defaulting to authenticated-user scope and supporting explicit owner IDs or exact owner names. |
| `followupboss_search_people_in_smart_list` | Resolve one exact smart-list name internally, search people only with the resolved `smart_list_id`, default to authenticated-user scope, optionally apply explicit `assigned_user_id`, and return smart-list provenance. |
| `followupboss_get_latest_lead` | Retrieve the newest lead assigned to the authenticated user. |
| `followupboss_get_person` | Retrieve one person by ID. |
| `followupboss_list_person_activity` | List calls, text messages, email events, events, and appointments for one explicit `person_id` in one scoped response. |
| `followupboss_create_person` | Create a person directly. |
| `followupboss_update_person` | Update a person by explicit ID. |
| `followupboss_delete_person` | Delete a person by explicit ID and return a structured confirmation. |
| `followupboss_check_duplicate_person` | Check whether a person already exists by email or phone. |
| `followupboss_list_unclaimed_people` | List unclaimed leads available to the authenticated user. |
| `followupboss_claim_person` | Claim an unclaimed lead by person ID. |
| `followupboss_ignore_unclaimed_person` | Ignore an unclaimed lead offer by person ID and return a structured confirmation. |
| `followupboss_search_events` | Search events with pagination metadata and supported event filters; do not use it as a substitute for note search by person ID. |
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
| `followupboss_list_deals` | List deals with documented filters and pagination metadata; use `followupboss_list_active_deals_for_person` for active deals tied to a specific lead/person. |
| `followupboss_list_active_deals_for_person` | List active, non-archived deals for a specific person/lead by explicit `person_id`. |
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
| `followupboss_list_tasks` | List tasks with documented filters and pagination metadata; use the owned task helpers for common "my tasks" intents. |
| `followupboss_list_my_overdue_tasks` | List incomplete overdue tasks assigned to the authenticated user. |
| `followupboss_list_my_tasks_due_today` | List incomplete tasks due today and assigned to the authenticated user. |
| `followupboss_list_my_upcoming_tasks` | List incomplete future tasks assigned to the authenticated user. |
| `followupboss_get_task` | Retrieve one task by ID. |
| `followupboss_create_task` | Create a task for a person. |
| `followupboss_update_task` | Update one task by explicit ID. |
| `followupboss_delete_task` | Delete one task by explicit ID and return a structured confirmation. |
| `followupboss_list_templates` | List email templates with pagination metadata. |
| `followupboss_get_template` | Retrieve one email template by ID. |
| `followupboss_merge_template` | Merge an email template with recipients. |
| `followupboss_create_template` | Create an email template. |
| `followupboss_update_template` | Update one email template by ID. |
| `followupboss_delete_template` | Delete one email template by ID and return a structured confirmation. |
| `followupboss_list_text_messages` | List existing text messages with documented filters and pagination metadata. Read-only; Follow Up Boss does not provide API support to log or send texts through the MCP. |
| `followupboss_get_text_message` | Retrieve one text message by ID. |
| `followupboss_list_text_message_templates` | List text message templates with pagination metadata. |
| `followupboss_get_text_message_template` | Retrieve one text message template by ID. |
| `followupboss_merge_text_message_template` | Merge a text message template with recipients. |
| `followupboss_create_text_message_template` | Create a text message template. |
| `followupboss_update_text_message_template` | Update one text message template by ID. |
| `followupboss_delete_text_message_template` | Delete one text message template by ID and return a structured confirmation. |
| `followupboss_add_note` | Add a note to a person, optionally waiting for person visibility first. |
| `followupboss_get_note` | Retrieve one note by note ID only; Follow Up Boss does not expose note search by FUB person ID through the API. |
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
2. point Inspector or Cursor at the configured HTTP endpoint
3. either complete the hosted OAuth flow when the client supports it, or add
   `Authorization: Bearer <token>` when you are testing with a pre-issued hosted token
4. exercise tools, resources, and prompts through the Inspector UI

Hosted tools, resources, and prompts all share the same auth boundary. If the bearer token is
missing, invalid, expired, or mapped to a disabled tenant, Inspector should receive the same
fail-closed auth response rather than a partial or anonymous surface.

## Debugging Notes

- In stdio mode, do not emit logs to stdout.
- The server uses Python logging rather than mixing diagnostics into the MCP transport channel.
- Debugging is easiest with `FOLLOWUPBOSS_LOG_LEVEL=DEBUG` plus MCP Inspector or another compliant client; request logs now include attempt counts, retry decisions, and request-shape summaries without dumping raw query or JSON values.
- When testing webhook flows, verify the signature using the exact raw request body bytes before parsing JSON.
