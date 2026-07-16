---
trigger: always_on
description: Investigation efficiency and evidence standards for Graphite network investigations — optimize for information gain, stop when the highest-risk assumption has been tested. Always active when investigating the Graphite digital twin.
---

# Graphite Investigation Standards — Evidence Before Conclusions

## Core principle: optimize for information gain

Before every tool call, implicitly ask: **will this materially reduce my
remaining uncertainty?** If earlier results already answer the question,
or if the outcome is very unlikely to change the recommendation, skip it.

The goal is not maximum evidence. It is minimum unresolved uncertainty.

Senior engineers do not inspect every routing table. They identify which
uncertainties could change their recommendation, gather the evidence to
resolve those, and stop.

## Investigation loop: gather → conclude → challenge → stop

This is the core reasoning structure for any non-trivial question:

1. **Gather core evidence** for the question type (per the relevant
   skill).
2. **Form a tentative conclusion** from the evidence.
3. **Identify the highest-risk assumption** behind that conclusion — the
   single most likely way it could be wrong. Ask: *what am I relying on
   that I have not directly verified?*
4. **Test it** with one targeted tool call.
5. **If the assumption holds** → deliver the answer.
   **If it fails** → revise the conclusion, deepen the investigation
   around the failure, and repeat from step 3.

This is the stopping condition: you stop when your conclusion's
highest-risk assumption has been tested and survived. Not when evidence
"seems sufficient." Not when a checklist is complete.

### Why this matters

Evidence that describes the **current state** does not automatically
predict the **post-change state**. For example:
- `get_redundancy_status(sg-edge-01)` shows sg-edge-01 has backup paths.
  But the maintenance question is: can *other devices* reach Singapore
  *without* sg-edge-01? That's a different question — it requires
  checking the remote peers' BGP topology, not sg-edge-01's.
- `check_reachability` with the target device UP confirms current
  connectivity. It does not confirm post-maintenance connectivity.

The hypothesis challenge catches this: "I'm concluding maintenance is
safe — but my evidence shows the current state. My highest-risk
assumption is that remote peers can reroute. Have I verified *their*
peering, or only the target's?"

## Stopping heuristic

Continue investigating only while there exists a plausible scenario where
your conclusion is wrong that you have not tested. Stop when:

- Your tentative conclusion's highest-risk assumption has been tested.
- No remaining uncertainty could realistically change the recommendation.
- Additional calls would confirm facts already established, not reveal
  new ones.

Let depth emerge from actual complexity, not from a target call count.

## Verification mandates — claim it only if you checked it

Never state these without tool evidence (or evidence from a tool that
already covered it):

| Claim | Required evidence |
|---|---|
| "Redundancy exists" / "failover available" | `get_redundancy_status` or `get_failover_path` |
| "No single point of failure" | `get_single_points_of_failure` |
| "Traffic will reroute" / "alternative path exists" | `get_alternative_paths`, `trace_route`, or `check_reachability` |
| "N users affected" / "severity = X" | `get_blast_radius` |
| "Service X depends on Y" | `get_service_dependencies` |
| "Nothing has changed" | `compare_with_baseline` |
| "BGP is healthy" / "peering will hold" | `get_device_bgp_summary` |

**Key**: if a previous tool result already established a fact, do not
re-verify it with a redundant call. For example, if
`get_redundancy_status` already reported alternative paths and ECMP
status, you do not also need `get_alternative_paths` unless the
redundancy result raised a specific concern worth investigating further.

If you cannot verify a claim, state it as an assumption, not a fact.

## Avoid confirmation loops

Do NOT repeatedly call the same tool (or equivalent tools) to re-verify
facts already established:

- Do not call `get_device_routes` on multiple devices unless you have a
  specific reason to expect different routing behavior on each.
- Do not call `get_device_bgp_summary` on every edge router if the first
  call already revealed the peering topology pattern (e.g., 1:1 peering).
  Check a second peer only if the first result raises a concern.
- Do not call `check_reachability` for every possible source-destination
  pair. Check representative pairs; expand only if results are
  inconsistent or surprising.

Repeat a tool call only when:
- Different devices may legitimately produce different results.
- Earlier results were contradictory or incomplete.
- A mutation changed state since the last call.

## Critical investigation gaps — still apply

These are the gaps that most commonly produce wrong answers. They are
worth checking even when they add an extra call:

- **Blast radius without redundancy.** Always pair these — blast radius
  is worst-case, redundancy tells you if failover prevents it.
- **ECMP claimed as proof of failover.** ECMP on one device ≠ end-to-end
  backup. If the conclusion depends on failover working, verify the
  backup path.
- **BGP skipped for inter-site questions.** 1:1 vs full-mesh peering
  fundamentally changes maintenance impact. If the target speaks BGP,
  check the peering topology.
- **Services ignored on "no direct users" devices.** A device may carry
  traffic for services thousands depend on. Check dependencies if blast
  radius shows services affected.
- **Current state confused with post-change state.** Evidence gathered
  with the target device UP does not predict behavior with it DOWN.
  For maintenance questions, ask: does my evidence describe the state
  *after* the change, or only the state *before* it?
