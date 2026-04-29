#!/usr/bin/env python3
"""Shared utilities for panther-ivy-plugin hook scripts.

Centralizes session ID resolution, workspace detection, MCP health state
management, and JSON hook output formatting.
"""

import fcntl
import json
import os
import sys
import time
try:
    from ivy_lsp.infra.observability.session import resolve_session_id as _canonical_resolve
except ImportError:
    _canonical_resolve = None


def resolve_session_id(hook_input: dict | None = None) -> str:
    """Resolve Claude session ID using canonical priority chain.

    Priority: ivy-lsp canonical > hook_payload > IVY_SESSION_ID >
    CLAUDE_SESSION_ID > CLAUDE_CODE_SESSION_ID > session file > "unknown"
    """
    if _canonical_resolve is not None:
        try:
            return _canonical_resolve(hook_payload=hook_input)
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


def get_mcp_health_state_path() -> str:
    """Get the path to the MCP health state file for the current session."""
    ws_root = get_workspace_root()
    sid = resolve_session_id()
    state_dir = os.path.join(ws_root, ".observability", "sessions", sid)
    os.makedirs(state_dir, exist_ok=True)
    return os.path.join(state_dir, "mcp-health-state.json")


MAX_CONSECUTIVE_MCP_FAILURES = 3

_MCP_HEALTH_STATE_TTL = 300  # Reset the circuit breaker after 5 min of no activity.


def read_mcp_health_state() -> dict:
    """Read the MCP health state file under a shared fcntl lock.

    Returns a fresh defaults dict when the file is missing, unreadable,
    or when its ``last_update`` timestamp is older than the TTL (the
    circuit breaker auto-resets after a period of no activity). A file
    that exists but contains unparseable JSON is also treated as a miss
    and the caller's next write will overwrite it — the circuit breaker
    prefers self-healing over preserving a broken state across sessions.

    Returns:
        A ``{"consecutive_failures": int, "last_update": float}`` dict.
    """
    path = get_mcp_health_state_path()
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


def write_mcp_health_state(state: dict) -> None:
    """Write the MCP health state file under an exclusive fcntl lock.

    Always stamps ``last_update`` before writing so the TTL-based
    auto-reset remains correct. Silent on OSError — callers run this on
    the hook hot path and must not fail the session on I/O errors.

    Args:
        state: Mutable dict written as JSON. ``last_update`` is set
            before writing; any caller-provided value is overwritten.
    """
    path = get_mcp_health_state_path()
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


_EVENTS_WITH_HOOK_SPECIFIC_OUTPUT = frozenset({
    "PreToolUse",
    "PostToolUse",
    "PostToolBatch",
    "PostToolUseFailure",
    "UserPromptSubmit",
    "SessionStart",
    "SessionEnd",
})


def emit_hook_output(
    event_name: str,
    *,
    additional_context: str | None = None,
    deny_reason: str | None = None,
    system_message: str | None = None,
) -> None:
    """Print a Claude Code advanced-protocol hook JSON decision to stdout.

    Two envelope shapes per the runtime schema. For events in
    ``_EVENTS_WITH_HOOK_SPECIFIC_OUTPUT`` the helper emits::

        {"hookSpecificOutput": {"hookEventName": ..., ...}, "systemMessage": ...}

    For all other events (``Stop``, ``SubagentStart``, ``SubagentStop``,
    ``Notification``, ``PreCompact``) the runtime rejects ``hookSpecificOutput``
    entirely; the helper emits only top-level fields. ``additional_context``
    has no top-level home in that schema and is silently dropped — callers
    targeting those events should pass ``system_message`` instead.

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
        additional_context: Optional string surfaced to the model as
            ``hookSpecificOutput.additionalContext``. Meaningful only for
            events in ``_EVENTS_WITH_HOOK_SPECIFIC_OUTPUT``; ignored otherwise.
        deny_reason: Optional string that turns the envelope into a blocking
            deny decision. Sets ``hookSpecificOutput.permissionDecision`` to
            ``"deny"`` and ``permissionDecisionReason`` to this value. Valid
            only for PreToolUse hooks.
        system_message: Optional top-level ``systemMessage`` the Claude Code
            runtime surfaces to the user out-of-band from the model. Valid
            for every event.

    Returns:
        None. Output is printed to stdout as a single JSON line.
    """
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
