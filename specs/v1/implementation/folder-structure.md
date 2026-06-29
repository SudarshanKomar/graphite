# Project Folder Structure

Complete directory layout for the Graphite project.

---

```
graphite/
│
├── README.md
├── .env.example                     # Environment variables template
├── .gitignore
├── pyproject.toml                   # Python project config (dependencies, scripts)
│
├── specs/                           # Architecture specs (this directory)
│   ├── adr/
│   ├── schemas/
│   ├── implementation/
│   ├── frontend/
│   └── demo/
│
├── backend/                         # Python backend (FastAPI + engine)
│   ├── pyproject.toml               # Backend-specific dependencies
│   ├── requirements.txt             # Pinned requirements for pip
│   │
│   ├── graphite/                    # Main Python package
│   │   ├── __init__.py
│   │   │
│   │   ├── twin/                    # Digital twin management
│   │   │   ├── __init__.py
│   │   │   ├── builder.py           # TwinBuilder: JSON → NetworkX graph
│   │   │   ├── manager.py           # TwinManager: baseline/working twin lifecycle
│   │   │   ├── graph_wrapper.py     # GraphWrapper: typed accessors over NetworkX
│   │   │   └── validator.py         # Schema validation for JSON source files
│   │   │
│   │   ├── simulation/              # Simulation engine (mutations)
│   │   │   ├── __init__.py
│   │   │   ├── engine.py            # SimulationEngine: apply mutations + cascading effects
│   │   │   └── cascading.py         # Cascading effect propagation logic
│   │   │
│   │   ├── analysis/                # Analysis engine (queries, no mutations)
│   │   │   ├── __init__.py
│   │   │   ├── engine.py            # AnalysisEngine: orchestrates analysis functions
│   │   │   ├── path.py              # Path finding, trace_route, reachability
│   │   │   ├── blast_radius.py      # Blast radius computation
│   │   │   ├── redundancy.py        # Redundancy analysis, SPOF detection, failover
│   │   │   ├── topology.py          # Site topology, device search, overview
│   │   │   └── comparison.py        # Baseline vs working twin diff
│   │   │
│   │   ├── tools/                   # Agent tools (bridge between agent and engines)
│   │   │   ├── __init__.py
│   │   │   ├── registry.py          # ToolRegistry: register and lookup tools (all 34 tools defined here)
│   │   │   └── base.py              # ToolSchema, ToolContext, ToolRegistry classes
│   │   │
│   │   ├── agent/                   # AI agent (ReAct loop)
│   │   │   ├── __init__.py
│   │   │   ├── react_agent.py       # Core ReAct loop
│   │   │   ├── prompts/
│   │   │   │   ├── system_prompt.py # System prompt template + tool descriptions
│   │   │   │   └── templates.py     # Prompt formatting utilities
│   │   │   ├── llm/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── base.py          # LLMProvider protocol/interface
│   │   │   │   ├── openai_provider.py  # OpenAI GPT-4o integration
│   │   │   │   └── anthropic_provider.py # Anthropic Claude integration
│   │   │   └── schemas.py           # Agent message schemas (Thought, Action, Observation)
│   │   │
│   │   └── api/                     # FastAPI application
│   │       ├── __init__.py
│   │       ├── app.py               # FastAPI app factory, lifespan, CORS
│   │       ├── routes/
│   │       │   ├── __init__.py
│   │       │   ├── agent.py         # POST /agent/query, SSE streaming
│   │       │   ├── topology.py      # GET /topology/sites, /topology/{site}
│   │       │   ├── simulation.py    # POST /simulation/reset, /simulation/inject
│   │       │   └── health.py        # GET /health
│   │       └── models.py            # Pydantic request/response models
│   │
│   ├── network_state/               # JSON source of truth files
│   │   ├── sites/
│   │   │   ├── bangalore.json
│   │   │   ├── london.json
│   │   │   ├── newyork.json
│   │   │   └── singapore.json
│   │   ├── devices.json
│   │   ├── links.json
│   │   ├── vlans.json
│   │   ├── bgp_peers.json
│   │   ├── services.json
│   │   ├── user_groups.json
│   │   └── telemetry_snapshot.json
│   │
│   └── tests/                       # Backend tests
│       ├── __init__.py
│       ├── conftest.py              # Shared fixtures (test graph, test twin)
│       ├── test_builder.py          # Twin builder tests
│       ├── test_graph_wrapper.py    # Graph wrapper tests
│       ├── test_simulation.py       # Simulation engine tests
│       ├── test_analysis.py         # Analysis engine tests
│       ├── test_tools.py            # Tool function tests
│       ├── test_agent.py            # Agent loop tests (mocked LLM)
│       └── test_api.py              # API endpoint tests
│
└── frontend/                        # Next.js frontend
    ├── package.json
    ├── next.config.js
    ├── tailwind.config.js
    ├── tsconfig.json
    │
    ├── public/
    │   └── favicon.ico
    │
    └── src/
        ├── app/
        │   ├── layout.tsx           # Root layout
        │   ├── page.tsx             # Main dashboard page
        │   └── globals.css          # Global styles
        │
        ├── components/
        │   ├── topology/
        │   │   ├── GlobalView.tsx   # Multi-site overview (React Flow)
        │   │   ├── SiteView.tsx     # Single site topology (React Flow)
        │   │   ├── DevicePanel.tsx  # Device detail sidebar
        │   │   └── nodes/           # Custom React Flow node components
        │   │       ├── SiteNode.tsx
        │   │       ├── DeviceNode.tsx
        │   │       └── ServiceNode.tsx
        │   │
        │   ├── agent/
        │   │   ├── ChatPanel.tsx    # Agent conversation panel
        │   │   ├── MessageBubble.tsx # Individual message display
        │   │   ├── ThoughtStep.tsx  # Agent reasoning step display
        │   │   └── ToolCallStep.tsx # Tool call + result display
        │   │
        │   ├── simulation/
        │   │   ├── FaultPanel.tsx   # Fault injection controls
        │   │   └── BlastOverlay.tsx # Blast radius overlay on topology
        │   │
        │   └── ui/                  # Shared UI components (shadcn/ui)
        │       └── ...
        │
        ├── lib/
        │   ├── api.ts              # Backend API client
        │   └── types.ts            # TypeScript type definitions
        │
        └── hooks/
            ├── useAgent.ts         # SSE connection to agent endpoint
            └── useTopology.ts      # Topology data fetching
```

---

## Directory Purpose Summary

| Directory | Purpose |
|---|---|
| `specs/` | Architecture decision records, schemas, implementation specs |
| `backend/graphite/twin/` | JSON loading, graph construction, twin lifecycle |
| `backend/graphite/simulation/` | State mutations with cascading effects |
| `backend/graphite/analysis/` | Pure query functions (path, blast radius, redundancy) |
| `backend/graphite/tools/` | Agent-callable tools (thin wrappers around simulation/analysis) |
| `backend/graphite/agent/` | ReAct loop, LLM providers, prompt templates |
| `backend/graphite/api/` | FastAPI routes, Pydantic models, SSE streaming |
| `backend/network_state/` | JSON source of truth (the baseline data) |
| `backend/tests/` | pytest test suite |
| `frontend/` | Next.js app with React Flow topology and chat panel |

---

## Key Dependency Flow

```
JSON files
    → TwinBuilder (twin/)
        → GraphWrapper (twin/)
            → AnalysisEngine (analysis/)  ← query tools read from here
            → SimulationEngine (simulation/) ← mutation tools write through here
                → Tools (tools/)
                    → Agent (agent/)
                        → API (api/)
                            → Frontend
```

No circular dependencies. Each layer depends only on layers below it.
