#!/usr/bin/env python3
"""Observability hook: PreToolUse — logs tool invocations with summarized input."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


def _summarize_tool_input(tool_name: str, tool_input: dict) -> dict:
    """Produce a privacy-safe summary of tool input."""
    if tool_name == "Bash":
        cmd = tool_input.get("command", "")
        return {"command": cmd[:200]}
    if tool_name in ("Write", "Edit"):
        return {
            "file_path": tool_input.get("file_path", ""),
            "content_length": len(tool_input.get("content", tool_input.get("new_string", ""))),
        }
    if tool_name == "Read":
        return {"file_path": tool_input.get("file_path", "")}
    if tool_name.startswith("mcp__"):
        parts = tool_name.split("__", 3)
        return {
            "mcp_server": parts[1] if len(parts) > 1 else "",
            "mcp_tool": parts[-1] if len(parts) > 2 else tool_name,
        }
    return {"keys": list(tool_input.keys())[:10]}


_SKIP_TOOLS = {"Read", "Grep", "Glob", "LS"}

try:
    from log_event import log_event, read_stdin

    data = read_stdin()
    session_id = data.get("session_id", "")
    tool_name = data.get("tool_name", "")

    # Skip high-frequency read-only tools unless explicitly opted in
    if tool_name in _SKIP_TOOLS and not os.environ.get("IVY_OBSERVABILITY_ALL_TOOLS"):
        sys.exit(0)
    tool_input = data.get("tool_input", {})

    log_event(
        "PreToolUse",
        session_id,
        {
            "tool_name": tool_name,
            "tool_use_id": data.get("tool_use_id", ""),
            "tool_summary": _summarize_tool_input(tool_name, tool_input if isinstance(tool_input, dict) else {}),
            "active_workspace": os.environ.get("IVY_ACTIVE_WORKSPACE", ""),
        },
    )
except Exception:
    pass
