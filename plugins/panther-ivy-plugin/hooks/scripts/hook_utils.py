#!/usr/bin/env python3
"""Shared utilities for panther-ivy-plugin hook scripts.

Centralizes session ID resolution, workspace detection, MCP health state
management, and JSON hook output formatting.
"""

# Defers PEP-604 union syntax evaluation so the module works under Python 3.9.
from __future__ import annotations

import fcntl
import json
import os
import sys
import time
from pathlib import Path
try:
    from ivy_lsp.infra.observability.session import resolve_session_id as _canonical_resolve
except ImportError:
    _canonical_resolve = None


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


def get_workspace_root() -> str:
    """Get workspace root from environment, with walk-up fallback."""
    ws_root = os.environ.get("IVY_WORKSPACE_ROOT", "").strip()
    if ws_root:
        return ws_root
    check = os.getcwd()
    for _ in range(10):
        candidate = os.path.join(check, "panther", "plugins", "services",
                                 "testers", "panther_ivy")
        if os.path.isdir(os.path.join(candidate, "protocol-testing")):
            return candidate
        parent = os.path.dirname(check)
        if parent == check:
            break
        check = parent
    return os.getcwd()


def resolve_workspace_state_path(detected_root: os.PathLike[str] | str) -> str | None:
    """Return the first existing .ivy-workspace-state.json across two candidate roots.

    The MCP ``ivy_workspace`` tool writes the state file at the
    panther_ivy submodule root (its LSP scope root), while SessionStart
    often resolves the session's detected workspace to the PANTHER
    project root one or more directories above. Callers that read
    workspace state cannot assume a single canonical location, so this
    helper centralises the two-root walk: every reader (SessionStart
    banner, mid-session change hook, future statusline poller)
    converges on the same resolution rule.

    Args:
        detected_root: The session's detected workspace root, typically
            the PANTHER project root or a standalone Ivy project. Path
            or str.

    Returns:
        Absolute path to the first existing state file, or ``None`` if
        neither candidate resolves.
    """
    detected = str(detected_root)
    panther_ivy = get_workspace_root()
    for candidate in (detected, panther_ivy):
        path = os.path.join(candidate, ".ivy-workspace-state.json")
        if os.path.isfile(path):
            return path
    return None


def read_active_workspace(state_path: str | None) -> str:
    """Read the active workspace name from the workspace-state JSON file.

    Centralised so every reader (notify-workspace-change.py, the
    PROJECT.md PostToolUse hook, the statusline segment) converges on
    the same parser. Returns the empty string when the file is missing,
    unparseable, or has no ``active_group`` set — callers that need to
    distinguish "no workspace" from "parse error" can do their own read.

    Args:
        state_path: Path returned by :func:`resolve_workspace_state_path`,
            or None when no candidate state file exists. Both inputs map
            to the empty string.

    Returns:
        The active workspace name, or ``""`` when no workspace is set.
    """
    if state_path is None:
        return ""
    try:
        data = json.loads(Path(state_path).read_text())
    except (OSError, json.JSONDecodeError):
        return ""
    if not isinstance(data, dict):
        return ""
    return str(data.get("active_group", "") or "").strip()


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
    ws_root = get_workspace_root()
    sid = resolve_session_id(hook_input)
    state_dir = os.path.join(ws_root, ".observability", "sessions", sid)
    os.makedirs(state_dir, exist_ok=True)
    return os.path.join(state_dir, "mcp-health-state.json")


MAX_CONSECUTIVE_MCP_FAILURES = 3

_MCP_HEALTH_STATE_TTL = 300  # Reset the circuit breaker after 5 min of no activity.


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


def read_stdin() -> dict:
    """Read and parse JSON from stdin. Returns empty dict on failure."""
    try:
        data = json.load(sys.stdin)
        return data if isinstance(data, dict) else {}
    except (OSError, EOFError, ValueError, TypeError):
        return {}


def is_pid_alive(pid: int) -> bool:
    """Return True iff ``ps -p <pid>`` finds the process.

    Wrapped in a 2-second timeout so a hung ``ps`` cannot block a
    SessionStart hook past Claude Code's per-hook budget. ``OSError``
    and ``subprocess.TimeoutExpired`` both fall through to False —
    callers treat "cannot determine liveness" as "not alive".
    """
    import subprocess

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
        from pathlib import Path
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


VALID_EVENT_NAMES = frozenset({
    "PreToolUse",
    "PostToolUse",
    "PostToolBatch",
    "PostToolUseFailure",
    "UserPromptSubmit",
    "SessionStart",
    "SessionEnd",
    "Stop",
    "SubagentStart",
    "SubagentStop",
    "Notification",
    "PreCompact",
    "PermissionRequest",
})


_EVENTS_WITH_HOOK_SPECIFIC_OUTPUT = frozenset({
    "PreToolUse",
    "PostToolUse",
    "PostToolBatch",
    "PostToolUseFailure",
    "UserPromptSubmit",
    "SessionStart",
    "SessionEnd",
    "SubagentStart",  # accepts additionalContext empirically (~2KB cap); see feedback_subagent_start_semantics
})


def emit_hook_output(
    event_name: str,
    *,
    system_message: str,
    additional_context: str | None = None,
    deny_reason: str | None = None,
) -> None:
    """Print a Claude Code advanced-protocol hook JSON decision to stdout.

    Two envelope shapes per the runtime schema. For events in
    ``_EVENTS_WITH_HOOK_SPECIFIC_OUTPUT`` the helper emits::

        {"hookSpecificOutput": {"hookEventName": ..., ...}, "systemMessage": ...}

    For all other events (``Stop``, ``SubagentStop``, ``Notification``,
    ``PreCompact``) the runtime rejects ``hookSpecificOutput`` entirely;
    the helper emits only top-level fields. ``additional_context`` has no
    top-level home in that schema and is silently dropped — callers
    targeting those events should pass ``system_message`` only.

    The caller MUST return via a normal exit 0 after calling this function.
    Per the Claude Code hooks protocol (https://code.claude.com/docs/en/hooks),
    JSON output is only processed on exit 0; ``sys.exit(2)`` would cause the
    JSON payload to be ignored entirely and fall back to the legacy
    block-on-exit-2 contract, which discards ``deny_reason`` and
    ``additional_context``.

    For PreToolUse hooks, passing ``deny_reason`` sets
    ``permissionDecision: "deny"`` in the envelope and blocks the tool call.
    This is the authoritative blocking mechanism; do not combine it with
    ``sys.exit(2)``.

    Args:
        event_name: Hook event name, e.g. ``"PreToolUse"`` / ``"PostToolUse"``
            / ``"Stop"``. Determines which envelope shape is emitted.
        system_message: REQUIRED top-level ``systemMessage`` shown to the user
            in the Claude Code UI out-of-band from the model. Every hook
            surface must surface what it did, even on no-op paths
            (e.g. ``"[ivy-workspace-scope] no-op (non-.ivy file)"``). Pass
            ``""`` to suppress — empty string skips the JSON field via the
            ``if system_message:`` guard below. ``None`` raises ``TypeError``
            so accidental omission is loud.
        additional_context: Optional string surfaced to the model as
            ``hookSpecificOutput.additionalContext``. Meaningful only for
            events in ``_EVENTS_WITH_HOOK_SPECIFIC_OUTPUT``; ignored otherwise.
        deny_reason: Optional string that turns the envelope into a blocking
            deny decision. Sets ``hookSpecificOutput.permissionDecision`` to
            ``"deny"`` and ``permissionDecisionReason`` to this value. Valid
            only for PreToolUse hooks.

    Raises:
        TypeError: If ``system_message`` is not a ``str``. Empty string is
            allowed and suppresses the field.

    Returns:
        None. Output is printed to stdout as a single JSON line.
    """
    if not isinstance(system_message, str):
        raise TypeError(
            "emit_hook_output requires system_message: str (got "
            f"{type(system_message).__name__}). Pass an empty string to "
            "suppress the systemMessage field; None is not allowed because "
            "every hook surface must explicitly state whether it produces "
            "a status line."
        )

    if event_name not in VALID_EVENT_NAMES:
        raise ValueError(
            f"emit_hook_output got unknown event_name {event_name!r}; "
            f"expected one of {sorted(VALID_EVENT_NAMES)}. Typo guard: a "
            "misspelled event name silently falls outside the runtime's "
            "allow-list and the additionalContext field is dropped without "
            "warning, so we raise here instead."
        )

    output: dict = {}
    if event_name in _EVENTS_WITH_HOOK_SPECIFIC_OUTPUT:
        hook_output: dict = {"hookEventName": event_name}
        if deny_reason:
            hook_output["permissionDecision"] = "deny"
            hook_output["permissionDecisionReason"] = deny_reason
        if additional_context:
            hook_output["additionalContext"] = additional_context
        output["hookSpecificOutput"] = hook_output
    if system_message:
        output["systemMessage"] = system_message
    print(json.dumps(output))


def emit_noop(event_name: str, reason: str) -> None:
    """Emit a low-priority status line for hooks that ran but did nothing.

    Convention: status messages emitted via this helper carry the
    ``[ivy-noop]`` prefix so the user can visually filter them from
    action-bearing status lines.

    Args:
        event_name: Hook event name (passed through to :func:`emit_hook_output`).
        reason: Short human-readable description of why the hook took no
            action. Combined into a ``"[ivy-noop] <reason>"`` system message.
    """
    emit_hook_output(event_name, system_message=f"[ivy-noop] {reason}")


def resolve_log_dir(session_id: str) -> str:
    """Determine the log directory for a session.

    Priority:
      1. $IVY_OBSERVABILITY_DIR/sessions/<session_id>/
      2. $IVY_WORKSPACE_ROOT/.observability/sessions/<session_id>/
      3. /tmp/ivy-observability/sessions/<session_id>/

    Returns:
        Absolute path string to the session log directory.
    """
    explicit = os.environ.get("IVY_OBSERVABILITY_DIR", "").strip()
    if explicit:
        return os.path.join(explicit, "sessions", session_id)

    workspace = os.environ.get("IVY_WORKSPACE_ROOT", "").strip()
    if workspace:
        return os.path.join(workspace, ".observability", "sessions", session_id)

    return os.path.join("/tmp/ivy-observability", "sessions", session_id)


def resolve_sessions_dir() -> str:
    """Return the sessions directory (parent of per-session log dirs).

    Uses the same 3-level fallback as ``resolve_log_dir``.
    """
    return os.path.dirname(resolve_log_dir("_"))
