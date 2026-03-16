#!/usr/bin/env python3
"""Observability hook: Stop — logs when agent considers stopping."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    from log_event import log_event, read_stdin

    data = read_stdin()
    session_id = data.get("session_id", "")
    message = data.get("last_assistant_message", "")

    log_event(
        "Stop",
        session_id,
        {
            "stop_hook_active": data.get("stop_hook_active", False),
            "message_length": len(message) if isinstance(message, str) else 0,
        },
    )
except Exception:
    pass
