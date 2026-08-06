"use client";

import type { ReactNode } from "react";
import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { Braces, CheckCircle2, CircleAlert, Eye, FileText, RadioTower, RefreshCw, Server, TriangleAlert } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { AsteriskInstancesCrud } from "@/components/crud/asterisk-instances-crud";
import { CarriersCrud } from "@/components/crud/carriers-crud";
import { SipTrunksCrud } from "@/components/crud/sip-trunks-crud";
import { Button } from "@/components/ui/button";
import { Modal } from "@/components/ui/modal";
import { Tabs } from "@/components/ui/tabs";
import { ModulePayload, WorkspacePayload, WorkspaceSection } from "@/lib/types";

const sections = [
  {
    id: "overview",
    label: "Overview"
  },
  {
    id: "trunks",
    label: "Trunks"
  },
  {
    id: "carriers",
    label: "Carriers"
  },
  {
    id: "instances",
    label: "Asterisk Instances"
  },
  {
    id: "provisioning",
    label: "Provisioning"
  }
];

function sectionById(payload: WorkspacePayload, id: string): WorkspaceSection | undefined {
  return payload.sections.find((section) => section.id === id);
}

function displayValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "boolean") return value ? "Yes" : "No";
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function formattedJson(value: unknown): string {
  if (value === null || value === undefined || value === "") return "{}";
  if (typeof value === "string") {
    try {
      return JSON.stringify(JSON.parse(value), null, 2);
    } catch {
      return value;
    }
  }
  return JSON.stringify(value, null, 2);
}

function statusTone(status: unknown) {
  const value = String(status ?? "").toLowerCase();
  if (["failed", "drift_detected", "error", "down"].includes(value)) return "border-transparent bg-[var(--red-bg)] text-[var(--red-text)]";
  if (["queued", "running", "pending", "provisioning", "degraded"].includes(value)) return "border-transparent bg-[var(--amber-bg)] text-[var(--amber-text)]";
  if (["active", "applied", "ok", "healthy"].includes(value)) return "border-transparent bg-[var(--green-bg)] text-[var(--green-text)]";
  return "border-border-2 bg-surface-muted text-muted-foreground";
}

function healthDotTone(status: unknown) {
  const value = String(status ?? "").toLowerCase();
  if (["failed", "error", "down"].includes(value)) return "bg-[var(--red)] shadow-[0_0_0_4px_var(--red-bg)]";
  if (["queued", "running", "pending", "provisioning", "degraded"].includes(value)) return "bg-[var(--amber)] shadow-[0_0_0_4px_var(--amber-bg)]";
  if (["active", "applied", "ok", "healthy"].includes(value)) return "bg-[var(--green)] shadow-[0_0_0_4px_var(--green-bg)]";
  return "bg-muted-foreground/50 shadow-[0_0_0_4px_var(--surface-muted)]";
}

function serviceStatusLabel(status: unknown) {
  const value = String(status ?? "unknown").toLowerCase();
  if (value === "healthy") return "Online";
  if (value === "degraded") return "Attention";
  if (value === "down") return "Down";
  if (value === "info") return "Info";
  return displayValue(status);
}

function RecordsTable({
  records,
  columns,
  emptyText,
  renderActions
}: {
  records: Array<Record<string, unknown>>;
  columns: Array<{ key: string; label: string }>;
  emptyText: string;
  renderActions?: (record: Record<string, unknown>) => ReactNode;
}) {
  if (!records.length) {
    return (
      <div className="rounded-md border border-dashed border-border-2 px-4 py-6 text-body-sm text-muted-foreground">
        {emptyText}
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-md border border-border-2">
      <table className="min-w-full border-collapse text-left text-body-sm">
        <thead className="bg-surface-muted text-muted-foreground">
          <tr>
            {columns.map((column) => (
              <th key={column.key} className="px-3 py-2 font-medium">
                {column.label}
              </th>
            ))}
            {renderActions ? <th className="w-24 px-3 py-2 text-right font-medium">Actions</th> : null}
          </tr>
        </thead>
        <tbody>
          {records.map((record, index) => (
            <tr key={String(record.id ?? `${record.scope_key ?? "record"}-${index}`)} className="border-t border-border-2">
              {columns.map((column) => {
                const value = record[column.key];
                return (
                  <td key={column.key} className="px-3 py-2 align-top">
                    {column.key === "status" ? (
                      <span className={`inline-flex rounded-full border px-2 py-0.5 text-label-sm font-medium ${statusTone(value)}`}>
                        {displayValue(value)}
                      </span>
                    ) : (
                      displayValue(value)
                    )}
                  </td>
                );
              })}
              {renderActions ? <td className="px-3 py-2 text-right align-top">{renderActions(record)}</td> : null}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function RenderedConfigViewer({ revision }: { revision: Record<string, unknown> }) {
  const tenants = Array.isArray(revision.rendered_tenants) ? revision.rendered_tenants : [];

  if (!tenants.length) {
    return (
      <div className="rounded-md border border-dashed border-border-2 px-4 py-6 text-body-sm text-muted-foreground">
        This revision does not contain rendered tenant files.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {tenants.map((tenant) => {
        const tenantRecord = tenant as Record<string, unknown>;
        const files = tenantRecord.files && typeof tenantRecord.files === "object" ? (tenantRecord.files as Record<string, unknown>) : {};
        const fileEntries = Object.entries(files);

        return (
          <section key={String(tenantRecord.tenant_key ?? tenantRecord.display_name)} className="space-y-2">
            <div>
              <h3 className="text-body font-medium">{displayValue(tenantRecord.display_name)}</h3>
              <div className="text-body-sm text-muted-foreground">{displayValue(tenantRecord.tenant_key)}</div>
            </div>
            <div className="space-y-3">
              {fileEntries.map(([fileName, content]) => (
                <details key={fileName} className="rounded-md border border-border-2 bg-card">
                  <summary className="cursor-pointer px-3 py-2 text-body-sm font-medium text-foreground hover:bg-surface-hover">
                    {fileName}
                  </summary>
                  <pre className="max-h-96 overflow-auto border-t border-border-2 bg-surface-muted px-3 py-3 text-xs leading-5 text-foreground">
                    {String(content ?? "")}
                  </pre>
                </details>
              ))}
            </div>
          </section>
        );
      })}
    </div>
  );
}

function OverviewPanel({ payload }: { payload: WorkspacePayload }) {
  const router = useRouter();
  const [isRefreshing, startRefresh] = useTransition();
  const serviceHealth = sectionById(payload, "service_health")?.records ?? [];
  const tenants = sectionById(payload, "overview")?.records ?? [];
  const unhealthyCount = serviceHealth.filter((record) => ["down", "failed", "error"].includes(String(record.status ?? "").toLowerCase())).length;
  const attentionCount = serviceHealth.filter((record) => ["degraded", "pending", "provisioning"].includes(String(record.status ?? "").toLowerCase())).length;

  return (
    <div className="space-y-5">
      <section className="rounded-md border border-border-2 bg-card px-4 py-4">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-section-title font-medium">Asterisk Services</h2>
              <span className={`inline-flex rounded-full px-2 py-0.5 text-label-sm font-medium ${statusTone(unhealthyCount ? "down" : attentionCount ? "degraded" : "healthy")}`}>
                {unhealthyCount ? `${unhealthyCount} down` : attentionCount ? `${attentionCount} need attention` : "All clear"}
              </span>
            </div>
            <p className="mt-1 text-body-sm text-muted-foreground">
              Runtime, provisioning and generated configuration state for the Voxalia-managed Asterisk stack.
            </p>
          </div>
          <div className="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-md border border-border-2 bg-surface-muted text-foreground">
            <Server className="h-5 w-5" aria-hidden="true" />
          </div>
        </div>
        <div className="mt-4 flex justify-end border-t border-border-2 pt-4">
          <Button
            type="button"
            variant="outline"
            disabled={isRefreshing}
            onClick={() => startRefresh(() => router.refresh())}
          >
            <RefreshCw className={`h-4 w-4 ${isRefreshing ? "animate-spin" : ""}`} aria-hidden="true" />
            {isRefreshing ? "Refreshing..." : "Refresh Status"}
          </Button>
        </div>
      </section>

      <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {serviceHealth.map((record) => (
          <article key={String(record.service_key ?? record.service)} className="rounded-md border border-border-2 bg-card px-4 py-4">
            <div className="flex items-start justify-between gap-4">
              <div className="min-w-0">
                <div className="flex items-center gap-3">
                  <span className={`h-3 w-3 shrink-0 rounded-full ${healthDotTone(record.status)}`} aria-hidden="true" />
                  <h3 className="truncate text-body font-medium">{displayValue(record.service)}</h3>
                </div>
                <div className="mt-3 space-y-1">
                  <div className="text-body-sm text-muted-foreground">{displayValue(record.detail)}</div>
                  <div className="text-label-sm text-muted-foreground">{displayValue(record.endpoint)}</div>
                </div>
              </div>
              <span className={`shrink-0 rounded-full px-2 py-0.5 text-label-sm font-medium ${statusTone(record.status)}`}>
                {serviceStatusLabel(record.status)}
              </span>
            </div>
            <div className="mt-4 flex items-center gap-2 border-t border-border-2 pt-3 text-label-sm text-muted-foreground">
              <CircleAlert className="h-4 w-4" aria-hidden="true" />
              Checked via {displayValue(record.checked_via)}
            </div>
          </article>
        ))}
      </section>

      <section className="grid gap-3 md:grid-cols-4">
        {payload.summary.map((item) => (
          <div key={item.label} className="rounded-md border border-border-2 bg-card px-4 py-3">
            <div className="text-label-sm font-medium uppercase text-muted-foreground">{item.label}</div>
            <div className="mt-1 text-section-title font-semibold">{item.value}</div>
          </div>
        ))}
      </section>

      <section className="space-y-3">
        <h2 className="text-section-title font-medium">Active Tenant Profiles</h2>
        <RecordsTable
          records={tenants}
          columns={[
            { key: "display_name", label: "Tenant" },
            { key: "tenant_key", label: "Key" }
          ]}
          emptyText="No active tenants found."
        />
      </section>
    </div>
  );
}

function ProvisioningPanel({ payload }: { payload: WorkspacePayload }) {
  const [modal, setModal] = useState<{ type: "job-result" | "rendered-config"; record: Record<string, unknown> } | null>(null);
  const provisioning = sectionById(payload, "provisioning")?.records ?? [];
  const revisions = sectionById(payload, "config_revisions")?.records ?? [];
  const tenantApplyState = sectionById(payload, "tenant_apply_state")?.records ?? [];
  const drift = sectionById(payload, "drift")?.records ?? [];
  const runtime = sectionById(payload, "runtime")?.records ?? [];
  const pendingTenants = tenantApplyState.filter((record) => String(record.status ?? "").toLowerCase() === "pending").length;
  const failedTenants = tenantApplyState.filter((record) => String(record.status ?? "").toLowerCase() === "failed").length;
  const applyStatus = failedTenants > 0 ? "failed" : pendingTenants > 0 ? "pending" : "applied";

  return (
    <div className="space-y-5">
      <div className="rounded-md border border-border-2 bg-card px-4 py-4">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div className="flex min-w-0 items-start gap-3">
            <div className={`mt-0.5 inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-md ${statusTone(applyStatus)}`}>
              {applyStatus === "applied" ? (
                <CheckCircle2 className="h-5 w-5" aria-hidden="true" />
              ) : applyStatus === "failed" ? (
                <TriangleAlert className="h-5 w-5" aria-hidden="true" />
              ) : (
                <RadioTower className="h-5 w-5" aria-hidden="true" />
              )}
            </div>
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-2">
                <h2 className="text-section-title font-medium">Asterisk Apply Config</h2>
                <span className={`inline-flex rounded-full px-2 py-0.5 text-label-sm font-medium ${statusTone(applyStatus)}`}>
                  {applyStatus === "applied" ? "Applied" : applyStatus === "failed" ? "Failed" : "Pending changes"}
                </span>
              </div>
              <p className="mt-1 text-body-sm text-muted-foreground">
                Applies the current Voxalia Asterisk settings as one consistent configuration. This first version records a render-only apply; it does not reload Asterisk yet.
              </p>
            </div>
          </div>
          <form action="/api/settings/asterisk-infrastructure/provisioning/apply" method="post">
            <Button type="submit" className="w-full md:w-auto" disabled={applyStatus === "applied"}>
              <RefreshCw className="h-4 w-4" aria-hidden="true" />
              Apply Config
            </Button>
          </form>
        </div>
      </div>

      <div className="grid gap-3 md:grid-cols-4">
        {payload.summary
          .filter((item) => ["Tenants", "Jobs", "Drift", "Devices"].includes(item.label))
          .map((item) => (
            <div key={item.label} className="rounded-md border border-border-2 bg-card px-4 py-3">
              <div className="text-label-sm font-medium uppercase text-muted-foreground">{item.label}</div>
              <div className="mt-1 text-section-title font-semibold">{item.value}</div>
            </div>
          ))}
      </div>

      <section className="space-y-3">
        <div>
          <h2 className="text-section-title font-medium">Apply State</h2>
          <p className="mt-1 text-body-sm text-muted-foreground">
            Consolidated status by infrastructure and tenant based on the last configuration change and the last recorded apply.
          </p>
        </div>
        <RecordsTable
          records={tenantApplyState}
          columns={[
            { key: "tenant", label: "Scope" },
            { key: "provisioning_mode", label: "Mode" },
            { key: "status", label: "Status" },
            { key: "pending_changes", label: "Pending" },
            { key: "pending_details", label: "Why" },
            { key: "last_config_change_at", label: "Last Change" },
            { key: "pending_jobs", label: "Pending Jobs" },
            { key: "drift_alerts", label: "Drift Alerts" },
            { key: "last_provisioned_at", label: "Last Apply" },
            { key: "last_drift_check_at", label: "Last Drift Check" }
          ]}
          emptyText="No apply scopes found."
        />
      </section>

      <section className="space-y-3">
        <h2 className="text-section-title font-medium">Provisioning Jobs</h2>
        <RecordsTable
          records={provisioning}
          columns={[
            { key: "scope", label: "Scope" },
            { key: "job_type", label: "Job" },
            { key: "status", label: "Status" },
            { key: "requested_at", label: "Requested" },
            { key: "finished_at", label: "Finished" },
            { key: "error_message", label: "Error" }
          ]}
          emptyText="No provisioning jobs have been recorded yet."
          renderActions={(record) => (
            <Button type="button" variant="ghost" className="h-8 w-8 px-0" title="View job result" onClick={() => setModal({ type: "job-result", record })}>
              <Eye className="h-4 w-4" aria-hidden="true" />
            </Button>
          )}
        />
      </section>

      <section className="space-y-3">
        <h2 className="text-section-title font-medium">Config Revisions</h2>
        <RecordsTable
          records={revisions}
          columns={[
            { key: "revision_key", label: "Revision" },
            { key: "status", label: "Status" },
            { key: "job_status", label: "Job Status" },
            { key: "tenant_count", label: "Tenants" },
            { key: "rendered_files", label: "Files" },
            { key: "applied_at", label: "Applied" },
            { key: "config_hash", label: "Hash" }
          ]}
          emptyText="No rendered config revisions have been recorded yet."
          renderActions={(record) => (
            <Button type="button" variant="ghost" className="h-8 w-8 px-0" title="View rendered config" onClick={() => setModal({ type: "rendered-config", record })}>
              <FileText className="h-4 w-4" aria-hidden="true" />
            </Button>
          )}
        />
      </section>

      <section className="space-y-3">
        <h2 className="text-section-title font-medium">Drift Checks</h2>
        <RecordsTable
          records={drift}
          columns={[
            { key: "scope", label: "Scope" },
            { key: "status", label: "Status" },
            { key: "expected_hash", label: "Expected" },
            { key: "observed_hash", label: "Observed" },
            { key: "checked_at", label: "Checked" }
          ]}
          emptyText="No drift checks have been recorded yet."
        />
      </section>

      <section className="space-y-3">
        <h2 className="text-section-title font-medium">Runtime</h2>
        <RecordsTable
          records={runtime}
          columns={[
            { key: "instance_key", label: "Instance" },
            { key: "status", label: "Status" },
            { key: "asterisk_version", label: "Version" },
            { key: "endpoint", label: "Endpoint" },
            { key: "last_seen_at", label: "Last Seen" }
          ]}
          emptyText="No runtime status has been reported yet."
        />
      </section>

      <Modal
        open={modal !== null}
        title={modal?.type === "rendered-config" ? "Rendered Config" : "Job Result"}
        description={
          modal
            ? modal.type === "rendered-config"
              ? String(modal.record.revision_key ?? "Rendered files generated by Apply Config.")
              : String(modal.record.job_type ?? "Provisioning job result.")
            : undefined
        }
        onClose={() => setModal(null)}
        className={modal?.type === "rendered-config" ? "max-w-6xl" : "max-w-3xl"}
      >
        {modal?.type === "rendered-config" ? (
          <RenderedConfigViewer revision={modal.record} />
        ) : (
          <div className="space-y-3">
            <div className="flex items-center gap-2 text-body-sm font-medium">
              <Braces className="h-4 w-4" aria-hidden="true" />
              Result JSON
            </div>
            <pre className="max-h-[60vh] overflow-auto rounded-md border border-border-2 bg-surface-muted px-3 py-3 text-xs leading-5 text-foreground">
              {formattedJson(modal?.record.result)}
            </pre>
          </div>
        )}
      </Modal>
    </div>
  );
}

export function AsteriskInfrastructurePlaceholder({
  trunksPayload,
  carriersPayload,
  instancesPayload,
  workspacePayload
}: {
  trunksPayload: ModulePayload;
  carriersPayload: ModulePayload;
  instancesPayload: ModulePayload;
  workspacePayload: WorkspacePayload;
}) {
  const [activeSectionId, setActiveSectionId] = useState(sections[0].id);

  return (
    <div className="space-y-6">
      <div className="flex flex-col justify-between gap-4 md:flex-row md:items-start">
        <div className="min-w-0">
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <Badge>Infrastructure scope</Badge>
          </div>
          <h1 className="text-page-title font-light">Asterisk Infrastructure</h1>
          <p className="mt-2 max-w-3xl text-page-subtitle text-muted-foreground">
            Global connectivity layer for trunks, carriers and Asterisk runtime instances.
          </p>
        </div>
      </div>

      <div className="rounded-md border border-border-2 bg-card px-4 py-3">
        <Tabs
          items={sections.map((section) => ({ id: section.id, label: section.label }))}
          value={activeSectionId}
          onValueChange={setActiveSectionId}
          className="max-w-full overflow-x-auto"
        />
      </div>

      {activeSectionId === "overview" ? (
        <OverviewPanel payload={workspacePayload} />
      ) : activeSectionId === "trunks" ? (
        <SipTrunksCrud payload={trunksPayload} />
      ) : activeSectionId === "carriers" ? (
        <CarriersCrud payload={carriersPayload} />
      ) : activeSectionId === "instances" ? (
        <AsteriskInstancesCrud payload={instancesPayload} />
      ) : (
        <ProvisioningPanel payload={workspacePayload} />
      )}
    </div>
  );
}
