#!/usr/bin/env python3
"""Observability hook: PostToolUseFailure — logs tool execution failures.

Also increments the MCP health circuit breaker counter for ivy MCP tools.
"""

import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

_STATE_FILE = "/tmp/ivy-mcp-health-state.json"
_MAX_CONSECUTIVE_FAILURES = 3

try:
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

    # Increment circuit breaker for MCP ivy tools
    if "ivy" in tool_name.lower():
        try:
            state = {"consecutive_failures": 0, "last_update": time.time()}
            if os.path.exists(_STATE_FILE):
                with open(_STATE_FILE) as f:
                    state = json.load(f)
            state["consecutive_failures"] = state.get("consecutive_failures", 0) + 1
            state["last_update"] = time.time()
            with open(_STATE_FILE, "w") as f:
                json.dump(state, f)

            if state["consecutive_failures"] >= _MAX_CONSECUTIVE_FAILURES:
                output = {
                    "hookSpecificOutput": {
                        "hookEventName": "PostToolUseFailure",
                        "additionalContext": (
                            f"[ivy-health] WARNING: {state['consecutive_failures']} "
                            "consecutive MCP tool failures. The MCP server may be "
                            "crashed. Consider running /nct-health or stopping MCP "
                            "tool calls until resolved."
                        ),
                    }
                }
                print(json.dumps(output))
        except Exception:
            pass  # Circuit breaker update is best-effort

except Exception:
    pass
