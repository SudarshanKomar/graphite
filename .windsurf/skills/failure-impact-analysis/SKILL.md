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

## Expected workflow

1. **Resolve the exact component ID.** Blast radius takes a graph ID, not
   a free-form name:
   - Device → its ID directly (e.g. `sg-leaf-03`).
   - VLAN → call `get_vlan_info(vlan_id, site)` first, use the returned
     `id` field (e.g. `blr-vlan-420`).
   - Service → its service ID (e.g. `erp-service`).
   - Link → its link ID (e.g. `link-blr-sg-wan`); `get_links` can help
     resolve this if unknown.
2. **Compute impact**: `get_blast_radius(component_id)` — this is the
   deterministic source of truth for affected devices, services, user
   groups, total users, severity, and severity factors. Lead the answer
   with this.
3. **Explain mechanism, don't just report the number.** Pull in supporting
   context so the "why" is grounded, not asserted:
   - `get_device_interfaces` / `get_device_info` for what the component
     connects to.
   - `get_service_dependencies` for any service in the blast radius, to
     show *why* a downstream service is affected (direct vs transitive
     dependency).
   - `check_reachability` between an affected user group and a key service
     when the user's question is framed as "can users still reach X".
4. **Note what's NOT affected** when it materially changes the picture
   (e.g. "wired users on a different VLAN are unaffected") — this is often
   what separates a good investigation from a shallow one, and it's a
   directly observable fact, not a guess, once you've inspected the
   topology.
5. If investigating a fault that may already be injected, cross-check with
   `compare_with_baseline` to confirm what actually changed versus what the
   user believes changed.

## Output structure

- **Answer first**: severity + one-line cause.
- **Affected**: devices / services / user count, from the blast-radius
  observation directly (don't recompute or estimate).
- **Mechanism**: 1-3 sentences on *why* — the dependency or topology path
  that explains the propagation.
- **Not affected** (only if relevant and confirmed).
- Skip remediation here unless asked — this skill is about impact, not
  fix planning (see the redundancy/SPOF and maintenance-planning skills
  for that).
