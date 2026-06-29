"use client";

import { create } from "zustand";
import { api } from "./api";
import { streamAgentQuery, type AgentStreamHandle } from "./agentStream";
import type {
  AgentEvent,
  BlastRadiusResult,
  DeviceInfo,
  GlobalTopology,
  MutationLogEntry,
  SiteTopology,
} from "./types";

export interface UserTurn {
  id: string;
  role: "user";
  text: string;
}
export interface AgentTurn {
  id: string;
  role: "agent";
  events: AgentEvent[];
  running: boolean;
}
export type ChatTurn = UserTurn | AgentTurn;

export type CapabilityMode = "observe" | "operate";

interface AppState {
  // connection
  connected: boolean;
  llmConfigured: boolean;
  error: string | null;

  // capability mode (V2)
  capabilityMode: CapabilityMode;

  // panel widths (V2 resizable)
  leftWidth: number;
  rightWidth: number;

  // topology
  view: "global" | "site";
  global: GlobalTopology | null;
  siteTopology: SiteTopology | null;
  selectedSite: string | null;
  selectedDevice: string | null;
  deviceInfo: DeviceInfo | null;

  // simulation
  mutations: MutationLogEntry[];
  busy: boolean;

  // blast radius overlay
  blast: BlastRadiusResult | null;
  blastLabel: string | null;
  showBlast: boolean;

  // copilot
  turns: ChatTurn[];
  isStreaming: boolean;
  _handle: AgentStreamHandle | null;

  // actions
  init: () => Promise<void>;
  loadGlobal: () => Promise<void>;
  openSite: (site: string) => Promise<void>;
  backToGlobal: () => void;
  refresh: () => Promise<void>;
  selectDevice: (id: string | null) => Promise<void>;
  injectFault: (
    mutationType: string,
    parameters: Record<string, unknown>,
  ) => Promise<boolean>;
  resetSim: () => Promise<void>;
  showBlastFor: (componentId: string, label: string) => Promise<void>;
  toggleBlast: () => void;
  clearBlast: () => void;
  setError: (msg: string | null) => void;
  setMode: (mode: CapabilityMode) => Promise<void>;
  setLeftWidth: (w: number) => void;
  setRightWidth: (w: number) => void;
  runAgent: (query: string) => void;
  cancelAgent: () => void;
}

let idCounter = 0;
const nextId = () => `t${++idCounter}-${Date.now()}`;

export const useStore = create<AppState>((set, get) => ({
  connected: false,
  llmConfigured: false,
  error: null,

  capabilityMode: "observe",
  leftWidth: 320,
  rightWidth: 400,

  view: "global",
  global: null,
  siteTopology: null,
  selectedSite: null,
  selectedDevice: null,
  deviceInfo: null,

  mutations: [],
  busy: false,

  blast: null,
  blastLabel: null,
  showBlast: false,

  turns: [],
  isStreaming: false,
  _handle: null,

  init: async () => {
    try {
      const h = await api.health();
      set({ connected: true, llmConfigured: h.llm_configured });
    } catch {
      set({ connected: false });
    }
    // Fetch capability mode from backend
    try {
      const m = await api.getMode();
      set({ capabilityMode: m.mode as CapabilityMode });
    } catch { /* backend may be older — default observe */ }
    await get().loadGlobal();
    await get().refresh();
  },

  loadGlobal: async () => {
    try {
      const global = await api.globalTopology();
      set({ global, connected: true });
    } catch (e) {
      set({ error: (e as Error).message, connected: false });
    }
  },

  openSite: async (site: string) => {
    try {
      const siteTopology = await api.siteTopology(site);
      set({ siteTopology, selectedSite: site, view: "site", selectedDevice: null, deviceInfo: null });
    } catch (e) {
      set({ error: (e as Error).message });
    }
  },

  backToGlobal: () =>
    set({ view: "global", selectedDevice: null, deviceInfo: null }),

  refresh: async () => {
    const { view, selectedSite } = get();
    try {
      const [global, muts] = await Promise.all([
        api.globalTopology(),
        api.mutations(),
      ]);
      set({ global, mutations: muts.mutations, connected: true });
      if (view === "site" && selectedSite) {
        const siteTopology = await api.siteTopology(selectedSite);
        set({ siteTopology });
      }
    } catch (e) {
      set({ error: (e as Error).message });
    }
  },

  selectDevice: async (id: string | null) => {
    if (!id) {
      set({ selectedDevice: null, deviceInfo: null });
      return;
    }
    set({ selectedDevice: id });
    try {
      const info = await api.deviceInfo(id);
      set({ deviceInfo: info });
    } catch (e) {
      set({ deviceInfo: null, error: (e as Error).message });
    }
  },

  injectFault: async (mutationType, parameters) => {
    set({ busy: true, error: null });
    try {
      await api.mutate({ mutation_type: mutationType, parameters });
      await get().refresh();
      set({ busy: false });
      return true;
    } catch (e) {
      set({ busy: false, error: (e as Error).message });
      return false;
    }
  },

  resetSim: async () => {
    set({ busy: true });
    try {
      await api.reset();
      set({ blast: null, blastLabel: null, showBlast: false });
      await get().refresh();
    } catch (e) {
      set({ error: (e as Error).message });
    } finally {
      set({ busy: false });
    }
  },

  showBlastFor: async (componentId, label) => {
    try {
      const blast = await api.blastRadius(componentId);
      set({ blast, blastLabel: label, showBlast: true });
    } catch (e) {
      set({ error: (e as Error).message });
    }
  },

  toggleBlast: () => set((s) => ({ showBlast: !s.showBlast })),
  clearBlast: () => set({ blast: null, blastLabel: null, showBlast: false }),
  setError: (msg) => set({ error: msg }),

  setMode: async (mode) => {
    try {
      const r = await api.setMode(mode);
      set({ capabilityMode: r.current_mode as CapabilityMode });
    } catch (e) {
      set({ error: (e as Error).message });
    }
  },

  setLeftWidth: (w) => set({ leftWidth: Math.max(220, Math.min(400, w)) }),
  setRightWidth: (w) => set({ rightWidth: Math.max(300, Math.min(600, w)) }),

  runAgent: (query: string) => {
    if (get().isStreaming || !query.trim()) return;
    const userTurn: UserTurn = { id: nextId(), role: "user", text: query };
    const agentTurn: AgentTurn = {
      id: nextId(),
      role: "agent",
      events: [],
      running: true,
    };
    set((s) => ({ turns: [...s.turns, userTurn, agentTurn], isStreaming: true }));

    const appendEvent = (ev: AgentEvent) => {
      set((s) => ({
        turns: s.turns.map((t) =>
          t.id === agentTurn.id && t.role === "agent"
            ? { ...t, events: [...t.events, ev] }
            : t,
        ),
      }));
      // Light up the topology when the agent computes a blast radius.
      if (ev.type === "tool_result" && ev.tool_name === "get_blast_radius") {
        const r = ev.result as unknown as BlastRadiusResult;
        if (r && r.affected_devices) {
          set({ blast: r, blastLabel: r.component_id, showBlast: true });
          void get().refresh();
        }
      }
    };

    const handle = streamAgentQuery(
      query,
      (ev) => {
        if (ev.type === "done") return;
        appendEvent(ev);
      },
      () => {
        set((s) => ({
          isStreaming: false,
          _handle: null,
          turns: s.turns.map((t) =>
            t.id === agentTurn.id && t.role === "agent"
              ? { ...t, running: false }
              : t,
          ),
        }));
      },
    );
    set({ _handle: handle });
  },

  cancelAgent: () => {
    get()._handle?.cancel();
    set((s) => ({
      isStreaming: false,
      _handle: null,
      turns: s.turns.map((t) =>
        t.role === "agent" && t.running ? { ...t, running: false } : t,
      ),
    }));
  },
}));
