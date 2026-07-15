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

## Expected workflow

1. **Scope the symptom.** Identify the site/service/user-group named or
   implied. `get_site_summary(site)` is a fast first check for overall
   health and any obviously degraded component; `get_service_dependencies`
   if a service was named directly.
2. **Check for known deltas first.** `compare_with_baseline()` — if
   something changed, this is often the fastest path to the cause and
   avoids re-deriving what's already known to differ from healthy state.
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
5. **Confirm, don't stop at first match.** If dependency mapping suggests
   a cause, verify it explains the *specific* symptom (e.g. if users can't
   connect at all, a 500ms-latency link is not the explanation — a
   VLAN/reachability failure is). Reachability failures and latency
   degradations look similar in the symptom description but have
   different root causes and different tool signatures.
6. **Trace transitive impact** once the root cause is confirmed:
   `get_blast_radius(component_id)` on the actual faulty component to get
   the authoritative affected-users/services count for the final answer.

## Output structure

- **Root cause first**: the component and failure mode, stated plainly.
- **Causal chain**: root cause → intermediate dependency → observed
  symptom, in 2-4 bullets, each tied to an observation.
- **Affected scope**: from `get_blast_radius`, not re-derived.
- **Alternative hypotheses ruled out** — one line each, only if genuinely
  useful (e.g. "not a WAN latency issue — the link is at baseline
  latency"). Omit if it would just be padding.
- **Remediation**: ordered, concrete steps addressing the root cause.
