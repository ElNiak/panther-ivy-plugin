#!/usr/bin/env bash
# SessionEnd hook: kill all ivy_lsp processes tracked via PID files.
# Always exits 0 — cleanup hooks must never fail the session.

PID_DIR="/tmp/ivy-lsp-pids"

if [ -d "$PID_DIR" ]; then
    for pidfile in "$PID_DIR"/*.pid; do
        [ -f "$pidfile" ] || continue
        pid="$(cat "$pidfile" 2>/dev/null)" || continue
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            kill -TERM "$pid" 2>/dev/null || true
        fi
        rm -f "$pidfile" 2>/dev/null || true
    done
fi

exit 0
