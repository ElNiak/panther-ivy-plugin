#!/usr/bin/env python3
"""PreToolUse hook: circuit breaker for MCP tools.

Uses a two-tier check to determine if the MCP server is reachable:
1. PID check (primary): validates the MCP process is alive via PID files.
2. TCP sidecar check (fallback): only when no PID files exist, tests TCP
   connectivity to the sidecar HTTP port.

Maintains a failure counter in a state file.  After 3 consecutive
definitive failures, blocks the tool call with advice.

Also categorises recent MCP log errors (folded in from the former
`observability/check_lsp_log.py` hook) and surfaces them via the
top-level `systemMessage` field.
"""

import glob
import os
import socket
import subprocess
import sys
import time
from collections import deque
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from hook_utils import (
    MAX_CONSECUTIVE_MCP_FAILURES,
    emit_hook_output,
    read_mcp_health_state,
    write_mcp_health_state,
)
from statusline_cache import update_from_hook as _statusline_update

_STALE_PORT_AGE = 120  # Port file older than 2 min with no TCP → stale
_PID_DIR = "/tmp/ivy-lsp-pids"

_LOG_PATH = os.environ.get("IVY_MCP_LOG_PATH", "/tmp/ivy-mcp-latest.log")
_LOG_MAX_LINES = 50
_LOG_MAX_AGE_SECONDS = 60
_ERROR_PATTERNS = ("CRITICAL", "ERROR", "Traceback")
_CRASH_PATTERNS = ("Traceback", "CRITICAL", "FATAL", "segfault", "core dumped")
_TIMEOUT_PATTERNS = ("timed out", "timeout", "TimeoutError", "deadline exceeded")
_CONNECTION_PATTERNS = (
    "ConnectionRefused",
    "ConnectionReset",
    "BrokenPipe",
    "connection lost",
    "reconnect",
)


def _read_mcp_log_tail(n: int) -> list[str]:
    """Return up to ``n`` recent MCP-log lines if the log is fresh.

    Returns an empty list when the log file is missing, unreadable, or
    older than ``_LOG_MAX_AGE_SECONDS`` (no recent activity → no
    actionable signal).
    """
    if not os.path.isfile(_LOG_PATH):
        return []
    try:
        log_mtime = os.path.getmtime(_LOG_PATH)
    except OSError:
        return []
    if time.time() - log_mtime > _LOG_MAX_AGE_SECONDS:
        return []
    try:
        with open(_LOG_PATH, "r", errors="replace") as f:
            tail = deque(f, maxlen=n)
    except OSError:
        return []
    return [line.rstrip() for line in tail]


def _categorise_recent_errors(log_tail: list[str]) -> dict[str, int]:
    """Bucket recent error lines into crashes/timeouts/connection/other."""
    buckets = {"crashes": 0, "timeouts": 0, "connection": 0, "other": 0}
    for line in log_tail:
        if not any(pat in line for pat in _ERROR_PATTERNS):
            continue
        lower = line.lower()
        if any(p.lower() in lower for p in _CRASH_PATTERNS):
            buckets["crashes"] += 1
        elif any(p.lower() in lower for p in _TIMEOUT_PATTERNS):
            buckets["timeouts"] += 1
        elif any(p.lower() in lower for p in _CONNECTION_PATTERNS):
            buckets["connection"] += 1
        else:
            buckets["other"] += 1
    return buckets


def _build_health_summary(liveness_ok: bool) -> tuple[str, str | None]:
    """Compose the health summary line and (optional) remediation hint."""
    buckets = _categorise_recent_errors(_read_mcp_log_tail(_LOG_MAX_LINES))
    total = sum(buckets.values())
    if liveness_ok and total == 0:
        return "[ivy-health] OK", None
    summary = (
        f"[ivy-health] {total} recent errors "
        f"({buckets['crashes']} crashes / {buckets['timeouts']} timeouts / "
        f"{buckets['connection']} connection / {buckets['other']} other)"
    )
    hint = None
    if not liveness_ok:
        hint = (
            "MCP liveness check failed. If this persists, ask the user to run "
            "/mcp to reconnect the Ivy MCP server."
        )
    return summary, hint


def _check_pid_alive():
    """Check MCP process liveness via PID files.

    Returns:
        True  — at least one live MCP PID found.
        False — only dead PID(s) found (process crashed).
        None  — no PID files exist (inconclusive).
    """
    pid_files = glob.glob(os.path.join(_PID_DIR, "mcp-*.pid"))
    if not pid_files:
        return None

    found_any = False
    for pf in pid_files:
        try:
            with open(pf) as f:
                pid = int(f.read().strip())
        except (OSError, ValueError):
            continue
        found_any = True
        result = subprocess.run(["ps", "-p", str(pid)], capture_output=True)
        if result.returncode == 0:
            return True  # At least one live process
        else:
            try:
                os.unlink(pf)
            except OSError:
                pass
            continue  # Dead PID, cleaned up stale file

    return False if found_any else None


def _check_sidecar_alive():
    """TCP fallback: test if the MCP sidecar HTTP port is reachable.

    Returns:
        True  — sidecar port responds.
        False — port file is fresh but port is closed (sidecar crashed).
        None  — no port files, or port file is stale (stdio assumed).
    """
    port_files = glob.glob("/tmp/ivy-mcp-*.port")
    if not port_files:
        return None  # No sidecar expected → stdio mode

    port_file = port_files[0]
    try:
        with open(port_file) as f:
            port = int(f.read().strip())
    except (OSError, ValueError):
        return None

    # Check staleness: if port file is old and port is unreachable, it's stale
    try:
        file_age = time.time() - os.path.getmtime(port_file)
    except OSError:
        file_age = float("inf")

    # TCP connect (single attempt, short timeout to stay within hook budget)
    reachable = False
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1.5)
        result = sock.connect_ex(("127.0.0.1", port))
        sock.close()
        reachable = result == 0
    except OSError:
        pass

    if reachable:
        return True

    # Port not listening — stale or crashed?
    if file_age > _STALE_PORT_AGE:
        # Stale port file from a previous session — clean it up
        try:
            os.unlink(port_file)
        except OSError:
            pass
        return None  # Inconclusive, not a failure

    return False  # Fresh port file but port closed → sidecar crashed


def main():
    state = read_mcp_health_state()

    # --- Tier 1: PID check (fast, no network) ---
    pid_result = _check_pid_alive()
    if pid_result is True:
        if state["consecutive_failures"] > 0:
            state["consecutive_failures"] = 0
            write_mcp_health_state(state)
        _statusline_update("mcp", {"status": "up"})
        _emit_health(liveness_ok=True, state=state)
        return

    if pid_result is False:
        # MCP process is dead — definitive failure
        state["consecutive_failures"] = state.get("consecutive_failures", 0) + 1
        write_mcp_health_state(state)
        _statusline_update("mcp", {"status": "down", "last_error": "pid-check-failed"})
        _emit_health(liveness_ok=False, state=state)
        return

    # --- Tier 2: TCP sidecar fallback (only when no PID files) ---
    tcp_result = _check_sidecar_alive()
    if tcp_result is True:
        if state["consecutive_failures"] > 0:
            state["consecutive_failures"] = 0
            write_mcp_health_state(state)
        _statusline_update("mcp", {"status": "up"})
        _emit_health(liveness_ok=True, state=state)
        return

    if tcp_result is False:
        # Fresh port file but sidecar not responding — definitive failure
        state["consecutive_failures"] = state.get("consecutive_failures", 0) + 1
        write_mcp_health_state(state)
        _statusline_update("mcp", {"status": "down", "last_error": "tcp-unreachable"})
        _emit_health(liveness_ok=False, state=state)
        return

    # tcp_result is None — no sidecar expected (stdio mode) or stale port cleaned
    # Allow the tool call; if the MCP server is truly down, Claude Code will
    # report the error directly on the tool result.
    if state["consecutive_failures"] > 0:
        state["consecutive_failures"] = 0
        write_mcp_health_state(state)
    _statusline_update("mcp", {"status": "up"})
    _emit_health(liveness_ok=True, state=state)


def _emit_health(*, liveness_ok: bool, state: dict[str, Any]) -> None:
    """Emit the canonical hook envelope for the current health snapshot."""
    summary, hint = _build_health_summary(liveness_ok)
    failures = state.get("consecutive_failures", 0)

    if not liveness_ok and failures >= MAX_CONSECUTIVE_MCP_FAILURES:
        emit_hook_output(
            "PreToolUse",
            system_message=summary,
            deny_reason=(
                f"MCP server appears crashed ({failures} "
                "consecutive failures). Ask the user to run /mcp to "
                "reconnect the server. If that fails, run the triage "
                "workflow to diagnose."
            ),
        )
        return

    emit_hook_output(
        "PreToolUse",
        system_message=summary,
        additional_context=hint,
    )


if __name__ == "__main__":
    main()
