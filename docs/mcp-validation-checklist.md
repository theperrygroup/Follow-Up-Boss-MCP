# MCP Validation Runbook

This runbook is the credential-backed companion to `make validate`, `make build-smoke`, `FOLLOWUPBOSS_RUN_LIVE_TESTS=1 make live-identity-check`, and `FOLLOWUPBOSS_RUN_LIVE_TESTS=1 make live-contract-check`. Use it to verify the complete registered Follow Up Boss MCP surface against a real account with credentials available either in the environment or in a repository-local `.env`, which the live-check targets now auto-load when present.

`src/followupboss_mcp/mcp_registration.py` is the source of truth for tools, resources, and prompts. `tests/mcp/test_mcp_tools_server_cli.py` is the quickest backstop for the currently asserted surface. If this file, `docs/mcp-usage.md`, and the registration file ever disagree, treat the registration file as authoritative and update the docs after validation.

The domain sections below follow the registration order from `register_server_surface()` so checklist drift is easy to spot when the server surface changes. For deeper offline testing guidance use `docs/testing.md`; for release-only artifact checks use `docs/release-checklist.md`; for contributor workflow details use `CONTRIBUTING.md`.

## How To Use This File

1. Fill in `Run Metadata`.
2. Confirm prerequisites and required fixtures.
3. Run the baseline automation before live validation.
4. Verify the MCP surface over both transports.
5. Work through each domain section in order, reusing fixtures and recording IDs in the scratchpad.
6. Leave blocked items unchecked and record the blocker in `Known Issues And Account Limitations`.
7. Finish the cleanup and doc-sync sections before treating the run as complete.

## Reusable Checklist vs Run Evidence

- Keep the checklist itself reusable: leave checkboxes unchecked until a specific run validates them.
- Store run-specific IDs, blockers, and notes in the metadata, scratchpad, and issues tables.
- If you need immutable release evidence, copy the completed state into a dated artifact before resetting this file for the next cycle.

## Run Metadata

| Field | Value |
| --- | --- |
| Validation date | |
| Validator | |
| Account or environment | |
| Auth mode (`api_key` or `oauth`) | |
| Transport(s) exercised | |
| Observed tool count | |
| Notes | |

## Fixture Scratchpad

| Fixture | ID(s) | Created via | Used by | Cleanup path | Notes |
| --- | --- | --- | --- | --- | --- |
| Disposable person | | `followupboss_create_person` | People, events, action plans, automations, appointments, calls, tasks, text messages, notes | `followupboss_delete_person` | |
| Unclaimed lead offer | | Existing sandbox data | `followupboss_claim_person`, `followupboss_ignore_unclaimed_person` | Manual or account-specific | |
| People relationship | | `followupboss_create_people_relationship` | People relationships | `followupboss_delete_people_relationship` | |
| Deal | | `followupboss_create_deal` | Deal write flow, deal attachments | `followupboss_delete_deal` | |
| Person attachment | | `followupboss_create_person_attachment` | Attachments | `followupboss_delete_person_attachment` | |
| Deal attachment | | `followupboss_create_deal_attachment` | Attachments | `followupboss_delete_deal_attachment` | |
| Reaction target | | Existing note, call, or threaded reply | Reactions | Match target cleanup path | |
| Reaction | | `followupboss_add_reaction` or existing data | `followupboss_get_reaction`, `followupboss_delete_reaction` | `followupboss_delete_reaction` | |
| Action-plan person | | `followupboss_apply_action_plan` | Action plans | Manual pause or resume, or account-specific rollback | |
| Automation-person | | `followupboss_trigger_automation` | Automations | Manual pause or resume, or account-specific rollback | |
| Group | | `followupboss_create_group` | Groups | `followupboss_delete_group` | |
| Custom field | | `followupboss_create_custom_field` | Custom fields | `followupboss_delete_custom_field` | |
| Deal custom field | | `followupboss_create_deal_custom_field` | Deal custom fields | `followupboss_delete_deal_custom_field` | |
| Appointment outcome | | `followupboss_create_appointment_outcome` | Appointment outcomes | `followupboss_delete_appointment_outcome` | |
| Appointment type | | `followupboss_create_appointment_type` | Appointment types | `followupboss_delete_appointment_type` | |
| Appointment | | `followupboss_create_appointment` | Appointments | `followupboss_delete_appointment` | |
| Call | | `followupboss_create_call` | Calls | Manual | |
| Pipeline | | `followupboss_create_pipeline` | Pipelines, stages | `followupboss_delete_pipeline` | |
| Pond | | `followupboss_create_pond` | Ponds | `followupboss_delete_pond` | |
| Stage | | `followupboss_create_stage` | Stages | `followupboss_delete_stage` | |
| Task | | `followupboss_create_task` | Tasks | `followupboss_delete_task` | |
| Team | | `followupboss_create_team` | Teams | `followupboss_delete_team` | |
| Template | | `followupboss_create_template` | Templates | `followupboss_delete_template` | |
| Text message | | `followupboss_create_text_message` | Text messages | Manual | |
| Text message template | | `followupboss_create_text_message_template` | Text message templates | `followupboss_delete_text_message_template` | |
| Note | | `followupboss_add_note` | Notes, reactions | `followupboss_delete_note` | |
| Webhook | | `followupboss_create_webhook` | Webhooks | `followupboss_delete_webhook` | |
| Disposable user | | Sandbox fixture | `followupboss_delete_user` | Account-specific | |
| Webhook event | | Existing sandbox event | `followupboss_get_webhook_event` | N/A | |
| Threaded reply | | Existing sandbox reply | `followupboss_get_threaded_reply` | N/A | |

## Known Issues And Account Limitations

| Domain | Tool or area | Issue or limitation | Impact | Follow-up |
| --- | --- | --- | --- | --- |
| | | | | |

## Prerequisites And Safety

- [ ] Confirm the shell exports the repository-expected `FOLLOWUPBOSS_*` variables from `.env`.
- [ ] Confirm `.env` provides either `FOLLOWUPBOSS_API_KEY` or `FOLLOWUPBOSS_ACCESS_TOKEN`, plus `FOLLOWUPBOSS_AUTH_MODE` if the default API-key mode is not being used.
- [ ] If you want the owner-only webhook CRUD path to pass instead of skip, provide `FOLLOWUPBOSS_OWNER_API_KEY` or `FOLLOWUPBOSS_OWNER_ACCESS_TOKEN`, plus optional `FOLLOWUPBOSS_OWNER_AUTH_MODE`, `FOLLOWUPBOSS_OWNER_SYSTEM_NAME`, and `FOLLOWUPBOSS_OWNER_SYSTEM_KEY` overrides when needed.
- [ ] If you plan to validate webhook signing or any integration-header-dependent flow, confirm the
  integration has been registered through Follow Up Boss's official
  [Registration and Identification](https://docs.followupboss.com/reference/identification) flow.
- [ ] Confirm optional registered-system env vars are present when needed:
  `FOLLOWUPBOSS_SYSTEM_NAME` / `FOLLOWUPBOSS_SYSTEM_KEY`, `FOLLOWUPBOSS_X_SYSTEM` /
  `FOLLOWUPBOSS_X_SYSTEM_KEY`, or the legacy `FOLLOW_UP_BOSS_*` equivalents.
- [ ] Confirm `uv`, `make`, and `npx` are available locally.
- [ ] Confirm the validation target is a sandbox or clearly disposable account with a temporary-data naming convention such as `MCP Validation <date>`.
- [ ] Confirm you have one reusable disposable person fixture or a plan to create one near the start of the run.
- [ ] Confirm you have one known existing email or phone plus one clearly fake control value for `followupboss_check_duplicate_person`.
- [ ] Confirm you have at least one disposable unclaimed lead offer if you plan to validate `followupboss_claim_person` or `followupboss_ignore_unclaimed_person`.
- [ ] Confirm you have a safe hosted file URI and file metadata for person and deal attachment tests.
- [ ] Confirm you have a valid action plan ID for mutation tests.
- [ ] Confirm you have a valid automation ID for mutation tests.
- [ ] Confirm you have a published inbox app plus disposable installation, conversation, message, and participant fixtures for inbox-app tests.
- [ ] Confirm you have valid pipeline, stage, owner, type, outcome, and reassignment references for deal, appointment, stage, pond, pipeline, team, and user lifecycle tests.
- [ ] Confirm you have unique labels and safe field types or dropdown choices for custom-field and deal-custom-field admin tests.
- [ ] Confirm you have a known reaction ID or another discovery path if `followupboss_add_reaction` only returns an acknowledgement instead of a full reaction object.
- [ ] Confirm you have a known threaded reply ID for `followupboss_get_threaded_reply`.
- [ ] Confirm you have a disposable user plus a safe reassignment target if you plan to validate `followupboss_delete_user`.
- [ ] Confirm you have a disposable team or a member-restoration plan if you plan to validate team write flows.
- [ ] Confirm you have a reachable webhook receiver URL, the ability to capture raw request bytes for signature verification, and a known webhook event ID or trigger path for `followupboss_get_webhook_event`.

## Baseline Automated Validation

- [ ] Run `make validate` and confirm the full local quality gate passes before any live validation.
- [ ] Run `make build-smoke` and confirm the packaged server still builds and validates.
- [ ] Run `FOLLOWUPBOSS_RUN_LIVE_TESTS=1 make live-identity-check` and confirm the live credential smoke test passes with the current `.env`.
- [ ] Run `FOLLOWUPBOSS_RUN_LIVE_TESTS=1 make live-contract-check` and confirm the broader live suite passes across identity, users, people, timeframes, MCP `/me` redaction, note reactions, registered-system person attachments when configured, disposable person-centered note, task, and appointment write-and-rollback flows, and an owner-only webhook CRUD path that skips cleanly when access is unavailable.
- [ ] If this run is release-facing, run `make release-validate` or the equivalent ingestion and coverage regeneration flow before closing the run.
- [ ] Record any failures, contract drift, or credential limitations in `Known Issues And Account Limitations` before continuing.

## MCP Surface Inventory

- [ ] Capture the advertised tool list from Inspector or another compliant client and confirm it matches the current surface in `src/followupboss_mcp/mcp_registration.py`.
- [ ] Confirm the observed tool count matches the current registered surface and record the count in `Run Metadata`.
- [ ] Confirm the public reference in `docs/mcp-usage.md` matches the observed tool names or record the drift before proceeding.
- [ ] Confirm the asserted surface in `tests/mcp/test_mcp_tools_server_cli.py` matches the observed tool names or record the drift before proceeding.
- [ ] Confirm the advertised resource list includes `followupboss://api-coverage-matrix`.
- [ ] Confirm the advertised prompt list includes `followupboss_compose_lead_event`.
- [ ] Confirm no unexpected legacy or duplicate tool names are exposed.

## MCP Transport Verification

### Stdio

Use Inspector against the stdio transport:

```bash
npx @modelcontextprotocol/inspector uv run followupboss-mcp stdio
```

- [ ] Inspector or another compliant client connects successfully over `stdio`.
- [ ] `followupboss_get_identity` succeeds over `stdio`.
- [ ] At least one list or search tool, one get tool, one create or update tool, and one delete tool succeed over `stdio`.
- [ ] Resource access and prompt rendering both work over `stdio`.
- [ ] Disconnecting and reconnecting the client leaves the `stdio` transport healthy for another run.
- [ ] No operational logging or stray text contaminates `stdout` during `stdio` use.

### Streamable HTTP

Start the server in one terminal:

```bash
uv run python -m followupboss_mcp.cli streamable-http --host 127.0.0.1 --port 8000 --path /mcp
```

Then connect Inspector or another client to `http://127.0.0.1:8000/mcp`.

- [ ] The server starts without import errors or runtime exceptions.
- [ ] Inspector or another compliant client connects successfully over `streamable-http`.
- [ ] `followupboss_get_identity` succeeds over `streamable-http`.
- [ ] At least one list or search tool, one get tool, one create or update tool, and one delete tool succeed over `streamable-http`.
- [ ] Resource access and prompt rendering both work over `streamable-http`.
- [ ] A second fresh client session against the same long-running `streamable-http` server can still execute tools after the first session disconnects.
- [ ] Shutting the server down cleanly does not leave the next run wedged.

## Resource And Prompt Checks

- [ ] Read `followupboss://api-coverage-matrix` and confirm the response is current, non-empty, and aligned with the repository's latest coverage docs.
- [ ] Render `followupboss_compose_lead_event` and confirm it gives usable guidance for composing a canonical `POST /events` payload.
- [ ] Confirm the resource and prompt are visible from both `stdio` and `streamable-http` clients.
- [ ] Confirm the resource URI and prompt name match the registration file exactly.
- [ ] If the resource fails in a packaged-install context because `docs/api-coverage-matrix.md` is not present, record the limitation in the issues table.

## Cross-Cutting Assertions

Apply these checks wherever the surface below supports them.

- [ ] Every list or search tool returns the expected top-level collection key plus `_metadata`.
- [ ] Every paginated list is exercised with a small page size such as `limit=1` so `_metadata`, `next_token`, and `offset` behavior are validated.
- [ ] When a second page is available, follow `next_token`, `offset`, or other documented paging inputs and confirm the subsequent result is consistent.
- [ ] Every get-by-ID tool is validated with an ID taken from either a list result, a just-created object, or a known sandbox fixture when no list tool exists.
- [ ] Every single-object response is JSON-serializable and safe for MCP clients.
- [ ] `followupboss_get_me` redacts secret-like fields such as `apiKey` before returning the current-user payload.
- [ ] Every update tool returns the mutated object or a successful acknowledgement that can be reconciled against a follow-up read.
- [ ] Every delete tool returns a structured confirmation payload with `deleted: true` and the correct identifier key such as `personId`, `userId`, `noteId`, or `webhookId`.
- [ ] For explicit-ID mutation tools, confirm the ID comes from a known fixture, list result, or just-created object rather than vague natural-language inference.
- [ ] For common authenticated-user intents, prefer the narrow helper tool over a broad search or list tool when the helper exists.
- [ ] For acknowledgement-style responses that do not return a full resource, confirm the returned payload still leaves enough information to reconcile the side effect, or record the gap in `Known Issues And Account Limitations`.
- [ ] At least one safe failure path is exercised without leaking secrets, such as a clearly invalid ID or a missing required field.
- [ ] If you hit permission-denied or rate-limit responses, confirm the surfaced MCP error text is understandable and record the limitation in the issues table.
- [ ] If registered-system env vars are configured through either the `SYSTEM_NAME` or `X_SYSTEM`
  aliases, at least one integration-header-dependent flow succeeds.
- [ ] With `FOLLOWUPBOSS_LOG_LEVEL=DEBUG`, logs still stay off `stdout` in `stdio` mode.
- [ ] Every stateful flow without an inverse MCP delete or undo path is captured in the scratchpad with a manual rollback note before you move on.
- [ ] Capture any contract drift, unexpected payload shapes, or sandbox limitations in `Known Issues And Account Limitations`.

## Domain Checklist

Work through the sections below in order. If a domain depends on an object created earlier in the checklist, reuse the existing fixture and update the scratchpad instead of creating unnecessary duplicates.

### Identity

- [ ] `followupboss_get_identity`: confirm the returned account and user details match the credential expected from `.env`.

### People

- [ ] `followupboss_search_people`: run with a small `limit` and confirm the `people` collection plus `_metadata`.
- [ ] `followupboss_get_latest_lead`: ask for "my latest lead" and confirm the helper returns either one assigned person or `person: null` with usable `_metadata`, without requiring a caller-supplied `assigned_user_id`.
- [ ] `followupboss_get_person`: fetch a person ID returned by the search call or from the created record below.
- [ ] `followupboss_create_person`: create a disposable person with clearly temporary data.
- [ ] `followupboss_update_person`: update the disposable person by explicit `person_id` and confirm the changed fields are reflected in the response.
- [ ] `followupboss_check_duplicate_person`: run once against the disposable person's email or phone and confirm the tool reports a positive match.
- [ ] `followupboss_check_duplicate_person`: run again with a clearly fake email or phone value and confirm the tool reports no match without a transport error.
- [ ] `followupboss_list_unclaimed_people`: confirm the list output and `_metadata`. An empty `people` collection is acceptable if the blocker is recorded.
- [ ] `followupboss_claim_person`: claim one disposable unclaimed lead and confirm the returned person record reflects the new claimed or assigned state.
- [ ] `followupboss_ignore_unclaimed_person`: ignore a separate disposable unclaimed lead and confirm the structured acknowledgement uses `personId`.
- [ ] `followupboss_delete_person`: delete a disposable person by explicit `person_id` only after all downstream person-dependent checks are complete and confirm the structured delete response uses `personId`.
- [ ] Record the created `personId` in the scratchpad and note whether it will be reused or deleted during cleanup.

### People Relationships

- [ ] `followupboss_list_people_relationships`: confirm list output and `_metadata`.
- [ ] `followupboss_get_people_relationship`: retrieve a relationship ID from the list response or from the created relationship below.
- [ ] `followupboss_create_people_relationship`: create a disposable relationship for the validation person.
- [ ] `followupboss_update_people_relationship`: update the relationship and confirm the mutated values.
- [ ] `followupboss_delete_people_relationship`: delete the disposable relationship and confirm the structured delete response uses `peopleRelationshipId`.

### Timeframes

- [ ] `followupboss_list_timeframes`: confirm list output and the expected timeframe values.

### Attachments

There are no list tools for attachments, so capture IDs directly from create responses.

- [ ] `followupboss_create_person_attachment`: create a disposable person attachment using a safe `uri`, `file_name`, and optional `file_size`.
- [ ] `followupboss_get_person_attachment`: fetch the created person attachment by ID.
- [ ] `followupboss_update_person_attachment`: update the person attachment and confirm the changed values.
- [ ] `followupboss_delete_person_attachment`: delete the person attachment and confirm the structured delete response uses `personAttachmentId`.
- [ ] `followupboss_create_deal_attachment`: create a disposable deal attachment using a valid deal ID plus safe file metadata.
- [ ] `followupboss_get_deal_attachment`: fetch the created deal attachment by ID.
- [ ] `followupboss_update_deal_attachment`: update the deal attachment and confirm the changed values.
- [ ] `followupboss_delete_deal_attachment`: delete the deal attachment and confirm the structured delete response uses `dealAttachmentId`.

### Reactions

There is no list tool for reactions, and `followupboss_add_reaction` may return only an acknowledgement. Capture the reaction ID from the create response if available, or use a known sandbox fixture.

- [ ] `followupboss_add_reaction`: add a disposable reaction to a note, call, or threaded reply using a safe `ref_type` and `ref_id`.
- [ ] `followupboss_get_reaction`: fetch a created or pre-existing reaction by ID.
- [ ] `followupboss_delete_reaction`: delete the reaction using the matching `ref_type`, `ref_id`, and `emoji` if needed, and confirm the structured delete response uses `refId`.

### Threaded Replies

There is no list or create tool for threaded replies, so use a known sandbox ID.

- [ ] `followupboss_get_threaded_reply`: fetch a known threaded reply by ID and confirm the payload is usable for downstream reaction-style references if needed.

### Events

- [ ] `followupboss_search_events`: confirm list output and `_metadata`.
- [ ] `followupboss_get_event`: retrieve one event ID returned by the list call.
- [ ] `followupboss_send_event`: send a canonical lead or lead-activity event using safe test data.
- [ ] If the immediate send response does not include the created event ID directly, confirm the side effect via `followupboss_search_events` or `followupboss_get_event`.

### Email Marketing

- [ ] `followupboss_list_email_campaigns`: confirm the campaign list path works with the available `origin` filters.
- [ ] `followupboss_create_email_campaign`: create a disposable campaign using a valid `origin` and `origin_id`.
- [ ] `followupboss_update_email_campaign`: update the created campaign and confirm the changed content.
- [ ] `followupboss_list_email_events`: confirm list output and `_metadata` with a small page size.
- [ ] `followupboss_send_email_events`: send a minimal disposable batch of email events linked to valid sandbox data.
- [ ] Record any manual cleanup needed because there is no MCP delete tool for email campaigns or email events.

### Action Plans

- [ ] `followupboss_list_action_plans`: confirm list output and `_metadata`.
- [ ] `followupboss_list_action_plan_people`: confirm list output and `_metadata`.
- [ ] `followupboss_apply_action_plan`: apply a known action plan to the validation person.
- [ ] `followupboss_update_action_plan_person`: pause or resume the created action-plan-person relationship and confirm the updated state.
- [ ] Record any manual rollback needed because there is no direct MCP delete or unapply tool.

### Automations

- [ ] `followupboss_list_automations`: confirm list output and `_metadata`.
- [ ] `followupboss_get_automation`: retrieve a known automation by ID.
- [ ] `followupboss_list_automation_people`: confirm list output and `_metadata`.
- [ ] `followupboss_get_automation_person`: fetch a known automation-person relationship by ID.
- [ ] `followupboss_trigger_automation`: trigger a known automation for the validation person.
- [ ] `followupboss_update_automation_person`: pause or resume the automation-person relationship and confirm the updated state.
- [ ] Record any manual rollback needed because automation runs are stateful.

### Groups

- [ ] `followupboss_list_groups`: confirm list output and `_metadata`.
- [ ] `followupboss_list_round_robin_groups`: confirm the round-robin-specific listing path works.
- [ ] `followupboss_get_group`: retrieve a known group by ID.
- [ ] `followupboss_create_group`: create a disposable group.
- [ ] `followupboss_update_group`: update the created group and confirm the mutated values.
- [ ] `followupboss_delete_group`: delete the disposable group and confirm the structured delete response.

### Inbox Apps

These checks require a published inbox app plus valid installation, conversation, message, and participant fixtures.

- [ ] `followupboss_list_inbox_app_installations`: confirm the installation list path works.
- [ ] `followupboss_install_inbox_app`: install an inbox app in a disposable scope if the sandbox supports it.
- [ ] `followupboss_deactivate_inbox_app`: deactivate the disposable installation and confirm the response.
- [ ] `followupboss_add_inbox_app_message`: add a disposable conversation message.
- [ ] `followupboss_add_inbox_app_note`: add a disposable conversation note.
- [ ] `followupboss_list_inbox_app_participants`: confirm the participant list path works.
- [ ] `followupboss_add_inbox_app_participant`: add a disposable participant to the test conversation.
- [ ] `followupboss_update_inbox_app_conversation`: update conversation status or metadata and confirm the changes.
- [ ] `followupboss_update_inbox_app_message`: update the test message by ID or external message ID.
- [ ] `followupboss_remove_inbox_app_participant`: remove the disposable participant and confirm success.

### Users

User deletion is destructive. Use a disposable user and a safe reassignment target.

- [ ] `followupboss_get_me`: confirm the current-user payload is returned and secret-like fields remain redacted.
- [ ] `followupboss_list_users`: confirm list output and `_metadata`.
- [ ] `followupboss_get_user`: retrieve a user ID returned by the list call.
- [ ] `followupboss_delete_user`: delete a disposable user, reassign their leads with `assign_to`, and confirm the structured delete response uses `userId`.

### Custom Fields

- [ ] `followupboss_list_custom_fields`: confirm list output and `_metadata`.
- [ ] `followupboss_get_custom_field`: fetch one field by ID.
- [ ] `followupboss_create_custom_field`: create a disposable custom field using the Follow Up Boss API field `name`.
- [ ] `followupboss_update_custom_field`: update the disposable field and confirm the changed values.
- [ ] `followupboss_delete_custom_field`: delete the disposable field and confirm the structured delete response.

### Deals

- [ ] `followupboss_list_deals`: confirm list output and `_metadata`.
- [ ] `followupboss_get_deal`: fetch one deal by ID.
- [ ] `followupboss_create_deal`: create a disposable deal using valid sandbox references.
- [ ] `followupboss_update_deal`: update the disposable deal and confirm the changed values.
- [ ] `followupboss_delete_deal`: delete the disposable deal and confirm the structured delete response.
- [ ] Record the prerequisite pipeline, stage, person, owner, and custom-field references used for deal writes.

### Deal Custom Fields

- [ ] `followupboss_list_deal_custom_fields`: confirm list output and `_metadata`.
- [ ] `followupboss_get_deal_custom_field`: fetch one deal custom field by ID from either the list response, the created field below, or a known sandbox fixture.
- [ ] `followupboss_create_deal_custom_field`: create a disposable deal custom field using a unique label and a safe type. If `type="dropdown"`, include disposable choices.
- [ ] `followupboss_update_deal_custom_field`: update the created field and confirm the changed values.
- [ ] `followupboss_delete_deal_custom_field`: delete the disposable field and confirm the structured delete response uses `dealCustomFieldId`.
- [ ] Record the created field ID and generated `name` in the scratchpad if the field will be reused in later deal-write tests.

### Appointment Outcomes

- [ ] `followupboss_list_appointment_outcomes`: confirm list output and `_metadata`.
- [ ] `followupboss_get_appointment_outcome`: fetch one outcome by ID.
- [ ] `followupboss_create_appointment_outcome`: create a disposable outcome.
- [ ] `followupboss_update_appointment_outcome`: update the disposable outcome and confirm the changed values.
- [ ] `followupboss_delete_appointment_outcome`: delete the disposable outcome with a reassignment target if required and confirm the structured delete response.

### Appointment Types

- [ ] `followupboss_list_appointment_types`: confirm list output and `_metadata`.
- [ ] `followupboss_get_appointment_type`: fetch one type by ID.
- [ ] `followupboss_create_appointment_type`: create a disposable type.
- [ ] `followupboss_update_appointment_type`: update the disposable type and confirm the changed values.
- [ ] `followupboss_delete_appointment_type`: delete the disposable type with a reassignment target if required and confirm the structured delete response.

### Appointments

- [ ] `followupboss_list_appointments`: confirm list output and `_metadata`.
- [ ] `followupboss_get_appointment`: fetch one appointment by ID.
- [ ] `followupboss_create_appointment`: create a disposable appointment using valid person, owner, type, and outcome references.
- [ ] `followupboss_update_appointment`: update the disposable appointment and confirm the changed values.
- [ ] `followupboss_delete_appointment`: delete the disposable appointment and confirm the structured delete response.

### Calls

- [ ] `followupboss_list_calls`: confirm list output and `_metadata`.
- [ ] `followupboss_get_call`: fetch one call by ID.
- [ ] `followupboss_create_call`: create a disposable call log entry.
- [ ] `followupboss_update_call`: update the disposable call log and confirm the changed values.
- [ ] Record any manual cleanup needed because there is no MCP delete tool for calls.

### Pipelines

- [ ] `followupboss_list_pipelines`: confirm list output and `_metadata`.
- [ ] `followupboss_get_pipeline`: fetch one pipeline by ID.
- [ ] `followupboss_create_pipeline`: create a disposable pipeline.
- [ ] `followupboss_update_pipeline`: update the disposable pipeline and confirm the changed values.
- [ ] `followupboss_delete_pipeline`: delete the disposable pipeline and confirm the structured delete response.

### Ponds

- [ ] `followupboss_list_ponds`: confirm list output and `_metadata`.
- [ ] `followupboss_get_pond`: fetch one pond by ID.
- [ ] `followupboss_create_pond`: create a disposable pond.
- [ ] `followupboss_update_pond`: update the disposable pond and confirm the changed values.
- [ ] `followupboss_delete_pond`: delete the disposable pond with a valid reassignment target and confirm the structured delete response.

### Smart Lists

- [ ] `followupboss_list_smart_lists`: confirm list output and `_metadata`.
- [ ] `followupboss_get_smart_list`: fetch one smart list by ID.

### Stages

- [ ] `followupboss_list_stages`: confirm list output and `_metadata`.
- [ ] `followupboss_get_stage`: fetch one stage by ID.
- [ ] `followupboss_create_stage`: create a disposable stage in a valid pipeline.
- [ ] `followupboss_update_stage`: update the disposable stage and confirm the changed values.
- [ ] `followupboss_delete_stage`: delete the disposable stage with a valid reassignment target and confirm the structured delete response.

### Tasks

- [ ] `followupboss_list_tasks`: confirm list output and `_metadata`.
- [ ] `followupboss_list_my_overdue_tasks`: ask for "my overdue tasks" and confirm the helper returns incomplete overdue tasks assigned to the authenticated user, with pagination metadata.
- [ ] `followupboss_list_my_tasks_due_today`: ask for "my tasks today" and confirm the helper returns incomplete tasks due today assigned to the authenticated user, with pagination metadata.
- [ ] `followupboss_get_task`: fetch one task by ID.
- [ ] `followupboss_create_task`: create a disposable task for the validation person and include assignee fields if the account requires them.
- [ ] `followupboss_update_task`: update the disposable task by explicit `task_id` and confirm the changed values.
- [ ] `followupboss_delete_task`: delete the disposable task by explicit `task_id` and confirm the structured delete response.

### Team Inboxes

- [ ] `followupboss_list_team_inboxes`: confirm list output and `_metadata`.

### Teams

Team writes are destructive to account membership. Use a disposable team or an explicit member-restoration plan.

- [ ] `followupboss_list_teams`: confirm list output and `_metadata`.
- [ ] `followupboss_get_team`: fetch one team by ID.
- [ ] `followupboss_create_team`: create a disposable team.
- [ ] `followupboss_update_team`: update the disposable team and confirm the changed values.
- [ ] `followupboss_delete_team`: delete the disposable team and confirm the structured delete response, including any member-move behavior relied on by the account.

### Templates

- [ ] `followupboss_list_templates`: confirm list output and `_metadata`.
- [ ] `followupboss_get_template`: fetch one template by ID.
- [ ] `followupboss_merge_template`: merge a template using valid sandbox recipients and confirm the preview content.
- [ ] `followupboss_create_template`: create a disposable template.
- [ ] `followupboss_update_template`: update the disposable template and confirm the changed values.
- [ ] `followupboss_delete_template`: delete the disposable template and confirm the structured delete response.

### Text Messages

- [ ] `followupboss_list_text_messages`: confirm list output and `_metadata`, preferably using safe filters such as `person_id`.
- [ ] `followupboss_get_text_message`: fetch one text message by ID.
- [ ] `followupboss_create_text_message`: record a disposable externally sent text-message log entry using valid sandbox data and a valid phone-number format.
- [ ] Record any manual cleanup needed because there is no MCP delete tool for text messages.

### Text Message Templates

- [ ] `followupboss_list_text_message_templates`: confirm list output and `_metadata`.
- [ ] `followupboss_get_text_message_template`: fetch one template by ID.
- [ ] `followupboss_merge_text_message_template`: merge a template using valid sandbox recipients and confirm the preview content.
- [ ] `followupboss_create_text_message_template`: create a disposable text-message template.
- [ ] `followupboss_update_text_message_template`: update the disposable template and confirm the changed values.
- [ ] `followupboss_delete_text_message_template`: delete the disposable template and confirm the structured delete response.

### Notes

- [ ] `followupboss_add_note`: create a disposable note for the validation person.
- [ ] `followupboss_get_note`: fetch the created note by ID.
- [ ] `followupboss_update_note`: update the created note and confirm the changed values.
- [ ] `followupboss_delete_note`: delete the created note and confirm the structured delete response.
- [ ] If needed, reuse the note ID for reaction testing.

### Webhooks

Webhook access may be owner-only, and event lookup requires a known webhook event ID.

- [ ] `followupboss_list_webhooks`: confirm list output and `_metadata`.
- [ ] `followupboss_get_webhook`: fetch one webhook by ID.
- [ ] `followupboss_get_webhook_event`: fetch a known webhook event by ID and confirm the payload is usable for delivery-debugging workflows.
- [ ] `followupboss_create_webhook`: create a disposable webhook pointed at a safe receiver URL.
- [ ] `followupboss_update_webhook`: update the disposable webhook and confirm the changed values.
- [ ] `followupboss_delete_webhook`: delete the disposable webhook and confirm the structured delete response.
- [ ] If the webhook workflow depends on `X-System-Key`, confirm the receiver validates the signature with the exact raw request body bytes before parsing JSON.

## Cleanup And Evidence

- [ ] Delete every temporary object that has an MCP delete tool, including people, attachments, relationships, deals, fields, appointment metadata, appointments, ponds, tasks, teams, templates, text-message templates, notes, and webhooks created for the run.
- [ ] Manually clean up every temporary object or state change that does not currently have an inverse MCP tool, including email campaigns, email events, inbox-app side effects, calls, text messages, automation runs, and action-plan applications.
- [ ] Reassign or restore any destructive account-level changes made during `followupboss_delete_user`, team mutations, unclaimed-lead claim or ignore flows, pipeline or stage deletes, or other admin operations.
- [ ] Review the scratchpad and confirm no temporary IDs were left behind or orphaned.
- [ ] Confirm every domain above was either validated successfully or explicitly recorded as blocked in `Known Issues And Account Limitations`.
- [ ] If the observed surface differs from the reference docs, update `docs/mcp-usage.md`.
- [ ] If validation exposed an official Follow Up Boss endpoint that is missing or misrepresented in the server, update `docs/api-coverage-matrix.md`.
- [ ] If this run is being used as release evidence, copy the completed checklist state or summarize it in `docs/final-validation-report.md`.
- [ ] Capture any blocked domains, missing sandbox prerequisites, or contract-drift findings in the issue tracker or release notes before the next cycle.
