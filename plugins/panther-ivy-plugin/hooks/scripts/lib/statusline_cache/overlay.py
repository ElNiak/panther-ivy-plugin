"""Per-session statusline overlay APIs.

The overlay lives at
``cache/<wsHash>/<active_group>/sessions/<session_id>/overlay.json`` and
holds session-private statusline state (per-session ``test_file``,
session badge metadata, ``active_skill``). The renderer reads the overlay
first for any segment whose value is session-private, falling back to the
shared cache when missing or stale. Two Claude Code windows in the same
workspace+protocol thus see the same shared segments (workflow, mcp, lsp)
but distinct session-private segments.

Overlay writes use the same fcntl-locked atomic-write discipline as the
shared cache, except the lockfile is a sibling ``overlay.lock`` to prevent
cross-talk between the shared-cache lock and the per-session lock when
both are held in flight.
"""

# pyright: reportMissingTypeArgument=false
from __future__ import annotations

import json

from lib.statusline_cache.paths import (
    CACHE_VERSION,
    _VALID_PATH_COMPONENT_RE,
    _resolve_active_group,
    overlay_path_for,
)
from lib.statusline_cache.shared import (
    _SECTIONS_WITH_TIMESTAMP,
    _atomic_write,
    _now_iso,
    _read_cache,
    _resolve_workspace_root,
    _with_cache_lock,
)


def _validate_session_id(session_id: str) -> bool:
    """Reject empty / unsafe session_id values."""
    if not session_id:
        return False
    return bool(_VALID_PATH_COMPONENT_RE.match(session_id))


def update_overlay(
    workspace_root: str,
    session_id: str,
    sections: dict,
    *,
    active_group: str | None = None,
) -> None:
    """Atomically merge sections into the per-session overlay file.

    Mirrors :func:`update_sections` semantics (per-section dict merge,
    ``last_checked_at`` auto-stamp for sections in
    :data:`_SECTIONS_WITH_TIMESTAMP`) but writes to the per-session
    overlay path. Best-effort: unsafe ``session_id`` values are silently
    dropped so a malformed Claude Code stdin payload cannot escape the
    overlay directory.

    Args:
        workspace_root: Absolute path to the Ivy workspace root.
        session_id: Stable Claude Code session identifier.
        sections: Mapping from section name to the fields to merge.
        active_group: The current ``ivy_workspace`` selection. ``None``
            falls through to :data:`_DEFAULT_GROUP`.
    """
    if not workspace_root or not sections:
        return
    if not _validate_session_id(session_id):
        return
    try:
        path = overlay_path_for(workspace_root, session_id, active_group)

        def _apply() -> None:
            cache = _read_cache(path)
            for section, data in sections.items():
                if not section or not isinstance(data, dict):
                    continue
                existing = cache.get(section)
                merged = (
                    {**existing, **data}
                    if isinstance(existing, dict)
                    else dict(data)
                )
                if (
                    section in _SECTIONS_WITH_TIMESTAMP
                    and "last_checked_at" not in merged
                ):
                    merged["last_checked_at"] = _now_iso()
                cache[section] = merged
            cache["version"] = CACHE_VERSION
            _atomic_write(path, cache)

        _with_cache_lock(path, _apply)
    except Exception:
        # Overlay is best-effort like the shared cache; never break a hook.
        pass


def read_overlay(
    workspace_root: str,
    session_id: str,
    *,
    active_group: str | None = None,
) -> dict | None:
    """Return the entire overlay JSON for one session, or ``None``.

    The renderer's per-session segments call this once per render and
    extract their fields from the returned dict. Missing file, unsafe
    ``session_id``, JSON decode error, version mismatch, or non-dict
    body all return ``None`` so the caller can fall through to the
    shared cache.
    """
    if not workspace_root:
        return None
    if not _validate_session_id(session_id):
        return None
    try:
        path = overlay_path_for(workspace_root, session_id, active_group)
        if not path.exists():
            return None
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, dict):
            return None
        if data.get("version") != CACHE_VERSION:
            return None
        return data
    except (OSError, json.JSONDecodeError):
        return None


def clear_overlay(
    workspace_root: str,
    session_id: str,
    *,
    active_group: str | None = None,
) -> None:
    """Delete the overlay file for one session.

    Used by the SessionStart reaper and by tests. No-op when the file is
    missing or the session_id is unsafe.
    """
    if not workspace_root:
        return
    if not _validate_session_id(session_id):
        return
    try:
        overlay_path_for(workspace_root, session_id, active_group).unlink(
            missing_ok=True
        )
    except OSError:
        pass


def update_overlay_from_hook(session_id: str, sections: dict) -> None:
    """Convenience wrapper: resolve workspace root + active_group and merge.

    Hooks that have a ``session_id`` from stdin (every Claude Code hook
    event includes it; see ``hooks-guide`` docs) should prefer this over
    calling :func:`update_overlay` with a manually-resolved workspace.
    """
    if not _validate_session_id(session_id):
        return
    ws_root = _resolve_workspace_root()
    if not ws_root:
        return
    active_group = _resolve_active_group(ws_root)
    update_overlay(ws_root, session_id, sections, active_group=active_group)


def read_overlay_from_hook(session_id: str) -> dict | None:
    """Convenience reader: resolve workspace root + active_group and read."""
    if not _validate_session_id(session_id):
        return None
    ws_root = _resolve_workspace_root()
    if not ws_root:
        return None
    active_group = _resolve_active_group(ws_root)
    return read_overlay(ws_root, session_id, active_group=active_group)


# Alias used by the bash renderer cache loader (statusline_overlay_load convention)
statusline_overlay_load = read_overlay
