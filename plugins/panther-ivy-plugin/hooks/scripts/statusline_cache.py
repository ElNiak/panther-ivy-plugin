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


def update_from_hook(section: str, data: dict) -> None:
    """Convenience wrapper for hooks: resolve workspace root and update cache.

    Uses :func:`hook_utils.get_workspace_root` so every hook agrees on the
    same panther_ivy directory (the cache key). Silently no-ops when the
    workspace cannot be resolved or an import fails.

    Args:
        section: Cache section name (e.g. ``"mcp"``, ``"workflow"``).
        data: Fields to merge into the section.
    """
    try:
        from hook_utils import get_workspace_root
        ws_root = get_workspace_root()
    except Exception:
        return
    if not ws_root:
        return
    update_section(ws_root, section, data)


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
    parser.add_argument("--section", required=True, help="Section name")
    parser.add_argument("--data", required=True, help="JSON-encoded data to merge")
    args = parser.parse_args()
    try:
        payload = json.loads(args.data)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid --data JSON: {exc}")
    if not isinstance(payload, dict):
        raise SystemExit("--data must be a JSON object")
    if args.auto_workspace:
        update_from_hook(args.section, payload)
    else:
        update_section(args.workspace, args.section, payload)
