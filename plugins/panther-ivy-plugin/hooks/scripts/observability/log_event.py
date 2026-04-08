#!/usr/bin/env python3
"""Observability event logger for panther-ivy-plugin hooks.

Writes structured JSON events to per-session JSONL log files.
Zero external dependencies — stdlib only.
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

try:
    from ivy_lsp.infra.observability.session import resolve_session_id as _canonical_resolve
    from ivy_lsp.infra.observability.session import workspace_hash
except ImportError:
    # Fallback if ivy-lsp not importable
    import hashlib

    def workspace_hash(workspace_root: str) -> str:
        return hashlib.sha256(workspace_root.encode()).hexdigest()[:12]

    _canonical_resolve = None


def _resolve_log_dir(session_id: str) -> Path:
    """Determine the log directory for a session.

    Priority:
      1. $IVY_OBSERVABILITY_DIR/sessions/<session_id>/
      2. $IVY_WORKSPACE_ROOT/.observability/sessions/<session_id>/
      3. /tmp/ivy-observability/sessions/<session_id>/
    """
    explicit = os.environ.get("IVY_OBSERVABILITY_DIR", "").strip()
    if explicit:
        return Path(explicit) / "sessions" / session_id

    workspace = os.environ.get("IVY_WORKSPACE_ROOT", "").strip()
    if workspace:
        return Path(workspace) / ".observability" / "sessions" / session_id

    return Path("/tmp/ivy-observability") / "sessions" / session_id


def _resolve_session_id(raw_session_id: str) -> str:
    """Resolve session ID — delegates to ivy-lsp canonical resolver with fallback.

    When ivy-lsp is importable the full priority chain is used:
      hook_payload > CLAUDE_SESSION_ID > CLAUDE_CODE_SESSION_ID >
      IVY_SESSION_ID > session file > "unknown"

    Fallback (ivy-lsp unavailable):
      IVY_SESSION_ID > CLAUDE_SESSION_ID > CLAUDE_CODE_SESSION_ID >
      session file > raw_session_id > "unknown"
    """
    if _canonical_resolve is not None:
        return _canonical_resolve({"session_id": raw_session_id} if raw_session_id else None)
    # Inline fallback matching ivy-lsp priority
    for var in ("IVY_SESSION_ID", "CLAUDE_SESSION_ID", "CLAUDE_CODE_SESSION_ID"):
        from_env = os.environ.get(var, "").strip()
        if from_env:
            return from_env
    ws_root = os.environ.get("IVY_WORKSPACE_ROOT", "").strip() or os.getcwd()
    ws_hash = workspace_hash(ws_root)
    session_file = Path("/tmp") / f"ivy-session-{ws_hash}.id"
    try:
        value = session_file.read_text().strip()
        if value:
            return value
    except OSError:
        pass
    return (raw_session_id or "unknown").strip() or "unknown"


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

        safe_session_id = _resolve_session_id(session_id)
        log_dir = log_dir_override or _resolve_log_dir(safe_session_id)
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


def read_stdin() -> dict[str, Any]:
    """Read and parse JSON from stdin. Returns empty dict on failure."""
    try:
        data = json.load(sys.stdin)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError, TypeError):
        return {}
