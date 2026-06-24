"use client";

import { useEffect, useRef, useState } from "react";
import { Bot, Send, Square, Sparkles } from "lucide-react";
import { useStore } from "@/lib/store";
import { cn } from "@/lib/utils";
import { EventItem } from "./EventItem";

const SUGGESTIONS = [
  "What happens if VLAN 420 is removed from Bangalore?",
  "Investigate the impact of sg-leaf-03 failing.",
  "Why is the ERP system in Singapore slow from Bangalore?",
];

export function CopilotPanel() {
  const turns = useStore((s) => s.turns);
  const isStreaming = useStore((s) => s.isStreaming);
  const llm = useStore((s) => s.llmConfigured);
  const runAgent = useStore((s) => s.runAgent);
  const cancelAgent = useStore((s) => s.cancelAgent);

  const [input, setInput] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [turns]);

  function submit(text: string) {
    const q = text.trim();
    if (!q || isStreaming) return;
    runAgent(q);
    setInput("");
  }

  return (
    <aside className="flex w-[400px] shrink-0 flex-col border-l border-line bg-surface/50">
      {/* Header */}
      <div className="flex h-12 shrink-0 items-center justify-between border-b border-line px-4">
        <div className="flex items-center gap-2">
          <span className="flex h-6 w-6 items-center justify-center rounded-md border border-signal/30 bg-signal/10 text-signal">
            <Bot className="h-3.5 w-3.5" />
          </span>
          <span className="text-sm font-semibold text-ink">Copilot</span>
          {isStreaming && (
            <span className="flex items-center gap-1 text-[10px] font-mono text-signal">
              <span className="h-1.5 w-1.5 animate-blink rounded-full bg-signal" /> investigating
            </span>
          )}
        </div>
        <span className="eyebrow">ReAct · Gemini</span>
      </div>

      {/* Conversation */}
      <div ref={scrollRef} className="min-h-0 flex-1 space-y-4 overflow-y-auto p-4">
        {turns.length === 0 && <EmptyState onPick={submit} disabled={!llm} />}
        {turns.map((turn) =>
          turn.role === "user" ? (
            <div key={turn.id} className="flex justify-end">
              <div className="max-w-[88%] rounded-xl rounded-br-sm border border-signal/30 bg-signal/10 px-3 py-2 text-[13px] text-ink">
                {turn.text}
              </div>
            </div>
          ) : (
            <div key={turn.id} className="space-y-2">
              {turn.events.map((ev, i) => (
                <EventItem key={i} event={ev} />
              ))}
              {turn.running && turn.events.length === 0 && (
                <div className="flex items-center gap-2 px-1 text-[12px] text-faint">
                  <span className="h-1.5 w-1.5 animate-blink rounded-full bg-signal" />
                  thinking…
                </div>
              )}
            </div>
          ),
        )}
      </div>

      {/* Composer */}
      <div className="shrink-0 border-t border-line p-3">
        {!llm && (
          <p className="mb-2 rounded-lg border border-line bg-elevated/60 px-2.5 py-1.5 text-[11px] text-faint">
            Agent offline — set <span className="font-mono text-muted">GEMINI_API_KEY</span> in the
            backend to enable live investigations.
          </p>
        )}
        <div className="flex items-end gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                submit(input);
              }
            }}
            rows={1}
            placeholder={llm ? "Ask the network copilot…" : "Agent offline"}
            disabled={!llm}
            className="field max-h-28 min-h-[40px] flex-1 resize-none"
          />
          {isStreaming ? (
            <button onClick={cancelAgent} className="btn btn-danger h-10 px-3" title="Stop">
              <Square className="h-3.5 w-3.5" />
            </button>
          ) : (
            <button
              onClick={() => submit(input)}
              disabled={!llm || !input.trim()}
              className="btn btn-signal h-10 px-3"
              title="Send"
            >
              <Send className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
      </div>
    </aside>
  );
}

function EmptyState({
  onPick,
  disabled,
}: {
  onPick: (q: string) => void;
  disabled: boolean;
}) {
  return (
    <div className="flex h-full flex-col items-center justify-center text-center">
      <span className="mb-3 flex h-11 w-11 items-center justify-center rounded-xl border border-signal/30 bg-signal/10 text-signal">
        <Sparkles className="h-5 w-5" />
      </span>
      <p className="text-sm font-medium text-ink">Network Operations Copilot</p>
      <p className="mt-1 max-w-[260px] text-[12px] leading-relaxed text-muted">
        Inject a fault, then ask the copilot to investigate impact, blast radius, and remediation.
      </p>
      <div className="mt-4 w-full space-y-1.5">
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            onClick={() => onPick(s)}
            disabled={disabled}
            className="w-full rounded-lg border border-line bg-surface/60 px-3 py-2 text-left text-[12px] text-muted transition hover:border-signal/40 hover:text-ink disabled:opacity-40"
          >
            {s}
          </button>
        ))}
      </div>
    </div>
  );
}
