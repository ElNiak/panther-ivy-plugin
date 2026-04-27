---
description: "Failure-recovery contract for specialist agent dispatch (timeout, context exhaustion, partial output, malformed output, tool-not-found, explicit error). Also publishes the canonical <dispatch-context> schema that all specialist agents must implement."
# Loaded on demand by name from workflow skills; not auto-injected on file edits.
---

# Agent Dispatch — Failure Recovery

## Canonical `<dispatch-context>` schema

Every specialist agent (`spec-analyst`, `model-reviewer`, `traceability-agent`) must include a `<dispatch-context>` block in its body. The block is an agent capability contract: callers populate it when dispatching; the runtime uses it to verify correct dispatch. The schema specification lives here (meta-content, not duplication); the per-agent instances with specific values live in the agent files.

```xml
<!-- Canonical <dispatch-context> schema. Every specialist agent must include this block. -->
<dispatch-context>
  <!-- REQUIRED by all agents -->
  <field name="target_files" required="true"
         example="Focus on bgp_connection.ivy and bgp_frame.ivy"/>
  <field name="workspace" required="true"
         example="Workspace: bgp  (from ivy_workspace(action=&quot;get&quot;))"/>
  <field name="phase_context" required="true"
         example="Dispatched from verify Phase 4 — diagnosis"/>

  <!-- OPTIONAL: shared across agents, populate when known -->
  <field name="prior_findings" required="false"
         example="G2 flagged missing invariant on quic_frame.ivy:78"/>

  <!-- OPTIONAL: spec-analyst only — required when dispatched for verification -->
  <field name="verification_target" required="false"
         example="Verify protocol-testing/bgp/bgp_stack/bgp_connection.ivy"/>
  <field name="failure_context" required="false"
         example="ivy_verify returned: invariant conn_established failed at line 45"/>

  <!-- OPTIONAL: model-reviewer only — required when dispatched for review -->
  <field name="review_scope" required="false"
         example="Targeted review of layer 7 (connection)"/>

  <!-- OPTIONAL: traceability-agent only — required for extraction mode; present for audit mode -->
  <field name="rfc_source" required="false"
         example="[rfc4271:6]"/>
  <field name="existing_manifest" required="false"
         example="protocol-testing/bgp/rfc4271_requirements.yaml"/>
</dispatch-context>
```

Field semantics:

| Field | Required by | Notes |
|-------|-------------|-------|
| `target_files` | all agents | Files or directories the agent should focus on |
| `workspace` | all agents | Active Ivy workspace name, obtained via `ivy_workspace(action="get")` |
| `phase_context` | all agents | Dispatching workflow and phase (e.g., "verify Phase 4 — diagnosis") |
| `prior_findings` | all agents (optional) | Findings from a preceding gate or phase that the agent should prioritize |
| `verification_target` | spec-analyst (conditionally required) | Ivy file path passed to `ivy_verify`; populate when dispatched for verification |
| `failure_context` | spec-analyst (optional) | `ivy_verify` / `ivy_compile` error output when dispatched for diagnosis |
| `review_scope` | model-reviewer (conditionally required) | Scoping description for adversarial review; populate when dispatched for review |
| `rfc_source` | traceability-agent (conditionally required) | RFC citation in `[rfcNNNN:X]` form; required for extraction mode |
| `existing_manifest` | traceability-agent (optional) | Path to existing YAML requirements manifest; required for audit mode |

The `required` attribute in each `<field>` element reflects the global default (false = optional for any caller). For conditionally-required fields, the agent's body documents when the caller must populate them.

This schema enforces the rule from `feedback_agent_orchestrator_three_layer_split`: agent files own the per-agent `<dispatch-context>` instances (capability contracts); this rule owns the schema specification (fault-handling contract meta-content).

## Failure recovery

All five workflows (navigate, triage, verify, build, review) dispatch specialist agents (`spec-analyst`, `model-reviewer`, `traceability-agent`) and generic `Explore` agents for Multi-Perspective Exploration (MPE). This rule codifies the failure-recovery contract so callers do not have to guess what to do on timeout, context exhaustion, malformed output, or tool-not-found.

### Canonical failure modes

1. **Timeout** — the agent did not return within the per-tier budget (see "Per-tier timeout defaults" below).
2. **Context exhaustion** — the agent hit its `maxTurns` limit without completing.
3. **Partial output** — the agent returned but the output is structurally incomplete (missing sections, truncated tables, incomplete enumerations).
4. **Malformed output** — the agent returned but the text cannot be parsed in the expected format.
5. **Tool-not-found** — one of the agent's allow-listed tools is unavailable (MCP server dead, schema not loaded, plugin infra issue).
6. **Explicit error** — the agent raised an error or emitted a failure message.

### Canonical recovery pattern

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

### Per-tier timeout defaults

| Tier | Default timeout | Agents at this tier |
|------|-----------------|---------------------|
| Sonnet | 90 s | `spec-analyst`, `traceability-agent`, generic `Explore` for MPE |
| Opus | 180 s | `model-reviewer` |

Per-agent Failure Modes sections may override these defaults.

### Wall-clock vs. turn-count

Claude Code's `Agent` tool does not expose a hard wall-clock timeout. The "timeout" above is a caller patience threshold: use the Background Verification pattern (already documented in `verify/SKILL.md`) to run long dispatches in a background agent with completion notification, or monitor your own wait time before falling through to step 5.

### Relationship to other rules

- **Cluster 1** (`pending_dispatch` journal event): the abandonment path emits `pending_dispatch(navigate, …)` so the causal chain is visible in the journal.
- **Cluster 7** (structured `progress` events): `agent_dispatch_start` / `agent_dispatch_failure` / `agent_dispatch_retry` reuse the cluster-7 `progress` payload schema (`{kind, ...}`), so `/nct-observability` surfaces them natively alongside `fix_attempt` and `compile_attempt` counters.
- **Cluster 12** (`mcp-tool-reliability.md`): an analogous pattern covers MCP tool call failures. The two rules overlap at the `tool_not_found` failure mode — if an agent's failure is traceable to its MCP tool, the MCP-tool-reliability retry-via-ToolSearch step may precede the agent-dispatch retry.
