---
name: cross-cutting-parallel-dispatch
description: "Use when facing 2+ independent agent dispatches with no shared state or sequential dependencies. Provides the single-message multi-Agent-call composition pattern, MPE vs role-split heuristics, and context-isolation invariants."
user-invocable: false
---

# Parallel Dispatch

**Type:** flexible — adapt principles to context.

## When to parallel-dispatch

Two or more agent dispatches qualify if:
- Each dispatch operates on independent inputs (no shared mutable state).
- No dispatch's output is required by another dispatch's input.
- Each dispatch's output can be aggregated post-hoc (no inter-agent coordination during execution).

If a dispatch must read another's output, sequence them. If two dispatches edit the same file, sequence them. Otherwise, parallel.

## How (single-message shape)

The parallel pattern is: ONE message containing N `Agent(...)` tool calls. The harness runs them concurrently. The orchestrator collects all N outputs in the next message turn.

```
Message N:    [Agent(...) Agent(...) Agent(...)]    ← three tool calls in one message
Message N+1:  [results from all three agents arrive]
```

NOT parallel:
- Three messages each with one `Agent(...)` call (sequential).
- One `Agent(...)` call awaited before the next (sequential).
- Chained inputs (output of A → input of B).

## MPE vs role-split

Two parallel-dispatch shapes recur in this plugin:

**Multi-Perspective Exploration (MPE)** — same question, multiple agent personas.

- `build` Phase 1: Conservative Architect / Pragmatic Engineer / Adversarial Auditor — three Explore agents on the same architectural question.
- One question, three perspectives, aggregated by the orchestrator.

**Role-split** — orthogonal subtasks, same orchestrator goal.

- `review` Phase 2 Quality path: `model-reviewer` (structural) + `spec-analyst` (compilation) + `Explore` (red-team) — three roles, three subtasks, three independent outputs.
- `plugin-self-mod` Steps 2 + 3: `model-reviewer` (spec-compliance axis) + `plugin-conventions-reviewer` (conventions axis) — two roles, two axes; can be parallelized because they audit independently.

Use MPE when a single question has multiple defensible answers. Use role-split when orthogonal evidence sources are needed.

## Context-isolation invariants

Each dispatched agent gets a fresh context window. Rules:
- Never assume one agent has read another's output during its run.
- Never share state files between agents during their dispatch (the journal is the only durable shared state, and it lives in the orchestrator's read).
- Always include a `<dispatch-context>` block per `.claude/rules/agent-dispatch.md` so the agent sees only the context it needs.

## Cross-references

- `reflection-patterns` Pattern B (Multi-Perspective Exploration) — the canonical MPE shape this skill operationalizes.
- `build/SKILL.md` Phase 1 — MPE example.
- `review/SKILL.md` Phase 2 Quality path — role-split example.
- `plugin-self-mod/SKILL.md` Steps 2 + 3 — role-split example for plugin-source review.
- `.claude/rules/agent-dispatch.md` — fault-handling contract for parallel dispatch failures.
