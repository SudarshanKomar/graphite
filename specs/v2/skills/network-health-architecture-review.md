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

## Evidence strategy

### Core evidence (always for a review)

1. **Site health**: `get_site_summary(site)` for sites in scope.
2. **Baseline diff**: `compare_with_baseline()` — surface active faults
   first. A review that misses injected faults is wrong.

### Architecture depth (scale to the question)

- **If user asks about architecture/resilience** (not just health):
  `get_single_points_of_failure(site)` for the sites in scope. This is
  what separates a review from a status check.
- **If question involves WAN or multi-site connectivity**:
  `get_inter_site_connectivity` for the relevant site pair(s).
- **If user wants a structural walkthrough**: `get_site_topology(site)`.
- **If inter-site architecture matters**: `get_device_bgp_summary` on an
  edge router to understand peering topology.

### Stopping condition

For a health check: site summaries + baseline diff may be sufficient.
For an architecture review: add SPOFs for sites in scope and stop unless
specific concerns emerge. Do not check `get_inter_site_connectivity` for
every site pair or `get_device_bgp_summary` on every edge router unless
the question specifically concerns inter-site design.

## Expected workflow

1. **Health pass**: `get_site_summary(site)` for each relevant site.
   `compare_with_baseline()` once to surface active faults.
2. **SPOF sweep** (if architecture/resilience is in scope):
   `get_single_points_of_failure(site)` for sites in scope.
3. **Deepen based on question scope**:
   - WAN question → `get_inter_site_connectivity` for relevant pairs.
   - Structural walkthrough → `get_site_topology`.
   - Inter-site resilience → `get_device_bgp_summary` on one edge router
     per site to understand peering pattern.
4. **Prioritize findings**: active faults > SPOFs > structural
   observations. Don't present them as an undifferentiated list.
5. Device-level telemetry (`cpu_percent`, `memory_percent`) is available
   via `get_device_info` as point-in-time signals — useful if the user
   asks about a specific device, but there is no historical trend tool.
   Do not present a snapshot reading as a capacity trend.

## Critical gaps

- **Healthy devices ≠ healthy architecture.** SPOFs and peering gaps are
  architectural risks that exist when everything is "up."
- **Generic advice without evidence.** Don't recommend "add redundancy"
  without citing what `get_single_points_of_failure` actually showed.

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
