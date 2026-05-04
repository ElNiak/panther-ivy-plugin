---
description: "Recovery pattern for ivy-tools MCP failures (schema not loaded via InputValidationError, server dead, tool-specific error). Differentiates reliability failures from verification findings; specifies the ToolSearch retry + AskUserQuestion fallback chain."
# Loaded on demand by name from workflow skills (called out as 'cluster 12' from agent-dispatch.md); not auto-injected on file edits.
---

# MCP Tool Reliability

The plugin's ivy-tools MCP server exposes ~18 tools. Schemas for deferred
tools are loaded on demand via `ToolSearch`. Tool schemas, or the MCP server
itself, may become unavailable mid-session — callers must not assume any
given tool call succeeds.

## Canonical recovery pattern

1. **On `InputValidationError` from an MCP tool call** (the typical signal
   for a deferred-tool schema that is not loaded):
   - Append a `progress` journal event recording the failure:
     ```
     ivy_workflow_state(
       action="append_journal",
       protocol="<protocol>",
       event_type="progress",
       state='{"kind": "mcp_tool_unavailable", "tool": "<tool_name>", "reason": "schema_not_loaded"}'
     )
     ```
   - Call `ToolSearch({query: "select:<tool_name>"})` to re-load the schema.
   - Retry the tool call once. On success, continue.

2. **On second failure** (retry did not recover):
   - Append a second `progress` entry:
     ```
     progress{kind: "mcp_tool_unavailable", tool: "<tool_name>", reason: "retry_failed"}
     ```
   - Present `AskUserQuestion` with three options:
     - **Retry after fixing MCP server** — dispatch
       `Agent(subagent_type="panther-ivy-plugin:ivy-triage-agent", prompt="Run the 9-step Ivy LSP + MCP health-check runbook and repair any failed steps.")`
       so the user sees the full diagnose-and-repair flow; on repair
       completion triage emits `pending_dispatch(<caller>, reason="post-triage-repair")`
       to hand control back.
     - **Skip this step** — proceed without the tool's output; record a
       `decision` journal entry:
       ```
       decision{summary: "Skip <tool_name> due to unavailability", context: <why>}
       ```
     - **Abandon phase** — emit
       `append_pending_dispatch(target_workflow="navigate", reason="MCP tool unavailable")`
       and clear the active-workflow flag. Navigate re-enters on the next
       turn and routes the user.

## Differentiating tool-call failures

Not every error from an MCP tool is a reliability failure — handle each
class differently:

- **Schema not loaded** (`InputValidationError`) — deferred-tool schema was
  not fetched. Auto-retry via `ToolSearch` usually fixes.
- **MCP server dead** — all tool calls fail consistently. Route to `triage`
  first rather than retrying individual tools.
- **Tool-specific error** (e.g., `ivy_verify` returning `status: FAIL`,
  `ivy_compile` returning a compile error with line numbers) — this is a
  verification / compilation finding, not a reliability issue. Handle per
  the owning workflow's failure-diagnosis procedure; do not apply this
  rule's recovery pattern.

## Automated retry for read-only tools

Read-only ivy_* MCP tools (`ivy_status`, `ivy_diagnostics`, `ivy_model_info`, `ivy_coverage`) trigger an automated retry once via the `mcp/retry.py` PostToolUseFailure hook. The hook emits a `progress{kind: "mcp_retry", tool: "..."}` journal entry regardless of retry outcome, so retried failures are visible in `ivy_observability(action="get_journal")`.

Write-side tools (`ivy_compile`, `ivy_verify`, `ivy_iut_test`) are NOT auto-retried (not idempotent); their failures surface immediately to the agent, which falls back to the manual retry + AskUserQuestion pattern documented above.

## Relationship to other rules

- `pending_dispatch` (cluster 1, `workflow_state.py::append_pending_dispatch`):
  the abandonment path emits a `pending_dispatch(navigate, …)` event.
- `agent-dispatch` rule (cluster 10, `.claude/rules/agent-dispatch.md`):
  analogous pattern for agent-dispatch failures; this rule covers MCP
  tool calls specifically.
- Structured `progress` payloads (cluster 7): the `progress` events written
  by this rule reuse the `{kind, ...}` payload schema that the attempt-
  counter persistence uses, so `/nct-observability` surfaces them natively.
