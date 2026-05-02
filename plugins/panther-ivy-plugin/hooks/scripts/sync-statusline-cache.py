#!/usr/bin/env python3
"""SessionStart + PostToolUse hook: mirror active-workflow into statusline cache.

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
cache on two events:

* **SessionStart** — runs once per session, after
  ``cleanup-stale-workflow.py`` has had a chance to delete stale
  active-workflow files. The mirror reflects whatever survives.
* **PostToolUse** with matcher ``mcp__.*ivy_workflow_state`` — runs on
  every ``ivy_workflow_state(action="set"|"clear")`` MCP call, so a
  mid-session workflow transition is reflected in the statusline before
  the next turn-boundary render. Without this leg the cache stays at
  its SessionStart value until the next session.

The hook is a *mirror*, not a normalizer: per
``.claude/rules/journaling-contract.md`` §9 and
``feedback_no_backward_compat_shims``, hooks must not silently rewrite
legacy ``workflow-*`` names. If the YAML holds a canonical name (in
``workflow_state._KNOWN_WORKFLOWS``) the cache is updated. If the YAML
holds a legacy or unknown value the cache ``workflow`` section is cleared
so the statusline falls back to its cold-start visual, and the user is
prompted to run ``scripts/migrate_legacy_workflow.py``.

The hookEventName in the emitted JSON envelope is detected from stdin
so a single script services both delivery paths without duplication.
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(
    0,
    os.path.join(os.environ.get("CLAUDE_PLUGIN_ROOT", "."), "hooks", "scripts"),
)

from hook_utils import (  # noqa: E402
    VALID_EVENT_NAMES,
    emit_hook_output,
    emit_noop,
    read_stdin,
)
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


def _resolve_event_name(hook_input: dict) -> str:
    """Pick the hookEventName for emit envelopes.

    Claude Code passes ``hook_event_name`` (snake_case) in the stdin
    payload of every hook fire. When the hook is invoked manually with
    ``< /dev/null`` (CLI smoke tests, the legacy invocation pattern from
    before the PostToolUse leg was added), the payload is empty — fall
    back to ``"SessionStart"`` so historical call sites and the
    backward-compatible behaviour keep working. Any value not in the
    canonical ``VALID_EVENT_NAMES`` set falls back to ``"SessionStart"``
    rather than raising — emit_hook_output already validates strictly,
    so the fallback only protects against a typo in the payload.
    """
    raw = str(hook_input.get("hook_event_name", "")).strip()
    return raw if raw in VALID_EVENT_NAMES else "SessionStart"


def main() -> None:
    hook_input = read_stdin()
    event_name = _resolve_event_name(hook_input)

    workspace_root = _resolve_workspace_root()
    if not workspace_root:
        emit_noop(
            event_name,
            "no panther_ivy workspace detected; skipping statusline-cache mirror",
        )
        return

    protocol_dir = find_protocol_dir()
    if not protocol_dir:
        emit_noop(
            event_name,
            "no protocol directory detected; skipping statusline-cache mirror",
        )
        return

    active = get_active_workflow(protocol_dir)
    cache_workflow = _read_cache_workflow(workspace_root)
    cache_path = cache_path_for(workspace_root)

    if not active:
        if cache_workflow:
            prev_name = cache_workflow.get("name") or "<unknown>"
            clear_section(workspace_root, "workflow")
            emit_hook_output(
                event_name,
                additional_context=(
                    "Cleared stale 'workflow' section from statusline cache "
                    f"({cache_path}); no active-workflow YAML present."
                ),
                system_message=(
                    f"[ivy-statusline] workflow: <none> (was: {prev_name}) "
                    f"cleared in {cache_path}"
                ),
            )
        else:
            emit_noop(
                event_name,
                "no active-workflow YAML and no cache workflow section to mirror",
            )
        return

    yaml_workflow = str(active.get("workflow", "")).strip()
    if not yaml_workflow:
        emit_noop(
            event_name,
            "active-workflow YAML missing 'workflow' field; nothing to mirror",
        )
        return

    if yaml_workflow not in _KNOWN_WORKFLOWS:
        cleared = cache_workflow is not None
        if cleared:
            clear_section(workspace_root, "workflow")
        action_phrase = (
            f"cleared cache section in {cache_path}"
            if cleared
            else "no cache section to clear"
        )
        ac_phrase = (
            "section was cleared rather than render an unknown name"
            if cleared
            else "section is empty so nothing was rendered"
        )
        emit_hook_output(
            event_name,
            additional_context=(
                f"Active-workflow YAML at {protocol_dir}/.panther-ivy/active-workflow "
                f"holds non-canonical name '{yaml_workflow}'. The statusline 'workflow' "
                f"{ac_phrase}. Run "
                "`python3 ${CLAUDE_PLUGIN_ROOT}/scripts/migrate_legacy_workflow.py` to "
                "migrate legacy YAMLs to canonical names."
            ),
            system_message=(
                f"[ivy-statusline] non-canonical workflow '{yaml_workflow}' detected; "
                f"{action_phrase}"
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
            event_name,
            additional_context=(
                f"Statusline cache workflow synced "
                f"'{cache_workflow.get('name')}' -> '{yaml_workflow}' in {cache_path}."
            ),
            system_message=(
                f"[ivy-statusline] workflow: {yaml_workflow} "
                f"(was: {cache_workflow.get('name')})"
            ),
        )
    elif not cache_workflow:
        emit_hook_output(
            event_name,
            additional_context=(
                f"Seeded statusline cache workflow with '{yaml_workflow}' in {cache_path}."
            ),
            system_message=(
                f"[ivy-statusline] workflow: {yaml_workflow} (was: <none>) "
                f"seeded in {cache_path}"
            ),
        )
    else:
        emit_noop(
            event_name,
            f"statusline cache already mirrors active-workflow ({yaml_workflow})",
        )


if __name__ == "__main__":
    main()
