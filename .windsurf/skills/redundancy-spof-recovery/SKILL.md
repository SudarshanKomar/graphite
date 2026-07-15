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

## Mandatory evidence — do NOT declare redundancy or SPOF status without these

1. **Redundancy status**: `get_redundancy_status(component_id)` — parallel
   links, alternative paths, ECMP, risk assessment.
2. **Failover path**: `get_failover_path(primary_component)` — does a
   backup path actually exist? What's the latency cost?
3. **End-to-end verification**: `check_reachability` or `trace_route`
   through the backup path — point-level redundancy (parallel links on
   one device) does not guarantee end-to-end connectivity via the backup.
4. **BGP topology** (if edge/WAN component): `get_device_bgp_summary` —
   is peering full-mesh or 1:1? A 1:1 peering topology means losing one
   edge router eliminates a peer's only path.

"Redundancy exists" without `get_redundancy_status` is an assumption, not
a fact. "Failover works" without end-to-end verification is a guess.

## Expected workflow

1. **Component-level redundancy**: `get_redundancy_status(component_id)`
   for the specific device or link in question — parallel link count,
   alternative paths, ECMP status, risk assessment.
2. **Failover behavior**: `get_failover_path(primary_component)` — the
   backup path's latency, the delta versus primary, and whether failover
   is automatic or manual.
3. **End-to-end verification**: Even if `get_redundancy_status` reports
   alternative paths exist, verify the backup path works end-to-end with
   `check_reachability` or `trace_route`. ECMP or parallel links on one
   device do not guarantee the entire backup path is functional.
4. **BGP topology** (for edge/WAN devices): `get_device_bgp_summary` on
   the component and its peers. The difference between 1:1 peering and
   full-mesh peering fundamentally changes whether failover actually works
   at the inter-site level.
5. **Site-wide sweep**: `get_single_points_of_failure(site)` when the
   question is about a site's overall resilience, not one component.
6. **Cross-reference with dependencies**: if the component hosts or
   carries a critical service, pair the redundancy finding with
   `get_service_dependencies` so the answer connects "no redundant path"
   to "which services/users are actually exposed by that gap."
7. For "what if we lost site X entirely" style DR questions, combine
   `get_inter_site_connectivity` (are there still WAN paths to the other
   sites) with the affected site's SPOF and service list — there is no
   single tool for whole-site DR, so state explicitly which pieces of the
   answer are computed vs. reasoned from combining computed facts.

## Common traps to avoid

- **ECMP ≠ end-to-end failover.** A device advertising ECMP means it has
  multiple next-hops. It does not mean the full backup path to the
  destination works. Verify with `trace_route` or `check_reachability`.
- **1:1 BGP peering is invisible to basic redundancy checks.** If
  blr-edge-01 peers only with sg-edge-01 (no cross-peering to sg-edge-02),
  losing sg-edge-01 isolates blr-edge-01 from Singapore even though
  sg-edge-02 is healthy. Only `get_device_bgp_summary` reveals this.
- **Reporting "redundant" based on parallel links alone.** Parallel links
  protect against link failure, not device failure. If the question is
  about device failure, check whether alternative paths exist through
  different devices.

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
