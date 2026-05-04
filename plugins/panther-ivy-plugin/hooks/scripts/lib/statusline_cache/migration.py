"""One-shot legacy statusline cache migration.

Moves a pre-partitioning ``<cache_root>/<hash>/statusline.json`` file to the
new ``<cache_root>/<hash>/default/statusline.json`` path on first SessionStart
after Phase 4 lands.

Per ``feedback_no_backward_compat_shims`` this is intentionally short-lived.
A follow-up commit removes ``migrate_legacy_cache`` and its call site in
``sync-statusline-cache.py`` once enough time has passed that no live install
still has a legacy file. The function and its test
(``tests/test_statusline_cache_migration.py``) are tagged for that cleanup.
"""

# pyright: reportMissingTypeArgument=false
from __future__ import annotations

import os

from lib.statusline_cache.paths import (
    _DEFAULT_GROUP,
    _cache_root,
    _workspace_digest,
    cache_path_for,
)
from lib.statusline_cache.shared import _with_cache_lock


def migrate_legacy_cache(workspace_root: str) -> bool:
    """Move a pre-partitioning cache file under the ``default/`` partition.

    Phase 1 of the per-protocol partitioning landed
    ``<cache_root>/<hash>/<active_group>/statusline.json`` as the new path
    layout. Pre-partitioning installs have ``<cache_root>/<hash>/statusline.json``
    instead. The first SessionStart after Phase 4 lands moves the legacy
    file under the ``default/`` partition so the renderer's cold-start
    visual is the user's preserved state, not ``[ivy: initializing]``.

    Idempotent and safe under concurrent SessionStart hooks: if both files
    exist (a Phase 4 hook fired in another window already migrated, then a
    write to the new path created the new file), the legacy file is
    deleted without overwriting the new one. The lock on the new path's
    sibling ``statusline.lock`` is taken during the move so a concurrent
    writer cannot race a torn rename.

    Args:
        workspace_root: Absolute path to the Ivy workspace root used to
            compute the workspace hash.

    Returns:
        ``True`` when a legacy file was found and moved or deleted (i.e. a
        migration step actually executed). ``False`` when the legacy file
        is absent or any IO error occurred (best-effort: a migration
        failure must not break the SessionStart hook).
    """
    if not workspace_root:
        return False
    try:
        digest = _workspace_digest(workspace_root)
        legacy_path = _cache_root() / digest / "statusline.json"
        if not legacy_path.is_file():
            return False
        new_path = _cache_root() / digest / _DEFAULT_GROUP / "statusline.json"
        new_path.parent.mkdir(parents=True, exist_ok=True)

        def _apply() -> None:
            if new_path.exists():
                # Already migrated by a sibling session; legacy file is
                # surplus state. Delete it rather than overwrite the new
                # path (which may already hold updates from the new
                # writers).
                try:
                    legacy_path.unlink()
                except OSError:
                    pass
                return
            os.replace(str(legacy_path), str(new_path))

        _with_cache_lock(new_path, _apply)
        return True
    except Exception:
        # Best-effort migration: a failure must not break SessionStart.
        return False
