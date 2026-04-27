---
description: "Failure-recovery contract for specialist agent dispatch (timeout, context exhaustion, partial output, malformed output, tool-not-found, explicit error)."
# Loaded on demand by name from workflow skills; not auto-injected on file edits.
---

# Agent Dispatch — Failure Recovery

All five workflows (navigate, triage, verify, build, review) dispatch specialist agents (`spec-analyst`, `model-reviewer`, `traceability-agent`) and generic `Explore` agents for Multi-Perspective Exploration (MPE). This rule codifies the failure-recovery contract so callers do not have to guess what to do on timeout, context exhaustion, malformed output, or tool-not-found.

## Canonical failure modes

1. **Timeout** — the agent did not return within the per-tier budget (see "Per-tier timeout defaults" below).
2. **Context exhaustion** — the agent hit its `maxTurns` limit without completing.
3. **Partial output** — the agent returned but the output is structurally incomplete (missing sections, truncated tables, incomplete enumerations).
4. **Malformed output** — the agent returned but the text cannot be parsed in the expected format.
5. **Tool-not-found** — one of the agent's allow-listed tools is unavailable (MCP server dead, schema not loaded, plugin infra issue).
6. **Explicit error** — the agent raised an error or emitted a failure message.

## Canonical recovery pattern

1. **Before dispatch**: append a structured `progress` journal entry:
   ```
   ivy_workflow_state(
     action="append_journal",
     protocol="<protocol>",
     event_type="progress",
     state='{"kind": "agent_dispatch_start", "agent": "<name>", "workflow": "<workflow>", "phase": "<phase>"}'
   )
   ```

2. **Dispatch** with a per-tier timeout. Sonnet agents get 90 s by default; Opus agents get 180 s. Per-agent Failure Modes sections may override.

3. **On failure**: append an `agent_dispatch_failure` progress entry with the classified reason:
   ```
   progress{kind: "agent_dispatch_failure", agent: "<name>", reason: "timeout" | "context_exhaustion" | "partial" | "malformed" | "tool_not_found" | "explicit_error"}
   ```

4. **Auto-retry once** if the failure is transient (`timeout`, `context_exhaustion`, `partial`, `malformed`). Append `progress{kind: "agent_dispatch_retry", agent: "<name>"}` before the retry. Do NOT auto-retry for `tool_not_found` or `explicit_error` — those need user input.

5. **If retry also fails** (or was skipped), present `AskUserQuestion` with three options:
   - **Retry manually** — user re-dispatches after intervention (e.g., trimming scope, fixing the prompt, restarting tools).
   - **Skip this agent** — proceed with sibling-agent output if any. Append `decision{summary: "Skip agent <name> after dispatch failure", context: "<why>"}`.
   - **Abandon workflow phase** — emit `append_pending_dispatch(target_workflow="navigate", reason="agent dispatch failed: <agent>")` and clear the active-workflow flag. Navigate's Phase 1 Step 2c routes the user on the next turn.

## Per-tier timeout defaults

| Tier | Default timeout | Agents at this tier |
|------|-----------------|---------------------|
| Sonnet | 90 s | `spec-analyst`, `traceability-agent`, generic `Explore` for MPE |
| Opus | 180 s | `model-reviewer` |

Per-agent Failure Modes sections may override these defaults.

## Wall-clock vs. turn-count

Claude Code's `Agent` tool does not expose a hard wall-clock timeout. The "timeout" above is a caller patience threshold: use the Background Verification pattern (already documented in `verify/SKILL.md`) to run long dispatches in a background agent with completion notification, or monitor your own wait time before falling through to step 5.

## Relationship to other rules

- **Cluster 1** (`pending_dispatch` journal event): the abandonment path emits `pending_dispatch(navigate, …)` so the causal chain is visible in the journal.
- **Cluster 7** (structured `progress` events): `agent_dispatch_start` / `agent_dispatch_failure` / `agent_dispatch_retry` reuse the cluster-7 `progress` payload schema (`{kind, ...}`), so `/nct-observability` surfaces them natively alongside `fix_attempt` and `compile_attempt` counters.
- **Cluster 12** (`mcp-tool-reliability.md`): an analogous pattern covers MCP tool call failures. The two rules overlap at the `tool_not_found` failure mode — if an agent's failure is traceable to its MCP tool, the MCP-tool-reliability retry-via-ToolSearch step may precede the agent-dispatch retry.
