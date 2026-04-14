#!/usr/bin/env python3
"""Observability event logger for panther-ivy-plugin hooks.

Writes structured JSON events to per-session JSONL log files.
Zero external dependencies — stdlib only (plus hook_utils).
"""

# Event schema v1 — aligned with ivy_lsp.observability.session.SessionEventLogger
# Fields: timestamp, session_id, channel, event_type, name, status, cwd
# Optional: duration_ms, call_id, payload

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from hook_utils import read_stdin, resolve_log_dir, resolve_session_id


def _maybe_rotate(
    filepath: Path,
    max_bytes: int = 5 * 1024 * 1024,  # 5 MB
    backup_count: int = 5,
) -> None:
    """Rotate filepath when it exceeds max_bytes (POSIX-atomic, lock-free).

    Safe with concurrent writers that use open/close per write (no cached
    file handles).  Worst-case race: one extra rotation cycle, zero data loss.
    """
    try:
        size = filepath.stat().st_size
    except OSError:
        return
    if size < max_bytes:
        return
    # Shift existing backups: .5 -> delete, .4 -> .5, ..., .1 -> .2
    for i in range(backup_count, 0, -1):
        src = filepath.parent / f"{filepath.name}.{i}"
        if i == backup_count:
            try:
                src.unlink()
            except OSError:
                pass
        else:
            dst = filepath.parent / f"{filepath.name}.{i + 1}"
            try:
                src.rename(dst)
            except OSError:
                pass
    # Rename current file to .1 — next append creates a fresh file
    try:
        filepath.rename(filepath.parent / f"{filepath.name}.1")
    except OSError:
        pass


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

        safe_session_id = resolve_session_id({"session_id": session_id} if session_id else None)
        log_dir = log_dir_override or Path(resolve_log_dir(safe_session_id))
        log_dir.mkdir(parents=True, exist_ok=True)

        event: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session_id": safe_session_id,
            "channel": channel,
            "event_type": event_type,
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
        _maybe_rotate(events_file)
        with open(events_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, default=str) + "\n")

        return events_file
    except (OSError, TypeError, ValueError):
        return None
    except Exception as exc:
        print(f"[ivy-obs] log_event: {type(exc).__name__}: {exc}", file=sys.stderr)
        return None


  # read_stdin re-exported from hook_utils for observe.py
