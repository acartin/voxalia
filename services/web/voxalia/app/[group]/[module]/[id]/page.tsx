import { notFound } from "next/navigation";
import { AppShell } from "@/components/portal/app-shell";
import { TenantWorkspace } from "@/components/workspace/tenant-workspace";
import { getMenu, getWorkspace } from "@/lib/api";
import { feedbackFromSearchParams } from "@/lib/feedback";

function workspaceEndpoint(group: string, module: string, id: string) {
  if (group === "settings" && module === "tenants") {
    return `/settings/tenants/${encodeURIComponent(id)}/workspace`;
  }

  return null;
}

export default async function WorkspaceRoute({
  params,
  searchParams
}: {
  params: Promise<{ group: string; module: string; id: string }>;
  searchParams?: Promise<{ feedback?: string; message?: string; tab?: string }>;
}) {
  const resolvedParams = await params;
  const resolvedSearchParams = await searchParams;
  const currentPath = `/${resolvedParams.group}/${resolvedParams.module}`;
  const endpoint = workspaceEndpoint(resolvedParams.group, resolvedParams.module, resolvedParams.id);
  if (!endpoint) notFound();

  const [menu, payload] = await Promise.all([getMenu(), getWorkspace(endpoint)]);
  const allowed = menu.sections.some((section) => section.items.some((item) => item.href === currentPath));
  if (!allowed) notFound();

  return (
    <AppShell menu={menu} currentPath={currentPath}>
      <TenantWorkspace
        payload={payload}
        initialTab={resolvedSearchParams?.tab}
        feedback={feedbackFromSearchParams(resolvedSearchParams)}
      />
    </AppShell>
  );
}
