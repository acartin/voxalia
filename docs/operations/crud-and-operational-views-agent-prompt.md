# Prompt For Building Voxalia CRUDs And Operational Views

You are working in `/srv/voxalia`.

Before changing code, read in this order:

1. `.agent/AI_CONTEXT.md`
2. `.agent/RULES.md`
3. `.agent/EXECUTION_MAP.md`
4. `.agent/WEB_UI_STANDARDS.md` if touching `services/web/voxalia`
5. Relevant ADRs in `docs/adr`

Non-negotiable rules:

- `services/web/voxalia` is Next.js and must never connect directly to PostgreSQL, Asterisk, FreePBX, Chatwoot or external providers.
- The web app consumes `services/web-api`.
- Backend endpoints must resolve tenant, role and permissions server-side.
- Every operational query must be tenant-scoped.
- Do not build CRUDs for FreePBX/Asterisk internal configuration.
- Do not build CRUDs for Chatwoot internal objects.
- Do not use soft delete. If the user confirms delete, delete the row. If the product needs disabled records, use `status` as lifecycle state, not as fake deletion.
- Keep UI text in English.
- Use the existing CRUD pattern from `Users`.

Existing CRUD pattern:

- Web reusable CRUD shell: `services/web/voxalia/components/crud/crud-resource-page.tsx`
- Web grid: `services/web/voxalia/components/crud/crud-grid.tsx`
- Web CRUD types: `services/web/voxalia/components/crud/types.ts`
- Users example: `services/web/voxalia/components/crud/users-crud.tsx`
- Module switch: `services/web/voxalia/components/portal/module-view.tsx`
- API module endpoints: `services/web-api/app/main.py`
- Menu source: `services/web-api/app/menu.py`
- Web route resolver: `services/web/voxalia/lib/modules.ts`

For every CRUD:

- Add API list/create/update/delete endpoints in `services/web-api/app/main.py` or split into a local router if the file becomes too large.
- Use Pydantic request models.
- Use parameterized SQL only.
- Enforce permissions in API before querying.
- Return a `ModulePayload` for list screens.
- Add a web component under `services/web/voxalia/components/crud`.
- Register it in `ModuleView`.
- Add or reuse a Next route handler under `services/web/voxalia/app/api/...` for mutations.
- Use FK-backed dropdowns where listed below. Do not hardcode IDs in forms except default tenant key where already established.
- Delete actions should use real `DELETE` endpoints when implemented.

## Scope 1: Tenant Workspace CRUDs

These are normal business/configuration CRUDs under `Settings > Tenants`, inside the tenant workspace tabs.

Tables:

- `tenants`
- `tenant_product_subscriptions`
- `tenant_service_policies`
- `tenant_service_hours`
- `tenant_channels`
- `voice_numbers`
- `tenant_contacts`
- `tenant_contact_methods`
- `agent_profiles`
- `tenant_agent_assignments`
- `tenant_scripts`
- `reporting_recipients`

Menu and placement:

- Main menu item: `Settings > Tenants`
- List page: `/settings/tenants`
- Workspace page: `/settings/tenants/{tenant_key}`
- Tabs:
  - `Overview`: `tenants`
  - `Products`: `tenant_product_subscriptions`
  - `Service Policy`: `tenant_service_policies`, `tenant_service_hours`
  - `Channels`: `tenant_channels`
  - `Numbers & Routing`: `voice_numbers`
  - `Contacts`: `tenant_contacts`, `tenant_contact_methods`
  - `Agents`: `agent_profiles`, `tenant_agent_assignments`
  - `Scripts`: `tenant_scripts`
  - `Reporting`: `reporting_recipients`
  - `Audit`: audit view filtered by tenant

Dropdown/FK sources:

- `tenant_product_subscriptions.tenant_id` -> `tenants`
- `tenant_service_policies.tenant_id` -> `tenants`
- `tenant_service_hours.service_policy_id` -> `tenant_service_policies`
- `tenant_channels.tenant_id` -> `tenants`
- `tenant_channels.service_policy_id` -> `tenant_service_policies`
- `voice_numbers.tenant_id` -> `tenants`
- `voice_numbers.channel_id` -> `tenant_channels`
- `tenant_contacts.tenant_id` -> `tenants`
- `tenant_contact_methods.contact_id` -> `tenant_contacts`
- `agent_profiles.user_id` -> `auth_users`
- `tenant_agent_assignments.agent_profile_id` -> `agent_profiles`
- `tenant_scripts.channel_id` -> `tenant_channels`
- `tenant_scripts.service_policy_id` -> `tenant_service_policies`
- `reporting_recipients.contact_id` -> `tenant_contacts`

## Scope 2: Security CRUDs

These are platform security/admin CRUDs.

Tables:

- `auth_users`
- `auth_roles`
- `auth_permissions`
- `auth_role_permissions`
- `auth_user_roles`
- `auth_user_tenants`

Menu and placement:

- `Settings > Users`: `auth_users`, `auth_user_roles`, `auth_user_tenants`
- `Settings > Roles`: `auth_roles`, `auth_permissions`, `auth_role_permissions`

Dropdown/FK sources:

- `auth_user_roles.user_id` -> `auth_users`
- `auth_user_roles.role_id` -> `auth_roles`
- `auth_user_tenants.user_id` -> `auth_users`
- `auth_user_tenants.tenant_id` -> `tenants`
- `auth_role_permissions.role_id` -> `auth_roles`
- `auth_role_permissions.permission_id` -> `auth_permissions`

## Scope 3: Conversation And Work CRUDs

These are Voxalia operational records. They are not a full CRM. They exist to support managed reception, follow-up and reporting.

CRUD/semi-CRUD tables:

- `conversation_contacts`
- `conversation_conversations`
- `conversation_participants`
- `conversation_notes`
- `conversation_outcomes`
- `conversation_opportunities`
- `workflow_tasks`

Append-only/detail tables:

- `conversation_interactions`
- `workflow_task_events`

Menu and placement:

- `Work > Conversations`: `conversation_conversations`, `conversation_interactions`, `conversation_participants`, `conversation_notes`, `conversation_outcomes`
- `Work > Contacts`: `conversation_contacts`
- `Work > Opportunities`: `conversation_opportunities`
- `Work > Follow-ups`: `workflow_tasks`, `workflow_task_events`

Dropdown/FK sources:

- `conversation_contacts.tenant_id` -> `tenants`
- `conversation_conversations.primary_contact_id` -> `conversation_contacts`
- `conversation_conversations.source_channel_id` -> `tenant_channels`
- `conversation_conversations.assigned_user_id` -> `auth_users`
- `conversation_participants.conversation_id` -> `conversation_conversations`
- `conversation_participants.contact_id` -> `conversation_contacts`
- `conversation_participants.user_id` -> `auth_users`
- `conversation_participants.tenant_contact_id` -> `tenant_contacts`
- `conversation_interactions.conversation_id` -> `conversation_conversations`
- `conversation_interactions.channel_id` -> `tenant_channels`
- `conversation_interactions.primary_contact_id` -> `conversation_contacts`
- `conversation_notes.conversation_id` -> `conversation_conversations`
- `conversation_notes.interaction_id` -> `conversation_interactions`
- `conversation_notes.author_user_id` -> `auth_users`
- `conversation_outcomes.conversation_id` -> `conversation_conversations`
- `conversation_outcomes.interaction_id` -> `conversation_interactions`
- `conversation_opportunities.conversation_id` -> `conversation_conversations`
- `conversation_opportunities.contact_id` -> `conversation_contacts`
- `conversation_opportunities.owner_user_id` -> `auth_users`
- `workflow_tasks.conversation_id` -> `conversation_conversations`
- `workflow_tasks.interaction_id` -> `conversation_interactions`
- `workflow_tasks.opportunity_id` -> `conversation_opportunities`
- `workflow_tasks.assigned_user_id` -> `auth_users`
- `workflow_tasks.assigned_tenant_contact_id` -> `tenant_contacts`

## Scope 4: Voice Operational Views

These are Voxalia-owned call records and recording records. They are not FreePBX configuration CRUDs.

Operational view/detail tables:

- `voice_call_sessions`
- `voice_call_legs`
- `voice_call_events`
- `voice_recordings`
- `voice_recording_files`
- `voice_recording_access_log`

Menu and placement:

- `Voice > Active calls`: filtered live view of `voice_call_sessions`
- `Voice > Recordings`: `voice_recordings`, `voice_recording_files`, `voice_recording_access_log`
- Call detail page: timeline from `voice_call_sessions`, `voice_call_legs`, `voice_call_events`, transcript/summary/observations when available

Allowed actions:

- view timeline
- view recording metadata
- play/download recording only through permissioned API
- retry AI processing
- mark recording exception
- create note/task/opportunity from call detail

Do not implement create/edit CRUD for calls. Calls are created by Asterisk adapter/runtime events.

Dropdown/FK sources:

- `voice_call_sessions.conversation_id` -> `conversation_conversations`
- `voice_call_sessions.interaction_id` -> `conversation_interactions`
- `voice_call_sessions.channel_id` -> `tenant_channels`
- `voice_call_sessions.number_id` -> `voice_numbers`
- `voice_call_legs.call_session_id` -> `voice_call_sessions`
- `voice_call_events.call_session_id` -> `voice_call_sessions`
- `voice_call_events.call_leg_id` -> `voice_call_legs`
- `voice_recordings.call_session_id` -> `voice_call_sessions`
- `voice_recordings.interaction_id` -> `conversation_interactions`
- `voice_recording_files.recording_id` -> `voice_recordings`
- `voice_recording_access_log.recording_id` -> `voice_recordings`
- `voice_recording_access_log.user_id` -> `auth_users`

## Scope 5: Asterisk/FreePBX Adapter Views

Do not build CRUDs for FreePBX internals.

Never create user CRUDs for:

- SIP trunks
- PJSIP extensions
- SIP devices
- FreePBX queues
- FreePBX queue members
- dialplan internals
- SIP credentials

Voxalia may expose read-only/admin diagnostic screens using:

- `asterisk_instance_status`
- `asterisk_provider_mappings`
- `channel_provider_mappings`
- `integration_webhook_events`

Menu and placement:

- `Voice > Queues`: operational status view only, using adapter data/mappings
- `Voice > Numbers & routing`: Voxalia-owned `voice_numbers` and channel/routing policy, not FreePBX dialplan
- `Settings > Integrations`: Asterisk connection and mapping diagnostics

Purpose:

- Show health of the connected Asterisk/FreePBX instance.
- Show which provider DID/queue/endpoint maps to which Voxalia tenant/channel/number.
- Show ingestion failures.
- Keep migration to another Asterisk instance possible by changing mappings/adapters, not business data.

## Scope 6: Chatwoot/External Provider Integration

Do not duplicate Chatwoot as a CRM or chat database.

Config/admin tables:

- `integration_connections`
- `channel_provider_accounts`
- `channel_provider_mappings`

Read-only troubleshooting/log tables:

- `integration_external_refs`
- `integration_sync_jobs`
- `integration_webhook_events`

Menu and placement:

- `Channels > Inboxes`: tenant channels and provider mappings
- `Channels > Chatwoot`: Chatwoot account/inbox mapping and webhook status
- `Settings > Integrations`: provider connections and sync jobs

Dropdown/FK sources:

- `integration_connections.tenant_id` -> `tenants` when tenant-scoped; null means system-wide provider
- `channel_provider_accounts.integration_connection_id` -> `integration_connections`
- `channel_provider_mappings.channel_id` -> `tenant_channels`
- `channel_provider_mappings.provider_account_id` -> `channel_provider_accounts`
- `integration_external_refs.integration_connection_id` -> `integration_connections`
- `integration_sync_jobs.integration_connection_id` -> `integration_connections`
- `integration_webhook_events.integration_connection_id` -> `integration_connections`

## Scope 7: AI, Call Intelligence And Search Views

These are processing/results/review screens, not normal CRUDs.

Tables:

- `ai_prompt_versions`
- `ai_processing_jobs`
- `ai_model_runs`
- `ai_transcriptions`
- `ai_transcript_segments`
- `ai_call_summaries`
- `ai_call_observations`
- `ai_extractions`
- `ai_quality_reviews`
- `search_documents`
- `search_document_chunks`
- `search_embeddings`
- `search_index_jobs`

Menu and placement:

- `Intelligence > Transcriptions`: jobs, transcriptions, segments
- `Intelligence > Quality`: summaries, observations, extractions, quality reviews
- `Intelligence > Reports`: report outputs later
- Call detail page: transcript, summary and observations for the call

Allowed actions:

- retry failed job
- cancel queued/running job if supported
- approve/reject AI summary
- accept/reject extraction
- reindex document/call/recording

Do not allow arbitrary editing of model output without keeping review/audit metadata.

Dropdown/FK sources:

- `ai_processing_jobs.call_session_id` -> `voice_call_sessions`
- `ai_processing_jobs.recording_id` -> `voice_recordings`
- `ai_processing_jobs.interaction_id` -> `conversation_interactions`
- `ai_model_runs.processing_job_id` -> `ai_processing_jobs`
- `ai_model_runs.prompt_version_id` -> `ai_prompt_versions`
- `ai_transcriptions.processing_job_id` -> `ai_processing_jobs`
- `ai_transcriptions.recording_id` -> `voice_recordings`
- `ai_transcriptions.model_run_id` -> `ai_model_runs`
- `ai_transcript_segments.transcription_id` -> `ai_transcriptions`
- `ai_call_summaries.call_session_id` -> `voice_call_sessions`
- `ai_call_summaries.transcription_id` -> `ai_transcriptions`
- `ai_call_summaries.model_run_id` -> `ai_model_runs`
- `ai_call_observations.call_session_id` -> `voice_call_sessions`
- `ai_call_observations.transcription_id` -> `ai_transcriptions`
- `ai_extractions.processing_job_id` -> `ai_processing_jobs`
- `ai_quality_reviews.call_session_id` -> `voice_call_sessions`
- `search_document_chunks.document_id` -> `search_documents`
- `search_embeddings.chunk_id` -> `search_document_chunks`

## Scope 8: Audit Views

These are append-only audit/review views, not normal CRUDs.

Tables:

- `audit_events`
- `audit_subject_links`
- `call_audit_findings`
- `call_audit_scores`
- `call_audit_reviews`

Menu and placement:

- `Settings > Audit log`: `audit_events`, `audit_subject_links`
- `Intelligence > Quality`: `call_audit_findings`, `call_audit_scores`, `call_audit_reviews`
- Tenant workspace `Audit` tab: tenant-filtered audit events
- Call detail page: call-specific audit findings/scores/reviews

Allowed actions:

- review finding
- approve/reject review
- dismiss false positive
- create follow-up task

No delete UI for audit records unless explicitly requested by the product owner.

Dropdown/FK sources:

- `audit_events.tenant_id` -> `tenants`
- `audit_events.actor_user_id` -> `auth_users`
- `audit_subject_links.audit_event_id` -> `audit_events`
- `call_audit_findings.call_session_id` -> `voice_call_sessions`
- `call_audit_scores.call_session_id` -> `voice_call_sessions`
- `call_audit_reviews.call_session_id` -> `voice_call_sessions`
- `call_audit_reviews.reviewer_user_id` -> `auth_users`

## Validation Required

After implementation:

- For `services/web-api`: run Python compile or container build according to `.agent/EXECUTION_MAP.md`.
- For `services/web/voxalia`: run `docker build -t voxalia-web:dev services/web/voxalia`.
- If service code changed and the user wants it visible locally, run `docker compose up -d --build voxalia-web-api voxalia-web`.
- Test with a real login session. Do not print secrets, tokens or full `.env`.
