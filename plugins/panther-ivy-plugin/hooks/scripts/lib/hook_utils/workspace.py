#!/usr/bin/env python3
"""Workspace-root resolution, workspace state I/O, and plugin-root helpers."""

from __future__ import annotations

import functools
import json
import os
from pathlib import Path


def get_workspace_root() -> str:
    """Get workspace root from environment, with walk-up fallback."""
    ws_root = os.environ.get("IVY_WORKSPACE_ROOT", "").strip()
    if ws_root:
        return ws_root
    check = os.getcwd()
    for _ in range(10):
        candidate = os.path.join(check, "panther", "plugins", "services",
                                 "testers", "panther_ivy")
        if os.path.isdir(os.path.join(candidate, "protocol-testing")):
            return candidate
        parent = os.path.dirname(check)
        if parent == check:
            break
        check = parent
    return os.getcwd()


def resolve_workspace_state_path(detected_root: os.PathLike[str] | str) -> str | None:
    """Return the first existing .ivy-workspace-state.json across two candidate roots.

    The MCP ``ivy_workspace`` tool writes the state file at the
    panther_ivy submodule root (its LSP scope root), while SessionStart
    often resolves the session's detected workspace to the PANTHER
    project root one or more directories above. Callers that read
    workspace state cannot assume a single canonical location, so this
    helper centralises the two-root walk: every reader (SessionStart
    banner, mid-session change hook, future statusline poller)
    converges on the same resolution rule.

    Args:
        detected_root: The session's detected workspace root, typically
            the PANTHER project root or a standalone Ivy project. Path
            or str.

    Returns:
        Absolute path to the first existing state file, or ``None`` if
        neither candidate resolves.
    """
    detected = str(detected_root)
    panther_ivy = get_workspace_root()
    for candidate in (detected, panther_ivy):
        path = os.path.join(candidate, ".ivy-workspace-state.json")
        if os.path.isfile(path):
            return path
    return None


def read_active_workspace(state_path: str | None) -> str:
    """Read the active workspace name from the workspace-state JSON file.

    Centralised so every reader (notify-workspace-change.py, the
    PROJECT.md PostToolUse hook, the statusline segment) converges on
    the same parser. Returns the empty string when the file is missing,
    unparseable, or has no ``active_group`` set — callers that need to
    distinguish "no workspace" from "parse error" can do their own read.

    Args:
        state_path: Path returned by :func:`resolve_workspace_state_path`,
            or None when no candidate state file exists. Both inputs map
            to the empty string.

    Returns:
        The active workspace name, or ``""`` when no workspace is set.
    """
    if state_path is None:
        return ""
    try:
        data = json.loads(Path(state_path).read_text())
    except (OSError, json.JSONDecodeError):
        return ""
    if not isinstance(data, dict):
        return ""
    return str(data.get("active_group", "") or "").strip()


def resolve_log_dir(session_id: str) -> str:
    """Determine the log directory for a session.

    Priority:
      1. $IVY_OBSERVABILITY_DIR/sessions/<session_id>/
      2. $IVY_WORKSPACE_ROOT/.observability/sessions/<session_id>/
      3. /tmp/ivy-observability/sessions/<session_id>/

    Returns:
        Absolute path string to the session log directory.
    """
    explicit = os.environ.get("IVY_OBSERVABILITY_DIR", "").strip()
    if explicit:
        return os.path.join(explicit, "sessions", session_id)

    workspace = os.environ.get("IVY_WORKSPACE_ROOT", "").strip()
    if workspace:
        return os.path.join(workspace, ".observability", "sessions", session_id)

    return os.path.join("/tmp/ivy-observability", "sessions", session_id)


@functools.lru_cache(maxsize=1)
def resolve_active_group_for_hook() -> str | None:
    """Resolve the current ``ivy_workspace`` selection for partition routing.

    Reads ``<workspace_root>/.ivy-workspace-state.json::active_group`` via
    :mod:`statusline_cache` and returns the validated group name, or
    ``None`` (which the cache layer maps to the ``default`` partition)
    when the workspace cannot be resolved.

    Hooks that update partition-aware statusline cache sections call this
    to compute the ``active_group`` argument once per process invocation;
    the ``lru_cache`` ensures repeated calls within a single hook
    subprocess do not re-walk the cwd or re-parse the JSON state file.
    Each Claude Code hook spawns a fresh subprocess so the cache is bound
    to one hook invocation and there is no test-isolation hazard.
    """
    # Local import keeps the dependency one-way: statusline_cache imports
    # nothing from hook_utils, hook_utils imports statusline_cache lazily
    # so a circular bootstrap path stays impossible.
    from lib.statusline_cache import _resolve_active_group, _resolve_workspace_root

    ws = _resolve_workspace_root()
    return _resolve_active_group(ws) if ws else None
