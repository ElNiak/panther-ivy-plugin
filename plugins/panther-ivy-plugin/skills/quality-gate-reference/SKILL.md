---
name: Quality Gate Reference
description: Use when asking about "quality gates", "quality evaluation", "quality scoring",
  "self-repair loop", "quality dimensions", "agent output quality", or how the multi-gate
  quality pipeline works for evaluating Ivy specification agent outputs.
---

# Quality Gate Reference

## Overview

The panther-ivy-plugin includes a multi-gate quality evaluation pipeline that automatically evaluates all agent outputs. Write agents are evaluated for structural correctness, type safety, semantic quality, and RFC traceability. Read agents are evaluated for factual accuracy and completeness.

## Architecture

```
Agent works on task
        │
        ▼
   [Gate 1: PostToolUse]     ◄── Fast lint after .ivy writes (<1s, non-blocking)
   │
   Agent finishes → SubagentStop fires
        │
        ├─ Write agents ──► [Gate 2: Agent hook]   ◄── Deep eval (reads files, scores)
        │                    ├─ PASS → agent stops
        │                    └─ FAIL → block → agent retries once → allow
        │
        └─ Read agents ───► [Gate 3: Prompt hook]  ◄── Accuracy check (single LLM call)
                             ├─ PASS → agent stops
                             └─ FAIL → block → agent retries once → allow
```

## Quality Dimensions

### Write Agents (nct-guide, nact-guide, nsct-guide, requirement-extractor)

| Dimension | Weight | Tool Used | What It Checks |
|-----------|--------|-----------|----------------|
| Structural | 25% | `ivy_lint` | `#lang` header, balanced braces, includes, file structure |
| Type Safety | 30% | `ivy_verify` | Formal verification, invariants, type correctness |
| Semantic | 20% | `ivy_model_info` + checklist | Naming, invariant coverage, guards, initialization |
| Traceability | 25% | `ivy_traceability_matrix` | Bracket tags, RFC coverage, orphaned/untagged assertions |

### Read Agents (spec-explorer, ivy-model-reviewer, traceability-reviewer, spec-verifier)

| Dimension | Weight | What It Checks |
|-----------|--------|----------------|
| Factual Accuracy | 50% | Claims reference specific files/symbols/lines, no vague assertions |
| Completeness | 30% | All checklist items addressed, user request fully covered |
| Tool Usage | 20% | MCP tools used correctly, no direct CLI calls |

## Scoring

- Each dimension scores 0-100
- **Overall** = weighted average of applicable dimensions
- **PASS**: overall >= 70 AND no dimension at 0
- **FAIL**: triggers self-repair (1 retry), then escalation to user

## Self-Repair Loop

1. Agent finishes → SubagentStop hook fires
2. Quality gate evaluates output
3. If FAIL: returns `{"decision": "block", "reason": "..."}` preventing the agent from stopping
4. Agent receives failure reason as feedback and continues fixing
5. On next stop attempt: `stop_hook_active` is true → agent is allowed to stop
6. Unresolved issues are surfaced to the user via `additionalContext`

## Hook Types

| Gate | Hook Event | Hook Type | Timeout | Reason |
|------|------------|-----------|---------|--------|
| Gate 1 | PostToolUse (Write\|Edit) | command | 10s | Fast bash-level structural check |
| Gate 2 | SubagentStop (write agents) | agent | 60s | Needs file access (Read, Grep, Glob) |
| Gate 3 | SubagentStop (read agents) | prompt | 30s | Text evaluation only, no tool access |

## Manual Quality Check

Use the `quality-gate` agent directly for on-demand evaluation:
- "Run a quality check on my QUIC specification"
- "Evaluate the quality of protocol-testing/quic/quic_stack/"
- "Check the quality of my RFC 9000 requirements manifest"

## Related Components

- **Agent**: `quality-gate` — dedicated quality evaluation agent
- **Hook**: `post-write-ivy-lint.sh` — PostToolUse fast lint
- **Skill**: `ivy-tools-reference` — MCP tool catalog used by quality gates
- **Agent**: `ivy-model-reviewer` — complementary read-only model review
