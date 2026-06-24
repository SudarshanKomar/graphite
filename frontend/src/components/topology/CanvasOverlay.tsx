"use client";

import { ChevronLeft, Globe2, Radar, Loader2 } from "lucide-react";
import { useStore } from "@/lib/store";
import { cn } from "@/lib/utils";
import { BlastRadiusCard } from "@/components/inspect/BlastRadiusCard";

function Legend() {
  const items = [
    { c: "bg-healthy", l: "healthy" },
    { c: "bg-high", l: "degraded" },
    { c: "bg-critical", l: "down / fault" },
  ];
  return (
    <div className="flex items-center gap-3 rounded-lg border border-line bg-panel/85 px-3 py-1.5 backdrop-blur-sm">
      {items.map((i) => (
        <span key={i.l} className="flex items-center gap-1.5 text-[10px] font-mono text-muted">
          <span className={cn("h-2 w-2 rounded-full", i.c)} />
          {i.l}
        </span>
      ))}
    </div>
  );
}

export function CanvasOverlay() {
  const view = useStore((s) => s.view);
  const global = useStore((s) => s.global);
  const siteTopology = useStore((s) => s.siteTopology);
  const backToGlobal = useStore((s) => s.backToGlobal);
  const blast = useStore((s) => s.blast);
  const showBlast = useStore((s) => s.showBlast);
  const toggleBlast = useStore((s) => s.toggleBlast);
  const connected = useStore((s) => s.connected);

  return (
    <>
      {/* Breadcrumb / title */}
      <div className="pointer-events-none absolute left-4 top-4 z-10">
        <div className="pointer-events-auto flex items-center gap-2">
          {view === "site" ? (
            <button onClick={backToGlobal} className="btn h-8 px-2.5 text-xs">
              <ChevronLeft className="h-3.5 w-3.5" /> Global
            </button>
          ) : (
            <span className="flex h-8 items-center gap-2 rounded-lg border border-line bg-panel/85 px-3 text-sm font-medium text-ink backdrop-blur-sm">
              <Globe2 className="h-4 w-4 text-signal" /> Global Network
            </span>
          )}
          {view === "site" && siteTopology && (
            <span className="flex h-8 items-center gap-2 rounded-lg border border-line bg-panel/85 px-3 backdrop-blur-sm">
              <span className="font-mono text-[11px] uppercase tracking-wider text-faint">
                {siteTopology.site}
              </span>
              <span className="text-sm font-medium text-ink">{siteTopology.site_name}</span>
            </span>
          )}
        </div>
      </div>

      {/* Top-right controls */}
      <div className="pointer-events-none absolute right-4 top-4 z-10 flex items-center gap-2">
        {blast && (
          <button
            onClick={toggleBlast}
            className={cn("btn pointer-events-auto h-8 px-2.5 text-xs", showBlast && "btn-danger")}
          >
            <Radar className="h-3.5 w-3.5" />
            {showBlast ? "Hide" : "Show"} blast radius
          </button>
        )}
        <div className="pointer-events-auto">
          <Legend />
        </div>
      </div>

      {/* Blast radius summary card */}
      {showBlast && blast && (
        <div className="absolute right-4 top-16 z-10 w-[300px] animate-fade-up">
          <BlastRadiusCard />
        </div>
      )}

      {/* Connecting / empty state */}
      {!global && (
        <div className="pointer-events-none absolute inset-0 z-0 flex items-center justify-center">
          <div className="flex items-center gap-2 text-sm text-muted">
            <Loader2 className="h-4 w-4 animate-spin text-signal" />
            {connected ? "Loading topology…" : "Connecting to Graphite backend…"}
          </div>
        </div>
      )}
    </>
  );
}
