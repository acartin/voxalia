import { notFound } from "next/navigation";
import { AppShell } from "@/components/portal/app-shell";
import { WebRtcPhoneLab } from "@/components/voice/webrtc-phone-lab";
import { getMenu } from "@/lib/api";

const currentPath = "/voice/webrtc-phone";

export default async function WebRtcPhonePage() {
  const menu = await getMenu();
  const allowed = menu.sections.some((section) => section.items.some((item) => item.href === currentPath));
  if (!allowed) notFound();

  return (
    <AppShell menu={menu} currentPath={currentPath}>
      <WebRtcPhoneLab />
    </AppShell>
  );
}
