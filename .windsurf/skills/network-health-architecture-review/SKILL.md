---
name: network-health-architecture-review
description: Use for broad, not-yet-scoped-to-one-fault questions about overall network health, a site's or the whole network's architecture, topology review, or "how does X look" style questions on the Graphite network digital twin.
---

# Skill: Network Health & Architecture Review

## When this activates

Open-ended, breadth-first questions rather than a single named
fault/symptom: "How healthy is the network right now?", "Give me an
overview of Bangalore's topology", "Review our Singapore DC architecture",
"Is there anything I should be worried about across the network?", "How
well-connected are our sites?" These lack a specific component to drill
into — the skill is about scoping breadth before (optionally) narrowing.

## Why this exists

Without a named component, there's a strong pull toward vague, generic
commentary ("your network looks reasonably well architected...").  This
skill keeps the review grounded in the same computed tools used for
narrow investigations, just aggregated across a wider scope, and gives a
repeatable checklist so reviews are consistent rather than ad hoc.

## Mandatory evidence — do NOT deliver an architecture review without these

1. **Site health**: `get_site_summary(site)` for every site in scope.
2. **Baseline diff**: `compare_with_baseline()` — surface active faults
   before anything else. A review that misses injected faults is wrong.
3. **SPOFs**: `get_single_points_of_failure(site)` for every site in
   scope — a health review that doesn't surface standing single points of
   failure is incomplete, even if the user didn't specifically ask about
   redundancy. SPOFs are standing risks worth surfacing proactively.
4. **Inter-site connectivity**: `get_inter_site_connectivity(site_a,
   site_b)` for key site pairs — to assess WAN health and BGP peering.

## Expected workflow

1. **Global health pass**: `get_site_summary(site)` for each relevant site
   (or all four if the question is network-wide) — device/link up-down
   counts, VLAN/service counts, total users, overall health status.
   `compare_with_baseline()` once, network-wide, to surface any active
   faults immediately rather than discovering them piecemeal.
2. **SPOF sweep** (mandatory, not optional): `get_single_points_of_failure(site)`
   for every site in scope. This is what separates a review from a status
   check. An architecture review that says "all devices healthy" but
   misses that a critical server is single-homed is incomplete.
3. **Structural pass** (as deep as the question warrants):
   - `get_site_topology(site)` for device/VLAN/service inventory when the
     user wants an architecture walkthrough, not just a health number.
   - `get_inter_site_connectivity(site_a, site_b)` for WAN health, BGP
     peering state, and reachability between sites.
   - `get_device_bgp_summary` on edge routers for inter-site architecture
     questions — peering topology (1:1 vs full-mesh) is a critical
     architectural characteristic.
4. **Search/inventory support**: `search_devices` when the review needs to
   characterize a subset (e.g. "how many firewalls do we have exposed at
   the edge") rather than the whole site.
5. **Prioritize findings.** A review can surface many facts; rank them —
   active faults (from `compare_with_baseline`) first, then SPOFs/resilience
   gaps, then general inventory/structure. Don't present them as an
   undifferentiated list.
6. Device-level telemetry (`cpu_percent`, `memory_percent`, interface
   error/drop counters) is available on individual devices via
   `get_device_info`/`get_device_interfaces` as point-in-time signals —
   useful if the user asks about a specific device's health, but there is
   no historical trend or utilization-threshold tool in Graphite. Do not
   present a single snapshot reading as a capacity trend or forecast.

## Common traps to avoid

- **Healthy devices ≠ healthy architecture.** All devices being "up" does
  not mean the architecture is sound. SPOFs, 1:1 BGP peering, and
  single-homed servers are architectural risks that exist even when
  everything is operational.
- **Skipping inter-site checks.** A per-site review that doesn't examine
  WAN connectivity and BGP peering misses a critical failure domain.
- **Presenting generic advice.** Don't say "you should consider adding
  redundancy" without citing which specific component lacks it and what
  `get_single_points_of_failure` showed.

## Output structure

- **Headline health verdict** per site or overall (healthy / degraded /
  critical), from `get_site_summary`/`compare_with_baseline` directly.
- **Notable findings**, prioritized: active faults > SPOFs/resilience gaps
  > structural observations.
- **Scope note**: if the user asked about "the network" but you only
  reviewed specific sites/components, say so rather than implying full
  coverage.
- Keep it a review, not an audit dump — this pairs with the response-style
  skill: headline + prioritized bullets, full inventory only on request.
