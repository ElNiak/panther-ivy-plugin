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
from hook_utils import emit_hook_output, read_stdin
from statusline_cache import update_from_hook as _statusline_update

from workflow_state import WorkflowContext


_TARGET_RE = re.compile(r"[\w/.\-]+\.(?:ivy|spec)")
_PLUGIN_AGENT_PREFIX = "panther-ivy-plugin:"


def _extract_target_file(prompt: str | None) -> str | None:
    """Best-effort extraction of the .ivy/.spec path mentioned in an Agent prompt."""
    if not prompt:
        return None
    m = _TARGET_RE.search(prompt)
    return m.group(0) if m else None


def _handle_agent(tool_input: dict[str, Any]) -> None:
    """PostToolUse branch for Agent dispatches.

    Returns silently for non-plugin agents (general-purpose, Explore, etc.).
    For plugin-prefixed agents, surfaces a `[ivy-state]` systemMessage and
    refreshes the statusline `active_agent` section.
    """
    subagent_type = tool_input.get("subagent_type", "") or ""
    if not subagent_type.startswith(_PLUGIN_AGENT_PREFIX):
        return

    prompt = tool_input.get("prompt", "") or ""
    target_file = _extract_target_file(prompt)

    _statusline_update(
        "active_agent",
        {"name": subagent_type, "target_file": target_file},
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
        return

    tool_name = hook_input.get("tool_name", "")
    tool_input = hook_input.get("tool_input", {})

    if tool_name == "Agent":
        _handle_agent(tool_input)
        return

    file_path = tool_input.get("file_path", "")

    if not file_path or not file_path.endswith(".ivy"):
        return

    # Track the most recently written .ivy file as the statusline "active test
    # file" — a best-effort hint; the workflow skill may override this with a
    # more authoritative focus target.
    from os.path import basename
    _statusline_update("test_file", {
        "basename": basename(file_path),
        "source": "last-edited",
    })

    if WorkflowContext.current() is not None:
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
