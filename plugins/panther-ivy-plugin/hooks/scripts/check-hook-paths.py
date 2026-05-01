#!/usr/bin/env python3
"""SessionStart self-test: verify every ``hooks.json`` command path exists.

Walks ``hooks.json`` and confirms each script referenced via
``${CLAUDE_PLUGIN_ROOT}/...`` resolves to a real file. Surfaces a single
``[ivy-meta] N hook script(s) missing`` system message when paths are
broken so the user sees the problem at SessionStart instead of mid-turn
when Claude Code's ``Failed with non-blocking status code: bash: …`` lands
during a tool call.

Always exits 0 — this is an advisory surface, not a fail-loud gate. The
runtime already tolerates missing hook paths gracefully (the failed hook
is skipped and the chain continues), so escalating to a hard failure
here would be more disruptive than the underlying problem.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hook_utils import emit_hook_output, emit_noop  # noqa: E402

_CLAUDE_PLUGIN_ROOT_TOKEN = "${CLAUDE_PLUGIN_ROOT}/"


def _extract_script_paths(hooks_json: dict) -> list[str]:
    """Yield each ``${CLAUDE_PLUGIN_ROOT}/...`` script path in hooks.json.

    The ``command`` strings in ``hooks.json`` follow the format
    ``<interpreter> ${CLAUDE_PLUGIN_ROOT}/<rel> [args...]``. We split on
    the token, take the first whitespace-separated word from the remainder,
    and skip any command that does not reference the plugin root.
    """
    paths: list[str] = []
    for entries in hooks_json.get("hooks", {}).values():
        for entry in entries:
            for hook in entry.get("hooks", []):
                command = hook.get("command", "")
                if _CLAUDE_PLUGIN_ROOT_TOKEN not in command:
                    continue
                rel = command.split(_CLAUDE_PLUGIN_ROOT_TOKEN, 1)[1].split()[0]
                paths.append(rel)
    return paths


def main() -> None:
    plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT", "").strip()
    if not plugin_root:
        emit_noop("SessionStart", "CLAUDE_PLUGIN_ROOT not set")
        return

    manifest = Path(plugin_root) / "hooks" / "hooks.json"
    if not manifest.is_file():
        emit_hook_output(
            "SessionStart",
            system_message=f"[ivy-meta] hooks.json not found at {manifest}",
        )
        return

    try:
        data = json.loads(manifest.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        emit_hook_output(
            "SessionStart",
            system_message=f"[ivy-meta] hooks.json unparseable: {exc}",
        )
        return

    missing: list[str] = []
    for rel in _extract_script_paths(data):
        if not (Path(plugin_root) / rel).is_file():
            missing.append(rel)

    if not missing:
        emit_noop("SessionStart", "all hooks.json command paths verified")
        return

    listing = "\n".join(f"  - {p}" for p in missing)
    emit_hook_output(
        "SessionStart",
        system_message=(
            f"[ivy-meta] {len(missing)} hook script(s) missing — "
            "expect 'Failed with non-blocking status code: bash: ...' on "
            "matching events"
        ),
        additional_context=(
            f"hooks.json references {len(missing)} script(s) that do not "
            f"exist on disk:\n{listing}\n"
            "Either restore the missing files or remove the entries from "
            "hooks.json. The runtime continues without them, but the user "
            "sees a per-event error message until they are reconciled."
        ),
    )


if __name__ == "__main__":
    main()
