---
description: "Failure-recovery contract for specialist agent dispatch (timeout, context exhaustion, partial output, malformed output, tool-not-found, explicit error). Also publishes the canonical <dispatch-context> schema that all specialist agents must implement."
# Loaded on demand by name from workflow skills; not auto-injected on file edits.
---

# Agent Dispatch — Failure Recovery

## Canonical `<dispatch-context>` schema

Every specialist agent (`ivy-verifier-agent`, `ivy-builder-agent`, `ivy-reviewer-agent`, `ivy-triage-agent`, `ivy-meta-agent`) must include a `<dispatch-context>` block in its body. The block is an agent capability contract: callers populate it when dispatching; the runtime uses it to verify correct dispatch. The schema specification lives here (meta-content, not duplication); the per-agent instances with specific values live in the agent files.

```xml
<!-- Canonical <dispatch-context> schema. Every specialist agent must include this block. -->
<dispatch-context>
  <!-- REQUIRED by all specialists -->
  <field name="target_files" required="true"
         example="Focus on bgp_connection.ivy and bgp_frame.ivy"/>
  <field name="workspace" required="true"
         example="Workspace: bgp  (from ivy_workspace(action=&quot;get&quot;))"/>
  <field name="phase_context" required="true"
         example="Dispatched from verify Phase 4 — diagnosis"/>

  <!-- OPTIONAL: shared across specialists, populate when known -->
  <field name="prior_findings" required="false"
         example="G2 flagged missing invariant on quic_frame.ivy:78"/>

  <!-- OPTIONAL: ivy-verifier-agent only — required when dispatched for verification -->
  <field name="verification_target" required="false"
         example="Verify protocol-testing/bgp/bgp_stack/bgp_connection.ivy"/>
  <field name="failure_context" required="false"
         example="ivy_verify returned: invariant conn_established failed at line 45"/>

  <!-- OPTIONAL: ivy-builder-agent only — required when scaffolding a new layer -->
  <field name="layer_target" required="false"
         example="Scaffold layer 8 (connection) on top of bgp_7_session.ivy"/>

  <!-- OPTIONAL: ivy-reviewer-agent only — coverage / quality / traceability paths -->
  <field name="review_scope" required="false"
         example="Coverage audit for RFC 4271 §6 (UPDATE message validation)"/>
  <field name="rfc_source" required="false"
         example="[rfc4271:6]"/>
  <field name="existing_manifest" required="false"
         example="protocol-testing/bgp/rfc4271_requirements.yaml"/>

  <!-- OPTIONAL: ivy-meta-agent only — plugin-source modification context -->
  <field name="plugin_paths" required="false"
         example="Edit skills/build-ops/SKILL.md to add a HARD-GATE in Phase 3"/>
</dispatch-context>
```

Field semantics:

| Field | Required by | Notes |
|-------|-------------|-------|
| `target_files` | all specialists | Files or directories the agent should focus on |
| `workspace` | all specialists | Active Ivy workspace name, obtained via `ivy_workspace(action="get")` |
| `phase_context` | all specialists | Dispatching workflow and phase (e.g., "verify Phase 4 — diagnosis") |
| `prior_findings` | all specialists (optional) | Findings from a preceding gate or phase that the agent should prioritize |
| `verification_target` | `ivy-verifier-agent` (conditionally required) | Ivy file path passed to `ivy_verify`; populate when dispatched for verification |
| `failure_context` | `ivy-verifier-agent` (optional) | `ivy_verify` / `ivy_compile` error output when dispatched for diagnosis |
| `layer_target` | `ivy-builder-agent` (conditionally required) | Layer to scaffold or extend; cite the predecessor layer for `NO_LAYER_WITHOUT_SCAFFOLD` |
| `review_scope` | `ivy-reviewer-agent` (conditionally required) | Scoping for coverage / quality / traceability path |
| `rfc_source` | `ivy-reviewer-agent` (conditionally required) | RFC citation in `[rfcNNNN:X]` form; required for extraction mode |
| `existing_manifest` | `ivy-reviewer-agent` (optional) | Path to existing YAML requirements manifest; required for audit mode |
| `plugin_paths` | `ivy-meta-agent` (conditionally required) | Plugin-source paths the meta agent will modify (skills/, agents/, hooks/, .claude/rules/, commands/, output-styles/, plugin.json) |

The `required` attribute in each `<field>` element reflects the global default (false = optional for any caller). For conditionally-required fields, the agent's body documents when the caller must populate them.

`ivy-triage-agent` does not extend the schema beyond the universal fields — its dispatch context is the universal triple plus optional `prior_findings` from the failing tool. Its repair work is driven by the journal and the runbook in `triage-ops`, not by extra dispatch fields.

This schema enforces the rule from `feedback_agent_orchestrator_three_layer_split`: agent files own the per-agent `<dispatch-context>` instances (capability contracts); this rule owns the schema specification (fault-handling contract meta-content).

## Failure recovery

The orchestrator (`skills/ivy/SKILL.md`) and the five ops-skills (build, verify, review, triage, meta-self-mod) dispatch specialist agents (`ivy-verifier-agent`, `ivy-builder-agent`, `ivy-reviewer-agent`, `ivy-triage-agent`, `ivy-meta-agent`) and generic `Explore` agents for Multi-Perspective Exploration (MPE). The orchestrator additionally fans out the three gate critics (`g-plan-critic`, `g-fidelity-critic`, `g-knowledge-critic`) at G0 / G0b / G6. This rule codifies the failure-recovery contract so callers do not have to guess what to do on timeout, context exhaustion, malformed output, or tool-not-found.

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

4. **Auto-retry once** if the failure is transient (`timeout`, `context_exhaustion`, `partial`, `malformed`). Append `progress{kind: "agent_dispatch_retry", agent: "<name>"}` before the retry. Do NOT auto-retry for `tool_not_found` or `explicit_error` — those need user input. Per-agent Failure Modes sections may narrow the transient set (e.g., `ivy-reviewer-agent` disables auto-retry on `context_exhaustion` — prefer partial output rather than re-dispatch given the Opus-tier budget).

5. **If retry also fails** (or was skipped), present `AskUserQuestion` with three options:
   - **Retry manually** — user re-dispatches after intervention (e.g., trimming scope, fixing the prompt, restarting tools).
   - **Skip this agent** — proceed with sibling-agent output if any. Append `decision{summary: "Skip agent <name> after dispatch failure", context: "<why>"}`.
   - **Abandon workflow phase** — clear the active-workflow flag (no `pending_dispatch`; the orchestrator's next-turn cold-start branch re-classifies user intent). Append `decision{summary: "Abandon <workflow> phase after agent dispatch failure", context: "<why>"}` so the journal preserves the causal chain.

### Per-tier timeout defaults

| Tier | Default timeout | Agents at this tier |
|------|-----------------|---------------------|
| Sonnet | 90 s | `g-fidelity-critic`, `g-knowledge-critic`, generic `Explore` for MPE |
| Opus | 180 s | `ivy-verifier-agent`, `ivy-builder-agent`, `ivy-reviewer-agent`, `ivy-triage-agent`, `ivy-meta-agent`, `g-plan-critic` |

Per-agent Failure Modes sections may override these defaults.

### Wall-clock vs. turn-count

Claude Code's `Agent` tool does not expose a hard wall-clock timeout. The "timeout" above is a caller patience threshold: use the Background Verification pattern (already documented in `verify/SKILL.md`) to run long dispatches in a background agent with completion notification, or monitor your own wait time before falling through to step 5.

### Worked recovery — ivy-verifier-agent timeout at verify Phase 6

A concrete sequence of journal events showing the recovery pattern in flight, so the abstract steps above have a recognisable shape.

```text
ivy_workflow_state(append_journal, progress,
  '{"kind":"agent_dispatch_start","agent":"ivy-verifier-agent",
    "workflow":"verify","phase":"diagnose"}')

Agent.ivy-verifier-agent(<dispatch-context>…</dispatch-context>)   # 180 s budget (Opus)
[no return at 185 s — caller patience exceeded]

ivy_workflow_state(append_journal, progress,
  '{"kind":"agent_dispatch_failure","agent":"ivy-verifier-agent",
    "reason":"timeout"}')
ivy_workflow_state(append_journal, progress,
  '{"kind":"agent_dispatch_retry","agent":"ivy-verifier-agent"}')

Agent.ivy-verifier-agent(...)   # retry; returns at 124 s with diagnosis.

→ continue verify Phase 6 with the diagnosis.
```

If the retry also fails, the workflow falls through to `AskUserQuestion(retry-manually | skip | abandon)`. The "abandon" branch clears the active-workflow flag without emitting a `pending_dispatch` and appends a `decision{summary: "Abandon verify diagnose after agent dispatch failure"}`; the orchestrator's next-turn cold-start branch re-classifies user intent.

### Relationship to other rules

- **Cluster 1** (`pending_dispatch` journal event): the abandonment path no longer emits `pending_dispatch` (the orchestrator absorbed the navigate role); instead it appends a `decision` entry naming the abandoned phase, so the causal chain stays visible in the journal.
- **Cluster 7** (structured `progress` events): `agent_dispatch_start` / `agent_dispatch_failure` / `agent_dispatch_retry` reuse the cluster-7 `progress` payload schema (`{kind, ...}`), so `/nct-observability` surfaces them natively alongside `fix_attempt` and `compile_attempt` counters.
- **Cluster 12** (`mcp-tool-reliability.md`): an analogous pattern covers MCP tool call failures. The two rules overlap at the `tool_not_found` failure mode — if an agent's failure is traceable to its MCP tool, the MCP-tool-reliability retry-via-ToolSearch step may precede the agent-dispatch retry.
