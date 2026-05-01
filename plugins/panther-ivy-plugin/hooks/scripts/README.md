# Hook Scripts

## Language Convention

Every hook is Python 3. `hooks.json` invokes each script as
`python3 ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/<name>.py`, so the scripts are
kept non-executable (`chmod 644`); any shebang line is documentary only.
This makes `hooks.json` the single source of truth for invocation — one
interpreter, one entry-point convention, no stale `+x` bits on edited
files.

The previous Bash hooks have been rewritten in Python and moved to
`.backup/hooks-shell-rewrite-2026-05-01/scripts/` for reference until the
next graduation sweep.

## Naming Convention

- **Hook entry points** (called by `hooks.json`): kebab-case
  (e.g., `check-mcp-health.py`).
- **Importable Python libraries** (shared utilities): snake_case per
  PEP 8 (e.g., `hook_utils.py`).
- **Observability subsystem** (`observability/`): snake_case for all
  files.

## Hook output discipline

Every hook emits its envelope through
`hook_utils.emit_hook_output(event_name, system_message=..., …)`. The
helper raises `TypeError` if `system_message` is omitted; pass an empty
string to suppress the UI line. The `emit_noop(event_name, reason)`
helper is the canonical way to surface "this hook ran but took no
action" — the resulting `[ivy-noop] <reason>` system message lets the
user filter no-op lines from action-bearing ones.

```python
from hook_utils import emit_hook_output, emit_noop

def main():
    if not _condition():
        emit_noop("PostToolUse", "non-.ivy file")
        return

    emit_hook_output(
        "PostToolUse",
        system_message="[ivy-foo] action taken",
        additional_context="Detail surfaced to the model.",
    )
```

A pytest at `tests/test_hook_output_discipline.py` AST-scans every script
and fails if any `emit_hook_output` call site omits `system_message`, or
if any script constructs a `hookSpecificOutput` envelope by hand instead
of going through the helper.

## Purpose Index

One line per script and the event that triggers it. Multi-handler events run in `hooks.json` array order; see `hooks.json` for the canonical ordering comments.

### PreToolUse
- `block-direct-ivy.py` — `Bash` — advisory hint when `ivyc`, `ivy_check`, `ivy_show`, or `ivy_to_cpp` is invoked directly (always exits 0; surfaces an MCP-tool suggestion table).
- `check-mcp-health.py` — `mcp__.*ivy` — *Is the MCP server process alive?* Two-tier check (PID file then TCP sidecar fallback). After 3 consecutive failures, BLOCKS the call.
- `check-indexing-ready.py` — `mcp__.*ivy` — *Has the LSP/MCP finished indexing the workspace?* 4 readiness signals; after 6 denials (~60 s) degrades to WARN. Orthogonal to `check-mcp-health.py`: a server can be alive but mid-indexing, or finished indexing then crash. Both checks are needed.
- `check-workspace-scope.py` — `Write|Edit` — blocks writes outside the active workspace.
- `observability/observe.py --event PreToolUse` — `mcp__|Bash|Write|Edit|Agent` — emits a JSONL observability event.

### PostToolUse
- `post-write-workflow-aware.py` — `Write|Edit|Agent` — updates workflow state after edits and Agent dispatches.
- `post-write-ivy-lint.py` — `Write|Edit` — runs three structural checks (`#lang` header, balanced braces, non-empty) after `.ivy` edits.
- `assess-modeling.py` — `Write|Edit` — dispatches the G2 modeling gate critic.
- `assess-testspec.py` — `Write|Edit` — dispatches the G3 test-spec gate critic.
- `assess-trace.py` — `ivy_iut_test` — dispatches the G5 trace-analysis gate critic.
- `record-workflow-error.py` — `ivy_verify|ivy_compile|ivy_diagnostics|ivy_coverage|ivy_iut_test|ivy_quality` — records failures to the workflow journal.
- `render-tool-result.py` — same MCP-tool matcher — renders structured MCP results into prose/tables.
- `track-skill-invocation.py` — `Skill` — surfaces a `[ivy-skill]` line, updates the statusline `active_skill` section, auto-loads each plugin skill's `references/*.md` into `additionalContext` (capped at 8000 chars), and appends `progress{kind: "skill_invoked"}` to the journal when an ops-skill fires inside an active workflow.
- `observability/observe.py --event PostToolUse` — `mcp__|Bash|Write|Edit|Agent` — emits a JSONL observability event.

### PostToolUseFailure
- `retry-ivy-mcp.py` — `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_(status|diagnostics|model_info|coverage)` — prompts the agent to retry once when a read-only idempotent ivy_* tool fails; appends a `progress{kind: "mcp_retry"}` journal entry.
- `observability/observe.py --event PostToolUseFailure` — `*` — records tool-call failures

### SessionStart (runs in array order)
1. `check-journaling-contract.py` — verifies the journaling contract is present and emits `[ivy-contract]` on success or fails the load on absence.
2. `detect-ivy-workspace.py` — auto-detects the Ivy workspace root via in-process `ivy_lsp.core.workspace.context.WorkspaceContext.detect` (with pure-Python fallback) and exports env vars to `CLAUDE_ENV_FILE` for downstream hooks.
3. `cleanup-stale-pids.py` — removes stale MCP/LSP PID files from prior sessions and reaps orphaned `ivy_lsp` processes scoped to the active workspace.
4. `cleanup-stale-workflow.py` — clears orphaned active-workflow flags from interrupted sessions.
5. `inject-using-plugin.py` — injects the orchestrator priming (1% rule, methodology routing, iron-laws summary, workspace contract).
6. `wait-for-indexing.py` — waits up to 30 s for the MCP server's `[MCP-READY]` sentinel; SIGTERM-handled with a one-shot envelope guarantee.
7. `observability/observe.py --event SessionStart` — emits the session-start JSONL event.

### SessionEnd (runs in array order)
1. `cleanup-ivy-lsp.py` — terminates the LSP and MCP server processes and removes sidecar port files.
2. `observability/observe.py --event SessionEnd` — emits the session-end JSONL event.

### Stop (runs in array order)
1. `record-session-end.py` — records end-of-turn state to the workflow journal.
2. `render-summary.py` — renders the end-of-session summary from `styles/summaries/`.
3. `observability/observe.py --event Stop` — emits a JSONL observability event.

### SubagentStart
1. `inject-journaling-contract.py` — emits a directive pointing dispatched plugin specialists at `.claude/rules/journaling-contract.md`; falls back to a 5-line read-only stub for critic agents.
2. `observability/observe.py --event SubagentStart` — emits a JSONL observability event.

### SubagentStop / PreCompact / PermissionRequest
- `observability/observe.py --event <Name>` — emits a JSONL observability event (one per hook).

### UserPromptSubmit
- `observability/observe.py --event UserPromptSubmit` — emits a JSONL observability event.

### Notification (runs in array order)
1. `notify-mcp-disconnect.py` — surfaces MCP-disconnect notifications and updates the statusline `mcp` section.
2. `observability/observe.py --event Notification` — emits a JSONL observability event.

## Shared Utilities (not directly invoked by hooks)

- `hook_utils.py` — session-id resolution, workspace detection, MCP health
  state, and `emit_hook_output` / `emit_noop` envelope helpers.
- `style_utils.py` — style-composition helpers for `render-tool-result.py`
  and `render-summary.py`.
- `workflow_state.py` — read/write wrappers around
  `.panther-ivy/active-workflow` and `build-state.yaml`.
- `statusline_cache.py` — populates
  `~/.claude/panther-ivy-plugin/cache/<hash>/statusline.json` consumed by
  `scripts/statusline/main.sh`.
- `observability/` — the JSONL observability subsystem (`observe.py`,
  `log_event.py`).
