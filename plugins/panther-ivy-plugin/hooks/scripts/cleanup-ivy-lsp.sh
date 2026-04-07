#!/usr/bin/env bash
# SessionEnd hook: kill all ivy_lsp processes tracked via PID files
# and clean up stale sidecar port files.
# Always exits 0 — cleanup hooks must never fail the session.

PID_DIR="/tmp/ivy-lsp-pids"

if [ -d "$PID_DIR" ]; then
    for pidfile in "$PID_DIR"/*.pid; do
        [ -f "$pidfile" ] || continue
        pid="$(cat "$pidfile" 2>/dev/null)" || continue
        if [ -n "$pid" ] && ps -p "$pid" > /dev/null 2>&1; then
            kill -TERM "$pid" 2>/dev/null || true
        fi
        rm -f "$pidfile" 2>/dev/null || true
    done
fi

# Clean up sidecar port files (stale after session ends)
for portfile in /tmp/ivy-mcp-*.port; do
    [ -f "$portfile" ] || continue
    rm -f "$portfile" 2>/dev/null || true
done

# Clean up health state file
rm -f /tmp/ivy-mcp-health-state.json 2>/dev/null || true

exit 0
