#!/usr/bin/env python3
"""PreToolUse hook: advisory tip for ivy_verify / ivy_coverage, once per session.

Emits a short `additional_context` tip the first time each annotated tool is
invoked in a session; subsequent calls in the same session exit silently.
Fixes the "Tip: …" prompt-hook noise caused by a PreToolUse prompt block
firing on every call.

State file: <workspace_root>/.observability/sessions/<session_id>/tips-shown.json
Non-blocking: any error path exits 0 so the tool call is never disrupted.
"""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from hook_utils import (
    emit_hook_output,
    get_workspace_root,
    read_stdin,
    resolve_session_id,
)

TIPS = {
    "ivy_verify": (
        'Tip: Consider running ivy_diagnostics(mode="structural") first for '
        "fast structural validation (milliseconds vs seconds). This catches "
        "syntax errors before the heavier formal verification."
    ),
    "ivy_coverage": (
        "Tip: Always scope ivy_coverage with test_file for large workspaces. "
        "Run ivy_diagnostics first. Use mode=stats before mode=matrix."
    ),
}


def _match_tool(tool_name: str) -> str | None:
    """Return the base tool name if the invocation matches an annotated tool."""
    for key in TIPS:
        if key in tool_name:
            return key
    return None


def _state_path(session_id: str) -> Path:
    state_dir = Path(get_workspace_root()) / ".observability" / "sessions" / session_id
    state_dir.mkdir(parents=True, exist_ok=True)
    return state_dir / "tips-shown.json"


def _load_shown(path: Path) -> dict[str, bool]:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text())
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def main() -> None:
    data = read_stdin()
    base_tool = _match_tool(data.get("tool_name", ""))
    if not base_tool:
        return

    session_id = resolve_session_id(data)
    if session_id == "unknown":
        # No reliable session → skip; showing the tip every turn would
        # reintroduce the noise this hook is meant to fix.
        return

    path = _state_path(session_id)
    shown = _load_shown(path)
    if shown.get(base_tool):
        return

    shown[base_tool] = True
    try:
        path.write_text(json.dumps(shown))
    except OSError:
        pass  # non-fatal; the worst case is the tip showing twice

    emit_hook_output("PreToolUse", additional_context=TIPS[base_tool])


if __name__ == "__main__":
    main()
