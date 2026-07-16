---
name: redundancy-spof-recovery
description: Use when the user asks about redundancy, single points of failure (SPOF), failover paths, or disaster-recovery / resilience questions for a device, link, or site in the Graphite network digital twin.
---

# Skill: Redundancy, SPOF & Recovery-Path Analysis

## When this activates

Questions like: "Is `sg-leaf-03` redundant?", "What are the single points
of failure in Bangalore?", "If the primary WAN link fails, is there a
failover path?", "How resilient is our Singapore DC fabric?", "What's our
disaster-recovery posture for the DB cluster?"

## Why this exists

Redundancy claims are exactly where LLMs are tempted to reason from
"typical" leaf-spine/campus design patterns instead of this twin's actual
wiring. Graphite computes redundancy deterministically (parallel links,
alternative paths, ECMP, BFS-based SPOF detection) — this skill exists to
make that the *only* source for resilience claims.

## Evidence strategy

### Core evidence (always)

1. **Redundancy status**: `get_redundancy_status(component_id)` — parallel
   links, alternative paths, ECMP, risk assessment. This is the
   non-negotiable starting point.
2. **Site-wide sweep** (if question is about a site, not a single
   component): `get_single_points_of_failure(site)`.

### Conditional deepening

- **If redundancy shows ECMP or alternative paths, but you're claiming
  "failover works"**: one `check_reachability` or `trace_route` through
  the backup to confirm end-to-end. ECMP on one device ≠ end-to-end path.
- **If component is edge/WAN and speaks BGP**: `get_device_bgp_summary`
  to check peering topology (1:1 vs full-mesh). 1:1 peering means losing
  one edge router eliminates a peer's only path — this is invisible to
  `get_redundancy_status`.
- **If you need failover latency cost**: `get_failover_path` — the backup
  path's latency delta. Only needed if the user cares about performance
  impact, not just availability.
- **If a SPOF is found and the user cares about exposure**:
  `get_service_dependencies` to connect "no redundant path" to the
  services/users actually exposed.

### Stopping condition

If `get_redundancy_status` shows full redundancy (multiple paths, ECMP,
low risk) and no BGP concern exists, the component is redundant — stop.
Deepen only when the core result raises a concern worth resolving.

## Expected workflow

1. **Component-level redundancy**: `get_redundancy_status(component_id)`.
   Evaluate the result — does it show full redundancy or gaps?
2. **Deepen based on results**:
   - Redundancy looks solid → stop (or one backup-path verification if
     claiming failover in the answer).
   - ECMP only, no confirmed alternative device path → verify with one
     `check_reachability` through the backup.
   - Edge/WAN device → `get_device_bgp_summary` to check peering topology.
   - SPOF or at-risk → `get_service_dependencies` to quantify exposure.
3. For site-wide questions: `get_single_points_of_failure(site)`.
4. For "what if we lost site X" DR questions: `get_inter_site_connectivity`
   + the site's SPOF and service list.

## Critical gaps

- **ECMP ≠ end-to-end failover.** Verify backup path if conclusion
  depends on failover.
- **1:1 BGP peering.** Invisible to `get_redundancy_status`. If the
  component is an edge router, check `get_device_bgp_summary`.
- **Parallel links ≠ device redundancy.** Parallel links protect against
  link failure, not device failure.

## Output structure

- **Verdict first**: redundant / at-risk / SPOF, stated plainly.
- **Evidence**: parallel paths (or their absence), alternative path
  latency delta, failover path if any, BGP peering structure — pulled
  directly from tool output.
- **Exposure**: what breaks and how many users/services are exposed if
  this single point fails (tie back to blast-radius skill if the user
  wants that level of detail — don't duplicate a full blast-radius report
  unless asked).
- **Gap remediation** (only if asked or clearly implied): concrete,
  ordered suggestions (e.g. "dual-home `sg-server-03` to `sg-leaf-04`",
  "add cross-peering between primary and secondary edge routers"),
  grounded in what the redundancy/topology tools actually showed is
  missing — not generic best-practice filler.
