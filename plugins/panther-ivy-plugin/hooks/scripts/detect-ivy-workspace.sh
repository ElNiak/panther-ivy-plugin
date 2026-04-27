#!/usr/bin/env bash
# SessionStart hook: detect Ivy workspace and inject context for Claude.
#
# Uses the unified Python detection module (ivy_lsp.workspace_context) when
# available, falling back to the bash-based detection in workspace-common.sh.
#
# Outputs:
#   - JSON with hookSpecificOutput.additionalContext for Claude
#   - Writes IVY_WORKSPACE_ROOT to CLAUDE_ENV_FILE (if set)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGIN_SCRIPTS_DIR="$SCRIPT_DIR/../../scripts"
# shellcheck source=../../scripts/workspace-common.sh
source "$PLUGIN_SCRIPTS_DIR/workspace-common.sh"

# --- Detection: try Python module first, fall back to bash ---
DETECT_JSON=""
DETECTED_ROOT=""
DETECTED_TYPE=""
RESOLVED_SESSION_ID=""

# Extract canonical Claude session id from hook JSON input when available.
# SessionStart hooks provide a JSON payload on stdin with "session_id".
HOOK_INPUT="$(cat 2>/dev/null || true)"
if [ -n "$HOOK_INPUT" ]; then
    RESOLVED_SESSION_ID=$(printf '%s' "$HOOK_INPUT" | python3 -c "import json,sys; print((json.load(sys.stdin).get('session_id') or '').strip())" 2>/dev/null) || true
fi
if [ -z "$RESOLVED_SESSION_ID" ]; then
    RESOLVED_SESSION_ID="${CLAUDE_SESSION_ID:-${CLAUDE_CODE_SESSION_ID:-${IVY_SESSION_ID:-}}}"
fi

# Apply date prefix for chronologically sortable session directories
if [ -n "$RESOLVED_SESSION_ID" ]; then
    _SESSION_DATE="$(date +%Y-%m-%dT%H%M)"
    RESOLVED_SESSION_ID="${_SESSION_DATE}-${RESOLVED_SESSION_ID}"
fi

# Resolve ivy-lsp source so we can run python3 -m ivy_lsp detect
resolve_ivy_lsp_source
if [ -n "${IVY_LSP_SRC:-}" ]; then
    DETECT_JSON=$(PYTHONPATH="$IVY_LSP_SRC" python3 -m ivy_lsp detect "$PWD" 2>/dev/null) || true
fi

if [ -n "$DETECT_JSON" ]; then
    DETECTED_ROOT=$(echo "$DETECT_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin).get('workspace_root',''))" 2>/dev/null) || true
    DETECTED_TYPE=$(echo "$DETECT_JSON" | python3 -c "import sys,json; print(json.load(sys.stdin).get('project_type','fallback'))" 2>/dev/null) || true
fi

# Fallback to bash detection if Python detection failed
if [ -z "$DETECTED_ROOT" ]; then
    detect_ivy_workspace
fi

# Write env var for later Bash commands
if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
    printf 'IVY_WORKSPACE_ROOT="%s"\n' "$DETECTED_ROOT" >> "$CLAUDE_ENV_FILE"
    # Propagate log symlink paths so downstream hooks find the right logs
    printf 'IVY_LSP_LOG_PATH="%s"\n' "${IVY_LSP_LOG_DIR:-/tmp}/ivy-lsp-lsp-latest.log" >> "$CLAUDE_ENV_FILE"
    printf 'IVY_MCP_LOG_PATH="%s"\n' "${IVY_LSP_LOG_DIR:-/tmp}/ivy-mcp-latest.log" >> "$CLAUDE_ENV_FILE"
    printf 'IVY_SESSION_ID="%s"\n' "$RESOLVED_SESSION_ID" >> "$CLAUDE_ENV_FILE"
    printf 'IVY_MCP_PID_FILE="/tmp/ivy-mcp-%s.pid"\n' "$$" >> "$CLAUDE_ENV_FILE"
fi

# Persist session id per workspace so launchers can recover it even if
# CLAUDE_ENV_FILE variables are not present in spawned server environments.
# Write session files for BOTH the detected root AND the panther_ivy
# submodule path (if different), because the MCP server launcher hashes
# the panther_ivy path while this hook hashes the project root.
if [ -n "$RESOLVED_SESSION_ID" ]; then
    WS_HASH="$(printf '%s' "$DETECTED_ROOT" | shasum -a 256 | cut -c1-12)"
    printf '%s\n' "$RESOLVED_SESSION_ID" > "/tmp/ivy-session-${WS_HASH}.id" 2>/dev/null || true

    # Also write for the panther_ivy submodule path (MCP server's workspace root)
    _piv_dir="$(find_panther_ivy "$PWD" 2>/dev/null)" || true
    if [ -n "$_piv_dir" ] && [ "$_piv_dir" != "$DETECTED_ROOT" ]; then
        PIV_HASH="$(printf '%s' "$_piv_dir" | shasum -a 256 | cut -c1-12)"
        printf '%s\n' "$RESOLVED_SESSION_ID" > "/tmp/ivy-session-${PIV_HASH}.id" 2>/dev/null || true
    fi
fi

# Prune sessions older than 7 days
find "${IVY_WORKSPACE_ROOT:-${DETECTED_ROOT}}/.observability/sessions" -maxdepth 1 -type d -mtime +7 -exec rm -rf {} + 2>/dev/null || true

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

# --- Active workspace restore ---
WORKSPACE_RESTORE_MSG=""
STATE_FILE="${DETECTED_ROOT}/.ivy-workspace-state.json"
if [ -f "$STATE_FILE" ]; then
    read -r ACTIVE_GROUP SET_BY <<< "$(python3 -c "
import json, sys
try:
    d = json.load(open(sys.argv[1]))
    print(d.get('active_group', ''), d.get('set_by', ''))
except: print(' ')
" "$STATE_FILE" 2>/dev/null)"

    if [ -n "$ACTIVE_GROUP" ] && [ "$SET_BY" = "explicit" ]; then
        if [ -n "${CLAUDE_ENV_FILE:-}" ]; then
            echo "IVY_ACTIVE_WORKSPACE=$ACTIVE_GROUP" >> "$CLAUDE_ENV_FILE"
        fi
        WORKSPACE_RESTORE_MSG="Active workspace restored: $ACTIVE_GROUP (set by: $SET_BY). Use /set-workspace to change or /clear-workspace to remove restrictions."
    fi
fi

# Build context message for Claude
if [ "$DETECTED_TYPE" = "panther" ]; then
    context="[ivy-workspace] Detected PANTHER project at: $DETECTED_ROOT. Ivy models are in protocol-testing/. The ivy-tools MCP server and LSP are scoped to this directory. MCP: ${MCP_STATUS}${MODEL_INFO}."
elif [ "$DETECTED_TYPE" = "standalone" ]; then
    context="[ivy-workspace] Detected standalone Ivy project at: $DETECTED_ROOT. MCP: ${MCP_STATUS}."
else
    context="[ivy-workspace] No Ivy project detected. Using CWD as workspace: $DETECTED_ROOT."
fi

# Append workspace status to context
if [ -n "$WORKSPACE_RESTORE_MSG" ]; then
    context="$context $WORKSPACE_RESTORE_MSG"
else
    context="$context No active workspace set. Use /set-workspace <protocol> to restrict edits. Available: quic, apt, apt_quic, minip, bgp, coap, scaffolds"
fi

# --- Workflow suggestion based on workspace state ---
WORKFLOW_SUGGESTION=""
if [ "$DETECTED_TYPE" = "panther" ] && [ -d "$DETECTED_ROOT/protocol-testing" ]; then
    # Check for active build-state across protocol directories
    BUILD_PROTO=""
    BUILD_PHASE=""
    for proto_dir in "$DETECTED_ROOT"/protocol-testing/*/; do
        bs_file="$proto_dir.panther-ivy/build-state.yaml"
        if [ -f "$bs_file" ]; then
            BUILD_PROTO="$(basename "$proto_dir")"
            BUILD_PHASE=$(python3 -c "
import sys
try:
    import yaml; d = yaml.safe_load(open(sys.argv[1])); print(d.get('phase', 'unknown'))
except: print('unknown')
" "$bs_file" 2>/dev/null) || BUILD_PHASE="unknown"
            break
        fi
    done

    # Check for recent .ivy changes (last 4 hours)
    RECENT_IVY=""
    if command -v git >/dev/null 2>&1; then
        RECENT_IVY=$(cd "$DETECTED_ROOT" && git log --oneline -1 --since="4 hours ago" -- '*.ivy' 2>/dev/null) || true
    fi

    # Build suggestion by priority
    if [ -n "$BUILD_PROTO" ]; then
        WORKFLOW_SUGGESTION="[WORKFLOW-SUGGESTION] Build-state found for $BUILD_PROTO (phase: $BUILD_PHASE). Resume with Skill(skill=\"panther-ivy-plugin:workflow-build\"). Or invoke a different workflow if the user's intent differs."
    elif [ -n "$RECENT_IVY" ]; then
        WORKFLOW_SUGGESTION="[WORKFLOW-SUGGESTION] Recent .ivy changes detected. Consider Skill(skill=\"panther-ivy-plugin:workflow-verify\") to validate changes, or match to the user's stated intent."
    elif [ "$MCP_STATUS" != "ready" ]; then
        WORKFLOW_SUGGESTION="[WORKFLOW-SUGGESTION] MCP server not ready ($MCP_STATUS). If Ivy tools are needed, invoke Skill(skill=\"panther-ivy-plugin:workflow-triage\") first."
    else
        WORKFLOW_SUGGESTION="[WORKFLOW-SUGGESTION] Ivy workspace active. Available workflow skills: verify (test/debug), build (create/extend model), review (coverage/quality), triage (fix tools), navigate (guided routing). Invoke the one matching the user's intent."
    fi
fi

# Append workflow suggestion to context
if [ -n "$WORKFLOW_SUGGESTION" ]; then
    context="$context $WORKFLOW_SUGGESTION"
fi

# --- Seed the statusline cache for this workspace (one python spawn) ---
if [ -n "$DETECTED_ROOT" ] && [ "$DETECTED_TYPE" = "panther" ]; then
    _MCP_CACHE_STATUS="unknown"
    case "$MCP_STATUS" in
        ready) _MCP_CACHE_STATUS="up" ;;
        starting) _MCP_CACHE_STATUS="starting" ;;
        "not started") _MCP_CACHE_STATUS="down" ;;
    esac
    _SECTIONS_JSON=$(python3 -c "
import json, sys
print(json.dumps({
    'workspace': {'root': sys.argv[1], 'protocol': sys.argv[2], 'detected_at': sys.argv[3]},
    'mcp': {'status': sys.argv[4]},
}))
" "$DETECTED_ROOT" "${ACTIVE_GROUP:-}" "$(date -u +%FT%TZ)" "$_MCP_CACHE_STATUS" 2>/dev/null) || _SECTIONS_JSON=""
    if [ -n "$_SECTIONS_JSON" ]; then
        python3 "$SCRIPT_DIR/statusline_cache.py" --workspace "$DETECTED_ROOT" \
            --sections "$_SECTIONS_JSON" 2>/dev/null || true
    fi
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
