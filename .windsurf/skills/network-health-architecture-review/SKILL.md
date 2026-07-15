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

## Expected workflow

1. **Global health pass**: `get_site_summary(site)` for each relevant site
   (or all four if the question is network-wide) — device/link up-down
   counts, VLAN/service counts, total users, overall health status.
   `compare_with_baseline()` once, network-wide, to surface any active
   faults immediately rather than discovering them piecemeal.
2. **Structural pass** (only as deep as the question warrants):
   - `get_site_topology(site)` for device/VLAN/service inventory when the
     user wants an architecture walkthrough, not just a health number.
   - `get_single_points_of_failure(site)` — a health/architecture review
     is exactly where resilience gaps belong, even if the user didn't ask
     about redundancy explicitly; a SPOF is a standing risk worth
     surfacing proactively.
   - `get_inter_site_connectivity(site_a, site_b)` when the question
     concerns overall connectivity between sites, or a WAN-dependent
     architecture question.
3. **Search/inventory support**: `search_devices` when the review needs to
   characterize a subset (e.g. "how many firewalls do we have exposed at
   the edge") rather than the whole site.
4. **Prioritize findings.** A review can surface many facts; rank them —
   active faults (from `compare_with_baseline`) first, then SPOFs/resilience
   gaps, then general inventory/structure. Don't present them as an
   undifferentiated list.
5. Device-level telemetry (`cpu_percent`, `memory_percent`, interface
   error/drop counters) is available on individual devices via
   `get_device_info`/`get_device_interfaces` as point-in-time signals —
   useful if the user asks about a specific device's health, but there is
   no historical trend or utilization-threshold tool in Graphite. Do not
   present a single snapshot reading as a capacity trend or forecast.

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
