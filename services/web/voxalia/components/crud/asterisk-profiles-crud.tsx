"use client";

import { Badge } from "@/components/ui/badge";
import { ModulePayload } from "@/lib/types";
import { CrudResourcePage } from "./crud-resource-page";
import { CrudChoice, CrudResourceConfig } from "./types";

type AsteriskProfileRecord = Record<string, unknown> & {
  id: string;
  tenant_key: string;
  tenant_name: string;
  voice_enabled: boolean;
  provisioning_mode: string;
  namespace_key: string;
  default_context_prefix: string;
  default_extension_prefix: string;
  status: string;
  contexts: number;
  extensions: number;
  queues: number;
  routes: number;
  recording_policies: number;
};

const statusOptions: CrudChoice[] = [
  { value: "active", label: "Active" },
  { value: "paused", label: "Paused" },
  { value: "provisioning", label: "Provisioning" },
  { value: "failed", label: "Failed" }
];

const provisioningModeOptions: CrudChoice[] = [
  { value: "generated", label: "Generated" },
  { value: "hybrid", label: "Hybrid" },
  { value: "manual", label: "Manual" }
];

function badgeForStatus(status: string) {
  const classes: Record<string, string> = {
    active: "bg-[var(--green-bg)] text-[var(--green-text)]",
    paused: "bg-[var(--amber-bg)] text-[var(--amber-text)]",
    provisioning: "bg-[var(--blue-bg)] text-[var(--blue-text)]",
    failed: "bg-[var(--red-bg)] text-[var(--red-text)]"
  };

  return <Badge className={classes[status] ?? undefined}>{status}</Badge>;
}

const asteriskProfilesConfig: CrudResourceConfig<AsteriskProfileRecord> = {
  id: "settings.asterisk",
  title: "Tenant Voice Profiles",
  eyebrow: "voice profile",
  description: "Asterisk provisioning namespaces by tenant. Open a tenant to manage contexts, extensions, queues, routing, recording and runtime diagnostics.",
  createLabel: "Create profile",
  createAction: "/api/settings/asterisk",
  rowActionBasePath: "/api/settings/asterisk",
  identityField: "id",
  titleField: "tenant_name",
  searchPlaceholder: "Search tenant, namespace, context prefix or extension prefix",
  emptyTitle: "No Asterisk tenant profiles match the current filters",
  emptyDescription: "Adjust search or filters and try again.",
  canCreate: false,
  allowedActions: ["view", "workspace"],
  workspaceLabel: "Open Asterisk workspace",
  workspaceHref: (record) => `/settings/asterisk/${encodeURIComponent(record.tenant_key)}`,
  filters: [
    { key: "status", label: "Status", allLabel: "All statuses", options: statusOptions },
    { key: "provisioning_mode", label: "Mode", allLabel: "All modes", options: provisioningModeOptions }
  ],
  columns: [
    {
      id: "tenant_name",
      header: "Tenant",
      searchValue: (record) => `${record.tenant_name} ${record.tenant_key} ${record.namespace_key}`,
      cell: (record) => (
        <div className="min-w-56">
          <div className="font-medium text-foreground">{record.tenant_name}</div>
          <div className="text-meta text-muted-foreground">{record.tenant_key}</div>
        </div>
      )
    },
    { id: "namespace_key", header: "Namespace" },
    { id: "default_context_prefix", header: "Context prefix" },
    { id: "default_extension_prefix", header: "Ext prefix" },
    { id: "provisioning_mode", header: "Mode" },
    { id: "contexts", header: "Contexts", className: "text-right font-mono", headerClassName: "text-right" },
    { id: "extensions", header: "Ext", className: "text-right font-mono", headerClassName: "text-right" },
    { id: "queues", header: "Queues", className: "text-right font-mono", headerClassName: "text-right" },
    {
      id: "status",
      header: "Status",
      cell: (record) => badgeForStatus(record.status),
      sortValue: (record) => record.status
    }
  ],
  createFields: [],
  editFields: [
    { label: "Tenant", name: "tenant_name", editable: false },
    { label: "Namespace", name: "namespace_key", editable: false },
    { label: "Context prefix", name: "default_context_prefix", editable: false },
    { label: "Extension prefix", name: "default_extension_prefix", editable: false },
    { label: "Provisioning mode", name: "provisioning_mode", editable: false },
    { label: "Status", name: "status", editable: false },
    { label: "Contexts", name: "contexts", editable: false },
    { label: "Extensions", name: "extensions", editable: false },
    { label: "Queues", name: "queues", editable: false },
    { label: "Routes", name: "routes", editable: false },
    { label: "Recording policies", name: "recording_policies", editable: false }
  ]
};

export function AsteriskProfilesCrud({ payload }: { payload: ModulePayload }) {
  return <CrudResourcePage config={asteriskProfilesConfig} records={payload.records as AsteriskProfileRecord[]} />;
}
