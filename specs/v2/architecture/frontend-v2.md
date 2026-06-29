# Frontend V2 Architecture

V2 frontend changes for MCP-native Graphite. The V1 three-panel console layout,
React Flow topology, and copilot panel remain structurally valid (see
`specs/v1/frontend/frontend-architecture.md`). This spec documents only V2
additions and refinements.

---

## V2 Frontend Changes

### 1. Observe / Operate Mode UI

**New API endpoints**:
- `GET /agent/mode` → `{ mode, mutation_tools_enabled }`
- `POST /agent/mode` → `{ previous_mode, current_mode, mutation_tools_enabled }`

**Store additions**:
```typescript
capabilityMode: "observe" | "operate";   // default: "observe"
setMode: (mode: "observe" | "operate") => Promise<void>;
```

**Header mode badge**: A toggle pill in the header controls area, between the
AI status badge and the Reset button.

| Mode | Appearance |
|---|---|
| Observe | Green border, green text, eye icon. Label: "Observe". Safe default. |
| Operate | Amber border, amber text, wrench icon. Label: "Operate". |

Clicking the badge toggles the mode via `POST /agent/mode`. The transition is
instant. In operate mode, a subtle amber tint appears on the header border to
signal elevated capability.

**Copilot mode context**: The copilot header shows the current mode as a small
tag next to "Copilot", so the user always knows what the agent can do.

**System prompt alignment**: When mode changes, the next agent query uses a
rebuilt system prompt (backend handles this — no frontend prompt construction).

### 2. Resizable Panels

Replace the static three-panel layout with draggable split-pane separators.

**Separator behavior**:
- Vertical separator between left rail and topology canvas
- Vertical separator between topology canvas and copilot panel
- Each separator: 4px wide hit zone, 1px visible line, cursor: `col-resize`
- Drag to resize with mouse
- Min/max constraints prevent collapse:
  - Left rail: min 220px, max 400px
  - Copilot panel: min 300px, max 600px
  - Topology canvas: takes remaining space (min 300px)
- Panel widths stored in Zustand (local state, not persisted to backend)
- Implementation: custom `usePanelResize` hook with `mousedown`/`mousemove`/`mouseup`

### 3. Responsive Behavior

**Breakpoints**:
| Name | Range | Layout |
|---|---|---|
| Desktop+ | ≥1280px | Full three-panel layout |
| Laptop | 1024–1279px | Narrower left rail (240px), narrower copilot (340px) |
| Tablet | 768–1023px | Left rail collapses to icon-only rail (48px); copilot below canvas |
| Mobile | <768px | Single-column: topology full-width, copilot below, left rail hidden |

**Header**: Stats row wraps to second line on narrow screens. Mode badge always visible.

### 4. Canvas Overlay Fixes

The CanvasOverlay (breadcrumb, legend, blast radius button, blast card) currently
uses `absolute` positioning with `top-4 right-4`. On narrow widths or when the
blast card is visible, these can overlap.

**Fix**: Use a flex row for the top overlay strip with `justify-between`. The
blast radius card drops to a second row below the controls when viewport is
narrow. Legend wraps below if needed.

### 5. Copilot Refinements

- **Mode tag**: Small colored tag next to "Copilot" header showing observe/operate
- **Idle state**: When no conversation active and mode is operate, show
  operate-specific prompts (e.g., "Break the BLR-SG link", "Restore VLAN 420")
- **Streaming readability**: Increase line-height on thought events, add
  subtle left-border on tool results for visual grouping

---

## Component Hierarchy (V2 additions highlighted)

```
ConsolePage
├── Header
│   ├── Brand
│   ├── Global Stats
│   ├── **ModeBadge** ← NEW (observe/operate toggle)
│   ├── AI Status Badge
│   ├── Connection Badge  
│   └── Reset Button
├── **ResizableLayout** ← NEW (wraps the three panels)
│   ├── LeftRail
│   │   ├── SiteList / DeviceDetail
│   │   ├── ScenarioBar
│   │   ├── FaultPanel
│   │   └── ActiveFaults
│   ├── **PanelSeparator** ← NEW
│   ├── TopologyCanvas
│   │   ├── ReactFlow (global / site views)
│   │   └── CanvasOverlay (breadcrumb, legend, blast)
│   ├── **PanelSeparator** ← NEW
│   └── CopilotPanel
│       ├── **Header + mode tag** ← UPDATED
│       ├── Conversation (EventItem list)
│       └── Composer
└── Toast
```

---

## State Flow (V2 additions)

```
User clicks Observe/Operate toggle
  → store.setMode("operate")
  → POST /agent/mode { mode: "operate" }
  → backend switches MCP server mode
  → store updates capabilityMode
  → Header badge re-renders
  → Copilot shows mode-appropriate prompts
  → Next agent query uses operate-mode system prompt

User drags panel separator
  → onMouseMove updates panel width in store
  → CSS flex-basis updates in real time
  → onMouseUp finalizes width
```

---

## API Dependencies (V2 additions)

| Frontend Action | API Call | V2 New? |
|---|---|---|
| Load global view | `GET /topology/global` | No |
| Load site view | `GET /topology/sites/{site}` | No |
| Inject fault | `POST /simulation/mutate` | No |
| Reset simulation | `POST /simulation/reset` | No |
| Agent query | `POST /agent/query` (SSE) | No |
| **Get mode** | **`GET /agent/mode`** | **Yes** |
| **Set mode** | **`POST /agent/mode`** | **Yes** |

---

## Design Constraints

1. No external UI component libraries (shadcn CLI, Radix packages). All components
   are hand-rolled Tailwind primitives. This avoids proxy/network issues.
2. System fonts only (no Google Fonts). Specified in `tailwind.config.ts`.
3. All colors from the Graphite palette in Tailwind config. No hardcoded hex values
   in components.
4. Panel resize uses native DOM events, no resize library dependency.
