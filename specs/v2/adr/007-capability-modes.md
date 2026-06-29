# ADR-007: Agent Capability Modes

**Status**: Accepted (revised)  
**Date**: 2025-06-26 (revised from 2025-06-25)  
**Evolves**: V1 query/mutation split (ADR-005 / Audit C9)

---

## Context

V1 enforced a hard split: the agent could only call 21 query tools; all 13 mutation tools were API-only. This was correct for V1's single use case (investigation after a pre-injected fault).

V2 needs a broader model. **Mutations are not just fault injection — they are general topology state-changing operations** including:

- **Destructive** — break a link, disable a switch, remove a VLAN
- **Restorative** — enable a device, restore a VLAN, fix a BGP peer
- **Analytical** — mutate then analyze impact ("what happens if…")
- **Remedial** — investigate, identify root cause, apply corrective mutation, verify recovery

The old V2 draft used three modes (investigation / simulation / remediation). This was too narrow and phase-oriented — it assumed mutations only serve fault injection. The corrected model frames modes around **agent autonomy level**, not tool categories.

## Decision

Two capability modes governing agent access to topology-changing tools. The MCP server enforces these at the protocol boundary.

### Modes

| Mode | Query Tools (21) | Mutation Tools (13) | Meta Tools (2) | Use Case |
|---|---|---|---|---|
| **observe** | ✅ | ❌ Refused | ✅ | Read-only inspection. Safe default. |
| **operate** | ✅ | ✅ | ✅ | Full topology control. User-trusted. |

### Why Two Modes, Not Three

The earlier draft proposed a separate "remediation" mode with confirmation gates. After analysis:

- **Confirmation gates require a fundamentally different interaction model** (async approval, pending-mutation queue, UI confirmation flow, timeout handling). This is a substantial feature, not a mode flag.
- **Two modes cleanly map to the safety boundary**: can the agent change state, or not?
- **All V2 use cases map to two modes**:

| User Intent | Mode | Agent Behavior |
|---|---|---|
| "Why is ERP down?" | observe | Query tools → root cause analysis |
| "What happens if sg-leaf-03 fails?" | operate | `disable_device` → `get_blast_radius` → analysis |
| "Break the BLR-SG link" | operate | `disable_link` → confirm done (minimal explanation) |
| "Restore VLAN 420" | operate | `add_vlan` → verify connectivity restored |
| "Investigate and fix the issue" | operate | Query → diagnose → mutation to fix → verify |
| "Reset everything" | either | `reset_simulation` (meta-tool, always available) |

A future V3 "supervised" mode with confirmation can be added without changing the observe/operate architecture — it would be a refinement of operate, not a separate axis.

### Mode Semantics

**`observe`** (default):
- Agent is a read-only inspector. It can look at anything but touch nothing.
- All query tools available. Mutation calls are refused with a guidance message.
- Use when: investigation, troubleshooting, topology browsing, root-cause analysis.

**`operate`**:
- Agent has full topology control. It can break things, fix things, simulate, remediate.
- All tools available. The agent is trusted by the user.
- Use when: user explicitly asks for state changes, what-if simulation, or "investigate and fix."
- Entering operate mode is an **explicit user decision** — never automatic.

### Enforcement Architecture

```python
async def handle_call_tool(self, name: str, arguments: dict) -> list[TextContent]:
    tool_def = self._tools[name]
    if tool_def.category == "mutation" and self._mode.current == "observe":
        raise McpError(
            INVALID_REQUEST,
            f"Tool '{name}' modifies topology state. "
            "Switch to operate mode first: set_capability_mode(mode='operate')"
        )
    result = tool_def.handler(arguments)
    return [TextContent(type="text", text=json.dumps(result))]
```

### Mode Switching

Two mechanisms:

1. **MCP meta-tool**: `set_capability_mode(mode: "observe" | "operate")`. Available in all modes. Lets the agent (or external MCP client) switch modes via the protocol.

2. **REST API**: `POST /agent/mode` for the Graphite frontend to switch modes directly. The UI presents a toggle (Observe / Operate).

Both update the same server-side mode state.

### Mode and Tool Listing

When mode is `observe`, the MCP `tools/list` response includes:
- All 21 query tools (full descriptions)
- 2 meta-tools (set_capability_mode, reset_simulation)
- Mutation tools are **still listed** but annotated as `"requires_mode": "operate"` in their descriptions. This way external agents can discover the full tool surface but understand they need to switch modes to use mutations.

When mode is `operate`, all 36 tools are listed with no restrictions.

### Per-Session Scope (Future)

V2 MVP: single shared mode (one operator model, consistent with V1's shared working twin).

Future: per-session mode and per-session working twin clone for multi-tenant.

## Consequences

**Positive:**
- Clean binary safety boundary: read-only vs full-access
- Covers all V2 use cases (investigation, simulation, remediation, explicit mutation)
- Simple to implement (one enum field on MCP server)
- External agents get the same model as the internal agent
- Easily extensible to "supervised" mode in V3

**Negative:**
- No per-mutation confirmation in V2 (acceptable for single-operator demo)
- Operate mode is all-or-nothing (no per-tool granularity)

## Implementation Notes

- Mode stored as enum on `GraphiteMcpServer` instance
- `set_capability_mode`: switches mode, returns new mode + mutation availability flag
- `reset_simulation`: meta-tool, available in all modes (resetting is always safe)
- Frontend: Observe/Operate toggle in header, colored badge (green/amber)
- System prompt: rebuilt on mode change with appropriate tool list and guidance
