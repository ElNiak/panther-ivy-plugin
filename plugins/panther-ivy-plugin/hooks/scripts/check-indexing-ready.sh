#!/usr/bin/env bash
# PreToolUse hook: BLOCK MCP tools while ivy-lsp is still indexing.
#
# Uses permissionDecision:"deny" to actually prevent the tool call,
# not just inject context. Claude sees the denial reason and can retry.
set -euo pipefail

MCP_LOG="${IVY_MCP_LOG_PATH:-/tmp/ivy-mcp-latest.log}"

# Fast path: MCP server started → check LSP indexing before allowing
if [ -f "$MCP_LOG" ] && grep -q "Starting ivy-lsp MCP server" "$MCP_LOG" 2>/dev/null; then
    # MCP is up — but LSP may still be indexing the workspace
    LSP_LOG="${IVY_LSP_LOG_PATH:-/tmp/ivy-lsp-lsp-latest.log}"
    if [ -f "$LSP_LOG" ]; then
        if ! grep -q "Indexed .* files" "$LSP_LOG" 2>/dev/null; then
            # LSP still indexing — BLOCK the tool call
            LOG_MTIME=$(stat -f%m "$LSP_LOG" 2>/dev/null || stat -c%Y "$LSP_LOG" 2>/dev/null || echo 0)
            NOW=$(date +%s)
            AGE=$(( NOW - LOG_MTIME ))
            if [ "$AGE" -lt 120 ]; then
                cat <<ENDJSON
{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"[ivy-indexing] LSP is still indexing the workspace (${AGE}s elapsed). Wait 10 seconds and retry. Results will be incomplete until indexing finishes.","additionalContext":"The LSP workspace index is not yet complete. Retry this tool call after a short wait."}}
ENDJSON
                exit 0
            fi
        fi
    fi
    exit 0
fi

# Grace period: if log exists but is < 30s old, server is still starting
if [ -f "$MCP_LOG" ]; then
    LOG_MTIME=$(stat -f%m "$MCP_LOG" 2>/dev/null || stat -c%Y "$MCP_LOG" 2>/dev/null || echo 0)
    NOW=$(date +%s)
    AGE=$(( NOW - LOG_MTIME ))
    if [ "$AGE" -lt 30 ]; then
        cat <<ENDJSON
{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"[ivy-startup] MCP server is still starting up (${AGE}s elapsed). Wait 10 seconds and retry.","additionalContext":"The Ivy MCP server needs 5-15 seconds to initialize. Retry after a short wait."}}
ENDJSON
        exit 0
    fi
fi

# Past grace period or no log at all — warn but allow
cat <<'ENDJSON'
{"hookSpecificOutput":{"hookEventName":"PreToolUse","additionalContext":"[ivy-health] MCP server may not be fully started. If this call fails, wait 10 seconds and retry."}}
ENDJSON
