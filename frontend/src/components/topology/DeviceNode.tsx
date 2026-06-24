"use client";

import { memo } from "react";
import { Handle, Position, type NodeProps } from "@xyflow/react";
import { deviceMeta } from "@/lib/deviceMeta";
import { cn } from "@/lib/utils";
import type { SiteDevice } from "@/lib/types";

export interface DeviceNodeData {
  device: SiteDevice;
  impact: "down" | "isolated" | "degraded" | null;
  isSource: boolean;
  [key: string]: unknown;
}

function DeviceNodeImpl({ data, selected }: NodeProps) {
  const d = data as unknown as DeviceNodeData;
  const { device, impact, isSource } = d;
  const meta = deviceMeta(device.device_type);
  const Icon = meta.icon;

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
    </div>
  );
}

export const DeviceNode = memo(DeviceNodeImpl);
