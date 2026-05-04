#!/usr/bin/env python3
"""SessionStart hook: clear stale active-workflow flags from interrupted sessions."""

import os
import sys

sys.path.insert(
    0,
    os.path.join(
        os.environ.get("CLAUDE_PLUGIN_ROOT", "."), "hooks", "scripts"
    ),
)
from lib.hook_utils import emit_hook_output, emit_noop
from lib.workflow_state import (
    append_journal_event,
    clear_active_workflow,
    find_protocol_dir,
    get_active_workflow,
    is_workflow_stale,
    journal_path,
)


def main() -> None:
    protocol_dir = find_protocol_dir()
    if not protocol_dir:
        emit_noop("SessionStart", "no protocol directory detected")
        return

    active = get_active_workflow(protocol_dir)
    if not active:
        emit_noop("SessionStart", "no active workflow to clean up")
        return

    if is_workflow_stale(protocol_dir):
        append_journal_event(
            protocol_dir,
            event_type="session_start",
            payload={"resumed_from": active.get("phase"), "stale_cleared": True},
            workflow=active.get("workflow"),
            phase=active.get("phase"),
        )
        clear_active_workflow(protocol_dir)
        workflow_name = active.get("workflow", "?")
        phase_name = active.get("phase", "?")
        emit_hook_output(
            "SessionStart",
            additional_context=(
                f"Cleared stale workflow '{workflow_name}' "
                f"(phase: {phase_name}) from a previous session."
            ),
            system_message=(
                f"[ivy-cleanup] cleared stale workflow '{workflow_name}' "
                f"(phase: {phase_name}); session_start appended to journal "
                f"at {journal_path(protocol_dir)}"
            ),
        )
    else:
        append_journal_event(
            protocol_dir,
            event_type="session_start",
            payload={"resumed_from": active.get("phase")},
            workflow=active.get("workflow"),
            phase=active.get("phase"),
        )
        workflow_name = active.get("workflow", "?")
        phase_name = active.get("phase", "?")
        emit_noop(
            "SessionStart",
            f"active workflow {workflow_name} (phase {phase_name}); "
            "deferring to orchestrator [ivy-resume]",
        )


if __name__ == "__main__":
    main()
