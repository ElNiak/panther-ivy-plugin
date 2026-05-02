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
from hook_utils import emit_hook_output, emit_noop, is_session_active, read_stdin
from workflow_state import (
    WorkflowContext,
    append_journal_event,
    journal_path,
    rotate_journal,
)


def main() -> None:
    read_stdin()

    if not is_session_active():
        emit_noop("Stop", "no ivy activity this session — skipping summary")
        return

    ctx = WorkflowContext.current()
    if ctx is None:
        emit_noop(
            "Stop",
            "activity recorded; no orchestrator workflow — skipping journal append",
        )
        return

    clean = True
    append_journal_event(
        ctx.protocol_dir,
        event_type="session_end",
        payload={
            "clean": clean,
            "phase_at_exit": ctx.phase or "unknown",
        },
        workflow=ctx.workflow,
        phase=ctx.phase,
    )

    rotate_journal(ctx.protocol_dir)

    emit_hook_output(
        "Stop",
        system_message=(
            f"[ivy-session] recorded clean={str(clean).lower()}; "
            f"session_end appended to journal at {journal_path(ctx.protocol_dir)}"
        ),
    )


if __name__ == "__main__":
    main()
