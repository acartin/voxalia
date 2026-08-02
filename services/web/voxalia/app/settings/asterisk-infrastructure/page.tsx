import { notFound } from "next/navigation";
import { AppShell } from "@/components/portal/app-shell";
import { AsteriskInfrastructurePlaceholder } from "@/components/workspace/asterisk-infrastructure-placeholder";
import { getAsteriskCarriers, getAsteriskInstances, getAsteriskTrunks, getMenu } from "@/lib/api";

const currentPath = "/settings/asterisk-infrastructure";

export default async function AsteriskInfrastructurePage() {
  const [menu, trunksPayload, carriersPayload, instancesPayload] = await Promise.all([
    getMenu(),
    getAsteriskTrunks(),
    getAsteriskCarriers(),
    getAsteriskInstances()
  ]);
  const allowed = menu.sections.some((section) => section.items.some((item) => item.href === currentPath));
  if (!allowed) notFound();

  return (
    <AppShell menu={menu} currentPath={currentPath}>
      <AsteriskInfrastructurePlaceholder
        trunksPayload={trunksPayload}
        carriersPayload={carriersPayload}
        instancesPayload={instancesPayload}
      />
    </AppShell>
  );
}
