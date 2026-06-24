"use client";

import { memo } from "react";
import { Handle, Position, type NodeProps } from "@xyflow/react";
import { Building2, Users, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";
import { HealthDot } from "@/components/ui/primitives";
import type { GlobalSite } from "@/lib/types";

export interface SiteNodeData {
  site: GlobalSite;
  [key: string]: unknown;
}

function SiteNodeImpl({ data }: NodeProps) {
  const { site } = data as unknown as SiteNodeData;
  const critical = site.health === "critical";
  const degraded = site.health === "degraded";

  return (
    <div
      className={cn(
        "group relative w-[208px] cursor-pointer select-none rounded-2xl border bg-panel/95 p-4 transition",
        "hover:-translate-y-0.5",
        critical
          ? "border-critical/70 shadow-glow-critical"
          : degraded
            ? "border-high/50"
            : "border-line hover:border-signal/40",
      )}
    >
      <Handle type="target" position={Position.Left} />
      <Handle type="source" position={Position.Right} />
      <Handle type="target" position={Position.Top} />
      <Handle type="source" position={Position.Bottom} />

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg border border-line bg-elevated text-signal">
            <Building2 className="h-4 w-4" />
          </span>
          <div>
            <div className="text-sm font-semibold text-ink">{site.name}</div>
            <div className="font-mono text-[10px] uppercase tracking-wider text-faint">
              {site.site}
            </div>
          </div>
        </div>
        <HealthDot health={site.health} />
      </div>

      <div className="mt-3 flex items-center justify-between text-[11px]">
        <div className="flex items-center gap-3 font-mono text-muted">
          <span>
            <span className="text-ink">{site.device_count}</span> dev
          </span>
          <span className="flex items-center gap-1">
            <Users className="h-3 w-3" />
            <span className="text-ink">{site.total_users.toLocaleString()}</span>
          </span>
        </div>
        {site.devices_down > 0 && (
          <span className="rounded bg-critical/15 px-1.5 py-0.5 font-mono text-[10px] font-semibold text-critical">
            {site.devices_down} down
          </span>
        )}
      </div>

      <div className="mt-2.5 flex items-center justify-end gap-1 text-[10px] font-medium text-faint opacity-0 transition group-hover:opacity-100">
        inspect site <ChevronRight className="h-3 w-3" />
      </div>
    </div>
  );
}

export const SiteNode = memo(SiteNodeImpl);
