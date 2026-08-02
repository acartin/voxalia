"use client";

import { Badge } from "@/components/ui/badge";
import { ModulePayload } from "@/lib/types";
import { CrudResourcePage } from "./crud-resource-page";
import { CrudChoice, CrudResourceConfig } from "./types";

type SipTrunkRecord = Record<string, unknown> & {
  id: string;
  trunk_key: string;
  display_name: string;
  carrier_key: string;
  carrier_name: string;
  provider_endpoint: string;
  transport: string;
  trunk_role: string;
  registration_mode: string;
  auth_mode: string;
  match_strategy: string;
  remote_hosts: string;
  codecs: string;
  max_channels: number;
  status: string;
};

const statusOptions: CrudChoice[] = [
  { value: "active", label: "Active" },
  { value: "inactive", label: "Inactive" },
  { value: "provisioning", label: "Provisioning" },
  { value: "failed", label: "Failed" }
];

const transportOptions: CrudChoice[] = [
  { value: "udp", label: "UDP" },
  { value: "tcp", label: "TCP" },
  { value: "tls", label: "TLS" },
  { value: "ws", label: "WS" },
  { value: "wss", label: "WSS" }
];

const roleOptions: CrudChoice[] = [
  { value: "bidirectional", label: "Bidirectional" },
  { value: "inbound", label: "Inbound" },
  { value: "outbound", label: "Outbound" }
];

const registrationModeOptions: CrudChoice[] = [
  { value: "outbound_registration", label: "Outbound registration" },
  { value: "inbound_registration", label: "Inbound registration" },
  { value: "none", label: "None" }
];

const authModeOptions: CrudChoice[] = [
  { value: "outbound_auth", label: "Outbound auth" },
  { value: "inbound_auth", label: "Inbound auth" },
  { value: "mutual", label: "Mutual" },
  { value: "none", label: "None" }
];

const matchStrategyOptions: CrudChoice[] = [
  { value: "ip", label: "IP identify" },
  { value: "line", label: "Registration line" },
  { value: "header", label: "Header match" },
  { value: "registration", label: "Registration" }
];

const fallbackCarrierOptions: CrudChoice[] = [
  { value: "freepbx-lab", label: "FreePBX Lab" }
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

function sipTrunksConfig(carrierOptions: CrudChoice[]): CrudResourceConfig<SipTrunkRecord> {
  return {
  id: "settings.asterisk.infrastructure.trunks",
  title: "SIP Trunks",
  eyebrow: "trunk",
  description: "Global PJSIP trunk intent for carrier connectivity. Secrets are kept out of this CRUD.",
  createLabel: "Create trunk",
  createAction: "/api/settings/asterisk-infrastructure/trunks",
  rowActionBasePath: "/api/settings/asterisk-infrastructure/trunks",
  identityField: "id",
  titleField: "display_name",
  searchPlaceholder: "Search trunk, carrier, endpoint, host or codec",
  emptyTitle: "No SIP trunks match the current filters",
  emptyDescription: "Adjust search or filters and try again.",
  allowedActions: ["view", "edit", "delete"],
  filters: [
    { key: "status", label: "Status", allLabel: "All statuses", options: statusOptions },
    { key: "transport", label: "Transport", allLabel: "All transports", options: transportOptions },
    { key: "trunk_role", label: "Role", allLabel: "All roles", options: roleOptions }
  ],
  columns: [
    {
      id: "display_name",
      header: "Trunk",
      searchValue: (record) =>
        `${record.display_name} ${record.trunk_key} ${record.carrier_name} ${record.provider_endpoint} ${record.remote_hosts} ${record.codecs}`,
      cell: (record) => (
        <div className="min-w-56">
          <div className="font-medium text-foreground">{record.display_name}</div>
          <div className="text-meta text-muted-foreground">{record.trunk_key}</div>
        </div>
      )
    },
    { id: "carrier_name", header: "Carrier" },
    { id: "provider_endpoint", header: "Endpoint" },
    { id: "transport", header: "Transport" },
    { id: "registration_mode", header: "Registration" },
    { id: "match_strategy", header: "Match" },
    { id: "max_channels", header: "Channels", className: "text-right font-mono", headerClassName: "text-right" },
    {
      id: "status",
      header: "Status",
      cell: (record) => badgeForStatus(record.status),
      sortValue: (record) => record.status
    }
  ],
  createFields: [
    { label: "Trunk key", name: "trunk_key", placeholder: "twilio-main", helperText: "Stable lowercase key for generated PJSIP object names." },
    { label: "Display name", name: "display_name", placeholder: "Twilio Main" },
    { label: "Carrier", name: "carrier_key", control: "select", options: carrierOptions },
    { label: "Provider endpoint", name: "provider_endpoint", placeholder: "sip:example.pstn.provider" },
    { label: "Transport", name: "transport", control: "select", options: transportOptions, defaultValue: "udp" },
    { label: "Role", name: "trunk_role", control: "select", options: roleOptions, defaultValue: "bidirectional" },
    { label: "Registration mode", name: "registration_mode", control: "select", options: registrationModeOptions, defaultValue: "outbound_registration" },
    { label: "Auth mode", name: "auth_mode", control: "select", options: authModeOptions, defaultValue: "outbound_auth" },
    { label: "Inbound match", name: "match_strategy", control: "select", options: matchStrategyOptions, defaultValue: "ip" },
    { label: "Remote hosts", name: "remote_hosts", required: false, placeholder: "203.0.113.10, sip.provider.example" },
    { label: "Codecs", name: "codecs", defaultValue: "ulaw,alaw" },
    { label: "Max channels", name: "max_channels", type: "number", defaultValue: "0" },
    { label: "Status", name: "status", control: "select", options: statusOptions, defaultValue: "active" },
    { label: "Config JSON", name: "config", control: "json", required: false, defaultValue: "{}" }
  ],
  editFields: [
    { label: "Trunk key", name: "trunk_key" },
    { label: "Display name", name: "display_name" },
    { label: "Carrier", name: "carrier_key", control: "select", options: carrierOptions },
    { label: "Provider endpoint", name: "provider_endpoint" },
    { label: "Transport", name: "transport", control: "select", options: transportOptions },
    { label: "Role", name: "trunk_role", control: "select", options: roleOptions },
    { label: "Registration mode", name: "registration_mode", control: "select", options: registrationModeOptions },
    { label: "Auth mode", name: "auth_mode", control: "select", options: authModeOptions },
    { label: "Inbound match", name: "match_strategy", control: "select", options: matchStrategyOptions },
    { label: "Remote hosts", name: "remote_hosts", required: false },
    { label: "Codecs", name: "codecs" },
    { label: "Max channels", name: "max_channels", type: "number" },
    { label: "Status", name: "status", control: "select", options: statusOptions },
    { label: "Config JSON", name: "config", control: "json", required: false }
  ]
  };
}

export function SipTrunksCrud({ payload }: { payload: ModulePayload }) {
  const records = payload.records as SipTrunkRecord[];
  const payloadFilters = payload.filters as Record<string, unknown> | undefined;
  const carrierOptions = Array.isArray(payloadFilters?.carrier_options)
    ? payloadFilters.carrier_options as CrudChoice[]
    : Array.isArray(records[0]?._carrier_options)
      ? records[0]._carrier_options as CrudChoice[]
    : fallbackCarrierOptions;

  return <CrudResourcePage config={sipTrunksConfig(carrierOptions)} records={records} />;
}
