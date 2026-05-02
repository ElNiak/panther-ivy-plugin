#!/usr/bin/env python3
"""Cache writer for the panther-ivy-plugin specialized status bar.

Hooks call :func:`update_section` on events that change statusline-relevant
state (MCP health, LSP indexing, workflow transitions, workspace detection).
The statusline script reads the resulting JSON file and renders segments from
it — the renderer never queries live state.

Cache layout:
    ~/.claude/panther-ivy-plugin/cache/<sha1(workspace_root)[:12]>/<active_group>/statusline.json
    ~/.claude/panther-ivy-plugin/cache/<sha1(workspace_root)[:12]>/<active_group>/sessions/<session_id>/overlay.json

Three orthogonal partitions:

* ``workspace_root`` (sha1) — distinguishes different ``panther_ivy/``
  checkouts on the same machine.
* ``active_group`` — distinguishes which Ivy protocol model the session
  is currently working on (``bgp`` / ``quic`` / ``apt`` / ...). Resolved
  from ``<workspace_root>/.ivy-workspace-state.json::active_group``,
  written by ``ivy_workspace(action="set", target=...)``. Falls back to
  ``"default"`` when no group is set (cleared workspace) or when the
  state file is missing / unreadable / malformed.
* ``session_id`` — distinguishes which Claude Code window owns
  session-private state (badge, last test_file, last skill). Used only
  for the per-session overlay file.

The shared ``statusline.json`` holds segments that are genuinely
workspace-shared (one MCP server, one LSP server, one canonical
workflow per workspace+protocol). The per-session ``overlay.json``
holds session-private segments and falls through to the shared cache
when missing.
"""

# pyright: reportMissingTypeArgument=false
from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

CACHE_VERSION = 1

_DEFAULT_CACHE_ROOT = Path.home() / ".claude" / "panther-ivy-plugin" / "cache"
_SECTIONS_WITH_TIMESTAMP = frozenset({"mcp", "lsp"})

# Sentinel partition for sessions without an explicit ivy_workspace selection.
# Existing pre-partitioning cache files migrate under this name.
_DEFAULT_GROUP = "default"

# Active-group names must be filesystem-safe path components. The canonical
# set the plugin recognizes is {bgp, quic, apt, apt_quic, minip, coap,
# scaffolds}, all of which match this pattern. Anything else (path
# traversal, slashes, empty) collapses to ``_DEFAULT_GROUP`` so a malformed
# .ivy-workspace-state.json cannot escape the cache directory.
_VALID_GROUP_RE = re.compile(r"^[A-Za-z0-9_-]+$")

# Session IDs from Claude Code are UUIDs (e.g. "00893aaf-19fa-41d2-8238-13269b9b3ca0").
# Allow the broader hex-with-dashes-and-underscores form so test fixtures using
# names like ``"test-session-A"`` or ``"sess_alpha"`` also validate.
_VALID_SESSION_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def _cache_root() -> Path:
    """Resolve the cache root directory, honoring the test override env var.

    Returns:
        Absolute path to the directory holding per-workspace cache folders.
    """
    override = os.environ.get("PANTHER_IVY_STATUSLINE_CACHE_ROOT", "").strip()
    if override:
        return Path(override)
    return _DEFAULT_CACHE_ROOT


def _normalize_active_group(active_group: str | None) -> str:
    """Sanitize ``active_group`` for use as a filesystem path component.

    Empty / non-string / unsafe values collapse to :data:`_DEFAULT_GROUP`.
    The validation regex blocks path traversal (``..``), absolute paths,
    and non-printable characters that would let a malformed
    ``.ivy-workspace-state.json`` write outside the cache directory.
    """
    if not active_group or not isinstance(active_group, str):
        return _DEFAULT_GROUP
    if not _VALID_GROUP_RE.match(active_group):
        return _DEFAULT_GROUP
    return active_group


def _resolve_active_group(workspace_root: str) -> str:
    """Return the current ``ivy_workspace`` selection or :data:`_DEFAULT_GROUP`.

    Reads ``<workspace_root>/.ivy-workspace-state.json::active_group`` —
    the canonical state file that ``ivy_workspace(action="set", target=...)``
    writes (see ``submodules/ivy-lsp/.../active_workspace.py:save``). Any
    failure (file missing, unreadable, malformed JSON, missing field, null
    field, or the field failing the safety regex) degrades gracefully to
    :data:`_DEFAULT_GROUP` so a session with no explicit selection still
    gets a deterministic partition.

    Args:
        workspace_root: Absolute path to the Ivy workspace root, typically
            the ``panther_ivy/`` directory.

    Returns:
        Either the validated ``active_group`` from the state file, or
        :data:`_DEFAULT_GROUP` when the state file is unavailable or the
        value is unsafe.
    """
    if not workspace_root:
        return _DEFAULT_GROUP
    state_path = Path(workspace_root) / ".ivy-workspace-state.json"
    if not state_path.is_file():
        return _DEFAULT_GROUP
    try:
        with state_path.open(encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return _DEFAULT_GROUP
    if not isinstance(data, dict):
        return _DEFAULT_GROUP
    return _normalize_active_group(data.get("active_group"))


def cache_path_for(workspace_root: str, active_group: str | None = None) -> Path:
    """Return the cache file path for a workspace root + active-group bucket.

    Args:
        workspace_root: Absolute path to the Ivy workspace root (typically the
            ``panther_ivy/`` directory or a specific ``protocol-testing/<p>/``).
        active_group: The current ``ivy_workspace`` selection (e.g. ``"bgp"``,
            ``"quic"``). When ``None`` or unsafe, falls back to
            :data:`_DEFAULT_GROUP` so a session that never called
            ``ivy_workspace(set)`` still gets a deterministic cache path.

    Returns:
        Absolute path to the bucket's ``statusline.json`` cache file. The
        ``PANTHER_IVY_STATUSLINE_CACHE_PATH`` env override short-circuits
        all path computation and returns the literal override path; tests
        that pre-date partitioning rely on this behaviour.
    """
    override = os.environ.get("PANTHER_IVY_STATUSLINE_CACHE_PATH", "").strip()
    if override:
        return Path(override)

    digest = hashlib.sha1(workspace_root.encode("utf-8")).hexdigest()[:12]
    group = _normalize_active_group(active_group)
    return _cache_root() / digest / group / "statusline.json"


def overlay_path_for(
    workspace_root: str,
    session_id: str,
    active_group: str | None = None,
) -> Path:
    """Return the per-session overlay file path within the active-group bucket.

    The overlay holds session-private statusline state (per-session
    ``test_file``, badge metadata, ``active_skill``) so two Claude Code
    windows in the same workspace+protocol do not overwrite each other's
    transient view. Falls through to :data:`_DEFAULT_GROUP` when
    ``active_group`` is unset, mirroring :func:`cache_path_for`.

    Args:
        workspace_root: Absolute path to the Ivy workspace root.
        session_id: Stable Claude Code session identifier (a UUID like
            ``"00893aaf-19fa-41d2-8238-13269b9b3ca0"``). The
            ``PANTHER_IVY_STATUSLINE_OVERLAY_PATH`` env override
            short-circuits the computation, mirroring
            :data:`PANTHER_IVY_STATUSLINE_CACHE_PATH` for tests.

    Returns:
        Absolute path to ``<wsHash>/<group>/sessions/<session_id>/overlay.json``,
        or the env override when set.
    """
    override = os.environ.get("PANTHER_IVY_STATUSLINE_OVERLAY_PATH", "").strip()
    if override:
        return Path(override)

    digest = hashlib.sha1(workspace_root.encode("utf-8")).hexdigest()[:12]
    group = _normalize_active_group(active_group)
    return (
        _cache_root() / digest / group / "sessions" / session_id / "overlay.json"
    )


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


# ---------------------------------------------------------------------------
# Per-session overlay
# ---------------------------------------------------------------------------
#
# The overlay lives at
# ``cache/<wsHash>/<active_group>/sessions/<session_id>/overlay.json`` and
# holds session-private statusline state (per-session ``test_file``,
# session badge metadata, ``active_skill``). The renderer reads the overlay
# first for any segment whose value is session-private, falling back to the
# shared cache when missing or stale. Two Claude Code windows in the same
# workspace+protocol thus see the same shared segments (workflow, mcp, lsp)
# but distinct session-private segments.
#
# Overlay writes use the same fcntl-locked atomic-write discipline as the
# shared cache, except the lockfile is a sibling ``overlay.lock`` to prevent
# cross-talk between the shared-cache lock and the per-session lock when
# both are held in flight.


def _validate_session_id(session_id: str) -> bool:
    """Reject empty / non-string / unsafe session_id values."""
    if not session_id or not isinstance(session_id, str):
        return False
    return bool(_VALID_SESSION_RE.match(session_id))


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

    Used by the SessionStart reaper (Phase 4) and by tests. No-op when
    the file is missing or the session_id is unsafe.
    """
    if not workspace_root:
        return
    if not _validate_session_id(session_id):
        return
    try:
        path = overlay_path_for(workspace_root, session_id, active_group)
        if path.exists():
            path.unlink()
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


if __name__ == "__main__":  # pragma: no cover
    import argparse

    parser = argparse.ArgumentParser(description="Update a statusline cache section.")
    ws_group = parser.add_mutually_exclusive_group(required=True)
    ws_group.add_argument("--workspace", help="Explicit workspace root path")
    ws_group.add_argument(
        "--auto-workspace",
        action="store_true",
        help="Resolve workspace via hook_utils.get_workspace_root()",
    )
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument(
        "--section",
        help="Single-section mode: cache section name (requires --data)",
    )
    mode_group.add_argument(
        "--sections",
        help="Multi-section mode: JSON object mapping section names to fields",
    )
    parser.add_argument(
        "--data",
        help="JSON-encoded data to merge (single-section mode only)",
    )
    args = parser.parse_args()

    try:
        if args.sections is not None:
            batch = json.loads(args.sections)
            if not isinstance(batch, dict):
                raise SystemExit("--sections must be a JSON object")
            if args.auto_workspace:
                update_sections_from_hook(batch)
            else:
                update_sections(args.workspace, batch)
        else:
            if args.data is None:
                raise SystemExit("--data is required with --section")
            payload = json.loads(args.data)
            if not isinstance(payload, dict):
                raise SystemExit("--data must be a JSON object")
            if args.auto_workspace:
                update_from_hook(args.section, payload)
            else:
                update_section(args.workspace, args.section, payload)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid JSON: {exc}")
