# MCP tool annotations

Every tool registration supplies `mcp.types.ToolAnnotations` with explicit
`readOnlyHint`, `destructiveHint`, and `openWorldHint` booleans. The Python SDK
uses snake case constructor names and serializes these fields with the MCP
camel case aliases. The three hints describe capabilities across all supported
arguments, including optional invitations, reminders, URL fetches, and workflow
resumption. Optional `idempotentHint` is left unspecified.

## Classification rules

These categories follow [OpenAI's tool planning guidance](https://developers.openai.com/plugins/plan/tools)
and [MCP ToolAnnotations](https://modelcontextprotocol.io/specification/2025-11-25/schema#toolannotations):

- Read operations return private CRM records or compute a preview. They cannot
  create, overwrite, delete, or send user data: **true / false / false**.
- Additive private writes create records without overwriting existing user data
  or causing documented irreversible delivery: **false / false / false**.
- Private destructive writes overwrite fields, delete records, change ownership,
  dismiss an offer, or schedule irreversible email to the bounded CRM assignee:
  **false / true / false**.
- External effects can send to contact recipients, start or resume native
  workflows that do so, fetch arbitrary external URLs, or configure external
  delivery: **false / true / true**. Existing-record overwrite and irreversible
  delivery make these destructive even if other argument combinations are safer.

The order above is **read-only / destructive / open-world**. A private Follow Up
Boss account is bounded even though its API is hosted remotely. Storing an
external URI without fetching it does not itself open the tool's boundary.
Ordinary private calendar replication and customer-configured webhook observers
are not treated as arbitrary external actions of every CRUD tool; explicit
native workflow triggers and external-delivery/fetch fields are counted.

## Behavior exceptions

- `merge_template` and `merge_text_message_template` use POST to compute previews,
  without sending email/text or saving a template. They remain read-only.
  [Email preview](https://docs.followupboss.com/reference/templates-merge),
  [text preview](https://docs.followupboss.com/reference/textmessagetemplates-merge).
- `create_person` can deduplicate by returning an existing contact without
  changing it, and does not run lead automations. `send_event` can update an
  existing contact, run lead workflows and profile enrichment, and cause outbound
  contact communication.
  [Person creation](https://docs.followupboss.com/reference/people-post),
  [lead ingestion](https://docs.followupboss.com/reference/send-in-a-lead).
- `create_call`, `create_email_campaign`, and `send_email_events` record calls,
  campaign metadata, or provider activity; they do not place calls or send email.
  Their update operations overwrite existing metadata.
  [Call logging](https://docs.followupboss.com/reference/calls-post),
  [email event logging](https://docs.followupboss.com/reference/emevents-post).
- `apply_action_plan`, `trigger_automation`, `update_action_plan_person`, and
  `update_automation_person` can start or resume workflows with outbound mail and
  record changes. `update_person` exposes stage/tag changes that trigger native
  automations. `update_deal` exposes deal-stage changes that trigger automations;
  new deal creation is explicitly excluded from that trigger.
  [Native automation actions](https://help.followupboss.com/hc/en-us/articles/33056241868311-Automations-2-0-Overview),
  [deal-stage exception](https://help.followupboss.com/hc/en-us/articles/4402695405847-Trigger-an-Automation-with-a-Deal-s-Stage-Changes).
- `create_task` can schedule a reminder email through `remind_seconds_before`.
  Delivery cannot be recalled, so it is destructive, while the recipient is the
  bounded CRM assignee. `update_task` overwrites private task fields and has no
  reminder or arbitrary-recipient argument.
  [Task creation](https://docs.followupboss.com/reference/tasks-post).
- Appointment create/update pass `send_invitation` as `sendInvitation`, permitting
  invitee email and SMS reminders. Their external effect is conditional but part
  of the static capability. Deletion removes the appointment; the API reference
  does not establish a cancellation email, so no such delivery is assumed.
  [Create](https://docs.followupboss.com/reference/appointments-post),
  [update](https://docs.followupboss.com/reference/appointments-id-put),
  [delete](https://docs.followupboss.com/reference/appointments-id-delete).
- Inbox App installation calls the subscription URL and can overwrite/reactivate
  an existing installation; deactivation emits an external lifecycle webhook.
  Conversation updates can permanently archive and emit assignment/archive
  webhooks. Message addition can overwrite the subject and fetch attachment or
  rich-object URLs. Message-status updates and participant/note records remain
  within the private conversation boundary.
  [Installation lifecycle](https://docs.followupboss.com/docs/inbox-apps-installation-lifecycle),
  [conversation webhooks](https://docs.followupboss.com/docs/inbox-apps-webhooks),
  [attachments](https://docs.followupboss.com/docs/inbox-apps-attachments),
  [rich objects](https://docs.followupboss.com/docs/inbox-apps-rich-objects).
- Person/deal attachments store URI references, unlike Inbox App downloads. Their
  creation is additive; update/delete overwrites/removes private metadata.
  [Person attachment](https://docs.followupboss.com/reference/personattachments-post),
  [deal attachment](https://docs.followupboss.com/reference/dealattachments-post).
- Webhook create/update enables ongoing data delivery to the supplied external
  URL; already delivered data cannot be recalled. Deletion only removes the
  private subscription and does not call the target.
  [Webhook delivery](https://docs.followupboss.com/reference/webhooks-guide).

## Complete catalog

The catalog below records the audited registration categories. Actual request
methods and payloads are in [the service modules](../src/followupboss_mcp/services);
composite reads and workflow adapters are in [the typed adapter](../src/followupboss_mcp/mcp_tools.py).
All values are explicitly advertised by [the server registrations](../src/followupboss_mcp/mcp_registration.py).

- 23 tools: false / false / false.
- 45 tools: false / true / false.
- 15 tools: false / true / true.
- 77 tools: true / false / false.

| Tool | Read-only | Destructive | Open-world | Registration family |
| --- | --- | --- | --- | --- |
| `followupboss_add_inbox_app_message` | false | true | true | inbox app |
| `followupboss_add_inbox_app_note` | false | false | false | inbox app |
| `followupboss_add_inbox_app_participant` | false | false | false | inbox app |
| `followupboss_add_note` | false | false | false | note |
| `followupboss_add_reaction` | false | false | false | reaction |
| `followupboss_apply_action_plan` | false | true | true | action plan |
| `followupboss_check_duplicate_person` | true | false | false | people |
| `followupboss_claim_person` | false | true | false | people |
| `followupboss_create_appointment` | false | true | true | appointment |
| `followupboss_create_appointment_outcome` | false | false | false | appointment metadata |
| `followupboss_create_appointment_type` | false | false | false | appointment metadata |
| `followupboss_create_call` | false | false | false | call |
| `followupboss_create_custom_field` | false | false | false | custom field |
| `followupboss_create_deal` | false | false | false | deal |
| `followupboss_create_deal_attachment` | false | false | false | attachment |
| `followupboss_create_deal_custom_field` | false | false | false | deal |
| `followupboss_create_email_campaign` | false | false | false | email marketing |
| `followupboss_create_group` | false | false | false | group |
| `followupboss_create_people_relationship` | false | false | false | people relationship |
| `followupboss_create_person` | false | false | false | people |
| `followupboss_create_person_attachment` | false | false | false | attachment |
| `followupboss_create_pipeline` | false | false | false | pipeline |
| `followupboss_create_pond` | false | false | false | pond |
| `followupboss_create_stage` | false | false | false | stage |
| `followupboss_create_task` | false | true | false | task |
| `followupboss_create_team` | false | false | false | team |
| `followupboss_create_template` | false | false | false | template |
| `followupboss_create_text_message_template` | false | false | false | text message |
| `followupboss_create_webhook` | false | true | true | webhook |
| `followupboss_deactivate_inbox_app` | false | true | true | inbox app |
| `followupboss_delete_appointment` | false | true | false | appointment |
| `followupboss_delete_appointment_outcome` | false | true | false | appointment metadata |
| `followupboss_delete_appointment_type` | false | true | false | appointment metadata |
| `followupboss_delete_custom_field` | false | true | false | custom field |
| `followupboss_delete_deal` | false | true | false | deal |
| `followupboss_delete_deal_attachment` | false | true | false | attachment |
| `followupboss_delete_deal_custom_field` | false | true | false | deal |
| `followupboss_delete_group` | false | true | false | group |
| `followupboss_delete_note` | false | true | false | note |
| `followupboss_delete_people_relationship` | false | true | false | people relationship |
| `followupboss_delete_person` | false | true | false | people |
| `followupboss_delete_person_attachment` | false | true | false | attachment |
| `followupboss_delete_pipeline` | false | true | false | pipeline |
| `followupboss_delete_pond` | false | true | false | pond |
| `followupboss_delete_reaction` | false | true | false | reaction |
| `followupboss_delete_stage` | false | true | false | stage |
| `followupboss_delete_task` | false | true | false | task |
| `followupboss_delete_team` | false | true | false | team |
| `followupboss_delete_template` | false | true | false | template |
| `followupboss_delete_text_message_template` | false | true | false | text message |
| `followupboss_delete_user` | false | true | false | user |
| `followupboss_delete_webhook` | false | true | false | webhook |
| `followupboss_get_appointment` | true | false | false | appointment |
| `followupboss_get_appointment_outcome` | true | false | false | appointment metadata |
| `followupboss_get_appointment_type` | true | false | false | appointment metadata |
| `followupboss_get_automation` | true | false | false | automation |
| `followupboss_get_automation_person` | true | false | false | automation |
| `followupboss_get_call` | true | false | false | call |
| `followupboss_get_custom_field` | true | false | false | custom field |
| `followupboss_get_deal` | true | false | false | deal |
| `followupboss_get_deal_attachment` | true | false | false | attachment |
| `followupboss_get_deal_custom_field` | true | false | false | deal |
| `followupboss_get_event` | true | false | false | event |
| `followupboss_get_group` | true | false | false | group |
| `followupboss_get_identity` | true | false | false | identity |
| `followupboss_get_latest_lead` | true | false | false | people |
| `followupboss_get_me` | true | false | false | user |
| `followupboss_get_note` | true | false | false | note |
| `followupboss_get_people_relationship` | true | false | false | people relationship |
| `followupboss_get_person` | true | false | false | people |
| `followupboss_get_person_attachment` | true | false | false | attachment |
| `followupboss_get_pipeline` | true | false | false | pipeline |
| `followupboss_get_pond` | true | false | false | pond |
| `followupboss_get_reaction` | true | false | false | reaction |
| `followupboss_get_smart_list` | true | false | false | smart list |
| `followupboss_get_stage` | true | false | false | stage |
| `followupboss_get_task` | true | false | false | task |
| `followupboss_get_team` | true | false | false | team |
| `followupboss_get_template` | true | false | false | template |
| `followupboss_get_text_message` | true | false | false | text message |
| `followupboss_get_text_message_template` | true | false | false | text message |
| `followupboss_get_threaded_reply` | true | false | false | threaded reply |
| `followupboss_get_user` | true | false | false | user |
| `followupboss_get_webhook` | true | false | false | webhook |
| `followupboss_get_webhook_event` | true | false | false | webhook |
| `followupboss_ignore_unclaimed_person` | false | true | false | people |
| `followupboss_install_inbox_app` | false | true | true | inbox app |
| `followupboss_list_action_plan_people` | true | false | false | action plan |
| `followupboss_list_action_plans` | true | false | false | action plan |
| `followupboss_list_active_deals_for_person` | true | false | false | deal |
| `followupboss_list_appointment_outcomes` | true | false | false | appointment metadata |
| `followupboss_list_appointment_types` | true | false | false | appointment metadata |
| `followupboss_list_appointments` | true | false | false | appointment |
| `followupboss_list_automation_people` | true | false | false | automation |
| `followupboss_list_automations` | true | false | false | automation |
| `followupboss_list_calls` | true | false | false | call |
| `followupboss_list_custom_fields` | true | false | false | custom field |
| `followupboss_list_deal_custom_fields` | true | false | false | deal |
| `followupboss_list_deals` | true | false | false | deal |
| `followupboss_list_email_campaigns` | true | false | false | email marketing |
| `followupboss_list_email_events` | true | false | false | email marketing |
| `followupboss_list_groups` | true | false | false | group |
| `followupboss_list_inbox_app_installations` | true | false | false | inbox app |
| `followupboss_list_inbox_app_participants` | true | false | false | inbox app |
| `followupboss_list_my_overdue_tasks` | true | false | false | task |
| `followupboss_list_my_tasks_due_today` | true | false | false | task |
| `followupboss_list_my_upcoming_tasks` | true | false | false | task |
| `followupboss_list_people_relationships` | true | false | false | people relationship |
| `followupboss_list_person_activity` | true | false | false | people |
| `followupboss_list_pipelines` | true | false | false | pipeline |
| `followupboss_list_ponds` | true | false | false | pond |
| `followupboss_list_round_robin_groups` | true | false | false | group |
| `followupboss_list_smart_lists` | true | false | false | smart list |
| `followupboss_list_stages` | true | false | false | stage |
| `followupboss_list_tasks` | true | false | false | task |
| `followupboss_list_team_inboxes` | true | false | false | team inbox |
| `followupboss_list_teams` | true | false | false | team |
| `followupboss_list_templates` | true | false | false | template |
| `followupboss_list_text_message_templates` | true | false | false | text message |
| `followupboss_list_text_messages` | true | false | false | text message |
| `followupboss_list_timeframes` | true | false | false | timeframe |
| `followupboss_list_unclaimed_people` | true | false | false | people |
| `followupboss_list_uncontacted_leads` | true | false | false | people |
| `followupboss_list_users` | true | false | false | user |
| `followupboss_list_webhooks` | true | false | false | webhook |
| `followupboss_merge_template` | true | false | false | template |
| `followupboss_merge_text_message_template` | true | false | false | text message |
| `followupboss_remove_inbox_app_participant` | false | true | false | inbox app |
| `followupboss_search_events` | true | false | false | event |
| `followupboss_search_people` | true | false | false | people |
| `followupboss_search_people_in_smart_list` | true | false | false | people |
| `followupboss_send_email_events` | false | false | false | email marketing |
| `followupboss_send_event` | false | true | true | event |
| `followupboss_trigger_automation` | false | true | true | automation |
| `followupboss_update_action_plan_person` | false | true | true | action plan |
| `followupboss_update_appointment` | false | true | true | appointment |
| `followupboss_update_appointment_outcome` | false | true | false | appointment metadata |
| `followupboss_update_appointment_type` | false | true | false | appointment metadata |
| `followupboss_update_automation_person` | false | true | true | automation |
| `followupboss_update_call` | false | true | false | call |
| `followupboss_update_custom_field` | false | true | false | custom field |
| `followupboss_update_deal` | false | true | true | deal |
| `followupboss_update_deal_attachment` | false | true | false | attachment |
| `followupboss_update_deal_custom_field` | false | true | false | deal |
| `followupboss_update_email_campaign` | false | true | false | email marketing |
| `followupboss_update_group` | false | true | false | group |
| `followupboss_update_inbox_app_conversation` | false | true | true | inbox app |
| `followupboss_update_inbox_app_message` | false | true | false | inbox app |
| `followupboss_update_note` | false | true | false | note |
| `followupboss_update_people_relationship` | false | true | false | people relationship |
| `followupboss_update_person` | false | true | true | people |
| `followupboss_update_person_attachment` | false | true | false | attachment |
| `followupboss_update_pipeline` | false | true | false | pipeline |
| `followupboss_update_pond` | false | true | false | pond |
| `followupboss_update_stage` | false | true | false | stage |
| `followupboss_update_task` | false | true | false | task |
| `followupboss_update_team` | false | true | false | team |
| `followupboss_update_template` | false | true | false | template |
| `followupboss_update_text_message_template` | false | true | false | text message |
| `followupboss_update_webhook` | false | true | true | webhook |

## Validation and release boundary

[The annotation tests](../tests/mcp/test_tool_annotations.py) declare an independent
complete expected-name partition, inspect serialized `tools/list` results for
explicit booleans, and exercise representative read, add, overwrite, delete,
preview, communication-log, and optional invitation behaviors using an offline
client. Existing protocol and tenant suites remain responsible for authentication,
routing, and isolation; annotations do not replace any authorization or validation.

OpenAI imports the deployed endpoint's advertised values. Submission JSON
justifications cannot override them. After authorized integration and deployment,
the submission owner must scan tools again and verify all 160 values against this
catalog before submitting.
[Server annotation scan requirement](https://developers.openai.com/plugins/deploy/app-review).
