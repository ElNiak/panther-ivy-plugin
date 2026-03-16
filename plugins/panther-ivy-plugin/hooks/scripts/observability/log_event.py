#!/usr/bin/env python3
"""Observability event logger for panther-ivy-plugin hooks.

Writes structured JSON events to per-session JSONL log files.
Zero external dependencies — stdlib only.
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


def _resolve_log_dir(session_id: str) -> Path:
    """Determine the log directory for a session.

    Priority:
      1. $IVY_OBSERVABILITY_DIR/sessions/<session_id>/
      2. $IVY_WORKSPACE_ROOT/.observability/sessions/<session_id>/
      3. /tmp/ivy-observability/sessions/<session_id>/
    """
    explicit = os.environ.get("IVY_OBSERVABILITY_DIR")
    if explicit:
        return Path(explicit) / "sessions" / session_id

    workspace = os.environ.get("IVY_WORKSPACE_ROOT")
    if workspace:
        return Path(workspace) / ".observability" / "sessions" / session_id

    return Path("/tmp/ivy-observability") / "sessions" / session_id


def log_event(
    event_type: str,
    session_id: str,
    payload: dict | None = None,
    *,
    log_dir_override: Path | None = None,
) -> Path | None:
    """Append a structured JSON event to the session's events.jsonl file.

    Args:
        event_type: Hook event name (e.g. "PreToolUse", "SessionStart").
        session_id: Claude Code session identifier.
        payload: Event-specific data dict.
        log_dir_override: Override log directory (for testing).

    Returns:
        Path to the events.jsonl file, or None if logging failed.

    Never raises — all errors are silently swallowed.
    """
    try:
        if os.environ.get("IVY_OBSERVABILITY_ENABLED", "1") == "0":
            return None

        log_dir = log_dir_override or _resolve_log_dir(session_id or "unknown")
        log_dir.mkdir(parents=True, exist_ok=True)

        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "session_id": session_id,
            "cwd": os.environ.get("PWD", os.getcwd()),
        }
        if payload:
            event["payload"] = payload

        events_file = log_dir / "events.jsonl"
        with open(events_file, "a") as f:
            f.write(json.dumps(event, default=str) + "\n")

        return events_file
    except Exception:
        return None


def read_stdin() -> dict:
    """Read and parse JSON from stdin. Returns empty dict on failure."""
    try:
        return json.load(sys.stdin)
    except Exception:
        return {}
