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
from hook_utils import emit_hook_output
from workflow_state import (
    append_journal_event,
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
        append_journal_event(
            protocol_dir,
            event_type="session_start",
            payload={"resumed_from": None},
            workflow=None,
            phase=None,
        )
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
                f"(phase: {phase_name})"
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
        emit_hook_output(
            "SessionStart",
            additional_context=(
                f"Active workflow: {active.get('workflow', '?')} "
                f"(phase: {active.get('phase', '?')})"
            ),
        )


if __name__ == "__main__":
    main()
