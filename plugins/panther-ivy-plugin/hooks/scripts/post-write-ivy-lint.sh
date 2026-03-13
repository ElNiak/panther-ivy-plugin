#!/usr/bin/env bash
# post-write-ivy-lint.sh
#
# PostToolUse hook: fast structural check after .ivy file writes.
# Returns additionalContext if issues found (non-blocking).
#
# Receives tool input via stdin as JSON with tool_input.file_path.
# Exit 0 always (non-blocking); outputs JSON additionalContext on issues.

set -euo pipefail

INPUT=$(cat)

# Extract file path from Write or Edit tool input
FILE_PATH=$(printf '%s' "$INPUT" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('file_path',''))" 2>/dev/null || echo "")

# Only check .ivy files
if [ -z "$FILE_PATH" ] || [[ "$FILE_PATH" != *.ivy ]]; then
  exit 0
fi

# Skip if file doesn't exist
if [ ! -f "$FILE_PATH" ]; then
  exit 0
fi

ERRORS=""

# Check #lang header
if ! head -1 "$FILE_PATH" 2>/dev/null | grep -q '#lang ivy1.7'; then
  ERRORS="${ERRORS}- Missing #lang ivy1.7 header on first line\n"
fi

# Check balanced braces (rough structural check)
STRIPPED=$(sed 's/#.*//; s/"[^"]*"//g' "$FILE_PATH" 2>/dev/null)
OPEN=$(printf '%s' "$STRIPPED" | grep -o '{' | wc -l | tr -d ' ')
CLOSE=$(printf '%s' "$STRIPPED" | grep -o '}' | wc -l | tr -d ' ')
if [ "$OPEN" -ne "$CLOSE" ]; then
  ERRORS="${ERRORS}- Unbalanced braces: $OPEN open vs $CLOSE close\n"
fi

# Check for empty file
if [ ! -s "$FILE_PATH" ]; then
  ERRORS="${ERRORS}- File is empty\n"
fi

if [ -n "$ERRORS" ]; then
  # Escape for JSON safety (handle " and \ in filenames and error text)
  REL_PATH=$(basename "$FILE_PATH" | sed 's/\\/\\\\/g; s/"/\\"/g')
  ERRORS_ESCAPED=$(printf '%s' "$ERRORS" | sed 's/\\/\\\\/g; s/"/\\"/g')
  # Return additionalContext so Claude sees the issues (non-blocking)
  printf '{"hookSpecificOutput":{"hookEventName":"PostToolUse","additionalContext":"[IVY-LINT] Structural issues in %s:\\n%sRun ivy_lint MCP tool for full diagnostics."}}' "$REL_PATH" "$ERRORS_ESCAPED"
fi

exit 0
