#!/usr/bin/env bash
# PreToolUse hook: BLOCK MCP tools while ivy-lsp is still indexing.
#
# Uses permissionDecision:"deny" to actually prevent the tool call.
# Claude sees the denial reason and can retry on the next turn.
#
# Readiness protocol (consistent with wait-for-indexing.sh):
#   Signal 1: LSP log "Indexed N files"      — Phase 1 indexing complete
#   Signal 2: Offline .ivy-index/ exists      — pre-built offline index
#   Signal 3: MCP log "Pre-populated..."      — MCP prepopulation done
#   Signal 4: MCP log "[MCP-READY]"           — MCP startup complete
#   Any ONE signal is sufficient to allow tool calls.
set -euo pipefail

MCP_LOG="${IVY_MCP_LOG_PATH:-/tmp/ivy-mcp-latest.log}"
LSP_LOG="${IVY_LSP_LOG_PATH:-/tmp/ivy-lsp-lsp-latest.log}"
WORKSPACE_ROOT="${IVY_WORKSPACE_ROOT:-}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=statusline_update_helper.sh
source "$SCRIPT_DIR/statusline_update_helper.sh"

# Circuit breaker: after 6 denials (~60s), degrade to warning
DENY_STATE="/tmp/ivy-lsp-pids/indexing-deny-count"
_increment_deny() {
    local count=0
    [ -f "$DENY_STATE" ] && count=$(cat "$DENY_STATE" 2>/dev/null || echo 0)
    count=$((count + 1))
    echo "$count" > "$DENY_STATE"
    echo "$count"
}
_reset_deny() {
    rm -f "$DENY_STATE"
}

# --- Check readiness signals ---

# Signal 1: LSP finished Phase 1 indexing
if [ -f "$LSP_LOG" ] && grep -q "Indexed .* files" "$LSP_LOG" 2>/dev/null; then
    _reset_deny
    _update_statusline lsp '{"status":"ready"}'
    exit 0  # Ready — allow tool call
fi

# Signal 2: Offline .ivy-index/ exists (pre-built by `ivy_lsp index --all`)
if [ -n "$WORKSPACE_ROOT" ]; then
    for idx_dir in "$WORKSPACE_ROOT"/protocol-testing/*/.ivy-index; do
        if [ -d "$idx_dir" ] && [ -f "$idx_dir/manifest.json" ]; then
            _reset_deny
            _update_statusline lsp '{"status":"ready"}'
            exit 0  # Offline index available — allow tool call
        fi
    done
fi

# Signal 3: MCP prepopulated from offline index
if [ -f "$MCP_LOG" ] && grep -q "Pre-populated from offline index\|pre-warmed\|PREWARM-DONE" "$MCP_LOG" 2>/dev/null; then
    _reset_deny
    _update_statusline lsp '{"status":"ready"}'
    exit 0  # MCP model ready — allow tool call
fi

# Signal 4: MCP server declared ready (consistent with wait-for-indexing.sh)
if [ -f "$MCP_LOG" ] && grep -q "\[MCP-READY\]" "$MCP_LOG" 2>/dev/null; then
    _reset_deny
    _update_statusline lsp '{"status":"ready"}'
    exit 0  # MCP ready sentinel — allow tool call
fi

# --- Not ready: check if server is starting/indexing ---

# MCP server started but indexing not done
if [ -f "$MCP_LOG" ] && grep -q "Starting ivy-lsp MCP server" "$MCP_LOG" 2>/dev/null; then
    if [ -f "$LSP_LOG" ]; then
        LOG_MTIME=$(stat -f%m "$LSP_LOG" 2>/dev/null || stat -c%Y "$LSP_LOG" 2>/dev/null || echo 0)
        NOW=$(date +%s)
        AGE=$(( NOW - LOG_MTIME ))
        if [ "$AGE" -lt 120 ]; then
            DENY_COUNT=$(_increment_deny)
            if [ "$DENY_COUNT" -gt 6 ]; then
                _update_statusline lsp '{"status":"ready"}'
                cat <<ENDJSON
{"hookSpecificOutput":{"hookEventName":"PreToolUse","additionalContext":"[ivy-indexing] LSP indexing appears stuck (${AGE}s, ${DENY_COUNT} denied calls). Allowing tool call — results may be incomplete. Consider running /nct-health."}}
ENDJSON
                exit 0
            fi
            _update_statusline lsp '{"status":"indexing"}'
            cat <<ENDJSON
{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"[ivy-indexing] LSP is still indexing the workspace (${AGE}s elapsed, attempt ${DENY_COUNT}/6). Wait 10 seconds and retry.","additionalContext":"The LSP workspace index is not yet complete. Retry this tool call after a short wait."},"systemMessage":"[ivy-indexing] not ready (attempt ${DENY_COUNT}/6)"}
ENDJSON
            exit 0
        fi
    fi
    # LSP log is old or missing but MCP is up — allow (assume ready)
    exit 0
fi

# MCP server still starting (log < 30s old)
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

# Past grace period or no log — warn but allow
cat <<'ENDJSON'
{"hookSpecificOutput":{"hookEventName":"PreToolUse","additionalContext":"[ivy-health] MCP server may not be fully started. If this call fails, wait 10 seconds and retry."}}
ENDJSON
