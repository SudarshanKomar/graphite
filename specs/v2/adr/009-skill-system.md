# ADR-009: Skill System for Graphite-as-MCP-Server Consumers

**Status**: Accepted
**Date**: 2025-07-14
**Builds on**: ADR-006 (MCP-Native Architecture), ADR-007 (Capability Modes)

---

## Context

ADR-006 made Graphite consumable by any MCP client — including agentic
IDEs such as Windsurf, which can connect to `python -m graphite.mcp`
(stdio transport) and let a user chat directly with the IDE's AI (Cascade)
using Graphite's 36 tools, no custom ReAct agent required.

This "external agent" path is architecturally complete but behaviorally
naive: a generic IDE assistant connecting to Graphite's MCP tools has no
inherent knowledge of:

- The grounding discipline Graphite's own ReAct agent enforces via its
  system prompt (`graphite/agent/prompts/system_prompt.py`) — never guess
  network state, resolve exact graph IDs, respect observe/operate mode.
- The recurring *investigation workflows* that make Graphite valuable:
  blast-radius analysis, redundancy/SPOF checks, root-cause tracing via
  service dependencies, mutate→verify→reset change simulation, and
  health/architecture review.
- The desired response shape: concise, answer-first, evidence-grounded —
  as opposed to a generic assistant's tendency to over-explain.

Without this knowledge, an external agent tends to under-use the deterministic
analysis tools (guessing impact instead of calling `get_blast_radius`),
mishandle capability modes (attempting mutations in observe mode, or never
resetting the twin after a what-if simulation), and produce verbose,
textbook-style answers instead of engineer-to-engineer briefings.

The custom ReAct agent (`graphite/agent/`) already encodes some of this in
its system prompt, but that prompt is internal to the FastAPI process and
is not visible to, or reusable by, an external MCP client such as
Windsurf's Cascade.

## Decision

**Introduce a Skill System, checked into the repository, as a combination of
Windsurf workspace rules (`.windsurf/rules/*.md`) for foundational behavior
and Windsurf skills (`.windsurf/skills/<skill>/SKILL.md`) for domain-specific
workflows that encode Graphite-specific investigation workflows and
communication/reasoning discipline for any AI agent (chiefly Windsurf's
Cascade, connected via the Graphite MCP server) that works with this codebase
or its digital twin.**

Foundational rules are single Markdown files with Windsurf rule frontmatter:

```markdown
---
trigger: always_on
description: <what this rule is for>
---
```

Domain skills are Windsurf skill directories with a `SKILL.md` file:

```markdown
---
name: <skill-name>
description: <used by the model to decide relevance>
---

<skill content: when it activates, why it exists, expected workflow,
preferred tools, expected output structure>
```

Windsurf loads every file under `.windsurf/rules/` and every `SKILL.md` under
`.windsurf/skills/` automatically when the repository is opened — no manual
setup, no application code change, no new runtime dependency. This directly
satisfies the requirement that cloning the repo and opening it in Windsurf
provides the intended behavior out of the box.

### Two tiers of skills

1. **Foundational (`always_on`)** — persona/grounding, response style,
   reasoning discipline. These apply to every Graphite-related
   interaction regardless of topic, mirroring what the internal agent's
   system prompt does unconditionally for every query.
2. **Domain** — one skill per recurring investigation
   shape (failure impact, redundancy/SPOF/recovery, service-dependency
   root cause, maintenance/change planning, health/architecture review).
   Each lives under `.windsurf/skills/<skill>/SKILL.md` with `name` and
   `description` frontmatter; Cascade uses the `description` to decide
   relevance, analogous to picking the right tool — except the "tool" here
   is a reasoning workflow, not a single function call.

### Why Windsurf rules, not application code

Alternatives considered (see below) that would bake this into
`graphite/agent/prompts/` were rejected because that prompt only reaches
the *internal* ReAct agent inside the FastAPI process. The Skill System's
purpose is to raise the floor for *any* agent working against Graphite's
MCP surface — most concretely, a developer or operator who opens this
repository in Windsurf and talks to Cascade directly through the MCP
connection (`python -m graphite.mcp`), which is exactly the "external
agent" consumer ADR-006 was designed to support.

### Relationship to the internal ReAct agent's system prompt

The two are intentionally consistent in substance (grounding rule,
mode discipline, ID resolution, blast-radius-first impact analysis) but
are not code-shared: the system prompt is a runtime string built per
request in Python; the Skill System is static, repository-level Windsurf
configuration. Keeping them separate avoids coupling the MCP-facing skill
docs to FastAPI/agent internals, while both draw from the same underlying
tool contracts (`graphite/mcp/tools.py`) and analysis semantics as their
common source of truth. If the tool surface changes, both need review,
but neither depends on the other's implementation.

## Consequences

**Positive:**
- Zero-setup: works the moment the repo is opened in Windsurf with the
  Graphite MCP server connected — no code change, no extra dependency.
- Reusable across any question shape that recurs in practice, instead of
  a one-off prompt tuned for a single demo scenario.
- Documents *why* each workflow exists alongside *how* to run it, so the
  rules double as onboarding material for contributors (see
  `specs/v2/architecture/skill-system.md`).
- Does not touch `graphite/agent/`, `graphite/mcp/`, or any other runtime
  module — fully additive, no regression risk to existing tests.

**Negative:**
- Two places encode similar guidance (system prompt vs. Windsurf rules) —
  accepted as the necessary cost of reaching an external-agent consumer
  without coupling to FastAPI internals. Both should be updated if the
  tool surface changes meaningfully.
- `model_decision` activation quality depends on Windsurf's own relevance
  matching against each skill's `description` — not something Graphite
  controls or can unit test.

## Alternatives Considered

### 1. Fold all guidance into `graphite/agent/prompts/system_prompt.py`
Rejected as the sole solution: it only reaches the internal ReAct agent.
An external agent (e.g. Windsurf/Cascade connected via MCP stdio) never
sees this prompt.

### 2. Add an MCP `prompts` primitive (server-supplied prompt templates)
ADR-006 explicitly deferred MCP prompts to a future revision ("adds MCP
surface without clear benefit... revisit in V3"). Introducing them now to
carry skill content would reopen that decision under time pressure and
add protocol surface for a benefit Windsurf rules already deliver with
zero code.

### 3. A bespoke in-repo "skills" JSON/YAML file read by nothing
Rejected — would require a consumer to load and honor it. Windsurf rules
are already a first-class, auto-loaded mechanism; inventing a parallel
one with no loader would be dead documentation, not a functioning skill
system.

## Implementation Notes

- Foundational rules live at `.windsurf/rules/` (repository root), numbered
  `00`-`02` (always on).
- Domain skills live at `.windsurf/skills/<skill>/SKILL.md` (repository root).
- Full philosophy, per-skill rationale, and extension guidance:
  `specs/v2/architecture/skill-system.md`.
- No changes to `graphite/mcp/`, `graphite/agent/`, or any test.
