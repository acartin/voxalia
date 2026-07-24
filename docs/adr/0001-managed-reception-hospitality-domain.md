# ADR 0001: Managed Reception For Hospitality And Tourism

- Status: Proposed
- Date: 2026-07-23
- Scope: first Voxalia product, first vertical, call center operations, domain model

## Context

Voxalia starts as a managed human reception service, not as a chatbot-first product. The first commercial vertical is hospitality and tourism: hotels, boutique hotels, tour operators, transportation providers, activity operators, and similar partners that need reliable bilingual or trilingual customer attention for callers in the United States and Canada.

The first channel is a 1-800 voice service. A guest or prospective guest calls a Voxalia-managed toll-free number. A Voxalia human agent answers, identifies the partner and caller context, handles the request, and can call, transfer, conference, or escalate to the partner when needed.

The same platform must later support Chatwoot, Voxalia-owned webchat, Meta/WhatsApp, email, PMS, CRM, payments, call intelligence, and AI agent assistance. Therefore the first design must not hardcode "hotel-only" behavior into the core.

## Decision

Voxalia will model the first product as a multi-tenant managed reception platform with a channel-based service configuration.

The first vertical will be `hospitality`, but the shared core will use generic concepts. In product and UI language, the organization that hires Voxalia is a Partner or Socio. In code and data, that same organization is represented by a single `Tenant` entity. We will not create a separate `Partner` entity unless a future operational need proves that one tenant can contain multiple distinct partners.

- `Tenant`: the paying partner/account and the security boundary, such as a hotel or tourism provider. UI may label it as Partner or Socio.
- `Agent`: a Voxalia operator who serves one or more tenants/partners.
- `Channel`: a configured way customers reach Voxalia for a tenant, such as toll-free voice, local voice, WhatsApp, webchat, Chatwoot inbox, email, or future channels.
- `Conversation`: the durable customer service thread across one or more interactions.
- `Interaction`: one touchpoint inside a conversation, such as a call, chat message, email, or handoff.
- `Call`: voice-specific interaction details.
- `Contact`: the guest, lead, caller, traveler, group organizer, or business contact.
- `Opportunity`: potential revenue or booking-related intent.
- `Task`: follow-up work for Voxalia or the tenant/partner.
- `EscalationContact`: partner-side person or department that can receive transfers, conferences, callbacks, or notifications.
- `ServicePolicy`: tenant/vertical rules for hours, languages, routing, escalation, data capture, and outcomes.
- `Script`: operational guidance shown to the agent for a product, vertical, tenant, channel, and intent.

The initial user-facing service is `managed-reception` for the `hospitality` vertical.

## First Operational Flow: 1-800 Voice

1. Caller calls a Voxalia-managed 1-800 number.
2. Asterisk receives the call through the SIP trunk.
3. The Asterisk channel adapter maps DID, inbound route, queue, or metadata to a `tenant_id` and `channel_id`.
4. The call is offered to a Voxalia agent.
5. Voxalia Operator Console shows:
   - tenant identity, displayed as partner/socio identity;
   - channel;
   - caller ID;
   - language expectation if known;
   - service hours and current local time for the partner;
   - active script;
   - escalation contacts;
   - recent conversations or matching contacts;
   - required capture fields;
   - call controls and outcome controls.
6. The agent handles the call.
7. If needed, the agent can:
   - click-to-call partner;
   - put caller on hold;
   - consult partner privately;
   - conference caller and partner;
   - transfer to partner or department;
   - schedule callback;
   - create task;
   - create opportunity;
   - mark emergency/escalation;
   - take message.
8. At call end, Voxalia stores call metadata, notes, outcome, tasks, opportunities, and the mandatory recording reference.
9. Partner reporting and future client portal views consume the normalized records, filtered by `tenant_id`.

## Mandatory Call Recording Policy

All Voxalia-managed voice calls must be recorded. Recording is not optional for the managed reception product.

Recordings are first-class operational evidence and will be used for:

- dispute resolution and service backup;
- partner-facing call history when policy allows;
- agent coaching and quality assurance;
- operational audits;
- post-call transcription;
- AI-generated summaries;
- structured extraction of tasks, opportunities, intents, and follow-up items;
- future call intelligence workflows.

The platform must treat recordings as sensitive tenant-scoped assets:

- every recording belongs to a `tenant_id`;
- every recording must be linked to a call/interaction and correlation id;
- recording storage must be private, not public;
- access must be permissioned and audited;
- retention policy must be explicit;
- deletion or legal hold must be supported by policy;
- AI processing must use recorded assets through audited backend jobs, not direct frontend access;
- transcript, summary, and extraction records must preserve source recording references and model/prompt metadata.

If recording fails for a call, the system must mark the call with a recording failure state and raise an operational alert. A missing recording is an exception, not an acceptable normal state.

Consent and disclosure language must be configurable by tenant/channel/jurisdiction and should be reviewed before production use. For the first 1-800 service, the call flow should assume an upfront recording notice before the agent handles the conversation.

## Tenant Model

A tenant represents the partner/socio that hires Voxalia. One table/entity is enough for the first release. The minimum tenant record for managed reception should include:

- legal/display name;
- status;
- vertical, initially `hospitality`;
- timezone;
- service languages;
- service hours;
- after-hours behavior;
- primary phone numbers;
- emergency contacts;
- reservation/sales contacts;
- operations contacts;
- billing/admin contacts;
- escalation rules;
- transfer rules;
- hold/conference preferences;
- callback windows;
- allowed channels;
- products subscribed;
- recording disclosure and retention policy;
- reporting recipients;
- notes visible to agents.

For hospitality and tourism, additional vertical configuration belongs under `verticals/hospitality` or tenant policy data, not in a separate partner profile table and not in shared core conditionals:

- room/reservation vocabulary;
- check-in/check-out rules;
- booking inquiry fields;
- group/event inquiry fields;
- airport transfer/tour pickup fields;
- cancellation and change-request scripts;
- guest complaint workflows;
- emergency handling;
- upsell or opportunity qualification rules.

## Channel Model

Every inbound or outbound customer entrypoint is a `Channel`.

Initial channel types:

- `voice_toll_free`: 1-800 USA/Canada service.
- `voice_local`: local DID or direct number.
- `chatwoot_inbox`: Chatwoot-managed inbox.
- `voxalia_webchat`: Voxalia-owned webchat.
- `meta_whatsapp`: WhatsApp or Meta messaging.
- `email`: shared inbox or routed email.

A channel should have:

- `channel_id`;
- `tenant_id`;
- `type`;
- `display_name`;
- `provider`;
- provider-specific identifiers kept outside shared domain where possible;
- inbound routing keys, such as DID, queue, inbox ID, widget ID, or account ID;
- active/inactive status;
- language defaults;
- service policy reference;
- reporting category;
- data retention policy.

The core should not know that a Chatwoot inbox ID, Asterisk DID, or Meta phone number is "the source of truth." Adapters translate those provider details into Voxalia channel and interaction events.

## Agent Model

Agents are Voxalia staff, not partner users.

The minimum agent model should include:

- user/account link;
- display name;
- languages;
- skills;
- assigned tenants or queues;
- role/permissions;
- availability status;
- telephony identity or provisioned web phone session;
- supervisor relationship if applicable;
- audit trail of state changes.

Agent status should support at least:

- offline;
- available;
- ringing;
- on_call;
- after_call_work;
- break;
- training;
- unavailable.

The system must distinguish partner users from Voxalia agents. A hotel employee who receives transfers is not automatically a Voxalia agent.

## Operator Console Requirements

The Operator Console is the primary workplace for Voxalia agents.

Initial call handling tools:

- answer incoming call;
- outbound click-to-call;
- hang up;
- mute/unmute;
- hold/resume;
- DTMF keypad;
- transfer to partner contact;
- attended transfer;
- blind transfer;
- conference caller with partner;
- private consult with partner before conference or transfer;
- see recording status;
- mark outcome;
- add notes;
- create/update contact;
- create opportunity;
- create task/callback;
- see active script;
- see partner service policy;
- see recent history;
- flag emergency or escalation.

The console should show call state clearly:

- disconnected;
- registering;
- ready;
- incoming;
- ringing;
- in_call;
- on_hold;
- consulting;
- conferencing;
- transferring;
- after_call_work;
- failed.

The web UI must not talk directly to Asterisk. It uses Voxalia API/WebSocket/SSE contracts. A voice runtime or Asterisk adapter owns provider communication.

## Call Control Boundary

Call control will be implemented behind Voxalia-owned contracts.

Preferred conceptual boundary:

```text
Operator Console
  -> Voxalia API / realtime gateway
  -> Voice Runtime
  -> Asterisk Adapter
  -> Asterisk / FreePBX / SIP trunk
```

The web app may later host a WebRTC softphone, but:

- SIP credentials must be short-lived or provisioned safely;
- permanent SIP secrets must not live in localStorage;
- HTTPS and WSS are required;
- media should flow browser <-> Asterisk/media infrastructure, not through Next.js;
- STUN/TURN must be planned for off-network agents;
- call events must still be normalized into Voxalia events.

## Events

Voice events should be normalized before reaching the core.

Initial event names:

```text
voice.call.offered
voice.call.answered
voice.call.bridged
voice.call.held
voice.call.resumed
voice.call.consult_started
voice.call.conference_started
voice.call.transfer_started
voice.call.transfer_completed
voice.call.completed
voice.recording.started
voice.recording.failed
voice.recording.available
conversation.created
interaction.created
task.created
opportunity.created
escalation.requested
agent.status_changed
```

Each event should include:

- event id;
- event type;
- event version;
- tenant id;
- channel id where applicable;
- conversation id where known;
- interaction id where known;
- correlation id;
- source adapter;
- occurred timestamp;
- provider references in a constrained `provider_refs` object, not as top-level domain identifiers.

## Reporting For Partners

The first useful partner report is operational, not analytics-heavy.

Minimum report content:

- total calls;
- answered calls;
- missed/abandoned calls;
- average wait time;
- average handle time;
- top outcomes;
- opportunities created;
- callbacks/tasks created;
- transfers to partner;
- emergency/escalation count;
- language mix;
- after-hours volume;
- notes or summaries when authorized;
- recording links only when policy allows;
- recording coverage and recording failures.

Every report must be scoped by `tenant_id`.

## Hospitality/Tourism Intents

Initial intent taxonomy for the vertical:

- reservation inquiry;
- existing reservation change;
- cancellation request;
- room availability;
- rate/package inquiry;
- group/event inquiry;
- airport transfer or transportation;
- tour/activity inquiry;
- restaurant/spa/amenity inquiry;
- guest complaint;
- lost and found;
- emergency;
- partner/vendor call;
- wrong number/spam;
- general information.

This taxonomy belongs to vertical configuration and can evolve without changing shared call handling primitives.

## Future PMS And CRM Integrations

PMS means Property Management System. For hospitality and tourism partners, Voxalia should be designed so future connectors can interact with PMS and CRM systems through explicit contracts.

Future PMS/CRM capabilities may include:

- checking room, package, tour, transfer, or activity availability;
- reading existing reservation status;
- creating reservation requests;
- executing confirmed reservations when policy and provider support allow it;
- updating guest/contact information;
- creating or updating CRM leads and opportunities;
- logging call notes and follow-up tasks into the partner system;
- triggering payment or deposit workflows through approved connectors.

These integrations are not required for the first managed reception release. The first release may capture the request manually and notify the partner. When PMS/CRM actions are added, they must be executed server-side through `connectors`, with tenant-scoped credentials, audit logs, explicit permission checks, and safe failure handling. The Operator Console should show whether data came from Voxalia records, PMS, CRM, or manual partner instructions.

## Out Of Scope For First Release

The first release does not require:

- fully autonomous AI agents;
- PMS/CRM availability checks, write-back, or reservation execution;
- payments;
- complex workforce management;
- predictive dialing;
- outbound campaigns;
- full omnichannel automation;
- advanced client portal;
- multi-region contact center failover;
- complete QA scorecards.

Those capabilities should remain possible, but they should not block the first managed reception release.

## Consequences

Positive:

- The first product is concrete and operationally useful.
- Voice, chat, and future channels share one conversation model.
- Hospitality-specific behavior is isolated in vertical policy/configuration.
- Call control remains secure and observable.
- The platform can grow beyond hotels without rewriting the core.

Tradeoffs:

- More upfront domain modeling than a simple softphone screen.
- Requires a Voxalia API/realtime boundary before the web can become fully operational.
- Requires disciplined event normalization from Asterisk and Chatwoot.
- WebRTC can be added, but production reliability requires TURN, observability, device handling, and strong credential boundaries.

## Open Questions

- Are toll-free numbers shared across many partners, dedicated per partner, or both?
- Will Voxalia agents answer from a browser softphone first, or from a SIP desktop/mobile client while the web console matures?
- Do partners require warm transfer only, or can blind transfer be allowed by policy?
- What recording consent language is required for USA/Canada callers and Costa Rica operations?
- Which languages are mandatory for launch: English, Spanish, French?
- What is the minimum after-hours behavior per partner?
- Should Chatwoot be used as a temporary agent workspace for chats only, or should Voxalia own the unified inbox from the beginning?
- Which PMS or CRM integration matters first for hospitality: Cloudbeds, generic email workflow, HubSpot/Zoho, or manual reporting?
