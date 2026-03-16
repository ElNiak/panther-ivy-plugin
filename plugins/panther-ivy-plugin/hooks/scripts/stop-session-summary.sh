#!/usr/bin/env bash
# stop-session-summary.sh
#
# Stop hook: output a session summary with ivy_lint status of modified .ivy files.
# Non-blocking — always exits 0. Outputs additionalContext JSON.

set -euo pipefail

# python3 is required to parse JSON and format output
if ! command -v python3 &>/dev/null; then
  exit 0
fi

# Find .ivy files modified in the working tree (unstaged + staged)
MODIFIED_IVY=$(git diff --name-only HEAD 2>/dev/null | grep '\.ivy$' || true)
STAGED_IVY=$(git diff --cached --name-only 2>/dev/null | grep '\.ivy$' || true)
UNTRACKED_IVY=$(git ls-files --others --exclude-standard 2>/dev/null | grep '\.ivy$' || true)

# Combine and deduplicate
ALL_IVY=$(printf '%s\n%s\n%s' "$MODIFIED_IVY" "$STAGED_IVY" "$UNTRACKED_IVY" | sort -u | grep -v '^$' || true)

if [ -z "$ALL_IVY" ]; then
  exit 0  # No .ivy files modified — nothing to report
fi

FILE_COUNT=$(echo "$ALL_IVY" | wc -l | tr -d ' ')
ISSUES=""
ISSUE_COUNT=0

while IFS= read -r f; do
  [ -z "$f" ] && continue
  [ ! -f "$f" ] && continue

  FILE_ISSUES=""

  # Check #lang header
  if ! head -1 "$f" 2>/dev/null | grep -q '#lang ivy1.7'; then
    FILE_ISSUES="${FILE_ISSUES}missing #lang header, "
  fi

  # Check balanced braces
  STRIPPED=$(sed 's/#.*//; s/"[^"]*"//g' "$f" 2>/dev/null || true)
  OPEN=$(printf '%s' "$STRIPPED" | grep -o '{' | wc -l | tr -d ' ')
  CLOSE=$(printf '%s' "$STRIPPED" | grep -o '}' | wc -l | tr -d ' ')
  if [ "$OPEN" -ne "$CLOSE" ]; then
    FILE_ISSUES="${FILE_ISSUES}unbalanced braces ($OPEN/$CLOSE), "
  fi

  if [ -n "$FILE_ISSUES" ]; then
    ISSUES="${ISSUES}  - ${f}: ${FILE_ISSUES%%, }\n"
    ISSUE_COUNT=$((ISSUE_COUNT + 1))
  fi
done <<< "$ALL_IVY"

# Build summary
if [ "$ISSUE_COUNT" -gt 0 ]; then
  SUMMARY="[IVY SESSION SUMMARY] $FILE_COUNT .ivy file(s) modified, $ISSUE_COUNT with lint issues:\\n${ISSUES}Run ivy_lint on flagged files before committing."
else
  SUMMARY="[IVY SESSION SUMMARY] $FILE_COUNT .ivy file(s) modified, all pass basic structural checks."
fi

# Output as additionalContext
ESCAPED=$(printf '%s' "$SUMMARY" | python3 -c "import json,sys; print(json.dumps(sys.stdin.read())[1:-1])")
printf '{"hookSpecificOutput":{"hookEventName":"Stop","additionalContext":"%s"}}' "$ESCAPED"

exit 0
