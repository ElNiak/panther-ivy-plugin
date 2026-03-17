---
name: nct-observability
description: Query and analyze Ivy observability session logs (JSONL events from hooks)
arguments:
  - name: mode
    description: "Analysis mode: summary (default), events, errors, timeline"
    required: false
---

Query and analyze the JSONL session logs written by the panther-ivy-plugin observability hooks. These logs record tool usage, verification results, and session events.

## Instructions

### Step 1: Locate the Log Directory

Search for logs in priority order:
1. `$IVY_OBSERVABILITY_DIR` environment variable
2. `$IVY_WORKSPACE_ROOT/.observability/`
3. `/tmp/ivy-observability/`

Use Bash to check each path:
```bash
echo "${IVY_OBSERVABILITY_DIR:-unset}" && ls "${IVY_OBSERVABILITY_DIR:-/nonexistent}" 2>/dev/null || \
ls "${IVY_WORKSPACE_ROOT:-.}/.observability/" 2>/dev/null || \
ls /tmp/ivy-observability/ 2>/dev/null || \
echo "No observability logs found"
```

If no logs are found, report: "No observability logs found. Hooks may not have been triggered yet in this session."

### Step 2: Read Log Files

JSONL log files are named by session (e.g., `session-<id>.jsonl`). Each line is a JSON object with at least:
- `timestamp` -- ISO 8601 timestamp
- `event_type` -- Event category (e.g., `PostToolUseSuccess`, `PostToolUseFailure`, `SessionStart`, `SessionEnd`)
- `tool_name` -- MCP tool name (for tool events)
- `duration_ms` -- Execution time (for tool events)

Read the most recent log file(s) using `Read` or `Bash`.

### Step 3: Analyze by Mode

#### Mode: `summary` (default)

Produce a summary table:

```
## Ivy Observability Summary

**Session**: <session_id>
**Duration**: <first_event> to <last_event>
**Total events**: <count>

| Metric | Value |
|--------|-------|
| Tool calls (success) | N |
| Tool calls (failure) | N |
| Unique tools used | N |
| Errors | N |

### Tool Usage Breakdown

| Tool | Calls | Avg Duration | Failures |
|------|-------|-------------|----------|
| ivy_verify | N | Nms | N |
| ivy_lint | N | Nms | N |
| ... | | | |
```

#### Mode: `events`

Show a chronological event table:

```
## Event Log

| Time | Event | Tool | Duration | Status |
|------|-------|------|----------|--------|
| HH:MM:SS | PostToolUseSuccess | ivy_verify | 2340ms | OK |
| HH:MM:SS | PostToolUseFailure | ivy_compile | 5200ms | FAIL |
| ... | | | | |
```

#### Mode: `errors`

Filter to only `PostToolUseFailure` events and any events with `error` fields:

```
## Errors

### Error 1: <timestamp>
- **Tool**: <tool_name>
- **Duration**: <duration_ms>ms
- **Details**: <error message or diagnostics>

### Error 2: ...
```

If no errors: "No errors recorded in this session."

#### Mode: `timeline`

Show an ASCII bar chart of event density over time (bucket by minute):

```
## Event Timeline

HH:00  ████████████  (12 events)
HH:01  ████  (4 events)
HH:02  ██████████████████  (18 events)
HH:03  ██  (2 events)
...
```

## Notes

- If the `mode` argument is not provided, default to `summary`.
- If multiple session log files exist, analyze the most recent one unless the user specifies otherwise.
- The observability hooks are configured in the plugin's `hooks/` directory. If no logs exist, the hooks may not have been triggered.

See the `tooling-reference` skill for tool architecture.
