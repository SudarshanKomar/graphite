"use client";

import { Hexagon, RotateCcw, Wifi, WifiOff, Sparkles, Eye, Wrench } from "lucide-react";
import { useStore } from "@/lib/store";
import { cn } from "@/lib/utils";

export function Header() {
  const global = useStore((s) => s.global);
  const connected = useStore((s) => s.connected);
  const llm = useStore((s) => s.llmConfigured);
  const reset = useStore((s) => s.resetSim);
  const busy = useStore((s) => s.busy);
  const mode = useStore((s) => s.capabilityMode);
  const setMode = useStore((s) => s.setMode);

  const sites = global?.sites ?? [];
  const totalUsers = sites.reduce((a, s) => a + s.total_users, 0);
  const impacted = sites.filter((s) => s.health !== "healthy").length;
  const devicesDown = sites.reduce((a, s) => a + s.devices_down, 0);

  const isOperate = mode === "operate";

  return (
    <header
      className={cn(
        "flex h-14 shrink-0 items-center justify-between border-b bg-surface/80 px-4 backdrop-blur-sm",
        isOperate ? "border-high/40" : "border-line",
      )}
    >
      {/* Brand */}
      <div className="flex items-center gap-2.5 shrink-0">
        <div className="relative flex h-8 w-8 items-center justify-center">
          <Hexagon className="h-8 w-8 text-signal" strokeWidth={1.4} />
          <span className="absolute h-1.5 w-1.5 rounded-full bg-signal shadow-[0_0_10px_rgba(51,230,176,0.9)]" />
        </div>
        <div className="leading-tight hidden sm:block">
          <div className="font-mono text-[15px] font-semibold tracking-[0.18em] text-ink">
            GRAPHITE
          </div>
          <div className="text-[10px] tracking-wide text-faint">
            Network Operations Copilot
          </div>
        </div>
      </div>

      {/* Global status — wraps on narrow screens */}
      <div className="hidden items-center gap-3 lg:flex xl:gap-5">
        <Stat label="sites" value={String(sites.length)} />
        <Divider />
        <Stat label="users" value={totalUsers.toLocaleString()} />
        <Divider />
        <Stat
          label="impacted"
          value={String(impacted)}
          tone={impacted ? "high" : "ok"}
        />
        <Divider />
        <Stat
          label="devices down"
          value={String(devicesDown)}
          tone={devicesDown ? "critical" : "ok"}
        />
      </div>

      {/* Controls */}
      <div className="flex items-center gap-2 shrink-0">
        {/* V2: Observe / Operate mode toggle */}
        <button
          onClick={() => setMode(isOperate ? "observe" : "operate")}
          className={cn(
            "flex items-center gap-1.5 rounded-md border px-2 py-1 text-[10px] font-mono font-semibold transition",
            isOperate
              ? "border-high/50 bg-high/10 text-high hover:bg-high/20"
              : "border-signal/30 bg-signal/10 text-signal hover:bg-signal/20",
          )}
          title={isOperate
            ? "OPERATE mode — agent can mutate topology. Click to switch to observe."
            : "OBSERVE mode — agent is read-only. Click to switch to operate."
          }
        >
          {isOperate ? <Wrench className="h-3 w-3" /> : <Eye className="h-3 w-3" />}
          {isOperate ? "Operate" : "Observe"}
        </button>

        <span
          className={cn(
            "hidden sm:flex items-center gap-1.5 rounded-md border px-2 py-1 text-[10px] font-mono",
            llm
              ? "border-signal/30 bg-signal/10 text-signal"
              : "border-line bg-elevated text-faint",
          )}
          title={llm ? "Gemini agent online" : "LLM not configured (set GEMINI_API_KEY)"}
        >
          <Sparkles className="h-3 w-3" /> {llm ? "AI" : "offline"}
        </span>
        <span
          className={cn(
            "hidden md:flex items-center gap-1.5 rounded-md border px-2 py-1 text-[10px] font-mono",
            connected
              ? "border-healthy/30 bg-healthy/10 text-healthy"
              : "border-critical/30 bg-critical/10 text-critical",
          )}
        >
          {connected ? <Wifi className="h-3 w-3" /> : <WifiOff className="h-3 w-3" />}
          {connected ? "connected" : "offline"}
        </span>
        <button onClick={() => reset()} disabled={busy} className="btn h-8 px-3 text-xs">
          <RotateCcw className={cn("h-3.5 w-3.5", busy && "animate-spin")} /> Reset
        </button>
      </div>
    </header>
  );
}

function Stat({
  label,
  value,
  tone = "default",
}: {
  label: string;
  value: string;
  tone?: "default" | "ok" | "high" | "critical";
}) {
  const color =
    tone === "critical"
      ? "text-critical"
      : tone === "high"
        ? "text-high"
        : tone === "ok"
          ? "text-healthy"
          : "text-ink";
  return (
    <div className="text-center">
      <div className={cn("font-mono text-sm font-semibold leading-none", color)}>
        {value}
      </div>
      <div className="mt-1 text-[9px] uppercase tracking-wider text-faint">{label}</div>
    </div>
  );
}

function Divider() {
  return <span className="h-6 w-px bg-line" />;
}
