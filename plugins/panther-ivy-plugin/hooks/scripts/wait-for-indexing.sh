#!/usr/bin/env bash
# SessionStart hook: wait for ivy-lsp MCP server to be ready.
#
# Polls the MCP log for the "Starting ivy-lsp MCP server" message.
# The MCP server builds models lazily on first tool call, so we only
# need to confirm the server process started. Surfaces status as
# additionalContext for Claude.
set -euo pipefail

MCP_LOG="${IVY_MCP_LOG_PATH:-/tmp/ivy-mcp-latest.log}"
LSP_LOG="${IVY_LSP_LOG_PATH:-/tmp/ivy-lsp-lsp-latest.log}"
MAX_WAIT="${IVY_LSP_INDEX_TIMEOUT:-15}"

# --- Wait for MCP server startup ---
MCP_READY=0
for _i in $(seq 1 "$MAX_WAIT"); do
    if [ -f "$MCP_LOG" ] && grep -q "Starting ivy-lsp MCP server" "$MCP_LOG" 2>/dev/null; then
        MCP_READY=1
        break
    fi
    sleep 1
done

# --- Check LSP indexing status (non-blocking) ---
LSP_STATUS=""
if [ -f "$LSP_LOG" ] && grep -q "Indexed .* files" "$LSP_LOG" 2>/dev/null; then
    LSP_STATUS=$(grep "Indexed .* files" "$LSP_LOG" | tail -1)
fi

# --- Build context message ---
if [ "$MCP_READY" = "1" ]; then
    if [ -n "$LSP_STATUS" ]; then
        MSG="[ivy-indexing] MCP server ready. LSP: $LSP_STATUS."
    else
        MSG="[ivy-indexing] MCP server ready. LSP indexing status unknown (model builds lazily on first tool call)."
    fi
else
    MSG="[ivy-indexing] WARNING: MCP server did not start within ${MAX_WAIT}s. MCP tools may be unavailable."
fi

# Escape for JSON
ESCAPED=$(printf '%s' "$MSG" | python3 -c "import json,sys; print(json.dumps(sys.stdin.read())[1:-1])" 2>/dev/null || echo "$MSG")

cat <<EOFJ
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "$ESCAPED"
  }
}
EOFJ
