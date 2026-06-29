# ADR-002: BGP Simulation Approach

**Status**: Accepted  
**Date**: 2025-06-22  
**Deciders**: Architecture Lead  

---

## Context

BGP is central to inter-site routing in enterprise networks. The simulation must model BGP realistically enough to demonstrate meaningful failure scenarios (peer down, prefix withdrawal, route convergence) without implementing a full BGP protocol stack.

## Decision

Adopt **BGP-with-prefixes** — a mid-fidelity simulation.

### AS Design
Each site operates as a private Autonomous System:

| Site       | AS Number | Prefix Block   |
|------------|-----------|----------------|
| Bangalore  | AS 65001  | 10.10.0.0/14   |
| London     | AS 65002  | 10.20.0.0/16   |
| New York   | AS 65003  | 10.30.0.0/16   |
| Singapore  | AS 65004  | 10.50.0.0/14   |

### What Is Modeled

1. **eBGP Peering Sessions**: Between edge routers of adjacent sites. Each session has:
   - `peer_ip`: IP of remote peer
   - `peer_as`: Remote AS number
   - `local_as`: Local AS number
   - `state`: `established` | `idle` | `active` (simplified FSM)
   - `prefixes_received`: List of prefixes learned from peer
   - `prefixes_advertised`: List of prefixes announced to peer

2. **Prefix Advertisement**: Each site's edge routers advertise the site's aggregate prefix(es) to their eBGP peers.

3. **AS Path**: Each prefix carries an AS path (list of AS numbers traversed). Used for basic path selection.

4. **Path Selection**: When multiple paths exist to a prefix, prefer shortest AS path length. No MED, local preference, or weight for MVP.

5. **Peer State Changes**: Disabling a BGP peer sets state to `idle`, withdraws all prefixes from that session, and triggers route recalculation on affected devices.

### What Is NOT Modeled

- Full BGP Finite State Machine (Connect, OpenSent, OpenConfirm, etc.)
- BGP timers (keepalive, hold)
- Route reflectors
- iBGP (internal BGP within a site)
- Communities, MED, local preference, weight
- Route dampening
- Graceful restart
- Route aggregation beyond site-level

### BGP Data Structure (Per Device)

```python
bgp_state = {
    "local_as": 65001,
    "router_id": "10.10.0.1",
    "peers": [
        {
            "peer_ip": "10.99.1.2",
            "peer_as": 65002,
            "state": "established",
            "prefixes_received": ["10.20.0.0/16"],
            "prefixes_advertised": ["10.10.0.0/14"],
            "as_path_to_peer": [65001, 65002]
        }
    ]
}
```

### Cascading Effects of BGP Failure

When a BGP peer is disabled:
1. Peer state → `idle`
2. All prefixes from that peer are withdrawn from local RIB
3. Devices that relied on those prefixes for routing lose reachability to those destinations
4. If alternative BGP paths exist (via another peer), traffic re-converges
5. If no alternative path, destination becomes unreachable

This cascade is implemented in the **simulation engine**, not the LLM.

## Consequences

**Positive:**
- Realistic enough for demo scenarios (peer down, prefix withdrawal, path selection)
- Simple to implement (prefix lists + AS paths as data, not protocol)
- Enables meaningful troubleshooting ("why can't BLR reach SG?" → BGP peer down → prefixes withdrawn)

**Negative:**
- Not protocol-accurate (networking experts may notice simplified FSM)
- No convergence timing simulation
- No iBGP means intra-site routing is assumed via IGP/static

**Mitigation:**
- Frame as "topology-level BGP simulation" in docs/demo
- Enough fidelity for blast-radius and troubleshooting use cases

## Alternatives Considered

### 1. BGP-as-Label (Too Simple)
Just label edges as "BGP". No prefixes, no AS paths. Rejected: not realistic enough to impress a networking architect.

### 2. Full BGP Implementation (Too Complex)
Implement full FSM, timers, route selection. Rejected: weeks of work, diminishing returns for demo scenarios.

## Implementation Notes

- BGP state stored as **node attributes** on edge router devices in the graph
- `bgp_state` attribute on each edge router node (contains `local_as`, `router_id`, `peers` list)
- Simulation engine handles peer state transitions and prefix propagation
- Analysis engine computes reachability using both graph topology and BGP prefix tables
- Tools: `get_bgp_summary`, `disable_bgp_peer`, `enable_bgp_peer`, `withdraw_prefix`, `advertise_prefix`
