#!/usr/bin/env python3
"""PreToolUse hook: circuit breaker for MCP tools.

Uses a two-tier check to determine if the MCP server is reachable:
1. PID check (primary): validates the MCP process is alive via PID files.
2. TCP sidecar check (fallback): only when no PID files exist, tests TCP
   connectivity to the sidecar HTTP port.

Maintains a failure counter in a state file.  After 3 consecutive
definitive failures, blocks the tool call with advice.
"""

import fcntl
import glob
import json
import os
import socket
import subprocess
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from hook_utils import get_mcp_health_state_path, emit_hook_output, MAX_CONSECUTIVE_MCP_FAILURES

_MAX_CONSECUTIVE_FAILURES = MAX_CONSECUTIVE_MCP_FAILURES
_STATE_TTL = 300  # Reset state after 5 minutes of no activity
_STALE_PORT_AGE = 120  # Port file older than 2 min with no TCP → stale
_PID_DIR = "/tmp/ivy-lsp-pids"


def _read_state() -> dict:
    """Read the health state file, returning defaults if missing/stale."""
    path = get_mcp_health_state_path()
    try:
        with open(path) as f:
            fcntl.flock(f, fcntl.LOCK_SH)
            try:
                state = json.load(f)
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)
        if time.time() - state.get("last_update", 0) > _STATE_TTL:
            return {"consecutive_failures": 0, "last_update": time.time()}
        return state
    except (OSError, json.JSONDecodeError, KeyError):
        return {"consecutive_failures": 0, "last_update": time.time()}


def _write_state(state: dict) -> None:
    """Write the health state file."""
    path = get_mcp_health_state_path()
    state["last_update"] = time.time()
    try:
        with open(path, "w") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            try:
                json.dump(state, f)
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)
    except OSError:
        pass


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
    state = _read_state()

    # --- Tier 1: PID check (fast, no network) ---
    pid_result = _check_pid_alive()
    if pid_result is True:
        if state["consecutive_failures"] > 0:
            state["consecutive_failures"] = 0
            _write_state(state)
        return  # Allow

    if pid_result is False:
        # MCP process is dead — definitive failure
        state["consecutive_failures"] = state.get("consecutive_failures", 0) + 1
        _write_state(state)
        _emit_result(state)
        return

    # --- Tier 2: TCP sidecar fallback (only when no PID files) ---
    tcp_result = _check_sidecar_alive()
    if tcp_result is True:
        if state["consecutive_failures"] > 0:
            state["consecutive_failures"] = 0
            _write_state(state)
        return  # Allow

    if tcp_result is False:
        # Fresh port file but sidecar not responding — definitive failure
        state["consecutive_failures"] = state.get("consecutive_failures", 0) + 1
        _write_state(state)
        _emit_result(state)
        return

    # tcp_result is None — no sidecar expected (stdio mode) or stale port cleaned
    # Allow the tool call; if the MCP server is truly down, Claude Code will
    # report the error directly on the tool result.
    if state["consecutive_failures"] > 0:
        state["consecutive_failures"] = 0
        _write_state(state)
    return


def _emit_result(state: dict) -> None:
    """Print the hook JSON output based on failure count."""
    failures = state["consecutive_failures"]
    if failures >= _MAX_CONSECUTIVE_FAILURES:
        emit_hook_output(
            "PreToolUse",
            deny_reason=(
                f"MCP server appears crashed ({failures} "
                "consecutive failures). Run /nct-health to diagnose, or restart "
                "the session to recover."
            ),
        )
    else:
        emit_hook_output(
            "PreToolUse",
            additional_context=(
                f"[ivy-health] MCP health check failed "
                f"({failures}/{_MAX_CONSECUTIVE_FAILURES}). "
                "Tool may fail."
            ),
        )


if __name__ == "__main__":
    main()
