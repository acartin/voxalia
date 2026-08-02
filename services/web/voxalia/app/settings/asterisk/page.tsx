import { notFound } from "next/navigation";
import { AsteriskProfilesCrud } from "@/components/crud/asterisk-profiles-crud";
import { AppShell } from "@/components/portal/app-shell";
import { getAsteriskModule, getMenu } from "@/lib/api";
import { feedbackFromSearchParams } from "@/lib/feedback";
import { Badge } from "@/components/ui/badge";
import { FeedbackAlert } from "@/components/ui/feedback-alert";

const currentPath = "/settings/asterisk";

export default async function AsteriskPage({
  searchParams
}: {
  searchParams?: Promise<{ feedback?: string; message?: string; tab?: string }>;
}) {
  const resolvedSearchParams = await searchParams;
  const menu = await getMenu();
  const allowed = menu.sections.some((section) => section.items.some((item) => item.href === currentPath));
  if (!allowed) notFound();

  const payload = await getAsteriskModule();
  const feedback = feedbackFromSearchParams(resolvedSearchParams);

  return (
    <AppShell menu={menu} currentPath={currentPath}>
      <div className="space-y-6">
        <div>
          <div className="mb-2 flex items-center gap-2">
            <Badge>{payload.module.status}</Badge>
            <Badge>role: {payload.context.role}</Badge>
          </div>
          <h1 className="text-page-title font-light">{payload.module.title}</h1>
          <p className="mt-2 max-w-3xl text-page-subtitle text-muted-foreground">{payload.module.description}</p>
        </div>
        <FeedbackAlert feedback={feedback} />
        <AsteriskProfilesCrud payload={payload} />
      </div>
    </AppShell>
  );
}
