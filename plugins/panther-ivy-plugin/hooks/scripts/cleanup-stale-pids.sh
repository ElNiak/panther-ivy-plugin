#!/usr/bin/env bash
# SessionStart hook: remove PID files for dead processes.
# Runs before server startup to ensure a clean slate.
# Cleans up leftovers from sessions that crashed without triggering SessionEnd.
# Always exits 0 — cleanup hooks must never fail the session.

PID_DIR="/tmp/ivy-lsp-pids"
[ -d "$PID_DIR" ] || exit 0

for pidfile in "$PID_DIR"/*.pid; do
    [ -f "$pidfile" ] || continue
    pid="$(cat "$pidfile" 2>/dev/null)" || continue
    if [ -n "$pid" ] && ! kill -0 "$pid" 2>/dev/null; then
        rm -f "$pidfile" 2>/dev/null || true
    fi
done

exit 0
