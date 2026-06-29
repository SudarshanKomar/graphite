# ADR-008: LangChain Evaluation

**Status**: Accepted (evaluation only — **LangChain will NOT be implemented in V2**)  
**Date**: 2025-06-25  
**Related**: ADR-003 (custom ReAct agent, preserved)

---

## Context

Architects evaluating Graphite have suggested assessing LangChain as a potential replacement for the custom ReAct agent. This ADR documents a thorough evaluation of LangChain's value proposition for Graphite, with a clear conclusion.

## Evaluation Criteria

| Criterion | Weight | Description |
|---|---|---|
| Agent flexibility | High | How well does it support custom reasoning patterns? |
| Tool integration | High | Does it improve or complicate tool dispatch? |
| Observability | High | Tracing, debugging, step inspection |
| Enterprise readiness | Medium | Maturity, support, security, licensing |
| MCP compatibility | High | How does it interact with MCP? |
| Dependency footprint | Medium | Size, transitive deps, version conflicts |
| Control & customizability | High | Can we preserve our specific agent behaviors? |

## Analysis

### What LangChain Offers

1. **Pre-built agent patterns**: ReAct, Plan-and-Execute, multi-agent routing. Graphite only needs ReAct, which is ~150 lines of custom code today.

2. **Tool abstraction**: `@tool` decorators, automatic schema generation. Graphite V2 moves to MCP tools, which LangChain would need to consume as MCP client tools — adding a LangChain-to-MCP mapping layer.

3. **LangSmith tracing**: Rich observability with traces, token usage, latency. Valuable, but achievable with simpler solutions (OpenTelemetry, custom logging). Graphite already streams every agent step as an SSE event.

4. **Memory systems**: Conversation buffer, summary, vector-backed memory. Graphite's MVP uses conversation history as memory (sufficient for 5-15 step investigations).

5. **Multi-model support**: Abstractions across OpenAI, Anthropic, Google, etc. Graphite already has a `LLMProvider` protocol that achieves this with ~30 lines per provider.

### LangChain Disadvantages for Graphite

1. **Dependency weight**: LangChain core + community pulls in a large dependency tree. Graphite's custom agent has zero framework dependencies beyond the LLM SDK.

2. **Abstraction opacity**: LangChain's agent internals (prompt construction, output parsing, tool dispatch) are framework-managed. Graphite's agent loop is fully visible, debuggable, and tunable — a direct advantage for a demo project where transparency is the point.

3. **MCP interaction complexity**: With MCP migration, tools are protocol-native. LangChain would sit between the agent and MCP as an additional abstraction layer: `LLM → LangChain Agent → LangChain Tool → MCP Client → MCP Server`. This is strictly worse than `LLM → ReAct Agent → MCP Client → MCP Server`.

4. **Reduced demo impact**: The custom ReAct agent demonstrates engineering capability. Using LangChain says "I plugged in a framework." The evaluating architect is more likely impressed by a well-built custom loop than a framework integration.

5. **Control tradeoffs**: Graphite's agent has specific behaviors (query-only enforcement, mode-based access, structured final_answer schema, corrective parse retries) that would need to be replicated within LangChain's abstractions — often fighting the framework rather than using it.

### Where LangChain WOULD Add Value

- **If Graphite needed multi-agent orchestration**: Supervisor/worker patterns. Not needed for V2.
- **If Graphite needed advanced memory**: Persistent cross-session memory, RAG. Not V2 scope.
- **If Graphite lacked tool/LLM abstractions**: But it already has them.
- **If LangSmith tracing were required**: Meaningful for production ops, but overkill for a demo project.

## Decision

**LangChain will NOT be implemented in V2.**

### Rationale Summary

| Factor | Assessment |
|---|---|
| Does LangChain reduce implementation effort? | No — Graphite's agent is already built and working |
| Does it improve the architecture? | No — it adds a layer between agent and MCP with no functional gain |
| Does it improve observability? | Marginally — LangSmith is nice but not necessary; Graphite already streams every step |
| Does it improve demo impact? | No — custom implementation is more impressive for the evaluation |
| Is it compatible with MCP-first design? | Poorly — LangChain tools and MCP tools are separate abstractions |
| One-axis-at-a-time principle | MCP migration is V2's axis. Adding LangChain = two axes |

### Future Reconsideration Triggers

LangChain should be re-evaluated if:
- Graphite evolves to need multi-agent orchestration (plan-and-execute, supervisor)
- Production deployment requires LangSmith-grade tracing
- LangChain develops first-class MCP server/client integration that eliminates the impedance mismatch
- Team composition changes to favor framework-based development

## Consequences

- V2 preserves the custom ReAct agent (~200 lines)
- No LangChain dependency added
- MCP migration proceeds without additional abstraction layers
- This evaluation satisfies the architect's request for formal LangChain assessment
