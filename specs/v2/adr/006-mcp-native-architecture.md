# ADR-006: MCP-Native Architecture

**Status**: Accepted  
**Date**: 2025-06-25  
**Supersedes**: ADR-005 tool registry (V1)  
**Preserved**: ADR-003 custom ReAct agent (V1)

---

## Context

Graphite V1's tool surface is a custom `ToolRegistry` — a bespoke registration/dispatch system that only Graphite's own ReAct agent can consume. This limits Graphite to a single consumer. Enterprise network teams increasingly use agentic IDEs (Windsurf, Cursor) and orchestration platforms (Claude Desktop, internal agents) that speak the **Model Context Protocol (MCP)**.

Making Graphite MCP-native turns it from a closed product into a **platform**: any MCP-compatible agent can inspect, analyze, and simulate against the digital twin.

## Decision

**Replace the custom `ToolRegistry` with a Graphite MCP Server as the canonical interface to all twin capabilities.**

### What this IS

- The MCP server becomes the single authoritative interface for all tool calls
- The Graphite ReAct agent becomes an MCP client
- External agents connect to the same MCP server
- `ToolRegistry`, `ToolSchema`, `ToolContext`, and `build_default_registry` are removed

### What this is NOT

- NOT a thin wrapper (`Agent → ToolRegistry → MCP → Engines`) — the registry is removed, not wrapped
- NOT a migration to an external agent framework — the custom ReAct loop is preserved (ADR-003)
- NOT a change to the twin/analysis/simulation engines — those are unchanged

### V2 Product Flow (Internal)

```
Frontend
   ↓
FastAPI
   ↓
Custom ReAct Agent
   ├── LLM Provider (Gemini / others)
   └── MCP Client (in-process)
            ↓
     Graphite MCP Server
            ↓
 Analysis Engine / Simulation Engine
```

### V2 Product Flow (External)

```
External Agent / IDE
        ↓
     MCP Client (stdio or SSE)
        ↓
 Graphite MCP Server
        ↓
Analysis Engine / Simulation Engine
```

### Transport Decision

| Consumer | Transport | Rationale |
|---|---|---|
| Internal ReAct agent | **In-process** (direct Python call) | Same process; no serialization overhead. MCP Python SDK supports this via `InMemoryTransport` or direct server method calls. |
| External IDE agents | **stdio** | Standard MCP transport; works with Claude Desktop, Windsurf, Cursor configs. |
| Future: remote agents | **SSE / Streamable HTTP** | For network-separated consumers. Not required for V2 MVP. |

### MCP Primitive Usage — What Graphite Exposes

| MCP Primitive | V2 Decision | Rationale |
|---|---|---|
| **Tools** | ✅ Yes — all 34 tools + 2 meta-tools (36 total) | Core value. Direct mapping from V1 tool surface + mode/reset management. |
| **Resources** | ✅ Yes — 3 curated resources | Browsable state for external agents. Read-only topology/diff snapshots. See architecture spec. |
| **Prompts** | ❌ No (V2) | Adds MCP surface without clear benefit. The internal agent has its own system prompt. External agents can compose their own. Revisit in V3. |

## Consequences

**Positive:**
- Graphite becomes consumable by any MCP client (IDEs, orchestrators, custom agents)
- Eliminates bespoke ToolRegistry abstraction
- Tool contracts become protocol-standardized (not custom JSON schemas)
- Multiple concurrent consumers possible (internal agent + external IDE)
- Future-proofs for MCP ecosystem growth

**Negative:**
- MCP SDK dependency (`mcp` Python package)
- Internal agent tool calls now traverse MCP protocol layer (mitigated by in-process transport)
- MCP is still an evolving specification — may need updates as protocol matures

**Acceptable:**
The MCP Python SDK is lightweight. In-process transport eliminates performance concerns. The protocol is backed by Anthropic and has wide adoption.

## Alternatives Considered

### 1. Keep ToolRegistry + Add MCP Adapter Alongside
Run both systems. Rejected: two tool registrations, two dispatch paths, synchronization burden. "One canonical interface" principle.

### 2. Expose REST API Only (No MCP)
External agents call FastAPI endpoints. Rejected: REST is not the agent tool-calling standard. MCP is purpose-built for agent-tool interaction with richer semantics (tool discovery, argument schemas, streaming results).

### 3. Full Framework Migration (LangChain + LangServe)
Replace everything with LangChain tools + LangServe. Rejected: changes two axes at once (tool system + agent framework). See ADR-008.

## Implementation Notes

- MCP server: `graphite/mcp/server.py` (`GraphiteMcpServer` class)
- MCP tool definitions: `graphite/mcp/tools.py` (ported from V1 registry + enriched descriptions)
- Agent calls `GraphiteMcpServer` methods directly (in-process, no separate client module)
- FastAPI simulation endpoints continue to call engines directly (not through MCP) — they are operator-facing REST, not agent-facing tool calls
- `ToolRegistry`, `ToolSchema`, `ToolContext`, `build_default_registry` → deprecated and removed
