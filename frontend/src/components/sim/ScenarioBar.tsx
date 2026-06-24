"use client";

import { useState } from "react";
import { PlayCircle } from "lucide-react";
import { useStore } from "@/lib/store";

interface Scenario {
  id: string;
  label: string;
  detail: string;
  run: (s: ReturnType<typeof useStore.getState>) => Promise<void>;
}

const SCENARIOS: Scenario[] = [
  {
    id: "vlan",
    label: "Remove VLAN 420",
    detail: "Bangalore · Corp WiFi",
    run: async (s) => {
      await s.resetSim();
      await s.openSite("bangalore");
      await s.injectFault("remove_vlan", { vlan_id: 420, site: "bangalore" });
      await s.showBlastFor("blr-vlan-420", "VLAN 420 @ bangalore");
    },
  },
  {
    id: "leaf",
    label: "Disable sg-leaf-03",
    detail: "Singapore · DB leaf",
    run: async (s) => {
      await s.resetSim();
      await s.openSite("singapore");
      await s.injectFault("disable_device", { device_id: "sg-leaf-03" });
      await s.showBlastFor("sg-leaf-03", "sg-leaf-03");
    },
  },
  {
    id: "latency",
    label: "BLR–SG latency 500ms",
    detail: "WAN degradation",
    run: async (s) => {
      await s.resetSim();
      s.backToGlobal();
      await s.injectFault("set_link_latency", {
        source: "blr-edge-01",
        target: "sg-edge-01",
        latency_ms: 500,
      });
    },
  },
];

export function ScenarioBar() {
  const [running, setRunning] = useState<string | null>(null);

  async function go(scn: Scenario) {
    setRunning(scn.id);
    try {
      await scn.run(useStore.getState());
    } finally {
      setRunning(null);
    }
  }

  return (
    <div className="panel">
      <div className="panel-head">
        <span className="eyebrow">Demo Scenarios</span>
      </div>
      <div className="space-y-1.5 p-2.5">
        {SCENARIOS.map((scn) => (
          <button
            key={scn.id}
            onClick={() => go(scn)}
            disabled={running !== null}
            className="group flex w-full items-center gap-2.5 rounded-lg border border-line bg-surface/60 px-2.5 py-2 text-left transition hover:border-signal/40 hover:bg-elevated disabled:opacity-50"
          >
            <PlayCircle className="h-4 w-4 shrink-0 text-signal" />
            <div className="min-w-0 flex-1">
              <div className="truncate text-[12px] font-medium text-ink">{scn.label}</div>
              <div className="truncate text-[10px] text-faint">{scn.detail}</div>
            </div>
            {running === scn.id && (
              <span className="h-3 w-3 animate-spin rounded-full border-2 border-line border-t-signal" />
            )}
          </button>
        ))}
      </div>
    </div>
  );
}
