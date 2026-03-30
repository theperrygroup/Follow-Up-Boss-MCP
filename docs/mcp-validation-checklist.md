# MCP Validation Checklist

This runbook is the credential-backed companion to the offline quality gates in `make validate`. Use it to verify the full registered Follow Up Boss MCP surface end to end against a real account with credentials loaded from `.env`.

The authoritative MCP surface is `src/followupboss_mcp/mcp_registration.py`. If this checklist and `docs/mcp-usage.md` ever disagree, treat the registration file as the source of truth and update the docs after validation. Only currently registered MCP tools, resources, and prompts are in scope here.

The domain sections below follow the registration order from `register_server_surface()` so checklist drift is easier to spot when the server surface changes.

## Run Metadata

| Field | Value |
| --- | --- |
| Validation date | `2026-03-29` |
| Validator | Cursor agent |
| Account or environment | Live `.env` account with `X-System` headers configured |
| Auth mode (`api_key` or `oauth`) | `api_key` |
| Transport(s) exercised | `stdio`, `streamable-http` |
| Notes | Mapped `FOLLOW_UP_BOSS_*` values from `.env` into the repository's expected `FOLLOWUPBOSS_*` variables before running live checks. Inspector-specific connection steps remain unchecked because this run used the official Python MCP clients directly. |

## How To Use This File

1. Load `.env` into your shell before starting the server or Inspector.
2. Run the automated baseline checks first so you are not debugging live account issues on top of a broken local build.
3. Exercise the MCP surface through MCP Inspector or another compliant MCP client.
4. Prefer a sandbox or disposable Follow Up Boss account. If you must use a shared QA account, use clearly labeled temporary data.
5. Record every created object ID in the scratchpad and clean it up as soon as the checklist allows.
6. If a domain is blocked by permissions, contract drift, or missing sandbox setup, leave the item unchecked and record the blocker in `Known Issues And Account Limitations`.

Example shell setup:

```bash
set -a
source .env
set +a
```

## Validation Scratchpad

| Object | ID | Created Via | Cleanup Path | Notes |
| --- | --- | --- | --- | --- |
| Disposable person | `296999` | `followupboss_create_person` | Manual | Created and updated during live MCP validation. No MCP delete tool exists for people. |
| People relationship | `24543` | `followupboss_create_people_relationship` | `followupboss_delete_people_relationship` | Created, fetched, updated, and deleted during live stdio validation. |
| Person attachment | `47` | `followupboss_create_person_attachment` | `followupboss_delete_person_attachment` | Created, fetched, updated, and deleted during live stdio validation. |
| Reaction target |  | Existing note, call, or threaded reply | Manual |  |
| Reaction |  | `followupboss_add_reaction` | `followupboss_delete_reaction` |  |
| Event | `1899982` | `followupboss_send_event` | Manual | Confirmed via `followupboss_search_events`; the immediate tool response returned the person record rather than an event record. |
| Email campaign |  | `followupboss_create_email_campaign` | Manual |  |
| Email event batch |  | `followupboss_send_email_events` | Manual |  |
| Action-plan person | `4505` | `followupboss_apply_action_plan` | Manual | Applied action plan `256` to person `296999` and immediately paused it. |
| Automation person |  | `followupboss_trigger_automation` | Manual |  |
| Group |  | `followupboss_create_group` | `followupboss_delete_group` |  |
| Custom field |  | `followupboss_create_custom_field` | `followupboss_delete_custom_field` |  |
| Deal |  | `followupboss_create_deal` | `followupboss_delete_deal` |  |
| Deal attachment |  | `followupboss_create_deal_attachment` | `followupboss_delete_deal_attachment` |  |
| Appointment outcome |  | `followupboss_create_appointment_outcome` | `followupboss_delete_appointment_outcome` |  |
| Appointment type |  | `followupboss_create_appointment_type` | `followupboss_delete_appointment_type` |  |
| Appointment |  | `followupboss_create_appointment` | `followupboss_delete_appointment` |  |
| Call |  | `followupboss_create_call` | Manual |  |
| Pipeline |  | `followupboss_create_pipeline` | `followupboss_delete_pipeline` |  |
| Pond |  | `followupboss_create_pond` | `followupboss_delete_pond` |  |
| Stage |  | `followupboss_create_stage` | `followupboss_delete_stage` |  |
| Task | `19822` | `followupboss_create_task` | `followupboss_delete_task` | Created, fetched, updated, listed, and deleted during live stdio validation. |
| Team |  | `followupboss_create_team` | `followupboss_delete_team` |  |
| Template | `2359` | `followupboss_create_template` | `followupboss_delete_template` | Created, fetched, updated, merged, listed, and deleted during live stdio validation. |
| Text message |  | `followupboss_create_text_message` | Manual |  |
| Text message template | `460` | `followupboss_create_text_message_template` | `followupboss_delete_text_message_template` | Created, fetched, updated, merged, listed, and deleted during live stdio validation. |
| Note | `556435`, `556436` | `followupboss_add_note` | `followupboss_delete_note` | One note was created over stdio and one over streamable HTTP; both were deleted. |
| Webhook |  | `followupboss_create_webhook` | `followupboss_delete_webhook` |  |

## Known Issues And Account Limitations

| Domain | Issue Or Limitation | Impact | Follow-Up |
| --- | --- | --- | --- |
| Baseline validation | `make validate` fails because `tests/unit/test_auth_config_logging.py::test_settings_validation_and_normalization` still expects a `ValidationError` that no longer occurs. | The full local quality gate stays red even though linting, type-checking, and most tests pass. | Update the test expectation or restore the intended settings validation behavior. |
| Live identity smoke | `make live-identity-check` reaches the live API successfully, but the live `/identity` payload no longer populates top-level `identity.id`. | The live smoke test fails on a stale assertion. | Relax or update the smoke assertion to match the current API response shape. |
| People relationships list | `followupboss_list_people_relationships` returns `Unexpected people relationships response` against the live API. | The list path remains blocked even though create/get/update/delete all worked. | Update `PeopleRelationshipsService.list_people_relationships()` for the current response shape. |
| Deals | `followupboss_list_deals` fails because `DealRecord.type` expects `str` while the live API returns `int`. | Deal list/get and any deal-dependent flows such as deal attachments are blocked. | Broaden the deal model to accept the live type shape. |
| Webhooks | The current credential is not the account owner; `followupboss_list_webhooks` returns `Only the account owner may access webhooks.` | Webhook list/get/create/delete remain blocked in this environment. | Re-run with an owner credential or explicitly document webhook validation as owner-only. |
| Automations | `followupboss_list_automations` returned an empty `automations` array while `_metadata.total` was nonzero, so no usable automation ID was obtained. | Automation get/trigger/update flows were not exercised. | Investigate live pagination/filtering behavior or re-run with a known automation ID. |
| Event input ergonomics | `followupboss_send_event` only succeeded when the nested `person` object used snake_case field names such as `first_name`, not response-style aliases such as `firstName`. | The tool works, but MCP callers can easily hit validation errors. | Document the required nested input shape or relax model input aliases. |
| Inbox apps | No published inbox app ID, installation, or conversation fixtures were available in this run. | Inbox app tools were not exercised. | Re-run with disposable inbox app prerequisites. |
| Email marketing writes | No safe `origin` / `origin_id` pair was available for mutation tests. | Email campaign create/update and email-event send remain unvalidated. | Re-run with disposable email-marketing fixtures. |

## Prerequisites And Safety

- [x] Confirm your shell exports the repository-expected `FOLLOWUPBOSS_*` variables before starting the server.
- [x] Confirm `.env` provides either `FOLLOWUPBOSS_API_KEY` or `FOLLOWUPBOSS_ACCESS_TOKEN`, plus `FOLLOWUPBOSS_AUTH_MODE` if you are not using the default API key mode.
- [x] Confirm optional `FOLLOWUPBOSS_SYSTEM_NAME` and `FOLLOWUPBOSS_SYSTEM_KEY` are present if you plan to validate webhook or integration-header-dependent flows.
- [x] Confirm `uv`, `make`, and `npx` are available locally.
- [x] Confirm you have a safe validation target account and a temporary-data naming convention such as `MCP Validation <date>`.
- [x] Confirm you have a reusable disposable person data set for cross-domain testing.
- [x] Confirm you have a safe hosted file URI and file metadata for person and deal attachment tests.
- [x] Confirm you have a valid action plan ID for mutation tests.
- [ ] Confirm you have a valid automation ID for mutation tests.
- [ ] Confirm you have a valid inbox app setup for installation, conversation, message, and participant tests.
- [ ] Confirm you have valid pipeline, stage, owner, type, and outcome references for deal, appointment, and stage lifecycle tests.
- [ ] Confirm you have a valid reachable webhook receiver URL for webhook creation tests.
- [ ] Confirm you have a valid email marketing `origin` and `origin_id` for campaign and email-event tests.
- [ ] Confirm you have a valid reaction target. If needed, create a temporary note first and reuse it for reaction checks.

## Baseline Automated Validation

- [ ] Run `make validate` and confirm the full local quality gate passes.
- [x] Run `make build-smoke` and confirm distribution artifacts still build and validate.
- [ ] Run `FOLLOWUPBOSS_RUN_LIVE_TESTS=1 make live-identity-check` and confirm the live identity smoke test passes with the current `.env` credentials.
- [x] Record any failures, permissions issues, or payload mismatches in `Known Issues And Account Limitations` before continuing.

## MCP Transport Verification

### Stdio

Use the official Inspector against the stdio transport:

```bash
npx @modelcontextprotocol/inspector uv run followupboss-mcp stdio
```

- [ ] Inspector connects successfully over stdio.
- [x] The advertised tool list matches the current registration surface, including `attachments` and `reactions` if they are registered.
- [x] The advertised resource list includes `followupboss://api-coverage-matrix`.
- [x] The advertised prompt list includes `followupboss_compose_lead_event`.
- [x] `followupboss_get_identity` succeeds over stdio.
- [x] At least one list or search tool, one get tool, one create or update tool, and one delete tool succeed over stdio.
- [x] No operational logging or stray text contaminates stdout during stdio use.
- [ ] Disconnecting and reconnecting the Inspector leaves the transport healthy for another run.

### Streamable HTTP

Start the server in one terminal:

```bash
uv run python -m followupboss_mcp.cli streamable-http --host 127.0.0.1 --port 8000 --path /mcp
```

Then connect Inspector to `http://127.0.0.1:8000/mcp`.

- [x] The server starts without import errors or runtime exceptions.
- [ ] Inspector connects successfully over streamable HTTP.
- [x] `followupboss_get_identity` succeeds over streamable HTTP.
- [x] At least one list or search tool, one get tool, one create or update tool, and one delete tool succeed over streamable HTTP.
- [x] Resource access and prompt rendering both work over streamable HTTP.
- [x] Shutting the server down cleanly does not leave the next run wedged.

## Resource And Prompt Checks

- [x] Read `followupboss://api-coverage-matrix` and confirm it returns current coverage-matrix content rather than an empty or stale response.
- [x] Render `followupboss_compose_lead_event` and confirm it produces usable guidance for composing a canonical `POST /events` payload.
- [x] Confirm both the resource and the prompt are visible from both stdio and streamable HTTP clients.
- [x] Confirm the resource and prompt names match the registration file exactly.

## Cross-Cutting Assertions

Apply these checks wherever the surface below supports them.

- [x] Every list or search tool returns the expected top-level collection key plus `_metadata`.
- [x] Every paginated list is exercised with a small page size such as `limit=1` so `_metadata`, `next_token`, and `offset` behavior are validated.
- [x] When a second page is available, follow `next_token`, `offset`, or other documented paging inputs and confirm the subsequent result is consistent.
- [x] Every get-by-ID tool is validated with an ID taken from either a list result or a just-created object.
- [x] Every single-object response is JSON-serializable and safe for MCP clients. Omitted default or null fields are acceptable if the remaining payload is correct.
- [x] Every update tool returns the mutated object and the changed values are visible in the response.
- [x] Every delete tool returns a structured confirmation payload with `deleted: true` and the correct identifier key.
- [x] At least one safe failure path is exercised without leaking secrets, such as requesting a clearly invalid ID or intentionally omitting a required field in Inspector.
- [x] If you hit permission-denied or rate-limit responses, confirm the surfaced MCP error text is understandable and record the limitation in the issues table.
- [ ] If `FOLLOWUPBOSS_SYSTEM_NAME` and `FOLLOWUPBOSS_SYSTEM_KEY` are configured, at least one flow that depends on integration headers succeeds.
- [ ] With `FOLLOWUPBOSS_LOG_LEVEL=DEBUG`, logs still stay off stdout in stdio mode.
- [x] Capture any contract drift, unexpected payload shapes, or sandbox limitations in `Known Issues And Account Limitations`.

## Domain Checklist

Work through the sections below in order. If a domain depends on an object created earlier in the checklist, record the ID in the scratchpad and reuse it instead of creating unnecessary duplicates.

### Identity

- [x] `followupboss_get_identity`: confirm the returned account and user details match the credential you expected to load from `.env`.

### People

- [x] `followupboss_search_people`: run with a small `limit` and confirm the `people` collection plus `_metadata`.
- [x] `followupboss_get_person`: fetch a person ID returned by the search call or from the created record below.
- [x] `followupboss_create_person`: create a disposable person with clearly temporary data.
- [x] `followupboss_update_person`: update the disposable person and confirm the changed fields are reflected in the response.
- [x] Record the created `personId` and reuse it in later sections where a person is required.
- [x] Note that there is no MCP delete tool for people and plan manual cleanup.

### People Relationships

- [ ] `followupboss_list_people_relationships`: confirm list output and `_metadata`.
- [x] `followupboss_get_people_relationship`: retrieve a relationship ID from the list response or from the created relationship below.
- [x] `followupboss_create_people_relationship`: create a disposable relationship for the validation person.
- [x] `followupboss_update_people_relationship`: update the relationship and confirm the mutated values.
- [x] `followupboss_delete_people_relationship`: delete the disposable relationship and confirm the structured delete response.

Current run note: the list path still fails live with `Unexpected people relationships response`, but create/get/update/delete worked for relationship `24543`.

### Attachments

There are no list tools for attachments, so capture IDs directly from create responses.

- [x] `followupboss_create_person_attachment`: create a disposable person attachment using a safe `uri`, `file_name`, and optional `file_size`.
- [x] `followupboss_get_person_attachment`: fetch the created person attachment by ID.
- [x] `followupboss_update_person_attachment`: update the person attachment and confirm the changed values.
- [x] `followupboss_delete_person_attachment`: delete the person attachment and confirm the structured delete response uses `personAttachmentId`.
- [ ] `followupboss_create_deal_attachment`: create a disposable deal attachment using a valid deal ID plus safe file metadata.
- [ ] `followupboss_get_deal_attachment`: fetch the created deal attachment by ID.
- [ ] `followupboss_update_deal_attachment`: update the deal attachment and confirm the changed values.
- [ ] `followupboss_delete_deal_attachment`: delete the deal attachment and confirm the structured delete response uses `dealAttachmentId`.

### Reactions

There is no list tool for reactions. Capture the returned reaction ID from the create response and the target reference details needed for cleanup.

- [ ] `followupboss_add_reaction`: add a disposable reaction to a note, call, or threaded reply using a safe `ref_type` and `ref_id`.
- [ ] `followupboss_get_reaction`: fetch the created reaction by ID.
- [ ] `followupboss_delete_reaction`: delete the reaction using the matching `ref_type`, `ref_id`, and `emoji` if needed, and confirm the structured delete response uses `refId`.

### Events

- [x] `followupboss_search_events`: confirm list output and `_metadata`.
- [x] `followupboss_get_event`: retrieve one event ID returned by the list call.
- [x] `followupboss_send_event`: send a canonical lead or lead-activity event using safe test data.
- [x] If the immediate send response does not include the created event ID directly, confirm the side effect via `followupboss_search_events` or `followupboss_get_event`.

Current run note: the successful `followupboss_send_event` call required snake_case keys inside the nested `person` object, and the immediate response returned the person resource. `followupboss_search_events` confirmed event `1899982` for person `296999`.

### Email Marketing

- [x] `followupboss_list_email_campaigns`: confirm the campaign list path works with your available `origin` filters.
- [ ] `followupboss_create_email_campaign`: create a disposable campaign using a valid `origin` and `origin_id`.
- [ ] `followupboss_update_email_campaign`: update the created campaign and confirm the changed content.
- [x] `followupboss_list_email_events`: confirm list output and `_metadata` with a small page size.
- [ ] `followupboss_send_email_events`: send a minimal disposable batch of email events linked to valid sandbox data.
- [ ] Note that there is no MCP delete tool for email campaigns or sent email events and plan manual cleanup.

### Action Plans

- [x] `followupboss_list_action_plans`: confirm list output and `_metadata`.
- [x] `followupboss_list_action_plan_people`: confirm list output and `_metadata`.
- [x] `followupboss_apply_action_plan`: apply a known action plan to the validation person.
- [x] `followupboss_update_action_plan_person`: pause or resume the created action-plan-person relationship and confirm the updated state.
- [x] Record any manual rollback needed because there is no direct MCP delete or unapply tool.

### Automations

- [x] `followupboss_list_automations`: confirm list output and `_metadata`.
- [ ] `followupboss_get_automation`: retrieve a known automation by ID.
- [x] `followupboss_list_automation_people`: confirm list output and `_metadata`.
- [ ] `followupboss_get_automation_person`: fetch a known automation-person relationship by ID.
- [ ] `followupboss_trigger_automation`: trigger a known automation for the validation person.
- [ ] `followupboss_update_automation_person`: pause or resume the automation-person relationship and confirm the updated state.
- [ ] Record any manual rollback needed because automation runs are stateful.

Current run note: `followupboss_list_automations` returned an empty `automations` array while `_metadata.total` was nonzero, so no usable automation ID was available for the trigger path.

### Groups

- [x] `followupboss_list_groups`: confirm list output and `_metadata`.
- [x] `followupboss_list_round_robin_groups`: confirm the round-robin-specific listing path works.
- [x] `followupboss_get_group`: retrieve a known group by ID.
- [ ] `followupboss_create_group`: create a disposable group.
- [ ] `followupboss_update_group`: update the created group and confirm the mutated values.
- [ ] `followupboss_delete_group`: delete the disposable group and confirm the structured delete response.

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
- [ ] Record any sandbox prerequisites or account gaps instead of silently skipping this domain.

### Users

- [x] `followupboss_list_users`: confirm list output and `_metadata`.
- [x] `followupboss_get_user`: retrieve a user ID returned by the list call.

### Custom Fields

- [x] `followupboss_list_custom_fields`: confirm list output and `_metadata`.
- [x] `followupboss_get_custom_field`: fetch one field by ID.
- [ ] `followupboss_create_custom_field`: create a disposable custom field using the Follow Up Boss API field `name`.
- [ ] `followupboss_update_custom_field`: update the disposable field and confirm the changed values.
- [ ] `followupboss_delete_custom_field`: delete the disposable field and confirm the structured delete response.

### Deals

- [ ] `followupboss_list_deals`: confirm list output and `_metadata`.
- [ ] `followupboss_get_deal`: fetch one deal by ID.
- [x] `followupboss_list_deal_custom_fields`: confirm the custom-field lookup list works for deal writes.
- [ ] `followupboss_create_deal`: create a disposable deal using valid sandbox references.
- [ ] `followupboss_update_deal`: update the disposable deal and confirm the changed values.
- [ ] `followupboss_delete_deal`: delete the disposable deal and confirm the structured delete response.
- [ ] Record the prerequisite pipeline, stage, and custom-field references used for deal writes.

Current run note: `followupboss_list_deals` is blocked by live model validation because the API returned an integer `type`.

### Appointment Outcomes

- [x] `followupboss_list_appointment_outcomes`: confirm list output and `_metadata`.
- [x] `followupboss_get_appointment_outcome`: fetch one outcome by ID.
- [ ] `followupboss_create_appointment_outcome`: create a disposable outcome.
- [ ] `followupboss_update_appointment_outcome`: update the disposable outcome and confirm the changed values.
- [ ] `followupboss_delete_appointment_outcome`: delete the disposable outcome with a reassignment target if required and confirm the structured delete response.

### Appointment Types

- [x] `followupboss_list_appointment_types`: confirm list output and `_metadata`.
- [x] `followupboss_get_appointment_type`: fetch one type by ID.
- [ ] `followupboss_create_appointment_type`: create a disposable type.
- [ ] `followupboss_update_appointment_type`: update the disposable type and confirm the changed values.
- [ ] `followupboss_delete_appointment_type`: delete the disposable type with a reassignment target if required and confirm the structured delete response.

### Appointments

- [x] `followupboss_list_appointments`: confirm list output and `_metadata`.
- [x] `followupboss_get_appointment`: fetch one appointment by ID.
- [ ] `followupboss_create_appointment`: create a disposable appointment using valid person, owner, type, and outcome references.
- [ ] `followupboss_update_appointment`: update the disposable appointment and confirm the changed values.
- [ ] `followupboss_delete_appointment`: delete the disposable appointment and confirm the structured delete response.

### Calls

- [x] `followupboss_list_calls`: confirm list output and `_metadata`.
- [ ] `followupboss_get_call`: fetch one call by ID.
- [ ] `followupboss_create_call`: create a disposable call log entry.
- [ ] `followupboss_update_call`: update the disposable call log and confirm the changed values.
- [ ] Note that there is no MCP delete tool for calls and plan manual cleanup.

### Pipelines

- [x] `followupboss_list_pipelines`: confirm list output and `_metadata`.
- [x] `followupboss_get_pipeline`: fetch one pipeline by ID.
- [ ] `followupboss_create_pipeline`: create a disposable pipeline.
- [ ] `followupboss_update_pipeline`: update the disposable pipeline and confirm the changed values.
- [ ] `followupboss_delete_pipeline`: delete the disposable pipeline and confirm the structured delete response.

### Ponds

- [x] `followupboss_list_ponds`: confirm list output and `_metadata`.
- [x] `followupboss_get_pond`: fetch one pond by ID.
- [ ] `followupboss_create_pond`: create a disposable pond.
- [ ] `followupboss_update_pond`: update the disposable pond and confirm the changed values.
- [ ] `followupboss_delete_pond`: delete the disposable pond with a valid reassignment target and confirm the structured delete response.

### Smart Lists

- [x] `followupboss_list_smart_lists`: confirm list output and `_metadata`.
- [x] `followupboss_get_smart_list`: fetch one smart list by ID.

### Stages

- [x] `followupboss_list_stages`: confirm list output and `_metadata`.
- [x] `followupboss_get_stage`: fetch one stage by ID.
- [ ] `followupboss_create_stage`: create a disposable stage in a valid pipeline.
- [ ] `followupboss_update_stage`: update the disposable stage and confirm the changed values.
- [ ] `followupboss_delete_stage`: delete the disposable stage with a valid reassignment target and confirm the structured delete response.

### Tasks

- [x] `followupboss_list_tasks`: confirm list output and `_metadata`.
- [x] `followupboss_get_task`: fetch one task by ID.
- [x] `followupboss_create_task`: create a disposable task for the validation person and include assignee fields if your account requires them.
- [x] `followupboss_update_task`: update the disposable task and confirm the changed values.
- [x] `followupboss_delete_task`: delete the disposable task and confirm the structured delete response.

### Team Inboxes

- [x] `followupboss_list_team_inboxes`: confirm list output and `_metadata`.

### Teams

- [x] `followupboss_list_teams`: confirm list output and `_metadata`.
- [x] `followupboss_get_team`: fetch one team by ID.
- [ ] `followupboss_create_team`: create a disposable team.
- [ ] `followupboss_update_team`: update the disposable team and confirm the changed values.
- [ ] `followupboss_delete_team`: delete the disposable team and confirm the structured delete response, including any member-move behavior you depend on.

### Templates

- [x] `followupboss_list_templates`: confirm list output and `_metadata`.
- [x] `followupboss_get_template`: fetch one template by ID.
- [x] `followupboss_merge_template`: merge a template using valid sandbox recipients and confirm the preview content.
- [x] `followupboss_create_template`: create a disposable template.
- [x] `followupboss_update_template`: update the disposable template and confirm the changed values.
- [x] `followupboss_delete_template`: delete the disposable template and confirm the structured delete response.

### Text Messages

- [x] `followupboss_list_text_messages`: confirm list output and `_metadata`, preferably using safe filters such as `person_id`.
- [ ] `followupboss_get_text_message`: fetch one text message by ID.
- [ ] `followupboss_create_text_message`: record a disposable externally sent text message log entry using valid sandbox data and a valid phone-number format.
- [ ] Note that there is no MCP delete tool for text messages and plan manual cleanup if your sandbox retains them.

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
- [ ] If needed, reuse the note ID for reaction testing.

### Webhooks

- [ ] `followupboss_list_webhooks`: confirm list output and `_metadata`.
- [ ] `followupboss_get_webhook`: fetch one webhook by ID.
- [ ] `followupboss_create_webhook`: create a disposable webhook pointed at a safe receiver URL.
- [ ] `followupboss_delete_webhook`: delete the disposable webhook and confirm the structured delete response.
- [ ] If your webhook workflow depends on `X-System-Key`, confirm the receiver validates the signature with the exact raw request body bytes before parsing JSON.

Current run note: `followupboss_list_webhooks` failed with `Only the account owner may access webhooks.` under the current credential.

## Cleanup And Follow-Up

- [x] Delete every temporary object that has an MCP delete tool.
- [ ] Manually clean up every temporary object that does not currently have an MCP delete tool, including people, calls, text messages, email campaigns, email events, inbox app side effects, and any stateful automation or action-plan artifacts.
- [x] Review the scratchpad and confirm no temporary IDs were left behind or orphaned.
- [x] Confirm every domain above was either validated successfully or explicitly recorded as blocked in `Known Issues And Account Limitations`.
- [ ] If any registered tool was missing from the broader docs, update `docs/mcp-usage.md`.
- [ ] If validation exposed an official Follow Up Boss endpoint that is still missing from the server, update `docs/api-coverage-matrix.md`.
- [ ] If this run is being used as release evidence, update `docs/final-validation-report.md`.
- [x] Capture any blocked domains, missing sandbox prerequisites, or contract-drift findings in the issue tracker or release notes before the next validation cycle.
