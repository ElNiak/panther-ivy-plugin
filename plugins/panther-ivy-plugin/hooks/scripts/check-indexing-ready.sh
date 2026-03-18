#!/usr/bin/env bash
# PreToolUse hook: warn if ivy-lsp MCP server has not started.
#
# Quick check — reads the MCP log for the startup message.
# Always allows the tool call (never blocks); surfaces a warning if
# the server appears not ready.
set -euo pipefail

MCP_LOG="${IVY_MCP_LOG_PATH:-/tmp/ivy-mcp-latest.log}"

# Fast path: MCP server started → allow silently
if [ -f "$MCP_LOG" ] && grep -q "Starting ivy-lsp MCP server" "$MCP_LOG" 2>/dev/null; then
    echo '{"decision":"allow"}'
    exit 0
fi

# No startup message found — warn but allow
echo '{"decision":"allow","message":"WARNING: Ivy MCP server may not be fully started yet. Results could be incomplete."}'
