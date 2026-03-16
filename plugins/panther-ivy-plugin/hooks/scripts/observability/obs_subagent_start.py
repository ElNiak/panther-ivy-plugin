#!/usr/bin/env python3
"""Observability hook: SubagentStart — logs subagent spawning."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    from log_event import log_event, read_stdin

    data = read_stdin()
    session_id = data.get("session_id", "")

    log_event(
        "SubagentStart",
        session_id,
        {
            "agent_id": data.get("agent_id", ""),
            "agent_type": data.get("agent_type", ""),
        },
    )
except Exception:
    pass
