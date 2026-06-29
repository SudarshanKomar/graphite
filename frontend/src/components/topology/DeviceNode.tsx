"use client";

import { memo, useState } from "react";
import { Handle, Position, type NodeProps } from "@xyflow/react";
import { Users, ChevronDown } from "lucide-react";
import { deviceMeta } from "@/lib/deviceMeta";
import { cn } from "@/lib/utils";
import type { SiteDevice, EndpointGroup } from "@/lib/types";

export interface DeviceNodeData {
  device: SiteDevice;
  impact: "down" | "isolated" | "degraded" | null;
  isSource: boolean;
  endpointInfo: { users: number; groups: EndpointGroup[] } | null;
  [key: string]: unknown;
}

const DEVICE_LABELS: Record<string, string> = {
  smartphones: "Smartphones",
  laptops: "Laptops",
  desktops: "Desktops",
  tablets: "Tablets",
  printers: "Printers",
  iot: "IoT devices",
  voip_phones: "VoIP phones",
  conference_phones: "Conf. phones",
};

function DeviceNodeImpl({ data, selected }: NodeProps) {
  const d = data as unknown as DeviceNodeData;
  const { device, impact, isSource, endpointInfo } = d;
  const meta = deviceMeta(device.device_type);
  const Icon = meta.icon;
  const [expanded, setExpanded] = useState(false);

  const down = device.status === "down" || device.status === "removed";
  const degraded = device.status === "degraded";

  return (
    <div
      className={cn(
        "group relative w-[154px] select-none rounded-xl border bg-elevated/95 px-3 py-2.5 transition",
        "shadow-[0_6px_20px_-10px_rgba(0,0,0,0.8)]",
        down
          ? "border-critical/70"
          : degraded
            ? "border-high/60"
            : "border-line hover:border-edge",
        selected && "ring-2 ring-signal/70",
        impact && (impact === "degraded" ? "ring-2 ring-high/70" : "ring-2 ring-critical/70 animate-pulse-ring"),
      )}
    >
      <Handle type="target" position={Position.Top} />
      <Handle type="source" position={Position.Bottom} />

      <div className="flex items-center gap-2">
        <span
          className={cn(
            "flex h-7 w-7 shrink-0 items-center justify-center rounded-lg border",
            down
              ? "border-critical/40 bg-critical/10 text-critical"
              : degraded
                ? "border-high/40 bg-high/10 text-high"
                : "border-signal/30 bg-signal/10 text-signal",
          )}
        >
          <Icon className="h-3.5 w-3.5" />
        </span>
        <div className="min-w-0">
          <div className="truncate font-mono text-[12px] font-medium text-ink">
            {device.id}
          </div>
          <div className="truncate text-[10px] text-faint">{meta.label}</div>
        </div>
      </div>

      <div className="mt-2 flex items-center justify-between">
        <span
          className={cn(
            "inline-flex items-center gap-1 text-[10px] font-mono",
            down ? "text-critical" : degraded ? "text-high" : "text-healthy",
          )}
        >
          <span
            className={cn(
              "h-1.5 w-1.5 rounded-full",
              down ? "bg-critical" : degraded ? "bg-high" : "bg-healthy",
            )}
          />
          {device.status}
        </span>
        {isSource && (
          <span className="rounded bg-critical/15 px-1 text-[9px] font-mono font-semibold uppercase text-critical">
            fault
          </span>
        )}
      </div>

      {/* V2.1.1: User badge for access-layer devices serving endpoint groups */}
      {endpointInfo && endpointInfo.users > 0 && (
        <button
          onClick={(e) => { e.stopPropagation(); setExpanded(!expanded); }}
          className="mt-1.5 flex w-full items-center justify-between rounded-md border border-line bg-surface/60 px-1.5 py-1 text-[10px] transition hover:border-edge"
        >
          <span className="flex items-center gap-1 font-mono text-muted">
            <Users className="h-3 w-3 text-signal/80" />
            <span className="text-ink font-semibold">{endpointInfo.users.toLocaleString()}</span>
            <span>users</span>
          </span>
          <ChevronDown className={cn("h-3 w-3 text-faint transition", expanded && "rotate-180")} />
        </button>
      )}

      {/* Expandable device breakdown */}
      {expanded && endpointInfo && (
        <div className="mt-1 animate-fade-up rounded-md border border-line bg-surface/80 p-1.5">
          {endpointInfo.groups.map((eg) => (
            <div key={eg.id} className="mb-1 last:mb-0">
              <div className="text-[9px] font-mono text-faint truncate">{eg.zone}</div>
              <div className="flex flex-wrap gap-x-2 gap-y-0.5">
                {Object.entries(eg.device_breakdown).map(([type, count]) => (
                  <span key={type} className="text-[9px] text-muted">
                    <span className="text-ink font-mono">{count}</span>{" "}
                    {DEVICE_LABELS[type] ?? type}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export const DeviceNode = memo(DeviceNodeImpl);
