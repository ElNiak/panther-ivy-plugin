#!/usr/bin/env python3
"""Shared utilities for panther-ivy-plugin hook scripts.

Centralizes session ID resolution, workspace detection, MCP health state
management, and JSON hook output formatting.
"""

import json
import os
import sys
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


def read_stdin() -> dict:
    """Read and parse JSON from stdin. Returns empty dict on failure."""
    try:
        data = json.load(sys.stdin)
        return data if isinstance(data, dict) else {}
    except (OSError, EOFError, ValueError, TypeError):
        return {}


def emit_hook_output(
    event_name: str,
    *,
    additional_context: str | None = None,
    deny_reason: str | None = None,
    system_message: str | None = None,
) -> None:
    """Print structured hook JSON output to stdout."""
    hook_output: dict = {"hookEventName": event_name}
    if deny_reason:
        hook_output["permissionDecision"] = "deny"
        hook_output["permissionDecisionReason"] = deny_reason
    if additional_context:
        hook_output["additionalContext"] = additional_context
    output: dict = {"hookSpecificOutput": hook_output}
    if system_message:
        output["systemMessage"] = system_message
    print(json.dumps(output))
