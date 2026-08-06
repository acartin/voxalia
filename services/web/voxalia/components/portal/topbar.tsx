"use client";

import { useEffect, useState } from "react";
import { LogOut, PanelLeftClose, PanelLeftOpen, RefreshCw } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/ui/theme-toggle";
import { RoleSimulator } from "@/components/portal/role-simulator";
import { MenuPayload } from "@/lib/types";
import { cn } from "@/lib/utils";

type ApplyStatus = {
  status: "applied" | "pending" | "failed";
  pending_scopes: number;
  failed_scopes: number;
  pending_changes: number;
  pending_details: string[];
};

export function Topbar({
  menu,
  currentPath,
  compact = false,
  sidebarCollapsed = false,
  onToggleSidebar
}: {
  menu: MenuPayload;
  currentPath: string;
  compact?: boolean;
  sidebarCollapsed?: boolean;
  onToggleSidebar?: () => void;
}) {
  const [applyStatus, setApplyStatus] = useState<ApplyStatus | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadApplyStatus() {
      try {
        const response = await fetch("/api/settings/asterisk-infrastructure/provisioning/status", {
          cache: "no-store"
        });
        if (!response.ok) return;
        const payload = await response.json() as ApplyStatus;
        if (!cancelled) setApplyStatus(payload);
      } catch {
        if (!cancelled) setApplyStatus(null);
      }
    }

    loadApplyStatus();
    const interval = window.setInterval(loadApplyStatus, 30000);
    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, []);

  const showApply = applyStatus?.status === "pending" || applyStatus?.status === "failed";
  const applyTitle = applyStatus?.pending_details?.length
    ? applyStatus.pending_details.join("\n")
    : applyStatus?.status === "failed"
      ? "Asterisk apply needs attention"
      : "Asterisk changes pending";

  return (
    <header className={cn("flex items-center justify-between border-b bg-surface px-5 shadow-[0_1px_2px_var(--shadow-color)]", compact ? "min-h-12" : "min-h-16")}>
      <div className="flex min-w-0 items-center gap-3">
        <Button
          type="button"
          variant="ghost"
          className="h-9 w-9 px-0"
          onClick={onToggleSidebar}
          aria-label={sidebarCollapsed ? "Expand menu" : "Collapse menu"}
          title={sidebarCollapsed ? "Expand menu" : "Collapse menu"}
        >
          {sidebarCollapsed ? <PanelLeftOpen className="h-4 w-4" /> : <PanelLeftClose className="h-4 w-4" />}
        </Button>
        <div className="min-w-0">
          {!compact ? <div className="text-meta font-medium uppercase tracking-[0.08em] text-ink-muted">Tenant {menu.tenant.client_id}</div> : null}
          <div className="truncate text-body font-semibold">{menu.tenant.name}</div>
        </div>
      </div>
      <div className="flex items-center gap-3">
        <div className="flex min-w-[12rem] justify-end">
          <form
            action="/api/settings/asterisk-infrastructure/provisioning/apply"
            method="post"
            className={cn(!showApply && "invisible pointer-events-none")}
            aria-hidden={!showApply}
          >
            <Button
              type="submit"
              variant="outline"
              className={cn(
                "h-9 border-transparent font-semibold shadow-[0_1px_2px_var(--shadow-color)]",
                applyStatus?.status === "failed"
                  ? "bg-[var(--red-bg)] text-[var(--red-text)] hover:bg-[var(--red-bg)] hover:text-[var(--red-text)]"
                  : "bg-[var(--amber-bg)] text-[var(--amber-text)] hover:bg-[var(--amber-bg)] hover:text-[var(--amber-text)]",
                compact && "px-2"
              )}
              title={applyTitle}
              aria-label="Apply Asterisk configuration"
            >
              <RefreshCw className="h-4 w-4" />
              {!compact ? (
                <span>
                  Apply Config
                  {applyStatus?.pending_changes ? ` (${applyStatus.pending_changes})` : ""}
                </span>
              ) : null}
            </Button>
          </form>
        </div>
        {menu.auth.can_simulate_roles && !compact ? (
          <RoleSimulator
            activeRole={menu.user.role}
            isSimulated={menu.auth.is_role_simulated}
            currentPath={currentPath}
          />
        ) : null}
        <Badge>{menu.user.role_label}</Badge>
        <ThemeToggle />
        <form action="/api/auth/logout" method="post">
          <Button type="submit" variant="ghost" className="h-9 w-9 px-0" aria-label="Sign out" title="Sign out">
            <LogOut className="h-4 w-4" />
          </Button>
        </form>
      </div>
    </header>
  );
}
