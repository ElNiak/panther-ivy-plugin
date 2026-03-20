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

# Count claim discussion comments added in this session
CLAIM_RESOLVED=0
CLAIM_IUT_FINDING=0
CLAIM_DEFERRED=0
CLAIM_GUARD=0
CLAIM_NA=0
CLAIM_KNOWN_DEV=0

while IFS= read -r f; do
  [ -z "$f" ] && continue
  [ ! -f "$f" ] && continue
  CLAIM_RESOLVED=$((CLAIM_RESOLVED + $(grep -c 'RESOLVED(' "$f" 2>/dev/null || echo 0)))
  CLAIM_IUT_FINDING=$((CLAIM_IUT_FINDING + $(grep -c 'IUT_FINDING(' "$f" 2>/dev/null || echo 0)))
  CLAIM_DEFERRED=$((CLAIM_DEFERRED + $(grep -c 'DEFERRED(' "$f" 2>/dev/null || echo 0)))
  CLAIM_GUARD=$((CLAIM_GUARD + $(grep -c 'GUARD_ADDED(' "$f" 2>/dev/null || echo 0)))
  CLAIM_NA=$((CLAIM_NA + $(grep -c 'N/A(' "$f" 2>/dev/null || echo 0)))
  CLAIM_KNOWN_DEV=$((CLAIM_KNOWN_DEV + $(grep -c 'KNOWN_DEVIATION(' "$f" 2>/dev/null || echo 0)))
done <<< "$ALL_IVY"

CLAIM_TOTAL=$((CLAIM_RESOLVED + CLAIM_IUT_FINDING + CLAIM_DEFERRED + CLAIM_GUARD + CLAIM_NA + CLAIM_KNOWN_DEV))

# --- Session metrics from observability events ---
EVENTS_DIR="${IVY_OBSERVABILITY_DIR:-/tmp/ivy-observability}/sessions"
SESSION_METRICS=""
if [ -d "$EVENTS_DIR" ]; then
  # Find the most recent events.jsonl file (written by log_event.py)
  LATEST_EVENTS=$(find "$EVENTS_DIR" -name "events.jsonl" -mmin -60 2>/dev/null | sort -r | head -1)
  if [ -n "$LATEST_EVENTS" ] && [ -f "$LATEST_EVENTS" ]; then
    SESSION_METRICS=$(python3 -c "
import json, sys, collections
counts = collections.Counter()
durations = collections.defaultdict(float)
errors = 0
try:
    with open('$LATEST_EVENTS') as f:
        for line in f:
            try:
                e = json.loads(line)
                if e.get('event_type') in ('PreToolUse', 'PostToolUse'):
                    tool = e.get('payload', {}).get('tool_name', 'unknown')
                    counts[tool] += 1
                if e.get('event_type') == 'PostToolUseFailure':
                    errors += 1
            except json.JSONDecodeError:
                continue
except Exception:
    pass
if counts:
    top = ', '.join(f'{t}={c}' for t, c in counts.most_common(5))
    print(f'Tool calls: {sum(counts.values())} ({top}). Errors: {errors}')
" 2>/dev/null || true)
  fi
fi

METRICS_SECTION=""
if [ -n "$SESSION_METRICS" ]; then
  METRICS_SECTION="\\n[TOOL METRICS] $SESSION_METRICS"
fi

# Build summary
CLAIM_SECTION=""
if [ "$CLAIM_TOTAL" -gt 0 ]; then
  CLAIM_SECTION="\\n[CLAIM DISCUSSIONS] $CLAIM_TOTAL resolution(s):"
  [ "$CLAIM_RESOLVED" -gt 0 ] && CLAIM_SECTION="${CLAIM_SECTION} $CLAIM_RESOLVED confirmed,"
  [ "$CLAIM_IUT_FINDING" -gt 0 ] && CLAIM_SECTION="${CLAIM_SECTION} $CLAIM_IUT_FINDING IUT findings,"
  [ "$CLAIM_GUARD" -gt 0 ] && CLAIM_SECTION="${CLAIM_SECTION} $CLAIM_GUARD guards added,"
  [ "$CLAIM_DEFERRED" -gt 0 ] && CLAIM_SECTION="${CLAIM_SECTION} $CLAIM_DEFERRED deferred,"
  [ "$CLAIM_NA" -gt 0 ] && CLAIM_SECTION="${CLAIM_SECTION} $CLAIM_NA N/A,"
  [ "$CLAIM_KNOWN_DEV" -gt 0 ] && CLAIM_SECTION="${CLAIM_SECTION} $CLAIM_KNOWN_DEV known deviations,"
  # Remove trailing comma
  CLAIM_SECTION="${CLAIM_SECTION%,}"
fi

if [ "$ISSUE_COUNT" -gt 0 ]; then
  SUMMARY="[IVY SESSION SUMMARY] $FILE_COUNT .ivy file(s) modified, $ISSUE_COUNT with lint issues:\\n${ISSUES}Run ivy_lint on flagged files before committing.${CLAIM_SECTION}${METRICS_SECTION}"
else
  SUMMARY="[IVY SESSION SUMMARY] $FILE_COUNT .ivy file(s) modified, all pass basic structural checks.${CLAIM_SECTION}${METRICS_SECTION}"
fi

# Output as additionalContext
ESCAPED=$(printf '%s' "$SUMMARY" | python3 -c "import json,sys; print(json.dumps(sys.stdin.read())[1:-1])")
printf '{"hookSpecificOutput":{"hookEventName":"Stop","additionalContext":"%s"}}' "$ESCAPED"

exit 0
