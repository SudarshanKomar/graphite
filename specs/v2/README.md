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
| [009](adr/009-skill-system.md) | Skill System | Windsurf rules (`specs/v2/rules/`) and skills (`specs/v2/skills/`) encode investigation workflows + house style for any MCP-connected agent (Cascade) working against Graphite |

### Architecture Specs (Design)

| Spec | Contents |
|---|---|
| [MCP Server Design](architecture/mcp-server-design.md) | Server structure, tool/resource registration, transport, lifecycle |
| [MCP Tool Contracts](architecture/mcp-tool-contracts.md) | All 36 tools (34 migrated + 2 meta), description quality standard, error handling |
| [Agent ↔ MCP Integration](architecture/agent-mcp-integration.md) | How ReactAgent becomes an MCP client; ~30 lines changed |
| [Safety Model](architecture/safety-model.md) | 4-layer defense for mutation tools; mode enforcement; rollback |
| [Migration Plan](architecture/migration-plan.md) | 6-step incremental migration; ~7-11 days; rollback plan |
| [Skill System](architecture/skill-system.md) | Philosophy, per-skill rationale, activation behavior, and extension guide for `specs/v2/rules/` and `specs/v2/skills/` |

### Skills

| Skill | Description |
|---|---|
| [failure-impact-analysis](skills/failure-impact-analysis.md) | Blast-radius and "what breaks if X goes down" questions. |
| [maintenance-change-planning](skills/maintenance-change-planning.md) | Maintenance windows, change-impact prediction, and what-if simulation. |
| [network-health-architecture-review](skills/network-health-architecture-review.md) | Broad network health and architecture reviews. |
| [redundancy-spof-recovery](skills/redundancy-spof-recovery.md) | Redundancy, SPOF, failover-path, and resilience questions. |
| [service-dependency-root-cause](skills/service-dependency-root-cause.md) | Symptom-first root-cause and service dependency mapping. |

### Rules

| Rule | Description |
|---|---|
| [00-graphite-persona-and-grounding](rules/00-graphite-persona-and-grounding.md) | Persona, evidence grounding, two-twin model, identifier discipline. |
| [01-graphite-response-style](rules/01-graphite-response-style.md) | Answer-first, concise, engineer-to-engineer response style. |
| [02-graphite-reasoning-discipline](rules/02-graphite-reasoning-discipline.md) | Hypothesis testing, evidence vs inference, pre-answer quality gate. |
| [03-graphite-investigation-standards](rules/03-graphite-investigation-standards.md) | Investigation efficiency and stopping conditions. |

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
