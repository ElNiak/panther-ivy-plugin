#!/usr/bin/env python3
"""SessionStart hook: clear stale active-workflow flags from interrupted sessions."""

import json
import os
import sys

sys.path.insert(
    0,
    os.path.join(
        os.environ.get("CLAUDE_PLUGIN_ROOT", "."), "hooks", "scripts"
    ),
)
from workflow_state import (
    clear_active_workflow,
    find_protocol_dir,
    get_active_workflow,
    is_workflow_stale,
)


def main() -> None:
    protocol_dir = find_protocol_dir()
    if not protocol_dir:
        return

    active = get_active_workflow(protocol_dir)
    if not active:
        return

    output: dict = {"hookSpecificOutput": {}}
    if is_workflow_stale(protocol_dir):
        clear_active_workflow(protocol_dir)
        output["hookSpecificOutput"]["additionalContext"] = (
            f"Cleared stale workflow '{active.get('workflow', '?')}' "
            f"(phase: {active.get('phase', '?')}) from a previous session."
        )
    else:
        output["hookSpecificOutput"]["additionalContext"] = (
            f"Active workflow: {active.get('workflow', '?')} "
            f"(phase: {active.get('phase', '?')})"
        )

    print(json.dumps(output))


if __name__ == "__main__":
    main()
