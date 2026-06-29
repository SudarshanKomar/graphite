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
    <aside className="flex h-full w-full flex-col gap-3 overflow-y-auto bg-surface/40 p-3">
      {selectedDevice ? <DeviceDetail /> : <SiteList />}
      <ScenarioBar />
      <FaultPanel />
      <ActiveFaults />
    </aside>
  );
}
