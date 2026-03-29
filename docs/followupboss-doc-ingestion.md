# Follow Up Boss Doc Ingestion

## Sources Ingested

The ingestion process used only official Follow Up Boss documentation pages under `https://docs.followupboss.com/reference`.

Artifacts produced by the script:

- machine-readable manifest: `docs/followupboss-endpoint-manifest.json`
- human-readable summary: `docs/followupboss-doc-ingestion.md`

Seed pages:

- `https://docs.followupboss.com/reference/getting-started`
- `https://docs.followupboss.com/reference/identification`
- `https://docs.followupboss.com/reference/authentication`
- `https://docs.followupboss.com/reference/requests-and-responses`
- `https://docs.followupboss.com/reference/error-responses`
- `https://docs.followupboss.com/reference/searching`
- `https://docs.followupboss.com/reference/pagination`
- `https://docs.followupboss.com/reference/rate-limiting`
- `https://docs.followupboss.com/reference/common-filters`
- `https://docs.followupboss.com/reference/common-issues`
- `https://docs.followupboss.com/reference/webhooks-guide`
- `https://docs.followupboss.com/reference/identity`
- `https://docs.followupboss.com/reference/events-get`
- `https://docs.followupboss.com/reference/events-post`
- `https://docs.followupboss.com/reference/people-get`
- `https://docs.followupboss.com/reference/people-post`
- `https://docs.followupboss.com/reference/people-id-get`
- `https://docs.followupboss.com/reference/people-id-put`
- `https://docs.followupboss.com/reference/users-get`
- `https://docs.followupboss.com/reference/users-id-get`
- `https://docs.followupboss.com/reference/customfields-get`
- `https://docs.followupboss.com/reference/notes-post`
- `https://docs.followupboss.com/reference/webhooks-get`
- `https://docs.followupboss.com/reference/webhooks-post`

## Extraction Output

- Total pages discovered: `174`
- Endpoint/reference pages with documented API paths: `153`
- Guide/reference pages without API paths: `21`

## Extraction Fields

- page title
- page slug
- endpoint path
- HTTP method
- short summary
- authentication requirement
- query params
- body fields
- header requirements
- notable warnings and restrictions
- discoverable response fields from official result examples

## Crawl Notes

- Discovery is driven by the official rendered navigation links and limited to `/reference/...` pages on `docs.followupboss.com`.
- URLs are normalized to canonical reference-page URLs so fragments do not create duplicate crawl targets.
- The parser reads the official embedded `ssr-props` JSON object for structured endpoint metadata.
- Warnings and restrictions are derived from markdown callouts in the official page body.
- Response fields are inferred only when the official result examples contain valid JSON.

## Discovered Endpoints

| Method | Path | Slug | Summary |
| --- | --- | --- | --- |
| `GET` | `/actionPlans` | `actionplans-get` | Get a list of Action Plans. |
| `GET` | `/actionPlansPeople` | `actionplanspeople-get` | List Action Plans applied to a particular person or list people on a particular Action Plan. |
| `PUT` | `/actionPlansPeople/:id` | `actionplanspeople-id-put` | Update the status of an Action Plan to Person relationship. |
| `POST` | `/actionPlansPeople` | `actionplanspeople-post` | Apply an Action Plan to a person. |
| `GET` | `/appointmentOutcomes` | `appointmentoutcomes-get` | List appointment outcomes. |
| `DELETE` | `/appointmentOutcomes/{id}` | `appointmentoutcomes-id-delete` | Delete an appointment outcome. |
| `GET` | `/appointmentOutcomes/{id}` | `appointmentoutcomes-id-get` | Retrieve an appointment outcome by ID. |
| `PUT` | `/appointmentOutcomes/{id}` | `appointmentoutcomes-id-put` | Update an appointment outcome. |
| `POST` | `/appointmentOutcomes` | `appointmentoutcomes-post` | Create an appointment outcome. |
| `GET` | `/appointmentTypes` | `appointmenttypes-get` | List appointment types. |
| `DELETE` | `/appointmentTypes/{id}` | `appointmenttypes-id-delete` | Delete an appointment type. |
| `GET` | `/appointmentTypes/{id}` | `appointmenttypes-id-get` | Retrieve an appointment type by ID |
| `PUT` | `/appointmentTypes/{id}` | `appointmenttypes-id-put` | Update an appointment type. |
| `POST` | `/appointmentTypes` | `appointmenttypes-post` | Create an appointment type. |
| `GET` | `/appointments` | `appointments-get` | Search for appointments. |
| `DELETE` | `/appointments/:id` | `appointments-id-delete` | Delete an appointment. |
| `GET` | `/appointments/:id` | `appointments-id-get` | Retrieve an appointment by id. |
| `PUT` | `/appointments/:id` | `appointments-id-put` | Update an appointment. |
| `POST` | `/appointments` | `appointments-post` | Create an appointment. |
| `GET` | `/automations` | `automations` | Get a list of Automations |
| `GET` | `/automations/{id}` | `automationsid` | Retrieve an Automation by ID. |
| `GET` | `/automationsPeople` | `automationspeople` | Get a list of pairings of Automations and the People on which they have or will be run. |
| `POST` | `/automationsPeople` | `automationspeople-1` | Manually trigger an Automation for a specified Person. |
| `PUT` | `/automationsPeople/{id}` | `automationspeopleid` | Pause or unpause an Automation for a Person. |
| `GET` | `/automationsPeople/{id}` | `automationspeopleid-1` | Retrieve an Automation-Person pairing. |
| `GET` | `/calls` | `calls-get` | Search for calls. |
| `GET` | `/calls/:id` | `calls-id-get` | Retrieve a call by id. |
| `PUT` | `/calls/:id` | `calls-id-put` | Update a call. |
| `POST` | `/calls` | `calls-post` | Add a call. |
| `GET` | `/customFields` | `customfields-get` | List all custom fields. |
| `DELETE` | `/customFields/:id` | `customfields-id-delete` | Delete a custom field. |
| `GET` | `/customFields/:id` | `customfields-id-get` | Get a custom field by id. |
| `PUT` | `/customFields/:id` | `customfields-id-put` | Update a custom field. |
| `POST` | `/customFields` | `customfields-post` | Create a custom field. |
| `DELETE` | `/dealAttachments/{id}` | `dealattachments-id-delete` | Delete a deal attachment. |
| `GET` | `/dealAttachments/{id}` | `dealattachments-id-get` | Get a deal attachment by id. |
| `PUT` | `/dealAttachments/{id}` | `dealattachments-id-put` | Update a deal attachment. |
| `POST` | `/dealAttachments` | `dealattachments-post` | Add an attachment to a deal. |
| `GET` | `/deals` | `deals-get` | Search for deals. |
| `DELETE` | `/deals/{id}` | `deals-id-delete` | Delete a deal. |
| `GET` | `/deals/{id}` | `deals-id-get` | Retrieve a deal by id. |
| `PUT` | `/deals/{id}` | `deals-id-put` | Update a deal. |
| `POST` | `/deals` | `deals-post` | Add a deal. |
| `GET` | `/dealCustomFields` | `dealcustomfields-get` | List all deals custom fields available in your account. |
| `DELETE` | `/dealCustomFields/:id` | `dealcustomfields-id-delete` | Delete a deals custom field. |
| `GET` | `/dealCustomFields/:id` | `dealcustomfields-id-get` | Get a deals custom field by ID. |
| `PUT` | `/dealCustomFields/:id` | `dealcustomfields-id-put` | Update a deals custom field. |
| `POST` | `/dealCustomFields` | `dealcustomfields-post` | Create a deals custom field. |
| `GET` | `/emCampaigns` | `emcampaigns-get` | List email marketing campaigns. |
| `PUT` | `/emCampaigns/:id` | `emcampaigns-id-put` | Update an email marketing campaign. |
| `POST` | `/emCampaigns` | `emcampaigns-post` | Create an email marketing campaign. |
| `GET` | `/emEvents` | `emevents-get` | List email marketing events. |
| `POST` | `/emEvents` | `emevents-post` | Notify Follow Up Boss about marketing emails sent, opens, clicks, bounces, unsubscribes and spam reports. |
| `GET` | `/templates` | `templates-get` | Lists all email templates. |
| `DELETE` | `/templates/:id` | `templates-id-delete` | Delete an email template. |
| `GET` | `/templates/:id` | `templates-id-get` | Retrieve an email template by id, optionally merging fields. |
| `PUT` | `/templates/:id` | `templates-id-put` | Update an email template. |
| `POST` | `/templates/merge` | `templates-merge` | Merge an email template with multiple recipients. |
| `POST` | `/templates` | `templates-post` | Create a new email template. |
| `GET` | `/events` | `events-get` | Search for events. |
| `GET` | `/events/:id` | `events-id-get` | Retrieve a single event by id. |
| `POST` | `/events` | `events-post` | Send in a lead or an event related to a lead. |
| `GET` | `/groups` | `groups-get` | List groups. |
| `DELETE` | `/groups/:id` | `groups-id-delete` | Delete a group. |
| `GET` | `/groups/:id` | `groups-id-get` | Retrieve a group by id. |
| `PUT` | `/groups/:id` | `groups-id-put` | Update a group. |
| `POST` | `/groups` | `groups-post` | Create a new group. |
| `GET` | `/groups/roundRobin` | `groups-roundrobin-get` | Lists groups and includes round-robin data. |
| `GET` | `/identity` | `identity` | Get identity and authentication information. |
| `POST` | `/inboxApps/{inboxAppId}/message` | `inbox-apps-add-message` | Adds a message to an existing or new Inbox App conversation. |
| `POST` | `/inboxApps/{inboxAppId}/note` | `inbox-apps-add-note` | Adds a note to an Inbox App conversation. |
| `POST` | `/inboxApps/{inboxAppId}/conversations/{extConversationId}/participants` | `inbox-apps-create-participant` | Adds a participant to an Inbox App conversation. |
| `DELETE` | `/inboxApps/{inboxAppId}` | `inbox-apps-deactivate` | Deactivates an installation of your Inbox App. Useful when a customer unsubscribes from your service, or requests that you turn off Inbox App functionality for them. |
| `DELETE` | `/inboxApps/{inboxAppId}/conversations/{extConversationId}/participants/{participantId}` | `inbox-apps-delete-participant` | Deletes an Inbox App conversation participant. |
| `GET` | `/inboxApps/{inboxAppId}/conversations/{extConversationId}/participants` | `inbox-apps-get-participants` | Retrieves participants in an Inbox App conversation. |
| `POST` | `/inboxApps/install` | `inbox-apps-install` | Installs your Inbox App for an account. |
| `PUT` | `/inboxApps/{inboxAppId}/conversations/{extConversationId}` | `inbox-apps-update-conversation` | Updates an Inbox App conversation. |
| `PUT` | `/inboxApps/:inboxAppId/message` | `inbox-apps-update-message` | Update an Inbox App Message. |
| `GET` | `/inboxApps/installedApps/{publishedInboxAppId}` | `view-inbox-app-installations` | Lists Inbox App installation(s) and ID(s) for your Published Inbox App on the current FUB account. |
| `DELETE` | `/notes/:id` | `notes-id-delete` | Delete a note. |
| `GET` | `/notes/:id` | `notes-id-get` | Retrieve a note by id. |
| `PUT` | `/notes/:id` | `notes-id-put` | Edit a note. |
| `POST` | `/notes` | `notes-post` | Add a note. |
| `GET` | `/people/checkDuplicate` | `people-checkduplicate` | Check whether a person exists in Follow Up Boss. |
| `POST` | `/people/claim` | `people-claim` | Claim a lead. |
| `GET` | `/people` | `people-get` | Search for people. |
| `DELETE` | `/people/:id` | `people-id-delete` | Delete a person by id. |
| `GET` | `/people/:id` | `people-id-get` | Retrieve a person by id. |
| `PUT` | `/people/:id` | `people-id-put` | Update a person by id. |
| `POST` | `/people/ignoreUnclaimed` | `people-ignoreunclaimed` | Ignore a lead. |
| `POST` | `/people` | `people-post` | Manually add a new person. |
| `GET` | `/people/unclaimed` | `peopleunclaimed` | Get unclaimed leads. |
| `DELETE` | `/personAttachments/{id}` | `personattachments-id-delete` | Delete an attachment by ID. |
| `GET` | `/personAttachments/{id}` | `personattachments-id-get` | Retrieve an attachment by ID. |
| `PUT` | `/personAttachments/{id}` | `personattachments-id-put` | Update an attachment by ID. |
| `POST` | `/personAttachments` | `personattachments-post` | Attach a file to a person. |
| `GET` | `/peopleRelationships` | `peoplerelationships` | Get relationships between people in Follow Up Boss. |
| `DELETE` | `/peopleRelationships/:id` | `peoplerelationships-id-delete` | Delete a relationship. |
| `GET` | `/peopleRelationships/:id` | `peoplerelationships-id-get` | Get a specific relationship. |
| `PUT` | `/peopleRelationships/:id` | `peoplerelationships-id-put` | Update details of a specific relationship. |
| `POST` | `/peopleRelationships` | `peoplerelationships-post` | Create a new relationship for a person. |
| `GET` | `/pipelines` | `pipelines-get` | Search for pipelines. |
| `DELETE` | `/pipelines/:id` | `pipelines-id-delete` | Delete a pipeline. |
| `GET` | `/pipelines/{id}` | `pipelines-id-get` | Retrieve a pipeline by id. |
| `PUT` | `/pipelines/{id}` | `pipelines-id-put` | Update a pipeline. |
| `POST` | `/pipelines` | `pipelines-post` | Add a pipeline. |
| `GET` | `/ponds` | `ponds-get` | Get a list of ponds. |
| `DELETE` | `/ponds/:id` | `ponds-id-delete` | Delete a pond by id. |
| `GET` | `/ponds/:id` | `ponds-id-get` | Get a pond by id. |
| `PUT` | `/ponds/:id` | `ponds-id-put` | Update a pond by id. |
| `POST` | `/ponds` | `ponds-post` | Create a pond. |
| `DELETE` | `/reactions/{refType}/{refId}` | `reactions-reftype-refid-delete` | Delete a reaction |
| `POST` | `/reactions/{refType}/{refId}` | `reactions-reftype-refid-post` | Add a reaction to a corresponding reference data object, e.g. "Note" or "ThreadedReply" |
| `GET` | `/reactions/{id}` | `reactionsnoteid` | Fetch a reaction |
| `GET` | `/smartLists/:id` | `smartlist-id-get` | Retrieve a Smart List by id. |
| `GET` | `/smartLists` | `smartlists-get` | Get a list of Smart Lists. |
| `DELETE` | `/stages/:id` | `stage-id-delete` | Delete a stage. |
| `GET` | `/stages` | `stages-get` | Retrieve a list of stages. |
| `GET` | `/stages/:id` | `stages-id-get` | Get a stage by id. |
| `PUT` | `/stages/:id` | `stages-id-put` | Update a stage. |
| `POST` | `/stages` | `stages-post` | Create a new stage. |
| `GET` | `/tasks` | `tasks-get` | Get a list of tasks. |
| `DELETE` | `/tasks/:id` | `tasks-id-delete` | Delete a task. |
| `GET` | `/tasks/:id` | `tasks-id-get` | Get a task by id. |
| `PUT` | `/tasks/:id` | `tasks-id-put` | Update a task. |
| `POST` | `/tasks` | `tasks-post` | Create a new task. |
| `GET` | `/teamInboxes` | `teaminboxes` | Get a list of Team Inboxes |
| `GET` | `/teams` | `teams-get` | Get a list of teams. |
| `DELETE` | `/teams/:id` | `teams-id-delete` | Delete a team by id. |
| `GET` | `/teams/:id` | `teams-id-get` | Get a team by id. |
| `PUT` | `/teams/:id` | `teams-id-put` | Update a team by id. |
| `POST` | `/teams` | `teams-post` | Create a new team. |
| `GET` | `/textMessageTemplates` | `textmessagetemplates-get` | Lists all text message templates. |
| `DELETE` | `/textMessageTemplates/:id` | `textmessagetemplates-id-delete` |  |
| `GET` | `/textMessageTemplates/{id}` | `textmessagetemplates-id-get` | Retrieve a text message template by id. |
| `PUT` | `/textMessageTemplates/:id` | `textmessagetemplates-id-put` | Update a text message template. |
| `POST` | `/textMessageTemplates/merge` | `textmessagetemplates-merge` | Merge a text message template with multiple recipients. |
| `POST` | `//textMessageTemplates` | `textmessagetemplates-post` | Create a text message template. |
| `GET` | `/textMessages` | `textmessages-get` | List text messages for a person or phone number. |
| `GET` | `/textMessages/{id}` | `textmessages-id-get` | Retrieve a text message by id. |
| `POST` | `/textMessages` | `textmessages-post` | Create a record of an externally sent text message. |
| `GET` | `/threadedReplies/{id}` | `threadedreplies-copy` | Fetches a threaded reply |
| `GET` | `/me` | `me` | Retrieve information about the currently authenticated user. |
| `GET` | `/users` | `users-get` | Search for users. |
| `DELETE` | `/users/:id` | `users-id-delete` | Delete a user. |
| `GET` | `/users/:id` | `users-id-get` | Retrieve a user by id. |
| `GET` | `/webhookEvents/:id` | `webhookevents-get` | Get a list of events for a given webhook. |
| `GET` | `/webhooks` | `webhooks-get` | Get a list of webhooks. |
| `DELETE` | `/webhooks/:id` | `webhooks-id-delete` | Delete a webhook. |
| `GET` | `/webhooks/:id` | `webhooks-id-get` | Get details of a specific webhook. |
| `PUT` | `/webhooks/:id` | `webhooks-id-put` | Update a webhook. |
| `POST` | `/webhooks` | `webhooks-post` | Subscribe to a new webhook. |
| `GET` | `/timeframes` | `timeframes-get` | Get a list of timeframes. |

## Limitations

- Some official pages provide placeholder `{}` response examples instead of a detailed schema; those pages may have sparse response-field extraction.
- Some parameter names appear as wildcard patterns such as `custom*`; those are preserved as documented rather than expanded into account-specific field names.
