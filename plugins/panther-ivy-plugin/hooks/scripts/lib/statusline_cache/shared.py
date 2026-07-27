"""Shared (workspace-scoped) statusline cache writer and readers.

Handles the active_group-keyed ``statusline.json`` file with fcntl locking
for cross-process serialization of read-modify-write sequences.
"""

# pyright: reportMissingTypeArgument=false
from __future__ import annotations

import fcntl
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from lib.statusline_cache.paths import (
    CACHE_VERSION,
    _normalize_active_group,
    _resolve_active_group,
    cache_path_for,
)

_SECTIONS_WITH_TIMESTAMP = frozenset({"mcp", "lsp"})


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_cache(path: Path) -> dict:
    """Read and return the cache JSON, or a fresh skeleton if missing/corrupt.

    Assumes the caller already holds the sibling ``statusline.lock`` exclusive
    lock; no per-file lock is taken here because ``os.replace`` atomicity
    already prevents torn reads of the JSON body.
    """
    if not path.exists():
        return {"version": CACHE_VERSION}
    try:
        with open(path) as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {"version": CACHE_VERSION}
        if data.get("version") != CACHE_VERSION:
            return {"version": CACHE_VERSION}
        return data
    except (OSError, json.JSONDecodeError):
        return {"version": CACHE_VERSION}


def _atomic_write(path: Path, data: dict) -> None:
    """Write ``data`` to ``path`` atomically via tempfile + rename.

    Assumes the caller holds the sibling ``statusline.lock`` exclusive lock.
    The ``os.replace`` at the end is itself atomic, so readers without the
    lock still observe either the pre-write or post-write file — never a
    partial write.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=".statusline-", suffix=".json.tmp", dir=str(path.parent)
    )
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, separators=(",", ":"))
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_name, path)
    except OSError:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass


def _with_cache_lock(path: Path, fn: "Callable[[], None]") -> None:
    """Run ``fn()`` while holding an exclusive lock on a sibling lockfile.

    Cross-process serialization of the read-modify-write sequence. Without
    this, two hooks firing in the same Claude turn (e.g. SessionStart +
    PreToolUse) could each read an empty cache, each merge only their own
    section, and each overwrite the other's section via ``os.replace`` —
    silently losing updates.

    Args:
        path: Cache file path. The lock is taken on ``<path>.lock``.
        fn: Zero-arg callable executed while the lock is held.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_suffix(path.suffix + ".lock")
    with open(lock_path, "a") as lockf:
        fcntl.flock(lockf.fileno(), fcntl.LOCK_EX)
        try:
            return fn()
        finally:
            fcntl.flock(lockf.fileno(), fcntl.LOCK_UN)


def update_sections(
    workspace_root: str,
    sections: dict,
    *,
    active_group: str | None = None,
) -> None:
    """Atomically merge multiple sections into the cache in one write.

    Hooks that touch several sections at once (e.g. setting both ``workflow``
    and ``workspace.protocol`` when a skill activates) should use this rather
    than calling :func:`update_section` repeatedly — it avoids re-reading the
    cache file per section and collapses the work into one lock acquisition.

    Args:
        workspace_root: Absolute path to the Ivy workspace root.
        sections: Mapping from section name to the fields to merge into it.
            Sections in :data:`_SECTIONS_WITH_TIMESTAMP` receive
            ``last_checked_at`` automatically when not supplied.
        active_group: The current ``ivy_workspace`` selection. When ``None``
            the cache write goes to the :data:`_DEFAULT_GROUP` partition.
    """
    if not workspace_root or not sections:
        return
    try:
        path = cache_path_for(workspace_root, active_group)

        def _apply() -> None:
            cache = _read_cache(path)
            for section, data in sections.items():
                if not section or not isinstance(data, dict):
                    continue
                existing = cache.get(section)
                merged = {**existing, **data} if isinstance(existing, dict) else dict(data)
                if section in _SECTIONS_WITH_TIMESTAMP and "last_checked_at" not in merged:
                    merged["last_checked_at"] = _now_iso()
                cache[section] = merged
            cache["version"] = CACHE_VERSION
            _atomic_write(path, cache)

        _with_cache_lock(path, _apply)
    except Exception:
        pass


def update_section(
    workspace_root: str,
    section: str,
    data: dict,
    *,
    active_group: str | None = None,
) -> None:
    """Merge ``data`` into ``section`` of the workspace's statusline cache.

    The cache file is created on first write. Concurrent writers from
    different hooks serialize on a sibling ``statusline.lock`` file so that
    two simultaneous writes to different sections do not silently overwrite
    each other.

    Sections in :data:`_SECTIONS_WITH_TIMESTAMP` automatically receive a
    ``last_checked_at`` field set to the current UTC time unless the caller
    already provided one. Callers needing freshness tracking for other
    sections should include the field explicitly.

    Args:
        workspace_root: Absolute path to the Ivy workspace root.
        section: Top-level cache key (``"workspace"``, ``"workflow"``,
            ``"mcp"``, ``"lsp"``, ``"test_file"``).
        data: Fields to set on the section. Replaces any existing value for
            the same keys; unspecified keys on the prior section are preserved.
        active_group: The current ``ivy_workspace`` selection (e.g. ``"bgp"``).
            When ``None`` the cache write goes to the :data:`_DEFAULT_GROUP`
            partition; same-protocol sessions then share state while different
            protocols stay isolated.
    """
    if not workspace_root or not section:
        return
    try:
        path = cache_path_for(workspace_root, active_group)

        def _apply() -> None:
            cache = _read_cache(path)
            existing = cache.get(section)
            merged = {**existing, **data} if isinstance(existing, dict) else dict(data)
            if section in _SECTIONS_WITH_TIMESTAMP and "last_checked_at" not in merged:
                merged["last_checked_at"] = _now_iso()
            cache[section] = merged
            cache["version"] = CACHE_VERSION
            _atomic_write(path, cache)

        _with_cache_lock(path, _apply)
    except Exception:
        # Statusline cache is best-effort; never let it break a hook.
        pass


def clear_section(
    workspace_root: str,
    section: str,
    *,
    active_group: str | None = None,
) -> None:
    """Remove ``section`` from the workspace's statusline cache.

    Hooks use this when they want a section to fall back to the cold-start
    visual (no key set → renderer shows the dim ``?`` or skips the segment)
    without wiping the entire cache (which :func:`clear_cache` does and
    which would lose unrelated keys like ``workspace`` and ``active_skill``).

    No-op when the cache file does not yet exist or already lacks the
    section. Acquires the same sibling lockfile as :func:`update_section`
    so a concurrent writer in a different hook cannot race a partial read.

    Args:
        workspace_root: Absolute path to the Ivy workspace root.
        section: Top-level cache key to remove.
        active_group: The current ``ivy_workspace`` selection. When ``None``
            the clear targets the :data:`_DEFAULT_GROUP` partition.
    """
    if not workspace_root or not section:
        return
    try:
        path = cache_path_for(workspace_root, active_group)
        if not path.exists():
            return

        def _apply() -> None:
            cache = _read_cache(path)
            if section not in cache:
                return
            del cache[section]
            cache["version"] = CACHE_VERSION
            _atomic_write(path, cache)

        _with_cache_lock(path, _apply)
    except Exception:
        # Statusline cache is best-effort; never let it break a hook.
        pass


def _resolve_workspace_root() -> str:
    """Resolve the panther_ivy directory without importing hook_utils.

    hook_utils uses PEP 604 (``dict | None``) annotations which fail at
    module-import time on Python < 3.10. This helper inlines the walk-up
    logic so statusline cache updates work under any Python that can
    import the standard library — the plugin's deployed runtime is
    3.10+, but nothing here should rely on that.

    Returns:
        Absolute path to the panther_ivy directory containing
        ``protocol-testing/``, or ``""`` when not found.
    """
    ws_env = os.environ.get("IVY_WORKSPACE_ROOT", "").strip()
    if ws_env and os.path.isdir(os.path.join(ws_env, "protocol-testing")):
        return ws_env

    check = os.getcwd()
    for _ in range(10):
        candidate = os.path.join(
            check, "panther", "plugins", "services", "testers", "panther_ivy"
        )
        if os.path.isdir(os.path.join(candidate, "protocol-testing")):
            return candidate
        if os.path.basename(check) == "panther_ivy" and \
                os.path.isdir(os.path.join(check, "protocol-testing")):
            return check
        parent = os.path.dirname(check)
        if parent == check:
            break
        check = parent
    return ""


def update_from_hook(
    section: str,
    data: dict,
    *,
    active_group: str | None = None,
) -> None:
    """Convenience wrapper for hooks: resolve workspace root and update cache.

    Silently no-ops when the workspace cannot be resolved. Hooks that already
    know their workspace root should prefer :func:`update_section` directly;
    hooks that touch multiple sections should use
    :func:`update_sections_from_hook` to avoid redundant reads.

    The ``active_group`` parameter, when ``None``, lands the write in the
    :data:`_DEFAULT_GROUP` partition — preserving the pre-partitioning
    behaviour for hooks that have not yet been updated to thread an
    explicit ``ivy_workspace`` selection. Hooks that want
    per-protocol partitioning compute the group themselves (typically
    via :func:`_resolve_active_group`) and pass it here, or call
    :func:`update_section` directly.

    Args:
        section: Cache section name (e.g. ``"mcp"``, ``"workflow"``).
        data: Fields to merge into the section.
        active_group: Explicit ``ivy_workspace`` selection. ``None``
            (default) → :data:`_DEFAULT_GROUP` partition.
    """
    ws_root = _resolve_workspace_root()
    if not ws_root:
        return
    update_section(ws_root, section, data, active_group=active_group)


def update_sections_from_hook(
    sections: dict,
    *,
    active_group: str | None = None,
) -> None:
    """Batched variant of :func:`update_from_hook` for multi-section writes."""
    ws_root = _resolve_workspace_root()
    if not ws_root:
        return
    update_sections(ws_root, sections, active_group=active_group)


def read_section_from_hook(
    section: str,
    *,
    active_group: str | None = None,
) -> dict | None:
    """Convenience reader: resolve workspace root and return a cache section.

    Mirrors :func:`update_from_hook` for the read path. Used by hooks
    that need to compare current state against the last-known statusline
    value (e.g. the mid-session workspace-change hook computes
    ``(was: <prev>)`` from this).

    Args:
        section: Cache section name (e.g. ``"workspace"``, ``"mcp"``).
        active_group: Explicit ``ivy_workspace`` selection. ``None``
            (default) reads from the :data:`_DEFAULT_GROUP` partition.

    Returns:
        The section dict, or ``None`` when the workspace cannot be
        resolved or the cache/section is missing or non-dict.
    """
    ws_root = _resolve_workspace_root()
    if not ws_root:
        return None
    try:
        path = cache_path_for(ws_root, active_group)
        cache = _read_cache(path)
        section_data = cache.get(section)
        return section_data if isinstance(section_data, dict) else None
    except Exception:
        return None


def clear_cache(workspace_root: str, active_group: str | None = None) -> None:
    """Delete the cache file for ``workspace_root``. Used for test setup."""
    try:
        path = cache_path_for(workspace_root, active_group)
        path.unlink()
    except (OSError, FileNotFoundError):
        pass
