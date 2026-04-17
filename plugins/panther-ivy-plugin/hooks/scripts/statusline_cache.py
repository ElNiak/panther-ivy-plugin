#!/usr/bin/env python3
"""Cache writer for the panther-ivy-plugin specialized status bar.

Hooks call :func:`update_section` on events that change statusline-relevant
state (MCP health, LSP indexing, workflow transitions, workspace detection).
The statusline script reads the resulting JSON file and renders segments from
it — the renderer never queries live state.

Cache layout:
    ~/.claude/panther-ivy-plugin/cache/<sha1(workspace_root)[:12]>/statusline.json

Per-workspace scoping lets parallel sessions on different workspaces stay
isolated while sessions on the same workspace share state.
"""

# pyright: reportMissingTypeArgument=false
from __future__ import annotations

import fcntl
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

CACHE_VERSION = 1

_DEFAULT_CACHE_ROOT = Path.home() / ".claude" / "panther-ivy-plugin" / "cache"
_SECTIONS_WITH_TIMESTAMP = frozenset({"mcp", "lsp"})


def _cache_root() -> Path:
    """Resolve the cache root directory, honoring the test override env var.

    Returns:
        Absolute path to the directory holding per-workspace cache folders.
    """
    override = os.environ.get("PANTHER_IVY_STATUSLINE_CACHE_ROOT", "").strip()
    if override:
        return Path(override)
    return _DEFAULT_CACHE_ROOT


def cache_path_for(workspace_root: str) -> Path:
    """Return the cache file path for a given workspace root.

    Args:
        workspace_root: Absolute path to the Ivy workspace root (typically the
            ``panther_ivy/`` directory or a specific ``protocol-testing/<p>/``).

    Returns:
        Absolute path to the workspace's ``statusline.json`` cache file.
    """
    override = os.environ.get("PANTHER_IVY_STATUSLINE_CACHE_PATH", "").strip()
    if override:
        return Path(override)

    digest = hashlib.sha1(workspace_root.encode("utf-8")).hexdigest()[:12]
    return _cache_root() / digest / "statusline.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_cache(path: Path) -> dict:
    """Read and return the cache JSON, or a fresh skeleton if missing/corrupt."""
    if not path.exists():
        return {"version": CACHE_VERSION}
    try:
        with open(path) as f:
            fcntl.flock(f, fcntl.LOCK_SH)
            try:
                data = json.load(f)
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)
        if not isinstance(data, dict):
            return {"version": CACHE_VERSION}
        if data.get("version") != CACHE_VERSION:
            return {"version": CACHE_VERSION}
        return data
    except (OSError, json.JSONDecodeError):
        return {"version": CACHE_VERSION}


def _atomic_write(path: Path, data: dict) -> None:
    """Write ``data`` to ``path`` atomically via tempfile + rename."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=".statusline-", suffix=".json.tmp", dir=str(path.parent)
    )
    try:
        with os.fdopen(fd, "w") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            try:
                json.dump(data, f, separators=(",", ":"))
                f.flush()
                os.fsync(f.fileno())
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)
        os.replace(tmp_name, path)
    except OSError:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass


def update_sections(workspace_root: str, sections: dict) -> None:
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
    """
    if not workspace_root or not sections:
        return
    try:
        path = cache_path_for(workspace_root)
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
    except Exception:
        pass


def update_section(workspace_root: str, section: str, data: dict) -> None:
    """Merge ``data`` into ``section`` of the workspace's statusline cache.

    The cache file is created on first write. Each call is atomic; concurrent
    writers from different hooks serialize via ``fcntl.LOCK_EX``.

    Sections in :data:`_SECTIONS_WITH_TIMESTAMP` automatically receive a
    ``last_checked_at`` field set to the current UTC time unless the caller
    already provided one. Callers needing freshness tracking for other sections
    should include the field explicitly.

    Args:
        workspace_root: Absolute path to the Ivy workspace root.
        section: Top-level cache key (``"workspace"``, ``"workflow"``,
            ``"mcp"``, ``"lsp"``, ``"test_file"``).
        data: Fields to set on the section. Replaces any existing value for
            the same keys; unspecified keys on the prior section are preserved.
    """
    if not workspace_root or not section:
        return
    try:
        path = cache_path_for(workspace_root)
        cache = _read_cache(path)
        existing = cache.get(section)
        if isinstance(existing, dict):
            merged = {**existing, **data}
        else:
            merged = dict(data)
        if section in _SECTIONS_WITH_TIMESTAMP and "last_checked_at" not in merged:
            merged["last_checked_at"] = _now_iso()
        cache[section] = merged
        cache["version"] = CACHE_VERSION
        _atomic_write(path, cache)
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


def update_from_hook(section: str, data: dict) -> None:
    """Convenience wrapper for hooks: resolve workspace root and update cache.

    Silently no-ops when the workspace cannot be resolved. Hooks that already
    know their workspace root should prefer :func:`update_section` directly;
    hooks that touch multiple sections should use
    :func:`update_sections_from_hook` to avoid redundant reads.

    Args:
        section: Cache section name (e.g. ``"mcp"``, ``"workflow"``).
        data: Fields to merge into the section.
    """
    ws_root = _resolve_workspace_root()
    if not ws_root:
        return
    update_section(ws_root, section, data)


def update_sections_from_hook(sections: dict) -> None:
    """Batched variant of :func:`update_from_hook` for multi-section writes."""
    ws_root = _resolve_workspace_root()
    if not ws_root:
        return
    update_sections(ws_root, sections)


def clear_cache(workspace_root: str) -> None:
    """Delete the cache file for ``workspace_root``. Used for test setup."""
    try:
        path = cache_path_for(workspace_root)
        path.unlink()
    except (OSError, FileNotFoundError):
        pass


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
