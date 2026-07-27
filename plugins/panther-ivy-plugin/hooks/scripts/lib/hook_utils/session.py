#!/usr/bin/env python3
"""Session-ID resolution, session activity, and MCP health state I/O."""

from __future__ import annotations

import fcntl
import json
import os
import subprocess
import time
from pathlib import Path

try:
    from ivy_lsp.infra.observability.session import resolve_session_id as _canonical_resolve
except ImportError:
    _canonical_resolve = None

_MCP_HEALTH_STATE_TTL = 300  # Reset the circuit breaker after 5 min of no activity.


def resolve_session_id(hook_input: dict | None = None) -> str:
    """Resolve Claude session ID using canonical priority chain.

    Priority: hook_payload (canonical or local) > CLAUDE_SESSION_ID /
    CLAUDE_CODE_SESSION_ID > IVY_SESSION_ID > /tmp/ivy-session-<ws_hash>.id
    file scoped to the panther_ivy workspace root > "unknown".

    Earlier revisions returned canonical's "unknown" verdict without
    trying the local fallback chain; the panther_ivy workspace path
    differs from os.getcwd() when the hook is spawned by the outer
    Claude Code worktree, so canonical's cwd-based file lookup misses
    a session-id file the SessionStart hook DID write at the panther_ivy
    workspace root. We therefore fall through on "unknown" and consult
    `get_workspace_root()` (which knows how to walk up to panther_ivy)
    before giving up.
    """
    if _canonical_resolve is not None:
        try:
            sid = _canonical_resolve(hook_payload=hook_input)
            if sid and sid != "unknown":
                return sid
        except Exception:
            pass

    if hook_input:
        payload_session = str(hook_input.get("session_id", "")).strip()
        if payload_session:
            return payload_session

    for var in ("IVY_SESSION_ID", "CLAUDE_SESSION_ID", "CLAUDE_CODE_SESSION_ID"):
        value = os.environ.get(var, "").strip()
        if value:
            return value

    try:
        from ivy_lsp.infra.observability.session import _read_session_file
        from .workspace import get_workspace_root
        ws_root = get_workspace_root()
        sid = _read_session_file(ws_root)
        if sid:
            return sid
    except (ImportError, OSError):
        # ImportError covers ivy-lsp not installed; OSError covers
        # `os.getcwd()` failure inside `get_workspace_root()` (cwd unlinked,
        # EACCES) and any unexpected I/O fall-through from `_read_session_file`.
        pass

    return "unknown"


def resolve_sessions_dir() -> str:
    """Return the sessions directory (parent of per-session log dirs).

    Uses the same 3-level fallback as ``resolve_log_dir``.
    """
    from .workspace import resolve_log_dir
    return os.path.dirname(resolve_log_dir("_"))


def get_mcp_health_state_path(hook_input: dict | None = None) -> str:
    """Get the path to the MCP health state file for the current session.

    Args:
        hook_input: Parsed hook stdin payload from the spawning Claude Code
            event. When provided, ``hook_input["session_id"]`` is the
            highest-priority source for the session id (matching canonical
            resolver order). Without it, callers fall back to env vars and
            the workspace-scoped session-id file, which is shared across
            concurrent Claude Code sessions on the same workspace and can
            therefore hold another session's id.
    """
    from .workspace import get_workspace_root
    ws_root = get_workspace_root()
    sid = resolve_session_id(hook_input)
    state_dir = os.path.join(ws_root, ".observability", "sessions", sid)
    os.makedirs(state_dir, exist_ok=True)
    return os.path.join(state_dir, "mcp-health-state.json")


def read_mcp_health_state(hook_input: dict | None = None) -> dict:
    """Read the MCP health state file under a shared fcntl lock.

    Returns a fresh defaults dict when the file is missing, unreadable,
    or when its ``last_update`` timestamp is older than the TTL (the
    circuit breaker auto-resets after a period of no activity). A file
    that exists but contains unparseable JSON is also treated as a miss
    and the caller's next write will overwrite it — the circuit breaker
    prefers self-healing over preserving a broken state across sessions.

    Args:
        hook_input: Threaded through to :func:`get_mcp_health_state_path`
            so the per-session path matches the spawning hook's session id
            even when env vars are unset and the shared session-id file
            holds another session's value.

    Returns:
        A ``{"consecutive_failures": int, "last_update": float}`` dict.
    """
    path = get_mcp_health_state_path(hook_input)
    try:
        with open(path) as f:
            fcntl.flock(f, fcntl.LOCK_SH)
            try:
                state = json.load(f)
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)
        if time.time() - state.get("last_update", 0) > _MCP_HEALTH_STATE_TTL:
            return {"consecutive_failures": 0, "last_update": time.time()}
        return state
    except (OSError, json.JSONDecodeError, KeyError):
        return {"consecutive_failures": 0, "last_update": time.time()}


def write_mcp_health_state(state: dict, hook_input: dict | None = None) -> None:
    """Write the MCP health state file under an exclusive fcntl lock.

    Always stamps ``last_update`` before writing so the TTL-based
    auto-reset remains correct. Silent on OSError — callers run this on
    the hook hot path and must not fail the session on I/O errors.

    Args:
        state: Mutable dict written as JSON. ``last_update`` is set
            before writing; any caller-provided value is overwritten.
        hook_input: Threaded through to :func:`get_mcp_health_state_path`
            so the per-session path matches the spawning hook's session id.
    """
    path = get_mcp_health_state_path(hook_input)
    state["last_update"] = time.time()
    try:
        with open(path, "w") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            try:
                json.dump(state, f)
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)
    except OSError:
        pass


def is_pid_alive(pid: int) -> bool:
    """Return True iff ``ps -p <pid>`` finds the process.

    Wrapped in a 2-second timeout so a hung ``ps`` cannot block a
    SessionStart hook past Claude Code's per-hook budget. ``OSError``
    and ``subprocess.TimeoutExpired`` both fall through to False —
    callers treat "cannot determine liveness" as "not alive".
    """
    try:
        return subprocess.run(
            ["ps", "-p", str(pid)],
            capture_output=True,
            timeout=2,
        ).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


def read_pid_file(path) -> int | None:
    """Read an integer PID from a file. Returns None on read or parse failure.

    Accepts ``pathlib.Path`` or ``str``.
    """
    try:
        text = Path(path).read_text().strip()
        return int(text) if text else None
    except (OSError, ValueError):
        return None


def file_contains(path, needle: str) -> bool:
    """True iff ``path`` is readable and contains ``needle`` (any line).

    The ``try``/``except OSError`` is the only existence gate (race-free) —
    a missing file raises ``FileNotFoundError`` which subclasses ``OSError``
    and is swallowed below, so a TOCTOU split between an ``is_file()`` check
    and ``open()`` cannot occur. Accepts ``pathlib.Path`` or ``str``.
    """
    try:
        with open(path, "r", errors="replace") as f:
            return any(needle in line for line in f)
    except OSError:
        return False


def _session_activity_path() -> Path:
    """Return the per-session activity flag path.

    Path: ``${TMPDIR or /tmp}/claude-ivy/session-activity-<sid>.flag``.
    When ``resolve_session_id()`` returns ``"unknown"``, the literal string
    ``unknown`` is used so back-to-back writes within a broken-session-id
    condition still cohere, but ``is_session_active()`` treats that path as
    absent (fail-closed).
    """
    tmpdir = os.environ.get("TMPDIR", "/tmp")
    sid = resolve_session_id()
    return Path(tmpdir) / "claude-ivy" / f"session-activity-{sid}.flag"


def mark_session_activity(signal: str) -> None:
    """Touch the per-session activity flag. Idempotent. Safe under parallel hooks.

    Args:
        signal: Human-readable string describing what triggered the activity
            mark (e.g. ``"skill:panther-ivy-plugin:ivy"``). Used only for the
            optional diagnostic log; not read by ``is_session_active()``.
    """
    import datetime
    flag = _session_activity_path()
    try:
        flag.parent.mkdir(parents=True, exist_ok=True)
        flag.touch(exist_ok=True)
        if os.environ.get("IVY_SESSION_ACTIVITY_LOG") == "1":
            log = flag.parent / f"signals-{flag.stem.removeprefix('session-activity-')}.log"
            entry = json.dumps({"ts": datetime.datetime.utcnow().isoformat(), "signal": signal})
            with open(log, "a") as f:
                f.write(entry + "\n")
    except OSError:
        pass


def is_session_active() -> bool:
    """Return True iff the per-session activity flag exists.

    Fail-closed: returns False when ``resolve_session_id()`` returns
    ``"unknown"`` so Stop hooks remain silent rather than producing
    false-positive journal writes on sessions where the session ID could
    not be resolved.
    """
    if resolve_session_id() == "unknown":
        return False
    return _session_activity_path().exists()
