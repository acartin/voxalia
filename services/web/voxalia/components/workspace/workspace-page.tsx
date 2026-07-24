"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { ArrowLeft, FolderKanban } from "lucide-react";
import { Alert } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Tabs } from "@/components/ui/tabs";
import { Feedback } from "@/lib/feedback";
import { WorkspacePayload, WorkspaceSection } from "@/lib/types";
import { cn } from "@/lib/utils";

const toneClasses = {
  blue: "text-semantic-blue",
  green: "text-semantic-green",
  amber: "text-semantic-amber",
  red: "text-semantic-red"
};

function PlaceholderSection({ section }: { section: WorkspaceSection }) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <FolderKanban className="h-4 w-4 text-muted-foreground" />
          <div className="text-card-title font-medium">{section.label}</div>
          {section.status ? <Badge>{section.status}</Badge> : null}
        </div>
        <div className="mt-1 text-body-sm text-muted-foreground">{section.description}</div>
      </CardHeader>
      <CardContent className="grid min-h-48 place-items-center bg-surface-2 text-center">
        <div className="max-w-md">
          <div className="text-card-title font-medium">Ready for implementation</div>
          <p className="mt-2 text-body-sm text-muted-foreground">
            This workspace section is wired to the tenant context and can receive grids, forms or operational controls in the next pass.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}

export function WorkspacePage({
  payload,
  backHref,
  backLabel,
  initialTab,
  feedback
}: {
  payload: WorkspacePayload;
  backHref: string;
  backLabel: string;
  initialTab?: string;
  feedback?: Feedback | null;
}) {
  const initialSectionId = useMemo(() => {
    const fallback = payload.sections[0]?.id ?? "overview";
    return payload.sections.some((section) => section.id === initialTab) ? String(initialTab) : fallback;
  }, [initialTab, payload.sections]);
  const [activeSectionId, setActiveSectionId] = useState(initialSectionId);
  const activeSection = payload.sections.find((section) => section.id === activeSectionId) ?? payload.sections[0];

  function selectSection(sectionId: string) {
    setActiveSectionId(sectionId);
    const url = new URL(window.location.href);
    url.searchParams.set("tab", sectionId);
    url.searchParams.delete("feedback");
    url.searchParams.delete("message");
    window.history.replaceState(null, "", url.toString());
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col justify-between gap-4 md:flex-row md:items-start">
        <div className="min-w-0">
          <Button asChild variant="ghost" className="mb-3 px-0">
            <Link href={backHref}>
              <ArrowLeft className="h-4 w-4" />
              {backLabel}
            </Link>
          </Button>
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <Badge>{payload.workspace.status}</Badge>
            <Badge>{payload.subject.status}</Badge>
            {payload.subject.badges.map((badge) => (
              <Badge key={badge}>{badge}</Badge>
            ))}
          </div>
          <h1 className="truncate text-page-title font-light">{payload.subject.title}</h1>
          {payload.subject.subtitle ? (
            <p className="mt-2 max-w-3xl text-page-subtitle text-muted-foreground">{payload.subject.subtitle}</p>
          ) : null}
        </div>
        <div className="grid grid-cols-2 gap-2 text-body-sm md:grid-cols-4">
          {payload.summary.map((item) => (
            <div key={item.label} className="rounded-md border border-border-2 bg-card px-3 py-2">
              <div className={cn("font-mono text-lg font-medium", item.tone && toneClasses[item.tone])}>{item.value}</div>
              <div className="text-meta text-muted-foreground">{item.label}</div>
            </div>
          ))}
        </div>
      </div>

      {feedback ? (
        <Alert variant={feedback.type} title={feedback.type === "error" ? "Could not save" : "Operation completed"}>
          {feedback.message}
        </Alert>
      ) : null}

      <div className="rounded-md border border-border-2 bg-card px-4 py-3">
        <Tabs
          items={payload.sections.map((section) => ({ id: section.id, label: section.label }))}
          value={activeSectionId}
          onValueChange={selectSection}
          className="max-w-full overflow-x-auto"
        />
      </div>

      {activeSection ? <PlaceholderSection section={activeSection} /> : null}
    </div>
  );
}
