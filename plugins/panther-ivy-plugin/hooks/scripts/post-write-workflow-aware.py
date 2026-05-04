#!/usr/bin/env python3
"""PostToolUse hook: workflow-aware annotation for Write/Edit and Agent.

For Write/Edit on .ivy files: when no workflow is active, suggests using the
review workflow or running structural diagnostics. When a workflow is active,
exits silently — the workflow handles quality checks inline.

For Agent dispatches whose subagent_type is plugin-prefixed
(``panther-ivy-plugin:*``): emits a `[ivy-state]` line so the user sees
which specialist agent was dispatched and (best-effort) which target file
the prompt referenced. Non-plugin agents are ignored.
"""

import re
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))
from lib.hook_utils import (
    emit_hook_output,
    emit_noop,
    mark_session_activity,
    read_stdin,
    resolve_active_group_for_hook as _active_group,
)
from lib.statusline_cache import update_overlay_from_hook as _overlay_update
from lib.statusline_cache import update_from_hook as _statusline_update

from lib.workflow_state import WorkflowContext


_TARGET_RE = re.compile(r"[\w/.\-]+\.(?:ivy|spec)")
_PLUGIN_AGENT_PREFIX = "panther-ivy-plugin:"

# Specialist agents flip the session-activity flag; critic agents do not —
# they are gate machinery, not user-initiated ivy work.
_SPECIALIST_AGENTS = frozenset({
    "ivy-refiner-agent",
    "ivy-experimenter-agent",
    "ivy-builder-agent",
    "ivy-reviewer-agent",
    "ivy-triage-agent",
    "ivy-meta-agent",
})


def _extract_target_file(prompt: str | None) -> str | None:
    """Best-effort extraction of the .ivy/.spec path mentioned in an Agent prompt."""
    if not prompt:
        return None
    m = _TARGET_RE.search(prompt)
    return m.group(0) if m else None


def _handle_agent(tool_input: dict[str, Any]) -> None:
    """PostToolUse branch for Agent dispatches.

    Emits a no-op status line for non-plugin agents (general-purpose, Explore,
    etc.). For plugin-prefixed agents, surfaces a `[ivy-state]` systemMessage
    and refreshes the statusline `active_agent` section.
    """
    subagent_type = tool_input.get("subagent_type", "") or ""
    if not subagent_type.startswith(_PLUGIN_AGENT_PREFIX):
        emit_noop(
            "PostToolUse",
            f"non-plugin agent dispatch ({subagent_type or 'unspecified'})",
        )
        return

    short_type = subagent_type[len(_PLUGIN_AGENT_PREFIX):]
    if short_type in _SPECIALIST_AGENTS:
        mark_session_activity(f"agent:{subagent_type}")

    prompt = tool_input.get("prompt", "") or ""
    target_file = _extract_target_file(prompt)

    _statusline_update(
        "active_agent",
        {"name": subagent_type, "target_file": target_file},
        active_group=_active_group(),
    )

    if WorkflowContext.current() is None:
        emit_hook_output(
            "PostToolUse",
            system_message=(
                f"[ivy-state] agent dispatched outside workflow: {subagent_type}"
            ),
            additional_context=(
                "Consider invoking the orchestrator first to establish "
                "workflow context."
            ),
        )
        return

    emit_hook_output(
        "PostToolUse",
        system_message=(
            f"[ivy-state] active-agent={subagent_type}, "
            f"target_file={target_file or '<n/a>'}"
        ),
    )


def main():
    hook_input = read_stdin()
    if not hook_input:
        emit_noop("PostToolUse", "no hook input")
        return

    tool_name = hook_input.get("tool_name", "")
    tool_input = hook_input.get("tool_input", {})

    if tool_name == "Agent":
        _handle_agent(tool_input)
        return

    file_path = tool_input.get("file_path", "")

    if not file_path or not file_path.endswith(".ivy"):
        emit_noop("PostToolUse", "non-.ivy file or empty path")
        return

    # Track the most recently written .ivy file in this session's per-session
    # overlay (cache/<wsHash>/<active_group>/sessions/<session_id>/overlay.json)
    # rather than the workspace-shared cache. Two Claude Code windows editing
    # different .ivy files in the same workspace previously overwrote each
    # other's `test_file` segment because they wrote to one shared file; the
    # overlay write is keyed by `session_id` from stdin so each window keeps
    # its own view. Falls back to a no-op when the harness omits session_id
    # (offline smoke-test invocation) — the renderer's testfile segment
    # falls through to the shared cache value when the overlay is missing.
    from os.path import basename
    session_id = str(hook_input.get("session_id", "")).strip()
    payload = {
        "test_file": {
            "basename": basename(file_path),
            "source": "last-edited",
        }
    }
    if session_id:
        _overlay_update(session_id, payload)
    else:
        # Harness payload missing session_id → keep legacy shared-cache write
        # so the segment is still populated in offline / smoke-test runs.
        _statusline_update(
            "test_file", payload["test_file"], active_group=_active_group()
        )

    if WorkflowContext.current() is not None:
        emit_noop(
            "PostToolUse",
            f".ivy edit inside active workflow ({basename(file_path)})",
        )
        return

    emit_hook_output(
        "PostToolUse",
        system_message=(
            "[ivy-state] orientation hint surfaced for non-workflow .ivy edit"
        ),
        additional_context=(
            "You edited an .ivy file outside of a workflow. Consider using the "
            "review workflow for quality checks, or run "
            'ivy_diagnostics(mode="structural") for a quick check.'
        ),
    )


if __name__ == "__main__":
    main()
