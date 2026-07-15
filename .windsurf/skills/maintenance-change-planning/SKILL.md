---
name: maintenance-change-planning
description: Use when the user wants to plan a maintenance window, predict the impact of a proposed change before making it, validate a design change, or run a what-if simulation against the Graphite network digital twin (requires operate mode).
---

# Skill: Maintenance & Change-Impact Planning

## When this activates

Forward-looking, not-yet-happened questions: "If we take `sg-leaf-03` down
for maintenance tonight, what breaks?", "What's the impact of removing
VLAN 420 for a migration?", "Can we degrade the BLR-SG link to test
failover behavior?", "Validate this topology change before we do it in
production." These differ from failure-impact analysis in that the fault
hasn't happened — the user wants a *prediction*, optionally validated by
actually simulating it in the twin.

## Why this exists

Graphite's mutation tools plus the baseline/working twin split make this
the one place the digital twin's value is highest: you can *actually run*
the proposed change in a disposable working copy, observe the real
computed impact, and discard it — instead of reasoning abstractly about
what "should" happen. This skill exists to make that predict → verify →
simulate → challenge → conclude loop the default pattern.

## Mandatory evidence — do NOT deliver a maintenance verdict without these

A maintenance safety recommendation is an **operational recommendation**
requiring deep investigation (10-25 tool calls). Before answering, you
MUST have tool-verified evidence for all of:

1. **Impact scope**: `get_blast_radius` on the maintenance target.
2. **Redundancy**: `get_redundancy_status` on the target — does a
   failover path exist?
3. **BGP topology** (if target speaks BGP): `get_device_bgp_summary` on
   both the target AND its peers — is peering 1:1 or full-mesh? Does the
   backup edge router have an alternative BGP path?
4. **Cross-site reachability**: `check_reachability` from EVERY other
   site's edge router to the site being maintained — a change that looks
   safe from one site may break another due to asymmetric peering.
5. **Service dependencies**: `get_service_dependencies` for services
   hosted at or routed through the maintenance target.
6. **Routing verification** (if traffic rerouting is assumed):
   `get_device_routes` on the backup device to confirm routes exist.

Missing any of these is how a "SAFE" verdict becomes "NOT SAFE" after a
user pushback. Get the evidence first.

## Expected workflow

1. **Predict first, cheaply.** Before mutating anything, use read-only
   tools to build the expected picture: `get_blast_radius(component_id)`
   on the target, `get_redundancy_status` for failover,
   `get_device_bgp_summary` on the target and its BGP peers (if any),
   and `check_reachability` from each remote site. This is the minimum
   investigation before forming even a tentative verdict.
2. **Challenge the prediction.** Before committing to a verdict from
   read-only tools alone:
   - If you found "redundancy available" — verify the backup path
     actually works end-to-end (`trace_route` or `check_reachability`
     through the backup device, not just through the primary).
   - If you found "0 users affected" — check whether downstream services
     depend on the target (`get_service_dependencies`).
   - If you found "ECMP enabled" — ECMP on one device does not mean the
     alternative path works. Verify with `get_alternative_paths`.
   - If the target is inter-site — check reachability from ALL remote
     sites, not just one.
3. **Simulate when warranted.** Actually mutating is worth it when: the
   change is compound (multiple components), the user wants to see
   cascading/recomputed service health rather than the static blast
   radius, or the read-only prediction raised concerns that need
   simulation to resolve.
4. **If simulating**: `set_capability_mode(mode="operate")` — state this
   transition explicitly, it's a deliberate action, not a silent default.
5. **Apply the minimal mutation(s)** that model the proposed change
   (`disable_device`, `disable_link`, `set_link_latency`, `remove_vlan`,
   `disable_bgp_peer`, etc. — pick the one matching the real-world action).
6. **Verify comprehensively** post-mutation:
   - `check_reachability` from all affected sites (not just one).
   - `get_blast_radius` (now reflecting cascaded state).
   - `compare_with_baseline` to show all deltas.
   - `get_device_bgp_summary` on peers to confirm which sessions dropped.
   - `get_service_dependencies` for impacted services.
   - `get_alternative_paths` / `trace_route` to verify rerouting.
   - `get_device_routes` on backup devices to confirm route tables.
7. **Restore the twin**: `reset_simulation` once the simulation has served
   its purpose. Confirm the reset happened (mutation count cleared).

## Common traps to avoid

- **Blast radius without redundancy check.** Blast radius shows worst-case
  impact. It does not tell you whether failover prevents it. Always pair
  with `get_redundancy_status` / `get_failover_path`.
- **Accepting ECMP as proof of failover.** ECMP on one device ≠ end-to-end
  backup path working. Verify with `trace_route` through the backup.
- **Checking reachability from one site only.** Inter-site BGP peering is
  often asymmetric (1:1 primary/secondary peering, no cross-mesh). Check
  from ALL remote sites.
- **Skipping BGP.** The difference between 1:1 peering and full-mesh
  peering completely changes the maintenance blast radius. If the target
  speaks BGP, you must inspect the peering topology.
- **"0 users" from blast radius alone.** A device may carry no direct users
  but carry traffic for services that thousands depend on.

## Output structure

- **Prediction/verdict first**: safe / conditionally safe / risky / blocked,
  and why.
- **Computed impact**: blast radius + redundancy + BGP topology findings,
  labeled as predicted (pre-mutation) vs. confirmed (post-simulation).
- **Conditions** (if conditionally safe): specific pre-maintenance actions
  required (e.g. "reroute traffic to secondary edge routers first").
- **Capacity note**: can the backup path/device handle the load? Cite the
  evidence (link bandwidth, alternative path latency).
- **Recommended window/sequencing** if multiple components are involved.
- **Simulation state note**: explicitly confirm whether the twin was
  reset back to baseline at the end, or is intentionally left mutated.
