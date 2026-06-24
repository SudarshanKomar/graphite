// Streams the agent's ReAct events from POST /agent/query (SSE-formatted body).
// EventSource only supports GET, so we read the response body manually and
// parse "data: {json}\n\n" frames.

import { API_BASE } from "./api";
import type { AgentEvent } from "./types";

export interface AgentStreamHandle {
  cancel: () => void;
}

export function streamAgentQuery(
  query: string,
  onEvent: (event: AgentEvent) => void,
  onClose?: (err?: Error) => void,
): AgentStreamHandle {
  const controller = new AbortController();

  (async () => {
    try {
      const res = await fetch(`${API_BASE}/agent/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, stream: true }),
        signal: controller.signal,
      });

      if (!res.ok) {
        let detail = res.statusText;
        try {
          detail = (await res.json()).detail || detail;
        } catch {
          /* ignore */
        }
        onEvent({ type: "error", message: `${res.status} ${detail}` });
        onClose?.();
        return;
      }
      if (!res.body) {
        onEvent({ type: "error", message: "No response body from agent." });
        onClose?.();
        return;
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      // eslint-disable-next-line no-constant-condition
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        let idx: number;
        while ((idx = buffer.indexOf("\n\n")) !== -1) {
          const frame = buffer.slice(0, idx);
          buffer = buffer.slice(idx + 2);
          const line = frame.split("\n").find((l) => l.startsWith("data:"));
          if (!line) continue;
          const json = line.slice(5).trim();
          if (!json) continue;
          try {
            onEvent(JSON.parse(json) as AgentEvent);
          } catch {
            /* skip malformed frame */
          }
        }
      }
      onClose?.();
    } catch (err) {
      if ((err as Error).name === "AbortError") {
        onClose?.();
        return;
      }
      onEvent({
        type: "error",
        message: `Connection failed: ${(err as Error).message}`,
      });
      onClose?.(err as Error);
    }
  })();

  return { cancel: () => controller.abort() };
}
