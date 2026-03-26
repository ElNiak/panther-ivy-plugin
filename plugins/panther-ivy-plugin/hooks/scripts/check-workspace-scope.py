#!/usr/bin/env python3
"""PreToolUse hook: check if file edit is within active workspace scope."""

import json
import os
import sys


def main():
    # Read hook input from stdin
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        # Can't parse input — allow (fail open)
        return

    tool_input = hook_input.get("tool_input", {})
    file_path = tool_input.get("file_path", "")

    if not file_path:
        return  # No file path — allow

    # Only check .ivy files
    if not file_path.endswith(".ivy"):
        return  # Non-ivy files are unconstrained

    # Check if stdlib
    if os.sep + os.path.join("ivy", "include") in file_path:
        return  # Stdlib always allowed

    # Load workspace state
    workspace_root = os.environ.get("IVY_WORKSPACE_ROOT", "")
    if not workspace_root:
        return  # No workspace detected — allow

    state_file = os.path.join(workspace_root, ".ivy-workspace-state.json")

    try:
        with open(state_file) as f:
            state = json.load(f)
    except (OSError, json.JSONDecodeError):
        # Missing or corrupt state file — allow (fail open)
        # But do progressive narrowing
        _progressive_narrowing(file_path, workspace_root)
        return

    active_group = state.get("active_group")
    active_layers = set(state.get("active_layers", []))
    set_by = state.get("set_by", "unknown")

    if not active_layers:
        # No active workspace — do progressive narrowing
        _progressive_narrowing(file_path, workspace_root)
        return

    # Determine file's layer from .ivyworkspace
    file_layer = _get_file_layer(file_path, workspace_root)

    if file_layer is None:
        # File not in any layer — warn but allow
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "additionalContext": (
                    "This file has no registered workspace layer. If creating a new protocol:\n"
                    " 1. Create protocol-testing/<name>/.ivyworkspace marker\n"
                    " 2. Or run scripts/generate_protocol_markers.py after adding to root .ivyworkspace"
                ),
            }
        }
        print(json.dumps(output))
        return

    if file_layer in active_layers:
        return  # In scope — allow

    # BLOCKED — file is outside active workspace
    # Find which group this file belongs to for the suggestion
    file_group = _find_group_for_layer(file_layer, workspace_root)

    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": (
                f"BLOCKED: '{os.path.basename(file_path)}' is in layer '{file_layer}' "
                f"(workspace group: {file_group or 'unknown'}).\n"
                f"Active workspace: '{active_group}' (set by: {set_by}).\n"
                f"To allow: /set-workspace {file_group or file_layer} | /clear-workspace"
            ),
        }
    }
    print(json.dumps(output))


def _get_file_layer(file_path, workspace_root):
    """Determine which workspace layer a file belongs to by checking .ivyworkspace."""
    ivyworkspace_path = os.path.join(workspace_root, ".ivyworkspace")
    try:
        with open(ivyworkspace_path) as f:
            config = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None

    # Normalize file path relative to workspace root
    abs_path = os.path.abspath(file_path)
    try:
        rel_path = os.path.relpath(abs_path, workspace_root)
    except ValueError:
        return None

    # Check each layer's include_paths
    for layer in config.get("workspace_layers", []):
        for include_path in layer.get("include_paths", []):
            if rel_path.startswith(include_path):
                return layer["id"]

    return None


def _find_group_for_layer(layer_id, workspace_root):
    """Find which workspace_group contains a layer."""
    ivyworkspace_path = os.path.join(workspace_root, ".ivyworkspace")
    try:
        with open(ivyworkspace_path) as f:
            config = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None

    for group_name, group_layers in config.get("workspace_groups", {}).items():
        if layer_id in group_layers:
            return group_name
    return None


def _resolve_session_id(hook_input=None):
    """Resolve Claude session id — delegates to ivy-lsp canonical resolver."""
    try:
        from ivy_lsp.infra.observability.session import resolve_session_id
        return resolve_session_id(hook_payload=hook_input)
    except ImportError:
        pass
    # Fallback if ivy-lsp not importable
    if hook_input:
        payload_session = str(hook_input.get("session_id", "")).strip()
        if payload_session:
            return payload_session
    return os.environ.get("IVY_SESSION_ID", "unknown")


def _progressive_narrowing(file_path, workspace_root):
    """Track inferred protocol from edits; suggest /set-workspace on cross-protocol."""
    session_id = _resolve_session_id()
    tmpdir = os.environ.get("TMPDIR", "/tmp")
    state_path = os.path.join(tmpdir, f"ivy-inferred-protocol-{session_id}.json")

    current_layer = _get_file_layer(file_path, workspace_root)
    if not current_layer:
        return

    try:
        with open(state_path) as f:
            inferred = json.load(f)
    except (OSError, json.JSONDecodeError):
        inferred = {}

    previous_layer = inferred.get("inferred_layer")

    if previous_layer and previous_layer != current_layer:
        # Cross-protocol edit — warn
        output = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "additionalContext": (
                    f"You are editing files across different protocol layers "
                    f"('{previous_layer}' and '{current_layer}'). "
                    f"Cross-protocol editing without workspace isolation may cause "
                    f"include collisions.\n"
                    f"Suggestion: /set-workspace <protocol> to restrict edits."
                ),
            }
        }
        print(json.dumps(output))
    elif not previous_layer:
        # First edit — suggest
        group = _find_group_for_layer(current_layer, workspace_root)
        if group:
            output = {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "additionalContext": (
                        f"No active workspace set. This file is in the '{current_layer}' layer.\n"
                        f"Consider /set-workspace {group} to enable edit isolation."
                    ),
                }
            }
            print(json.dumps(output))

    # Update inferred state
    inferred["inferred_layer"] = current_layer
    try:
        with open(state_path, "w") as f:
            json.dump(inferred, f)
    except OSError:
        pass


if __name__ == "__main__":
    main()
