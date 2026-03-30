# MCP Validation Checklist

This runbook is the live, credential-backed companion to the offline quality gates in `make validate`. Use it to verify the full Follow Up Boss MCP surface end to end with the credentials loaded from `.env`.

The authoritative MCP surface is `src/followupboss_mcp/mcp_registration.py`. If this checklist and `docs/mcp-usage.md` ever disagree, treat the registration file as the source of truth and update the docs after validation.

## Current Run Status

Last worked: `2026-03-29`

- Verified live MCP connectivity over both `stdio` and `streamable-http` with the current credentials.
- The current `.env` uses `FOLLOW_UP_BOSS_*` variable names, so this run mapped them to the repository's expected `FOLLOWUPBOSS_*` names before testing.
- `make validate` currently fails because total coverage is `99.86%`, with gaps in `src/followupboss_mcp/models/email_marketing.py` and `src/followupboss_mcp/services/email_marketing.py`.
- `FOLLOWUPBOSS_RUN_LIVE_TESTS=1 make live-identity-check` reaches the live API, but the assertion currently fails because the `GET /identity` response is no longer populating the top-level `identity.id` field the test expects.
- Later fresh MCP startups became unavailable because `src/followupboss_mcp/models/email_marketing.py` currently raises a `SyntaxError`; after user direction, the rest of this run avoided that import path and only used already verified MCP results plus direct service probes for diagnosis.
- A built wheel installed into an isolated temporary virtualenv was used to continue MCP validation after the source tree became unstartable.
- Confirmed live MCP operations in this run include: resource access, prompt rendering, `get_identity`, `search_people`, `get_person`, `create_person`, `update_person`, `list_users`, `get_user`, `add_note`, `get_note`, `update_note`, `delete_note`, people relationship get/create/update/delete, action plan apply/pause, automation trigger/pause, `send_event` plus follow-up event search confirmation, call create/get/update, text message list/get/create, group create/update/delete, appointment create/get/update/delete, task create/get/update/delete, template create/update/merge/delete, and text message template get/create/update/merge/delete.

## How To Use This File

1. Load `.env` into your shell using your normal workflow before starting the server or Inspector.
2. Run the baseline automated checks first so you do not debug live issues on top of local build failures.
3. Execute the manual MCP checks through MCP Inspector or another compliant MCP client.
4. Prefer a sandbox or disposable Follow Up Boss account. If you must use a shared QA account, use clearly labeled temporary data.
5. Record every created object ID and clean it up as soon as the checklist allows.

Example shell setup:

```bash
set -a
source .env
set +a
```

## Validation Scratchpad

Record temporary objects here while you work through the checklist.

| Object | ID | Created Via | Cleanup Path | Notes |
| --- | --- | --- | --- | --- |
| Disposable person | `296994` | `followupboss_create_person` | Manual | Created during live MCP validation. No MCP delete tool exists for people. |
| People relationship | `24542` | `followupboss_create_people_relationship` | `followupboss_delete_people_relationship` | Created, fetched, updated, and deleted during wheel-based MCP validation. |
| Email campaign |  | `followupboss_create_email_campaign` | Manual |  |
| Group | `16` | `followupboss_create_group` | `followupboss_delete_group` | Created, updated, and deleted during wheel-based MCP validation. |
| Custom field |  | `followupboss_create_custom_field` | `followupboss_delete_custom_field` |  |
| Deal |  | `followupboss_create_deal` | `followupboss_delete_deal` |  |
| Event | `1899786` | `followupboss_send_event` | Manual | Created for disposable person during wheel-based MCP validation; event ID was confirmed via `followupboss_search_events` because the live send response returned the person resource. |
| Appointment outcome |  | `followupboss_create_appointment_outcome` | `followupboss_delete_appointment_outcome` |  |
| Appointment type |  | `followupboss_create_appointment_type` | `followupboss_delete_appointment_type` |  |
| Appointment | `600998` | `followupboss_create_appointment` | `followupboss_delete_appointment` | Created, fetched, updated, and deleted during wheel-based MCP validation. |
| Action-plan person | `4504` | `followupboss_apply_action_plan` | Manual | Applied action plan `256` to disposable person `296994` and paused it during wheel-based MCP validation. |
| Call | `71431` | `followupboss_create_call` | Manual | Created, fetched, and updated during wheel-based MCP validation. No MCP delete tool exists for calls. |
| Automation person | `525008` | `followupboss_trigger_automation` | Manual | Triggered automation `225` for disposable person `296994` and paused it during wheel-based MCP validation. |
| Pipeline |  | `followupboss_create_pipeline` | `followupboss_delete_pipeline` |  |
| Pond | `28` | `followupboss_create_pond` | `followupboss_delete_pond` | Created, updated, and deleted during wheel-based MCP validation. |
| Stage |  | `followupboss_create_stage` | `followupboss_delete_stage` |  |
| Task | `19821` | `followupboss_create_task` | `followupboss_delete_task` | Created, fetched, updated, and deleted during wheel-based MCP validation. |
| Team | `39` | `followupboss_create_team` | `followupboss_delete_team` | Created, updated, and deleted during wheel-based MCP validation. |
| Template | `2358` | `followupboss_create_template` | `followupboss_delete_template` | Created, updated, merged, and deleted during wheel-based MCP validation. |
| Text message | `165969` | `followupboss_create_text_message` | Manual | Logged external text message, fetched it by ID, and confirmed filtered listing during wheel-based MCP validation. |
| Text message template | `459` | `followupboss_create_text_message_template` | `followupboss_delete_text_message_template` | Created, fetched, updated, merged, and deleted during wheel-based MCP validation. |
| Note | `556416`, `556417` | `followupboss_add_note` | `followupboss_delete_note` | Both temporary notes were deleted during validation. |
| Webhook |  | `followupboss_create_webhook` | `followupboss_delete_webhook` |  |

## Prerequisites And Safety

- [ ] Confirm `.env` provides either `FOLLOWUPBOSS_API_KEY` or `FOLLOWUPBOSS_ACCESS_TOKEN`, plus the matching `FOLLOWUPBOSS_AUTH_MODE` if you are not using the default API key mode.
- [ ] Confirm optional `FOLLOWUPBOSS_SYSTEM_NAME` and `FOLLOWUPBOSS_SYSTEM_KEY` are present if you plan to validate webhook or integration-header-dependent flows.
- [x] Confirm `uv`, `make`, and `npx` are available locally.
- [ ] Confirm you have a safe validation target account and a naming convention for temporary objects such as `MCP Validation <date>`.

Gather and confirm these domain-specific prerequisites before starting the live checks:

- [ ] A valid action plan ID for action plan mutation tests.
- [ ] A valid automation ID for automation mutation tests.
- [ ] A valid inbox app setup for inbox app installation and conversation tests.
- [ ] A valid pipeline or stage target for deal and stage lifecycle tests if your account requires them.
- [ ] A valid appointment owner, type, and outcome setup for appointment tests.
- [ ] A valid reachable webhook receiver URL for webhook creation tests.
- [ ] A valid email marketing `origin` and `origin_id` for email campaign and email event tests.

## Baseline Automated Validation

- [ ] Run `make validate` and confirm the full local quality gate passes.
- [x] Run `make build-smoke` and confirm distribution artifacts still build and validate.
- [ ] Run `FOLLOWUPBOSS_RUN_LIVE_TESTS=1 make live-identity-check` and confirm the live identity smoke test passes with the `.env` credentials.

Current run notes:
- `make validate` failed at the coverage step because live code under `email_marketing` is below the repo's `100%` gate.
- `make live-identity-check` reached the live account successfully but failed on a stale assertion about the shape of the identity response.

## MCP Transport Verification

### Stdio

Use the official Inspector against the stdio transport:

```bash
npx @modelcontextprotocol/inspector uv run followupboss-mcp stdio
```

- [ ] Inspector connects successfully over stdio.
- [x] The server advertises tools, one resource, and one prompt.
- [x] `followupboss_get_identity` succeeds over stdio.
- [x] At least one list tool and one mutating tool succeed over stdio.
- [x] No operational logging or stray text contaminates stdout during stdio use.

### Streamable HTTP

Start the server in one terminal:

```bash
uv run python -m followupboss_mcp.cli streamable-http --host 127.0.0.1 --port 8000 --path /mcp
```

Then connect Inspector to the exposed endpoint.

- [ ] Inspector connects successfully over streamable HTTP.
- [x] `followupboss_get_identity` succeeds over streamable HTTP.
- [x] At least one list tool and one mutating tool succeed over streamable HTTP.
- [x] Resource access and prompt rendering both work over streamable HTTP.
- [x] Shutting the server down cleanly does not leave the transport wedged for the next run.

## Resource And Prompt Checks

- [x] Read `followupboss://api-coverage-matrix` and confirm it returns the current coverage matrix content rather than an empty or stale response.
- [x] Render `followupboss_compose_lead_event` and confirm it produces usable guidance for composing a canonical `POST /events` payload.
- [x] Confirm both the resource and the prompt are visible from both stdio and streamable HTTP clients.

## Cross-Cutting Assertions

Apply these checks wherever the surface below supports them.

- [ ] Every list or search tool returns a top-level collection plus `_metadata`.
- [ ] Every paginated list is exercised with a small page size such as `limit=1` so `_metadata`, `next_token`, and `offset` behavior are validated.
- [ ] Every get-by-ID tool is validated with an ID taken from either a list result or a just-created object.
- [ ] Every update tool returns the mutated object and the changed values are visible in the response.
- [ ] Every delete tool returns a structured confirmation payload with `deleted: true` and the correct identifier key.
- [ ] At least one safe failure path is exercised without leaking secrets, such as requesting a clearly invalid ID or intentionally omitting a required field in Inspector.
- [ ] If `FOLLOWUPBOSS_SYSTEM_NAME` and `FOLLOWUPBOSS_SYSTEM_KEY` are configured, at least one flow that depends on integration headers succeeds.
- [ ] With `FOLLOWUPBOSS_LOG_LEVEL=DEBUG`, logs still stay off stdout in stdio mode.

## Domain Checklist

### Identity

- [x] `followupboss_get_identity`: confirm the returned account and user details match the credential you expected to load from `.env`.

### People

- [x] `followupboss_search_people`: run with a small `limit`; confirm `people` plus `_metadata`.
- [x] `followupboss_get_person`: fetch a person ID returned by the search call.
- [x] `followupboss_create_person`: create a disposable person with clearly temporary data.
- [x] `followupboss_update_person`: update the disposable person and confirm the changed fields are reflected in the response.
- [x] Record the created `personId` and reuse it in later sections where a person is required.
- [x] Note that there is no MCP delete tool for people; plan manual cleanup if needed.

### People Relationships

- [ ] `followupboss_list_people_relationships`: confirm list output and `_metadata`.
- [x] `followupboss_get_people_relationship`: retrieve a relationship ID from the list response or from the created relationship below.
- [x] `followupboss_create_people_relationship`: create a disposable relationship for the validation person.
- [x] `followupboss_update_people_relationship`: update the relationship and confirm the mutated values.
- [x] `followupboss_delete_people_relationship`: delete the disposable relationship and confirm the structured delete response.

Current run note: the live `/peopleRelationships` endpoint now returns a paginated object, but `PeopleRelationshipsService.list_people_relationships()` still expects a raw list, so this MCP path currently fails.

### Events

- [x] `followupboss_search_events`: confirm list output and `_metadata`.
- [x] `followupboss_get_event`: retrieve one event ID returned by the list call.
- [x] `followupboss_send_event`: send a canonical lead or lead-activity event using safe test data and confirm the response shape is valid enough for live use.

Current run note: `followupboss_send_event` created event `1899786` for disposable person `296994`, and `followupboss_search_events` confirmed the event. The immediate live response payload came back as the person resource keyed by `person.id` rather than an event record, so follow-up search/get checks are still useful here.

### Email Marketing

This domain is currently registered in `mcp_registration.py` even though it is easy to overlook in the broader docs set. Validate it explicitly.

- [x] `followupboss_list_email_campaigns`: confirm the campaign list path works with your available `origin` filters.
- [ ] `followupboss_create_email_campaign`: create a disposable campaign using a valid `origin` and `origin_id`.
- [ ] `followupboss_update_email_campaign`: update the created campaign and confirm the changed content.
- [x] `followupboss_list_email_events`: confirm list output with a small page size.
- [ ] `followupboss_send_email_events`: send a minimal disposable batch of email events linked to valid sandbox data.
- [ ] Note that there is no MCP delete tool for email campaigns or sent email events; plan manual cleanup if your sandbox retains them.

### Action Plans

- [x] `followupboss_list_action_plans`: confirm list output and `_metadata`.
- [x] `followupboss_list_action_plan_people`: confirm list output and `_metadata`.
- [x] `followupboss_apply_action_plan`: apply a known action plan to the validation person.
- [x] `followupboss_update_action_plan_person`: pause or resume the created action-plan-person relationship and confirm the updated state.
- [x] Note any manual rollback needed because there is no direct MCP delete or unapply tool.

Current run note: action plan `256` was applied to disposable person `296994`, producing action-plan-person `4504`, which was then paused.

### Automations

- [x] `followupboss_list_automations`: confirm list output and `_metadata`.
- [x] `followupboss_get_automation`: retrieve a known automation by ID.
- [x] `followupboss_list_automation_people`: confirm list output and `_metadata`.
- [x] `followupboss_get_automation_person`: fetch a known automation-person relationship by ID.
- [x] `followupboss_trigger_automation`: trigger a known automation for the validation person.
- [x] `followupboss_update_automation_person`: pause or resume the automation-person relationship and confirm the updated state.
- [x] Note any manual rollback needed because automation runs are stateful.

Current run note: automation `225` was triggered for disposable person `296994`, producing automation-person `525008`, which was then paused.

### Groups

- [x] `followupboss_list_groups`: confirm list output and `_metadata`.
- [x] `followupboss_list_round_robin_groups`: confirm the round-robin-specific listing path works.
- [x] `followupboss_get_group`: retrieve a known group by ID.
- [x] `followupboss_create_group`: create a disposable group.
- [x] `followupboss_update_group`: update the created group and confirm the mutated values.
- [x] `followupboss_delete_group`: delete the disposable group and confirm the structured delete response.

### Inbox Apps

These checks require a real inbox app setup with valid installation, conversation, message, and participant data.

- [ ] `followupboss_list_inbox_app_installations`: confirm the installation list path works.
- [ ] `followupboss_install_inbox_app`: install an inbox app in a disposable scope if your sandbox supports it.
- [ ] `followupboss_deactivate_inbox_app`: deactivate the disposable installation and confirm the response.
- [ ] `followupboss_add_inbox_app_message`: add a disposable conversation message.
- [ ] `followupboss_add_inbox_app_note`: add a disposable conversation note.
- [ ] `followupboss_list_inbox_app_participants`: confirm the participant list path works.
- [ ] `followupboss_add_inbox_app_participant`: add a disposable participant to the test conversation.
- [ ] `followupboss_update_inbox_app_conversation`: update conversation status or metadata and confirm the changes.
- [ ] `followupboss_update_inbox_app_message`: update the test message by ID or external message ID.
- [ ] `followupboss_remove_inbox_app_participant`: remove the disposable participant and confirm success.
- [ ] Record any gaps in your sandbox prerequisites instead of silently skipping this domain.

### Users

- [x] `followupboss_list_users`: confirm list output and `_metadata`.
- [x] `followupboss_get_user`: retrieve a user ID returned by the list call.

### Appointment Outcomes

- [x] `followupboss_list_appointment_outcomes`: confirm list output and `_metadata`.
- [x] `followupboss_get_appointment_outcome`: fetch one outcome by ID.
- [ ] `followupboss_create_appointment_outcome`: create a disposable outcome.
- [ ] `followupboss_update_appointment_outcome`: update the disposable outcome and confirm the changed values.
- [ ] `followupboss_delete_appointment_outcome`: delete the disposable outcome and confirm the structured delete response.

Current run note: the current credential receives `403` for appointment outcome mutations.

### Appointment Types

- [x] `followupboss_list_appointment_types`: confirm list output and `_metadata`.
- [x] `followupboss_get_appointment_type`: fetch one type by ID.
- [ ] `followupboss_create_appointment_type`: create a disposable type.
- [ ] `followupboss_update_appointment_type`: update the disposable type and confirm the changed values.
- [ ] `followupboss_delete_appointment_type`: delete the disposable type and confirm the structured delete response.

Current run note: the current credential receives `403` for appointment type mutations.

### Custom Fields

- [x] `followupboss_list_custom_fields`: confirm list output and `_metadata`.
- [x] `followupboss_get_custom_field`: fetch one field by ID.
- [ ] `followupboss_create_custom_field`: create a disposable custom field using a valid API field name.
- [ ] `followupboss_update_custom_field`: update the disposable field and confirm the changed values.
- [ ] `followupboss_delete_custom_field`: delete the disposable field and confirm the structured delete response.
- [ ] Confirm your test uses the Follow Up Boss field `name`, not only the UI label.

Current run note: the current credential receives `403` for custom field mutations.

### Deals

- [ ] `followupboss_list_deals`: confirm list output and `_metadata`.
- [ ] `followupboss_get_deal`: fetch one deal by ID.
- [ ] `followupboss_create_deal`: create a disposable deal using valid sandbox references.
- [ ] `followupboss_update_deal`: update the disposable deal and confirm the changed values.
- [ ] `followupboss_delete_deal`: delete the disposable deal and confirm the structured delete response.
- [x] `followupboss_list_deal_custom_fields`: confirm the custom-field lookup list works for deal writes.

Current run note: both deal list and get currently fail model validation because the live API is returning a numeric `type` value while `DealRecord` still expects `str`.

### Appointments

- [x] `followupboss_list_appointments`: confirm list output and `_metadata`.
- [x] `followupboss_get_appointment`: fetch one appointment by ID.
- [x] `followupboss_create_appointment`: create a disposable appointment using valid person, owner, and metadata references.
- [x] `followupboss_update_appointment`: update the disposable appointment and confirm the changed values.
- [x] `followupboss_delete_appointment`: delete the disposable appointment and confirm the structured delete response.

### Calls

- [x] `followupboss_list_calls`: confirm list output and `_metadata`.
- [x] `followupboss_get_call`: fetch one call by ID.
- [x] `followupboss_create_call`: create a disposable call log entry.
- [x] `followupboss_update_call`: update the disposable call log and confirm the changed values.
- [x] Note that there is no MCP delete tool for calls; plan manual cleanup if needed.

Current run note: call `71431` was created for disposable person `296994`, fetched by ID, and updated successfully.

### Pipelines

- [x] `followupboss_list_pipelines`: confirm list output and `_metadata`.
- [x] `followupboss_get_pipeline`: fetch one pipeline by ID.
- [ ] `followupboss_create_pipeline`: create a disposable pipeline.
- [ ] `followupboss_update_pipeline`: update the disposable pipeline and confirm the changed values.
- [ ] `followupboss_delete_pipeline`: delete the disposable pipeline and confirm the structured delete response.

Current run note: the current credential receives `403` for pipeline mutations.

### Ponds

- [x] `followupboss_list_ponds`: confirm list output and `_metadata`.
- [x] `followupboss_get_pond`: fetch one pond by ID.
- [x] `followupboss_create_pond`: create a disposable pond.
- [x] `followupboss_update_pond`: update the disposable pond and confirm the changed values.
- [x] `followupboss_delete_pond`: delete the disposable pond with a valid reassignment target and confirm the structured delete response.

### Smart Lists

- [x] `followupboss_list_smart_lists`: confirm list output and `_metadata`.
- [x] `followupboss_get_smart_list`: fetch one smart list by ID.

### Stages

- [x] `followupboss_list_stages`: confirm list output and `_metadata`.
- [x] `followupboss_get_stage`: fetch one stage by ID.
- [ ] `followupboss_create_stage`: create a disposable stage in a valid pipeline.
- [ ] `followupboss_update_stage`: update the disposable stage and confirm the changed values.
- [ ] `followupboss_delete_stage`: delete the disposable stage with a valid reassignment target and confirm the structured delete response.

Current run note: the current credential receives `403` for stage mutations.

### Tasks

- [x] `followupboss_list_tasks`: confirm list output and `_metadata`.
- [x] `followupboss_get_task`: fetch one task by ID.
- [x] `followupboss_create_task`: create a disposable task for the validation person.
- [x] `followupboss_update_task`: update the disposable task and confirm the changed values.
- [x] `followupboss_delete_task`: delete the disposable task and confirm the structured delete response.

Current run note: the create-task tool schema does not mark an assignee as required, but the backend currently requires either `assigned_to` or `assigned_user_id`.

### Team Inboxes

- [x] `followupboss_list_team_inboxes`: confirm list output and `_metadata`.

### Teams

- [x] `followupboss_list_teams`: confirm list output and `_metadata`.
- [x] `followupboss_get_team`: fetch one team by ID.
- [x] `followupboss_create_team`: create a disposable team.
- [x] `followupboss_update_team`: update the disposable team and confirm the changed values.
- [x] `followupboss_delete_team`: delete the disposable team and confirm the structured delete response, including any member-move behavior you depend on.

### Templates

- [x] `followupboss_list_templates`: confirm list output and `_metadata`.
- [x] `followupboss_get_template`: fetch one template by ID.
- [x] `followupboss_merge_template`: merge a template using valid sandbox recipients and confirm the preview content.
- [x] `followupboss_create_template`: create a disposable template.
- [x] `followupboss_update_template`: update the disposable template and confirm the changed values.
- [x] `followupboss_delete_template`: delete the disposable template and confirm the structured delete response.

### Text Messages

- [x] `followupboss_list_text_messages`: confirm list output and `_metadata`.
- [x] `followupboss_get_text_message`: fetch one text message by ID.
- [x] `followupboss_create_text_message`: record a disposable externally sent text message log entry.
- [x] Note that there is no MCP delete tool for text messages; plan manual cleanup if your sandbox retains them.

Current run note: the upstream API rejects unfiltered `GET /textMessages` calls, but the MCP list path succeeds when `person_id` is provided.
Current run note: `followupboss_create_text_message` rejected placeholder `555-*` numbers but succeeded with valid E.164-style numbers, creating text message `165969` for disposable person `296994`.

### Text Message Templates

- [x] `followupboss_list_text_message_templates`: confirm list output and `_metadata`.
- [x] `followupboss_get_text_message_template`: fetch one template by ID.
- [x] `followupboss_merge_text_message_template`: merge a template using valid sandbox recipients and confirm the preview content.
- [x] `followupboss_create_text_message_template`: create a disposable text message template.
- [x] `followupboss_update_text_message_template`: update the disposable template and confirm the changed values.
- [x] `followupboss_delete_text_message_template`: delete the disposable template and confirm the structured delete response.

### Notes

- [x] `followupboss_add_note`: create a disposable note for the validation person.
- [x] `followupboss_get_note`: fetch the created note by ID.
- [x] `followupboss_update_note`: update the created note and confirm the changed values.
- [x] `followupboss_delete_note`: delete the created note and confirm the structured delete response.

### Webhooks

- [ ] `followupboss_list_webhooks`: confirm list output and `_metadata`.
- [ ] `followupboss_get_webhook`: fetch one webhook by ID.
- [ ] `followupboss_create_webhook`: create a disposable webhook pointed at a safe receiver URL.
- [ ] `followupboss_delete_webhook`: delete the disposable webhook and confirm the structured delete response.
- [ ] If your webhook workflow depends on `X-System-Key`, confirm the receiver validates the signature with the exact raw request body bytes.

Current run note: the current credential is not the account owner, so live webhook listing is blocked with `403 Only the account owner may access webhooks.`

## Cleanup And Follow-Up

- [x] Delete every temporary object that has an MCP delete tool.
- [ ] Manually clean up every temporary object that does not currently have an MCP delete tool, including people, calls, text messages, email campaigns, email events, and any stateful automation or action-plan artifacts.
- [ ] Review the scratchpad and confirm no temporary IDs were left behind.
- [ ] If any registered tool was missing from the broader docs, update `docs/mcp-usage.md`.
- [ ] If validation exposed an official Follow Up Boss endpoint that is still missing from the server, update `docs/api-coverage-matrix.md`.
- [ ] If this run is being used as release evidence, update `docs/final-validation-report.md`.
- [ ] Capture any blocked domains, missing sandbox prerequisites, or contract drift findings in the issue tracker or release notes before the next validation cycle.
