"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { AsteriskInstancesCrud } from "@/components/crud/asterisk-instances-crud";
import { CarriersCrud } from "@/components/crud/carriers-crud";
import { SipTrunksCrud } from "@/components/crud/sip-trunks-crud";
import { Tabs } from "@/components/ui/tabs";
import { ModulePayload } from "@/lib/types";

const sections = [
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
  }
];

export function AsteriskInfrastructurePlaceholder({
  trunksPayload,
  carriersPayload,
  instancesPayload
}: {
  trunksPayload: ModulePayload;
  carriersPayload: ModulePayload;
  instancesPayload: ModulePayload;
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

      {activeSectionId === "trunks" ? (
        <SipTrunksCrud payload={trunksPayload} />
      ) : activeSectionId === "carriers" ? (
        <CarriersCrud payload={carriersPayload} />
      ) : (
        <AsteriskInstancesCrud payload={instancesPayload} />
      )}
    </div>
  );
}
