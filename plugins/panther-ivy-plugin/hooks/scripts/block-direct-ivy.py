#!/usr/bin/env python3
"""PreToolUse hook: warn (do not block) on direct Ivy CLI calls in Bash.

Goes through ``emit_hook_output`` so the envelope shape is correct by
construction.

The script is **advisory** — it never sets ``permissionDecision: "deny"``.
``iron-laws.md`` describes this hook as an "advisory hint" rather than an
enforcement site, so the documentation matches the script's actual behavior.
"""

from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hook_utils import emit_hook_output, emit_noop, read_stdin  # noqa: E402

_DIRECT_IVY_RE = re.compile(r"\b(?:ivy_check|ivyc|ivy_show|ivy_to_cpp)\b")

_SUGGESTION_TABLE = (
    "**Detected direct Ivy CLI invocation.** Consider using ivy-tools MCP tools instead:\n\n"
    "| CLI Tool   | Recommended MCP Tool | Alt. Command       |\n"
    "|------------|----------------------|--------------------|\n"
    "| `ivy_check`  | `ivy_verify`         | `/nct-check`       |\n"
    "| `ivyc`       | `ivy_compile`        | `/nct-compile`     |\n"
    "| `ivy_show`   | `ivy_model_info`     | `/nct-model-info`  |\n"
    "| `ivy_to_cpp` | `ivy_compile`        | —                  |\n\n"
    "**Benefits of MCP tools:**\n"
    "- Structured JSON output\n"
    "- Semantic model integration\n"
    "- Workflow state tracking\n"
    "- Better error handling and recovery"
)


def main() -> None:
    data = read_stdin()
    tool_input = data.get("tool_input", {}) or {}
    command = str(tool_input.get("command", ""))

    if not command:
        emit_noop("PreToolUse", "no Bash command in tool input")
        return

    match = _DIRECT_IVY_RE.search(command)
    if not match:
        emit_noop("PreToolUse", "no direct Ivy CLI call detected")
        return

    emit_hook_output(
        "PreToolUse",
        system_message=f"[ivy-block] direct CLI call detected: {match.group(0)}",
        additional_context=_SUGGESTION_TABLE,
    )


if __name__ == "__main__":
    main()
