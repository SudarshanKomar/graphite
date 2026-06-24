"use client";

import { AlertTriangle, CheckCircle2 } from "lucide-react";
import { useStore } from "@/lib/store";
import type { MutationLogEntry } from "@/lib/types";

function describe(m: MutationLogEntry): string {
  const type = (m.mutation_type || m.type || "mutation") as string;
  const skip = new Set(["mutation_type", "type", "timestamp", "result", "ok", "success"]);
  const parts = Object.entries(m)
    .filter(([k, v]) => !skip.has(k) && v !== null && typeof v !== "object")
    .map(([k, v]) => `${k}=${v}`);
  return parts.length ? `${type} · ${parts.join(", ")}` : type;
}

export function ActiveFaults() {
  const mutations = useStore((s) => s.mutations);

  return (
    <div className="panel">
      <div className="panel-head justify-between">
        <span className="eyebrow">Active Faults</span>
        <span className="chip">{mutations.length}</span>
      </div>
      <div className="p-2.5">
        {mutations.length === 0 ? (
          <div className="flex items-center gap-2 px-1 py-1 text-[11px] text-faint">
            <CheckCircle2 className="h-3.5 w-3.5 text-healthy" />
            Baseline — no active faults
          </div>
        ) : (
          <ul className="space-y-1">
            {mutations.map((m, i) => (
              <li
                key={i}
                className="flex items-start gap-2 rounded-lg border border-line bg-surface/60 px-2.5 py-1.5"
              >
                <AlertTriangle className="mt-0.5 h-3 w-3 shrink-0 text-high" />
                <span className="break-all font-mono text-[10.5px] leading-snug text-muted">
                  {describe(m)}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
