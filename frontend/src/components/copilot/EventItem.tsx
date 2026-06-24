"use client";

import { useState } from "react";
import {
  Brain,
  Wrench,
  ClipboardList,
  ChevronRight,
  CircleCheckBig,
  TriangleAlert,
  Users,
  Server,
  Boxes,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { SeverityBadge } from "@/components/ui/primitives";
import type { AgentEvent } from "@/lib/types";

export function EventItem({ event }: { event: AgentEvent }) {
  if (event.type === "thought") return <Thought content={event.content} />;
  if (event.type === "tool_call")
    return <ToolCall name={event.tool_name} params={event.parameters} />;
  if (event.type === "tool_result")
    return <ToolResult name={event.tool_name} result={event.result} />;
  if (event.type === "final_answer") return <FinalAnswer event={event} />;
  if (event.type === "error") return <ErrorBlock message={event.message} />;
  return null;
}

function Thought({ content }: { content: string }) {
  return (
    <div className="flex gap-2 px-1 py-1.5 text-[12px] leading-relaxed text-muted">
      <Brain className="mt-0.5 h-3.5 w-3.5 shrink-0 text-signal/80" />
      <p className="italic">{content}</p>
    </div>
  );
}

function ToolCall({ name, params }: { name: string; params: Record<string, unknown> }) {
  return (
    <div className="rounded-lg border border-line bg-surface/60 px-2.5 py-1.5">
      <div className="flex items-center gap-1.5 text-[11px]">
        <Wrench className="h-3 w-3 text-low" />
        <span className="font-mono text-low">{name}</span>
        <span className="font-mono text-faint">
          ({Object.entries(params).map(([k, v]) => `${k}: ${JSON.stringify(v)}`).join(", ")})
        </span>
      </div>
    </div>
  );
}

function ToolResult({ name, result }: { name: string; result: Record<string, unknown> }) {
  const [open, setOpen] = useState(false);
  const err = (result as { error?: string }).error;
  return (
    <div className="rounded-lg border border-line bg-surface/40">
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center gap-1.5 px-2.5 py-1.5 text-left text-[11px]"
      >
        <ChevronRight className={cn("h-3 w-3 text-faint transition", open && "rotate-90")} />
        <ClipboardList className="h-3 w-3 text-faint" />
        <span className="font-mono text-muted">{name}</span>
        {err ? (
          <span className="ml-auto font-mono text-[10px] text-critical">{err}</span>
        ) : (
          <span className="ml-auto font-mono text-[10px] text-faint">result</span>
        )}
      </button>
      {open && (
        <pre className="max-h-52 overflow-auto border-t border-line px-2.5 py-2 font-mono text-[10px] leading-relaxed text-muted">
          {JSON.stringify(result, null, 2)}
        </pre>
      )}
    </div>
  );
}

function FinalAnswer({ event }: { event: Extract<AgentEvent, { type: "final_answer" }> }) {
  const users = event.affected_components?.users;
  return (
    <div className="animate-fade-up rounded-xl border border-signal/30 bg-signal/[0.04] p-3 shadow-glow">
      <div className="mb-2 flex items-center justify-between">
        <span className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-signal">
          <CircleCheckBig className="h-3.5 w-3.5" /> Conclusion
        </span>
        <div className="flex items-center gap-2">
          <SeverityBadge severity={event.severity} />
          <span className="font-mono text-[10px] text-muted">
            {Math.round((event.confidence ?? 0) * 100)}% conf
          </span>
        </div>
      </div>

      <p className="text-[13px] font-medium leading-snug text-ink">{event.summary}</p>

      {event.root_cause && (
        <div className="mt-2.5">
          <div className="eyebrow mb-1">Root cause</div>
          <p className="text-[12px] leading-relaxed text-muted">{event.root_cause}</p>
        </div>
      )}

      <div className="mt-2.5 flex flex-wrap gap-2">
        {users && (
          <Tag icon={<Users className="h-3 w-3" />}>{users.count?.toLocaleString()} users</Tag>
        )}
        {event.affected_components?.devices && (
          <Tag icon={<Boxes className="h-3 w-3" />}>
            {event.affected_components.devices.length} devices
          </Tag>
        )}
        {event.affected_components?.services && (
          <Tag icon={<Server className="h-3 w-3" />}>
            {event.affected_components.services.length} services
          </Tag>
        )}
      </div>

      {event.remediation?.length > 0 && (
        <div className="mt-3">
          <div className="eyebrow mb-1.5">Remediation</div>
          <ol className="space-y-1">
            {event.remediation.map((r, i) => (
              <li key={i} className="flex gap-2 text-[12px] leading-snug text-muted">
                <span className="font-mono text-signal">{i + 1}.</span>
                <span>{r}</span>
              </li>
            ))}
          </ol>
        </div>
      )}
    </div>
  );
}

function Tag({ icon, children }: { icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <span className="inline-flex items-center gap-1 rounded-md border border-line bg-elevated/60 px-1.5 py-0.5 text-[10.5px] font-mono text-muted">
      {icon}
      {children}
    </span>
  );
}

function ErrorBlock({ message }: { message: string }) {
  return (
    <div className="flex gap-2 rounded-lg border border-critical/40 bg-critical/10 px-2.5 py-2 text-[12px] text-critical">
      <TriangleAlert className="mt-0.5 h-3.5 w-3.5 shrink-0" />
      <span>{message}</span>
    </div>
  );
}
