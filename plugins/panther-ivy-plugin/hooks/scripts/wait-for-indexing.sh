#!/usr/bin/env bash
# SessionStart hook: wait for ivy-lsp indexing to complete.
#
# Polls the LSP log for the "Indexed N files" milestone (logged by
# server_setup.py after Phase 1 fast-index).  Surfaces indexing status
# as additionalContext so Claude knows the workspace is ready.
set -euo pipefail

LOG_FILE="${IVY_LSP_LOG_PATH:-/tmp/ivy-lsp-latest.log}"
MAX_WAIT="${IVY_LSP_INDEX_TIMEOUT:-30}"

for _i in $(seq 1 "$MAX_WAIT"); do
    if [ -f "$LOG_FILE" ] && grep -q "Indexed .* files" "$LOG_FILE" 2>/dev/null; then
        INDEXED_LINE=$(grep "Indexed .* files" "$LOG_FILE" | tail -1)
        # Escape for JSON
        ESCAPED=$(printf '%s' "$INDEXED_LINE" | python3 -c "import json,sys; print(json.dumps(sys.stdin.read())[1:-1])" 2>/dev/null || echo "$INDEXED_LINE")
        cat <<EOFJ
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "[ivy-indexing] $ESCAPED. Workspace ready."
  }
}
EOFJ
        exit 0
    fi
    sleep 1
done

# Timeout — warn but don't block
cat <<EOFJ
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "[ivy-indexing] WARNING: Indexing did not complete within ${MAX_WAIT}s. MCP tools may return incomplete results until indexing finishes."
  }
}
EOFJ
