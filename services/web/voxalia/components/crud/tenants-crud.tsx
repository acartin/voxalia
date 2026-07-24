"use client";

import { Badge } from "@/components/ui/badge";
import { ModulePayload } from "@/lib/types";
import { CrudResourcePage } from "./crud-resource-page";
import { CrudChoice, CrudResourceConfig } from "./types";

type TenantRecord = Record<string, unknown> & {
  id: string;
  tenant_key: string;
  display_name: string;
  legal_name?: string;
  vertical: string;
  timezone: string;
  status: string;
  users: number;
};

const statusOptions: CrudChoice[] = [
  { value: "active", label: "Active" },
  { value: "inactive", label: "Inactive" },
  { value: "suspended", label: "Suspended" }
];

const verticalOptions: CrudChoice[] = [
  { value: "hospitality", label: "Hospitality" },
  { value: "internal", label: "Internal" },
  { value: "other", label: "Other" }
];

function badgeForStatus(status: string) {
  const classes: Record<string, string> = {
    active: "bg-[var(--green-bg)] text-[var(--green-text)]",
    inactive: "bg-[var(--amber-bg)] text-[var(--amber-text)]",
    suspended: "bg-[var(--red-bg)] text-[var(--red-text)]"
  };

  return <Badge className={classes[status] ?? undefined}>{status}</Badge>;
}

const tenantsCrudConfig: CrudResourceConfig<TenantRecord> = {
  id: "settings.tenants",
  title: "Tenants",
  eyebrow: "tenant",
  description: "Tenant records are the entry point for partner configuration, service policy and operational workspaces.",
  createLabel: "Create tenant",
  createAction: "/api/settings/tenants",
  rowActionBasePath: "/api/settings/tenants",
  identityField: "id",
  titleField: "display_name",
  searchPlaceholder: "Search tenant, key, vertical or timezone",
  emptyTitle: "No tenants match the current filters",
  emptyDescription: "Adjust search or filters and try again.",
  canCreate: false,
  allowedActions: ["view", "workspace"],
  workspaceLabel: "Open workspace",
  workspaceHref: (record) => `/settings/tenants/${encodeURIComponent(record.tenant_key)}`,
  filters: [
    { key: "status", label: "Status", allLabel: "All statuses", options: statusOptions },
    { key: "vertical", label: "Vertical", allLabel: "All verticals", options: verticalOptions }
  ],
  columns: [
    {
      id: "display_name",
      header: "Tenant",
      searchValue: (record) => `${record.display_name} ${record.tenant_key} ${record.legal_name ?? ""}`,
      cell: (record) => (
        <div className="min-w-56">
          <div className="font-medium text-foreground">{record.display_name}</div>
          <div className="text-meta text-muted-foreground">{record.tenant_key}</div>
        </div>
      )
    },
    { id: "vertical", header: "Vertical" },
    { id: "timezone", header: "Timezone" },
    {
      id: "users",
      header: "Users",
      className: "text-right font-mono",
      headerClassName: "text-right",
      sortValue: (record) => record.users
    },
    {
      id: "status",
      header: "Status",
      cell: (record) => badgeForStatus(record.status),
      sortValue: (record) => record.status
    }
  ],
  createFields: [],
  editFields: [
    { label: "Tenant ID", name: "id", editable: false },
    { label: "Tenant key", name: "tenant_key", editable: false },
    { label: "Display name", name: "display_name", editable: false },
    { label: "Legal name", name: "legal_name", editable: false },
    { label: "Vertical", name: "vertical", editable: false },
    { label: "Timezone", name: "timezone", editable: false },
    { label: "Status", name: "status", editable: false },
    { label: "Users", name: "users", editable: false }
  ]
};

export function TenantsCrud({ payload }: { payload: ModulePayload }) {
  return <CrudResourcePage config={tenantsCrudConfig} records={payload.records as TenantRecord[]} />;
}
