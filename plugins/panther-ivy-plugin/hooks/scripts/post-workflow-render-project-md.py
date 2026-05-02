#!/usr/bin/env python3
"""PostToolUse hook: regenerate PROJECT.md after ivy_workflow_state set/clear.

Triggered for tool_name matching ``mcp__.*ivy_workflow_state``. Looks up
the active workspace from ``.ivy-workspace-state.json`` (key:
``active_group``) and runs ``scripts/render-project-md.py`` against the
matching ``protocol-testing/<active_group>/`` directory.

Skips silently when:

- ``tool_input.action`` is not ``set`` or ``clear`` (get/list/etc. don't
  change journal-derived state).
- No active workspace.
- The protocol-testing/<workspace>/ directory does not exist.

Per output-style.md state-persistence T2 template, the user-facing
``systemMessage`` is the ``[ivy-project-md]`` marker reporting the path
and outcome. Always exits 0.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hook_utils import (  # noqa: E402
    emit_hook_output,
    read_active_workspace,
    read_stdin,
    resolve_workspace_state_path,
)
from project_md_state import resolve_protocol_dir  # noqa: E402

PLUGIN_ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    payload = read_stdin()
    tool_input = payload.get("tool_input", {}) or {}
    action = tool_input.get("action")
    if action not in {"set", "clear"}:
        return 0

    cwd = os.getcwd()
    workspace = read_active_workspace(resolve_workspace_state_path(cwd))
    if not workspace:
        emit_hook_output(
            "PostToolUse",
            system_message="[ivy-project-md] no-op (no active workspace).",
        )
        return 0

    protocol_dir = resolve_protocol_dir(Path(cwd), workspace)
    if not protocol_dir.is_dir():
        emit_hook_output(
            "PostToolUse",
            system_message=(
                f"[ivy-project-md] no-op (protocol-testing/{workspace}/ "
                "missing)."
            ),
        )
        return 0

    script = PLUGIN_ROOT / "scripts" / "render-project-md.py"
    proc = subprocess.run(
        [sys.executable, str(script), "--protocol-dir", str(protocol_dir)],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        emit_hook_output(
            "PostToolUse",
            system_message=(
                f"[ivy-project-md] WARN: render-project-md failed for {workspace}: "
                f"{proc.stderr.strip()[:200]}"
            ),
        )
        return 0

    emit_hook_output(
        "PostToolUse",
        system_message=(
            f"[ivy-project-md] PROJECT.md updated for {workspace} "
            f"at protocol-testing/{workspace}/PROJECT.md"
        ),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
