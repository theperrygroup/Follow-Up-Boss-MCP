#!/usr/bin/env python3
"""Validate and regenerate the Follow Up Boss API coverage matrix."""

from __future__ import annotations

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = PROJECT_ROOT / "docs" / "followupboss-endpoint-manifest.json"
MATRIX_PATH = PROJECT_ROOT / "docs" / "api-coverage-matrix.md"

COVERAGE_MAP: dict[str, dict[str, str]] = {
    "GET /identity": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Used as the health check path.",
        "tests": "Yes",
    },
    "GET /actionPlans": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Lists action plans with documented filters and pagination metadata.",
        "tests": "Yes",
    },
    "GET /actionPlansPeople": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": (
            "Lists action-plan-person relationships with documented filters "
            "and pagination metadata."
        ),
        "tests": "Yes",
    },
    "POST /actionPlansPeople": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Applies an action plan to a specific person.",
        "tests": "Yes",
    },
    "PUT /actionPlansPeople/:id": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Pauses or resumes an action-plan-person relationship.",
        "tests": "Yes",
    },
    "GET /appointmentOutcomes": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Lists appointment outcomes with pagination metadata and sort support.",
        "tests": "Yes",
    },
    "GET /appointmentOutcomes/{id}": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Single-appointment-outcome lookup.",
        "tests": "Yes",
    },
    "POST /appointmentOutcomes": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Creates an appointment outcome with optional orderWeight support.",
        "tests": "Yes",
    },
    "PUT /appointmentOutcomes/{id}": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Updates appointment outcome metadata with documented orderWeight behavior.",
        "tests": "Yes",
    },
    "DELETE /appointmentOutcomes/{id}": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Input only",
        "notes": "Delete requires assignOutcomeId and returns structured deletion confirmation.",
        "tests": "Yes",
    },
    "GET /appointmentTypes": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Lists appointment types with pagination metadata and sort support.",
        "tests": "Yes",
    },
    "GET /appointmentTypes/{id}": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Single-appointment-type lookup.",
        "tests": "Yes",
    },
    "POST /appointmentTypes": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Creates an appointment type with optional orderWeight support.",
        "tests": "Yes",
    },
    "PUT /appointmentTypes/{id}": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Updates appointment type metadata with documented orderWeight behavior.",
        "tests": "Yes",
    },
    "DELETE /appointmentTypes/{id}": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Input only",
        "notes": "Delete requires assignTypeId and returns structured deletion confirmation.",
        "tests": "Yes",
    },
    "GET /groups": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Lists groups with documented type and sort filters plus pagination metadata.",
        "tests": "Yes",
    },
    "GET /groups/:id": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Single-group lookup.",
        "tests": "Yes",
    },
    "POST /groups": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Creates a group with distribution and first-to-claim defaults where needed.",
        "tests": "Yes",
    },
    "PUT /groups/:id": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Updates group metadata and member assignment defaults.",
        "tests": "Yes",
    },
    "DELETE /groups/:id": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Input only",
        "notes": "Delete returns structured deletion confirmation.",
        "tests": "Yes",
    },
    "GET /groups/roundRobin": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Lists groups and includes round-robin assignment details.",
        "tests": "Yes",
    },
    "GET /automations": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Lists Automations 2.0 workflows with documented filters and pagination metadata.",
        "tests": "Yes",
    },
    "GET /automations/{id}": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Single-automation lookup for registered-system automation workflows.",
        "tests": "Yes",
    },
    "GET /automationsPeople": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Lists automation-person pairings with person, automation, and status filters.",
        "tests": "Yes",
    },
    "GET /automationsPeople/{id}": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Single automation-person pairing lookup.",
        "tests": "Yes",
    },
    "POST /automationsPeople": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Triggers an Automation 2.0 workflow for a specific person.",
        "tests": "Yes",
    },
    "PUT /automationsPeople/{id}": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Pauses or resumes an automation-person pairing.",
        "tests": "Yes",
    },
    "GET /inboxApps/installedApps/{publishedInboxAppId}": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Lists installed inbox app installations for a published inbox app.",
        "tests": "Yes",
    },
    "POST /inboxApps/install": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Installs an inbox app for account-wide or user-scoped usage.",
        "tests": "Yes",
    },
    "DELETE /inboxApps/{inboxAppId}": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Input only",
        "notes": (
            "Deactivates an inbox app installation and returns structured deletion confirmation."
        ),
        "tests": "Yes",
    },
    "GET /inboxApps/{inboxAppId}/conversations/{extConversationId}/participants": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Lists inbox app conversation participants with synthetic pagination metadata.",
        "tests": "Yes",
    },
    "POST /inboxApps/{inboxAppId}/conversations/{extConversationId}/participants": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Adds a participant to an inbox app conversation.",
        "tests": "Yes",
    },
    "POST /inboxApps/{inboxAppId}/message": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": (
            "Adds a message to an inbox app conversation with typed sender and owner payloads."
        ),
        "tests": "Yes",
    },
    "POST /inboxApps/{inboxAppId}/note": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Adds a note to an inbox app conversation with typed user attribution.",
        "tests": "Yes",
    },
    (
        "DELETE /inboxApps/{inboxAppId}/conversations/"
        "{extConversationId}/participants/{participantId}"
    ): {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Input only",
        "notes": (
            "Removes an inbox app conversation participant and returns structured deletion "
            "confirmation."
        ),
        "tests": "Yes",
    },
    "PUT /inboxApps/:inboxAppId/message": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Updates inbox app message delivery metadata or external message IDs.",
        "tests": "Yes",
    },
    "PUT /inboxApps/{inboxAppId}/conversations/{extConversationId}": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Updates inbox app conversation subject, archive state, person, or assignment.",
        "tests": "Yes",
    },
    "GET /peopleRelationships": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Lists people relationships with synthetic pagination metadata.",
        "tests": "Yes",
    },
    "GET /peopleRelationships/:id": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Fetches a single people relationship by ID.",
        "tests": "Yes",
    },
    "POST /peopleRelationships": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Creates a people relationship for a person.",
        "tests": "Yes",
    },
    "PUT /peopleRelationships/:id": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Updates a people relationship and preserves overwrite semantics for arrays.",
        "tests": "Yes",
    },
    "DELETE /peopleRelationships/:id": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Input only",
        "notes": "Deletes a people relationship and returns structured deletion confirmation.",
        "tests": "Yes",
    },
    "DELETE /personAttachments/{id}": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Input only",
        "notes": "Deletes a person attachment and returns structured deletion confirmation.",
        "tests": "Yes",
    },
    "GET /personAttachments/{id}": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Fetches a registered-system person attachment by ID.",
        "tests": "Yes",
    },
    "PUT /personAttachments/{id}": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Updates a registered-system person attachment by ID.",
        "tests": "Yes",
    },
    "POST /personAttachments": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Creates a registered-system person attachment using an external URI.",
        "tests": "Yes",
    },
    "GET /people": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Supports next-token and offset pagination.",
        "tests": "Yes",
    },
    "POST /people": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Documented as non-canonical for lead ingestion; prefer POST /events.",
        "tests": "Yes",
    },
    "GET /people/:id": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Supports fields selection.",
        "tests": "Yes",
    },
    "PUT /people/:id": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Supports mergeTags query semantics.",
        "tests": "Yes",
    },
    "DELETE /people/:id": {
        "implementation": "Deferred",
        "mcp": "No",
        "models": "No",
        "notes": "Not part of the requested MCP tool surface.",
        "tests": "No",
    },
    "GET /events": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Supports next-token pagination.",
        "tests": "Yes",
    },
    "POST /events": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Canonical external lead and lead-activity ingestion path.",
        "tests": "Yes",
    },
    "GET /events/:id": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Single-event lookup.",
        "tests": "Yes",
    },
    "GET /users": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Collection query coverage included.",
        "tests": "Yes",
    },
    "GET /users/:id": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Single-user lookup.",
        "tests": "Yes",
    },
    "DELETE /users/:id": {
        "implementation": "Deferred",
        "mcp": "No",
        "models": "No",
        "notes": "Deferred until explicitly needed.",
        "tests": "No",
    },
    "GET /customFields": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Supports custom field name validation helpers.",
        "tests": "Yes",
    },
    "GET /deals": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Supports documented deal filters and pagination metadata.",
        "tests": "Yes",
    },
    "GET /deals/{id}": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Single-deal lookup with dynamic custom field support.",
        "tests": "Yes",
    },
    "POST /deals": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Creates a deal and supports dynamic deal custom field values.",
        "tests": "Yes",
    },
    "PUT /deals/{id}": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Updates a deal and preserves documented custom field semantics.",
        "tests": "Yes",
    },
    "DELETE /deals/{id}": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Input only",
        "notes": "Delete returns structured deletion confirmation.",
        "tests": "Yes",
    },
    "GET /dealCustomFields": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Lists deal custom fields for write-time field-name discovery.",
        "tests": "Yes",
    },
    "GET /calls": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Supports documented call filters and pagination metadata.",
        "tests": "Yes",
    },
    "GET /calls/:id": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Single-call lookup.",
        "tests": "Yes",
    },
    "GET /appointments": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Supports documented appointment filters and pagination metadata.",
        "tests": "Yes",
    },
    "GET /appointments/:id": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Single-appointment lookup.",
        "tests": "Yes",
    },
    "POST /appointments": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Creates an appointment with optional invitees and sendInvitation support.",
        "tests": "Yes",
    },
    "PUT /appointments/:id": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Updates an appointment and supports sendInvitation query semantics.",
        "tests": "Yes",
    },
    "DELETE /appointments/:id": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Input only",
        "notes": "Delete returns structured deletion confirmation.",
        "tests": "Yes",
    },
    "POST /calls": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Creates a call log entry for a related person.",
        "tests": "Yes",
    },
    "PUT /calls/:id": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Updates a call log entry.",
        "tests": "Yes",
    },
    "DELETE /dealAttachments/{id}": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Input only",
        "notes": "Deletes a deal attachment and returns structured deletion confirmation.",
        "tests": "Yes",
    },
    "GET /dealAttachments/{id}": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Fetches a registered-system deal attachment by ID.",
        "tests": "Yes",
    },
    "PUT /dealAttachments/{id}": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Updates a registered-system deal attachment by ID.",
        "tests": "Yes",
    },
    "POST /dealAttachments": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Creates a registered-system deal attachment using an external URI.",
        "tests": "Yes",
    },
    "GET /emCampaigns": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Lists email marketing campaigns with origin and originId filtering.",
        "tests": "Yes",
    },
    "POST /emCampaigns": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Creates an email marketing campaign with required origin identifiers.",
        "tests": "Yes",
    },
    "PUT /emCampaigns/:id": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Updates an email marketing campaign subject, name, or HTML body.",
        "tests": "Yes",
    },
    "GET /emEvents": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Lists email marketing events with documented filters and pagination metadata.",
        "tests": "Yes",
    },
    "POST /emEvents": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": (
            "Posts batched email marketing events and returns accepted IDs plus skipped recipients."
        ),
        "tests": "Yes",
    },
    "POST /customFields": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Creates a custom field for the authenticated account owner.",
        "tests": "Yes",
    },
    "GET /customFields/:id": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Fetches a single custom field by ID.",
        "tests": "Yes",
    },
    "PUT /customFields/:id": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Updates custom field metadata and dropdown-choice mappings by ID.",
        "tests": "Yes",
    },
    "DELETE /customFields/:id": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Input only",
        "notes": "Deletes a custom field and returns structured deletion confirmation.",
        "tests": "Yes",
    },
    "POST /notes": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Supports optional person-availability wait flow.",
        "tests": "Yes",
    },
    "GET /notes/:id": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Single-note lookup.",
        "tests": "Yes",
    },
    "PUT /notes/:id": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Single-note update.",
        "tests": "Yes",
    },
    "DELETE /notes/:id": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Input only",
        "notes": "Delete returns structured deletion confirmation.",
        "tests": "Yes",
    },
    "GET /webhooks": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Requires registered system headers.",
        "tests": "Yes",
    },
    "POST /webhooks": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Requires registered system headers and owner-level permissions.",
        "tests": "Yes",
    },
    "GET /webhooks/:id": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Single-webhook lookup.",
        "tests": "Yes",
    },
    "PUT /webhooks/:id": {
        "implementation": "Deferred",
        "mcp": "No",
        "models": "No",
        "notes": "Deferred until explicitly needed.",
        "tests": "No",
    },
    "DELETE /webhooks/:id": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Input only",
        "notes": "Delete endpoint exposed through MCP.",
        "tests": "Yes",
    },
    "GET /templates": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Lists email templates with pagination metadata.",
        "tests": "Yes",
    },
    "GET /templates/:id": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Single-template lookup with optional mergePersonId support.",
        "tests": "Yes",
    },
    "POST /templates": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Creates a new email template.",
        "tests": "Yes",
    },
    "POST /templates/merge": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Merges an email template with recipient-aware merge-field expansion.",
        "tests": "Yes",
    },
    "PUT /templates/:id": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Updates template name, subject, and body.",
        "tests": "Yes",
    },
    "DELETE /templates/:id": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Input only",
        "notes": "Delete returns structured deletion confirmation.",
        "tests": "Yes",
    },
    "GET /pipelines": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Lists pipelines with exact-name filtering and pagination metadata.",
        "tests": "Yes",
    },
    "GET /pipelines/{id}": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Single-pipeline lookup including stage definitions.",
        "tests": "Yes",
    },
    "POST /pipelines": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Creates a pipeline with optional ordered stages.",
        "tests": "Yes",
    },
    "PUT /pipelines/{id}": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Updates pipeline metadata and supports stage create-or-update semantics.",
        "tests": "Yes",
    },
    "DELETE /pipelines/:id": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Input only",
        "notes": "Delete returns structured deletion confirmation.",
        "tests": "Yes",
    },
    "GET /ponds": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Lists ponds with documented pagination metadata.",
        "tests": "Yes",
    },
    "GET /ponds/:id": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Single-pond lookup.",
        "tests": "Yes",
    },
    "POST /ponds": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Creates a pond with a lead agent and full member list.",
        "tests": "Yes",
    },
    "PUT /ponds/:id": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Updates pond metadata and expects complete member replacement semantics.",
        "tests": "Yes",
    },
    "DELETE /ponds/:id": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Input only",
        "notes": "Delete requires assignTo and returns structured deletion confirmation.",
        "tests": "Yes",
    },
    "GET /smartLists": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Lists smart lists with pagination metadata and documented fub2/all filters.",
        "tests": "Yes",
    },
    "GET /smartLists/:id": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Single-smart-list lookup.",
        "tests": "Yes",
    },
    "GET /stages": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Lists stages with pagination metadata and documented sort support.",
        "tests": "Yes",
    },
    "GET /stages/:id": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Single-stage lookup.",
        "tests": "Yes",
    },
    "POST /stages": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Creates a stage with optional orderWeight support.",
        "tests": "Yes",
    },
    "PUT /stages/:id": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Updates stage metadata with documented orderWeight behavior.",
        "tests": "Yes",
    },
    "DELETE /stages/:id": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Input only",
        "notes": "Delete requires assignStageId and returns structured deletion confirmation.",
        "tests": "Yes",
    },
    "GET /teams": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Lists teams with pagination metadata.",
        "tests": "Yes",
    },
    "GET /teams/:id": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Single-team lookup.",
        "tests": "Yes",
    },
    "POST /teams": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Creates a team with members and optional leader IDs.",
        "tests": "Yes",
    },
    "PUT /teams/:id": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": (
            "Updates team metadata and expects complete member and leader replacement semantics."
        ),
        "tests": "Yes",
    },
    "DELETE /teams/:id": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Input only",
        "notes": (
            "Delete optionally supports moveToTeamId and returns structured deletion confirmation."
        ),
        "tests": "Yes",
    },
    "GET /teamInboxes": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Lists team inboxes with pagination metadata.",
        "tests": "Yes",
    },
    "GET /textMessages": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Lists text messages for a person or phone number.",
        "tests": "Yes",
    },
    "GET /textMessages/{id}": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Single-text-message lookup.",
        "tests": "Yes",
    },
    "POST /textMessages": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Records an externally sent text message log entry.",
        "tests": "Yes",
    },
    "GET /textMessageTemplates": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Lists text message templates with pagination metadata.",
        "tests": "Yes",
    },
    "GET /textMessageTemplates/{id}": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Single text message template lookup.",
        "tests": "Yes",
    },
    "POST /textMessageTemplates": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Creates a new text message template.",
        "tests": "Yes",
    },
    "POST /textMessageTemplates/merge": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Merges a text message template with recipient-aware merge-field expansion.",
        "tests": "Yes",
    },
    "PUT /textMessageTemplates/:id": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Updates text message template content and sharing state.",
        "tests": "Yes",
    },
    "DELETE /textMessageTemplates/:id": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Input only",
        "notes": "Delete returns structured deletion confirmation.",
        "tests": "Yes",
    },
    "GET /tasks": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Supports documented task filters and pagination metadata.",
        "tests": "Yes",
    },
    "GET /tasks/:id": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Single-task lookup.",
        "tests": "Yes",
    },
    "POST /tasks": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Requires a related person and an assignee.",
        "tests": "Yes",
    },
    "PUT /tasks/:id": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Yes",
        "notes": "Supports task completion and due-date updates.",
        "tests": "Yes",
    },
    "DELETE /tasks/:id": {
        "implementation": "Implemented",
        "mcp": "Yes",
        "models": "Input only",
        "notes": "Delete returns structured deletion confirmation.",
        "tests": "Yes",
    },
}


def _load_manifest() -> dict[str, object]:
    """Load the generated endpoint manifest from disk.

    Returns:
        The decoded manifest payload.

    Raises:
        SystemExit: If the manifest is missing or has an unexpected top-level shape.
    """
    if not MANIFEST_PATH.exists():
        raise SystemExit(f"Manifest not found: {MANIFEST_PATH}")
    payload = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit("Manifest payload is invalid.")
    return {str(key): value for key, value in payload.items()}


def _normalize_endpoint_path(path: str) -> str:
    """Normalize endpoint paths so generated coverage keys stay stable.

    Args:
        path: The raw endpoint path extracted from documentation.

    Returns:
        A normalized endpoint path with exactly one leading slash and no
        duplicate interior slashes.
    """
    normalized = "/" + path.strip().lstrip("/")
    while "//" in normalized:
        normalized = normalized.replace("//", "/")
    return normalized


def _endpoint_key(page: dict[str, object]) -> str | None:
    """Build a normalized coverage key for a manifest page.

    Args:
        page: A manifest page entry.

    Returns:
        The normalized `<METHOD> <PATH>` key, or `None` when the page does not
        represent a documented endpoint.
    """
    method = page.get("http_method")
    path = page.get("endpoint_path")
    if not isinstance(method, str) or not isinstance(path, str):
        return None
    return f"{method.strip().upper()} {_normalize_endpoint_path(path)}"


def write_matrix(manifest: dict[str, object]) -> None:
    """Write the explicit coverage matrix."""
    pages = manifest.get("pages", [])
    if not isinstance(pages, list):
        raise SystemExit("Manifest pages payload is invalid.")
    endpoint_keys = sorted(
        {key for page in pages if isinstance(page, dict) for key in [_endpoint_key(page)] if key}
    )

    lines = [
        "# API Coverage Matrix",
        "",
        "Generated from the official Follow Up Boss doc-ingestion manifest and an explicit "
        "repository coverage declaration.",
        "",
        "| Endpoint | Implementation | Models | MCP | Tests | Notes |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for endpoint in endpoint_keys:
        status = COVERAGE_MAP.get(
            endpoint,
            {
                "implementation": "Deferred",
                "mcp": "No",
                "models": "No",
                "notes": (
                    "Discovered during the official docs crawl and intentionally "
                    "deferred from the current repository scope."
                ),
                "tests": "No",
            },
        )
        lines.append(
            f"| `{endpoint}` | {status['implementation']} | {status['models']} | "
            f"{status['mcp']} | {status['tests']} | {status['notes']} |"
        )
    MATRIX_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    """Validate the manifest and regenerate the matrix."""
    manifest = _load_manifest()
    write_matrix(manifest)
    print(f"Wrote {MATRIX_PATH}")


if __name__ == "__main__":
    main()
