#!/usr/bin/env python3
"""Observability hook: PermissionRequest — logs permission request events."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    from log_event import log_event, read_stdin

    data = read_stdin()
    session_id = data.get("session_id", "")
    suggestions = data.get("permission_suggestions", [])

    log_event(
        "PermissionRequest",
        session_id,
        {
            "tool_name": data.get("tool_name", ""),
            "suggestion_count": len(suggestions) if isinstance(suggestions, list) else 0,
        },
    )
except Exception:
    pass
