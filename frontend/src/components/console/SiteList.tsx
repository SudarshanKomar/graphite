"use client";

import { ChevronRight } from "lucide-react";
import { useStore } from "@/lib/store";
import { cn } from "@/lib/utils";
import { HealthDot } from "@/components/ui/primitives";

export function SiteList() {
  const global = useStore((s) => s.global);
  const openSite = useStore((s) => s.openSite);
  const selectedSite = useStore((s) => s.selectedSite);
  const view = useStore((s) => s.view);
  const sites = global?.sites ?? [];

  return (
    <div className="panel">
      <div className="panel-head">
        <span className="eyebrow">Sites</span>
      </div>
      <div className="space-y-1 p-2">
        {sites.map((site) => {
          const active = view === "site" && selectedSite === site.site;
          return (
            <button
              key={site.site}
              onClick={() => openSite(site.site)}
              className={cn(
                "group flex w-full items-center gap-2.5 rounded-lg border px-2.5 py-2 text-left transition",
                active
                  ? "border-signal/40 bg-signal/5"
                  : "border-transparent hover:border-line hover:bg-elevated/60",
              )}
            >
              <HealthDot health={site.health} />
              <div className="min-w-0 flex-1">
                <div className="truncate text-[13px] font-medium text-ink">{site.name}</div>
                <div className="font-mono text-[10px] text-faint">
                  {site.device_count} devices · {site.total_users.toLocaleString()} users
                </div>
              </div>
              {site.devices_down > 0 && (
                <span className="rounded bg-critical/15 px-1 font-mono text-[9px] font-semibold text-critical">
                  {site.devices_down}↓
                </span>
              )}
              <ChevronRight className="h-3.5 w-3.5 text-faint transition group-hover:translate-x-0.5 group-hover:text-muted" />
            </button>
          );
        })}
      </div>
    </div>
  );
}
