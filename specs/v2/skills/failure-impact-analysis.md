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

## Evidence strategy

### Core evidence (always)

1. **Blast radius**: `get_blast_radius(component_id)` — the deterministic
   source of truth for affected devices, services, users, severity.
2. **Redundancy context**: `get_redundancy_status(component_id)` — does
   failover mitigate the impact? Always pair with blast radius.

### Conditional deepening

- **If blast radius shows services affected**: `get_service_dependencies`
  for the key affected services — to explain the dependency chain (direct
  vs transitive). Not needed if no services are in the blast radius.
- **If user asks "can X still reach Y"**: `check_reachability` to verify
  — don't infer from topology.
- **If a fault may already be injected**: `compare_with_baseline` to
  confirm what actually changed.

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
   impact mitigated by failover?
4. **Deepen if warranted** based on what blast radius and redundancy
   showed:
   - Services affected → `get_service_dependencies` for key services.
   - Reachability question → `check_reachability`.
   - Stop once the mechanism is understood and numbers are grounded.
5. **Note what's NOT affected** when it materially changes the picture.

## Critical gaps

- **Blast radius without redundancy.** Always pair — blast radius is
  worst-case, redundancy tells you if failover prevents it.
- **Reporting service impact without the dependency chain.** "3 services
  affected" is less useful than the causal chain. But only expand when
  services are actually in the blast radius.

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
