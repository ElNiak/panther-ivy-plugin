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
    WorkflowContext,
    append_journal_event,
    rotate_journal,
)


def main() -> None:
    read_stdin()

    ctx = WorkflowContext.current()
    if ctx is None:
        return

    append_journal_event(
        ctx.protocol_dir,
        event_type="session_end",
        payload={
            "clean": True,
            "phase_at_exit": ctx.phase or "unknown",
        },
        workflow=ctx.workflow,
        phase=ctx.phase,
    )

    rotate_journal(ctx.protocol_dir)


if __name__ == "__main__":
    main()
