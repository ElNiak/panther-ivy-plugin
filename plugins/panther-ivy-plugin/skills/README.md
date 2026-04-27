# Skills

## Overview

Skills provide reference material and domain knowledge for Ivy protocol testing within the PANTHER framework. The 18 skills use the **flat-with-prefix layout** — each skill lives at `skills/<category>-<name>/SKILL.md` with `name: <category>-<leaf>` matching the leaf directory. Categories are encoded as the prefix:

- **workflow-*** (5) — User-facing entry points; activated by routing or explicit invocation.
- **knowledge-*** (7) — Reference material loaded by workflows and agents on demand.
- **cross-cutting-*** (4) — Patterns and gates invoked by multiple workflows.
- **meta-*** (2) — Plugin-internal; not user-invocable directly.

## Workflow Skills (5)

| Skill | Purpose |
|-------|---------|
| [workflow-navigate](workflow-navigate/) | Session entry point — detect intent, resume context, route to the right workflow |
| [workflow-verify](workflow-verify/) | Verify, compile, diagnose failures in Ivy specifications |
| [workflow-build](workflow-build/) | Create models, add layers, propagate type changes |
| [workflow-review](workflow-review/) | Audit quality, check RFC coverage, run multi-agent review |
| [workflow-triage](workflow-triage/) | Diagnose toolchain issues, health check LSP + MCP stack |

## Knowledge Skills (7)

| Skill | Purpose |
|-------|---------|
| [knowledge-apt-attack-patterns](knowledge-apt-attack-patterns/) | APT-layer pattern library for NACT |
| [knowledge-ivy-toolkit](knowledge-ivy-toolkit/) | MCP tool documentation and tool selection guidance |
| [knowledge-ivy-writing-guide](knowledge-ivy-writing-guide/) | Ivy 1.7 syntax reference and RFC annotation conventions |
| [knowledge-methodology-reference](knowledge-methodology-reference/) | NCT, NACT, NSCT methodology reference + 14-layer template |
| [knowledge-propagation-patterns](knowledge-propagation-patterns/) | Patterns for propagating type changes across spec layers |
| [knowledge-specification-patterns](knowledge-specification-patterns/) | 14-layer structural template and formal model patterns |
| [knowledge-verification-failures](knowledge-verification-failures/) | Error-pattern catalog, debugging methodology, counterexample interpretation, and claim-discussion gate (consolidates the four prior `claim-discussion`, `counterexample-guide`, `ivy-debugging-methodology`, `ivy-error-patterns` skills) |

## Cross-cutting Skills (4)

| Skill | Purpose |
|-------|---------|
| [cross-cutting-completion-gate](cross-cutting-completion-gate/) | 5-step IDENTIFY → RUN → READ → VERIFY → THEN-claim gate |
| [cross-cutting-reflection-patterns](cross-cutting-reflection-patterns/) | Reflection Gate, MPE, Situation Briefing, G0–G6 patterns |
| [cross-cutting-parallel-dispatch](cross-cutting-parallel-dispatch/) | Multi-Agent dispatch composition pattern |
| [cross-cutting-knowledge-capture](cross-cutting-knowledge-capture/) | Session learnings extraction at workflow phase boundaries |

## Meta Skills (2)

Plugin-internal: not user-invocable.

| Skill | Purpose |
|-------|---------|
| [meta-plugin-self-mod](meta-plugin-self-mod/) | 3-agent loop for plugin source modifications |

Plus 1 SessionStart-injected meta-skill: see [meta-using-panther-ivy-plugin/SKILL.md](meta-using-panther-ivy-plugin/SKILL.md). Not indexed as a peer because it is auto-injected at SessionStart by `hooks/scripts/inject-using-plugin.sh`, not user-invocable.

## Naming convention

The flat-with-prefix layout (`skills/<category>-<name>/`) was chosen after the 2026-04-27 migration confirmed empirically that nested layouts with slash-named skills (`skills/<category>/<name>/` with `name: <category>/<name>`) are not registered by the Claude Code harness. See `.claude/rules/skill-conventions.md` for the canonical rule and `docs/skill-audit-2026-04-27.md` for the original audit findings.
