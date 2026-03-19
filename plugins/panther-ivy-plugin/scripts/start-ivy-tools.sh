#!/usr/bin/env bash
# Auto-detect Ivy workspace scope before launching the MCP server.
#
# Detection priority:
#   1. PANTHER project: look for panther_ivy/protocol-testing/ relative to CWD
#   2. Walk up from CWD looking for directories with .ivy files
#   3. Fallback: use CWD
#
# Outputs:
#   - Sets IVY_LSP_INCLUDE_PATHS / IVY_LSP_EXCLUDE_PATHS env vars
#   - Launches ivy_lsp --mcp with --workspace pointing to detected root
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=workspace-common.sh
source "$SCRIPT_DIR/workspace-common.sh"

_IVY_LOG_DIR="${IVY_LSP_LOG_DIR:-/tmp}"
_IVY_LOG_TS="$(date +%Y-%m-%dT%H%M%S)"
LOG_FILE="${IVY_LSP_LOG_FILE:-${_IVY_LOG_DIR}/ivy-lsp-${_IVY_LOG_TS}-$$.log}"
ln -sfn "$LOG_FILE" "${_IVY_LOG_DIR}/ivy-mcp-latest.log"

log() {
    echo "[ivy-tools] $*" >>"$LOG_FILE"
}

# --- Detection ---

detect_ivy_workspace

if [ "$DETECTED_TYPE" = "panther" ]; then
    if [ -f "$DETECTED_ROOT/.ivyworkspace" ]; then
        log "Found .ivyworkspace — deferring path config to Python marker detection"
    else
        export IVY_LSP_INCLUDE_PATHS="${IVY_LSP_INCLUDE_PATHS:-protocol-testing}"
        export IVY_LSP_EXCLUDE_PATHS="${IVY_LSP_EXCLUDE_PATHS:-submodules,test,doc,examples,notebooks,patches,ivy}"
    fi
    log "Detected PANTHER project: workspace=$DETECTED_ROOT"
elif [ "$DETECTED_TYPE" = "standalone" ]; then
    log "Detected standalone ivy project: workspace=$DETECTED_ROOT"
else
    log "No ivy project detected, using CWD: workspace=$DETECTED_ROOT"
fi

log "Workspace: $DETECTED_ROOT (type=$DETECTED_TYPE)"
log "Include paths: ${IVY_LSP_INCLUDE_PATHS:-<none>}"
log "Exclude paths: ${IVY_LSP_EXCLUDE_PATHS:-<none>}"

# --- Resolve ivy-lsp source ---

resolve_ivy_lsp_source

# --- Launch ---

REINSTALL_FLAG=""
if [ "${IVY_LSP_FORCE_REINSTALL:-}" = "1" ]; then
    REINSTALL_FLAG="--reinstall"
fi

# --- PID tracking for cleanup ---
PID_DIR="/tmp/ivy-lsp-pids"
mkdir -p "$PID_DIR"

# Kill stale MCP servers from previous sessions
for pidfile in "$PID_DIR"/mcp-*.pid; do
    [ -f "$pidfile" ] || continue
    old_pid="$(cat "$pidfile" 2>/dev/null)" || continue
    [ "$old_pid" = "$$" ] && continue
    if kill -0 "$old_pid" 2>/dev/null; then
        log "Killing stale MCP server (PID=$old_pid)"
        kill -TERM "$old_pid" 2>/dev/null || true
    fi
    rm -f "$pidfile" 2>/dev/null || true
done

trap 'rm -f "$PID_DIR/mcp-$$.pid" 2>/dev/null' EXIT TERM INT

if [ -n "$IVY_LSP_SRC" ]; then
    log "Using local ivy-lsp source: $IVY_LSP_SRC"
    # shellcheck disable=SC2086
    uvx \
        $REINSTALL_FLAG \
        --from "${IVY_LSP_SRC}[mcp]" \
        ivy_lsp \
        --mcp \
        --workspace "$DETECTED_ROOT" \
        2>>"$LOG_FILE" &
else
    uvx \
        --from "git+https://github.com/ElNiak/ivy-lsp[mcp]" \
        ivy_lsp \
        --mcp \
        --workspace "$DETECTED_ROOT" \
        2>>"$LOG_FILE" &
fi
CHILD=$!
echo "$CHILD" > "$PID_DIR/mcp-$$.pid"
wait "$CHILD"
