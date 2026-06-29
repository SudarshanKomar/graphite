// REST client for the Graphite backend. SSE (POST) streaming lives in
// agentStream.ts because it needs a ReadableStream reader, not EventSource.

import type {
  BlastRadiusResult,
  DeviceInfo,
  GlobalTopology,
  MutateRequest,
  MutationLogEntry,
  SiteTopology,
} from "./types";

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ||
  process.env.NEXT_PUBLIC_API_URL ||
  "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || JSON.stringify(body);
    } catch {
      /* ignore */
    }
    throw new Error(`${res.status} ${detail}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => request<{ status: string; llm_configured: boolean }>("/health"),

  globalTopology: () => request<GlobalTopology>("/topology/global"),

  siteTopology: (site: string) =>
    request<SiteTopology>(`/topology/sites/${site}`),

  deviceInfo: (deviceId: string) =>
    request<DeviceInfo>(`/topology/devices/${deviceId}`),

  blastRadius: (componentId: string) =>
    request<BlastRadiusResult>(`/analysis/blast-radius/${componentId}`),

  mutate: (body: MutateRequest) =>
    request<{ mutation_type: string; result: Record<string, unknown> }>(
      "/simulation/mutate",
      { method: "POST", body: JSON.stringify(body) },
    ),

  reset: () =>
    request<{ status: string; mutations_applied: number }>("/simulation/reset", {
      method: "POST",
    }),

  mutations: () =>
    request<{ mutations: MutationLogEntry[]; total: number }>(
      "/simulation/mutations",
    ),

  diff: () => request<Record<string, unknown>>("/simulation/diff"),

  // V2 capability mode
  getMode: () =>
    request<{ mode: string; mutation_tools_enabled: boolean }>("/agent/mode"),

  setMode: (mode: string) =>
    request<{ previous_mode: string; current_mode: string; mutation_tools_enabled: boolean }>(
      "/agent/mode",
      { method: "POST", body: JSON.stringify({ mode }) },
    ),
};
