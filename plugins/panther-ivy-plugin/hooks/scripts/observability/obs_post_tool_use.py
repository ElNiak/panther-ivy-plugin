#!/usr/bin/env python3
"""Observability hook: PostToolUse — logs successful tool completions."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

_SKIP_TOOLS = {"Read", "Grep", "Glob", "LS"}

try:
    from log_event import log_event, read_stdin

    data = read_stdin()
    session_id = data.get("session_id", "")
    tool_name = data.get("tool_name", "")

    # Skip high-frequency read-only tools unless explicitly opted in
    if tool_name in _SKIP_TOOLS and not os.environ.get("IVY_OBSERVABILITY_ALL_TOOLS"):
        sys.exit(0)
    is_mcp = tool_name.startswith("mcp__") if tool_name else False

    payload = {
        "tool_name": tool_name,
        "tool_use_id": data.get("tool_use_id", ""),
        "is_mcp_tool": is_mcp,
    }
    if is_mcp:
        parts = tool_name.split("__", 3)
        payload["mcp_server"] = parts[1] if len(parts) > 1 else ""
        payload["mcp_tool_name"] = parts[-1] if len(parts) > 2 else tool_name

    log_event("PostToolUse", session_id, payload)
except Exception:
    pass
