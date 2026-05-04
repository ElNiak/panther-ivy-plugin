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
- `pretooluse/block-direct-ivy.py` — `Bash` — advisory hint when `ivyc`, `ivy_check`, `ivy_show`, or `ivy_to_cpp` is invoked directly (always exits 0; surfaces an MCP-tool suggestion table).
- `mcp/health.py` — `mcp__.*ivy` — circuit-breaker for the panther-ivy-plugin MCP server. After 3 consecutive failures, BLOCKS the call.
- `mcp/indexing-ready.py` — `mcp__.*ivy` — gates MCP tool calls until the LSP/MCP finished indexing. After 6 denials (~60 s) degrades to WARN.
- `workspace/scope.py` — `Write|Edit` — blocks writes outside the active workspace.
- `observability/observe.py --event PreToolUse` — `mcp__|Bash|Write|Edit|Agent` — emits a JSONL observability event.

### PostToolUse
- `render/workflow-aware-annotation.py` — `Write|Edit|Agent` — updates workflow state after edits and Agent dispatches; writes the per-session statusline overlay.
- `posttooluse/lint/ivy.py` — `Write|Edit` — runs three structural checks (`#lang` header, balanced braces, non-empty) after `.ivy` edits.
- `posttooluse/lint/python-format.py` — `Write|Edit` — auto-fix `.py` files via ruff.
- `posttooluse/gates/run-gate.py --id g2` — `Write|Edit` — dispatches the G2 modeling gate critic.
- `posttooluse/gates/run-gate.py --id g3` — `Write|Edit` — dispatches the G3 test-spec gate critic.
- `posttooluse/gates/run-gate.py --id g5` — `ivy_iut_test` — dispatches the G5 trace-analysis gate critic.
- `record/workflow-error.py` — `ivy_verify|ivy_compile|ivy_diagnostics|ivy_coverage|ivy_iut_test|ivy_quality` — records failures to the workflow journal.
- `render/tool-result.py` — same MCP-tool matcher — renders structured MCP results into prose/tables.
- `mcp/activity.py` — `mcp__plugin_panther-ivy-plugin_.*` — marks per-session activity flag for any panther-ivy MCP tool call.
- `record/skill-invocation.py` — `Skill` — surfaces a `[ivy-skill]` line, updates the statusline `active_skill` section, auto-loads each plugin skill's `references/*.md` into `additionalContext` (capped at 8000 chars), and appends `progress{kind: "skill_invoked"}` to the journal when an ops-skill fires inside an active workflow.
- `record/askuserquestion.py` — `AskUserQuestion` — records question/answer payloads to JSONL and a compact journal pointer.
- `workspace/change-notify.py` — `mcp__.*ivy_workspace` — surfaces a status-line banner when `ivy_workspace(action="set"|"clear")` fires.
- `render/project-md.py` — `mcp__.*ivy_workflow_state` — regenerates `protocol-testing/<protocol>/PROJECT.md` rolled-up view.
- `statusline/sync.py` — `mcp__.*ivy_workflow_state` — syncs workflow state into the statusline cache.
- `observability/observe.py --event PostToolUse` — `mcp__|Bash|Write|Edit|Agent` — emits a JSONL observability event.

### PostToolUseFailure
- `mcp/retry.py` — `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_(status|diagnostics|model_info|coverage)` — prompts the agent to retry once when a read-only idempotent ivy_* tool fails; appends a `progress{kind: "mcp_retry"}` journal entry.
- `observability/observe.py --event PostToolUseFailure` — `*` — records tool-call failures.

### SessionStart (runs in array order)
1. `journaling/contract-check.py` — verifies the journaling contract is present and emits `[ivy-contract]` on success or blocks the session on absence.
2. `session/start/check-hook-paths.py` — self-test that every `${CLAUDE_PLUGIN_ROOT}/hooks/scripts/...` path in `hooks.json` resolves on disk.
3. `workspace/detect.py` — auto-detects the Ivy workspace root and exports env vars to `CLAUDE_ENV_FILE` for downstream hooks.
4. `cleanup/stale-pids.py` — removes stale MCP/LSP PID files from prior sessions and reaps orphaned `ivy_lsp` processes.
5. `cleanup/stale-workflow.py` — clears orphaned active-workflow flags from interrupted sessions.
6. `statusline/sync.py` — syncs workspace + workflow state into the statusline cache.
7. `prompt/using-plugin.py` — injects the panther-ivy-plugin overview into the session system prompt.
8. `mcp/indexing-wait.py` — waits up to 30 s for the MCP server's `[MCP-READY]` sentinel.
9. `observability/observe.py --event SessionStart` — emits the session-start JSONL event.

### SessionEnd (runs in array order)
1. `cleanup/ivy-lsp.py` — terminates the LSP and MCP server processes and removes sidecar port files.
2. `observability/observe.py --event SessionEnd` — emits the session-end JSONL event.

### Stop (runs in array order)
1. `record/session-end.py` — records end-of-turn state to the workflow journal.
2. `render/summary/main.py` — renders the end-of-session summary.
3. `observability/observe.py --event Stop` — emits a JSONL observability event.

### SubagentStart
1. `journaling/contract-inject.py` — emits a directive pointing dispatched plugin specialists at `.claude/rules/journaling-contract.md`; falls back to a 5-line read-only stub for critic agents.
2. `observability/observe.py --event SubagentStart` — emits a JSONL observability event.

### SubagentStop / PreCompact / PermissionRequest
- `observability/observe.py --event <Name>` — emits a JSONL observability event (one per hook).

### UserPromptSubmit
- `prompt/style.py` — compose / apply the active output style on every user turn.
- `observability/observe.py --event UserPromptSubmit` — emits a JSONL observability event.

### Notification (runs in array order)
1. `mcp/disconnect-notify.py` — surfaces MCP-disconnect notifications and updates the statusline `mcp` section.
2. `observability/observe.py --event Notification` — emits a JSONL observability event.

## Shared Utilities (not directly invoked by hooks)

- `lib/hook_utils/` — session-id resolution, workspace detection, MCP health
  state, and `emit_hook_output` / `emit_noop` envelope helpers.
- `lib/style_utils.py` — style-composition helpers for `render/tool-result.py`
  and `render/summary/`.
- `lib/workflow_state/` — read/write wrappers around
  `.panther-ivy/active-workflow` and `scaffold-state.yaml`.
- `lib/statusline_cache/` — populates
  `~/.claude/panther-ivy-plugin/cache/<hash>/statusline.json` consumed by
  `scripts/statusline/main.sh`.
- `lib/log_event.py` — low-level JSONL event writer shared by `observability/observe.py`
  and other observability consumers.
- `observability/` — the JSONL observability subsystem (`observe.py`).

## See also

- `.claude/rules/journaling-contract.md` — journal event schemas and the session-activity flag.
- `.claude/rules/postuse-hook-ordering.md` — why PostToolUse hooks run in their current order.
- `.claude/rules/output-style.md` — `systemMessage` prefix table and T1/T2/T3 discipline.
