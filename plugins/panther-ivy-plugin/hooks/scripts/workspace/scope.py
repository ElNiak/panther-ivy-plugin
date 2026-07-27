#!/usr/bin/env python3
"""PreToolUse hook: check if file edit is within active workspace scope."""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.hook_utils import resolve_session_id, emit_hook_output, emit_noop, read_stdin


def main():
    # Read hook input from stdin
    hook_input = read_stdin()
    if not hook_input:
        emit_noop("PreToolUse", "no hook input")
        return

    tool_input = hook_input.get("tool_input", {})
    file_path = tool_input.get("file_path", "")

    if not file_path:
        emit_noop("PreToolUse", "no file_path in tool input")
        return

    if not file_path.endswith(".ivy"):
        emit_noop("PreToolUse", "non-.ivy file")
        return

    if os.sep + os.path.join("ivy", "include") in file_path:
        emit_noop("PreToolUse", "ivy/include path (ignored)")
        return

    workspace_root = os.environ.get("IVY_WORKSPACE_ROOT", "")
    if not workspace_root:
        emit_noop("PreToolUse", "IVY_WORKSPACE_ROOT not set")
        return

    # Parse .ivyworkspace once for all helpers
    ivyworkspace_config = _load_ivyworkspace(workspace_root)

    state_file = os.path.join(workspace_root, ".ivy-workspace-state.json")

    try:
        with open(state_file) as f:
            state = json.load(f)
    except (OSError, json.JSONDecodeError):
        _progressive_narrowing(file_path, workspace_root, ivyworkspace_config)
        return

    active_group = state.get("active_group")
    active_layers = set(state.get("active_layers", []))
    set_by = state.get("set_by", "unknown")

    if not active_layers:
        _progressive_narrowing(file_path, workspace_root, ivyworkspace_config)
        return

    file_layer = _get_file_layer(file_path, workspace_root, ivyworkspace_config)

    if file_layer is None:
        emit_hook_output(
            "PreToolUse",
            system_message=(
                f"[ivy-workspace-scope] {os.path.basename(file_path)} has no "
                "registered workspace layer"
            ),
            additional_context=(
                "This file has no registered workspace layer. If creating a new protocol:\n"
                " 1. Create protocol-testing/<name>/.ivyworkspace marker\n"
                " 2. Or run scripts/generate_protocol_markers.py after adding to root .ivyworkspace"
            ),
        )
        return

    if file_layer in active_layers:
        emit_noop(
            "PreToolUse",
            f"layer '{file_layer}' is in active workspace",
        )
        return

    file_group = _find_group_for_layer(file_layer, ivyworkspace_config)

    emit_hook_output(
        "PreToolUse",
        system_message=f"[ivy-workspace-scope] BLOCKED: {os.path.basename(file_path)}",
        deny_reason=(
            f"BLOCKED: '{os.path.basename(file_path)}' is in layer '{file_layer}' "
            f"(workspace group: {file_group or 'unknown'}).\n"
            f"Active workspace: '{active_group}' (set by: {set_by}).\n"
            f"To allow, invoke the ivy_workspace MCP tool: "
            f"ivy_workspace(action='set', target='{file_group or file_layer}') "
            f"or ivy_workspace(action='clear')."
        ),
    )


def _load_ivyworkspace(workspace_root):
    """Load and parse .ivyworkspace config. Returns dict or empty dict."""
    try:
        with open(os.path.join(workspace_root, ".ivyworkspace")) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def _get_file_layer(file_path, workspace_root, config):
    """Determine which workspace layer a file belongs to."""
    if not config:
        return None

    abs_path = os.path.realpath(file_path)
    try:
        rel_path = os.path.relpath(abs_path, workspace_root)
    except ValueError:
        return None

    for layer in config.get("workspace_layers", []):
        for include_path in layer.get("include_paths", []):
            if rel_path.startswith(include_path):
                return layer["id"]

    return None


def _find_group_for_layer(layer_id, config):
    """Find which workspace_group contains a layer."""
    if not config:
        return None

    for group_name, group_layers in config.get("workspace_groups", {}).items():
        if layer_id in group_layers:
            return group_name
    return None


def _progressive_narrowing(file_path, workspace_root, ivyworkspace_config):
    """Track inferred protocol from edits; suggest /set-workspace on cross-protocol."""
    session_id = resolve_session_id()
    state_dir = os.path.join(workspace_root, ".observability", "sessions", session_id)
    os.makedirs(state_dir, exist_ok=True)
    state_path = os.path.join(state_dir, "inferred-protocol.json")

    current_layer = _get_file_layer(file_path, workspace_root, ivyworkspace_config)
    if not current_layer:
        emit_noop("PreToolUse", "file has no resolvable workspace layer")
        return

    try:
        with open(state_path) as f:
            inferred = json.load(f)
    except (OSError, json.JSONDecodeError):
        inferred = {}

    previous_layer = inferred.get("inferred_layer")

    if previous_layer and previous_layer != current_layer:
        # Cross-protocol edit — warn
        emit_hook_output(
            "PreToolUse",
            system_message=(
                f"[ivy-workspace-scope] cross-protocol edit detected "
                f"({previous_layer} → {current_layer})"
            ),
            additional_context=(
                f"You are editing files across different protocol layers "
                f"('{previous_layer}' and '{current_layer}'). "
                f"Cross-protocol editing without workspace isolation may cause "
                f"include collisions.\n"
                f"Suggestion: /set-workspace <protocol> to restrict edits."
            ),
        )
    elif not previous_layer:
        # First edit — suggest
        group = _find_group_for_layer(current_layer, ivyworkspace_config)
        if group:
            emit_hook_output(
                "PreToolUse",
                system_message=(
                    f"[ivy-workspace-scope] no active workspace; "
                    f"first edit in layer '{current_layer}' (group {group})"
                ),
                additional_context=(
                    f"No active workspace set. This file is in the '{current_layer}' layer.\n"
                    f"Consider /set-workspace {group} to enable edit isolation."
                ),
            )
        else:
            emit_noop(
                "PreToolUse",
                f"first edit in layer '{current_layer}' has no group mapping",
            )
    else:
        emit_noop(
            "PreToolUse",
            f"continuing edits in inferred layer '{current_layer}'",
        )

    # Update inferred state
    inferred["inferred_layer"] = current_layer
    try:
        with open(state_path, "w") as f:
            json.dump(inferred, f)
    except OSError:
        pass


if __name__ == "__main__":
    main()
