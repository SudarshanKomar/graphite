# Skill System — Design & Reference

Companion to [ADR-009](../adr/009-skill-system.md). This document is the
detailed reference: philosophy, per-skill rationale, activation behavior,
worked examples, and guidance for adding new skills. It is the primary
onboarding doc for anyone extending `.windsurf/rules/` (foundational rules)
and `.windsurf/skills/` (domain skills).

---

## Philosophy

Graphite is not a CLI wrapper around MCP tools, and it is not a generic
"ask questions about JSON" assistant. Reading the tool catalogue
(`graphite/mcp/tools.py`) and the demo scenarios
(`specs/v1/demo/demo-scenarios.md`) makes the product shape clear: every
tool answers a **topology or impact reasoning** question — device/link/
VLAN inspection, path/reachability, blast radius, service dependencies,
redundancy/SPOF/failover, site/inter-site topology, and baseline diffing.
There is deliberately no ping, no live interface configuration, no
terminal access, no "typical topology" assumptions — the mutation tools
exist to *simulate* network conditions (fault injection, what-if
analysis), not to operate a real device.

Two consumer paths exist for this tool surface (ADR-006):

1. **Internal**: FastAPI → custom ReAct agent → in-process MCP calls. This
   path already has tailored behavior via
   `graphite/agent/prompts/system_prompt.py`.
2. **External**: any MCP client — most relevantly, a developer/operator
   who opens this repository in **Windsurf** and connects to
   `python -m graphite.mcp` (stdio), then talks to Cascade directly using
   Graphite's tools. This path had *no* tailored behavior — Cascade would
   use the tools competently as a generic assistant, but without any of
   Graphite's investigation discipline or house style.

The Skill System closes that gap for path 2, using Windsurf's native rule
and skill mechanisms (`.windsurf/rules/*.md` for foundational rules and
`.windsurf/skills/<skill>/SKILL.md` for domain skills), so that opening this
repository in Windsurf is sufficient — no manual prompt-copying, no separate
configuration step.

**A skill is a reasoning workflow, not a tool wrapper.** Each domain skill
below encodes a *sequence and rationale* for calling several tools
together to answer a class of question well — mirroring how a senior
network engineer would actually investigate, not a 1:1 mapping to a
single MCP tool.

---

## Directory layout

```
.windsurf/
├── rules/
│   ├── 00-graphite-persona-and-grounding.md      (always_on)
│   ├── 01-graphite-response-style.md             (always_on)
│   ├── 02-graphite-reasoning-discipline.md        (always_on)
│   └── 03-graphite-investigation-standards.md     (always_on)
└── skills/
    ├── failure-impact-analysis/SKILL.md
    ├── redundancy-spof-recovery/SKILL.md
    ├── service-dependency-root-cause/SKILL.md
    ├── maintenance-change-planning/SKILL.md
    └── network-health-architecture-review/SKILL.md
```

Numbering convention: `00`-`09` reserved for foundational, always-on rules
in `.windsurf/rules/`; domain skills live under `.windsurf/skills/<skill>/SKILL.md`
and are activated by Cascade from their `description`. This leaves room to
insert new rules in either tier without renumbering everything.

Foundational rules use Windsurf's rule frontmatter:

```markdown
---
trigger: always_on
description: <what this rule is for>
---
```

Domain skills use Windsurf's skill frontmatter:

```markdown
---
name: <skill-name>
description: <what this skill is for>
---
```

The `always_on` rules are injected into every Cascade turn in this workspace.
The skills are offered by Cascade, which decides relevance from the `description`
field — the same mechanism as tool selection, so descriptions are written the
same way the MCP tool descriptions are: specific, example-bearing, and phrased
around the user's likely wording.

---

## Foundational skills (always on)

### `00-graphite-persona-and-grounding.md`

**Why it exists**: the single highest-leverage rule. Without it, a
generic assistant will answer network questions from general knowledge
("core switches are usually redundant...") instead of this twin's actual,
tool-verified state. It establishes:
- The grounding rule (every factual claim ← a tool observation).
- The two-twin model (baseline vs. working) and when to reach for
  `compare_with_baseline`.
- Capability-mode discipline (observe default; operate is a deliberate,
  stated transition; mutations get reset when their purpose is served).
- ID resolution discipline (never guess graph IDs; look them up).
- An explicit boundary of what Graphite is not (no ping, no config, no
  terminal) so Cascade declines out-of-scope requests plainly.

### `01-graphite-response-style.md`

**Why it exists**: directly addresses the stated pain point — LLMs
over-explain. Encodes answer-first / evidence-second / action-if-relevant
/ details-on-demand, with explicit anti-patterns (re-explaining topology
before answering, dumping raw tool JSON, tri-repeating the same
conclusion under three headings).

### `02-graphite-reasoning-discipline.md`

**Why it exists**: keeps the *investigation* rigorous even though the
*output* (per the style skill) is short. Requires considering competing
hypotheses before committing, distinguishing observation from inference,
and calibrating confidence to evidence quality. Includes a **pre-answer
quality gate** — a 5-point checklist (evidence test, assumption test,
completeness test, contradiction test, self-challenge test) that the
agent runs silently before delivering any recommendation. The gate's
purpose: the agent's first answer should match the quality it produces
when challenged, without requiring a user nudge.

### `03-graphite-investigation-standards.md`

**Why it exists**: the **keystone** rule that governs investigation
efficiency. While `02` establishes reasoning philosophy (how to think),
`03` establishes investigation process (when to gather more evidence and
when to stop). Introduces:
- **Information-gain principle**: before every tool call, ask "will this
  reduce an uncertainty that could change my recommendation?" If not,
  skip it.
- **Stopping heuristic**: stop when the next tool call is unlikely to
  change the recommendation. Depth emerges from actual complexity, not
  target call counts.
- **Verification mandates**: specific factual claims require specific
  tool evidence — but with an "already established" exception to prevent
  redundant calls.
- **Confirmation-loop anti-pattern**: do not call the same tool on
  multiple devices to re-confirm a fact already established.
- **Focused assumption audit and self-challenge**: verify remaining
  uncertainties only if they could realistically change the
  recommendation; challenge with one targeted check, not exhaustive
  exploration.

These four compose: reasoning discipline governs how to think,
investigation standards govern what evidence to collect and when to stop,
response style governs what's surfaced, persona/grounding governs what
counts as a valid fact in any of them.

---

## Domain skills

Each entry: **trigger shape → why this workflow → core evidence (always
gathered) → conditional deepening (only if core raises concerns) →
stopping condition → output structure.**

Every domain skill uses a **"core + conditional deepening"** evidence
strategy. Core evidence is the small set of tools that always runs (2-3
tools). Conditional deepening lists additional tools that run only when
core evidence raises a specific concern. This prevents checklist-driven
over-investigation while preserving the verification mandates from
rule `03`.

### `failure-impact-analysis/SKILL.md`

- **Trigger shape**: "what happens if X fails/is removed", or "X is down,
  what's the impact".
- **Core evidence**: `get_blast_radius` + `get_redundancy_status`.
- **Conditional**: service dependencies (only if blast radius shows
  services affected), reachability (only if user asks "can X reach Y"),
  baseline comparison (only if fault may already be injected).
- **Done**: severity + affected scope + redundancy mitigation.

### `redundancy-spof-recovery/SKILL.md`

- **Trigger shape**: "is X redundant", "SPOFs in site Y", "failover
  path", "DR posture for Z".
- **Core evidence**: `get_redundancy_status` (component) or
  `get_single_points_of_failure` (site-wide).
- **Conditional**: end-to-end verification (if claiming failover works),
  `get_device_bgp_summary` (if edge/WAN component), `get_failover_path`
  (if user cares about latency cost), service dependencies (if SPOF found
  and exposure matters).
- **Done**: plain verdict before evidence.

### `service-dependency-root-cause/SKILL.md`

- **Trigger shape**: symptom-first — "ERP is down", "users can't
  connect", "X seems slow".
- **Core evidence**: `compare_with_baseline` (first, always) +
  `get_service_dependencies` (dependency chain).
- **Conditional**: reachability (connectivity symptom), trace_route
  (latency symptom), blast radius (after root cause confirmed, for
  scope). If baseline diff explains the symptom, shortcut the full
  hypothesis cycle.
- **Done**: root cause + causal chain + blast-radius scope.

### `maintenance-change-planning/SKILL.md`

- **Trigger shape**: forward-looking — "is maintenance safe", "what
  breaks if we take X down".
- **Core evidence**: `get_blast_radius` + `get_redundancy_status` +
  `get_device_bgp_summary` on target (if BGP-speaking).
- **Conditional**: cross-site reachability (only if BGP shows 1:1
  peering or asymmetric risk), service dependencies (only if blast radius
  shows services affected), routing tables (only if conclusion depends on
  traffic rerouting), simulation (only if compound change or user
  requests it).
- **Done**: verdict + impact + conditions for conditional safety.

### `network-health-architecture-review/SKILL.md`

- **Trigger shape**: broad — "how healthy is the network", "review
  architecture", "how well-connected are sites".
- **Core evidence**: `get_site_summary` per site in scope +
  `compare_with_baseline`.
- **Conditional**: SPOF sweep (if architecture/resilience is in scope),
  inter-site connectivity (if WAN question), site topology (if structural
  walkthrough), BGP summary (if inter-site design question).
- **Done**: headline verdict + prioritized findings.

---

## Why some candidate categories were *not* made separate skills

The task brief listed more candidate categories than were implemented.
Deliberate scoping decisions:

- **Capacity assessment**: `network_state/telemetry_snapshot.json` has
  point-in-time CPU/memory/interface counters for a handful of devices,
  surfaced via `get_device_info`/`get_device_interfaces`, but there is no
  historical trend, no utilization threshold, and no bandwidth-vs-demand
  computation anywhere in the analysis engine. A dedicated "capacity
  assessment" skill would have to invent a workflow the tools cannot
  actually support. Instead, the health/architecture-review skill notes
  what telemetry *is* available and explicitly warns against treating a
  snapshot as a trend.
- **Disaster-recovery planning** and **post-change validation**: folded
  into the redundancy/SPOF skill and the maintenance/change-planning
  skill respectively, rather than given standalone files, because each
  would otherwise just restate the same tool sequence under a different
  name (`get_failover_path` *is* the DR-relevant tool; "verify after
  mutating" is a step inside change planning, not a distinct trigger
  shape a user asks about on its own).
- **Design validation**: this is the same workflow as change-impact
  prediction (propose a topology change, predict/simulate its impact) —
  covered by the maintenance/change-planning skill rather than
  duplicated.

---

## Relationship to the internal ReAct agent

`graphite/agent/prompts/system_prompt.py` encodes similar substance
(grounding, mode discipline, ID resolution, blast-radius-first impact
analysis) for the *internal* agent, at runtime, in Python. The Skill
System is intentionally not code-shared with it (see ADR-009's
"Alternatives Considered" for why an MCP `prompts` primitive or reusing
the system-prompt module directly were rejected). Both should be kept in
substantive sync if the MCP tool surface changes, but each can evolve
independently — the system prompt is constrained by what fits a single
LLM context turn built per-request, while a Windsurf rule can be as
example-rich as is useful without any runtime cost.

---

## Validation performed

- Confirmed `.windsurf/rules/*.md` and `.windsurf/skills/<skill>/SKILL.md`
  are picked up automatically by Windsurf on opening this repository — no
  `mcp.json`/config changes required for the rules/skills themselves
  (`mcp.json` is a separate, pre-existing mechanism for connecting the
  Graphite MCP *server*, documented in `specs/v2/architecture/mcp-server-design.md`
  and referenced in `graphite/mcp/__main__.py`; the two are complementary,
  not coupled).
- No changes to `graphite/agent/`, `graphite/mcp/`, `graphite/analysis/`,
  `graphite/simulation/`, or any test file — this is a purely additive,
  documentation/configuration-level change with zero regression surface.
  `cd backend && python -m pytest` is unaffected.

---

## Extending the Skill System

To add a new skill:

1. Confirm it's grounded in an actual tool workflow — check
   `graphite/mcp/tools.py` (and the underlying `graphite/analysis/`
   module if unsure what's computable) before writing the skill. If the
   workflow requires a tool that doesn't exist, that's a product gap, not
   a skill to write around with guesses.
2. Create `.windsurf/skills/<name>/SKILL.md` with `name: <name>` and a
   `description` phrased around how a user would actually ask the question
   (mirror the style of existing tool descriptions in `graphite/mcp/tools.py`).
3. Follow the section structure used above: When this activates / Why
   this exists / Expected workflow (ordered, tool-by-tool with rationale)
   / Output structure.
4. Add an entry to this document (rationale) and, if the addition
   reflects a genuine architectural decision (not just an additive doc
   change), consider whether it warrants its own ADR or is covered by
   ADR-009.
5. If a candidate skill would just restate an existing skill's tool
   sequence under a different name (as with DR/redundancy above), fold it
   into the existing skill instead of creating a near-duplicate.
