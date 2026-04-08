#!/usr/bin/env python3
"""PostToolUse hook: suppress review suggestion when a workflow is active.

When no workflow is active and an .ivy file is written, suggests using the
review workflow or running structural diagnostics. When a workflow is active,
exits silently — the workflow handles quality checks inline.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from hook_utils import emit_hook_output, read_stdin

from workflow_state import find_protocol_dir, get_active_workflow


def main():
    hook_input = read_stdin()
    if not hook_input:
        return

    tool_input = hook_input.get("tool_input", {})
    file_path = tool_input.get("file_path", "")

    if not file_path or not file_path.endswith(".ivy"):
        return

    protocol_dir = find_protocol_dir()
    if protocol_dir and get_active_workflow(protocol_dir) is not None:
        return

    emit_hook_output(
        "PostToolUse",
        additional_context=(
            "You edited an .ivy file outside of a workflow. Consider using the "
            "review workflow for quality checks, or run "
            'ivy_diagnostics(mode="structural") for a quick check.'
        ),
    )


if __name__ == "__main__":
    main()
