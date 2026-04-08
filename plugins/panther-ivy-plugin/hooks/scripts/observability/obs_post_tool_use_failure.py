#!/usr/bin/env python3
"""Observability hook: PostToolUseFailure — logs tool execution failures.

Also increments the MCP health circuit breaker counter for ivy MCP tools.
"""

import fcntl
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))
from hook_utils import get_mcp_health_state_path, emit_hook_output, MAX_CONSECUTIVE_MCP_FAILURES


def main():
    from log_event import log_event, read_stdin

    data = read_stdin()
    session_id = data.get("session_id", "")
    error = data.get("error", "")
    tool_name = data.get("tool_name", "")

    log_event(
        "PostToolUseFailure",
        session_id,
        {
            "tool_name": tool_name,
            "tool_use_id": data.get("tool_use_id", ""),
            "error": str(error)[:500],
            "is_interrupt": data.get("is_interrupt", False),
        },
    )

    if "ivy" not in tool_name.lower():
        return

    try:
        state_path = get_mcp_health_state_path()
        state = {"consecutive_failures": 0, "last_update": time.time()}
        if os.path.exists(state_path):
            with open(state_path) as f:
                fcntl.flock(f, fcntl.LOCK_SH)
                try:
                    state = json.load(f)
                finally:
                    fcntl.flock(f, fcntl.LOCK_UN)
        state["consecutive_failures"] = state.get("consecutive_failures", 0) + 1
        state["last_update"] = time.time()
        with open(state_path, "w") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            try:
                json.dump(state, f)
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)

        if state["consecutive_failures"] >= MAX_CONSECUTIVE_MCP_FAILURES:
            emit_hook_output(
                "PostToolUseFailure",
                additional_context=(
                    f"[ivy-health] WARNING: {state['consecutive_failures']} "
                    "consecutive MCP tool failures. The MCP server may be "
                    "crashed. Consider running /nct-health or stopping MCP "
                    "tool calls until resolved."
                ),
            )
    except Exception:
        pass


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
