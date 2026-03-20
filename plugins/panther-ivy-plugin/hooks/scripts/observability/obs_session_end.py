#!/usr/bin/env python3
"""Observability hook: SessionEnd — logs session cleanup with tool usage summary."""

import collections
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    from log_event import log_event, read_stdin

    data = read_stdin()
    session_id = data.get("session_id", "")

    payload = {
        "reason": data.get("reason", ""),
    }

    # Read back session events to produce a tool usage summary
    obs_dir = os.environ.get("IVY_OBSERVABILITY_DIR", "/tmp/ivy-observability")
    events_file = Path(obs_dir) / "sessions" / session_id / "events.jsonl"
    if not events_file.exists():
        # Fallback: check workspace-relative path
        ws_root = os.environ.get("IVY_WORKSPACE_ROOT", "")
        if ws_root:
            alt = Path(ws_root) / ".observability" / "sessions" / session_id / "events.jsonl"
            if alt.exists():
                events_file = alt

    if events_file.exists():
        tool_counts = collections.Counter()
        try:
            for line in events_file.read_text().splitlines():
                try:
                    evt = json.loads(line)
                    if evt.get("event_type") == "PreToolUse":
                        tool_name = (evt.get("payload") or {}).get("tool_name", "?")
                        tool_counts[tool_name] += 1
                except (json.JSONDecodeError, TypeError):
                    continue
        except OSError:
            pass

        if tool_counts:
            payload["tool_summary"] = dict(tool_counts.most_common(10))
            payload["total_tool_calls"] = sum(tool_counts.values())

    log_event("SessionEnd", session_id, payload)
except Exception:
    pass
