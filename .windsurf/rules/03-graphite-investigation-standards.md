---
trigger: always_on
description: Minimum evidence standards and investigation depth discipline for Graphite network investigations — prevents premature conclusions and unverified claims. Always active when investigating the Graphite digital twin.
---

# Graphite Investigation Standards — Evidence Before Conclusions

The difference between a good answer and a great answer is never a better
model — it is more evidence. Graphite's tools are your senses. Use them
thoroughly before concluding.

## Match investigation depth to question stakes

Not every question requires the same depth. Classify before investigating:

**Quick lookup** (1-3 tool calls): "Is sg-leaf-03 up?", "What VLAN is on
port X?", "Show me Bangalore's topology." Factual retrieval — answer
directly from the tool result.

**Operational investigation** (5-15 tool calls): "What's the blast radius
of X?", "Why can't users connect?", "What are the SPOFs in Singapore?"
Requires multiple tools to build a complete picture. Don't stop at the
first relevant result — cross-reference and verify.

**Operational recommendation** (10-25+ tool calls): "Is tonight's
maintenance safe?", "Can we take down sg-edge-01?", "What's our biggest
architectural risk?", "Is our DR strategy resilient?" Requires the same
depth a senior engineer would apply before signing a change ticket.
Stopping early here is the primary failure mode to avoid.

When in doubt, investigate more. A thorough answer with strong evidence
is always better than a quick answer that happens to be right.

## Verification mandates — specific claims require specific tools

Never state any of the following without the corresponding tool evidence:

| Claim | Required tool verification |
|---|---|
| "Redundancy exists" / "failover available" | `get_redundancy_status` or `get_failover_path` |
| "No single point of failure" | `get_single_points_of_failure` |
| "Traffic will reroute" / "alternative path exists" | `get_alternative_paths` or `trace_route` |
| "Reachable" / "path exists" | `check_reachability` |
| "N users affected" / "severity = X" | `get_blast_radius` |
| "Service X depends on Y" | `get_service_dependencies` |
| "Nothing has changed" / "baseline state" | `compare_with_baseline` |
| "BGP is healthy" / "peering will hold" | `get_device_bgp_summary` |
| "Routes exist" / "routing will converge" | `get_device_routes` |
| "Capacity is sufficient" / "can handle load" | `get_device_info` + link bandwidth evidence |

If you cannot verify a claim with a tool, state it as an assumption, not
a fact. Use "assuming" or "not verified" rather than asserting it.

## Assumption audit — before every recommendation

Before delivering any operational recommendation (maintenance verdict,
risk assessment, architecture opinion), audit your reasoning:

1. **List your assumptions.** What did you not verify? (e.g., "I assumed
   sg-edge-02 can handle the full traffic load but did not inspect its
   link capacity.")
2. **Which assumptions are verifiable?** If a tool exists to check it,
   check it now — do not deliver the answer with a verifiable but
   unchecked assumption.
3. **Which assumptions remain?** Only truly unverifiable assumptions
   (outside the tool surface) are acceptable, and they must be flagged
   as such in the answer.

## Self-challenge — try to prove yourself wrong

Before delivering your verdict on any operational or architectural
question:

1. State your tentative conclusion internally.
2. Ask: **what evidence would disprove this?** Examples:
   - "I'm saying maintenance is safe — but does the backup path actually
     work end-to-end?" → `check_reachability` / `trace_route` to verify.
   - "I'm saying redundancy exists — but is BGP peering 1:1 with no
     cross-mesh?" → `get_device_bgp_summary` to check.
   - "I'm saying 0 users affected — but are there downstream service
     dependencies I haven't traced?" → `get_service_dependencies`.
   - "I'm saying the network is healthy — but are there standing SPOFs
     that represent latent risk?" → `get_single_points_of_failure`.
3. If the disproving evidence is obtainable via a tool, **call the tool
   before answering**. If it doesn't disprove you, your conclusion is
   stronger. If it does, revise.

This is not optional for operational recommendations.

## Common investigation failures to avoid

These are recurring patterns where the agent stops too early:

- **Blast radius without redundancy check.** `get_blast_radius` shows
  impact assuming full failure. It does not tell you whether failover
  will prevent that failure. Always pair blast radius with
  `get_redundancy_status` / `get_failover_path` for maintenance or
  resilience questions.

- **Claiming "0 users affected" without verifying routing behavior.**
  Blast radius is a static graph computation. It does not model BGP
  reconvergence, routing table changes, or traffic redistribution.
  For maintenance questions, simulate the change and verify reachability.

- **Accepting "ECMP enabled" as proof of working failover.** ECMP on one
  device does not mean the end-to-end backup path works. Verify with
  `trace_route` or `check_reachability` through the backup device.

- **Checking reachability from one site only.** When an edge device or
  WAN component is involved, check reachability from ALL affected sites.
  A change that looks safe from one site may break connectivity from
  another due to asymmetric BGP peering.

- **Skipping BGP topology for inter-site questions.** Inter-site
  connectivity depends on BGP peering structure. If the maintenance
  target speaks BGP, always inspect `get_device_bgp_summary` on both the
  target and its peers. The difference between 1:1 peering and full-mesh
  peering changes the blast radius entirely.

- **Not checking service dependencies.** A device with "no direct users"
  may still carry traffic for services that thousands of users depend on.
  Trace service dependencies before concluding "low impact."
