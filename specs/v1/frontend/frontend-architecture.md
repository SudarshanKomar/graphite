# Frontend Architecture

Next.js + React Flow + Tailwind CSS + shadcn/ui.

---

## Layout

Three-panel layout:

```
┌─────────────────────────────────────────────────────────────┐
│  Header: "Graphite — Intelligent Network Copilot"    [Reset]│
├──────────────┬──────────────────────────┬───────────────────┤
│              │                          │                   │
│  Left Panel  │     Main Canvas          │   Right Panel     │
│  (250px)     │     (flex-grow)          │   (400px)         │
│              │                          │                   │
│  - Site list │  React Flow topology     │  Agent Chat       │
│  - Fault     │  visualization           │  - Messages       │
│    injection │                          │  - Thoughts       │
│    controls  │  (Global or Site view)   │  - Tool calls     │
│              │                          │  - Final answer   │
│  - Device    │                          │  - Input box      │
│    detail    │                          │                   │
│    (when     │                          │                   │
│    selected) │                          │                   │
│              │                          │                   │
└──────────────┴──────────────────────────┴───────────────────┘
```

---

## View Hierarchy

### 1. Global View (default)

Shows all 4 sites as large nodes connected by WAN links.

**Site node content**:
- Site name
- Device count
- Health indicator (colored dot: green/yellow/red)
- Employee count

**WAN link content**:
- Latency label (e.g., "55ms")
- Bandwidth label (e.g., "10G")
- Color: green (up, low latency), yellow (degraded/high latency), red (down)

**Layout**: Approximate geographic positioning
- Bangalore: center-left
- London: top-left  
- New York: top-right
- Singapore: center-right

**Interaction**: Click site node → drill into Site View

### 2. Site View (drill-down)

Shows internal topology of one site.

**Breadcrumb**: `Global > Bangalore`

**Node types with visual differentiation**:

| Device Type | Shape | Color | Icon |
|---|---|---|---|
| Router/Edge | Rectangle | Blue | 🔀 Router icon |
| Core Switch | Rectangle | Indigo | ◆ Diamond |
| Distribution Switch | Rectangle | Purple | ▬ Bridge |
| Access Switch | Rounded rect | Gray | ⊞ Grid |
| Firewall | Hexagon | Orange | 🛡 Shield |
| Spine/Leaf | Rectangle | Teal | ▤ Rack |
| Server | Rectangle | Green | □ Server |
| Access Point | Circle | Cyan | 📡 Signal |

**Node label**: Device name + status indicator  
**Node tooltip**: Device type, vendor, OS, management IP

**Link visualization**:
- Up: solid green line
- Down: dashed red line
- Degraded (high latency): solid yellow/orange line

**VLAN visualization**: Toggle-able overlay. When enabled, highlight devices that carry a selected VLAN.

**Layout**: Hierarchical top-to-bottom (edge routers at top, access layer at bottom) using React Flow's dagre layout.

### 3. Device Detail Panel (left sidebar, below site list)

When a device node is clicked, show:
- Device name, type, vendor, OS
- Status (up/down with colored badge)
- Management IP
- Interface list (name, IP, status, speed, connected_to)
- Routing table (prefix, next_hop, protocol)
- BGP peers (if applicable): peer IP, AS, state, prefixes

---

## Blast Radius Overlay

When `get_blast_radius` returns results (either from agent or direct API call):

1. **Affected nodes** get a pulsing red border/glow
2. **Degraded nodes** get a yellow border
3. **Healthy nodes** stay green
4. **The failed component** gets a red "X" overlay
5. A floating summary card shows:
   - Total affected devices
   - Total affected users
   - Severity badge (critical/high/medium/low)
   - List of affected services

This overlay is **additive** — it sits on top of the topology view.  
Toggle with a button: "Show Blast Radius" / "Hide Blast Radius"

---

## Agent Chat Panel (right sidebar)

### Message Types

1. **User message**: Standard chat bubble (right-aligned, blue)

2. **Agent thought**: Collapsible, gray italic text with 🧠 icon
   ```
   🧠 Thinking: VLAN 420 is missing from Bangalore. I should check which 
   user groups are affected...
   ```

3. **Tool call**: Collapsible card with tool name and parameters
   ```
   🔧 Calling: get_vlan_info
   Parameters: { vlan_id: 420, site: "bangalore" }
   ```

4. **Tool result**: Collapsible card (collapsed by default) with JSON result
   ```
   📋 Result: get_vlan_info
   ▶ { vlan_id: 420, status: "removed", ... }  (click to expand)
   ```

5. **Final answer**: Prominent card with sections:
   - **Summary** (bold text)
   - **Root Cause** (detail paragraph)
   - **Affected Components** (devices, services, users counts)
   - **Severity** (colored badge)
   - **Confidence** (percentage)
   - **Remediation Steps** (numbered list)

### Streaming Behavior

- SSE connection opened on query submit
- Events rendered as they arrive
- Typing indicator while waiting for next event
- Auto-scroll to bottom on new events
- "Stop" button to cancel agent run

---

## Fault Injection Panel (left sidebar section)

### Controls

```
┌─ Fault Injection ─────────────────┐
│                                   │
│  Fault Type: [dropdown]           │
│    ○ Disable Device               │
│    ○ Disable Link                 │
│    ○ Remove VLAN                  │
│    ○ Disable BGP Peer             │
│    ○ Set Link Latency             │
│                                   │
│  [Dynamic parameter fields]       │
│                                   │
│  [ Inject Fault ]  [ Reset All ]  │
│                                   │
│  Active Faults:                   │
│  • blr-core-01: disabled          │
│  • VLAN 420 @ bangalore: removed  │
│                                   │
└───────────────────────────────────┘
```

**Dynamic fields per fault type**:
- Disable Device → Device selector (dropdown with search)
- Disable Link → Source device + Target device selectors
- Remove VLAN → VLAN ID + Site selector
- Disable BGP Peer → Device + Peer IP selectors
- Set Link Latency → Source + Target + Latency (ms) input

**After injection**: Show result toast + update topology view (colors change)

---

## State Management

Use React context or Zustand (lightweight):

```typescript
interface AppState {
    currentView: "global" | "site";
    selectedSite: string | null;
    selectedDevice: string | null;
    topology: GlobalTopology | null;
    siteTopology: SiteTopology | null;
    activeFaults: Fault[];
    blastRadius: BlastRadiusResult | null;
    showBlastOverlay: boolean;
    agentMessages: AgentMessage[];
    isAgentRunning: boolean;
}
```

---

## API Integration

### REST Endpoints Used

| Frontend Action | API Call |
|---|---|
| Load global view | `GET /topology/global` |
| Load site view | `GET /topology/sites/{site}` |
| Inject fault | `POST /simulation/inject` |
| Reset simulation | `POST /simulation/reset` |
| Agent query | `POST /agent/query` (SSE) |

### SSE Client

```typescript
function useAgentStream(query: string) {
    // Use fetch() with POST + ReadableStream (not EventSource, which only supports GET)
    // Parse SSE-formatted events: "data: {...}\n\n"
    // Event types: thought, tool_call, tool_result, final_answer, error
    // Update agentMessages state as events arrive
    // Handle stream close / errors
    // See spec-refinements Issue 9 for implementation pattern
}
```

---

## Technology Choices

| Concern | Choice | Reason |
|---|---|---|
| Framework | Next.js 16.2.9 (Turbopack) | Modern React, SSR not needed but good defaults |
| Styling | Tailwind CSS | Fast, utility-first, good for dashboards |
| Components | Hand-rolled Tailwind primitives | Avoids shadcn CLI dependency, works behind TLS proxy |
| Graph visualization | @xyflow/react v12 | Best React graph library, interactive, custom nodes |
| Layout algorithm | Deterministic tiered layout | Custom layout, removes dagre dependency |
| Icons | Lucide React | Clean, consistent icon set |
| State | Zustand | Lightweight, no boilerplate |
| HTTP client | fetch (built-in) | Simple, no extra dep |
