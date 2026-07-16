# V1 Specification Index

All Graphite V1 specifications are archived in this directory (`specs/v1/`). V1 is **complete, released, and frozen**.

V2 specs (in `specs/v2/`) reference V1 specs by relative path where the original design remains valid.

---

## V1 Spec Inventory

| Category | Path | Contents |
|---|---|---|
| **ADRs** | `specs/v1/adr/001–005` | Baseline twin, BGP simulation, ReAct agent, graph representation, tool consolidation |
| **Schemas** | `specs/v1/schemas/` | JSON source-of-truth, graph node/edge schema, tool schemas (34 tools: 21 query + 13 mutation) |
| **Implementation** | `specs/v1/implementation/` | Folder structure, class hierarchy, MVP roadmap, spec refinements (resolved), spec change log |
| **Frontend** | `specs/v1/frontend/` | Frontend architecture (Next.js + React Flow + Tailwind + Zustand) |
| **Demo** | `specs/v1/demo/` | 3 demo scenarios (VLAN removal, leaf switch failure, WAN degradation) |
| **Audit** | `specs/v1/audit/` | Audit round 1 findings |

## V1 Key Architecture Decisions (Summary)

These decisions carry into V2 unless explicitly superseded by a V2 ADR:

1. **Two-twin model** — Baseline (immutable) + Working (mutable clone)
2. **Single heterogeneous MultiDiGraph** — physical + logical entities in one graph
3. **BGP as node attributes** — not graph edges
4. **Query/mutation tool split** — agent can observe, never mutate (V2 evolves this)
5. **Custom ReAct agent** — no framework dependency (preserved in V2)
6. **Deterministic engine owns truth** — LLM handles reasoning/orchestration only
7. **GraphWrapper as sole NetworkX importer** — all graph access through wrapper

## V1 Architecture Deviations

See `../project_state/architecture-deviations.md` for D1–D11. These are documented intentional deviations from specs, not bugs.
