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

## Evidence strategy — core + hypothesis challenge

### Core evidence (always gather these)

1. **Impact scope**: `get_blast_radius` on the maintenance target.
2. **Redundancy**: `get_redundancy_status` on the target — does failover
   exist?
3. **BGP topology** (if target speaks BGP): `get_device_bgp_summary` on
   the target — is it a BGP speaker? Who are its peers?

### Hypothesis challenge (mandatory — this is the stopping condition)

After gathering core evidence, form a tentative conclusion. Then ask:

**"My evidence shows the current state with this device UP. What is the
highest-risk assumption I'm making about what happens when it's DOWN?"**

Common highest-risk assumptions for maintenance questions:
- "Remote peers can reach this site through the backup device" — but have
  you checked the *remote peers'* BGP topology? `get_redundancy_status`
  shows the target's redundancy, not whether blr-edge-01 has a BGP
  session to sg-edge-02.
- "Traffic will reroute" — but routing tables and BGP sessions gathered
  with the target UP may not reflect post-failure behavior.
- "Backup device can handle the load" — but have you checked its
  capacity?

**Test the assumption** with one targeted call. The specific test depends
on what the assumption is:
- "Remote peers can reroute" → `get_device_bgp_summary` on a remote peer
  (e.g. blr-edge-01) to check whether it has an alternative path.
- "Backup path works end-to-end" → `check_reachability` through the
  backup device specifically.
- "Services won't break" → `get_service_dependencies` for affected
  services.

If the assumption holds → deliver the answer.
If it fails → revise and deepen around that specific failure.

### Conditional deepening (only if hypothesis challenge reveals a gap)

- **If remote peers have 1:1 peering** (no cross-mesh): the maintenance
  IS dangerous. Check `check_reachability` from the affected remote
  site to confirm the breakage, then issue a conditional/unsafe verdict.
- **If blast radius shows services affected**: `get_service_dependencies`
  for the key services.
- **If rerouting is uncertain**: `get_device_routes` on the backup device.

### Simulate only when warranted

Actually mutating is worth it when: the change is compound, the user
explicitly asks to simulate, or the hypothesis challenge revealed a
concern that needs real cascading-effects computation to confirm.

## Expected workflow

1. **Core evidence.** `get_blast_radius`, `get_redundancy_status`,
   and (if BGP-speaking) `get_device_bgp_summary` on the target.
2. **Tentative conclusion.** Based on core evidence.
3. **Hypothesis challenge.** "What is my highest-risk assumption?" →
   test it with one targeted tool call. For maintenance on a BGP device,
   this is typically: check the *remote peers'* BGP topology to see if
   they can reroute without the target.
4. **If assumption holds** → deliver the answer.
   **If assumption fails** → deepen around the specific failure.
5. **Simulate if warranted.** `set_capability_mode(mode="operate")` →
   mutation → targeted verification → `reset_simulation`.

## Critical gaps to avoid

- **Current-state evidence confused with post-change safety.**
  `get_redundancy_status` on the target shows the target's redundancy,
  not whether remote peers can reach the site without it. For
  maintenance, always ask: "can the *other* devices reach this site
  without the target?" That may require checking a remote peer's BGP
  summary, not just the target's.
- **Blast radius without redundancy.** Always pair.
- **Skipping BGP on inter-site targets.** 1:1 vs full-mesh peering
  changes the entire maintenance impact.

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
