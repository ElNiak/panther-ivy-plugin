#!/usr/bin/env bash
# SessionStart hook: remove PID files for dead processes.
# Then sweep for orphaned ivy_lsp processes not tracked by any PID file.
# Always exits 0 — cleanup hooks must never fail the session.

PID_DIR="/tmp/ivy-lsp-pids"
[ -d "$PID_DIR" ] || { mkdir -p "$PID_DIR"; exit 0; }

# Phase 1: Remove dead PID files (existing logic)
for pidfile in "$PID_DIR"/*.pid; do
    [ -f "$pidfile" ] || continue
    pid="$(cat "$pidfile" 2>/dev/null)" || continue
    if [ -n "$pid" ] && ! ps -p "$pid" > /dev/null 2>&1; then
        rm -f "$pidfile" 2>/dev/null || true
    fi
done

# Phase 2: Kill orphaned ivy_lsp processes for THIS workspace.
# Source workspace-common.sh for detect_ivy_workspace().
# Path: hooks/scripts/ -> ../../ -> plugin root -> scripts/
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../scripts" && pwd)"
if [ -f "$SCRIPT_DIR/workspace-common.sh" ]; then
    # shellcheck source=../../scripts/workspace-common.sh
    source "$SCRIPT_DIR/workspace-common.sh"
    set +euo pipefail  # Restore: cleanup hooks must never fail
    detect_ivy_workspace 2>/dev/null || true
fi

# Fallback: try env vars if detect failed
DETECTED_ROOT="${DETECTED_ROOT:-${IVY_WORKSPACE_ROOT:-${IVY_LSP_WORKSPACE:-}}}"
[ -z "$DETECTED_ROOT" ] && exit 0

# Collect PIDs of tracked (live) processes
tracked_pids=""
for pidfile in "$PID_DIR"/*.pid; do
    [ -f "$pidfile" ] || continue
    pid="$(cat "$pidfile" 2>/dev/null)" || continue
    tracked_pids="$tracked_pids $pid"
done

# Find all ivy_lsp processes whose command line contains our workspace root.
# Use ps + grep instead of pgrep for broader compatibility.
for pid in $(ps -eo pid,args 2>/dev/null | grep "[i]vy_lsp" | grep "$DETECTED_ROOT" | awk '{print $1}'); do
    # Skip if this PID is tracked
    case " $tracked_pids " in
        *" $pid "*) continue ;;
    esac
    # Skip our own PID
    [ "$pid" = "$$" ] && continue
    # Kill orphan
    echo "[cleanup-stale-pids] Killing orphaned ivy_lsp process: PID=$pid" >&2
    kill -TERM "$pid" 2>/dev/null || true
done

exit 0
