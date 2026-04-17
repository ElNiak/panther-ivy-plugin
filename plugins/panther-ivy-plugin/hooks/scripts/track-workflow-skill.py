#!/usr/bin/env python3
"""PostToolUse hook for Skill: auto-write active-workflow state when workflow skills are invoked."""

import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from hook_utils import emit_hook_output, get_workspace_root, read_stdin
from statusline_cache import update_from_hook as _statusline_update
from workflow_state import (
    append_journal_event,
    find_protocol_dir,
    get_active_workflow,
    resolve_protocol_from_workspace,
)

_WORKFLOW_SKILLS = {"navigate", "build", "verify", "review", "triage"}
_PLUGIN_PREFIX = "panther-ivy-plugin:"
_STATE_DIR = ".panther-ivy"
_ACTIVE_WORKFLOW_FILE = "active-workflow"
_KNOWN_PROTOCOLS = {"quic", "bgp", "coap", "minip", "apt", "apt_quic"}


def _extract_skill_name(raw: str) -> str | None:
    """Extract the bare workflow name from a skill identifier."""
    name = raw.strip().lower()
    if name.startswith(_PLUGIN_PREFIX):
        name = name[len(_PLUGIN_PREFIX):]
    return name if name in _WORKFLOW_SKILLS else None


def _extract_protocol_from_args(args: str) -> str | None:
    """Try to find a protocol name in skill arguments."""
    if not args:
        return None
    args_lower = args.strip().lower()
    for proto in _KNOWN_PROTOCOLS:
        if re.search(r"\b" + re.escape(proto) + r"\b", args_lower):
            return proto
    return None


def main() -> None:
    hook_input = read_stdin()
    tool_name = hook_input.get("tool_name", "")
    if tool_name != "Skill":
        return

    tool_input = hook_input.get("tool_input", {})
    skill_raw = tool_input.get("skill", "")
    workflow_name = _extract_skill_name(skill_raw)
    if workflow_name is None:
        return

    args = tool_input.get("args", "")

    protocol = _extract_protocol_from_args(args)
    if protocol is None:
        ws_root = get_workspace_root()
        protocol = resolve_protocol_from_workspace(ws_root)

    protocol_dir = find_protocol_dir(protocol)
    if protocol_dir is None:
        return

    previous_state = get_active_workflow(protocol_dir)
    previous_phase = previous_state.get("phase") if previous_state else None

    state_dir = os.path.join(protocol_dir, _STATE_DIR)
    os.makedirs(state_dir, exist_ok=True)

    data = {
        "workflow": workflow_name,
        "phase": "init",
        "invocation_depth": 0,
        "started": datetime.now(timezone.utc).isoformat(),
    }

    filepath = os.path.join(state_dir, _ACTIVE_WORKFLOW_FILE)
    try:
        import yaml

        with open(filepath, "w") as f:
            yaml.safe_dump(data, f)
    except ImportError:
        with open(filepath, "w") as f:
            f.write(f"workflow: {workflow_name}\n")
            f.write("phase: init\n")
            f.write("invocation_depth: 0\n")
            f.write(f"started: '{data['started']}'\n")

    if previous_phase is not None and previous_phase != "init":
        append_journal_event(
            protocol_dir,
            event_type="phase_transition",
            payload={"from": previous_phase, "to": "init"},
            workflow=workflow_name,
            phase="init",
        )

    _statusline_update("workflow", {
        "name": workflow_name,
        "phase": "init",
        "invocation_depth": 0,
        "caller": None,
        "started": data["started"],
    })
    if protocol:
        _statusline_update("workspace", {"protocol": protocol})

    emit_hook_output(
        "PostToolUse",
        additional_context=(
            f"[workflow-state] Set active workflow: {workflow_name}/init"
            + (f" (protocol: {protocol})" if protocol else "")
        ),
    )


if __name__ == "__main__":
    main()
