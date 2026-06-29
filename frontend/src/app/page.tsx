"use client";

import { useCallback, useEffect, useRef } from "react";
import { ReactFlowProvider } from "@xyflow/react";
import { useStore } from "@/lib/store";
import { Header } from "@/components/console/Header";
import { LeftRail } from "@/components/console/LeftRail";
import { CopilotPanel } from "@/components/copilot/CopilotPanel";
import { TopologyCanvas } from "@/components/topology/TopologyCanvas";
import { Toast } from "@/components/ui/Toast";

function PanelSeparator({ onDrag }: { onDrag: (deltaX: number) => void }) {
  const dragging = useRef(false);
  const lastX = useRef(0);

  const onMouseDown = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      dragging.current = true;
      lastX.current = e.clientX;
      const onMove = (ev: MouseEvent) => {
        if (!dragging.current) return;
        const dx = ev.clientX - lastX.current;
        lastX.current = ev.clientX;
        onDrag(dx);
      };
      const onUp = () => {
        dragging.current = false;
        window.removeEventListener("mousemove", onMove);
        window.removeEventListener("mouseup", onUp);
      };
      window.addEventListener("mousemove", onMove);
      window.addEventListener("mouseup", onUp);
    },
    [onDrag],
  );

  return (
    <div
      onMouseDown={onMouseDown}
      className="group relative z-10 flex w-1 shrink-0 cursor-col-resize items-center justify-center"
    >
      <div className="h-full w-px bg-line transition group-hover:bg-signal/40 group-active:bg-signal/60" />
    </div>
  );
}

export default function ConsolePage() {
  const init = useStore((s) => s.init);
  const leftWidth = useStore((s) => s.leftWidth);
  const rightWidth = useStore((s) => s.rightWidth);

  useEffect(() => {
    void init();
  }, [init]);

  // Read live width from store inside drag handler (avoids stale closure capture).
  const onLeftDrag = useCallback(
    (dx: number) => {
      const w = useStore.getState().leftWidth;
      useStore.getState().setLeftWidth(w + dx);
    },
    [],
  );
  const onRightDrag = useCallback(
    (dx: number) => {
      const w = useStore.getState().rightWidth;
      useStore.getState().setRightWidth(w - dx);
    },
    [],
  );

  return (
    <div className="flex h-screen w-screen flex-col overflow-hidden">
      <Header />
      <div className="flex min-h-0 flex-1">
        <div style={{ width: leftWidth, minWidth: 220, maxWidth: 400, flexShrink: 0 }}>
          <LeftRail />
        </div>
        <PanelSeparator onDrag={onLeftDrag} />
        <main className="relative min-w-0 flex-1">
          <ReactFlowProvider>
            <TopologyCanvas />
          </ReactFlowProvider>
        </main>
        <PanelSeparator onDrag={onRightDrag} />
        <div style={{ width: rightWidth, minWidth: 300, maxWidth: 600, flexShrink: 0 }}>
          <CopilotPanel />
        </div>
      </div>
      <Toast />
    </div>
  );
}
