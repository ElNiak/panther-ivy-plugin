---
name: nct-observability
description: Query and analyze Ivy observability session logs (JSONL events from hooks)
arguments:
  - name: mode
    description: "Analysis mode: summary (default), events, errors, timeline"
    required: false
---
> **Shortcut command** — queries session JSONL logs. Always available, never suppressed by active workflows.

<!-- MODE: FAST — Read-only log analysis, no orchestrator required -->

Query and analyze the JSONL session logs written by the panther-ivy-plugin observability hooks. These logs record tool usage, verification results, and session events.

<!-- Workspace: Active workspace state is included in session logs. Use /set-workspace <protocol> before sessions to capture workspace context in observability data. -->

## Instructions

### Step 1: Locate the Log Directory

Search for logs in priority order:
1. `$IVY_OBSERVABILITY_DIR/sessions/` (explicit override)
2. `$IVY_WORKSPACE_ROOT/.observability/sessions/` (primary — workspace-local)
3. `/tmp/ivy-observability/sessions/` (fallback)

Use Bash to check each path:
```bash
echo "${IVY_OBSERVABILITY_DIR:-unset}" && ls "${IVY_OBSERVABILITY_DIR:-/nonexistent}/sessions/" 2>/dev/null || \
ls "${IVY_WORKSPACE_ROOT:-.}/.observability/sessions/" 2>/dev/null || \
ls /tmp/ivy-observability/sessions/ 2>/dev/null || \
echo "No observability logs found"
```

If no logs are found, report: "No observability logs found. Hooks may not have been triggered yet in this session."

### Step 2: Read Log Files

Each session has its own directory (e.g., `sessions/<session_id>/events.jsonl`). Each line is a JSON object with at least:
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
| ivy_diagnostics | N | Nms | N |
| ... | | | |

### Attempt Counts

Per-file / per-layer attempt counters read from the workflow journal. Shows cumulative `fix_attempt` (verify) and `compile_attempt` (build) counts since the most recent `override_attempt_cap` decision for each key (or session start if no override has been recorded).

| Key | Kind | Count | Overrides | Last attempt |
|-----|------|-------|-----------|--------------|
| bgp/bgp_tests/server_tests/bgp_server_test_join.ivy | fix_attempt | 3 | 0 | HH:MM:SS |
| bgp_open | compile_attempt | 5 | 1 | HH:MM:SS |
| ... | | | | |

Sourced from `ivy_workflow_state(action="get_journal", last_n=200)`. Walk the journal per-key: count `progress{kind in {fix_attempt, compile_attempt}}` entries that appear after the most recent `decision{kind: "override_attempt_cap"}` for the same `key`. A non-zero `Overrides` column means the user has authorized the cap to re-engage at least once for that key — an escalation hotspot worth surfacing.
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

### Step 4: Interactive Exploration

After presenting the analysis for any mode, engage the user.

**After presenting summary/events/timeline → Collaborative**:
- Ask: "Here's the {mode} analysis. Want to drill into any specific area? (e.g., a specific tool, time range, or error pattern)"
- If the user picks an area, filter and present the relevant subset.

**If errors mode shows failures → Collaborative**:
- Highlight the most frequent failure: "I see {N} tool failures. The most frequent: `{tool_name}` ({count} times). Want to investigate this pattern?"
- If the user says yes, show the full error details for that tool.

**If no logs found → Inform-and-Continue**:
- State: "No observability logs found. Hooks may not have triggered yet in this session. Run any `/nct-*` command to generate events."
- No gate needed.

## Notes

- If the `mode` argument is not provided, default to `summary`.
- If multiple session log files exist, analyze the most recent one unless the user specifies otherwise.
- The observability hooks are configured in the plugin's `hooks/` directory. If no logs exist, the hooks may not have been triggered.

See the `ivy-toolkit` skill for tool architecture.
