"use client";

import { Badge } from "@/components/ui/badge";
import { ModulePayload } from "@/lib/types";
import { CrudResourcePage } from "./crud-resource-page";
import { CrudChoice, CrudResourceConfig } from "./types";

type CarrierRecord = Record<string, unknown> & {
  id: string;
  carrier_key: string;
  display_name: string;
  provider_name: string;
  account_scope: string;
  region: string;
  support_status: string;
  failover_policy: string;
  status: string;
};

const statusOptions: CrudChoice[] = [
  { value: "active", label: "Active" },
  { value: "inactive", label: "Inactive" },
  { value: "provisioning", label: "Provisioning" },
  { value: "failed", label: "Failed" }
];

const accountScopeOptions: CrudChoice[] = [
  { value: "global", label: "Global" },
  { value: "regional", label: "Regional" },
  { value: "tenant_dedicated", label: "Tenant dedicated" },
  { value: "lab", label: "Lab" }
];

const supportStatusOptions: CrudChoice[] = [
  { value: "standard", label: "Standard" },
  { value: "premium", label: "Premium" },
  { value: "limited", label: "Limited" },
  { value: "unsupported", label: "Unsupported" }
];

const failoverPolicyOptions: CrudChoice[] = [
  { value: "manual", label: "Manual" },
  { value: "automatic", label: "Automatic" },
  { value: "none", label: "None" }
];

function badgeForStatus(status: string) {
  const classes: Record<string, string> = {
    active: "bg-[var(--green-bg)] text-[var(--green-text)]",
    inactive: "bg-[var(--amber-bg)] text-[var(--amber-text)]",
    provisioning: "bg-[var(--blue-bg)] text-[var(--blue-text)]",
    failed: "bg-[var(--red-bg)] text-[var(--red-text)]"
  };

  return <Badge className={classes[status] ?? undefined}>{status}</Badge>;
}

const carriersConfig: CrudResourceConfig<CarrierRecord> = {
  id: "settings.asterisk.infrastructure.carriers",
  title: "Carriers",
  eyebrow: "carrier",
  description: "Global provider account catalog for trunk connectivity and support posture.",
  createLabel: "Create carrier",
  createAction: "/api/settings/asterisk-infrastructure/carriers",
  rowActionBasePath: "/api/settings/asterisk-infrastructure/carriers",
  identityField: "id",
  titleField: "display_name",
  searchPlaceholder: "Search carrier, provider, region or support status",
  emptyTitle: "No carriers match the current filters",
  emptyDescription: "Adjust search or filters and try again.",
  allowedActions: ["view", "edit", "delete"],
  filters: [
    { key: "status", label: "Status", allLabel: "All statuses", options: statusOptions },
    { key: "account_scope", label: "Scope", allLabel: "All scopes", options: accountScopeOptions },
    { key: "support_status", label: "Support", allLabel: "All support states", options: supportStatusOptions }
  ],
  columns: [
    {
      id: "display_name",
      header: "Carrier",
      searchValue: (record) =>
        `${record.display_name} ${record.carrier_key} ${record.provider_name} ${record.region} ${record.support_status}`,
      cell: (record) => (
        <div className="min-w-56">
          <div className="font-medium text-foreground">{record.display_name}</div>
          <div className="text-meta text-muted-foreground">{record.carrier_key}</div>
        </div>
      )
    },
    { id: "provider_name", header: "Provider" },
    { id: "account_scope", header: "Scope" },
    { id: "region", header: "Region" },
    { id: "support_status", header: "Support" },
    { id: "failover_policy", header: "Failover" },
    {
      id: "status",
      header: "Status",
      cell: (record) => badgeForStatus(record.status),
      sortValue: (record) => record.status
    }
  ],
  createFields: [
    { label: "Carrier key", name: "carrier_key", placeholder: "twilio-us", helperText: "Stable lowercase key for provider account references." },
    { label: "Display name", name: "display_name", placeholder: "Twilio US" },
    { label: "Provider name", name: "provider_name", placeholder: "Twilio" },
    { label: "Account scope", name: "account_scope", control: "select", options: accountScopeOptions, defaultValue: "global" },
    { label: "Region", name: "region", defaultValue: "us" },
    { label: "Support status", name: "support_status", control: "select", options: supportStatusOptions, defaultValue: "standard" },
    { label: "Failover policy", name: "failover_policy", control: "select", options: failoverPolicyOptions, defaultValue: "manual" },
    { label: "Status", name: "status", control: "select", options: statusOptions, defaultValue: "active" },
    { label: "Config JSON", name: "config", control: "json", required: false, defaultValue: "{}" }
  ],
  editFields: [
    { label: "Carrier key", name: "carrier_key" },
    { label: "Display name", name: "display_name" },
    { label: "Provider name", name: "provider_name" },
    { label: "Account scope", name: "account_scope", control: "select", options: accountScopeOptions },
    { label: "Region", name: "region" },
    { label: "Support status", name: "support_status", control: "select", options: supportStatusOptions },
    { label: "Failover policy", name: "failover_policy", control: "select", options: failoverPolicyOptions },
    { label: "Status", name: "status", control: "select", options: statusOptions },
    { label: "Config JSON", name: "config", control: "json", required: false }
  ]
};

export function CarriersCrud({ payload }: { payload: ModulePayload }) {
  return <CrudResourcePage config={carriersConfig} records={payload.records as CarrierRecord[]} />;
}
