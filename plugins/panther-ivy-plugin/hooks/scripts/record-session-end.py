#!/usr/bin/env python3
"""Stop hook: record session_end event in workflow journal.

Appends a session_end event when Claude's turn ends and a workflow is active.
Non-blocking -- always exits 0.
"""

import os
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
    rotate_journal,
)


def main() -> None:
    read_stdin()

    protocol_dir = find_protocol_dir()
    if not protocol_dir:
        return

    active = get_active_workflow(protocol_dir)
    if not active:
        return

    append_journal_event(
        protocol_dir,
        event_type="session_end",
        payload={
            "clean": True,
            "phase_at_exit": active.get("phase", "unknown"),
        },
        workflow=active.get("workflow"),
        phase=active.get("phase"),
    )

    rotate_journal(protocol_dir)


if __name__ == "__main__":
    main()
