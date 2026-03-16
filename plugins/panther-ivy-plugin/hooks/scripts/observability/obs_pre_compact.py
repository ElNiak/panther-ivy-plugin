#!/usr/bin/env python3
"""Observability hook: PreCompact — logs context compaction events."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    from log_event import log_event, read_stdin

    data = read_stdin()
    session_id = data.get("session_id", "")

    log_event(
        "PreCompact",
        session_id,
        {
            "trigger": data.get("trigger", ""),
            "has_custom_instructions": bool(data.get("custom_instructions")),
        },
    )
except Exception:
    pass
