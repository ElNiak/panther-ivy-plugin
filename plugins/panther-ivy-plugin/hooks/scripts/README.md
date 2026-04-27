# Hook Scripts

## Naming Convention

- **Hook entry points** (called by `hooks.json`): kebab-case (e.g., `check-mcp-health.py`)
- **Importable Python libraries** (shared utilities): snake_case per PEP 8 (e.g., `hook_utils.py`)
- **Observability subsystem** (`observability/`): snake_case for all files

This matches the Claude Code plugin convention (kebab-case for user-facing components) while following Python packaging norms for importable modules.

## File Mode Convention

- **Python scripts**: kept non-executable (`chmod 644`). `hooks.json` invokes them as `python3 ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/<name>.py`. Any shebang line at the top of a Python script is documentary only.
- **Shell scripts**: executable (`chmod 755`) with `#!/usr/bin/env bash` shebangs. `hooks.json` invokes them directly.

The Python-non-executable convention is intentional: it keeps `hooks.json` as the single source of truth for invocation (one `python3` interpreter is used everywhere), and avoids stale `+x` bits on files that get edited but no longer run as scripts.

## Purpose Index

One line per script and the event that triggers it. Multi-handler events run in `hooks.json` array order; see `hooks.json` for the canonical ordering comments.

### PreToolUse
- `check-workspace-scope.py` — `Write|Edit` — blocks writes outside the active workspace
- `block-direct-ivy.sh` — `Bash` — warns when `ivyc`, `ivy_check`, `ivy_show`, `ivy_to_cpp` are invoked directly instead of via MCP
- `tip-shown.py` — `ivy_verify`, `ivy_coverage` — shows a one-time tip on first use
- `check-mcp-health.py` — `mcp__.*ivy` — *Is the MCP server process alive?* Two-tier check (PID file then TCP sidecar fallback). After 3 consecutive failures, BLOCKS the call.
- `observability/check_lsp_log.py` — `mcp__.*ivy` — tails the LSP log for diagnostic context (does not block).
- `check-indexing-ready.sh` — `mcp__.*ivy` — *Has the LSP/MCP finished indexing the workspace?* 4 readiness signals; after 6 denials (~60 s) degrades to WARN. Orthogonal to `check-mcp-health.py`: a server can be alive but mid-indexing, or finished indexing then crash. Both checks are needed.
- `observability/observe.py --event PreToolUse` — `mcp__|Bash|Write|Edit|Agent` — emits a JSONL observability event

### PostToolUse
- `track-workflow-skill.py` — `Skill` — records which workflow skill is active
- `auto-load-skill-references.py` — `Skill` — injects each invoked skill's `references/` files
- `post-write-ivy-lint.sh` — `Write|Edit` — runs `ivy_diagnostics(mode="structural")` after `.ivy` edits
- `post-write-workflow-aware.py` — `Write|Edit` — updates workflow state after edits
- `assess-modeling.py` — `Write|Edit` — dispatches the G2 modeling gate critic
- `assess-testspec.py` — `Write|Edit` — dispatches the G3 test-spec gate critic
- `assess-trace.py` — `ivy_iut_test` — dispatches the G5 trace-analysis gate critic
- `interaction-checkpoint.py` — `ivy_verify|ivy_coverage|ivy_extract_requirements|ivy_quality` — fires interactive checkpoints
- `render-tool-result.py` — `ivy_verify|ivy_coverage|ivy_diagnostics|ivy_compile|ivy_quality` — renders structured MCP results into prose/tables
- `record-workflow-error.py` — `ivy_verify|ivy_compile|ivy_diagnostics|ivy_coverage|ivy_iut_test|ivy_quality` — records failures to the workflow journal
- `observability/observe.py --event PostToolUse` — `mcp__|Bash|Write|Edit|Agent` — emits a JSONL observability event

### PostToolUseFailure
- `retry-ivy-mcp.py` — `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_(status|diagnostics|model_info|coverage)` — prompts the agent to retry once when a read-only idempotent ivy_* tool fails; appends a `progress{kind: "mcp_retry"}` journal entry.
- `observability/observe.py --event PostToolUseFailure` — `*` — records tool-call failures

### SessionStart (runs in array order)
1. `cleanup-stale-pids.sh` — removes stale MCP/LSP PID files from prior sessions
2. `cleanup-stale-workflow.py` — clears orphaned active-workflow flags
3. `detect-ivy-workspace.sh` — auto-detects the Ivy workspace root and exports env vars
4. `observability/observe.py --event SessionStart` — emits the session-start JSONL event
5. `wait-for-indexing.sh` — waits up to 30 s for indexing to complete

### SessionEnd (runs in array order)
1. `cleanup-ivy-lsp.sh` — terminates the LSP and MCP server processes
2. `observability/observe.py --event SessionEnd` — emits the session-end JSONL event

### Stop (runs in array order)
1. `record-session-end.py` — records end-of-turn state to the workflow journal
2. `render-summary.py` — renders the end-of-session summary from `styles/summaries/`
3. `observability/observe.py --event Stop` — emits a JSONL observability event

### SubagentStart / SubagentStop / PreCompact / PermissionRequest
- `observability/observe.py --event <Name>` — emits a JSONL observability event (one per hook)

### UserPromptSubmit (runs in array order)
1. `compose-style.py` — injects the active output-style overlay for the current workflow/phase
2. `route-user-prompt.py` — consults `routing-rules.json` to activate the matching workflow
3. `observability/observe.py --event UserPromptSubmit` — emits a JSONL observability event

### Notification (runs in array order)
1. `notify-mcp-disconnect.py` — handles MCP-disconnect notifications
2. `observability/observe.py --event Notification` — emits a JSONL observability event

## Shared Utilities (not directly invoked by hooks)

- `hook_utils.py` — session-id resolution, workspace detection, journal helpers
- `style_utils.py` — style-composition helpers for `compose-style.py` / `render-tool-result.py` / `render-summary.py`
- `workflow_state.py` — read/write wrappers around `.panther-ivy/active-workflow` and `build-state.yaml`
- `statusline_cache.py`, `statusline_update_helper.sh` — populate `~/.claude/panther-ivy-plugin/cache/<hash>/statusline.json` consumed by `scripts/statusline/main.sh`
- `observability/` — the JSONL observability subsystem (`observe.py`, `check_lsp_log.py`, …)
