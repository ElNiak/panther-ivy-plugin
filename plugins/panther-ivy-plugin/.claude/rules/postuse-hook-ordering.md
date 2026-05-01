---
paths:
  - "hooks/hooks.json"
  - "hooks/scripts/post-*.py"
  - "hooks/scripts/assess-*.py"
  - "hooks/scripts/record-*.py"
  - "hooks/scripts/track-*.py"
---

# PostToolUse Hook Ordering

When editing PostToolUse hook configuration or scripts, preserve this ordering contract.

Claude Code fires PostToolUse hooks in the order they appear in `hooks.json`. The current order is:

1. `post-write-workflow-aware.py` (matcher: `Write|Edit|Agent`) — runs first. For `Agent` dispatches it records the active specialist agent in the statusline cache and emits an `[ivy-state]` hint. For `.ivy` writes outside an active workflow it surfaces an orientation hint suggesting `review` or `ivy_diagnostics(mode="structural")`. Inside an active workflow it emits an `[ivy-noop]` line.
2. `post-write-ivy-lint.py` (matcher: `Write|Edit`) — runs three structural checks (`#lang` header, balanced braces, non-empty) on the edited `.ivy` file and emits a short pass/fail summary. Fast (~100 ms), stateless.
3. `assess-modeling.py` and `assess-testspec.py` (matcher: `Write|Edit`) — adversarial G2 / G3 critics. They read `WorkflowContext.current()` and `scaffold-state.yaml`, append a `gate_dispatched` journal event, and emit a verbatim dispatch directive instructing the orchestrator to spawn critic swarms.
4. `assess-trace.py` (matcher: `ivy_iut_test`) — fires only after IUT runs. Emits the G5 trace-analysis dispatch directive and appends a `gate_dispatched` journal event.
5. `record-workflow-error.py` and `render-tool-result.py` (matcher: `ivy_verify|ivy_compile|ivy_diagnostics|ivy_coverage|ivy_iut_test|ivy_quality`) — record-workflow-error appends `error` journal events on failure patterns and, after `ivy_verify`, emits the G4 verification-gate dispatch directive. render-tool-result is pure formatting — it reformats MCP tool output for the active workflow style.
6. `track-skill-invocation.py` (matcher: `Skill`) — for plugin skills (`panther-ivy-plugin:*`), updates the statusline `active_skill` section, auto-loads `references/*.md` into `additionalContext` (capped at 8000 chars), and appends `progress{kind: "skill_invoked"}` to the journal when an ops-skill fires inside an active workflow. For non-plugin skills emits the `[ivy-skill]` status line only.
7. `observability/observe.py --event PostToolUse` (matcher: `mcp__|Bash|Write|Edit|Agent`) — runs last. Captures the structured event into the JSONL observability log.

**Why this order matters.** Ordering here is about output layering, not workflow-state visibility — every hook in this cluster reads the same `WorkflowContext` snapshot (skill-invocation hooks, not PostToolUse hooks, advance workflow phase). Specifically: `post-write-workflow-aware.py` runs first because it has the broadest matcher (it is the only hook that handles `Agent` dispatches) and updates the statusline before any heavier output fires. The lint hook runs second because it is fast and stateless — structural feedback lands before adversarial dispatch. Adversarial assessors run before the skill-tracking hook because their output is the most expensive (G2 / G3 / G4 / G5 directives instruct Claude to spawn calibrated critic swarms); the skill-tracking hook runs after them so its references-load doesn't push gate directives further back in the model's context. Observability runs last so it captures the final tool-event shape.

**State read by each script:**

| Script | Reads | Writes |
|---|---|---|
| `post-write-workflow-aware.py` | `WorkflowContext.current()`, `tool_input.file_path` or `subagent_type`/`prompt` | statusline cache via `statusline_cache.update_from_hook`; orientation hint via `additional_context` |
| `post-write-ivy-lint.py` | edited file | `additional_context` with finding bullets; `[ivy-lint]` summary in `system_message` |
| `assess-modeling.py` | edited file path, `WorkflowContext.current()`, `scaffold-state.yaml` | `gate_dispatched` journal event; G2 dispatch directive via `additional_context` |
| `assess-testspec.py` | edited test-spec path, `WorkflowContext.current()`, `scaffold-state.yaml` | `gate_dispatched` journal event; G3 dispatch directive via `additional_context` |
| `assess-trace.py` | `tool_result` artifacts, active-workflow state, `scaffold-state.yaml` | `gate_dispatched` journal event; G5 dispatch directive via `additional_context` |
| `record-workflow-error.py` | `tool_result`, `WorkflowContext.current()`, `scaffold-state.yaml` | `error` journal entry on pattern match; `gate_dispatched` journal entry after `ivy_verify`; G4 dispatch directive via `additional_context` |
| `track-skill-invocation.py` | `tool_input.skill`, `WorkflowContext.current()`, `${CLAUDE_PLUGIN_ROOT}/skills/<name>/references/*.md` | statusline `active_skill` section; `progress{kind: "skill_invoked"}` journal entry for ops-skill invocations inside an active workflow; references payload via `additional_context` |

**Adding new hooks.** Hooks that produce surface-context output (statusline updates, orientation hints) register at position 1 alongside `post-write-workflow-aware.py`. Stateless structural checks register at position 2. Adversarial gate dispatchers register at position 3 or 4 depending on matcher. Skill-tracking and similar reference loaders register at position 6 (after gates so they do not push critical directives back in context). Observability sinks always register last so they capture the final tool-event shape.

When debugging hook execution order, query the JSONL observability log via `ivy_observability(action="get_journal")` or inspect raw events under `.panther-ivy/observability/` for the PostToolUse stream.
