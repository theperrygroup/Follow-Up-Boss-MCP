# API Coverage Matrix

Generated from the official Follow Up Boss doc-ingestion manifest and an explicit repository coverage declaration.

| Endpoint | Implementation | Models | MCP | Tests | Notes |
| --- | --- | --- | --- | --- | --- |
| `DELETE /appointmentOutcomes/{id}` | Implemented | Input only | Yes | Yes | Delete requires assignOutcomeId and returns structured deletion confirmation. |
| `DELETE /appointmentTypes/{id}` | Implemented | Input only | Yes | Yes | Delete requires assignTypeId and returns structured deletion confirmation. |
| `DELETE /appointments/:id` | Implemented | Input only | Yes | Yes | Delete returns structured deletion confirmation. |
| `DELETE /customFields/:id` | Deferred | No | No | No | Deferred until explicit custom field admin support is requested. |
| `DELETE /dealAttachments/{id}` | Deferred | No | No | No | Discovered during the official docs crawl and intentionally deferred from the current repository scope. |
| `DELETE /dealCustomFields/:id` | Deferred | No | No | No | Discovered during the official docs crawl and intentionally deferred from the current repository scope. |
| `DELETE /deals/{id}` | Implemented | Input only | Yes | Yes | Delete returns structured deletion confirmation. |
| `DELETE /groups/:id` | Deferred | No | No | No | Discovered during the official docs crawl and intentionally deferred from the current repository scope. |
| `DELETE /inboxApps/{inboxAppId}` | Deferred | No | No | No | Discovered during the official docs crawl and intentionally deferred from the current repository scope. |
| `DELETE /inboxApps/{inboxAppId}/conversations/{extConversationId}/participants/{participantId}` | Deferred | No | No | No | Discovered during the official docs crawl and intentionally deferred from the current repository scope. |
| `DELETE /notes/:id` | Implemented | Input only | Yes | Yes | Delete returns structured deletion confirmation. |
| `DELETE /people/:id` | Deferred | No | No | No | Not part of the requested MCP tool surface. |
| `DELETE /peopleRelationships/:id` | Deferred | No | No | No | Discovered during the official docs crawl and intentionally deferred from the current repository scope. |
| `DELETE /personAttachments/{id}` | Deferred | No | No | No | Discovered during the official docs crawl and intentionally deferred from the current repository scope. |
| `DELETE /pipelines/:id` | Implemented | Input only | Yes | Yes | Delete returns structured deletion confirmation. |
| `DELETE /ponds/:id` | Implemented | Input only | Yes | Yes | Delete requires assignTo and returns structured deletion confirmation. |
| `DELETE /reactions/{refType}/{refId}` | Deferred | No | No | No | Discovered during the official docs crawl and intentionally deferred from the current repository scope. |
| `DELETE /stages/:id` | Implemented | Input only | Yes | Yes | Delete requires assignStageId and returns structured deletion confirmation. |
| `DELETE /tasks/:id` | Implemented | Input only | Yes | Yes | Delete returns structured deletion confirmation. |
| `DELETE /teams/:id` | Deferred | No | No | No | Discovered during the official docs crawl and intentionally deferred from the current repository scope. |
| `DELETE /templates/:id` | Implemented | Input only | Yes | Yes | Delete returns structured deletion confirmation. |
| `DELETE /textMessageTemplates/:id` | Implemented | Input only | Yes | Yes | Delete returns structured deletion confirmation. |
| `DELETE /users/:id` | Deferred | No | No | No | Deferred until explicitly needed. |
| `DELETE /webhooks/:id` | Implemented | Input only | Yes | Yes | Delete endpoint exposed through MCP. |
| `GET /actionPlans` | Deferred | No | No | No | Discovered during the official docs crawl and intentionally deferred from the current repository scope. |
| `GET /actionPlansPeople` | Deferred | No | No | No | Discovered during the official docs crawl and intentionally deferred from the current repository scope. |
| `GET /appointmentOutcomes` | Implemented | Yes | Yes | Yes | Lists appointment outcomes with pagination metadata and sort support. |
| `GET /appointmentOutcomes/{id}` | Implemented | Yes | Yes | Yes | Single-appointment-outcome lookup. |
| `GET /appointmentTypes` | Implemented | Yes | Yes | Yes | Lists appointment types with pagination metadata and sort support. |
| `GET /appointmentTypes/{id}` | Implemented | Yes | Yes | Yes | Single-appointment-type lookup. |
| `GET /appointments` | Implemented | Yes | Yes | Yes | Supports documented appointment filters and pagination metadata. |
| `GET /appointments/:id` | Implemented | Yes | Yes | Yes | Single-appointment lookup. |
| `GET /automations` | Deferred | No | No | No | Discovered during the official docs crawl and intentionally deferred from the current repository scope. |
| `GET /automations/{id}` | Deferred | No | No | No | Discovered during the official docs crawl and intentionally deferred from the current repository scope. |
| `GET /automationsPeople` | Deferred | No | No | No | Discovered during the official docs crawl and intentionally deferred from the current repository scope. |
| `GET /automationsPeople/{id}` | Deferred | No | No | No | Discovered during the official docs crawl and intentionally deferred from the current repository scope. |
| `GET /calls` | Implemented | Yes | Yes | Yes | Supports documented call filters and pagination metadata. |
| `GET /calls/:id` | Implemented | Yes | Yes | Yes | Single-call lookup. |
| `GET /customFields` | Implemented | Yes | Yes | Yes | Supports custom field name validation helpers. |
| `GET /customFields/:id` | Deferred | No | No | No | Deferred until explicit custom field admin support is requested. |
| `GET /dealAttachments/{id}` | Deferred | No | No | No | Discovered during the official docs crawl and intentionally deferred from the current repository scope. |
| `GET /dealCustomFields` | Implemented | Yes | Yes | Yes | Lists deal custom fields for write-time field-name discovery. |
| `GET /dealCustomFields/:id` | Deferred | No | No | No | Discovered during the official docs crawl and intentionally deferred from the current repository scope. |
| `GET /deals` | Implemented | Yes | Yes | Yes | Supports documented deal filters and pagination metadata. |
| `GET /deals/{id}` | Implemented | Yes | Yes | Yes | Single-deal lookup with dynamic custom field support. |
| `GET /emCampaigns` | Deferred | No | No | No | Discovered during the official docs crawl and intentionally deferred from the current repository scope. |
| `GET /emEvents` | Deferred | No | No | No | Discovered during the official docs crawl and intentionally deferred from the current repository scope. |
| `GET /events` | Implemented | Yes | Yes | Yes | Supports next-token pagination. |
| `GET /events/:id` | Implemented | Yes | Yes | Yes | Single-event lookup. |
| `GET /groups` | Deferred | No | No | No | Discovered during the official docs crawl and intentionally deferred from the current repository scope. |
| `GET /groups/:id` | Deferred | No | No | No | Discovered during the official docs crawl and intentionally deferred from the current repository scope. |
| `GET /groups/roundRobin` | Deferred | No | No | No | Discovered during the official docs crawl and intentionally deferred from the current repository scope. |
| `GET /identity` | Implemented | Yes | Yes | Yes | Used as the health check path. |
| `GET /inboxApps/installedApps/{publishedInboxAppId}` | Deferred | No | No | No | Discovered during the official docs crawl and intentionally deferred from the current repository scope. |
| `GET /inboxApps/{inboxAppId}/conversations/{extConversationId}/participants` | Deferred | No | No | No | Discovered during the official docs crawl and intentionally deferred from the current repository scope. |
| `GET /me` | Deferred | No | No | No | Discovered during the official docs crawl and intentionally deferred from the current repository scope. |
| `GET /notes/:id` | Implemented | Yes | Yes | Yes | Single-note lookup. |
| `GET /people` | Implemented | Yes | Yes | Yes | Supports next-token and offset pagination. |
| `GET /people/:id` | Implemented | Yes | Yes | Yes | Supports fields selection. |
| `GET /people/checkDuplicate` | Deferred | No | No | No | Discovered during the official docs crawl and intentionally deferred from the current repository scope. |
| `GET /people/unclaimed` | Deferred | No | No | No | Discovered during the official docs crawl and intentionally deferred from the current repository scope. |
| `GET /peopleRelationships` | Deferred | No | No | No | Discovered during the official docs crawl and intentionally deferred from the current repository scope. |
| `GET /peopleRelationships/:id` | Deferred | No | No | No | Discovered during the official docs crawl and intentionally deferred from the current repository scope. |
| `GET /personAttachments/{id}` | Deferred | No | No | No | Discovered during the official docs crawl and intentionally deferred from the current repository scope. |
| `GET /pipelines` | Implemented | Yes | Yes | Yes | Lists pipelines with exact-name filtering and pagination metadata. |
| `GET /pipelines/{id}` | Implemented | Yes | Yes | Yes | Single-pipeline lookup including stage definitions. |
| `GET /ponds` | Implemented | Yes | Yes | Yes | Lists ponds with documented pagination metadata. |
| `GET /ponds/:id` | Implemented | Yes | Yes | Yes | Single-pond lookup. |
| `GET /reactions/{id}` | Deferred | No | No | No | Discovered during the official docs crawl and intentionally deferred from the current repository scope. |
| `GET /smartLists` | Implemented | Yes | Yes | Yes | Lists smart lists with pagination metadata and documented fub2/all filters. |
| `GET /smartLists/:id` | Implemented | Yes | Yes | Yes | Single-smart-list lookup. |
| `GET /stages` | Implemented | Yes | Yes | Yes | Lists stages with pagination metadata and documented sort support. |
| `GET /stages/:id` | Implemented | Yes | Yes | Yes | Single-stage lookup. |
| `GET /tasks` | Implemented | Yes | Yes | Yes | Supports documented task filters and pagination metadata. |
| `GET /tasks/:id` | Implemented | Yes | Yes | Yes | Single-task lookup. |
| `GET /teamInboxes` | Deferred | No | No | No | Discovered during the official docs crawl and intentionally deferred from the current repository scope. |
| `GET /teams` | Deferred | No | No | No | Discovered during the official docs crawl and intentionally deferred from the current repository scope. |
| `GET /teams/:id` | Deferred | No | No | No | Discovered during the official docs crawl and intentionally deferred from the current repository scope. |
| `GET /templates` | Implemented | Yes | Yes | Yes | Lists email templates with pagination metadata. |
| `GET /templates/:id` | Implemented | Yes | Yes | Yes | Single-template lookup with optional mergePersonId support. |
| `GET /textMessageTemplates` | Implemented | Yes | Yes | Yes | Lists text message templates with pagination metadata. |
| `GET /textMessageTemplates/{id}` | Implemented | Yes | Yes | Yes | Single text message template lookup. |
| `GET /textMessages` | Implemented | Yes | Yes | Yes | Lists text messages for a person or phone number. |
| `GET /textMessages/{id}` | Implemented | Yes | Yes | Yes | Single-text-message lookup. |
| `GET /threadedReplies/{id}` | Deferred | No | No | No | Discovered during the official docs crawl and intentionally deferred from the current repository scope. |
| `GET /timeframes` | Deferred | No | No | No | Discovered during the official docs crawl and intentionally deferred from the current repository scope. |
| `GET /users` | Implemented | Yes | Yes | Yes | Collection query coverage included. |
| `GET /users/:id` | Implemented | Yes | Yes | Yes | Single-user lookup. |
| `GET /webhookEvents/:id` | Deferred | No | No | No | Discovered during the official docs crawl and intentionally deferred from the current repository scope. |
| `GET /webhooks` | Implemented | Yes | Yes | Yes | Requires registered system headers. |
| `GET /webhooks/:id` | Implemented | Yes | Yes | Yes | Single-webhook lookup. |
| `POST /actionPlansPeople` | Deferred | No | No | No | Discovered during the official docs crawl and intentionally deferred from the current repository scope. |
| `POST /appointmentOutcomes` | Implemented | Yes | Yes | Yes | Creates an appointment outcome with optional orderWeight support. |
| `POST /appointmentTypes` | Implemented | Yes | Yes | Yes | Creates an appointment type with optional orderWeight support. |
| `POST /appointments` | Implemented | Yes | Yes | Yes | Creates an appointment with optional invitees and sendInvitation support. |
| `POST /automationsPeople` | Deferred | No | No | No | Discovered during the official docs crawl and intentionally deferred from the current repository scope. |
| `POST /calls` | Implemented | Yes | Yes | Yes | Creates a call log entry for a related person. |
| `POST /customFields` | Deferred | No | No | No | Deferred until explicit custom field admin support is requested. |
| `POST /dealAttachments` | Deferred | No | No | No | Discovered during the official docs crawl and intentionally deferred from the current repository scope. |
| `POST /dealCustomFields` | Deferred | No | No | No | Discovered during the official docs crawl and intentionally deferred from the current repository scope. |
| `POST /deals` | Implemented | Yes | Yes | Yes | Creates a deal and supports dynamic deal custom field values. |
| `POST /emCampaigns` | Deferred | No | No | No | Discovered during the official docs crawl and intentionally deferred from the current repository scope. |
| `POST /emEvents` | Deferred | No | No | No | Discovered during the official docs crawl and intentionally deferred from the current repository scope. |
| `POST /events` | Implemented | Yes | Yes | Yes | Canonical external lead and lead-activity ingestion path. |
| `POST /groups` | Deferred | No | No | No | Discovered during the official docs crawl and intentionally deferred from the current repository scope. |
| `POST /inboxApps/install` | Deferred | No | No | No | Discovered during the official docs crawl and intentionally deferred from the current repository scope. |
| `POST /inboxApps/{inboxAppId}/conversations/{extConversationId}/participants` | Deferred | No | No | No | Discovered during the official docs crawl and intentionally deferred from the current repository scope. |
| `POST /inboxApps/{inboxAppId}/message` | Deferred | No | No | No | Discovered during the official docs crawl and intentionally deferred from the current repository scope. |
| `POST /inboxApps/{inboxAppId}/note` | Deferred | No | No | No | Discovered during the official docs crawl and intentionally deferred from the current repository scope. |
| `POST /notes` | Implemented | Yes | Yes | Yes | Supports optional person-availability wait flow. |
| `POST /people` | Implemented | Yes | Yes | Yes | Documented as non-canonical for lead ingestion; prefer POST /events. |
| `POST /people/claim` | Deferred | No | No | No | Discovered during the official docs crawl and intentionally deferred from the current repository scope. |
| `POST /people/ignoreUnclaimed` | Deferred | No | No | No | Discovered during the official docs crawl and intentionally deferred from the current repository scope. |
| `POST /peopleRelationships` | Deferred | No | No | No | Discovered during the official docs crawl and intentionally deferred from the current repository scope. |
| `POST /personAttachments` | Deferred | No | No | No | Discovered during the official docs crawl and intentionally deferred from the current repository scope. |
| `POST /pipelines` | Implemented | Yes | Yes | Yes | Creates a pipeline with optional ordered stages. |
| `POST /ponds` | Implemented | Yes | Yes | Yes | Creates a pond with a lead agent and full member list. |
| `POST /reactions/{refType}/{refId}` | Deferred | No | No | No | Discovered during the official docs crawl and intentionally deferred from the current repository scope. |
| `POST /stages` | Implemented | Yes | Yes | Yes | Creates a stage with optional orderWeight support. |
| `POST /tasks` | Implemented | Yes | Yes | Yes | Requires a related person and an assignee. |
| `POST /teams` | Deferred | No | No | No | Discovered during the official docs crawl and intentionally deferred from the current repository scope. |
| `POST /templates` | Implemented | Yes | Yes | Yes | Creates a new email template. |
| `POST /templates/merge` | Deferred | No | No | No | Discovered during the official docs crawl and intentionally deferred from the current repository scope. |
| `POST /textMessageTemplates` | Implemented | Yes | Yes | Yes | Creates a new text message template. |
| `POST /textMessageTemplates/merge` | Deferred | No | No | No | Discovered during the official docs crawl and intentionally deferred from the current repository scope. |
| `POST /textMessages` | Deferred | No | No | No | Discovered during the official docs crawl and intentionally deferred from the current repository scope. |
| `POST /webhooks` | Implemented | Yes | Yes | Yes | Requires registered system headers and owner-level permissions. |
| `PUT /actionPlansPeople/:id` | Deferred | No | No | No | Discovered during the official docs crawl and intentionally deferred from the current repository scope. |
| `PUT /appointmentOutcomes/{id}` | Implemented | Yes | Yes | Yes | Updates appointment outcome metadata with documented orderWeight behavior. |
| `PUT /appointmentTypes/{id}` | Implemented | Yes | Yes | Yes | Updates appointment type metadata with documented orderWeight behavior. |
| `PUT /appointments/:id` | Implemented | Yes | Yes | Yes | Updates an appointment and supports sendInvitation query semantics. |
| `PUT /automationsPeople/{id}` | Deferred | No | No | No | Discovered during the official docs crawl and intentionally deferred from the current repository scope. |
| `PUT /calls/:id` | Implemented | Yes | Yes | Yes | Updates a call log entry. |
| `PUT /customFields/:id` | Deferred | No | No | No | Deferred until explicit custom field admin support is requested. |
| `PUT /dealAttachments/{id}` | Deferred | No | No | No | Discovered during the official docs crawl and intentionally deferred from the current repository scope. |
| `PUT /dealCustomFields/:id` | Deferred | No | No | No | Discovered during the official docs crawl and intentionally deferred from the current repository scope. |
| `PUT /deals/{id}` | Implemented | Yes | Yes | Yes | Updates a deal and preserves documented custom field semantics. |
| `PUT /emCampaigns/:id` | Deferred | No | No | No | Discovered during the official docs crawl and intentionally deferred from the current repository scope. |
| `PUT /groups/:id` | Deferred | No | No | No | Discovered during the official docs crawl and intentionally deferred from the current repository scope. |
| `PUT /inboxApps/:inboxAppId/message` | Deferred | No | No | No | Discovered during the official docs crawl and intentionally deferred from the current repository scope. |
| `PUT /inboxApps/{inboxAppId}/conversations/{extConversationId}` | Deferred | No | No | No | Discovered during the official docs crawl and intentionally deferred from the current repository scope. |
| `PUT /notes/:id` | Implemented | Yes | Yes | Yes | Single-note update. |
| `PUT /people/:id` | Implemented | Yes | Yes | Yes | Supports mergeTags query semantics. |
| `PUT /peopleRelationships/:id` | Deferred | No | No | No | Discovered during the official docs crawl and intentionally deferred from the current repository scope. |
| `PUT /personAttachments/{id}` | Deferred | No | No | No | Discovered during the official docs crawl and intentionally deferred from the current repository scope. |
| `PUT /pipelines/{id}` | Implemented | Yes | Yes | Yes | Updates pipeline metadata and supports stage create-or-update semantics. |
| `PUT /ponds/:id` | Implemented | Yes | Yes | Yes | Updates pond metadata and expects complete member replacement semantics. |
| `PUT /stages/:id` | Implemented | Yes | Yes | Yes | Updates stage metadata with documented orderWeight behavior. |
| `PUT /tasks/:id` | Implemented | Yes | Yes | Yes | Supports task completion and due-date updates. |
| `PUT /teams/:id` | Deferred | No | No | No | Discovered during the official docs crawl and intentionally deferred from the current repository scope. |
| `PUT /templates/:id` | Implemented | Yes | Yes | Yes | Updates template name, subject, and body. |
| `PUT /textMessageTemplates/:id` | Implemented | Yes | Yes | Yes | Updates text message template content and sharing state. |
| `PUT /webhooks/:id` | Deferred | No | No | No | Deferred until explicitly needed. |
