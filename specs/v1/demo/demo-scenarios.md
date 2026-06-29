# Demo Scenarios

Detailed step-by-step walkthrough for each MVP demo scenario. These are the core demonstrations that prove Graphite's value.

---

## Scenario 1: VLAN 420 Removal — "Why can't WiFi users connect?"

### Setup

**Persona**: Network operator investigating user complaints.

**Pre-condition**: System is at baseline (all healthy).

### Steps

**Step 1 — Operator injects fault via UI**

The operator uses the Fault Injection panel:
- Fault Type: "Remove VLAN"
- VLAN ID: 420
- Site: Bangalore
- Clicks "Inject Fault"

**System response**:
- Simulation engine removes VLAN 420 from working twin
- Cascading effects:
  - `blr-vlan-420` node status set to `"removed"` (node stays in graph for queryability)
  - `carries_vlan` edges from all devices to blr-vlan-420 removed
  - `serves` edge from blr-vlan-420 to `blr-corp-wifi-users` removed
  - User group `blr-corp-wifi-users` (5000 users) loses connectivity
- Topology view updates:
  - VLAN 420 disappears from device details
  - Access switches that served WiFi show yellow/degraded indicator
- Active Faults list shows: "VLAN 420 @ bangalore: removed"

**Step 2 — Operator asks agent**

Types in chat: *"Bangalore WiFi users are reporting they can't connect to the network. What's wrong?"*

**Step 3 — Agent investigates (expected tool calls)**

| Step | Agent Thought | Tool Call | Key Observation |
|---|---|---|---|
| 1 | WiFi issues in Bangalore. Let me check the site health first. | `get_site_summary(site="bangalore")` | Site is "degraded", 1 VLAN issue |
| 2 | Site is degraded. WiFi is usually on Corp WiFi VLAN. Let me check VLAN 420. | `get_vlan_info(vlan_id=420, site="bangalore")` | VLAN 420 status="removed", 0 devices carrying it |
| 3 | VLAN 420 is missing! This is the Corp WiFi VLAN. Let me check what's affected. | `get_blast_radius(component_id="blr-vlan-420")` | 5000 users affected, auth-service degraded for WiFi users |
| 4 | Let me verify — can WiFi users still reach services? | `check_reachability(source="blr-corp-wifi-users", destination="erp-service")` | Unreachable — no VLAN path |
| 5 | Let me check what changed from baseline. | `compare_with_baseline()` | Shows VLAN 420 removed |

**Step 4 — Agent delivers final answer**

```
Summary: Corporate WiFi connectivity failure in Bangalore caused by 
VLAN 420 removal.

Root Cause: VLAN 420 (Corp WiFi, subnet 10.42.0.0/16) has been removed 
from the Bangalore campus network. This VLAN provides network connectivity 
for all corporate wireless users. Without it, WiFi clients cannot obtain 
IP addresses or reach any network services.

Affected Components:
- Devices: blr-core-01, blr-core-02, blr-dist-01, blr-dist-02, 
  10 access switches (VLAN unconfigured)
- Users: ~5,000 corporate WiFi users (blr-corp-wifi-users)
- Services: ERP (unreachable for WiFi users), Auth Service (unreachable 
  for WiFi users), Jira (unreachable for WiFi users)

Severity: CRITICAL
- 5,000 users affected (exceeds critical threshold of 1,000)
- Core business services unreachable for wireless users
- Wired users (VLAN 110) are NOT affected

Confidence: 0.97

Remediation:
1. Restore VLAN 420 on blr-core-01 and blr-core-02 (core switches)
2. Verify VLAN 420 trunk is allowed on distribution switches (blr-dist-01, blr-dist-02)
3. Verify access switch ports still have VLAN 420 in allowed list
4. Confirm DHCP is operational on 10.42.0.0/16 subnet
5. Test WiFi client connectivity after restoration
```

**Step 5 — Blast radius visualization**

The topology view highlights:
- 🔴 Red: All access switches that previously carried VLAN 420
- 🟡 Yellow: Distribution and core switches (partially affected)
- Summary card: "5,000 users affected | Severity: CRITICAL"

---

## Scenario 2: Leaf Switch Failure — "Singapore DC leaf-03 is down"

### Setup

**Persona**: DC operations investigating a switch failure alert.

### Steps

**Step 1 — Inject fault**

- Fault Type: "Disable Device"
- Device: sg-leaf-03
- Clicks "Inject Fault"

**System response**:
- `sg-leaf-03` status → "down"
- All physical links to/from sg-leaf-03 → status "down"
- Links to sg-spine-01 and sg-spine-02 disabled
- Link to sg-server-03 (DB cluster) disabled
- `db-cluster` service → "down" (hosted on sg-server-03, reachable only through sg-leaf-03)
- Services depending on db-cluster (auth-service, erp-service) → "degraded"

**Step 2 — Ask agent**

*"sg-leaf-03 in Singapore DC just went down. What's the impact?"*

**Step 3 — Agent investigates**

| Step | Agent Thought | Tool Call | Key Observation |
|---|---|---|---|
| 1 | Let me check the device status. | `get_device_info(device_id="sg-leaf-03")` | Status: down |
| 2 | What's connected to this leaf switch? | `get_device_interfaces(device_id="sg-leaf-03")` | Connected to spine-01, spine-02, sg-server-03 |
| 3 | Let me check the full blast radius. | `get_blast_radius(component_id="sg-leaf-03")` | DB cluster down, ERP/Auth degraded |
| 4 | Is there redundancy? Can traffic reroute? | `get_redundancy_status(component_id="sg-leaf-03")` | No redundancy for sg-server-03 (single-homed to leaf-03) |
| 5 | What about the services that depend on the DB? | `get_service_dependencies(service_id="db-cluster")` | auth-service and erp-service both depend on db-cluster |
| 6 | Let me check if the spine layer is still healthy. | `get_failover_path(primary_component="sg-leaf-03")` | No failover for server-03 traffic; other leaves still reachable |

**Step 4 — Final answer**

```
Summary: Singapore DC leaf switch failure causing database cluster outage 
and cascading service degradation.

Root Cause: sg-leaf-03 is down, severing connectivity to the DB cluster 
(sg-server-03). The DB cluster is single-homed to leaf-03 with no 
redundant path.

Affected Components:
- Devices: sg-leaf-03 (down), sg-server-03 (isolated)
- Services: db-cluster (DOWN), auth-service (DEGRADED — depends on db-cluster), 
  erp-service (DEGRADED — depends on auth-service and db-cluster)
- Users: All users across all sites that depend on ERP/Auth 
  (~13,000 potential impact)

Severity: CRITICAL
- Core database cluster is completely unavailable
- Cascading impact on authentication and ERP
- No redundant path exists for sg-server-03

Note on Redundancy:
- Spine layer (sg-spine-01, sg-spine-02) is healthy
- Other leaf switches (sg-leaf-01, sg-leaf-02, sg-leaf-04) are operational
- Server racks 1, 2, and K8s cluster are unaffected
- CRITICAL GAP: sg-server-03 (DB cluster) is single-homed to sg-leaf-03

Confidence: 0.95

Remediation:
1. Immediate: Restore sg-leaf-03 (hardware replacement or reboot)
2. If leaf-03 cannot be restored quickly:
   - Migrate DB cluster to a server behind a different leaf switch
   - Or add a secondary link from sg-server-03 to sg-leaf-04 for redundancy
3. Long-term: Dual-home all critical servers to two leaf switches
4. Update monitoring to alert on single-homed critical services
```

---

## Scenario 3: WAN Link Degradation — "BLR-SG traffic is slow"

### Setup

**Persona**: Network engineer investigating performance complaints for cross-site traffic.

### Steps

**Step 1 — Inject fault**

- Fault Type: "Set Link Latency"
- Source: blr-edge-01
- Target: sg-edge-01
- Latency: 500 (ms)
- Clicks "Inject Fault"

**System response**:
- Link blr-edge-01 ↔ sg-edge-01 latency updated from ~55ms to 500ms
- Topology view: WAN link between BLR and SG turns yellow/orange

**Step 2 — Ask agent**

*"Users in Bangalore are complaining that accessing ERP and Jira is very slow. Can you investigate?"*

**Step 3 — Agent investigates**

| Step | Agent Thought | Tool Call | Key Observation |
|---|---|---|---|
| 1 | ERP and Jira are in Singapore. Let me check the path from BLR to SG. | `trace_route(source="blr-corp-wifi-users", destination="erp-service")` | Path exists but total latency 520ms (normally ~60ms) |
| 2 | Very high latency. Let me check the WAN links. | `get_inter_site_connectivity(site_a="bangalore", site_b="singapore")` | WAN link latency: 500ms (normally 55ms) |
| 3 | The BLR-SG WAN link is degraded. Are there alternative paths? | `get_alternative_paths(source="blr-edge-01", destination="sg-edge-01")` | Alt path via LON or NYC exists but much longer |
| 4 | Let me compare with baseline to confirm the change. | `compare_with_baseline()` | blr-edge-01↔sg-edge-01 latency changed: 55ms → 500ms |
| 5 | What's the blast radius of this degradation? | `get_blast_radius(component_id="link-blr-sg-wan")` | All BLR users accessing SG services affected |

**Step 4 — Final answer**

```
Summary: WAN link degradation between Bangalore and Singapore causing 
severe latency for cross-site service access.

Root Cause: The WAN link between blr-edge-01 and sg-edge-01 has degraded 
from 55ms to 500ms latency (~9x increase). All traffic from Bangalore to 
Singapore services traverses this link.

Affected Components:
- Links: blr-edge-01 ↔ sg-edge-01 (latency: 500ms, normally 55ms)
- Services impacted for BLR users: ERP, Jira, Auth (all hosted in SG)
- Users affected: All Bangalore users accessing Singapore services 
  (~8,000 users, ~5,000 WiFi + ~3,000 wired)

Severity: HIGH
- Services are reachable but severely degraded
- Not a complete outage — functionality exists but user experience is poor
- All Bangalore-to-Singapore traffic affected

Alternative Paths:
- BLR → LON → SG: ~180ms (via London relay)
- BLR → NYC → SG: ~210ms (via New York relay)
- Both alternatives are better than current 500ms but worse than 
  normal 55ms direct path

Confidence: 0.93

Remediation:
1. Investigate WAN link quality (contact ISP/MPLS provider)
2. If link cannot be fixed quickly: reroute BLR-SG traffic via London 
   (BLR→LON→SG at ~180ms, still degraded but ~3x better)
3. Monitor link for further degradation
4. Consider setting up automated failover for WAN link latency thresholds
```

---

## Demo Flow for Presentation

Recommended order for a live demo:

1. **Start with Global View**: Show the healthy 4-site topology. Explain the architecture.
2. **Drill into Bangalore**: Show internal campus topology. Point out VLAN structure.
3. **Drill into Singapore DC**: Show leaf-spine fabric. Point out service hosting.
4. **Return to Global View**: Show WAN links with latency.
5. **Run Scenario 1** (VLAN 420): Most dramatic — 5000 users, cascading to services.
6. **Reset, Run Scenario 2** (Leaf switch): Shows redundancy analysis, single-homing gap.
7. **Reset, Run Scenario 3** (WAN degradation): Shows latency analysis, path alternatives.

**Key talking points during demo**:
- Agent uses *deterministic graph engine* for facts, LLM only for reasoning
- Blast radius is computed, not hallucinated
- Path analysis follows actual routing tables
- Cascading effects are propagated automatically
- Agent reasoning is transparent (visible thought process)

---

## Non-Goal Scenarios (Future, Not MVP)

These are explicitly out of scope for MVP but worth mentioning as future work:

- **ACL misconfiguration**: Firewall blocks traffic it shouldn't
- **DNS failure**: Resolution breaks, services appear down
- **BGP route leak**: Wrong prefixes advertised, traffic misdirected
- **Dual-failure**: Two simultaneous failures (ECMP both paths down)
- **Rolling upgrade**: Impact of upgrading devices one at a time
