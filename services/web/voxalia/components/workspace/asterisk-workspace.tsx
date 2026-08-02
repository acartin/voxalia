import { WorkspacePage } from "@/components/workspace/workspace-page";
import { Feedback } from "@/lib/feedback";
import { WorkspacePayload } from "@/lib/types";

export function AsteriskWorkspace({
  payload,
  initialTab,
  contextFilter,
  extensionFilter,
  flowFilter,
  queueFilter,
  feedback
}: {
  payload: WorkspacePayload;
  initialTab?: string;
  contextFilter?: string;
  extensionFilter?: string;
  flowFilter?: string;
  queueFilter?: string;
  feedback?: Feedback | null;
}) {
  return (
    <WorkspacePage
      payload={payload}
      backHref="/settings/asterisk"
      backLabel="Asterisk"
      initialTab={initialTab}
      contextFilter={contextFilter}
      extensionFilter={extensionFilter}
      flowFilter={flowFilter}
      queueFilter={queueFilter}
      feedback={feedback}
    />
  );
}
