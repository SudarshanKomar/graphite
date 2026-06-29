# Class Hierarchy

Python class design for all backend components. Includes key methods, attributes, and relationships.

---

## 1. Twin Management (`graphite/twin/`)

### TwinBuilder

Loads JSON files and constructs a NetworkX MultiDiGraph.

```python
class TwinBuilder:
    """Builds a NetworkX graph from JSON source-of-truth files."""

    def __init__(self, data_dir: str | Path):
        """
        Args:
            data_dir: Path to network_state/ directory
        """

    def build(self) -> nx.MultiDiGraph:
        """Load all JSON files and construct the complete graph.
        
        Returns: Populated NetworkX MultiDiGraph
        Raises: ValidationError if JSON is invalid
        """

    # JSON-to-graph field mapping applied during loading:
    # - devices.json `type` field → graph node `device_type` (avoid Python builtin collision)
    # - services.json `type` field → graph node `service_type`
    # - VLANs loaded from JSON get `status="active"` (not in JSON, set by builder)
    # - BGP state from bgp_peers.json → merged into device node `bgp_state` attribute
    # - Telemetry from telemetry_snapshot.json → merged into device node `telemetry` attribute

    # Private methods for each entity type:
    def _load_sites(self, graph: nx.MultiDiGraph) -> None: ...
    def _load_devices(self, graph: nx.MultiDiGraph) -> None: ...
    def _load_links(self, graph: nx.MultiDiGraph) -> None: ...
    def _load_vlans(self, graph: nx.MultiDiGraph) -> None: ...
    def _load_bgp_peers(self, graph: nx.MultiDiGraph) -> None: ...
    def _load_services(self, graph: nx.MultiDiGraph) -> None: ...
    def _load_user_groups(self, graph: nx.MultiDiGraph) -> None: ...
    def _load_telemetry(self, graph: nx.MultiDiGraph) -> None: ...
    def _validate(self, graph: nx.MultiDiGraph) -> None: ...
```

### TwinManager

Manages baseline and working twin lifecycle.

```python
class TwinManager:
    """Manages baseline (immutable) and working (mutable) graph twins."""

    def __init__(self, builder: TwinBuilder):
        self._baseline: nx.MultiDiGraph  # Set once, never mutated
        self._working: nx.MultiDiGraph | None

    def initialize(self) -> None:
        """Build baseline from JSON. Called once at startup."""

    def clone_working(self) -> None:
        """Deep-copy baseline into working twin. Discards existing working twin."""

    def reset(self) -> None:
        """Alias for clone_working(). Resets simulation state."""

    @property
    def baseline(self) -> nx.MultiDiGraph:
        """Read-only access to baseline graph."""

    @property
    def working(self) -> nx.MultiDiGraph:
        """Access to working graph. Raises if not cloned yet."""

    def has_working(self) -> bool:
        """Check if working twin exists."""
```

### GraphWrapper

Typed accessor layer over raw NetworkX graph. **All other code accesses the graph through this wrapper** — never imports NetworkX directly.

```python
class GraphWrapper:
    """Typed accessors over a NetworkX MultiDiGraph."""

    def __init__(self, graph: nx.MultiDiGraph):
        self._graph = graph

    # --- Node queries ---
    def get_node(self, node_id: str) -> dict:
        """Get node attributes. Raises NodeNotFound."""

    def get_node_type(self, node_id: str) -> str:
        """Get node_type attribute."""

    def node_exists(self, node_id: str) -> bool: ...

    def get_nodes_by_type(self, node_type: str, **filters) -> list[dict]:
        """Get all nodes of a type, optionally filtered by attributes.
        Example: get_nodes_by_type("device", site="bangalore", status="up")
        """

    # --- Edge queries ---
    def get_edges(self, source: str, target: str, relation: str = None) -> list[dict]:
        """Get edges between two nodes, optionally filtered by relation."""

    def get_neighbors(self, node_id: str, relation: str = None, direction: str = "out") -> list[str]:
        """Get neighbor node IDs.
        direction: "out" (successors), "in" (predecessors), "both"
        """

    def get_edges_by_relation(self, relation: str) -> list[tuple[str, str, dict]]:
        """Get all edges of a given relation type."""

    # --- Typed convenience methods ---
    def get_devices(self, site: str = None, device_type: str = None, status: str = None) -> list[dict]: ...
    def get_vlans(self, site: str = None) -> list[dict]: ...
    def get_services(self, site: str = None) -> list[dict]: ...
    def get_user_groups(self, site: str = None) -> list[dict]: ...
    def get_sites(self) -> list[dict]: ...

    def get_physical_neighbors(self, device_id: str) -> list[str]:
        """Devices connected via physical_link."""

    def get_vlan_devices(self, vlan_node_id: str) -> list[str]:
        """Devices that carry this VLAN (carries_vlan predecessors)."""

    def get_vlan_user_groups(self, vlan_node_id: str) -> list[dict]:
        """User groups served by this VLAN."""

    def get_service_deps(self, service_id: str) -> list[str]:
        """Direct dependency service IDs."""

    def get_service_dependents(self, service_id: str) -> list[str]:
        """Services that depend on this service."""

    # --- Mutation helpers (used by simulation engine) ---
    def set_node_attr(self, node_id: str, **attrs) -> None:
        """Update node attributes."""

    def set_edge_attr(self, source: str, target: str, relation: str, **attrs) -> None:
        """Update edge attributes."""

    def add_node(self, node_id: str, **attrs) -> None: ...
    def remove_node(self, node_id: str) -> None: ...
    def add_edge(self, source: str, target: str, relation: str, **attrs) -> None: ...
    def remove_edge(self, source: str, target: str, relation: str) -> None: ...

    # --- Raw access (for analysis engine internals) ---
    @property
    def nx_graph(self) -> nx.MultiDiGraph:
        """Direct access to underlying NetworkX graph (use sparingly)."""
```

### Validator

```python
class Validator:
    """Validates JSON source files against expected schemas."""

    @staticmethod
    def validate_devices(data: list[dict]) -> list[str]:
        """Returns list of validation errors (empty if valid)."""

    @staticmethod
    def validate_links(data: list[dict], device_ids: set[str]) -> list[str]: ...

    @staticmethod
    def validate_vlans(data: list[dict], device_ids: set[str]) -> list[str]: ...

    # ... one method per entity type
```

---

## 2. Simulation Engine (`graphite/simulation/`)

### SimulationEngine

Orchestrates mutations and cascading effects on the working twin.

```python
class SimulationEngine:
    """Applies mutations to the working twin with cascading effects."""

    def __init__(self, twin_manager: TwinManager):
        self._twin_manager = twin_manager
        self._mutation_log: list[MutationRecord] = []

    @property
    def graph(self) -> GraphWrapper:
        """Shortcut to working twin wrapped in GraphWrapper."""

    def disable_device(self, device_id: str) -> dict: ...
    def enable_device(self, device_id: str) -> dict: ...
    def disable_link(self, source: str, target: str) -> dict: ...
    def enable_link(self, source: str, target: str) -> dict: ...
    def set_link_latency(self, source: str, target: str, latency_ms: float) -> dict: ...
    def remove_vlan(self, vlan_id: int, site: str) -> dict: ...
    def add_vlan(self, vlan_id: int, site: str, subnet: str, name: str, devices: list[str]) -> dict: ...
    def disable_bgp_peer(self, device_id: str, peer_ip: str) -> dict: ...
    def enable_bgp_peer(self, device_id: str, peer_ip: str) -> dict: ...
    def withdraw_prefix(self, device_id: str, prefix: str) -> dict: ...
    def advertise_prefix(self, device_id: str, prefix: str) -> dict: ...
    def add_static_route(self, device_id: str, prefix: str, next_hop: str) -> dict: ...
    def remove_static_route(self, device_id: str, prefix: str) -> dict: ...

    def reset(self) -> None:
        """Reset working twin to baseline. Clears mutation log."""

    def get_mutation_log(self) -> list[dict]:
        """Return log of all mutations applied in this session."""

    def _recompute_service_health(self) -> None:
        """Recompute all service statuses after any mutation.
        Rules:
        - Host device down → service 'down'
        - All direct deps down → service 'down'
        - Some deps down/degraded → service 'degraded'
        - Host up + all deps healthy → service 'healthy'
        Called automatically at the end of every mutation method.
        """
```

### MutationRecord

```python
@dataclass
class MutationRecord:
    timestamp: str
    mutation_type: str  # e.g., "disable_device", "remove_vlan"
    parameters: dict
    cascading_effects: dict
```

### CascadingEffects

Pure functions that compute secondary effects of a mutation.

```python
class CascadingEffects:
    """Computes and applies secondary effects of mutations."""

    @staticmethod
    def device_disabled(graph: GraphWrapper, device_id: str) -> dict:
        """When a device goes down:
        1. All physical_link edges from/to this device → status="down"
        2. If device hosts a service → service status="down"
        3. If device is a BGP speaker → all peers → state="idle", prefixes withdrawn
        4. VLANs that were only reachable through this device → affected
        Returns dict describing all changes made.
        """

    @staticmethod
    def device_enabled(graph: GraphWrapper, device_id: str) -> dict:
        """Reverse of device_disabled. Restores links, services, BGP peers."""

    @staticmethod
    def link_disabled(graph: GraphWrapper, source: str, target: str) -> dict: ...
    @staticmethod
    def link_enabled(graph: GraphWrapper, source: str, target: str) -> dict: ...
    @staticmethod
    def vlan_removed(graph: GraphWrapper, vlan_node_id: str) -> dict: ...
    @staticmethod
    def bgp_peer_disabled(graph: GraphWrapper, device_id: str, peer_ip: str) -> dict: ...
```

---

## 3. Analysis Engine (`graphite/analysis/`)

### AnalysisEngine

Facade over all analysis functions. Query-only, never mutates graph.

```python
class AnalysisEngine:
    """Pure query engine over a graph. Never mutates state."""

    def __init__(self, twin_manager: TwinManager):
        self._twin_manager = twin_manager

    @property
    def graph(self) -> GraphWrapper:
        """Working twin wrapped in GraphWrapper."""

    @property
    def baseline_graph(self) -> GraphWrapper:
        """Baseline twin wrapped in GraphWrapper."""

    # Delegates to specialized modules:
    def trace_route(self, source: str, destination: str) -> dict:
        """Delegates to path.trace_route()"""
    def check_reachability(self, source: str, destination: str) -> dict: ...
    def get_alternative_paths(self, source: str, destination: str) -> dict: ...
    def get_blast_radius(self, component_id: str) -> dict: ...
    def get_service_dependencies(self, service_id: str) -> dict: ...
    def get_redundancy_status(self, component_id: str) -> dict: ...
    def get_single_points_of_failure(self, site: str) -> dict: ...
    def get_failover_path(self, primary_component: str) -> dict: ...
    def compare_with_baseline(self) -> dict: ...
    # ... all query methods
```

### Path Analysis (`path.py`)

```python
def trace_route(graph: GraphWrapper, source: str, destination: str) -> dict:
    """Hop-by-hop trace following routing tables.
    
    Algorithm:
    1. Resolve source/destination to device IDs
    2. At each hop, consult device's routing table for next hop
    3. Verify physical link to next hop is up
    4. Accumulate latency
    5. Stop when destination reached or no route / link down
    """

def check_reachability(graph: GraphWrapper, source: str, destination: str) -> dict: ...
def get_alternative_paths(graph: GraphWrapper, source: str, destination: str) -> dict: ...
```

### Blast Radius (`blast_radius.py`)

```python
def get_blast_radius(graph: GraphWrapper, component_id: str) -> dict:
    """Compute full impact of a failed component.
    
    Algorithm:
    1. Identify component type (device, vlan, service, link)
    2. For device: find all services hosted, all VLANs carried, all downstream devices
    3. For VLAN: find all user groups served, check if those users can still reach services
    4. For service: find all dependent services (reverse dependency walk)
    5. Aggregate affected users
    6. Calculate severity based on thresholds
    """

def _compute_severity(affected_users: int, affected_services: list[dict]) -> tuple[str, list[str]]:
    """Returns (severity_level, reason_list)."""
```

### Redundancy (`redundancy.py`)

```python
def get_redundancy_status(graph: GraphWrapper, component_id: str) -> dict: ...

def get_single_points_of_failure(graph: GraphWrapper, site: str) -> dict:
    """For each device/link in the site, temporarily remove it and check
    if any previously-reachable destination becomes unreachable.
    If yes, it's a SPOF."""

def get_failover_path(graph: GraphWrapper, primary_component: str) -> dict: ...
```

### Comparison (`comparison.py`)

```python
def compare_with_baseline(working: GraphWrapper, baseline: GraphWrapper) -> dict:
    """Diff all node and edge attributes between working and baseline graphs.
    Returns list of changes (attribute diffs)."""
```

---

## 4. Tools (`graphite/tools/`)

### BaseTool & Registry

```python
@dataclass
class ToolSchema:
    """Schema exposed to the LLM."""
    name: str
    description: str
    parameters: dict  # JSON Schema for parameters
    returns: str      # Description of return type
    category: str     # "query" or "mutation" — only query tools shown to agent

class ToolRegistry:
    """Registry of all agent-callable tools."""

    def __init__(self):
        self._tools: dict[str, Callable] = {}
        self._schemas: dict[str, ToolSchema] = {}

    def register(self, schema: ToolSchema, func: Callable) -> None: ...
    def get_tool(self, name: str) -> Callable: ...
    def get_schema(self, name: str) -> ToolSchema: ...
    def list_schemas(self) -> list[ToolSchema]: ...

    async def execute(self, tool_name: str, parameters: dict) -> dict:
        """Execute a tool by name with given parameters.
        Returns tool result dict.
        Raises ToolNotFound, ToolExecutionError.
        """

def tool(name: str, description: str, parameters: dict):
    """Decorator to register a function as an agent tool.
    
    Usage:
    @tool(name="get_device_info", description="...", parameters={...})
    def get_device_info(context: ToolContext, device_id: str) -> dict:
        ...
    """
```

### ToolContext

Injected into every tool function. Provides access to engines.

```python
@dataclass
class ToolContext:
    """Shared context passed to all tool functions."""
    simulation_engine: SimulationEngine
    analysis_engine: AnalysisEngine
    twin_manager: TwinManager
```

### Tool Function Pattern

Every tool follows this pattern:

```python
@tool(
    name="get_device_info",
    description="Returns device metadata and current status",
    parameters={
        "type": "object",
        "properties": {
            "device_id": {"type": "string", "description": "Device ID"}
        },
        "required": ["device_id"]
    }
)
def get_device_info(ctx: ToolContext, device_id: str) -> dict:
    node = ctx.analysis_engine.graph.get_node(device_id)
    if node.get("node_type") != "device":
        raise ToolExecutionError(f"'{device_id}' is not a device")
    return {
        "id": device_id,
        "name": node["name"],
        "device_type": node["device_type"],
        # ...
    }
```

---

## 5. Agent (`graphite/agent/`)

### ReactAgent

```python
class ReactAgent:
    """ReAct agent: Thought → Action → Observation loop."""

    MAX_ITERATIONS = 15

    def __init__(
        self,
        llm: LLMProvider,
        tool_registry: ToolRegistry,
        system_prompt: str
    ):
        self._llm = llm
        self._tools = tool_registry
        self._system_prompt = system_prompt

    async def run(self, user_query: str) -> AsyncGenerator[AgentEvent, None]:
        """Execute agent loop, yielding events for streaming.
        
        Yields:
            ThoughtEvent: Agent's reasoning
            ToolCallEvent: Tool being called with params
            ToolResultEvent: Tool execution result
            FinalAnswerEvent: Agent's final response
            ErrorEvent: If something goes wrong
        """

    async def _call_llm(self, messages: list[Message]) -> AgentResponse:
        """Call LLM and parse structured response."""

    async def _execute_tool(self, tool_name: str, params: dict) -> dict:
        """Execute tool via registry, handle errors."""
```

### LLMProvider (Protocol)

```python
class LLMProvider(Protocol):
    async def complete(
        self,
        messages: list[Message],
        tools: list[ToolSchema] | None = None
    ) -> LLMResponse: ...

class OpenAIProvider:
    """OpenAI GPT-4o implementation."""
    def __init__(self, api_key: str, model: str = "gpt-4o"): ...
    async def complete(self, messages, tools) -> LLMResponse: ...

class AnthropicProvider:
    """Anthropic Claude implementation."""
    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"): ...
    async def complete(self, messages, tools) -> LLMResponse: ...
```

### Agent Events (for SSE streaming)

```python
@dataclass
class ThoughtEvent:
    type: str = "thought"
    content: str = ""

@dataclass
class ToolCallEvent:
    type: str = "tool_call"
    tool_name: str = ""
    parameters: dict = field(default_factory=dict)

@dataclass
class ToolResultEvent:
    type: str = "tool_result"
    tool_name: str = ""
    result: dict = field(default_factory=dict)

@dataclass
class FinalAnswerEvent:
    type: str = "final_answer"
    summary: str = ""
    root_cause: str = ""
    affected_components: dict = field(default_factory=dict)
    severity: str = ""
    confidence: float = 0.0
    remediation: list[str] = field(default_factory=list)

@dataclass
class ErrorEvent:
    type: str = "error"
    message: str = ""

AgentEvent = ThoughtEvent | ToolCallEvent | ToolResultEvent | FinalAnswerEvent | ErrorEvent
```

---

## 6. API Layer (`graphite/api/`)

### FastAPI App

```python
# app.py
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: build twin, initialize engines, register tools
    twin_manager = TwinManager(TwinBuilder(DATA_DIR))
    twin_manager.initialize()
    twin_manager.clone_working()
    # Store in app state
    app.state.twin_manager = twin_manager
    app.state.sim_engine = SimulationEngine(twin_manager)
    app.state.analysis_engine = AnalysisEngine(twin_manager)
    # ... register tools, create agent
    yield
    # Shutdown: cleanup

app = FastAPI(title="Graphite API", lifespan=lifespan)
```

### Key Endpoints

```python
# routes/agent.py
@router.post("/agent/query")
async def agent_query(request: AgentQueryRequest) -> StreamingResponse:
    """SSE endpoint. Streams agent events as they occur."""

# routes/topology.py
@router.get("/topology/sites")
async def get_sites() -> list[SiteSummary]: ...

@router.get("/topology/sites/{site}")
async def get_site_topology(site: str) -> SiteTopologyResponse: ...

@router.get("/topology/global")
async def get_global_topology() -> GlobalTopologyResponse: ...

# routes/simulation.py
@router.post("/simulation/reset")
async def reset_simulation() -> dict: ...

@router.post("/simulation/inject")
async def inject_fault(request: FaultInjectionRequest) -> dict: ...

# routes/health.py
@router.get("/health")
async def health_check() -> dict: ...
```

### Pydantic Models

```python
# models.py
class AgentQueryRequest(BaseModel):
    query: str
    conversation_id: str | None = None

class FaultInjectionRequest(BaseModel):
    fault_type: Literal["disable_device", "disable_link", "remove_vlan",
                         "disable_bgp_peer", "set_link_latency"]
    parameters: dict

class SiteSummary(BaseModel):
    id: str
    name: str
    device_count: int
    health: str

class GlobalTopologyResponse(BaseModel):
    sites: list[SiteSummary]
    wan_links: list[dict]  # [{source, target, bandwidth, latency_ms, status}]

class SiteTopologyResponse(BaseModel):
    site: str
    site_name: str
    devices: list[dict]
    links: list[dict]
    vlans: list[dict]
    services: list[dict]
    user_groups: list[dict]
```

---

## Dependency Injection Summary

```
TwinBuilder
    ↓ (builds)
TwinManager
    ↓ (provides graph to)
SimulationEngine ←──── ToolContext ────→ AnalysisEngine
                          ↓
                    ToolRegistry
                          ↓
                     ReactAgent
                          ↓
                    FastAPI Routes
```

All wiring happens in `app.py` lifespan. No global singletons.
