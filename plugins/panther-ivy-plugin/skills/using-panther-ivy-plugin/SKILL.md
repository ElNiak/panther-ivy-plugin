---
name: using-panther-ivy-plugin
description: "You MUST consult this on starting any panther-ivy-plugin session. Establishes the 1% rule, iron-law primer, methodology routing (NCT/NACT/NSCT), and workspace awareness. Injected at SessionStart as EXTREMELY_IMPORTANT context."
user-invocable: false
---

# Using panther-ivy-plugin

**Type:** rigid — follow exactly, do not adapt away discipline.

## Skill-trigger discipline

### 1% rule

If you think there is even a 1% chance that a panther-ivy-plugin skill might apply to your task, you ABSOLUTELY MUST invoke it via the `Skill` tool. The `routing-rules.json` matchers are the precision layer; this rule is the catch-all backup for inputs the matchers miss.

When no panther-ivy-plugin skill applies, default to `Skill(skill="panther-ivy-plugin:workflow-navigate")` — it is the routing hub and will choose the right workflow or none.

User instructions override skills; skills override default behavior. Iron laws override all three (see `.claude/rules/iron-laws.md`).

### Skill-tool invocation, not paraphrase

When a skill applies, you MUST invoke the `Skill` tool. Do NOT paraphrase the skill body or provide guidance from memory — load the current skill content via the tool. Skill bodies evolve; cached recall drifts.

## Methodology routing

Three testing methodologies determine which workflow + reference skills load:

- **NCT (compliance testing)** — RFC compliance against IUTs. Workflow: `build` → `verify` → `review`. Reference skills: `methodology-reference`, `specification-patterns`, `ivy-writing-guide`.
- **NACT (security testing)** — adversarial / APT-style attacks. Workflow: `build` (with apt-attack-patterns scope) → `verify`. Reference skill: `apt-attack-patterns`.
- **NSCT (simulation testing)** — Shadow Network Simulator scenarios. Workflow: `build` → emits experiment-config sidecar at Phase 6.

If methodology is unclear, ask the user before proceeding.

## Iron laws (canonical)

Four iron laws govern this plugin's workflow discipline. Read `.claude/rules/iron-laws.md` for the canonical wording. Each rigid workflow skill body inlines a 1-2-sentence summary of the iron law it is bound by.

| Iron law | Workflow bound | One-line binding |
|---|---|---|
| `NO_FIX_WITHOUT_VERIFY` | verify | No claim of resolution without a fresh `ivy_verify` / `ivy_compile` tool result from the current turn. |
| `NO_LAYER_WITHOUT_SCAFFOLD` | build | `ivy_diagnostics(mode=structural)` MUST be SOUND on the predecessor layer before Write/Edit on layer N. |
| `NO_QUALITY_WITHOUT_COVERAGE` | review | Every quality verdict MUST cite a fresh `ivy_coverage` / `ivy_quality` tool output. |
| `STALENESS_RULE` | all | Re-run if the include closure was edited since the prior tool result. |

A fifth iron law `PLUGIN_3LOOP` is referenced by `plugin-self-mod` for the plugin-source 3-agent loop (implementer → spec-reviewer → conventions-reviewer); deferred to canonical-rule cleanup pass.

## Workspace awareness

The plugin operates in three modes:

- **Workspace-set**: `/set-workspace <protocol>` was run; PreToolUse hooks block edits outside the active workspace; MCP tools default to that workspace.
- **Workspace-clear**: no active workspace; tools accept any path; `navigate` Phase 1 will detect and prompt.
- **Multi-workspace**: rare, but per-skill `references/` may load workspace-specific patterns.

Check the active workspace via `ivy_workspace(action="get")`.

## Skill catalog

**Workflow skills** (rigid — follow exactly):

- `navigate` — routing hub.
- `build` — protocol model construction.
- `verify` — verify-compile-IUT cycle.
- `review` — coverage + quality audit.
- `triage` — MCP/LSP/Serena stack health.
- `knowledge-capture` — session learning capture.
- `completion-gate` — pre-claim verification gate (5-step IDENTIFY→RUN→READ→VERIFY→THEN-claim).
- `plugin-self-mod` — 3-loop for plugin source edits.

**Pattern skills** (flexible — adapt to context):

- `ivy-writing-guide` — Ivy 1.7 syntax.
- `ivy-error-patterns` — verifier catalog + error lookup.
- `methodology-reference` — NCT/NACT/NSCT.
- `specification-patterns` — 14-layer template.
- `apt-attack-patterns` — APT 6-stage lifecycle.
- `ivy-toolkit` — MCP tool catalog.
- `propagation-patterns` — type change impact.
- `counterexample-guide` — verification failure interpretation.
- `claim-discussion` — verification/coverage claim resolution.
- `ivy-debugging-methodology` — pre-fix research.
- `reflection-patterns` — adversarial gates G0–G5.
- `parallel-dispatch` — agent dispatch composition.

## Integration

- **Loaded by:** SessionStart hook `inject-using-plugin.sh` (every session start). User cannot dismiss; the hook is the load-bearing entry point.
- **Cross-references:** `.claude/rules/iron-laws.md` (canonical), `.claude/rules/skill-conventions.md` (plugin-local conventions), `routing-rules.json` (precision-layer matchers).
- **Terminal state:** none — this skill is reference-only, injected as additional context for every session. No phase, no dispatch, no workflow.
