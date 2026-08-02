"use client";

import { Badge } from "@/components/ui/badge";
import { ModulePayload } from "@/lib/types";
import { CrudResourcePage } from "./crud-resource-page";
import { CrudChoice, CrudResourceConfig } from "./types";

type AsteriskInstanceRecord = Record<string, unknown> & {
  id: string;
  instance_key: string;
  display_name: string;
  environment: string;
  role: string;
  control_mode: string;
  endpoint_ref: string;
  region: string;
  asterisk_version: string;
  capabilities: string;
  status: string;
  health_status: string;
  last_seen_at?: string | null;
};

const environmentOptions: CrudChoice[] = [
  { value: "dev", label: "Dev" },
  { value: "staging", label: "Staging" },
  { value: "production", label: "Production" },
  { value: "lab", label: "Lab" }
];

const roleOptions: CrudChoice[] = [
  { value: "standalone", label: "Standalone" },
  { value: "primary", label: "Primary" },
  { value: "secondary", label: "Secondary" },
  { value: "worker", label: "Worker" }
];

const controlModeOptions: CrudChoice[] = [
  { value: "config_render", label: "Config render" },
  { value: "ami", label: "AMI" },
  { value: "ari", label: "ARI" },
  { value: "ssh", label: "SSH" },
  { value: "manual", label: "Manual" }
];

const statusOptions: CrudChoice[] = [
  { value: "active", label: "Active" },
  { value: "inactive", label: "Inactive" },
  { value: "maintenance", label: "Maintenance" },
  { value: "provisioning", label: "Provisioning" },
  { value: "failed", label: "Failed" }
];

const healthStatusOptions: CrudChoice[] = [
  { value: "unknown", label: "Unknown" },
  { value: "healthy", label: "Healthy" },
  { value: "degraded", label: "Degraded" },
  { value: "offline", label: "Offline" }
];

function badgeForStatus(status: string) {
  const classes: Record<string, string> = {
    active: "bg-[var(--green-bg)] text-[var(--green-text)]",
    inactive: "bg-[var(--amber-bg)] text-[var(--amber-text)]",
    maintenance: "bg-[var(--blue-bg)] text-[var(--blue-text)]",
    provisioning: "bg-[var(--blue-bg)] text-[var(--blue-text)]",
    failed: "bg-[var(--red-bg)] text-[var(--red-text)]"
  };

  return <Badge className={classes[status] ?? undefined}>{status}</Badge>;
}

function badgeForHealth(status: string) {
  const classes: Record<string, string> = {
    healthy: "bg-[var(--green-bg)] text-[var(--green-text)]",
    degraded: "bg-[var(--amber-bg)] text-[var(--amber-text)]",
    offline: "bg-[var(--red-bg)] text-[var(--red-text)]",
    unknown: "bg-surface-2 text-muted-foreground"
  };

  return <Badge className={classes[status] ?? undefined}>{status}</Badge>;
}

const asteriskInstancesConfig: CrudResourceConfig<AsteriskInstanceRecord> = {
  id: "settings.asterisk.infrastructure.instances",
  title: "Asterisk Instances",
  eyebrow: "instance",
  description: "Global runtime node inventory for provisioning targets, health posture and deployment mapping.",
  createLabel: "Create instance",
  createAction: "/api/settings/asterisk-infrastructure/instances",
  rowActionBasePath: "/api/settings/asterisk-infrastructure/instances",
  identityField: "id",
  titleField: "display_name",
  searchPlaceholder: "Search instance, endpoint, environment, region or capability",
  emptyTitle: "No Asterisk instances match the current filters",
  emptyDescription: "Adjust search or filters and try again.",
  allowedActions: ["view", "edit", "delete"],
  filters: [
    { key: "environment", label: "Environment", allLabel: "All environments", options: environmentOptions },
    { key: "status", label: "Status", allLabel: "All statuses", options: statusOptions },
    { key: "health_status", label: "Health", allLabel: "All health states", options: healthStatusOptions }
  ],
  columns: [
    {
      id: "display_name",
      header: "Instance",
      searchValue: (record) =>
        `${record.display_name} ${record.instance_key} ${record.endpoint_ref} ${record.environment} ${record.region} ${record.capabilities}`,
      cell: (record) => (
        <div className="min-w-56">
          <div className="font-medium text-foreground">{record.display_name}</div>
          <div className="text-meta text-muted-foreground">{record.instance_key}</div>
        </div>
      )
    },
    { id: "environment", header: "Environment" },
    { id: "role", header: "Role" },
    { id: "control_mode", header: "Control" },
    { id: "endpoint_ref", header: "Endpoint ref" },
    { id: "region", header: "Region" },
    {
      id: "health_status",
      header: "Health",
      cell: (record) => badgeForHealth(record.health_status),
      sortValue: (record) => record.health_status
    },
    {
      id: "status",
      header: "Status",
      cell: (record) => badgeForStatus(record.status),
      sortValue: (record) => record.status
    }
  ],
  createFields: [
    { label: "Instance key", name: "instance_key", placeholder: "asterisk-prod-01", helperText: "Stable lowercase key for provisioning references." },
    { label: "Display name", name: "display_name", placeholder: "Asterisk Prod 01" },
    { label: "Environment", name: "environment", control: "select", options: environmentOptions, defaultValue: "dev" },
    { label: "Role", name: "role", control: "select", options: roleOptions, defaultValue: "standalone" },
    { label: "Control mode", name: "control_mode", control: "select", options: controlModeOptions, defaultValue: "config_render" },
    { label: "Endpoint ref", name: "endpoint_ref", placeholder: "env:VOXALIA_ASTERISK_RUNTIME" },
    { label: "Region", name: "region", defaultValue: "local" },
    { label: "Asterisk version", name: "asterisk_version", required: false, placeholder: "20.11.1" },
    { label: "Capabilities", name: "capabilities", defaultValue: "pjsip,queues,recording" },
    { label: "Status", name: "status", control: "select", options: statusOptions, defaultValue: "active" },
    { label: "Health", name: "health_status", control: "select", options: healthStatusOptions, defaultValue: "unknown" },
    { label: "Config JSON", name: "config", control: "json", required: false, defaultValue: "{}" }
  ],
  editFields: [
    { label: "Instance key", name: "instance_key" },
    { label: "Display name", name: "display_name" },
    { label: "Environment", name: "environment", control: "select", options: environmentOptions },
    { label: "Role", name: "role", control: "select", options: roleOptions },
    { label: "Control mode", name: "control_mode", control: "select", options: controlModeOptions },
    { label: "Endpoint ref", name: "endpoint_ref" },
    { label: "Region", name: "region" },
    { label: "Asterisk version", name: "asterisk_version", required: false },
    { label: "Capabilities", name: "capabilities" },
    { label: "Status", name: "status", control: "select", options: statusOptions },
    { label: "Health", name: "health_status", control: "select", options: healthStatusOptions },
    { label: "Config JSON", name: "config", control: "json", required: false }
  ]
};

export function AsteriskInstancesCrud({ payload }: { payload: ModulePayload }) {
  return <CrudResourcePage config={asteriskInstancesConfig} records={payload.records as AsteriskInstanceRecord[]} />;
}
