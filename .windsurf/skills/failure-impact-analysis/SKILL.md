---
name: failure-impact-analysis
description: Use when the user asks what would happen if a device, link, VLAN, or service failed/were removed/degraded — blast radius, cascading impact, "what breaks if X goes down" style questions on the Graphite network digital twin.
---

# Skill: Failure Impact / Blast Radius Analysis

## When this activates

Questions shaped like: "What happens if `sg-leaf-03` fails?", "What's the
impact of removing VLAN 420?", "If the BLR-SG link goes down, who's
affected?", or an already-injected fault ("X is down, what's the blast
radius?").

## Why this exists

Blast radius is Graphite's signature capability — impact is *computed* by
the analysis engine (devices affected, services affected, user groups,
total user count, severity + severity factors), not estimated from
general networking intuition. The single most valuable thing this skill
does is stop the model from guessing impact and force it through
`get_blast_radius`.

## Mandatory evidence — do NOT assess impact without these

1. **Blast radius**: `get_blast_radius(component_id)` — the deterministic
   source of truth. Always call this.
2. **Service dependencies**: `get_service_dependencies` for every service
   listed in the blast radius — to explain *why* downstream services are
   affected and whether dependencies are direct or transitive.
3. **Redundancy context**: `get_redundancy_status(component_id)` — does
   failover exist that could mitigate the impact? Blast radius shows
   worst-case; redundancy shows whether that worst case is the actual case.

## Expected workflow

1. **Resolve the exact component ID.** Blast radius takes a graph ID, not
   a free-form name:
   - Device → its ID directly (e.g. `sg-leaf-03`).
   - VLAN → call `get_vlan_info(vlan_id, site)` first, use the returned
     `id` field (e.g. `blr-vlan-420`).
   - Service → its service ID (e.g. `erp-service`).
   - Link → its link ID (e.g. `link-blr-sg-wan`); `get_links` can help
     resolve this if unknown.
2. **Compute impact**: `get_blast_radius(component_id)` — lead the answer
   with severity, affected devices/services/users from this result.
3. **Check redundancy**: `get_redundancy_status(component_id)` — is the
   impact mitigated by failover? Blast radius shows what breaks IF the
   component is fully down with no failover. Redundancy status tells you
   whether that is the realistic outcome or whether traffic reroutes.
4. **Explain mechanism, don't just report the number.** Pull in supporting
   context so the "why" is grounded, not asserted:
   - `get_service_dependencies` for services in the blast radius, to show
     *why* a downstream service is affected (direct vs transitive).
   - `get_device_info` / `get_device_interfaces` for what the component
     connects to.
   - `check_reachability` between an affected user group and a key service
     when the user's question is framed as "can users still reach X".
5. **Note what's NOT affected** when it materially changes the picture
   (e.g. "wired users on a different VLAN are unaffected") — this is often
   what separates a good investigation from a shallow one.
6. If investigating a fault that may already be injected, cross-check with
   `compare_with_baseline` to confirm what actually changed versus what the
   user believes changed.

## Common traps to avoid

- **Blast radius without redundancy.** Blast radius is worst-case. If
  redundancy exists, the actual impact may be lower. Always pair them.
- **Reporting service impact without understanding the dependency chain.**
  "3 services affected" is less useful than "db-cluster is down → auth
  depends on it → ERP depends on auth." Use `get_service_dependencies`.
- **Skipping reachability when users ask "can X still reach Y."** Don't
  infer reachability from topology — verify it with `check_reachability`.

## Output structure

- **Answer first**: severity + one-line cause.
- **Affected**: devices / services / user count, from the blast-radius
  observation directly (don't recompute or estimate).
- **Redundancy/failover**: does mitigation exist? From
  `get_redundancy_status`. If yes, the effective impact may differ from
  worst-case blast radius — state both.
- **Mechanism**: 1-3 sentences on *why* — the dependency or topology path
  that explains the propagation.
- **Not affected** (only if relevant and confirmed).
- Skip remediation here unless asked — this skill is about impact, not
  fix planning (see the redundancy/SPOF and maintenance-planning skills
  for that).
