---
name: meta-using-panther-ivy-plugin
description: "Deprecated under approach E orchestrator refactor (2026-04-28). Functionality moved to skills/ivy/SKILL.md and inject-using-plugin.sh primer. Will be deleted in Phase F."
user-invocable: false
---

# Using panther-ivy-plugin

## 1% rule

If a panther-ivy-plugin skill might apply (even at 1% probability), invoke it via the `Skill` tool. When ambiguous, default to `Skill(skill="panther-ivy-plugin:workflow-navigate")`. When a skill applies, do not paraphrase from memory — bodies evolve.

User instructions override skills; iron laws (`.claude/rules/iron-laws.md`) override both.

## Methodology routing

- **NCT** (compliance testing) — `build` → `verify` → `review`.
- **NACT** (security / APT) — `build` → `verify`, with attack-pattern scope.
- **NSCT** (simulation) — `build` → emits experiment-config sidecar.

If methodology is unclear, ask the user.

## Iron laws

| Law | Workflow | Binding |
|---|---|---|
| `NO_FIX_WITHOUT_VERIFY` | verify | No claim of resolution without a fresh `ivy_verify` / `ivy_compile` tool result this turn. |
| `NO_LAYER_WITHOUT_SCAFFOLD` | build | `ivy_diagnostics(mode=structural)` SOUND on the predecessor layer before Write/Edit on layer N. |
| `NO_QUALITY_WITHOUT_COVERAGE` | review | Every quality verdict cites a fresh `ivy_coverage` / `ivy_quality` output. |
| `STALENESS_RULE` | all | Re-run if the include closure was edited since the prior tool result. |

Canonical wording: `.claude/rules/iron-laws.md`.

## Workspace

Active workspace via `ivy_workspace(action="get")`. Use `/set-workspace <protocol>` to scope edits.

For the full overview (skill catalog, integration details, deferred laws, dispatch protocols), Read `references/full-overview.md`.
