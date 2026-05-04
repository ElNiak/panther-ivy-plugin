"""Tests for the legacy statusline cache migration.

Phase 1 of the per-protocol partitioning landed the new path layout
``<cache_root>/<hash>/<active_group>/statusline.json``. Pre-partitioning
installs have ``<cache_root>/<hash>/statusline.json`` instead. The first
SessionStart after Phase 4 lands runs :func:`migrate_legacy_cache`, which
moves the legacy file under the ``default/`` partition so the renderer's
cold-start visual is the user's preserved state rather than the
``[ivy: initializing]`` token.

The migration is idempotent: a no-op once the legacy file is gone.
Concurrent SessionStart hooks are safe because the move is wrapped in
the same fcntl lock the regular cache writers use.

Three scenarios:

  1. Legacy exists + new does not → file moves; legacy is gone afterward.
  2. Legacy exists + new exists → legacy is deleted (sibling session
     already migrated); new path is preserved unchanged.
  3. Neither exists → no-op.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PLUGIN_ROOT / "hooks" / "scripts"))

import lib.statusline_cache as sc  # noqa: E402


def _legacy_path(workspace_root: str) -> Path:
    """Compute the pre-partitioning legacy cache path for assertions.

    Mirrors :func:`statusline_cache.cache_path_for` for ``active_group=None``
    *minus* the partition directory — i.e. the layout that existed before
    the per-protocol partitioning shipped. Tests use this to verify the
    migration starts from a faithful pre-partitioning state.
    """
    return sc._cache_root() / sc._workspace_digest(workspace_root) / "statusline.json"


class TestMigrateLegacyCache:
    def test_legacy_alone_moves_to_default_partition(self, tmp_path: Path):
        ws = "/some/panther_ivy"
        legacy = _legacy_path(ws)
        legacy.parent.mkdir(parents=True)
        legacy.write_text(
            json.dumps(
                {
                    "version": 1,
                    "workflow": {"name": "scaffold", "phase": "init"},
                }
            )
        )

        moved = sc.migrate_legacy_cache(ws)

        assert moved is True
        new_path = sc.cache_path_for(ws, None)  # default partition
        assert not legacy.exists(), "legacy file must be gone after migration"
        assert new_path.exists(), "new path must hold the migrated content"
        new_content = json.loads(new_path.read_text())
        assert new_content["workflow"]["name"] == "scaffold"

    def test_legacy_and_new_both_present_legacy_dropped(self, tmp_path: Path):
        """Sibling session migrated first → legacy is surplus, drop it."""
        ws = "/some/panther_ivy"
        legacy = _legacy_path(ws)
        legacy.parent.mkdir(parents=True)
        legacy.write_text(json.dumps({"version": 1, "workflow": {"name": "stale"}}))

        new_path = sc.cache_path_for(ws, None)
        new_path.parent.mkdir(parents=True)
        new_path.write_text(json.dumps({"version": 1, "workflow": {"name": "fresh"}}))

        moved = sc.migrate_legacy_cache(ws)

        assert moved is True, "function should report it acted on the legacy file"
        assert not legacy.exists(), "legacy file must be deleted"
        new_content = json.loads(new_path.read_text())
        assert new_content["workflow"]["name"] == "fresh", (
            "must NOT overwrite the new path's content"
        )

    def test_neither_exists_is_noop(self, tmp_path: Path):
        ws = "/some/panther_ivy"
        moved = sc.migrate_legacy_cache(ws)
        assert moved is False
        assert not _legacy_path(ws).exists()
        assert not sc.cache_path_for(ws, None).exists()

    def test_idempotent_double_run(self, tmp_path: Path):
        """Calling migrate twice in a row does not undo the first."""
        ws = "/some/panther_ivy"
        legacy = _legacy_path(ws)
        legacy.parent.mkdir(parents=True)
        legacy.write_text(json.dumps({"version": 1, "workflow": {"name": "scaffold"}}))

        first = sc.migrate_legacy_cache(ws)
        second = sc.migrate_legacy_cache(ws)

        assert first is True
        assert second is False, "second run finds nothing to migrate"
        new_path = sc.cache_path_for(ws, None)
        assert new_path.exists()
        assert json.loads(new_path.read_text())["workflow"]["name"] == "scaffold"

    def test_empty_workspace_root_returns_false(self):
        assert sc.migrate_legacy_cache("") is False
