#!/usr/bin/env python3
"""PostToolUse hook for Skill: maintain active-workflow state across dispatch.

Contract: the `active-workflow` YAML file's `invocation_depth` and `caller`
fields together implement the sub-workflow protocol documented in the plugin
CLAUDE.md (lines 41-52). When workflow A dispatches workflow B via the Skill
tool, the hook captures A as B's `caller` and increments `invocation_depth`.
When B completes, the skill body itself decrements via `ivy_workflow_state`.

This hook only handles the entry path. Write path rules:
- Same workflow as the existing active one: no-op (preserve `started`,
  `invocation_depth`, `caller`). Re-invoking the same skill mid-workflow
  does not reset its start timestamp or nesting depth.
- Different workflow, existing is still active (not stale): nested
  dispatch. Increment `invocation_depth`, set `caller` to the existing
  workflow, refresh `started` to the child's start.
- Different workflow, existing is absent or stale (> 2h): fresh start.
  `invocation_depth=0`, `caller=null`.

Concurrent writes are serialized via `fcntl.flock(..., LOCK_EX)` matching
the pattern in `check-mcp-health.py`.
"""

import fcntl
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

sys.path.insert(0, str(Path(__file__).parent))
from hook_utils import emit_hook_output, get_workspace_root, read_stdin
from statusline_cache import update_sections_from_hook as _statusline_update_sections
from workflow_state import (
    append_journal_event,
    find_protocol_dir,
    get_active_workflow,
    is_workflow_stale,
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


def _compute_new_state(
    protocol_dir: str,
    previous: dict[str, Any] | None,
    workflow_name: str,
    now_iso: str,
) -> tuple[dict[str, Any] | None, str]:
    """Compute the new active-workflow payload for a Skill dispatch.

    Args:
        protocol_dir: Path to the protocol directory (for staleness check).
        previous: Parsed contents of the existing active-workflow file, or
            None if no prior state exists.
        workflow_name: The skill-derived workflow name being dispatched.
        now_iso: ISO-8601 timestamp for the dispatch moment.

    Returns:
        (new_state, kind). `new_state` is the dict to write, or None when
        the dispatch is a same-workflow re-entry (no write needed). `kind`
        is one of ``"reenter"``, ``"nested"``, ``"fresh"``.
    """
    if previous is not None and previous.get("workflow") == workflow_name:
        return None, "reenter"

    if previous is not None and not is_workflow_stale(protocol_dir):
        prior_depth = previous.get("invocation_depth", 0)
        try:
            depth = int(prior_depth) + 1
        except (TypeError, ValueError):
            depth = 1
        return (
            {
                "workflow": workflow_name,
                "phase": "init",
                "invocation_depth": depth,
                "caller": previous.get("workflow"),
                "started": now_iso,
            },
            "nested",
        )

    return (
        {
            "workflow": workflow_name,
            "phase": "init",
            "invocation_depth": 0,
            "caller": None,
            "started": now_iso,
        },
        "fresh",
    )


def _write_state_locked(filepath: str, data: dict[str, Any]) -> None:
    """Serialize ``data`` to ``filepath`` under an exclusive flock."""
    with open(filepath, "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            yaml.safe_dump(data, f)
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


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
    filepath = os.path.join(state_dir, _ACTIVE_WORKFLOW_FILE)

    now_iso = datetime.now(timezone.utc).isoformat()
    new_state, kind = _compute_new_state(protocol_dir, previous_state, workflow_name, now_iso)

    if new_state is not None:
        _write_state_locked(filepath, new_state)

    if previous_phase is not None and previous_phase != "init" and kind != "reenter":
        append_journal_event(
            protocol_dir,
            event_type="phase_transition",
            payload={"from": previous_phase, "to": "init"},
            workflow=workflow_name,
            phase="init",
        )

    effective_state = new_state or previous_state or {
        "workflow": workflow_name,
        "phase": "init",
        "invocation_depth": 0,
        "caller": None,
        "started": now_iso,
    }

    updates = {
        "workflow": {
            "name": effective_state["workflow"],
            "phase": effective_state.get("phase", "init"),
            "invocation_depth": effective_state.get("invocation_depth", 0),
            "caller": effective_state.get("caller"),
            "started": effective_state.get("started", now_iso),
        },
    }
    if protocol:
        updates["workspace"] = {"protocol": protocol}
    _statusline_update_sections(updates)

    if kind == "nested":
        context = (
            f"[workflow-state] Nested dispatch: "
            f"{effective_state['caller']} -> {workflow_name} "
            f"(depth {effective_state['invocation_depth']})"
        )
    elif kind == "reenter":
        context = f"[workflow-state] Re-entry ignored: {workflow_name} already active"
    else:
        context = f"[workflow-state] Set active workflow: {workflow_name}/init"
    if protocol:
        context += f" (protocol: {protocol})"

    emit_hook_output("PostToolUse", additional_context=context)


if __name__ == "__main__":
    main()
