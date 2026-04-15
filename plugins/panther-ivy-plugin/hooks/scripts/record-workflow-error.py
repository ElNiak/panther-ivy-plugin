#!/usr/bin/env python3
"""PostToolUse hook: record error events in workflow journal during active workflows.

Detects compilation failures, verification failures, and tool errors from
MCP tool results when a workflow is active.
Non-blocking -- always exits 0.
"""

import json
import os
import re
import sys

sys.path.insert(
    0,
    os.path.join(
        os.environ.get("CLAUDE_PLUGIN_ROOT", "."), "hooks", "scripts"
    ),
)
from hook_utils import read_stdin
from workflow_state import (
    append_journal_event,
    find_protocol_dir,
    get_active_workflow,
)

_ERROR_PATTERNS = [
    (re.compile(r"compilation failed", re.IGNORECASE), "Ivy compilation failed"),
    (re.compile(r"FAIL\b.*isolate", re.IGNORECASE), "Verification failure"),
    (re.compile(r"error:.*\.ivy", re.IGNORECASE), "Ivy file error"),
    (re.compile(r'"success":\s*false', re.IGNORECASE), "MCP tool returned failure"),
    (re.compile(r"timed?\s*out|timeout\s+(?:exceeded|expired|killed)", re.IGNORECASE), "Operation timed out"),
]

_WATCHED_TOOLS = {
    "ivy_verify", "ivy_compile", "ivy_diagnostics",
    "ivy_coverage", "ivy_iut_test", "ivy_quality",
}


def _extract_error_summary(tool_result: str) -> str | None:
    """Check tool result for error patterns and return summary."""
    for pattern, summary in _ERROR_PATTERNS:
        if pattern.search(tool_result):
            return summary
    return None


def main() -> None:
    hook_input = read_stdin()
    tool_name = hook_input.get("tool_name", "")

    if tool_name not in _WATCHED_TOOLS:
        return

    protocol_dir = find_protocol_dir()
    if not protocol_dir:
        return

    active = get_active_workflow(protocol_dir)
    if not active:
        return

    tool_result = hook_input.get("tool_result", "")
    if isinstance(tool_result, dict):
        tool_result = json.dumps(tool_result)
    elif not isinstance(tool_result, str):
        tool_result = str(tool_result)

    error_summary = _extract_error_summary(tool_result)
    if not error_summary:
        return

    append_journal_event(
        protocol_dir,
        event_type="error",
        payload={
            "summary": error_summary,
            "tool": tool_name,
            "recoverable": True,
        },
        workflow=active.get("workflow"),
        phase=active.get("phase"),
    )


if __name__ == "__main__":
    main()
