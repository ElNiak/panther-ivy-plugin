#!/usr/bin/env python3
"""Observability event logger for panther-ivy-plugin hooks.

Writes structured JSON events to per-session JSONL log files.
Zero external dependencies — stdlib only.
"""

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


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


def _resolve_session_id(raw_session_id: str) -> str:
    """Resolve session ID from session file, falling back to raw payload ID.

    The session file contains the date-prefixed ID written by SessionStart hook.
    Hook scripts are short-lived, so no caching is needed.
    """
    ws_root = os.environ.get("IVY_WORKSPACE_ROOT", "").strip()
    if ws_root:
        ws_hash = hashlib.sha256(ws_root.encode()).hexdigest()[:12]
        session_file = Path("/tmp") / f"ivy-session-{ws_hash}.id"
        try:
            value = session_file.read_text().strip()
            if value:
                return value
        except OSError:
            pass
    return (raw_session_id or "unknown").strip() or "unknown"


def log_event(
    event_type: str,
    session_id: str,
    payload: dict | None = None,
    *,
    log_dir_override: Path | None = None,
    channel: str = "hook",
    name: str | None = None,
    status: str = "ok",
    duration_ms: float | None = None,
    call_id: str | None = None,
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

        safe_session_id = _resolve_session_id(session_id)
        log_dir = log_dir_override or _resolve_log_dir(safe_session_id)
        log_dir.mkdir(parents=True, exist_ok=True)

        event: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "session_id": safe_session_id,
            "channel": channel,
            "name": name or event_type,
            "status": status,
            "cwd": os.environ.get("PWD", os.getcwd()),
        }
        if duration_ms is not None:
            event["duration_ms"] = round(duration_ms, 2)
        if call_id:
            event["call_id"] = call_id
        if payload:
            event["payload"] = payload

        events_file = log_dir / "events.jsonl"
        with open(events_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, default=str) + "\n")

        return events_file
    except Exception:
        return None


def read_stdin() -> dict[str, Any]:
    """Read and parse JSON from stdin. Returns empty dict on failure."""
    try:
        data = json.load(sys.stdin)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError, TypeError):
        return {}
