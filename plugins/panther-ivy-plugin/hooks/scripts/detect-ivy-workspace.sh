#!/usr/bin/env bash
# SessionStart hook: detect Ivy workspace and inject context for Claude.
#
# Outputs:
#   - JSON with hookSpecificOutput.additionalContext for Claude
#   - Writes IVY_WORKSPACE_ROOT to CLAUDE_ENV_FILE (if set)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_SCRIPTS_DIR="$SCRIPT_DIR/../../scripts"
# shellcheck source=../../scripts/workspace-common.sh
source "$PLUGIN_SCRIPTS_DIR/workspace-common.sh"

detect_ivy_workspace

# Write env var for later Bash commands
if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
    printf 'IVY_WORKSPACE_ROOT="%s"\n' "$DETECTED_ROOT" >> "$CLAUDE_ENV_FILE"
    # Propagate log symlink paths so downstream hooks find the right logs
    printf 'IVY_LSP_LOG_PATH="%s"\n' "${IVY_LSP_LOG_DIR:-/tmp}/ivy-lsp-lsp-latest.log" >> "$CLAUDE_ENV_FILE"
    printf 'IVY_MCP_LOG_PATH="%s"\n' "${IVY_LSP_LOG_DIR:-/tmp}/ivy-mcp-latest.log" >> "$CLAUDE_ENV_FILE"
    printf 'IVY_SESSION_ID="%s"\n' "$$" >> "$CLAUDE_ENV_FILE"
    printf 'IVY_MCP_PID_FILE="/tmp/ivy-mcp-%s.pid"\n' "$$" >> "$CLAUDE_ENV_FILE"
fi

# Determine MCP server status (non-blocking quick check)
MCP_LOG="${IVY_MCP_LOG_PATH:-/tmp/ivy-mcp-latest.log}"
MCP_STATUS="not started"
if [ -f "$MCP_LOG" ] && grep -q "\[MCP-READY\]" "$MCP_LOG" 2>/dev/null; then
    MCP_STATUS="ready"
elif [ -f "$MCP_LOG" ]; then
    MCP_STATUS="starting"
fi

# Count Ivy model files if in a PANTHER workspace
MODEL_INFO=""
if [ "$DETECTED_TYPE" = "panther" ] && [ -d "$DETECTED_ROOT/protocol-testing" ]; then
    IVY_COUNT=$(find "$DETECTED_ROOT/protocol-testing" -name "*.ivy" -type f 2>/dev/null | wc -l | tr -d ' ')
    MODEL_INFO=" | Models: ${IVY_COUNT} .ivy files"
fi

# Build context message for Claude
if [ "$DETECTED_TYPE" = "panther" ]; then
    context="[ivy-workspace] Detected PANTHER project at: $DETECTED_ROOT. Ivy models are in protocol-testing/. The ivy-tools MCP server and LSP are scoped to this directory. MCP: ${MCP_STATUS}${MODEL_INFO}."
elif [ "$DETECTED_TYPE" = "standalone" ]; then
    context="[ivy-workspace] Detected standalone Ivy project at: $DETECTED_ROOT. MCP: ${MCP_STATUS}."
else
    context="[ivy-workspace] No Ivy project detected. Using CWD as workspace: $DETECTED_ROOT."
fi

# Escape context for JSON safety using proper JSON escaping
context_escaped=$(printf '%s' "$context" | python3 -c "import json,sys; print(json.dumps(sys.stdin.read())[1:-1])" 2>/dev/null)
if [ -z "$context_escaped" ]; then
    context_escaped="[ivy-workspace] Context could not be JSON-escaped"
fi

# Output hook result as JSON
cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "$context_escaped"
  }
}
EOF
