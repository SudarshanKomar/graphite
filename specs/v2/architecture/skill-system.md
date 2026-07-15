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
│   └── 02-graphite-reasoning-discipline.md        (always_on)
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
and calibrating confidence to evidence quality — modeled on how a senior
architect reasons under an escalation, not how a textbook explains
networking.

These three compose: reasoning discipline governs the investigation,
response style governs what's surfaced, persona/grounding governs what
counts as a valid fact in either.

---

## Domain skills

Each entry: **trigger shape → why this workflow, not a guess → tools
preferred, in order → what "done" looks like.**

### `failure-impact-analysis/SKILL.md`

- **Trigger shape**: "what happens if X fails/is removed", or "X is down,
  what's the impact" (post-fault investigation of an already-injected
  problem).
- **Why**: `get_blast_radius` is Graphite's signature deterministic
  capability. This skill exists purely to make it the mandatory first
  move instead of narrative guessing, and to require resolving the exact
  component ID first (VLAN → `get_vlan_info` → its `id` field; link →
  `get_links`) since blast radius rejects free-form names.
- **Preferred tools**: `get_vlan_info`/`get_links` (ID resolution) →
  `get_blast_radius` → `get_service_dependencies` / `check_reachability`
  (mechanism) → `compare_with_baseline` (cross-check if a fault may
  already be live).
- **Done**: severity + cause stated first, affected devices/services/user
  count taken verbatim from the blast-radius observation, brief mechanism
  explanation, and what's *not* affected when that's material.

### `redundancy-spof-recovery/SKILL.md`

- **Trigger shape**: "is X redundant", "single points of failure in
  site Y", "is there a failover path", "what's our DR posture for Z".
- **Why**: resilience claims are the second most common place a generic
  assistant substitutes "typical leaf-spine design" assumptions for
  actual computed redundancy. Also folds disaster-recovery-style
  questions in here rather than a separate skill, since Graphite's only
  DR-relevant tool (`get_failover_path`) is a redundancy tool, not a
  distinct capability — a separate "DR skill" would just re-describe the
  same three tools under a different name.
- **Preferred tools**: `get_redundancy_status` (component-level) →
  `get_single_points_of_failure` (site-wide sweep) → `get_failover_path`
  (post-failure behavior/cost) → `get_service_dependencies` (tie the gap
  to actual exposure) → `get_inter_site_connectivity` for whole-site DR
  questions.
- **Done**: a plain verdict (redundant / at-risk / SPOF) before the
  supporting evidence; remediation only if asked, and only grounded in
  what the tools showed is actually missing.

### `service-dependency-root-cause/SKILL.md`

- **Trigger shape**: symptom-first reports — "ERP is down", "users can't
  connect", "X seems slow" — where the user gives an effect and wants the
  cause.
- **Why**: this is the classic root-cause escalation shape and the one
  most prone to premature conclusions. The skill enforces forming
  multiple hypotheses (path/latency vs. dependency vs. host) *before*
  further tool calls, and explicitly warns that "can't connect at all"
  and "connects but slow" are different failure classes (VLAN/reachability
  vs. latency) that must not be conflated.
- **Preferred tools**: `get_site_summary` / `compare_with_baseline`
  (scope + known deltas first) → `get_service_dependencies` →
  `trace_route` / `check_reachability` → `get_device_info` / `get_link_info`
  on the suspect component → `get_blast_radius` on the confirmed root
  cause for the final affected-scope numbers.
- **Done**: root cause stated first, a short causal chain (each link
  tied to an observation), affected scope from blast radius (not
  re-derived), ruled-out alternatives only if genuinely informative.

### `maintenance-change-planning/SKILL.md`

- **Trigger shape**: forward-looking, not-yet-happened — "if we take X
  down for maintenance", "what's the impact of removing VLAN 420 for a
  migration", "validate this change before we make it".
- **Why**: this is where the twin's mutate/reset capability (not just its
  query tools) delivers unique value — a proposed change can actually be
  *run* in a disposable working copy and the real cascaded impact
  observed, not just estimated from a static blast-radius call. The skill
  exists to make the full loop (predict cheaply first → decide if
  simulation is warranted → operate mode explicitly → mutate → verify →
  reset) the default pattern, since without it an agent either mutates
  without predicting first, or forgets to reset the twin afterward.
- **Preferred tools**: `get_blast_radius` + `get_redundancy_status`
  (cheap prediction) → `set_capability_mode(mode="operate")` (stated
  explicitly) → the matching mutation tool → `get_blast_radius` /
  `compare_with_baseline` / `get_service_dependencies` (verify) →
  `reset_simulation` (restore, confirmed).
- **Done**: verdict first (safe / risky / blocked), predicted vs.
  confirmed impact clearly labeled as such, and an explicit statement of
  whether the twin was reset or intentionally left mutated.

### `network-health-architecture-review/SKILL.md`

- **Trigger shape**: broad, not-yet-scoped-to-one-fault — "how healthy is
  the network", "review Bangalore's architecture", "how well-connected
  are our sites".
- **Why**: open-ended questions with no named component are exactly where
  a generic assistant drifts into vague commentary. The skill gives a
  repeatable checklist (health pass → structural pass → proactive SPOF
  check → prioritized findings) so breadth-first reviews are consistent
  rather than ad hoc, and explicitly scopes what device-level telemetry
  (`cpu_percent`, interface error/drop counters) can and cannot support —
  point-in-time signal only, not a capacity trend, since Graphite has no
  historical/utilization-threshold tool.
- **Preferred tools**: `get_site_summary` (per site) →
  `compare_with_baseline` (network-wide) → `get_site_topology` (structural
  depth, if asked) → `get_single_points_of_failure` (proactive, even if
  not asked) → `get_inter_site_connectivity` → `search_devices` for
  inventory characterization.
- **Done**: headline verdict per site/overall, findings prioritized
  (active faults > SPOFs > structural notes), and an explicit scope note
  if coverage was partial.

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
