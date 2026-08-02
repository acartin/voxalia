import { notFound } from "next/navigation";
import { AppShell } from "@/components/portal/app-shell";
import { AsteriskWorkspace } from "@/components/workspace/asterisk-workspace";
import { getAsteriskWorkspace, getMenu } from "@/lib/api";
import { feedbackFromSearchParams } from "@/lib/feedback";

const currentPath = "/settings/asterisk";

export default async function AsteriskTenantPage({
  params,
  searchParams
}: {
  params: Promise<{ tenantKey: string }>;
  searchParams?: Promise<{ context?: string; extension_id?: string; feedback?: string; flow_id?: string; message?: string; queue_key?: string; tab?: string }>;
}) {
  const resolvedParams = await params;
  const resolvedSearchParams = await searchParams;
  const menu = await getMenu();
  const allowed = menu.sections.some((section) => section.items.some((item) => item.href === currentPath));
  if (!allowed) notFound();

  const payload = await getAsteriskWorkspace(resolvedParams.tenantKey);

  return (
    <AppShell menu={menu} currentPath={currentPath}>
      <AsteriskWorkspace
        payload={payload}
        initialTab={resolvedSearchParams?.tab}
        contextFilter={resolvedSearchParams?.context}
        extensionFilter={resolvedSearchParams?.extension_id}
        flowFilter={resolvedSearchParams?.flow_id}
        queueFilter={resolvedSearchParams?.queue_key}
        feedback={feedbackFromSearchParams(resolvedSearchParams)}
      />
    </AppShell>
  );
}
