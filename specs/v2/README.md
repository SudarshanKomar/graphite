# V2 Specifications — MCP-Native Architecture

Graphite V2 evolves the tool interaction layer from a custom `ToolRegistry` to the **Model Context Protocol (MCP)**, making Graphite consumable by any MCP-compatible agent while preserving the custom ReAct agent loop.

---

## V2 Scope

| Changed | Unchanged |
|---|---|
| Tool dispatch: ToolRegistry → MCP Server | Twin model (baseline + working) |
| Tool access: fixed split → capability modes | Analysis Engine |
| External agent support (new) | Simulation Engine |
| Tool metadata: enriched descriptions | GraphWrapper / NetworkX |
| | ReAct agent loop (custom, no framework) |
| | LLM Provider abstraction |
| | FastAPI REST API |
| | Frontend (Next.js console) |
| | Network state JSON data |

## V2 Spec Inventory

### ADRs (Decisions)

| ADR | Title | Key Decision |
|---|---|---|
| [006](adr/006-mcp-native-architecture.md) | MCP-Native Architecture | Replace ToolRegistry with MCP server; agent becomes MCP client |
| [007](adr/007-capability-modes.md) | Capability Modes | Observe (default, query-only) / Operate (full topology control) |
| [008](adr/008-langchain-evaluation.md) | LangChain Evaluation | Evaluated and rejected for V2; custom ReAct preserved |
| [009](adr/009-skill-system.md) | Skill System | Windsurf rules (`.windsurf/rules/`) and skills (`.windsurf/skills/`) encode investigation workflows + house style for any MCP-connected agent (Cascade) working against Graphite |

### Architecture Specs (Design)

| Spec | Contents |
|---|---|
| [MCP Server Design](architecture/mcp-server-design.md) | Server structure, tool/resource registration, transport, lifecycle |
| [MCP Tool Contracts](architecture/mcp-tool-contracts.md) | All 36 tools (34 migrated + 2 meta), description quality standard, error handling |
| [Agent ↔ MCP Integration](architecture/agent-mcp-integration.md) | How ReactAgent becomes an MCP client; ~30 lines changed |
| [Safety Model](architecture/safety-model.md) | 4-layer defense for mutation tools; mode enforcement; rollback |
| [Migration Plan](architecture/migration-plan.md) | 6-step incremental migration; ~7-11 days; rollback plan |
| [Skill System](architecture/skill-system.md) | Philosophy, per-skill rationale, activation behavior, and extension guide for `.windsurf/rules/` and `.windsurf/skills/` |

### What Remains Valid from V1

These V1 specs require no V2 updates — reference them directly:

- `specs/v1/adr/001-baseline-twin-architecture.md` — twin model unchanged
- `specs/v1/adr/002-bgp-simulation-approach.md` — BGP simulation unchanged
- `specs/v1/adr/003-agent-framework-selection.md` — ReAct agent preserved
- `specs/v1/adr/004-graph-representation.md` — graph model unchanged
- `specs/v1/schemas/baseline-twin-json-schema.md` — JSON data unchanged
- `specs/v1/schemas/graph-node-edge-schema.md` — graph schema unchanged
- `specs/v1/frontend/frontend-architecture.md` — frontend unchanged (MCP is backend-only)
- `specs/v1/demo/demo-scenarios.md` — demo scenarios unchanged

V1 spec that is **superseded** by V2:
- `specs/v1/adr/005-tool-surface-consolidation.md` — superseded by ADR-006 (MCP) and ADR-007 (modes)
- `specs/v1/schemas/tool-schemas.md` — tool definitions migrate to MCP; see `mcp-tool-contracts.md`

---

## V2 Architecture Summary

```
┌─────────────────────────────────────────────────┐
│                  Graphite V2                      │
│                                                   │
│   ┌──────────┐    ┌─────────────────────┐        │
│   │ Frontend │───▶│    FastAPI REST      │        │
│   └──────────┘    │  /topology /sim /agent│        │
│                   └────────┬────────────┘        │
│                            │                      │
│              ┌─────────────▼──────────────┐      │
│              │    Custom ReAct Agent       │      │
│              │  (thought→action→observe)   │      │
│              │         │                  │      │
│              │    LLM Provider            │      │
│              └─────────┬──────────────────┘      │
│                        │ in-process               │
│              ┌─────────▼──────────────┐          │
│              │  Graphite MCP Server   │◀── External Agents
│              │  (36 tools, 3 resources)│   (stdio / SSE)
│              │  [mode: observe]        │          │
│              └────┬──────────┬────────┘          │
│                   │          │                    │
│          ┌────────▼──┐  ┌───▼──────────┐        │
│          │ Analysis  │  │ Simulation   │        │
│          │ Engine    │  │ Engine       │        │
│          └─────┬─────┘  └──────┬───────┘        │
│                │               │                  │
│          ┌─────▼───────────────▼─────┐           │
│          │     GraphWrapper          │           │
│          │  (baseline + working twin)│           │
│          └───────────────────────────┘           │
└─────────────────────────────────────────────────┘
```
