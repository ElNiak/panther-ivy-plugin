#!/usr/bin/env bash
# SessionStart hook: detect Ivy workspace and inject context for Claude.
#
# Outputs:
#   - JSON with hookSpecificOutput.additionalContext for Claude
#   - Writes IVY_WORKSPACE_ROOT to CLAUDE_ENV_FILE (if set)
set -euo pipefail

DETECTED_ROOT=""
DETECTED_TYPE=""

# 1. Check for PANTHER project structure
find_panther_ivy() {
    local dir="$1"
    local candidate="$dir/panther/plugins/services/testers/panther_ivy"
    if [ -d "$candidate/protocol-testing" ]; then
        echo "$candidate"
        return 0
    fi
    local check="$dir"
    local depth=0
    while [ "$check" != "/" ] && [ $depth -lt 10 ]; do
        candidate="$check/panther/plugins/services/testers/panther_ivy"
        if [ -d "$candidate/protocol-testing" ]; then
            echo "$candidate"
            return 0
        fi
        if [ -d "$check/protocol-testing" ] && [ -f "$check/panther_ivy.py" ]; then
            echo "$check"
            return 0
        fi
        check="$(dirname "$check")"
        depth=$((depth + 1))
    done
    return 1
}

panther_ivy_dir="$(find_panther_ivy "$PWD" 2>/dev/null)" || true

if [ -n "$panther_ivy_dir" ]; then
    DETECTED_ROOT="$panther_ivy_dir"
    DETECTED_TYPE="panther"
fi

# 2. Walk up from CWD for directories with .ivy files
if [ -z "$DETECTED_ROOT" ]; then
    check="$PWD"
    depth=0
    while [ "$check" != "/" ] && [ $depth -lt 8 ]; do
        ivy_count=$(find "$check" -maxdepth 2 -name "*.ivy" 2>/dev/null | head -5 | wc -l)
        if [ "$ivy_count" -ge 3 ]; then
            DETECTED_ROOT="$check"
            DETECTED_TYPE="standalone"
            break
        fi
        check="$(dirname "$check")"
        depth=$((depth + 1))
    done
fi

# 3. Fallback
if [ -z "$DETECTED_ROOT" ]; then
    DETECTED_ROOT="$PWD"
    DETECTED_TYPE="fallback"
fi

# Write env var for later Bash commands
if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
    echo "IVY_WORKSPACE_ROOT=$DETECTED_ROOT" >> "$CLAUDE_ENV_FILE"
fi

# Build context message for Claude
if [ "$DETECTED_TYPE" = "panther" ]; then
    context="[ivy-workspace] Detected PANTHER project at: $DETECTED_ROOT. Ivy models are in protocol-testing/. The ivy-tools MCP server and LSP are scoped to this directory."
elif [ "$DETECTED_TYPE" = "standalone" ]; then
    context="[ivy-workspace] Detected standalone Ivy project at: $DETECTED_ROOT."
else
    context="[ivy-workspace] No Ivy project detected. Using CWD as workspace: $DETECTED_ROOT."
fi

# Escape context for JSON safety (handle \ and " in paths)
context_escaped=$(printf '%s' "$context" | sed 's/\\/\\\\/g; s/"/\\"/g')

# Output hook result as JSON
cat <<EOF
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "$context_escaped"
  }
}
EOF
