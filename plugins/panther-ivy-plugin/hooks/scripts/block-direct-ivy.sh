#\!/usr/bin/env bash
# block-direct-ivy.sh
#
# PreToolUse hook that blocks direct Ivy CLI calls in Bash commands.
# Enforces usage of ivy-tools MCP tools instead.
#
# Receives tool input via stdin as JSON with a "command" field.
# Exit 0 = allow, exit non-zero = block with message.

set -euo pipefail

# Read the tool input from stdin
INPUT=$(cat)

# Extract the command field from the JSON input
COMMAND=$(echo "$INPUT" | grep -o '"command"[[:space:]]*:[[:space:]]*"[^"]*"' | head -1 | sed 's/"command"[[:space:]]*:[[:space:]]*"//;s/"$//')

# Check if the command contains direct Ivy CLI tool invocations
if echo "$COMMAND" | grep -qE '\bivy_check\b|\bivyc\b|\bivy_show\b|\bivy_to_cpp\b'; then
    echo "BLOCKED: Direct Ivy CLI usage detected."
    echo ""
    echo "Use ivy-tools MCP tools instead:"
    echo "  ivy_check  -> mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_verify     (or /nct-check)"
    echo "  ivyc       -> mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_compile    (or /nct-compile)"
    echo "  ivy_show   -> mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_model_info (or /nct-model-info)"
    echo "  ivy_to_cpp -> mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_compile"
    exit 1
fi

# Allow the command
exit 0
