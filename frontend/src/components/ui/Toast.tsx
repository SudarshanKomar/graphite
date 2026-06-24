"use client";

import { useEffect } from "react";
import { AlertTriangle, X } from "lucide-react";
import { useStore } from "@/lib/store";

export function Toast() {
  const error = useStore((s) => s.error);
  const setError = useStore((s) => s.setError);

  useEffect(() => {
    if (!error) return;
    const t = setTimeout(() => setError(null), 6000);
    return () => clearTimeout(t);
  }, [error, setError]);

  if (!error) return null;

  return (
    <div className="pointer-events-none fixed bottom-5 left-1/2 z-50 -translate-x-1/2 animate-fade-up">
      <div className="pointer-events-auto flex max-w-md items-start gap-2.5 rounded-xl border border-critical/40 bg-panel px-4 py-3 shadow-glow-critical">
        <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-critical" />
        <p className="text-sm text-ink">{error}</p>
        <button
          onClick={() => setError(null)}
          className="ml-1 text-faint transition hover:text-ink"
          aria-label="Dismiss"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
