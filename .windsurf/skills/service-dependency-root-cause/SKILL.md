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

## Evidence strategy

### Fast path — check baseline diff first

`compare_with_baseline()` is always the first call. If the twin has been
mutated, the diff often reveals the root cause immediately. If the diff
directly explains the symptom, you can shortcut the full hypothesis
cycle.

### Core evidence

1. **Baseline diff**: `compare_with_baseline()` — first call, always.
2. **Service dependencies**: `get_service_dependencies(service_id)` for
   the named/implied service — to map the dependency chain.

### Conditional deepening

- **If symptom is connectivity-shaped** ("can't connect"): one
  `check_reachability` to confirm path is broken, and `get_vlan_info` if
  a VLAN issue is plausible.
- **If symptom is latency-shaped** ("slow"): `trace_route` to measure
  path latency.
- **If baseline diff identified the cause**: you may not need the
  dependency or reachability calls — the diff is the evidence.
- **Once root cause is confirmed**: `get_blast_radius(component_id)` for
  authoritative affected scope in the final answer.

### Stopping condition

Stop when you have identified a root cause that explains the specific
symptom, and have `get_blast_radius` numbers for the scope. Do not
continue investigating alternative hypotheses if the confirmed cause
fully explains the symptom.

## Expected workflow

1. **Check for known deltas.** `compare_with_baseline()` — if something
   changed, evaluate whether it explains the symptom. If yes, you have a
   strong lead.
2. **Map dependencies.** `get_service_dependencies` for the affected
   service — is an upstream dependency down?
3. **Discriminate hypotheses with targeted tools** (only the tools that
   resolve the remaining uncertainty):
   - Connectivity question → `check_reachability`.
   - Latency question → `trace_route`.
   - Suspect component → `get_device_info` or `get_link_info`.
   - VLAN question → `get_vlan_info`.
4. **Confirm the root cause explains the symptom.** If users can't
   connect at all, a 500ms link is not the explanation — look for
   VLAN/reachability failure instead.
5. **Get authoritative scope**: `get_blast_radius(component_id)` on the
   confirmed root cause.

## Critical gaps

- **Skipping baseline comparison.** If a fault was injected, the diff
  tells you exactly what changed. Always check first.
- **Committing to the first plausible cause.** Trace the dependency chain
  — "auth is degraded" is a symptom, not a root cause.
- **Conflating "can't connect" with "slow."** Different failure classes
  need different tools (reachability vs trace_route).

## Output structure

- **Root cause first**: the component and failure mode, stated plainly.
- **Causal chain**: root cause → intermediate dependency → observed
  symptom, in 2-4 bullets, each tied to an observation.
- **Affected scope**: from `get_blast_radius`, not re-derived.
- **Alternative hypotheses ruled out** — one line each, only if genuinely
  useful (e.g. "not a WAN latency issue — the link is at baseline
  latency"). Omit if it would just be padding.
- **Remediation**: ordered, concrete steps addressing the root cause.
