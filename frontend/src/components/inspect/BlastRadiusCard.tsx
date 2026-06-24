"use client";

import { Radar, Users, Server, Boxes, X } from "lucide-react";
import { useStore } from "@/lib/store";
import { SeverityBadge } from "@/components/ui/primitives";

export function BlastRadiusCard() {
  const blast = useStore((s) => s.blast);
  const label = useStore((s) => s.blastLabel);
  const clearBlast = useStore((s) => s.clearBlast);
  if (!blast) return null;

  const down = blast.affected_devices.filter(
    (d) => d.impact === "down" || d.impact === "isolated",
  ).length;

  return (
    <div className="panel overflow-hidden">
      <div className="panel-head justify-between bg-critical/5">
        <span className="flex items-center gap-1.5 text-xs font-semibold text-critical">
          <Radar className="h-3.5 w-3.5" /> Blast Radius
        </span>
        <div className="flex items-center gap-2">
          <SeverityBadge severity={blast.severity} />
          <button onClick={clearBlast} className="text-faint hover:text-ink" aria-label="Clear">
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>

      <div className="space-y-3 p-3">
        <div className="font-mono text-[11px] text-muted">
          source: <span className="text-ink">{label ?? blast.component_id}</span>
        </div>

        <div className="grid grid-cols-3 gap-2">
          <Metric icon={<Users className="h-3.5 w-3.5" />} value={blast.total_users_affected.toLocaleString()} label="users" tone="critical" />
          <Metric icon={<Boxes className="h-3.5 w-3.5" />} value={String(down)} label="devices" tone="high" />
          <Metric icon={<Server className="h-3.5 w-3.5" />} value={String(blast.affected_services.length)} label="services" tone="muted" />
        </div>

        {blast.affected_services.length > 0 && (
          <div>
            <div className="eyebrow mb-1.5">Affected services</div>
            <div className="space-y-1">
              {blast.affected_services.slice(0, 5).map((s) => (
                <div key={s.id} className="flex items-center justify-between text-[11px]">
                  <span className="truncate text-ink">{s.name}</span>
                  <span className={s.impact === "down" ? "text-critical" : "text-high"}>
                    {s.impact}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {blast.severity_factors.length > 0 && (
          <div className="rounded-lg border border-line bg-surface/60 p-2">
            <div className="eyebrow mb-1">Why this severity</div>
            <ul className="space-y-0.5">
              {blast.severity_factors.map((f, i) => (
                <li key={i} className="text-[10.5px] leading-snug text-muted">· {f}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}

function Metric({
  icon,
  value,
  label,
  tone,
}: {
  icon: React.ReactNode;
  value: string;
  label: string;
  tone: "critical" | "high" | "muted";
}) {
  const color =
    tone === "critical" ? "text-critical" : tone === "high" ? "text-high" : "text-ink";
  return (
    <div className="rounded-lg border border-line bg-surface/60 p-2 text-center">
      <div className={`flex items-center justify-center ${color}`}>{icon}</div>
      <div className={`mt-1 font-mono text-base font-semibold ${color}`}>{value}</div>
      <div className="text-[9px] uppercase tracking-wider text-faint">{label}</div>
    </div>
  );
}
