"use client";

import { useEffect } from "react";
import { ReactFlowProvider } from "@xyflow/react";
import { useStore } from "@/lib/store";
import { Header } from "@/components/console/Header";
import { LeftRail } from "@/components/console/LeftRail";
import { CopilotPanel } from "@/components/copilot/CopilotPanel";
import { TopologyCanvas } from "@/components/topology/TopologyCanvas";
import { Toast } from "@/components/ui/Toast";

export default function ConsolePage() {
  const init = useStore((s) => s.init);

  useEffect(() => {
    void init();
  }, [init]);

  return (
    <div className="flex h-screen w-screen flex-col overflow-hidden">
      <Header />
      <div className="flex min-h-0 flex-1">
        <LeftRail />
        <main className="relative min-w-0 flex-1">
          <ReactFlowProvider>
            <TopologyCanvas />
          </ReactFlowProvider>
        </main>
        <CopilotPanel />
      </div>
      <Toast />
    </div>
  );
}
