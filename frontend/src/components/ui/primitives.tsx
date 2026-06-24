"use client";

import { cn } from "@/lib/utils";
import type { Health, Severity, Status } from "@/lib/types";

export const SEVERITY_COLOR: Record<Severity, string> = {
  critical: "text-critical border-critical/40 bg-critical/10",
  high: "text-high border-high/40 bg-high/10",
  medium: "text-medium border-medium/40 bg-medium/10",
  low: "text-low border-low/40 bg-low/10",
};

const HEALTH_DOT: Record<Health, string> = {
  healthy: "bg-healthy shadow-[0_0_8px_rgba(63,185,80,0.7)]",
  degraded: "bg-high shadow-[0_0_8px_rgba(240,136,62,0.7)]",
  critical: "bg-critical shadow-[0_0_10px_rgba(248,81,73,0.8)]",
};

export function HealthDot({ health, className }: { health: Health; className?: string }) {
  return (
    <span
      className={cn("inline-block h-2 w-2 rounded-full", HEALTH_DOT[health], className)}
      aria-label={health}
    />
  );
}

export function SeverityBadge({ severity }: { severity: Severity }) {
  return (
    <span
      className={cn(
        "rounded-md border px-1.5 py-0.5 text-[10px] font-mono font-semibold uppercase tracking-wide",
        SEVERITY_COLOR[severity],
      )}
    >
      {severity}
    </span>
  );
}

const STATUS_STYLE: Record<string, string> = {
  up: "text-healthy",
  active: "text-healthy",
  down: "text-critical",
  removed: "text-critical",
  degraded: "text-high",
};

export function StatusPill({ status }: { status: Status }) {
  const ok = status === "up" || status === "active";
  return (
    <span className={cn("inline-flex items-center gap-1 text-[11px] font-mono", STATUS_STYLE[status] ?? "text-muted")}>
      <span className={cn("h-1.5 w-1.5 rounded-full", ok ? "bg-healthy" : status === "degraded" ? "bg-high" : "bg-critical")} />
      {status}
    </span>
  );
}

export function Spinner({ className }: { className?: string }) {
  return (
    <span
      className={cn(
        "inline-block h-3.5 w-3.5 animate-spin rounded-full border-2 border-line border-t-signal",
        className,
      )}
    />
  );
}

export function Section({
  title,
  right,
  children,
  className,
}: {
  title: string;
  right?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("panel", className)}>
      <div className="panel-head justify-between">
        <span className="eyebrow">{title}</span>
        {right}
      </div>
      <div className="p-3">{children}</div>
    </div>
  );
}
