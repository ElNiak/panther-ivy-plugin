#!/usr/bin/env bash
# lint-before-verify.sh
#
# PreToolUse hook that advises running ivy_lint before ivy_verify.
# Advisory only — always exits 0 (non-blocking).
#
# Receives tool input via stdin as JSON with a "tool_name" field.

set -euo pipefail

# Read the tool input from stdin
INPUT=$(cat)

# python3 is required to parse JSON input
if ! command -v python3 &>/dev/null; then
  exit 0
fi

# Extract the tool name from the JSON input
TOOL_NAME=$(printf '%s' "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('tool_name',''))" 2>&1) || exit 0

# Check if this is an ivy_verify call
if echo "$TOOL_NAME" | grep -q "ivy_verify"; then
    echo "Tip: Consider running ivy_lint first for fast structural validation (milliseconds vs seconds). This catches syntax errors before the heavier formal verification."
fi

# Always allow (advisory only)
exit 0
