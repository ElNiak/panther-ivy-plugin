#!/usr/bin/env bash
# PreToolUse hook: warn if ivy-lsp MCP server has not started.
#
# Quick check — reads the MCP log for the startup message.
# Always allows the tool call (never blocks); surfaces a warning if
# the server appears not ready. Includes grace period logic for startup.
set -euo pipefail

MCP_LOG="${IVY_MCP_LOG_PATH:-/tmp/ivy-mcp-latest.log}"

# Fast path: MCP server started → allow silently (no output = silent pass)
if [ -f "$MCP_LOG" ] && grep -q "Starting ivy-lsp MCP server" "$MCP_LOG" 2>/dev/null; then
    exit 0
fi

# Grace period: if log exists but is < 30s old, server is still starting
if [ -f "$MCP_LOG" ]; then
    LOG_MTIME=$(stat -f%m "$MCP_LOG" 2>/dev/null || stat -c%Y "$MCP_LOG" 2>/dev/null || echo 0)
    NOW=$(date +%s)
    AGE=$(( NOW - LOG_MTIME ))
    if [ "$AGE" -lt 30 ]; then
        echo '{"systemMessage":"The Ivy MCP server is still starting up ('"${AGE}"'s elapsed). Do NOT call this tool yet. Wait 10 seconds, then retry this exact tool call. The server typically needs 5-15 seconds to initialize."}'
        exit 0
    fi
fi

# Past grace period or no log at all — warn but allow
echo '{"systemMessage":"WARNING: Ivy MCP server may not be fully started. If this call fails, wait 10 seconds and retry up to 3 times."}'
