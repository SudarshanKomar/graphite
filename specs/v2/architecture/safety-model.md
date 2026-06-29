# Safety Model for Mutation Tools

How Graphite V2 prevents accidental or unauthorized topology mutations.

---

## Threat Model

Graphite's digital twin is a simulation — mutations don't affect real networks. However, unintended mutations corrupt investigation results and degrade the operator experience. Safety concerns:

| Threat | Impact | Mitigation |
|---|---|---|
| Agent accidentally calls mutation tool during investigation | Corrupts working twin mid-analysis | Mode enforcement (observe mode) |
| External agent issues mutations without understanding | Unexpected state changes | Mode enforcement + clear tool annotations |
| Multiple mutation sequences create inconsistent state | Confusing blast radius / analysis | Reset capability + mutation log |
| Mode switched to operate without user awareness | User trusts observe-mode safety guarantee | UI indicator + explicit mode switch |

---

## Defense Layers

### Layer 1: Capability Mode (Primary — MCP Server)

The MCP server refuses mutation tool calls when mode is `observe`:

```python
if tool_def.category == "mutation" and self._mode.current == "observe":
    raise McpError(INVALID_REQUEST,
        f"'{name}' modifies topology state. "
        "Switch to operate mode first: set_capability_mode(mode='operate')")
```

This is the **hard enforcement** layer. It protects against both the internal agent and external clients.

### Layer 2: System Prompt Guidance (Secondary — LLM)

The agent's system prompt tells the LLM what mode it's in and what tools are available. In observe mode, the prompt instructs the agent to use read-only tools only. This is defense-in-depth: even if the MCP server somehow fails to enforce, the LLM won't attempt mutations.

In operate mode, the prompt tells the agent it has full topology control and can perform destructive, restorative, or analytical mutations as needed.

### Layer 3: Mutation Log (Audit)

Every mutation is logged with timestamp, type, parameters, and cascading effects (existing V1 `MutationRecord`). The log is queryable via `compare_with_baseline()` and `reset_simulation`. This provides:
- Full audit trail of what changed
- Easy rollback via reset

### Layer 4: Reset Capability (Recovery)

`reset_simulation` (meta-tool) discards the working twin and re-clones from baseline. **Available in all modes** — resetting to a clean state is always safe.

---

## Mode Transition Safety

### Observe → Operate

- **Trigger**: Agent calls `set_capability_mode(mode="operate")` OR frontend `POST /agent/mode`
- **Gate**: None for V2 MVP (user is the single operator)
- **Future (V3)**: Optional confirmation prompt in UI

### Operate → Observe

- **Trigger**: Same mechanisms
- **Behavior**: Mode switches immediately. Active mutations in the working twin are NOT reversed (they persist until explicit reset). Switching mode restricts future actions, it doesn't undo past ones.

### Reset Does Not Change Mode

`reset_simulation` clears mutations but preserves the current mode. Mental model: "I want a clean slate but stay in operate mode to try something else."

---

## Consumer-Aware Response Behavior

Graphite V2 supports two consumer contexts with different expectations:

### Graphite Product UI

The frontend visualizes topology state (fault colors, blast-radius overlays, health badges). When the agent performs a mutation in operate mode:
- The UI updates topology visualization automatically (via polling or refresh after mutation)
- Agent responses can be **concise** — the UI carries visual context
- Example: agent says "Disabled sg-leaf-03. 3 links down, db-cluster unreachable." The topology canvas shows the rest.

### External IDE / Agentic IDE (no Graphite UI)

There is no topology visualization. The agent's text response is the only output.
- Agent responses should be **precise and self-contained** — include all relevant detail
- Mutation tool return values already include cascading effects (V1 design) which serve this well
- Example: the full blast-radius breakdown, affected services, user counts, severity — all in text

This distinction does NOT require code branching. The MCP server returns the same rich tool results in both cases. The difference is in system prompt guidance — the Graphite agent prompt can note that a UI visualizes state, while an external agent prompt would not.

---

## External Agent Safety

External MCP clients (IDE agents, Claude Desktop) face the same mode enforcement.

### Tool Annotations

Mutation tools include explicit annotations in their MCP descriptions:

```
⚠️ MUTATION — Modifies topology state. Requires operate mode.
Changes persist until reset_simulation is called.
```

### Default Mode

All sessions start in `observe` mode. Switching to `operate` requires an explicit `set_capability_mode` call. The mode switch is logged.

### Concurrent Clients

V2 MVP: single shared mode across all clients (consistent with V1's single-operator model).

Future: per-session mode + per-session working twin for multi-tenant.

---

## Supervised / Confirmation Mode (Future — NOT V2)

A future V3 enhancement could add a `supervised` variant of operate mode:

```
Agent: "I recommend restoring VLAN 420. Shall I proceed?"
User: "Yes"
Agent → MCP: add_vlan(420, "bangalore", ...)  [with confirmation token]
```

This would require:
- Confirmation token system on the MCP server
- UI or CLI approval flow
- Timeout on pending confirmations
- No changes to the observe/operate mode boundary

Explicitly out of V2 scope. The observe/operate architecture supports adding this later as a refinement of operate, not a separate axis.
