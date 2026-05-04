#!/usr/bin/env python3
"""PostToolUse hook on the ivy_workspace MCP tool: surface workspace changes.

After every ``ivy_workspace(action=...)`` MCP call, compare the current
state file against the last value cached for the statusline. If they
differ, refresh the cache and emit a T3 state-change banner so the user
sees the new workspace inline. If they match (set-with-same-target,
get/list calls), no-op.

The hook does not inspect the action field. Suppression of redundant
calls falls out of the ``prev == new`` comparison; ``clear`` is just
``new == ""`` and renders ``(none)``.

T3 template per ``output-style.md`` § "State-persistence message
templates": ``[ivy-workspace] active workspace: <new> (was: <prev>)``.

Always exits 0. Hook timeouts must never block user actions.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.hook_utils import (  # noqa: E402
    emit_hook_output,
    emit_noop,
    read_stdin,
    resolve_workspace_state_path,
)
import lib.statusline_cache as statusline_cache  # noqa: E402


def _read_active_group(state_path: str | None) -> tuple[str, str | None]:
    """Return (active_group, error_msg).

    ``active_group`` is ``""`` when the file is missing (expected after
    ``ivy_workspace(action="clear")``). ``error_msg`` is non-None only
    when the file exists but cannot be parsed; the caller emits a WARN.
    """
    if state_path is None:
        return "", None
    try:
        data = json.loads(Path(state_path).read_text())
    except (OSError, json.JSONDecodeError) as exc:
        return "", f"{type(exc).__name__}: {exc}"
    if not isinstance(data, dict):
        return "", "state file root is not a JSON object"
    return str(data.get("active_group", "") or ""), None


def main() -> None:
    _ = read_stdin()  # consume stdin even though payload not needed
    cwd = os.getcwd()
    state_path = resolve_workspace_state_path(cwd)
    new_group, err = _read_active_group(state_path)

    if err is not None:
        emit_hook_output(
            "PostToolUse",
            system_message=(
                f"[ivy-workspace] WARN: state file unreadable at "
                f"{state_path}: {err}"
            ),
        )
        return

    # The `workspace.protocol` section tracks "what was the last-seen
    # active group" — it's cross-protocol metadata, not per-protocol state.
    # Pin it to the `default` partition explicitly so the diff against
    # `new_group` is correct across switches: writing it to whatever
    # partition `_resolve_active_group()` returns would store the value
    # under the *new* group's bucket and lose visibility of the prior one.
    cache_section = (
        statusline_cache.read_section_from_hook("workspace", active_group="default")
        or {}
    )
    prev_group = str(cache_section.get("protocol", "") or "")

    if prev_group == new_group:
        emit_noop("PostToolUse", "workspace unchanged")
        return

    statusline_cache.update_from_hook(
        "workspace", {"protocol": new_group}, active_group="default"
    )

    new_label = new_group or "(none)"
    prev_label = prev_group or "(none)"
    emit_hook_output(
        "PostToolUse",
        system_message=(
            f"[ivy-workspace] active workspace: {new_label} "
            f"(was: {prev_label})"
        ),
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # last-ditch safety net; hook must not crash
        emit_hook_output(
            "PostToolUse",
            system_message=f"[ivy-workspace] WARN: hook error: {type(exc).__name__}",
        )
