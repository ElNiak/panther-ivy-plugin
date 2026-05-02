"""Tests for statusline cache partitioning by ``active_group``.

The shared statusline cache file is keyed by ``(workspace_root, active_group)``
so two Claude Code sessions in the same panther_ivy/ checkout but with
different ``ivy_workspace`` selections (e.g. one in bgp, one in quic)
do not overwrite each other's ``wf:`` segment. Sessions that have not
called ``ivy_workspace(action="set", ...)`` fall through to the
:data:`_DEFAULT_GROUP` partition so a session-default behaviour is
preserved for the legacy callers.

These tests exercise the :func:`cache_path_for` API directly (without
going through a hook subprocess) plus :func:`_resolve_active_group`,
which reads the canonical state file ``.ivy-workspace-state.json``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PLUGIN_ROOT / "hooks" / "scripts"))

import statusline_cache as sc  # noqa: E402


@pytest.fixture(autouse=True)
def _isolate_cache_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect the cache root and the override path under tmp_path.

    Clearing ``PANTHER_IVY_STATUSLINE_CACHE_PATH`` ensures the partition
    logic actually runs — the override would otherwise short-circuit
    every test to a single file.
    """
    monkeypatch.setenv("PANTHER_IVY_STATUSLINE_CACHE_ROOT", str(tmp_path / "cache"))
    monkeypatch.delenv("PANTHER_IVY_STATUSLINE_CACHE_PATH", raising=False)
    monkeypatch.delenv("PANTHER_IVY_STATUSLINE_OVERLAY_PATH", raising=False)
    return tmp_path


def _make_workspace(tmp_path: Path, *, active_group: str | None) -> Path:
    """Build a panther_ivy-like workspace dir, optionally seeding the state file."""
    ws = tmp_path / "panther_ivy"
    (ws / "protocol-testing").mkdir(parents=True)
    if active_group is not None:
        state = {
            "active_group": active_group,
            "active_layers": [active_group],
            "active_tests": [],
            "granularity": "protocol",
            "set_by": "explicit",
        }
        (ws / ".ivy-workspace-state.json").write_text(json.dumps(state))
    return ws


class TestCachePathPartitioning:
    def test_distinct_groups_produce_distinct_paths(self, tmp_path: Path):
        ws = _make_workspace(tmp_path, active_group=None)
        bgp_path = sc.cache_path_for(str(ws), "bgp")
        quic_path = sc.cache_path_for(str(ws), "quic")
        assert bgp_path != quic_path
        assert bgp_path.parent.name == "bgp"
        assert quic_path.parent.name == "quic"
        # Same workspace_root → same workspace-hash directory
        assert bgp_path.parent.parent == quic_path.parent.parent

    def test_none_and_default_collide(self, tmp_path: Path):
        ws = _make_workspace(tmp_path, active_group=None)
        path_none = sc.cache_path_for(str(ws), None)
        path_default = sc.cache_path_for(str(ws), "default")
        assert path_none == path_default
        assert path_none.parent.name == "default"

    def test_unsafe_group_names_collapse_to_default(self, tmp_path: Path):
        ws = _make_workspace(tmp_path, active_group=None)
        for unsafe in ["../etc", "a/b", "x:y", "", "  "]:
            path = sc.cache_path_for(str(ws), unsafe)
            assert path.parent.name == "default", (
                f"unsafe group '{unsafe}' must not escape the cache directory"
            )

    def test_env_override_short_circuits_partitioning(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        ws = _make_workspace(tmp_path, active_group=None)
        override = tmp_path / "explicit-override.json"
        monkeypatch.setenv("PANTHER_IVY_STATUSLINE_CACHE_PATH", str(override))
        # Override returns the literal path regardless of active_group.
        assert sc.cache_path_for(str(ws), "bgp") == override
        assert sc.cache_path_for(str(ws), "quic") == override

    def test_writes_to_different_groups_are_isolated(self, tmp_path: Path):
        ws = _make_workspace(tmp_path, active_group=None)
        sc.update_section(
            str(ws), "workflow", {"name": "scaffold:phase4"}, active_group="bgp"
        )
        sc.update_section(
            str(ws), "workflow", {"name": "refine:diagnose"}, active_group="quic"
        )

        bgp_cache = json.loads(sc.cache_path_for(str(ws), "bgp").read_text())
        quic_cache = json.loads(sc.cache_path_for(str(ws), "quic").read_text())

        assert bgp_cache["workflow"]["name"] == "scaffold:phase4"
        assert quic_cache["workflow"]["name"] == "refine:diagnose"

    def test_clear_section_targets_only_its_group(self, tmp_path: Path):
        ws = _make_workspace(tmp_path, active_group=None)
        sc.update_section(
            str(ws), "workflow", {"name": "scaffold:phase4"}, active_group="bgp"
        )
        sc.update_section(
            str(ws), "workflow", {"name": "refine:diagnose"}, active_group="quic"
        )
        sc.clear_section(str(ws), "workflow", active_group="bgp")

        bgp_cache = json.loads(sc.cache_path_for(str(ws), "bgp").read_text())
        quic_cache = json.loads(sc.cache_path_for(str(ws), "quic").read_text())
        assert "workflow" not in bgp_cache
        assert quic_cache["workflow"]["name"] == "refine:diagnose"


class TestResolveActiveGroup:
    def test_missing_state_file_returns_default(self, tmp_path: Path):
        ws = _make_workspace(tmp_path, active_group=None)
        assert sc._resolve_active_group(str(ws)) == "default"

    def test_explicit_group_returned_verbatim(self, tmp_path: Path):
        ws = _make_workspace(tmp_path, active_group="bgp")
        assert sc._resolve_active_group(str(ws)) == "bgp"

    def test_null_active_group_in_state_returns_default(self, tmp_path: Path):
        ws = _make_workspace(tmp_path, active_group=None)
        # Explicitly write a state file with active_group: null (cleared state)
        state = {
            "active_group": None,
            "active_layers": [],
            "active_tests": [],
            "granularity": "none",
            "set_by": "cleared",
        }
        (ws / ".ivy-workspace-state.json").write_text(json.dumps(state))
        assert sc._resolve_active_group(str(ws)) == "default"

    def test_corrupt_state_file_returns_default(self, tmp_path: Path):
        ws = _make_workspace(tmp_path, active_group=None)
        (ws / ".ivy-workspace-state.json").write_text("{not valid json")
        assert sc._resolve_active_group(str(ws)) == "default"

    def test_empty_workspace_root_returns_default(self):
        assert sc._resolve_active_group("") == "default"

    def test_unsafe_group_in_state_collapses_to_default(self, tmp_path: Path):
        # A buggy or malicious writer puts a path-traversal value in the state.
        ws = _make_workspace(tmp_path, active_group=None)
        state = {
            "active_group": "../../escape",
            "active_layers": [],
            "active_tests": [],
            "granularity": "protocol",
            "set_by": "explicit",
        }
        (ws / ".ivy-workspace-state.json").write_text(json.dumps(state))
        assert sc._resolve_active_group(str(ws)) == "default"
