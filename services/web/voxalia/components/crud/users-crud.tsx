"use client";

import { Badge } from "@/components/ui/badge";
import { roleOptions } from "@/lib/modules";
import { ModulePayload } from "@/lib/types";
import { CrudResourcePage } from "./crud-resource-page";
import { CrudChoice, CrudResourceConfig } from "./types";

type UserRecord = Record<string, unknown> & {
  id: string;
  email: string;
  display_name: string;
  role: string;
  tenant_scope: string;
  status: string;
  last_seen_at?: string;
};

const statusOptions: CrudChoice[] = [
  { value: "active", label: "Active" },
  { value: "inactive", label: "Inactive" },
  { value: "locked", label: "Locked" }
];

const tenantScopeOptions: CrudChoice[] = [
  { value: "system", label: "System" },
  { value: "tenant", label: "Tenant" }
];

function badgeForStatus(status: string) {
  const classes: Record<string, string> = {
    active: "bg-[var(--green-bg)] text-[var(--green-text)]",
    inactive: "bg-[var(--amber-bg)] text-[var(--amber-text)]",
    locked: "bg-[var(--red-bg)] text-[var(--red-text)]"
  };

  return <Badge className={classes[status] ?? undefined}>{status}</Badge>;
}

function formatLastSeen(value: unknown) {
  if (!value) return "Never";
  const date = new Date(String(value));
  if (Number.isNaN(date.getTime())) return String(value);
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  }).format(date);
}

const usersCrudConfig: CrudResourceConfig<UserRecord> = {
  id: "settings.users",
  title: "Users",
  eyebrow: "user",
  description: "Account lifecycle, tenant membership and role-based access for Voxalia staff and partner users.",
  createLabel: "Create user",
  createAction: "/api/settings/users",
  rowActionBasePath: "/api/settings/users",
  identityField: "id",
  titleField: "display_name",
  searchPlaceholder: "Search name, email, role or tenant",
  emptyTitle: "No users match the current filters",
  emptyDescription: "Adjust search or filters and try again.",
  allowedActions: ["view", "edit", "deactivate"],
  filters: [
    { key: "status", label: "Status", allLabel: "All statuses", options: statusOptions },
    { key: "role", label: "Role", allLabel: "All roles", options: roleOptions.map((role) => ({ value: role.id, label: role.label })) },
    { key: "tenant_scope", label: "Scope", allLabel: "All scopes", options: tenantScopeOptions }
  ],
  columns: [
    {
      id: "display_name",
      header: "Name",
      searchValue: (record) => `${record.display_name} ${record.email}`,
      cell: (record) => (
        <div className="min-w-48">
          <div className="font-medium text-foreground">{record.display_name}</div>
          <div className="text-meta text-muted-foreground">{record.email}</div>
        </div>
      )
    },
    { id: "role_label", header: "Role", searchValue: (record) => `${record.role} ${record.role_label}` },
    { id: "tenant_name", header: "Tenant", searchValue: (record) => `${record.tenant_name} ${record.tenant_id}` },
    {
      id: "status",
      header: "Status",
      cell: (record) => badgeForStatus(String(record.status)),
      sortValue: (record) => String(record.status)
    },
    {
      id: "last_seen_at",
      header: "Last seen",
      cell: (record) => formatLastSeen(record.last_seen_at),
      sortValue: (record) => record.last_seen_at ?? ""
    }
  ],
  createFields: [
    { label: "Email", name: "email", type: "email" },
    { label: "Display name", name: "display_name" },
    {
      label: "Role",
      name: "role",
      control: "select",
      options: roleOptions.map((role) => ({ value: role.id, label: role.label }))
    },
    { label: "Tenant key", name: "tenant_key", defaultValue: "voxalia", helperText: "Resolved and validated by the API before assignment." },
    {
      label: "Status",
      name: "status",
      control: "select",
      defaultValue: "active",
      options: statusOptions
    },
    { label: "Temporary password", name: "password", type: "password", minLength: 8, helperText: "Required until invitation delivery is connected." }
  ],
  editFields: [
    { label: "User ID", name: "id", editable: false },
    { label: "Email", name: "email", type: "email", editable: false },
    { label: "Display name", name: "display_name" },
    {
      label: "Role",
      name: "role",
      control: "select",
      options: roleOptions.map((role) => ({ value: role.id, label: role.label }))
    },
    { label: "Tenant key", name: "tenant_key" },
    { label: "Tenant scope", name: "tenant_scope", editable: false },
    {
      label: "Status",
      name: "status",
      control: "select",
      options: statusOptions
    },
    { label: "Last seen", name: "last_seen_at", editable: false },
    { label: "Temporary password", name: "password", type: "password", minLength: 8, required: false, editOnly: true }
  ]
};

export function UsersCrud({ payload }: { payload: ModulePayload }) {
  return <CrudResourcePage config={usersCrudConfig} records={payload.records as UserRecord[]} />;
}
