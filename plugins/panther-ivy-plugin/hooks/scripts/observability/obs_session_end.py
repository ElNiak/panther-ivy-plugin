#!/usr/bin/env python3
"""Observability hook: SessionEnd — logs session cleanup."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    from log_event import log_event, read_stdin

    data = read_stdin()
    session_id = data.get("session_id", "")

    log_event(
        "SessionEnd",
        session_id,
        {
            "reason": data.get("reason", ""),
        },
    )
except Exception:
    pass
