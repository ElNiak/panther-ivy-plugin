#!/usr/bin/env python3
"""Observability hook: PostToolUseFailure — logs tool execution failures."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    from log_event import log_event, read_stdin

    data = read_stdin()
    session_id = data.get("session_id", "")
    error = data.get("error", "")

    log_event(
        "PostToolUseFailure",
        session_id,
        {
            "tool_name": data.get("tool_name", ""),
            "tool_use_id": data.get("tool_use_id", ""),
            "error": str(error)[:500],
            "is_interrupt": data.get("is_interrupt", False),
        },
    )
except Exception:
    pass
