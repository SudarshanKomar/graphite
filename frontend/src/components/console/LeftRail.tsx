"use client";

import { useStore } from "@/lib/store";
import { SiteList } from "./SiteList";
import { ScenarioBar } from "@/components/sim/ScenarioBar";
import { FaultPanel } from "@/components/sim/FaultPanel";
import { ActiveFaults } from "@/components/sim/ActiveFaults";
import { DeviceDetail } from "@/components/inspect/DeviceDetail";

export function LeftRail() {
  const selectedDevice = useStore((s) => s.selectedDevice);

  return (
    <aside className="flex w-80 shrink-0 flex-col gap-3 overflow-y-auto border-r border-line bg-surface/40 p-3">
      {selectedDevice ? <DeviceDetail /> : <SiteList />}
      <ScenarioBar />
      <FaultPanel />
      <ActiveFaults />
    </aside>
  );
}
