#!/usr/bin/env python3
"""Unified parametric observability hook for panther-ivy-plugin.

Replaces 11 individual obs_*.py scripts. Called with --event <EventType>
to handle any Claude Code lifecycle event.

Usage:
    python3 observe.py --event PreToolUse < hook_input.json
    python3 observe.py --event SessionEnd < hook_input.json
"""

import argparse
import collections
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from lib.hook_utils import (
        MAX_CONSECUTIVE_MCP_FAILURES,
        emit_hook_output,
        emit_noop,
        read_mcp_health_state,
        write_mcp_health_state,
    )
    _HAS_HOOK_UTILS = True
except ImportError:
    _HAS_HOOK_UTILS = False

_DEFAULT_SKIP_TOOLS = {"Read", "Grep", "Glob", "LS"}


def _resolve_skip_tools() -> set[str]:
    """Read the skip-list from $IVY_OBSERVABILITY_SKIP_TOOLS or fall back to the default.

    The env var is a comma-separated list of tool names. An empty string value
    disables skipping entirely (every tool is logged). The default (`Read`,
    `Grep`, `Glob`, `LS`) prevents the highest-frequency read-only tools from
    flooding the JSONL observability stream.
    """
    override = os.environ.get("IVY_OBSERVABILITY_SKIP_TOOLS")
    if override is None:
        return set(_DEFAULT_SKIP_TOOLS)
    return {t.strip() for t in override.split(",") if t.strip()}


_SKIP_TOOLS = _resolve_skip_tools()
_KNOWN_EVENTS = {
    "PreToolUse", "PostToolUse", "PostToolUseFailure", "SessionStart",
    "SessionEnd", "Stop", "SubagentStart", "SubagentStop",
    "UserPromptSubmit", "Notification", "PermissionRequest", "PreCompact",
}


def _parse_mcp_tool_name(tool_name: str) -> tuple[str, str]:
    """Extract (server, tool) from an MCP tool name like 'mcp__server__tool'."""
    parts = tool_name.split("__", 3)
    return (parts[1] if len(parts) > 1 else "", parts[-1] if len(parts) > 2 else tool_name)


def _summarize_tool_input(tool_name: str, tool_input: dict) -> dict:
    """Produce a privacy-safe summary of tool input."""
    if tool_name == "Bash":
        return {"command": tool_input.get("command", "")[:200]}
    if tool_name in ("Write", "Edit"):
        return {
            "file_path": tool_input.get("file_path", ""),
            "content_length": len(tool_input.get("content", tool_input.get("new_string", ""))),
        }
    if tool_name == "Read":
        return {"file_path": tool_input.get("file_path", "")}
    if tool_name == "WebFetch":
        return {
            "url": tool_input.get("url", "")[:200],
            "prompt_length": len(tool_input.get("prompt", "")),
        }
    if tool_name.startswith("mcp__"):
        server, tool = _parse_mcp_tool_name(tool_name)
        return {"mcp_server": server, "mcp_tool": tool}
    return {"keys": list(tool_input.keys())[:10]}


def _build_payload(event_type: str, data: dict) -> dict | None:
    """Build event-specific payload from hook input data.

    Returns None to signal the event should be skipped (e.g., high-frequency tools).
    """
    tool_name = data.get("tool_name", "")

    if event_type == "PreToolUse":
        if tool_name in _SKIP_TOOLS and not os.environ.get("IVY_OBSERVABILITY_ALL_TOOLS"):
            return None
        tool_input = data.get("tool_input", {})
        return {
            "tool_name": tool_name,
            "tool_use_id": data.get("tool_use_id", ""),
            "tool_summary": _summarize_tool_input(tool_name, tool_input if isinstance(tool_input, dict) else {}),
            "active_workspace": os.environ.get("IVY_ACTIVE_WORKSPACE", ""),
        }

    if event_type == "PostToolUse":
        if tool_name in _SKIP_TOOLS and not os.environ.get("IVY_OBSERVABILITY_ALL_TOOLS"):
            return None
        is_mcp = tool_name.startswith("mcp__") if tool_name else False
        payload = {
            "tool_name": tool_name,
            "tool_use_id": data.get("tool_use_id", ""),
            "is_mcp_tool": is_mcp,
        }
        if is_mcp:
            server, tool = _parse_mcp_tool_name(tool_name)
            payload["mcp_server"] = server
            payload["mcp_tool_name"] = tool
        return payload

    if event_type == "PostToolUseFailure":
        error = data.get("error", "")
        tool_input = data.get("tool_input", {}) or {}
        return {
            "tool_name": tool_name,
            "tool_use_id": data.get("tool_use_id", ""),
            "error": str(error)[:500],
            "is_interrupt": data.get("is_interrupt", False),
            "tool_summary": _summarize_tool_input(
                tool_name,
                tool_input if isinstance(tool_input, dict) else {},
            ),
        }

    if event_type == "SessionStart":
        return {
            "source": data.get("source", ""),
            "model": data.get("model", ""),
            "agent_type": data.get("agent_type", ""),
            "permission_mode": data.get("permission_mode", ""),
            "workspace_root": os.environ.get("IVY_WORKSPACE_ROOT", ""),
        }

    if event_type == "SessionEnd":
        payload = {"reason": data.get("reason", "")}
        payload.update(_session_end_tool_summary(data.get("session_id", "")))
        return payload

    if event_type == "Stop":
        message = data.get("last_assistant_message", "")
        return {
            "stop_hook_active": data.get("stop_hook_active", False),
            "message_length": len(message) if isinstance(message, str) else 0,
        }

    if event_type == "SubagentStart":
        return {
            "agent_id": data.get("agent_id", ""),
            "agent_type": data.get("agent_type", ""),
        }

    if event_type == "SubagentStop":
        message = data.get("last_assistant_message", "")
        return {
            "agent_id": data.get("agent_id", ""),
            "agent_type": data.get("agent_type", ""),
            "stop_hook_active": data.get("stop_hook_active", False),
            "message_length": len(message) if isinstance(message, str) else 0,
        }

    if event_type == "UserPromptSubmit":
        prompt = data.get("prompt", "")
        return {
            "prompt_length": len(prompt) if isinstance(prompt, str) else 0,
            "prompt_preview": prompt[:100] if isinstance(prompt, str) else "",
        }

    if event_type == "Notification":
        message = data.get("message", "")
        return {
            "notification_type": data.get("notification_type", ""),
            "title": data.get("title", ""),
            "message_length": len(message) if isinstance(message, str) else 0,
        }

    if event_type == "PermissionRequest":
        suggestions = data.get("permission_suggestions", [])
        return {
            "tool_name": data.get("tool_name", ""),
            "suggestion_count": len(suggestions) if isinstance(suggestions, list) else 0,
        }

    if event_type == "PreCompact":
        return {
            "trigger": data.get("trigger", ""),
            "has_custom_instructions": bool(data.get("custom_instructions")),
        }

    return {}


def _session_end_tool_summary(session_id: str) -> dict:
    """Read back events.jsonl to produce a tool usage summary for SessionEnd."""
    obs_dir = os.environ.get("IVY_OBSERVABILITY_DIR", "").strip()
    ws_root = os.environ.get("IVY_WORKSPACE_ROOT", "").strip()

    candidates = []
    if obs_dir:
        candidates.append(Path(obs_dir) / "sessions" / session_id / "events.jsonl")
    if ws_root:
        candidates.append(Path(ws_root) / ".observability" / "sessions" / session_id / "events.jsonl")
    candidates.append(Path("/tmp/ivy-observability") / "sessions" / session_id / "events.jsonl")

    for events_file in candidates:
        if events_file.exists():
            try:
                tool_counts = collections.Counter()
                for line in events_file.read_text().splitlines():
                    try:
                        evt = json.loads(line)
                        if evt.get("event_type") == "PreToolUse":
                            tool_name = (evt.get("payload") or {}).get("tool_name", "?")
                            tool_counts[tool_name] += 1
                    except (json.JSONDecodeError, TypeError):
                        continue
                if tool_counts:
                    return {
                        "tool_summary": dict(tool_counts.most_common(10)),
                        "total_tool_calls": sum(tool_counts.values()),
                    }
            except OSError:
                pass
    return {}


def _handle_mcp_health_circuit_breaker(
    tool_name: str, hook_input: dict | None = None
) -> None:
    """Increment the MCP health failure counter for ivy tools and warn when threshold is reached.

    Args:
        tool_name: Name of the tool whose call just failed.
        hook_input: Parsed stdin payload from the spawning ``observe.py``
            invocation. Threaded through to ``read_mcp_health_state`` /
            ``write_mcp_health_state`` so the circuit-breaker counter
            writes to the *current* session's per-session state file
            instead of the workspace-shared file (which can hold a sibling
            session's id under concurrent Claude Code sessions).
    """
    if "ivy" not in tool_name.lower():
        return

    if not _HAS_HOOK_UTILS:
        return

    try:
        state = read_mcp_health_state(hook_input)
        state["consecutive_failures"] = state.get("consecutive_failures", 0) + 1
        write_mcp_health_state(state, hook_input)

        if state["consecutive_failures"] >= MAX_CONSECUTIVE_MCP_FAILURES:
            emit_hook_output(
                "PostToolUseFailure",
                system_message=(
                    f"[ivy-health] {state['consecutive_failures']} consecutive "
                    "MCP tool failures — server may be crashed"
                ),
                additional_context=(
                    f"[ivy-health] WARNING: {state['consecutive_failures']} "
                    "consecutive MCP tool failures. The MCP server may be "
                    "crashed. Ask the user to run /mcp to reconnect. "
                    "If that fails, run the triage workflow to diagnose."
                ),
            )
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--event", required=True)
    args = parser.parse_args()

    if os.environ.get("IVY_OBSERVABILITY_ENABLED", "1") == "0":
        if _HAS_HOOK_UTILS:
            emit_noop(args.event, "observability disabled (IVY_OBSERVABILITY_ENABLED=0)")
        return

    if args.event not in _KNOWN_EVENTS:
        print(f"[ivy-obs] unknown event type: {args.event}", file=sys.stderr)

    from log_event import log_event
    from lib.hook_utils import read_stdin

    data = read_stdin()
    session_id = data.get("session_id", "")
    tool_name = data.get("tool_name", "")
    payload = _build_payload(args.event, data)

    if payload is None:
        if _HAS_HOOK_UTILS:
            emit_noop(args.event, f"event filtered (tool={tool_name or 'n/a'})")
        return

    try:
        log_event(args.event, session_id, payload)
    except Exception:
        pass

    if args.event == "PostToolUseFailure":
        _handle_mcp_health_circuit_breaker(tool_name, hook_input=data)

    if _HAS_HOOK_UTILS:
        emit_hook_output(
            args.event,
            system_message=f"[ivy-obs] {args.event} logged for {tool_name or 'lifecycle'}",
        )


if __name__ == "__main__":
    main()
