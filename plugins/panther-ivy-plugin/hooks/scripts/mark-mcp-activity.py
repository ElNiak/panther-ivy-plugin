#!/usr/bin/env python3
"""PostToolUse hook: mark session activity on any panther-ivy MCP tool call.

Single responsibility: confirm the tool_name matches the panther-ivy-plugin
MCP namespace and touch the per-session activity flag. Covers tools that the
testing-tool matcher (ivy_verify|ivy_compile|…) misses — specifically
ivy_workspace, ivy_workflow_state, and ivy_status — as well as any future
panther-ivy MCP tools added without updating other matchers.

No journal write. No other side effects.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hook_utils import emit_noop, mark_session_activity, read_stdin  # noqa: E402

_PREFIX = "mcp__plugin_panther-ivy-plugin_"


def main() -> None:
    data = read_stdin()
    tool_name = data.get("tool_name", "")
    if not isinstance(tool_name, str) or not tool_name.startswith(_PREFIX):
        emit_noop("PostToolUse", f"non-panther-ivy-plugin MCP tool ({tool_name or 'unknown'})")
        return
    mark_session_activity(f"mcp:{tool_name}")
    emit_noop("PostToolUse", f"session activity marked for {tool_name}")


if __name__ == "__main__":
    main()
