#!/usr/bin/env bash
# SessionStart hook: wait for ivy-lsp MCP server to be ready.
#
# Polls the MCP log for the "[MCP-READY]" sentinel logged after tool
# registration completes. Surfaces status as additionalContext for Claude.
set -euo pipefail

MCP_LOG="${IVY_MCP_LOG_PATH:-/tmp/ivy-mcp-latest.log}"
LSP_LOG="${IVY_LSP_LOG_PATH:-/tmp/ivy-lsp-lsp-latest.log}"
MAX_WAIT="${IVY_LSP_INDEX_TIMEOUT:-30}"

# --- Guard: skip polling if MCP log is unavailable ---
# If IVY_MCP_LOG_PATH was not explicitly set AND the fallback file doesn't exist,
# the MCP server has not been configured yet (detect-ivy-workspace.sh may not have run).
# Exit early with an informational message rather than polling for 30s needlessly.
if [ -z "${IVY_MCP_LOG_PATH+x}" ] && [ ! -f "/tmp/ivy-mcp-latest.log" ]; then
    SKIP_MSG="[ivy-indexing] MCP server log not available — skipping readiness check"
    SKIP_ESCAPED=$(printf '%s' "$SKIP_MSG" | python3 -c "import json,sys; print(json.dumps(sys.stdin.read())[1:-1])" 2>/dev/null)
    if [ -z "$SKIP_ESCAPED" ]; then
        SKIP_ESCAPED="$SKIP_MSG"
    fi
    cat <<EOFSKIP
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "$SKIP_ESCAPED"
  }
}
EOFSKIP
    exit 0
fi

# --- Wait for MCP server startup ---
MCP_READY=0
MSG=""
for _i in $(seq 1 "$MAX_WAIT"); do
    if [ -f "$MCP_LOG" ] && grep -q "\[MCP-READY\]" "$MCP_LOG" 2>/dev/null; then
        MCP_READY=1
        break
    fi
    sleep 1
    # Check for MCP crash sentinel
    if [ -f "$MCP_LOG" ] && grep -q "\[MCP-FATAL\]" "$MCP_LOG" 2>/dev/null; then
        CRASH_MSG=$(grep "\[MCP-FATAL\]" "$MCP_LOG" | tail -1)
        MSG="[ivy-indexing] MCP server CRASHED: $CRASH_MSG"
        break
    fi
    # Check if MCP process is still alive
    for pidfile in /tmp/ivy-lsp-pids/mcp-*.pid; do
        [ -f "$pidfile" ] || continue
        mcp_pid="$(cat "$pidfile" 2>/dev/null)" || continue
        if ! kill -0 "$mcp_pid" 2>/dev/null; then
            MSG="[ivy-indexing] MCP server process died (PID=$mcp_pid)"
            break 2
        fi
    done
done

# --- Check LSP indexing status (non-blocking) ---
LSP_STATUS=""
if [ -f "$LSP_LOG" ] && grep -q "Indexed .* files" "$LSP_LOG" 2>/dev/null; then
    LSP_STATUS=$(grep "Indexed .* files" "$LSP_LOG" | tail -1)
fi

# --- Build context message ---
if [ -n "$MSG" ]; then
    # Crash or process-died message was already set in the polling loop
    :
elif [ "$MCP_READY" = "1" ]; then
    if [ -n "$LSP_STATUS" ]; then
        MSG="[ivy-indexing] MCP server ready. LSP: $LSP_STATUS."
    else
        MSG="[ivy-indexing] MCP server ready. LSP indexing status unknown (model builds lazily on first tool call)."
    fi
else
    MSG="[ivy-indexing] WARNING: MCP server did not start within ${MAX_WAIT}s. MCP tools may be unavailable."
fi

# Escape for JSON
ESCAPED=$(printf '%s' "$MSG" | python3 -c "import json,sys; print(json.dumps(sys.stdin.read())[1:-1])" 2>/dev/null)
if [ -z "$ESCAPED" ]; then
    ESCAPED="[ivy-indexing] Status message could not be JSON-escaped"
fi

cat <<EOFJ
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "$ESCAPED"
  }
}
EOFJ
