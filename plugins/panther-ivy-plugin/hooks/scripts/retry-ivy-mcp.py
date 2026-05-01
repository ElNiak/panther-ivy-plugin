#!/usr/bin/env python3
"""PostToolUseFailure hook: prompt retry for idempotent read-only ivy_* MCP tools.

Fires when one of the four read-only ivy_* tools fails transiently. Because the
Claude Code hook protocol has no "re-invoke" primitive, the hook emits
additionalContext instructing the agent to retry once, and always appends a
progress{kind: "mcp_retry"} journal entry so the failure is visible in
ivy_observability(action="get_journal").

Write-side tools (ivy_compile, ivy_verify, ivy_iut_test) are intentionally NOT
in the allowlist — they are not idempotent and their failures surface immediately.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hook_utils import emit_hook_output, emit_noop, read_stdin
from workflow_state import WorkflowContext, append_journal_event

_ALLOWLIST = frozenset({
    "mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_status",
    "mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_diagnostics",
    "mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_model_info",
    "mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_coverage",
})


def main() -> None:
    data = read_stdin()
    tool_name = data.get("tool_name", "")

    if tool_name not in _ALLOWLIST:
        emit_noop(
            "PostToolUseFailure",
            f"tool '{tool_name or 'unknown'}' not in retry allowlist",
        )
        return

    short_name = tool_name.split("__")[-1] if "__" in tool_name else tool_name

    ctx = WorkflowContext.current()
    if ctx is not None:
        append_journal_event(
            ctx.protocol_dir,
            event_type="progress",
            payload={"kind": "mcp_retry", "tool": tool_name, "attempt": 1},
            workflow=ctx.workflow,
            phase=ctx.phase,
        )

    emit_hook_output(
        "PostToolUseFailure",
        additional_context=(
            f"[ivy-retry] Transient failure on {short_name}. "
            "The retry-ivy-mcp hook fired. Retry the same tool call once "
            "before reporting failure. This tool is read-only and idempotent — "
            "a single retry is safe. If the retry also fails, apply the manual "
            "recovery pattern from the mcp-tool-reliability rule."
        ),
        system_message=f"[ivy-retry] retried {short_name} after failure",
    )


if __name__ == "__main__":
    main()
