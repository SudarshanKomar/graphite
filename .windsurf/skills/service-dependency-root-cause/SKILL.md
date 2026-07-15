---
name: service-dependency-root-cause
description: Use when the user reports a symptom (a service is down/degraded/slow, users can't connect, something "seems broken") and wants the underlying cause diagnosed on the Graphite network digital twin — root-cause investigation and service dependency mapping.
---

# Skill: Service Dependency Mapping & Root-Cause Investigation

## When this activates

Symptom-first questions: "ERP is down, what's wrong?", "Why can't
Bangalore WiFi users connect?", "Auth service is degraded, why?", "Users
say access to Jira is slow." The user gives you an effect; you must find
the cause.

## Why this exists

This is the classic escalation shape, and it's the one where jumping to
the first plausible cause is most tempting. The skill enforces the
architect's habit: map the dependency graph, form multiple hypotheses,
and let deterministic tools discriminate between them — rather than
pattern-matching the symptom to a guessed cause.

## Mandatory evidence — do NOT diagnose root cause without these

1. **Baseline comparison**: `compare_with_baseline()` — always call this
   FIRST. If the twin has been mutated, the diff tells you what changed
   and is often the fastest path to root cause. Skip this and you risk
   re-deriving known state from scratch.
2. **Service dependencies**: `get_service_dependencies(service_id)` for
   every service named in the symptom — to understand the dependency chain
   and find which upstream component is actually broken.
3. **Reachability/path verification**: `check_reachability` or
   `trace_route` between the affected users and the degraded service —
   to distinguish "path broken" from "path degraded" from "path fine but
   service down."
4. **Blast radius**: `get_blast_radius(component_id)` on the confirmed
   root cause — for authoritative affected scope in the final answer.

## Expected workflow

1. **Check for known deltas FIRST.** `compare_with_baseline()` — if
   something changed, this is the fastest path to the cause. If the diff
   is non-empty, you likely have your root cause or a strong lead.
2. **Scope the symptom.** Identify the site/service/user-group named or
   implied. `get_site_summary(site)` for overall health;
   `get_service_dependencies` if a service was named directly.
3. **Form candidate hypotheses before tool-calling further**, e.g. for
   "ERP is slow": (a) WAN/path latency, (b) a degraded dependency
   (auth/db), (c) the ERP host device itself. Don't commit to one before
   checking.
4. **Discriminate with targeted tools**:
   - `get_service_dependencies(service_id)` — is a dependency down/degraded?
   - `trace_route` / `check_reachability` — is there a path at all, and at
     what latency, from the affected user group to the service?
   - `get_device_info` / `get_link_info` on suspect components named by
     the dependency graph or trace.
   - `get_vlan_info` when the symptom is connectivity-shaped (can't
     connect vs. can connect-but-slow) — a missing/removed VLAN is a
     distinct failure mode from a degraded link.
5. **Verify the root cause explains ALL symptoms.** If dependency mapping
   suggests a cause, verify it explains the *specific* symptom (e.g. if
   users can't connect at all, a 500ms-latency link is not the
   explanation — a VLAN/reachability failure is). If it doesn't fully
   explain the symptom, investigate further.
6. **Trace transitive impact** once the root cause is confirmed:
   `get_blast_radius(component_id)` on the actual faulty component to get
   the authoritative affected-users/services count for the final answer.

## Common traps to avoid

- **Skipping baseline comparison.** If a fault was injected, the diff
  tells you exactly what changed. Investigating from scratch is slower and
  risks missing the actual mutation.
- **Committing to the first plausible cause.** "Auth is degraded" is a
  symptom, not a root cause. Trace the dependency chain: why is auth
  degraded? Is db-cluster down? Is the host device down?
- **Conflating "can't connect" with "connects but slow."** These are
  different failure classes. "Can't connect" → check reachability, VLANs.
  "Slow" → check latency via `trace_route`, link degradation.
- **Reporting affected scope from inference, not blast radius.** Once you
  identify the root cause, call `get_blast_radius` for authoritative
  numbers rather than counting manually.

## Output structure

- **Root cause first**: the component and failure mode, stated plainly.
- **Causal chain**: root cause → intermediate dependency → observed
  symptom, in 2-4 bullets, each tied to an observation.
- **Affected scope**: from `get_blast_radius`, not re-derived.
- **Alternative hypotheses ruled out** — one line each, only if genuinely
  useful (e.g. "not a WAN latency issue — the link is at baseline
  latency"). Omit if it would just be padding.
- **Remediation**: ordered, concrete steps addressing the root cause.
