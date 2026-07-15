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
what "should" happen. This skill exists to make that mutate → verify →
reset loop the default pattern instead of a one-off improvisation, and to
keep it safe (always ends with a clean twin unless the user says
otherwise).

## Expected workflow

1. **Predict first, cheaply.** Before mutating anything, use read-only
   tools to build the expected picture: `get_blast_radius(component_id)`
   on the target (this already tells you the impact of the component
   being *down*, which is what most maintenance windows are), plus
   `get_redundancy_status` to check whether the maintenance window has a
   safe failover. Many "what if we do X" questions can be fully answered
   this way with zero mutation.
2. **Decide if simulation is warranted.** Actually mutating is worth it
   when: the change is compound (multiple components), the user wants to
   see cascading/recomputed service health rather than the static blast
   radius, or they explicitly ask to "simulate"/"test" it.
3. **If simulating**: `set_capability_mode(mode="operate")` — state this
   transition explicitly, it's a deliberate action, not a silent default.
4. **Apply the minimal mutation(s)** that model the proposed change
   (`disable_device`, `disable_link`, `set_link_latency`, `remove_vlan`,
   `disable_bgp_peer`, etc. — pick the one matching the real-world action).
5. **Verify with query tools** post-mutation: `get_blast_radius` again
   (now reflecting cascaded/recomputed state), `compare_with_baseline` to
   show exactly what the working twin now differs by, and
   `get_service_dependencies`/`check_reachability` for anything the user
   specifically cares about.
6. **Restore the twin**: `reset_simulation` once the simulation has served
   its purpose — unless the user explicitly wants the change to persist
   for further discussion in the same session. Confirm the reset happened
   (mutation count cleared) rather than assuming it.

## Output structure

- **Prediction/verdict first**: safe to proceed / risky / blocked, and why.
- **Computed impact**: blast radius + redundancy findings, labeled as
  predicted (pre-mutation) vs. confirmed (post-mutation simulation) so the
  user knows which is which.
- **Recommended window/sequencing** if multiple components are involved
  (e.g. "drain traffic before disabling X because Y has no failover").
- **Simulation state note**: explicitly confirm whether the twin was
  reset back to baseline at the end, or is intentionally left mutated.
