# Parallel dispatch — single-message multi-Agent pattern

When dispatching multiple agents that share no state and run independently (e.g., 3 gate critics for an asymmetric vote), invoke them in a SINGLE message with multiple `Agent` tool calls. The harness runs them in parallel; sequential dispatch wastes wall-clock time.

## Pattern

Use the gate's owning critic agent and dispatch it three times. Example for G0 (plan-gate); G0b uses `g-fidelity-critic`, G6 uses `g-knowledge-critic`:

```
Agent(subagent_type="panther-ivy-plugin:g-plan-critic", description="G0 critic", prompt="<verbatim critic prompt incl. dispatch-context>")
Agent(subagent_type="panther-ivy-plugin:g-plan-critic", description="G0 critic", prompt="<verbatim critic prompt incl. dispatch-context>")
Agent(subagent_type="panther-ivy-plugin:g-plan-critic", description="G0 critic", prompt="<verbatim critic prompt incl. dispatch-context>")
```

All three calls go in the same assistant turn. Each agent forks its own context with no awareness of the others. Each returns a verdict (SOUND / UNSOUND / ABSTAIN) plus a reason and citation.

## Aggregation

Read the three verdicts. The vote is asymmetric: a single UNSOUND citing concrete file:line is informative and overrides quiet majority. Apply this order:

- ≥2 UNSOUND → halt and surface to user via AskUserQuestion (retry, override with rationale, or abandon).
- ≥2 SOUND **and no UNSOUND dissent** (so all three are SOUND, or 2 SOUND + 1 ABSTAIN) → proceed.
- ≥2 ABSTAIN → ABSTAIN; gather more evidence (re-read the artefact, broaden include closure, populate `prior_findings`) and re-dispatch.
- Any other distribution (notably 2 SOUND + 1 UNSOUND, 1 SOUND + 1 UNSOUND + 1 ABSTAIN, etc.) → ABSTAIN; the dissent must be reconciled before proceeding.

## Verbatim critic prompt requirement

Each critic gets the EXACT same prompt — no per-agent adaptation. The prompt must include the populated `<dispatch-context>` block per the agent's body and `agent-dispatch.md`. Verbatim spawn prompts are the asymmetric-vote discipline: any per-agent adaptation biases the vote.

## Failure recovery

If a critic times out or returns malformed output, follow `agent-dispatch.md`: append `agent_dispatch_failure` journal entry, auto-retry once for transient failures, then `AskUserQuestion` for retry/skip/abandon if retry fails.

## When NOT to use

- Sequential dependencies (output of agent A feeds agent B): use sequential dispatch.
- Single-perspective tasks (one critic suffices): single Agent call.
- Workflow agents (specialist agents that perform work, not vote): single Agent call per dispatch.

## Per-candidate aggregation (G6 only)

`g-knowledge-critic` returns a per-candidate `KEEP / DROP / DEFER` list in addition to the per-batch `VERDICT_*`. Aggregation runs at two levels:

**Per-batch VERDICT (gate-level):** apply the asymmetric-vote rule above (≥2 SOUND / ≥2 UNSOUND / ≥2 ABSTAIN / mixed → ABSTAIN).

**Per-candidate vote (within a SOUND batch):** aggregate KEEP / DROP / DEFER across the three critics for each individual candidate:

- ≥2 KEEP → write `knowledge_captured(...)` with `confidence="high"`.
- ≥2 DROP → no journal write; candidate dropped silently.
- ≥2 DEFER → DEFER the candidate.
- 1-1-1 split (one of each) → DEFER (consistent with the asymmetric-vote convention that mixed votes resolve to ABSTAIN at gate level).

For DEFERred candidates, surface an `AskUserQuestion` in the same orchestrator turn with three options: KEEP (writes `knowledge_captured(...)` with `confidence="user-confirmed"`), DROP (no write), or SKIP (no write; candidate NOT added to the dedup set, so a future G6 invocation may re-vote on it). SKIP is the conservative default for "I'm not sure right now".
