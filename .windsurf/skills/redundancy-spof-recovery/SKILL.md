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

## Expected workflow

1. **Component-level redundancy**: `get_redundancy_status(component_id)`
   for the specific device or link in question — parallel link count,
   alternative paths, ECMP status, risk assessment.
2. **Site-wide sweep**: `get_single_points_of_failure(site)` when the
   question is about a site's overall resilience, not one component. This
   returns every device/link whose failure would isolate part of the site
   — use it to give a complete picture rather than checking one component
   in isolation.
3. **Failover behavior**: `get_failover_path(primary_component)` when the
   question concerns what happens *after* a failure — latency of the
   backup path and the delta versus primary. This is the closest tool to a
   "disaster recovery" answer: it tells you whether recovery is automatic
   and at what cost (added latency), or whether there is no path at all.
4. **Cross-reference with dependencies**: if the component hosts or
   carries a critical service, pair the redundancy finding with
   `get_service_dependencies` so the answer connects "no redundant path"
   to "which services/users are actually exposed by that gap."
5. For "what if we lost site X entirely" style DR questions, combine
   `get_inter_site_connectivity` (are there still WAN paths to the other
   sites) with the affected site's SPOF and service list — there is no
   single tool for whole-site DR, so state explicitly which pieces of the
   answer are computed vs. reasoned from combining computed facts.

## Output structure

- **Verdict first**: redundant / at-risk / SPOF, stated plainly.
- **Evidence**: parallel paths (or their absence), alternative path
  latency delta, failover path if any — pulled directly from tool output.
- **Exposure**: what breaks and how many users/services are exposed if
  this single point fails (tie back to blast-radius skill if the user
  wants that level of detail — don't duplicate a full blast-radius report
  unless asked).
- **Gap remediation** (only if asked or clearly implied): concrete,
  ordered suggestions (e.g. "dual-home `sg-server-03` to `sg-leaf-04`"),
  grounded in what the redundancy/topology tools actually showed is
  missing — not generic best-practice filler.
