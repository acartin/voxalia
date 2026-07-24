export const moduleEndpointByPath: Record<string, string> = {
  "/console/overview": "/console/overview",
  "/console/live-desk": "/console/live-desk",
  "/voice/webrtc-phone": "/voice/webrtc-phone",
  "/voice/active-calls": "/voice/active-calls",
  "/voice/queues": "/voice/queues",
  "/voice/numbers": "/voice/numbers",
  "/voice/recordings": "/voice/recordings",
  "/voice/scripts": "/voice/scripts",
  "/work/conversations": "/work/conversations",
  "/crm/contacts": "/crm/contacts",
  "/crm/opportunities": "/crm/opportunities",
  "/crm/follow-ups": "/crm/follow-ups",
  "/channels/inboxes": "/channels/inboxes",
  "/channels/chatwoot": "/channels/chatwoot",
  "/channels/webchat": "/channels/webchat",
  "/channels/whatsapp": "/channels/whatsapp",
  "/intelligence/transcriptions": "/intelligence/transcriptions",
  "/intelligence/quality": "/intelligence/quality",
  "/intelligence/reports": "/intelligence/reports",
  "/settings/tenants": "/settings/tenants",
  "/settings/users": "/settings/users",
  "/settings/roles": "/settings/roles",
  "/settings/integrations": "/settings/integrations",
  "/settings/audit": "/settings/audit"
};

export const roleOptions = [
  { id: "system_admin", label: "System admin" },
  { id: "admin", label: "Admin" },
  { id: "supervisor", label: "Supervisor" },
  { id: "agent", label: "Agent" },
  { id: "client_admin", label: "Client admin" },
  { id: "client", label: "Client" }
] as const;
