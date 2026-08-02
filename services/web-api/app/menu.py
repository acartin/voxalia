MENU_CATALOG = [
    {
        "id": "console",
        "label": "Console",
        "items": [
            {
                "id": "overview",
                "label": "Overview",
                "href": "/console/overview",
                "description": "Operational health, active service state and daily workload.",
                "required_permission": "reports:read",
            },
            {
                "id": "live-desk",
                "label": "Live desk",
                "href": "/console/live-desk",
                "description": "Agent workspace for active calls, notes, outcomes and next actions.",
                "required_permission": "voice:operate",
            },
        ],
    },
    {
        "id": "voice",
        "label": "Voice",
        "items": [
            {"id": "webrtc-phone", "label": "Web phone", "href": "/voice/webrtc-phone", "description": "Browser softphone for live call handling through Asterisk WebRTC.", "required_permission": "voice:operate"},
            {"id": "active-calls", "label": "Active calls", "href": "/voice/active-calls", "description": "Live calls, ringing sessions, holds, transfers and conferences.", "required_permission": "voice:operate"},
            {"id": "queues", "label": "Queues", "href": "/voice/queues", "description": "Agent queues, availability, routing status and service levels.", "required_permission": "voice:configure"},
            {"id": "numbers", "label": "Numbers & routing", "href": "/voice/numbers", "description": "DIDs, toll-free numbers, trunks, inbound routes and recording policies.", "required_permission": "voice:configure"},
            {"id": "recordings", "label": "Recordings", "href": "/voice/recordings", "description": "Tenant-scoped call recordings, retention status and exceptions.", "required_permission": "voice:recordings:read"},
            {"id": "scripts", "label": "Scripts", "href": "/voice/scripts", "description": "Call scripts, intake flows, disclosure text and escalation guidance.", "required_permission": "voice:configure"},
        ],
    },
    {
        "id": "work",
        "label": "Work",
        "items": [
            {"id": "conversations", "label": "Conversations", "href": "/work/conversations", "description": "Customer service history across voice and future channels.", "required_permission": "conversations:read"},
            {"id": "contacts", "label": "Contacts", "href": "/crm/contacts", "description": "Guests, callers, leads, travel contacts and partner-side contacts.", "required_permission": "conversations:read"},
            {"id": "opportunities", "label": "Opportunities", "href": "/crm/opportunities", "description": "Booking, reservation, upsell and group inquiry opportunities.", "required_permission": "conversations:manage"},
            {"id": "follow-ups", "label": "Follow-ups", "href": "/crm/follow-ups", "description": "Callbacks, tasks, partner handoffs and unresolved requests.", "required_permission": "conversations:manage"},
        ],
    },
    {
        "id": "channels",
        "label": "Channels",
        "items": [
            {"id": "inboxes", "label": "Inboxes", "href": "/channels/inboxes", "description": "Configured voice, chat, email and messaging entrypoints by tenant.", "required_permission": "channels:configure"},
            {"id": "chatwoot", "label": "Chatwoot", "href": "/channels/chatwoot", "description": "Chatwoot inbox mappings and handoff configuration.", "required_permission": "channels:configure"},
            {"id": "webchat", "label": "Webchat", "href": "/channels/webchat", "description": "Voxalia webchat widgets, routing and capture rules.", "required_permission": "channels:configure"},
            {"id": "whatsapp", "label": "WhatsApp", "href": "/channels/whatsapp", "description": "Meta/WhatsApp channel bindings and operating state.", "required_permission": "channels:configure"},
        ],
    },
    {
        "id": "intelligence",
        "label": "Intelligence",
        "items": [
            {"id": "transcriptions", "label": "Transcriptions", "href": "/intelligence/transcriptions", "description": "Async transcription jobs and processing status.", "required_permission": "ai:jobs:manage"},
            {"id": "quality", "label": "Quality", "href": "/intelligence/quality", "description": "QA review, coaching signals and audit workflows.", "required_permission": "audit:read"},
            {"id": "reports", "label": "Reports", "href": "/intelligence/reports", "description": "Tenant reports, delivery rules and management summaries.", "required_permission": "reports:read"},
        ],
    },
    {
        "id": "settings",
        "label": "Settings",
        "items": [
            {"id": "tenants", "label": "Tenants", "href": "/settings/tenants", "description": "Partners, tenant policies, service hours and escalation contacts.", "required_permission": "tenants:manage"},
            {"id": "users", "label": "Users", "href": "/settings/users", "description": "Users, tenant memberships and account lifecycle.", "required_permission": "auth:users:manage"},
            {"id": "agents", "label": "Agents", "href": "/settings/agents", "description": "Voxalia operator profiles, tenant assignments, skills and availability.", "required_permission": "auth:users:manage"},
            {"id": "roles", "label": "Roles", "href": "/settings/roles", "description": "Roles, permission grants and authorization policy.", "required_permission": "auth:roles:manage"},
            {"id": "asterisk-infrastructure", "label": "Asterisk Infrastructure", "href": "/settings/asterisk-infrastructure", "description": "Global Asterisk connectivity placeholders for trunks, carriers and instances.", "required_permission": "voice:configure"},
            {"id": "asterisk", "label": "Asterisk Tenant Profiles", "href": "/settings/asterisk", "description": "Tenant voice profiles, assigned numbers, contexts, routing, recording and provisioning.", "required_permission": "voice:configure"},
            {"id": "integrations", "label": "Integrations", "href": "/settings/integrations", "description": "PMS, CRM, payment, email and provider connector settings.", "required_permission": "integrations:configure"},
            {"id": "audit", "label": "Audit log", "href": "/settings/audit", "description": "Security and operational audit trail.", "required_permission": "audit:read"},
        ],
    },
]


def effective_menu(permissions: frozenset[str]) -> list[dict[str, object]]:
    sections = []
    for section in MENU_CATALOG:
        items = [
            item
            for item in section["items"]
            if not item.get("required_permission") or item["required_permission"] in permissions
        ]
        if items:
            sections.append({**section, "items": items})
    return sections


def item_for_path(path: str) -> dict[str, str] | None:
    for section in MENU_CATALOG:
        for item in section["items"]:
            if item["href"] == path:
                return item
    return None
