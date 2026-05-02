#!/usr/bin/env python3
"""SessionStart hook: mirror canonical active-workflow into statusline cache.

The per-workspace statusline cache JSON at
``~/.claude/panther-ivy-plugin/cache/<sha1>/statusline.json`` holds the
``workflow.*`` section that the statusline ``wf:`` segment renders. Cache
writes are event-driven (workflow transitions, skill invocations, MCP
probes) and never re-read from the canonical source-of-truth at session
boundaries. If the cache was last written before the active-workflow YAML
changed (e.g. across a manual edit, a ``migrate_legacy_workflow.py`` run,
or a several-day gap with no workflow transitions), the statusline keeps
rendering the stale token indefinitely.

This hook closes that gap by mirroring the active-workflow YAML into the
cache on every SessionStart. It is a *mirror*, not a normalizer: per
``.claude/rules/journaling-contract.md`` §9 and
``feedback_no_backward_compat_shims``, hooks must not silently rewrite
legacy ``workflow-*`` names. If the YAML holds a canonical name (in
``workflow_state._KNOWN_WORKFLOWS``) the cache is updated. If the YAML
holds a legacy or unknown value the cache ``workflow`` section is cleared
so the statusline falls back to its cold-start visual, and the user is
prompted to run ``scripts/migrate_legacy_workflow.py``.

Order-relative-to-cleanup-stale-workflow: this hook is registered AFTER
``cleanup-stale-workflow.py`` so it observes the post-cleanup YAML state.
Stale cleanups happen first; the mirror reflects whatever survives.
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(
    0,
    os.path.join(os.environ.get("CLAUDE_PLUGIN_ROOT", "."), "hooks", "scripts"),
)

from hook_utils import emit_hook_output, emit_noop  # noqa: E402
from statusline_cache import (  # noqa: E402
    _resolve_workspace_root,
    cache_path_for,
    clear_section,
    update_section,
)
from workflow_state import (  # noqa: E402
    _KNOWN_WORKFLOWS,
    find_protocol_dir,
    get_active_workflow,
)


def _read_cache_workflow(workspace_root: str) -> dict | None:
    """Return the existing cache ``workflow`` section, or ``None``."""
    path = cache_path_for(workspace_root)
    if not path.exists():
        return None
    try:
        with open(path) as fh:
            data = json.load(fh)
        section = data.get("workflow")
        return section if isinstance(section, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def main() -> None:
    workspace_root = _resolve_workspace_root()
    if not workspace_root:
        emit_noop(
            "SessionStart",
            "no panther_ivy workspace detected; skipping statusline-cache mirror",
        )
        return

    protocol_dir = find_protocol_dir()
    if not protocol_dir:
        emit_noop(
            "SessionStart",
            "no protocol directory detected; skipping statusline-cache mirror",
        )
        return

    active = get_active_workflow(protocol_dir)
    cache_workflow = _read_cache_workflow(workspace_root)
    cache_path = cache_path_for(workspace_root)

    if not active:
        if cache_workflow:
            clear_section(workspace_root, "workflow")
            emit_hook_output(
                "SessionStart",
                additional_context=(
                    "Cleared stale 'workflow' section from statusline cache "
                    f"({cache_path}); no active-workflow YAML present."
                ),
                system_message=(
                    f"[ivy-statusline] cleared stale workflow from {cache_path} "
                    "(no active-workflow YAML)"
                ),
            )
        else:
            emit_noop(
                "SessionStart",
                "no active-workflow YAML and no cache workflow section to mirror",
            )
        return

    yaml_workflow = str(active.get("workflow", "")).strip()
    if not yaml_workflow:
        emit_noop(
            "SessionStart",
            "active-workflow YAML missing 'workflow' field; nothing to mirror",
        )
        return

    if yaml_workflow not in _KNOWN_WORKFLOWS:
        if cache_workflow is not None:
            clear_section(workspace_root, "workflow")
        emit_hook_output(
            "SessionStart",
            additional_context=(
                f"Active-workflow YAML at {protocol_dir}/.panther-ivy/active-workflow "
                f"holds non-canonical name '{yaml_workflow}'. The statusline 'workflow' "
                "section was cleared rather than render an unknown name. Run "
                "`python3 ${CLAUDE_PLUGIN_ROOT}/scripts/migrate_legacy_workflow.py` to "
                "migrate legacy YAMLs to canonical names."
            ),
            system_message=(
                f"[ivy-statusline] non-canonical workflow '{yaml_workflow}' detected; "
                f"cleared cache section in {cache_path}"
            ),
        )
        return

    update_section(
        workspace_root,
        "workflow",
        {
            "name": yaml_workflow,
            "phase": str(active.get("phase", "init")),
            "invocation_depth": int(active.get("invocation_depth", 0) or 0),
            "caller": active.get("caller"),
            "started": active.get("started"),
        },
    )

    if cache_workflow and cache_workflow.get("name") != yaml_workflow:
        emit_hook_output(
            "SessionStart",
            additional_context=(
                f"Statusline cache workflow synced "
                f"'{cache_workflow.get('name')}' -> '{yaml_workflow}' in {cache_path}."
            ),
            system_message=(
                f"[ivy-statusline] workflow: {yaml_workflow} "
                f"(was: {cache_workflow.get('name')})"
            ),
        )
    else:
        emit_noop(
            "SessionStart",
            f"statusline cache already mirrors active-workflow ({yaml_workflow})",
        )


if __name__ == "__main__":
    main()
