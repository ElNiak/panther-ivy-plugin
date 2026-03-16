#!/usr/bin/env python3
"""Observability hook: Notification — logs notification events."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    from log_event import log_event, read_stdin

    data = read_stdin()
    session_id = data.get("session_id", "")
    message = data.get("message", "")

    log_event(
        "Notification",
        session_id,
        {
            "notification_type": data.get("notification_type", ""),
            "title": data.get("title", ""),
            "message_length": len(message) if isinstance(message, str) else 0,
        },
    )
except Exception:
    pass
