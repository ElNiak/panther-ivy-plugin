#!/usr/bin/env bash
# PreToolUse hook: warn if ivy-lsp indexing has not completed.
#
# Quick check — reads the LSP log symlink for the indexing milestone.
# Always allows the tool call (never blocks); surfaces a warning if
# indexing appears incomplete.
set -euo pipefail

LOG_FILE="${IVY_LSP_LOG_PATH:-/tmp/ivy-lsp-latest.log}"

# Fast path: log exists and has indexing milestone → allow silently
if [ -f "$LOG_FILE" ] && grep -q "Indexed .* files" "$LOG_FILE" 2>/dev/null; then
    echo '{"decision":"allow"}'
    exit 0
fi

# No milestone found — warn but allow
echo '{"decision":"allow","message":"WARNING: Ivy workspace may not be fully indexed yet. MCP tool results could be incomplete."}'
