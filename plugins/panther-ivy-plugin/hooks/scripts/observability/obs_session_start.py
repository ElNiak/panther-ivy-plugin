#!/usr/bin/env python3
"""Observability hook: SessionStart — logs session initialization."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    from log_event import log_event, read_stdin

    data = read_stdin()
    session_id = data.get("session_id", "")
    log_event(
        "SessionStart",
        session_id,
        {
            "source": data.get("source", ""),
            "model": data.get("model", ""),
            "agent_type": data.get("agent_type", ""),
            "permission_mode": data.get("permission_mode", ""),
        },
    )
except Exception:
    pass
