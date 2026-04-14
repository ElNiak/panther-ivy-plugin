#!/usr/bin/env python3
"""PostToolUse hook for Skill: auto-write active-workflow state when workflow skills are invoked."""

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from hook_utils import get_workspace_root, read_stdin

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


def _resolve_protocol_from_workspace(ws_root: str) -> str | None:
    """Read active workspace state to get current protocol."""
    state_file = os.path.join(ws_root, ".ivy-workspace-state.json")
    if not os.path.exists(state_file):
        return None
    try:
        with open(state_file) as f:
            data = json.load(f)
        group = data.get("active_group", "")
        return group if group else None
    except (OSError, ValueError, TypeError):
        return None


def _find_protocol_dir(ws_root: str, protocol: str | None) -> str | None:
    """Resolve protocol directory under ws_root/protocol-testing/."""
    proto_testing = os.path.join(ws_root, "protocol-testing")
    if not os.path.isdir(proto_testing):
        return None

    if protocol:
        candidate = os.path.join(proto_testing, protocol)
        return candidate if os.path.isdir(candidate) else None

    try:
        subdirs = [
            d
            for d in os.listdir(proto_testing)
            if os.path.isdir(os.path.join(proto_testing, d))
            and not d.startswith(".")
        ]
    except OSError:
        return None
    if len(subdirs) == 1:
        return os.path.join(proto_testing, subdirs[0])
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
    ws_root = get_workspace_root()

    protocol = _extract_protocol_from_args(args)
    if protocol is None:
        protocol = _resolve_protocol_from_workspace(ws_root)

    protocol_dir = _find_protocol_dir(ws_root, protocol)
    if protocol_dir is None:
        return

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

    output = {
        "hookSpecificOutput": {
            "additionalContext": (
                f"[workflow-state] Set active workflow: {workflow_name}/init"
                + (f" (protocol: {protocol})" if protocol else "")
            )
        }
    }
    print(json.dumps(output))


if __name__ == "__main__":
    main()
