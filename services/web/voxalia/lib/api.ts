import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { MenuItem, MenuPayload, MenuSection, ModulePayload, Role, WorkspacePayload } from "@/lib/types";

export const API_BASE_URL = process.env.VOXALIA_API_BASE_URL ?? "";
export const ASTERISK_API_BASE_URL = process.env.VOXALIA_ASTERISK_API_BASE_URL ?? "";
export const placeholderAuthEnabled = process.env.VOXALIA_PLACEHOLDER_AUTH !== "false" && !API_BASE_URL;
export const sessionCookieName = "voxalia_session";
export const placeholderRoleCookieName = "voxalia_placeholder_role";
export const defaultAuthenticatedPath = "/console/overview";

export const roleLabels: Record<Role, string> = {
  system_admin: "System admin",
  admin: "Admin",
  supervisor: "Supervisor",
  agent: "Agent",
  client_admin: "Client admin",
  client: "Client"
};

export const roleOrder: Role[] = ["system_admin", "admin", "supervisor", "agent", "client_admin", "client"];

export const permissionsByRole: Record<Role, string[]> = {
  system_admin: ["*"],
  admin: [
    "tenants:read",
    "voice:operate",
    "voice:configure",
    "voice:recordings:read",
    "conversations:read",
    "conversations:manage",
    "reports:read",
    "reports:manage",
    "channels:configure",
    "integrations:configure",
    "audit:read",
    "ai:jobs:manage"
  ],
  supervisor: [
    "tenants:read",
    "voice:operate",
    "voice:recordings:read",
    "conversations:read",
    "conversations:manage",
    "reports:read",
    "audit:read"
  ],
  agent: ["tenants:read", "voice:operate", "conversations:read", "conversations:manage"],
  client_admin: ["tenants:read", "voice:recordings:read", "conversations:read", "reports:read", "reports:manage"],
  client: ["tenants:read", "conversations:read", "reports:read"]
};

export const menuCatalog: MenuSection[] = [
  {
    id: "console",
    label: "Console",
    items: [
      {
        id: "overview",
        label: "Overview",
        href: "/console/overview",
        description: "Operational health, active service state and daily workload.",
        required_permission: "reports:read"
      },
      {
        id: "live-desk",
        label: "Live desk",
        href: "/console/live-desk",
        description: "Agent workspace for active calls, notes, outcomes and next actions.",
        required_permission: "voice:operate"
      }
    ]
  },
  {
    id: "voice",
    label: "Voice",
    items: [
      {
        id: "webrtc-phone",
        label: "Web phone",
        href: "/voice/webrtc-phone",
        description: "Browser softphone for live call handling through Asterisk WebRTC.",
        required_permission: "voice:operate"
      },
      {
        id: "active-calls",
        label: "Active calls",
        href: "/voice/active-calls",
        description: "Live calls, ringing sessions, holds, transfers and conferences.",
        required_permission: "voice:operate"
      },
      {
        id: "queues",
        label: "Queues",
        href: "/voice/queues",
        description: "Agent queues, availability, routing status and service levels.",
        required_permission: "voice:configure"
      },
      {
        id: "numbers",
        label: "Numbers",
        href: "/voice/numbers",
        description: "DIDs, toll-free numbers, trunks, inbound routes and recording policies.",
        required_permission: "voice:configure"
      },
      {
        id: "recordings",
        label: "Recordings",
        href: "/voice/recordings",
        description: "Tenant-scoped call recordings, retention status and exceptions.",
        required_permission: "voice:recordings:read"
      },
      {
        id: "scripts",
        label: "Scripts",
        href: "/voice/scripts",
        description: "Call scripts, intake flows, disclosure text and escalation guidance.",
        required_permission: "voice:configure"
      }
    ]
  },
  {
    id: "work",
    label: "Work",
    items: [
      {
        id: "conversations",
        label: "Conversations",
        href: "/work/conversations",
        description: "Customer service history across voice and future channels.",
        required_permission: "conversations:read"
      },
      {
        id: "contacts",
        label: "Contacts",
        href: "/crm/contacts",
        description: "Guests, callers, leads, travel contacts and partner-side contacts.",
        required_permission: "conversations:read"
      },
      {
        id: "opportunities",
        label: "Opportunities",
        href: "/crm/opportunities",
        description: "Booking, reservation, upsell and group inquiry opportunities.",
        required_permission: "conversations:manage"
      },
      {
        id: "follow-ups",
        label: "Follow-ups",
        href: "/crm/follow-ups",
        description: "Callbacks, tasks, partner handoffs and unresolved requests.",
        required_permission: "conversations:manage"
      }
    ]
  },
  {
    id: "channels",
    label: "Channels",
    items: [
      {
        id: "inboxes",
        label: "Inboxes",
        href: "/channels/inboxes",
        description: "Configured voice, chat, email and messaging entrypoints by tenant.",
        required_permission: "channels:configure"
      },
      {
        id: "chatwoot",
        label: "Chatwoot",
        href: "/channels/chatwoot",
        description: "Chatwoot inbox mappings and handoff configuration.",
        required_permission: "channels:configure"
      },
      {
        id: "webchat",
        label: "Webchat",
        href: "/channels/webchat",
        description: "Voxalia webchat widgets, routing and capture rules.",
        required_permission: "channels:configure"
      },
      {
        id: "whatsapp",
        label: "WhatsApp",
        href: "/channels/whatsapp",
        description: "Meta/WhatsApp channel bindings and operating state.",
        required_permission: "channels:configure"
      }
    ]
  },
  {
    id: "intelligence",
    label: "Intelligence",
    items: [
      {
        id: "transcriptions",
        label: "Transcriptions",
        href: "/intelligence/transcriptions",
        description: "Async transcription jobs and processing status.",
        required_permission: "ai:jobs:manage"
      },
      {
        id: "quality",
        label: "Quality",
        href: "/intelligence/quality",
        description: "QA review, coaching signals and audit workflows.",
        required_permission: "audit:read"
      },
      {
        id: "reports",
        label: "Reports",
        href: "/intelligence/reports",
        description: "Tenant reports, delivery rules and management summaries.",
        required_permission: "reports:read"
      }
    ]
  },
  {
    id: "settings",
    label: "Settings",
    items: [
      {
        id: "tenants",
        label: "Tenants",
        href: "/settings/tenants",
        description: "Partners, tenant policies, service hours and escalation contacts.",
        required_permission: "tenants:manage"
      },
      {
        id: "users",
        label: "Users",
        href: "/settings/users",
        description: "Users, tenant memberships, agents and account lifecycle.",
        required_permission: "auth:users:manage"
      },
      {
        id: "agents",
        label: "Agents",
        href: "/settings/agents",
        description: "Voxalia operator profiles, tenant assignments, skills and availability.",
        required_permission: "auth:users:manage"
      },
      {
        id: "roles",
        label: "Roles",
        href: "/settings/roles",
        description: "Roles, permission grants and authorization policy.",
        required_permission: "auth:roles:manage"
      },
      {
        id: "asterisk-infrastructure",
        label: "Asterisk Infrastructure",
        href: "/settings/asterisk-infrastructure",
        description: "Global Asterisk connectivity for trunks, carriers and runtime instances.",
        required_permission: "voice:configure"
      },
      {
        id: "asterisk",
        label: "Asterisk Tenant Profiles",
        href: "/settings/asterisk",
        description: "Tenant voice profiles, assigned numbers, contexts, routing, recording and provisioning.",
        required_permission: "voice:configure"
      },
      {
        id: "integrations",
        label: "Integrations",
        href: "/settings/integrations",
        description: "PMS, CRM, payment, email and provider connector settings.",
        required_permission: "integrations:configure"
      },
      {
        id: "audit",
        label: "Audit log",
        href: "/settings/audit",
        description: "Security and operational audit trail.",
        required_permission: "audit:read"
      }
    ]
  }
];

export function isRole(value: string): value is Role {
  return roleOrder.includes(value as Role);
}

export function canAccess(role: Role, item: MenuItem) {
  const permissions = permissionsByRole[role];
  return permissions.includes("*") || (item.required_permission ? permissions.includes(item.required_permission) : true);
}

export function menuForRole(role: Role): MenuSection[] {
  return menuCatalog
    .map((section) => ({
      ...section,
      items: section.items.filter((item) => canAccess(role, item))
    }))
    .filter((section) => section.items.length > 0);
}

export function roleCanAccessPath(role: Role, path: string) {
  return menuForRole(role).some((section) => section.items.some((item) => item.href === path));
}

export function defaultPathForRole(role: Role) {
  return menuForRole(role)[0]?.items[0]?.href ?? defaultAuthenticatedPath;
}

const defaultPlaceholderRole: Role = "system_admin";

function placeholderMenuForRole(role: Role): MenuPayload {
  return {
    user: {
      id: "placeholder-user",
      email: "admin@voxalia.local",
      role,
      role_label: roleLabels[role]
    },
    tenant: {
      client_id: "voxalia",
      name: "Voxalia",
      mode: "placeholder"
    },
    auth: {
      provider: placeholderAuthEnabled ? "placeholder" : "voxalia-api",
      status: placeholderAuthEnabled ? "placeholder" : "active",
      can_simulate_roles: placeholderAuthEnabled,
      is_role_simulated: role !== defaultPlaceholderRole
    },
    sections: menuForRole(role)
  };
}

export const placeholderMenu: MenuPayload = placeholderMenuForRole(defaultPlaceholderRole);

async function authHeaders(): Promise<HeadersInit> {
  const cookieStore = await cookies();
  const token = cookieStore.get(sessionCookieName)?.value;
  if (!token) redirect("/login");

  return {
    Authorization: `Bearer ${token}`
  };
}

async function getJson<T>(path: string): Promise<T> {
  if (!API_BASE_URL) {
    throw new Error("VOXALIA_API_BASE_URL is not configured");
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: await authHeaders(),
    cache: "no-store"
  });

  if (response.status === 401) redirect("/login");
  if (response.status === 403) redirect(defaultAuthenticatedPath);

  if (!response.ok) {
    throw new Error(`Voxalia API error ${response.status} on ${path}`);
  }

  return response.json() as Promise<T>;
}

export async function getMenu(): Promise<MenuPayload> {
  if (placeholderAuthEnabled) {
    const cookieStore = await cookies();
    if (!cookieStore.get(sessionCookieName)?.value) redirect("/login");
    const requestedRole = cookieStore.get(placeholderRoleCookieName)?.value ?? defaultPlaceholderRole;
    const role = isRole(requestedRole) ? requestedRole : defaultPlaceholderRole;
    return placeholderMenuForRole(role);
  }

  return getJson<MenuPayload>("/menu");
}

export async function getModule(path: string): Promise<ModulePayload> {
  if (placeholderAuthEnabled) {
    const menu = await getMenu();
    const item = menu.sections.flatMap((section) => section.items).find((entry) => entry.href === path);
    const isUsersModule = path === "/settings/users";

    return {
      module: {
        id: path.replace(/^\//, "").replace(/\//g, "."),
        title: item?.label ?? "Placeholder",
        description: item?.description ?? "Placeholder screen ready for the Voxalia API contract.",
        status: isUsersModule ? "Pattern" : "Placeholder"
      },
      context: {
        client_id: menu.tenant.client_id,
        role: menu.user.role
      },
      links: {},
      actions: isUsersModule
        ? [
            { id: "create", label: "Create user", enabled: true, permission: "auth:users:manage" },
            { id: "export", label: "Export", enabled: false, permission: "auth:users:export" }
          ]
        : [
            { id: "create", label: "Create", enabled: false },
            { id: "export", label: "Export", enabled: false }
          ],
      records: []
    };
  }

  return getJson<ModulePayload>(path);
}

export async function getWorkspace(path: string): Promise<WorkspacePayload> {
  if (placeholderAuthEnabled) {
    throw new Error("Workspace pages require VOXALIA_API_BASE_URL");
  }

  return getJson<WorkspacePayload>(path);
}

export async function getAsteriskModule(): Promise<ModulePayload> {
  if (!ASTERISK_API_BASE_URL) {
    throw new Error("VOXALIA_ASTERISK_API_BASE_URL is not configured");
  }

  const response = await fetch(`${ASTERISK_API_BASE_URL}/asterisk/tenants`, {
    cache: "no-store"
  });

  if (!response.ok) {
    throw new Error(`Voxalia Asterisk API error ${response.status}`);
  }

  return response.json() as Promise<ModulePayload>;
}

export async function getAsteriskTrunks(): Promise<ModulePayload> {
  if (!ASTERISK_API_BASE_URL) {
    throw new Error("VOXALIA_ASTERISK_API_BASE_URL is not configured");
  }

  const response = await fetch(`${ASTERISK_API_BASE_URL}/asterisk/infrastructure/trunks`, {
    cache: "no-store"
  });

  if (!response.ok) {
    throw new Error(`Voxalia Asterisk API error ${response.status}`);
  }

  return response.json() as Promise<ModulePayload>;
}

export async function getAsteriskCarriers(): Promise<ModulePayload> {
  if (!ASTERISK_API_BASE_URL) {
    throw new Error("VOXALIA_ASTERISK_API_BASE_URL is not configured");
  }

  const response = await fetch(`${ASTERISK_API_BASE_URL}/asterisk/infrastructure/carriers`, {
    cache: "no-store"
  });

  if (!response.ok) {
    throw new Error(`Voxalia Asterisk API error ${response.status}`);
  }

  return response.json() as Promise<ModulePayload>;
}

export async function getAsteriskInstances(): Promise<ModulePayload> {
  if (!ASTERISK_API_BASE_URL) {
    throw new Error("VOXALIA_ASTERISK_API_BASE_URL is not configured");
  }

  const response = await fetch(`${ASTERISK_API_BASE_URL}/asterisk/infrastructure/instances`, {
    cache: "no-store"
  });

  if (!response.ok) {
    throw new Error(`Voxalia Asterisk API error ${response.status}`);
  }

  return response.json() as Promise<ModulePayload>;
}

export async function getAsteriskInfrastructureWorkspace(): Promise<WorkspacePayload> {
  if (!ASTERISK_API_BASE_URL) {
    throw new Error("VOXALIA_ASTERISK_API_BASE_URL is not configured");
  }

  const response = await fetch(`${ASTERISK_API_BASE_URL}/asterisk/workspace`, {
    cache: "no-store"
  });

  if (!response.ok) {
    throw new Error(`Voxalia Asterisk API error ${response.status}`);
  }

  return response.json() as Promise<WorkspacePayload>;
}

export async function getAsteriskWorkspace(tenantKey: string): Promise<WorkspacePayload> {
  if (!ASTERISK_API_BASE_URL) {
    throw new Error("VOXALIA_ASTERISK_API_BASE_URL is not configured");
  }

  const response = await fetch(`${ASTERISK_API_BASE_URL}/asterisk/tenants/${encodeURIComponent(tenantKey)}/workspace`, {
    cache: "no-store"
  });

  if (!response.ok) {
    throw new Error(`Voxalia Asterisk API error ${response.status}`);
  }

  return response.json() as Promise<WorkspacePayload>;
}
