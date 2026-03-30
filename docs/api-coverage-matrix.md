# API Coverage Matrix

Generated from the official Follow Up Boss doc-ingestion manifest and an explicit repository coverage declaration.

| Endpoint | Implementation | Models | MCP | Tests | Notes |
| --- | --- | --- | --- | --- | --- |
| `DELETE /appointmentOutcomes/{id}` | Implemented | Input only | Yes | Yes | Delete requires assignOutcomeId and returns structured deletion confirmation. |
| `DELETE /appointmentTypes/{id}` | Implemented | Input only | Yes | Yes | Delete requires assignTypeId and returns structured deletion confirmation. |
| `DELETE /appointments/:id` | Implemented | Input only | Yes | Yes | Delete returns structured deletion confirmation. |
| `DELETE /customFields/:id` | Implemented | Input only | Yes | Yes | Deletes a custom field and returns structured deletion confirmation. |
| `DELETE /dealAttachments/{id}` | Implemented | Input only | Yes | Yes | Deletes a deal attachment and returns structured deletion confirmation. |
| `DELETE /dealCustomFields/:id` | Implemented | Input only | Yes | Yes | Deletes a deal custom field and returns structured deletion confirmation. |
| `DELETE /deals/{id}` | Implemented | Input only | Yes | Yes | Delete returns structured deletion confirmation. |
| `DELETE /groups/:id` | Implemented | Input only | Yes | Yes | Delete returns structured deletion confirmation. |
| `DELETE /inboxApps/{inboxAppId}` | Implemented | Input only | Yes | Yes | Deactivates an inbox app installation and returns structured deletion confirmation. |
| `DELETE /inboxApps/{inboxAppId}/conversations/{extConversationId}/participants/{participantId}` | Implemented | Input only | Yes | Yes | Removes an inbox app conversation participant and returns structured deletion confirmation. |
| `DELETE /notes/:id` | Implemented | Input only | Yes | Yes | Delete returns structured deletion confirmation. |
| `DELETE /people/:id` | Deferred | No | No | No | Not part of the requested MCP tool surface. |
| `DELETE /peopleRelationships/:id` | Implemented | Input only | Yes | Yes | Deletes a people relationship and returns structured deletion confirmation. |
| `DELETE /personAttachments/{id}` | Implemented | Input only | Yes | Yes | Deletes a person attachment and returns structured deletion confirmation. |
| `DELETE /pipelines/:id` | Implemented | Input only | Yes | Yes | Delete returns structured deletion confirmation. |
| `DELETE /ponds/:id` | Implemented | Input only | Yes | Yes | Delete requires assignTo and returns structured deletion confirmation. |
| `DELETE /reactions/{refType}/{refId}` | Implemented | Input only | Yes | Yes | Deletes a reaction from a note, call, or threaded reply. |
| `DELETE /stages/:id` | Implemented | Input only | Yes | Yes | Delete requires assignStageId and returns structured deletion confirmation. |
| `DELETE /tasks/:id` | Implemented | Input only | Yes | Yes | Delete returns structured deletion confirmation. |
| `DELETE /teams/:id` | Implemented | Input only | Yes | Yes | Delete optionally supports moveToTeamId and returns structured deletion confirmation. |
| `DELETE /templates/:id` | Implemented | Input only | Yes | Yes | Delete returns structured deletion confirmation. |
| `DELETE /textMessageTemplates/:id` | Implemented | Input only | Yes | Yes | Delete returns structured deletion confirmation. |
| `DELETE /users/:id` | Deferred | No | No | No | Deferred until explicitly needed. |
| `DELETE /webhooks/:id` | Implemented | Input only | Yes | Yes | Delete endpoint exposed through MCP. |
| `GET /actionPlans` | Implemented | Yes | Yes | Yes | Lists action plans with documented filters and pagination metadata. |
| `GET /actionPlansPeople` | Implemented | Yes | Yes | Yes | Lists action-plan-person relationships with documented filters and pagination metadata. |
| `GET /appointmentOutcomes` | Implemented | Yes | Yes | Yes | Lists appointment outcomes with pagination metadata and sort support. |
| `GET /appointmentOutcomes/{id}` | Implemented | Yes | Yes | Yes | Single-appointment-outcome lookup. |
| `GET /appointmentTypes` | Implemented | Yes | Yes | Yes | Lists appointment types with pagination metadata and sort support. |
| `GET /appointmentTypes/{id}` | Implemented | Yes | Yes | Yes | Single-appointment-type lookup. |
| `GET /appointments` | Implemented | Yes | Yes | Yes | Supports documented appointment filters and pagination metadata. |
| `GET /appointments/:id` | Implemented | Yes | Yes | Yes | Single-appointment lookup. |
| `GET /automations` | Implemented | Yes | Yes | Yes | Lists Automations 2.0 workflows with documented filters and pagination metadata. |
| `GET /automations/{id}` | Implemented | Yes | Yes | Yes | Single-automation lookup for registered-system automation workflows. |
| `GET /automationsPeople` | Implemented | Yes | Yes | Yes | Lists automation-person pairings with person, automation, and status filters. |
| `GET /automationsPeople/{id}` | Implemented | Yes | Yes | Yes | Single automation-person pairing lookup. |
| `GET /calls` | Implemented | Yes | Yes | Yes | Supports documented call filters and pagination metadata. |
| `GET /calls/:id` | Implemented | Yes | Yes | Yes | Single-call lookup. |
| `GET /customFields` | Implemented | Yes | Yes | Yes | Supports custom field name validation helpers. |
| `GET /customFields/:id` | Implemented | Yes | Yes | Yes | Fetches a single custom field by ID. |
| `GET /dealAttachments/{id}` | Implemented | Yes | Yes | Yes | Fetches a registered-system deal attachment by ID. |
| `GET /dealCustomFields` | Implemented | Yes | Yes | Yes | Lists deal custom fields for write-time field-name discovery. |
| `GET /dealCustomFields/:id` | Implemented | Yes | Yes | Yes | Fetches a single deal custom field by ID. |
| `GET /deals` | Implemented | Yes | Yes | Yes | Supports documented deal filters and pagination metadata. |
| `GET /deals/{id}` | Implemented | Yes | Yes | Yes | Single-deal lookup with dynamic custom field support. |
| `GET /emCampaigns` | Implemented | Yes | Yes | Yes | Lists email marketing campaigns with origin and originId filtering. |
| `GET /emEvents` | Implemented | Yes | Yes | Yes | Lists email marketing events with documented filters and pagination metadata. |
| `GET /events` | Implemented | Yes | Yes | Yes | Supports next-token pagination. |
| `GET /events/:id` | Implemented | Yes | Yes | Yes | Single-event lookup. |
| `GET /groups` | Implemented | Yes | Yes | Yes | Lists groups with documented type and sort filters plus pagination metadata. |
| `GET /groups/:id` | Implemented | Yes | Yes | Yes | Single-group lookup. |
| `GET /groups/roundRobin` | Implemented | Yes | Yes | Yes | Lists groups and includes round-robin assignment details. |
| `GET /identity` | Implemented | Yes | Yes | Yes | Used as the health check path. |
| `GET /inboxApps/installedApps/{publishedInboxAppId}` | Implemented | Yes | Yes | Yes | Lists installed inbox app installations for a published inbox app. |
| `GET /inboxApps/{inboxAppId}/conversations/{extConversationId}/participants` | Implemented | Yes | Yes | Yes | Lists inbox app conversation participants with synthetic pagination metadata. |
| `GET /me` | Deferred | No | No | No | Discovered during the official docs crawl and intentionally deferred from the current repository scope. |
| `GET /notes/:id` | Implemented | Yes | Yes | Yes | Single-note lookup. |
| `GET /people` | Implemented | Yes | Yes | Yes | Supports next-token and offset pagination. |
| `GET /people/:id` | Implemented | Yes | Yes | Yes | Supports fields selection. |
| `GET /people/checkDuplicate` | Implemented | Yes | Yes | Yes | Checks whether a person already exists by email address or phone number. |
| `GET /people/unclaimed` | Implemented | Yes | Yes | Yes | Lists unclaimed leads available to the authenticated user. |
| `GET /peopleRelationships` | Implemented | Yes | Yes | Yes | Lists people relationships with synthetic pagination metadata. |
| `GET /peopleRelationships/:id` | Implemented | Yes | Yes | Yes | Fetches a single people relationship by ID. |
| `GET /personAttachments/{id}` | Implemented | Yes | Yes | Yes | Fetches a registered-system person attachment by ID. |
| `GET /pipelines` | Implemented | Yes | Yes | Yes | Lists pipelines with exact-name filtering and pagination metadata. |
| `GET /pipelines/{id}` | Implemented | Yes | Yes | Yes | Single-pipeline lookup including stage definitions. |
| `GET /ponds` | Implemented | Yes | Yes | Yes | Lists ponds with documented pagination metadata. |
| `GET /ponds/:id` | Implemented | Yes | Yes | Yes | Single-pond lookup. |
| `GET /reactions/{id}` | Implemented | Yes | Yes | Yes | Fetches a single reaction by ID. |
| `GET /smartLists` | Implemented | Yes | Yes | Yes | Lists smart lists with pagination metadata and documented fub2/all filters. |
| `GET /smartLists/:id` | Implemented | Yes | Yes | Yes | Single-smart-list lookup. |
| `GET /stages` | Implemented | Yes | Yes | Yes | Lists stages with pagination metadata and documented sort support. |
| `GET /stages/:id` | Implemented | Yes | Yes | Yes | Single-stage lookup. |
| `GET /tasks` | Implemented | Yes | Yes | Yes | Supports documented task filters and pagination metadata. |
| `GET /tasks/:id` | Implemented | Yes | Yes | Yes | Single-task lookup. |
| `GET /teamInboxes` | Implemented | Yes | Yes | Yes | Lists team inboxes with pagination metadata. |
| `GET /teams` | Implemented | Yes | Yes | Yes | Lists teams with pagination metadata. |
| `GET /teams/:id` | Implemented | Yes | Yes | Yes | Single-team lookup. |
| `GET /templates` | Implemented | Yes | Yes | Yes | Lists email templates with pagination metadata. |
| `GET /templates/:id` | Implemented | Yes | Yes | Yes | Single-template lookup with optional mergePersonId support. |
| `GET /textMessageTemplates` | Implemented | Yes | Yes | Yes | Lists text message templates with pagination metadata. |
| `GET /textMessageTemplates/{id}` | Implemented | Yes | Yes | Yes | Single text message template lookup. |
| `GET /textMessages` | Implemented | Yes | Yes | Yes | Lists text messages for a person or phone number. |
| `GET /textMessages/{id}` | Implemented | Yes | Yes | Yes | Single-text-message lookup. |
| `GET /threadedReplies/{id}` | Implemented | Yes | Yes | Yes | Fetches a single threaded reply with nested reactions. |
| `GET /timeframes` | Implemented | Yes | Yes | Yes | Lists valid Follow Up Boss timeframes for people timeframeId values. |
| `GET /users` | Implemented | Yes | Yes | Yes | Collection query coverage included. |
| `GET /users/:id` | Implemented | Yes | Yes | Yes | Single-user lookup. |
| `GET /webhookEvents/:id` | Deferred | No | No | No | Discovered during the official docs crawl and intentionally deferred from the current repository scope. |
| `GET /webhooks` | Implemented | Yes | Yes | Yes | Requires registered system headers. |
| `GET /webhooks/:id` | Implemented | Yes | Yes | Yes | Single-webhook lookup. |
| `POST /actionPlansPeople` | Implemented | Yes | Yes | Yes | Applies an action plan to a specific person. |
| `POST /appointmentOutcomes` | Implemented | Yes | Yes | Yes | Creates an appointment outcome with optional orderWeight support. |
| `POST /appointmentTypes` | Implemented | Yes | Yes | Yes | Creates an appointment type with optional orderWeight support. |
| `POST /appointments` | Implemented | Yes | Yes | Yes | Creates an appointment with optional invitees and sendInvitation support. |
| `POST /automationsPeople` | Implemented | Yes | Yes | Yes | Triggers an Automation 2.0 workflow for a specific person. |
| `POST /calls` | Implemented | Yes | Yes | Yes | Creates a call log entry for a related person. |
| `POST /customFields` | Implemented | Yes | Yes | Yes | Creates a custom field for the authenticated account owner. |
| `POST /dealAttachments` | Implemented | Yes | Yes | Yes | Creates a registered-system deal attachment using an external URI. |
| `POST /dealCustomFields` | Implemented | Yes | Yes | Yes | Creates a deal custom field with the documented admin-only options. |
| `POST /deals` | Implemented | Yes | Yes | Yes | Creates a deal and supports dynamic deal custom field values. |
| `POST /emCampaigns` | Implemented | Yes | Yes | Yes | Creates an email marketing campaign with required origin identifiers. |
| `POST /emEvents` | Implemented | Yes | Yes | Yes | Posts batched email marketing events and returns accepted IDs plus skipped recipients. |
| `POST /events` | Implemented | Yes | Yes | Yes | Canonical external lead and lead-activity ingestion path. |
| `POST /groups` | Implemented | Yes | Yes | Yes | Creates a group with distribution and first-to-claim defaults where needed. |
| `POST /inboxApps/install` | Implemented | Yes | Yes | Yes | Installs an inbox app for account-wide or user-scoped usage. |
| `POST /inboxApps/{inboxAppId}/conversations/{extConversationId}/participants` | Implemented | Yes | Yes | Yes | Adds a participant to an inbox app conversation. |
| `POST /inboxApps/{inboxAppId}/message` | Implemented | Yes | Yes | Yes | Adds a message to an inbox app conversation with typed sender and owner payloads. |
| `POST /inboxApps/{inboxAppId}/note` | Implemented | Yes | Yes | Yes | Adds a note to an inbox app conversation with typed user attribution. |
| `POST /notes` | Implemented | Yes | Yes | Yes | Supports optional person-availability wait flow. |
| `POST /people` | Implemented | Yes | Yes | Yes | Documented as non-canonical for lead ingestion; prefer POST /events. |
| `POST /people/claim` | Implemented | Yes | Yes | Yes | Claims an offered lead and surfaces both success and already-claimed payloads. |
| `POST /people/ignoreUnclaimed` | Implemented | Input only | Yes | Yes | Acknowledges and ignores an unclaimed lead offer. |
| `POST /peopleRelationships` | Implemented | Yes | Yes | Yes | Creates a people relationship for a person. |
| `POST /personAttachments` | Implemented | Yes | Yes | Yes | Creates a registered-system person attachment using an external URI. |
| `POST /pipelines` | Implemented | Yes | Yes | Yes | Creates a pipeline with optional ordered stages. |
| `POST /ponds` | Implemented | Yes | Yes | Yes | Creates a pond with a lead agent and full member list. |
| `POST /reactions/{refType}/{refId}` | Implemented | Yes | Yes | Yes | Adds a reaction to a note, call, or threaded reply. |
| `POST /stages` | Implemented | Yes | Yes | Yes | Creates a stage with optional orderWeight support. |
| `POST /tasks` | Implemented | Yes | Yes | Yes | Requires a related person and an assignee. |
| `POST /teams` | Implemented | Yes | Yes | Yes | Creates a team with members and optional leader IDs. |
| `POST /templates` | Implemented | Yes | Yes | Yes | Creates a new email template. |
| `POST /templates/merge` | Implemented | Yes | Yes | Yes | Merges an email template with recipient-aware merge-field expansion. |
| `POST /textMessageTemplates` | Implemented | Yes | Yes | Yes | Creates a new text message template. |
| `POST /textMessageTemplates/merge` | Implemented | Yes | Yes | Yes | Merges a text message template with recipient-aware merge-field expansion. |
| `POST /textMessages` | Implemented | Yes | Yes | Yes | Records an externally sent text message log entry. |
| `POST /webhooks` | Implemented | Yes | Yes | Yes | Requires registered system headers and owner-level permissions. |
| `PUT /actionPlansPeople/:id` | Implemented | Yes | Yes | Yes | Pauses or resumes an action-plan-person relationship. |
| `PUT /appointmentOutcomes/{id}` | Implemented | Yes | Yes | Yes | Updates appointment outcome metadata with documented orderWeight behavior. |
| `PUT /appointmentTypes/{id}` | Implemented | Yes | Yes | Yes | Updates appointment type metadata with documented orderWeight behavior. |
| `PUT /appointments/:id` | Implemented | Yes | Yes | Yes | Updates an appointment and supports sendInvitation query semantics. |
| `PUT /automationsPeople/{id}` | Implemented | Yes | Yes | Yes | Pauses or resumes an automation-person pairing. |
| `PUT /calls/:id` | Implemented | Yes | Yes | Yes | Updates a call log entry. |
| `PUT /customFields/:id` | Implemented | Yes | Yes | Yes | Updates custom field metadata and dropdown-choice mappings by ID. |
| `PUT /dealAttachments/{id}` | Implemented | Yes | Yes | Yes | Updates a registered-system deal attachment by ID. |
| `PUT /dealCustomFields/:id` | Implemented | Yes | Yes | Yes | Updates a deal custom field and preserves dropdown choice remapping support. |
| `PUT /deals/{id}` | Implemented | Yes | Yes | Yes | Updates a deal and preserves documented custom field semantics. |
| `PUT /emCampaigns/:id` | Implemented | Yes | Yes | Yes | Updates an email marketing campaign subject, name, or HTML body. |
| `PUT /groups/:id` | Implemented | Yes | Yes | Yes | Updates group metadata and member assignment defaults. |
| `PUT /inboxApps/:inboxAppId/message` | Implemented | Yes | Yes | Yes | Updates inbox app message delivery metadata or external message IDs. |
| `PUT /inboxApps/{inboxAppId}/conversations/{extConversationId}` | Implemented | Yes | Yes | Yes | Updates inbox app conversation subject, archive state, person, or assignment. |
| `PUT /notes/:id` | Implemented | Yes | Yes | Yes | Single-note update. |
| `PUT /people/:id` | Implemented | Yes | Yes | Yes | Supports mergeTags query semantics. |
| `PUT /peopleRelationships/:id` | Implemented | Yes | Yes | Yes | Updates a people relationship and preserves overwrite semantics for arrays. |
| `PUT /personAttachments/{id}` | Implemented | Yes | Yes | Yes | Updates a registered-system person attachment by ID. |
| `PUT /pipelines/{id}` | Implemented | Yes | Yes | Yes | Updates pipeline metadata and supports stage create-or-update semantics. |
| `PUT /ponds/:id` | Implemented | Yes | Yes | Yes | Updates pond metadata and expects complete member replacement semantics. |
| `PUT /stages/:id` | Implemented | Yes | Yes | Yes | Updates stage metadata with documented orderWeight behavior. |
| `PUT /tasks/:id` | Implemented | Yes | Yes | Yes | Supports task completion and due-date updates. |
| `PUT /teams/:id` | Implemented | Yes | Yes | Yes | Updates team metadata and expects complete member and leader replacement semantics. |
| `PUT /templates/:id` | Implemented | Yes | Yes | Yes | Updates template name, subject, and body. |
| `PUT /textMessageTemplates/:id` | Implemented | Yes | Yes | Yes | Updates text message template content and sharing state. |
| `PUT /webhooks/:id` | Deferred | No | No | No | Deferred until explicitly needed. |
