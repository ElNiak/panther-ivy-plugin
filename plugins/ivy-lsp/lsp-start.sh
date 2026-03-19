#!/usr/bin/env bash
# Launch Ivy LSP, preferring local source when available.
# Priority: IVY_LSP_DEV_ROOT env var > local submodule > GitHub remote
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMMON="$SCRIPT_DIR/../panther-ivy-plugin/scripts/workspace-common.sh"

_IVY_LOG_DIR="${IVY_LSP_LOG_DIR:-/tmp}"
_IVY_LOG_TS="$(date +%Y-%m-%dT%H%M%S)"
LOG_FILE="${IVY_LSP_LOG_FILE:-${_IVY_LOG_DIR}/ivy-lsp-${_IVY_LOG_TS}-$$.log}"
ln -sfn "$LOG_FILE" "${_IVY_LOG_DIR}/ivy-lsp-latest.log"
ln -sfn "$LOG_FILE" "${_IVY_LOG_DIR}/ivy-lsp-lsp-latest.log"
log() { echo "[ivy-lsp] $*" >>"$LOG_FILE"; }

if [ -f "$COMMON" ]; then
    source "$COMMON"
    detect_ivy_workspace
    resolve_ivy_lsp_source
else
    log "workspace-common.sh not found at $COMMON, using remote"
    IVY_LSP_SRC=""
fi

REINSTALL_FLAG=""
[ "${IVY_LSP_FORCE_REINSTALL:-}" = "1" ] && REINSTALL_FLAG="--reinstall"

# --- PID tracking for cleanup ---
PID_DIR="/tmp/ivy-lsp-pids"
mkdir -p "$PID_DIR"

# Kill stale LSP servers from previous sessions
for pidfile in "$PID_DIR"/lsp-*.pid; do
    [ -f "$pidfile" ] || continue
    old_pid="$(cat "$pidfile" 2>/dev/null)" || continue
    [ "$old_pid" = "$$" ] && continue
    if kill -0 "$old_pid" 2>/dev/null; then
        log "Killing stale LSP server (PID=$old_pid)"
        kill -TERM "$old_pid" 2>/dev/null || true
    fi
    rm -f "$pidfile" 2>/dev/null || true
done

if [ -n "$IVY_LSP_SRC" ]; then
    log "Using LOCAL ivy-lsp: $IVY_LSP_SRC"
    # shellcheck disable=SC2086
    uvx $REINSTALL_FLAG --from "$IVY_LSP_SRC" --with z3-solver --with pyyaml ivy_lsp 2>>"$LOG_FILE" &
else
    log "Using REMOTE ivy-lsp: git+https://github.com/ElNiak/ivy-lsp"
    uvx --from "git+https://github.com/ElNiak/ivy-lsp" --with z3-solver --with pyyaml ivy_lsp 2>>"$LOG_FILE" &
fi
CHILD=$!
echo "$CHILD" > "$PID_DIR/lsp-$CHILD.pid"
trap 'rm -f "$PID_DIR/lsp-$CHILD.pid" 2>/dev/null' EXIT TERM INT
wait "$CHILD"
