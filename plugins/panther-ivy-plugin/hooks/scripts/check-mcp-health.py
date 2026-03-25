#!/usr/bin/env python3
"""PreToolUse hook: circuit breaker for MCP tools.

Checks if the MCP sidecar is reachable by testing TCP connectivity to
the sidecar port. Maintains a failure counter in a state file.
After 3 consecutive failures, blocks the tool call with advice.
"""

import json
import socket
import time


_STATE_FILE = "/tmp/ivy-mcp-health-state.json"
_MAX_CONSECUTIVE_FAILURES = 3
_STATE_TTL = 300  # Reset state after 5 minutes of no activity


def _read_state() -> dict:
    """Read the health state file, returning defaults if missing/stale."""
    try:
        with open(_STATE_FILE) as f:
            state = json.load(f)
        # Reset if stale
        if time.time() - state.get("last_update", 0) > _STATE_TTL:
            return {"consecutive_failures": 0, "last_update": time.time()}
        return state
    except (OSError, json.JSONDecodeError, KeyError):
        return {"consecutive_failures": 0, "last_update": time.time()}


def _write_state(state: dict) -> None:
    """Write the health state file."""
    state["last_update"] = time.time()
    try:
        with open(_STATE_FILE, "w") as f:
            json.dump(state, f)
    except OSError:
        pass


def _check_sidecar_alive() -> bool:
    """Test if the MCP sidecar port is reachable (with retry).

    Retries up to 3 times with 200ms delay to handle the startup race
    where the port file exists but uvicorn hasn't bound yet.
    """
    import glob
    port_files = glob.glob("/tmp/ivy-mcp-*.port")
    if not port_files:
        return False
    try:
        with open(port_files[0]) as f:
            port = int(f.read().strip())
    except (OSError, ValueError):
        return False
    # TCP connect with retry
    # 2 retries × 1.5s socket timeout = 3s max, within the 5s hook timeout
    for attempt in range(2):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1.5)
            result = sock.connect_ex(("127.0.0.1", port))
            sock.close()
            if result == 0:
                return True
        except OSError:
            pass
        if attempt < 1:
            time.sleep(0.2)
    return False


def main():
    state = _read_state()

    if _check_sidecar_alive():
        # Reset failure counter on success
        if state["consecutive_failures"] > 0:
            state["consecutive_failures"] = 0
            _write_state(state)
        return  # Allow tool call

    # Sidecar unreachable — increment failure counter
    state["consecutive_failures"] = state.get("consecutive_failures", 0) + 1
    _write_state(state)

    if state["consecutive_failures"] >= _MAX_CONSECUTIVE_FAILURES:
        # Block the tool call via permissionDecision (current API)
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": (
                    f"MCP server appears crashed ({state['consecutive_failures']} "
                    "consecutive failures). Run /nct-health to diagnose, or restart "
                    "the session to recover."
                ),
            }
        }
        print(json.dumps(output))
    else:
        # Warn but allow
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "additionalContext": (
                    f"[ivy-health] MCP sidecar connectivity check failed "
                    f"({state['consecutive_failures']}/{_MAX_CONSECUTIVE_FAILURES}). "
                    "Tool may fail."
                ),
            }
        }
        print(json.dumps(output))


if __name__ == "__main__":
    main()
