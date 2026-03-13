#!/usr/bin/env bash
# block-direct-ivy.sh
#
# PreToolUse hook that warns about direct Ivy CLI calls in Bash commands.
# Suggests using ivy-tools MCP tools instead.
#
# Receives tool input via stdin as JSON with a "command" field.
# Exit 0 = allow (with suggestion), exit non-zero = block.

set -euo pipefail

# Read the tool input from stdin
INPUT=$(cat)

# Extract the command field from the JSON input
COMMAND=$(printf '%s' "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('command',''))" 2>/dev/null || echo "")

# Check if the command contains direct Ivy CLI tool invocations
if echo "$COMMAND" | grep -qE '\bivy_check\b|\bivyc\b|\bivy_show\b|\bivy_to_cpp\b'; then
    echo "NOTE: Consider using ivy-tools MCP tools instead of direct CLI:"
    echo "  ivy_check  -> ivy_verify MCP tool     (or /nct-check)"
    echo "  ivyc       -> ivy_compile MCP tool    (or /nct-compile)"
    echo "  ivy_show   -> ivy_model_info MCP tool (or /nct-model-info)"
    echo "  ivy_to_cpp -> ivy_compile MCP tool"
    echo ""
    echo "MCP tools provide structured JSON output and integrate with the semantic model."
fi

# Always allow the command (informational only)
exit 0
