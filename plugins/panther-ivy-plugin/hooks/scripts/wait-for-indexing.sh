#!/usr/bin/env bash
# SessionStart hook: wait for ivy-lsp MCP server to be ready.
#
# Polls the MCP log for the "[MCP-READY]" sentinel logged after tool
# registration completes. Surfaces status as additionalContext for Claude.
set -euo pipefail

START=$(date +%s)

# Emit partial status if killed by hook timeout
trap '_emit_timeout_msg' TERM INT
_emit_timeout_msg() {
    local elapsed=$(( $(date +%s) - START ))
    cat <<EOFT
{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"[ivy-indexing] Readiness check timed out. MCP tools may still be starting — retry after 10 seconds if a tool call fails."},"systemMessage":"[ivy-indexing] timed out after ${elapsed}s"}
EOFT
    exit 0
}

MCP_LOG="${IVY_MCP_LOG_PATH:-/tmp/ivy-mcp-latest.log}"
LSP_LOG="${IVY_LSP_LOG_PATH:-/tmp/ivy-lsp-lsp-latest.log}"
MAX_WAIT="${IVY_LSP_INDEX_TIMEOUT:-12}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=statusline_update_helper.sh
source "$SCRIPT_DIR/statusline_update_helper.sh"

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
  },
  "systemMessage": "[ivy-indexing] skipped (MCP log unavailable)"
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
        if ! ps -p "$mcp_pid" > /dev/null 2>&1; then
            MSG="[ivy-indexing] MCP server process died (PID=$mcp_pid)"
            break 2
        fi
    done
done

# --- Wait for LSP indexing (non-blocking, max 10s additional) ---
LSP_STATUS=""
LSP_INDEXED=0
if [ "$MCP_READY" = "1" ] && [ -f "$LSP_LOG" ]; then
    for _j in $(seq 1 5); do
        if grep -q "Indexed .* files" "$LSP_LOG" 2>/dev/null; then
            LSP_INDEXED=1
            LSP_STATUS=$(grep "Indexed .* files" "$LSP_LOG" | tail -1)
            break
        fi
        sleep 1
    done
    if [ "$LSP_INDEXED" = "0" ]; then
        LSP_STATUS="still indexing"
    fi
elif [ -f "$LSP_LOG" ] && grep -q "Indexed .* files" "$LSP_LOG" 2>/dev/null; then
    LSP_INDEXED=1
    LSP_STATUS=$(grep "Indexed .* files" "$LSP_LOG" | tail -1)
fi

# --- Report active workspace size (non-blocking) ---
WORKSPACE_INFO=""
if [ -n "${IVY_ACTIVE_WORKSPACE:-}" ]; then
    WORKSPACE_ROOT="${IVY_WORKSPACE_ROOT:-}"
    if [ -n "$WORKSPACE_ROOT" ] && [ -f "${WORKSPACE_ROOT}/.ivy-workspace-state.json" ]; then
        IVY_FILE_COUNT=$(find "$WORKSPACE_ROOT/protocol-testing/${IVY_ACTIVE_WORKSPACE}/" -name "*.ivy" 2>/dev/null | wc -l | tr -d ' ')
        WORKSPACE_INFO=" Active workspace: ${IVY_ACTIVE_WORKSPACE} (${IVY_FILE_COUNT} .ivy files)."
    else
        WORKSPACE_INFO=" Active workspace: ${IVY_ACTIVE_WORKSPACE}."
    fi
fi

# --- Check model pre-warming status (non-blocking) ---
MODEL_STATUS=""
if [ -f "$MCP_LOG" ] && grep -q "\[INDEX-MODEL-READY\]" "$MCP_LOG" 2>/dev/null; then
    MODEL_STATUS="ready"
elif [ -f "$MCP_LOG" ] && grep -q "\[INDEX-PREWARM\]" "$MCP_LOG" 2>/dev/null; then
    MODEL_STATUS="building"
fi

# --- Build context message ---
if [ -n "$MSG" ]; then
    # Crash or process-died message was already set in the polling loop
    :
elif [ "$MCP_READY" = "1" ]; then
    # Base MCP ready message
    BASE_MSG="[ivy-indexing] MCP server ready."
    # Append model status
    if [ "$MODEL_STATUS" = "ready" ]; then
        MODEL_MSG=" Model: ready."
    elif [ "$MODEL_STATUS" = "building" ]; then
        MODEL_MSG=" Model: building (will be ready for coverage/traceability tools shortly)."
    else
        MODEL_MSG=" Model builds lazily on first tool call."
    fi
    # Append LSP status
    if [ "$LSP_INDEXED" = "1" ] && [ -n "$LSP_STATUS" ]; then
        MSG="${BASE_MSG}${MODEL_MSG} LSP: $LSP_STATUS."
    elif [ "$LSP_STATUS" = "still indexing" ]; then
        MSG="${BASE_MSG}${MODEL_MSG} LSP: still indexing. Wait 10 seconds for indexing to finish before calling MCP tools."
    else
        MSG="${BASE_MSG}${MODEL_MSG}"
    fi
    # Append workspace info if available
    if [ -n "$WORKSPACE_INFO" ]; then
        MSG="${MSG}${WORKSPACE_INFO}"
    fi
    # Append soft retry guidance for edge cases
    MSG="${MSG} Note: If an ivy MCP tool fails unexpectedly, wait 5 seconds and retry once — the server may be recovering."
else
    MSG="[ivy-indexing] WARNING: MCP server did not start within ${MAX_WAIT}s. If an ivy MCP tool call fails with a server error, wait 10 seconds and retry the same call up to 3 times before reporting failure to the user."
fi

# --- Statusline cache update ---
if [ "$MCP_READY" = "1" ]; then
    _update_statusline mcp '{"status":"up"}'
else
    _update_statusline mcp '{"status":"down","last_error":"startup-timeout"}'
fi
if [ "$LSP_INDEXED" = "1" ]; then
    _update_statusline lsp '{"status":"ready"}'
elif [ "$LSP_STATUS" = "still indexing" ]; then
    _update_statusline lsp '{"status":"indexing"}'
fi

# Escape for JSON
ESCAPED=$(printf '%s' "$MSG" | python3 -c "import json,sys; print(json.dumps(sys.stdin.read())[1:-1])" 2>/dev/null)
if [ -z "$ESCAPED" ]; then
    ESCAPED="[ivy-indexing] Status message could not be JSON-escaped"
fi

ELAPSED=$(( $(date +%s) - START ))
if [ "$MCP_READY" = "1" ]; then
    SYS_MSG="[ivy-indexing] indexed (${ELAPSED}s)"
else
    SYS_MSG="[ivy-indexing] timed out after ${ELAPSED}s"
fi

cat <<EOFJ
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "$ESCAPED"
  },
  "systemMessage": "$SYS_MSG"
}
EOFJ
