# ADR-001: Baseline + Working Twin Architecture

**Status**: Accepted  
**Date**: 2025-06-22  
**Deciders**: Architecture Lead  

---

## Context

Graphite requires a simulation environment that allows fault injection, blast-radius analysis, and troubleshooting against a network digital twin. The system must support:

- A known-good reference state for comparison
- Safe mutation for simulation without corrupting the reference
- Easy reset to clean state after simulation
- Diffing between healthy and degraded states

## Decision

Use a **two-instance graph architecture**:

### Baseline Twin (Immutable)
- Built once from JSON source-of-truth files at startup
- Represents the fully healthy network state
- **Never mutated** after construction
- Used as reference for comparison and reset operations

### Working Twin (Mutable)
- Created as a deep copy of the baseline twin
- All simulation mutations (fault injection, config changes) target this instance
- All analysis queries run against this instance
- Discarded and re-cloned from baseline on reset

### Lifecycle

```
Startup:
  JSON files → TwinBuilder → Baseline Graph (frozen)

Simulation start:
  Baseline Graph → deep copy → Working Graph

Mutations:
  disable_device(), remove_vlan(), etc. → Working Graph

Analysis:
  trace_route(), blast_radius(), etc. → Working Graph

Reset:
  Discard Working Graph → deep copy Baseline → new Working Graph
```

### Single Working Twin (MVP)
For MVP, only **one working twin** exists at a time. No named branches or parallel scenarios. This avoids state management complexity.

### Comparison Support
The baseline twin enables a `compare_with_baseline()` operation that diffs the working twin against baseline to identify all mutations applied. This is valuable for the agent to understand what has changed.

## Consequences

**Positive:**
- Clean separation between reference and simulation state
- No rollback complexity — just discard and re-clone
- Agent can always compare against healthy baseline
- Simple mental model: "main branch" vs "feature branch"

**Negative:**
- Deep copy has memory overhead (~2x graph memory)
- No support for parallel simulation branches in MVP
- Re-clone is O(n) on graph size (acceptable for simulated topology)

## Alternatives Considered

### 1. Single Mutable Graph with Undo Stack
Push mutations onto a stack, pop to undo. Rejected: complex undo logic for cascading effects (disable device → links down → VLANs unreachable). Partial undo is error-prone.

### 2. Event Sourcing
Store all mutations as events, replay from baseline. Elegant but over-engineered for MVP. Could be a Phase 2 enhancement.

### 3. Database-backed State
Use SQLite or similar. Rejected: adds dependency, slower for graph traversal, NetworkX operates in-memory anyway.

## Implementation Notes

- Use `copy.deepcopy()` on the NetworkX graph for cloning
- Baseline twin should be constructed by `TwinBuilder` class
- Working twin managed by `TwinManager` class
- `TwinManager` exposes: `initialize()`, `clone_working()`, `reset()`, `baseline` (property), `working` (property)
- Baseline-vs-working diff is computed by `AnalysisEngine.compare_with_baseline()`, not TwinManager
- JSON loading happens once at startup; no hot-reload needed for MVP
