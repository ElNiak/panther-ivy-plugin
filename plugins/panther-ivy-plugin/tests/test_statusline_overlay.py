"""Tests for the per-session statusline overlay.

The overlay file at
``cache/<wsHash>/<active_group>/sessions/<session_id>/overlay.json``
holds session-private statusline state (``test_file``, badge metadata,
``active_skill``) so two Claude Code windows in the same workspace+protocol
do not overwrite each other's transient view. The renderer reads the
overlay first for any session-private segment and falls back to the
shared cache when the overlay is missing.

These tests exercise the overlay API directly. Phase 2 will switch the
``test_file`` writer (``post-write-workflow-aware.py``) from the shared
cache to the overlay; that hook-side wiring is tested in
``test_post_write_overlay.py`` (Phase 2).
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


SESSION_A = "00893aaf-19fa-41d2-8238-13269b9b3ca0"
SESSION_B = "11111111-2222-3333-4444-555555555555"


def _make_workspace(tmp_path: Path) -> Path:
    ws = tmp_path / "panther_ivy"
    (ws / "protocol-testing").mkdir(parents=True)
    return ws


class TestOverlayPath:
    def test_overlay_nests_under_group_then_sessions(self, tmp_path: Path):
        ws = _make_workspace(tmp_path)
        path = sc.overlay_path_for(str(ws), SESSION_A, "bgp")
        assert path.name == "overlay.json"
        assert path.parent.name == SESSION_A
        assert path.parent.parent.name == "sessions"
        assert path.parent.parent.parent.name == "bgp"

    def test_overlay_uses_default_group_when_none(self, tmp_path: Path):
        ws = _make_workspace(tmp_path)
        path = sc.overlay_path_for(str(ws), SESSION_A, None)
        assert path.parent.parent.parent.name == "default"

    def test_overlay_env_override(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        ws = _make_workspace(tmp_path)
        override = tmp_path / "explicit-overlay.json"
        monkeypatch.setenv("PANTHER_IVY_STATUSLINE_OVERLAY_PATH", str(override))
        assert sc.overlay_path_for(str(ws), SESSION_A, "bgp") == override


class TestOverlayWriteRead:
    def test_write_then_read_roundtrip(self, tmp_path: Path):
        ws = _make_workspace(tmp_path)
        sc.update_overlay(
            str(ws),
            SESSION_A,
            {"test_file": {"path": "bgp/bgp_frame.ivy", "action": "Edit"}},
            active_group="bgp",
        )
        overlay = sc.read_overlay(str(ws), SESSION_A, active_group="bgp")
        assert overlay is not None
        assert overlay["test_file"]["path"] == "bgp/bgp_frame.ivy"
        assert overlay["test_file"]["action"] == "Edit"
        assert overlay["version"] == sc.CACHE_VERSION

    def test_section_merge_preserves_unspecified_keys(self, tmp_path: Path):
        ws = _make_workspace(tmp_path)
        sc.update_overlay(
            str(ws),
            SESSION_A,
            {"test_file": {"path": "x.ivy", "action": "Edit"}},
            active_group="bgp",
        )
        # Now set just the path; action should remain.
        sc.update_overlay(
            str(ws),
            SESSION_A,
            {"test_file": {"path": "y.ivy"}},
            active_group="bgp",
        )
        overlay = sc.read_overlay(str(ws), SESSION_A, active_group="bgp")
        assert overlay is not None
        assert overlay["test_file"]["path"] == "y.ivy"
        assert overlay["test_file"]["action"] == "Edit"

    def test_two_sessions_have_independent_overlays(self, tmp_path: Path):
        ws = _make_workspace(tmp_path)
        sc.update_overlay(
            str(ws),
            SESSION_A,
            {"test_file": {"path": "bgp_frame.ivy"}},
            active_group="bgp",
        )
        sc.update_overlay(
            str(ws),
            SESSION_B,
            {"test_file": {"path": "bgp_route.ivy"}},
            active_group="bgp",
        )
        a = sc.read_overlay(str(ws), SESSION_A, active_group="bgp")
        b = sc.read_overlay(str(ws), SESSION_B, active_group="bgp")
        assert a is not None and a["test_file"]["path"] == "bgp_frame.ivy"
        assert b is not None and b["test_file"]["path"] == "bgp_route.ivy"

    def test_read_missing_returns_none(self, tmp_path: Path):
        ws = _make_workspace(tmp_path)
        assert sc.read_overlay(str(ws), SESSION_A, active_group="bgp") is None

    def test_clear_overlay_deletes_file(self, tmp_path: Path):
        ws = _make_workspace(tmp_path)
        sc.update_overlay(
            str(ws),
            SESSION_A,
            {"test_file": {"path": "x.ivy"}},
            active_group="bgp",
        )
        assert sc.overlay_path_for(str(ws), SESSION_A, "bgp").exists()
        sc.clear_overlay(str(ws), SESSION_A, active_group="bgp")
        assert not sc.overlay_path_for(str(ws), SESSION_A, "bgp").exists()
        assert sc.read_overlay(str(ws), SESSION_A, active_group="bgp") is None

    def test_cross_group_isolation(self, tmp_path: Path):
        """Same session_id, different active_group → distinct overlay files."""
        ws = _make_workspace(tmp_path)
        sc.update_overlay(
            str(ws),
            SESSION_A,
            {"test_file": {"path": "bgp_frame.ivy"}},
            active_group="bgp",
        )
        sc.update_overlay(
            str(ws),
            SESSION_A,
            {"test_file": {"path": "quic_frame.ivy"}},
            active_group="quic",
        )
        bgp_overlay = sc.read_overlay(str(ws), SESSION_A, active_group="bgp")
        quic_overlay = sc.read_overlay(str(ws), SESSION_A, active_group="quic")
        assert bgp_overlay is not None
        assert quic_overlay is not None
        assert bgp_overlay["test_file"]["path"] == "bgp_frame.ivy"
        assert quic_overlay["test_file"]["path"] == "quic_frame.ivy"

    def test_corrupt_overlay_returns_none(self, tmp_path: Path):
        ws = _make_workspace(tmp_path)
        path = sc.overlay_path_for(str(ws), SESSION_A, "bgp")
        path.parent.mkdir(parents=True)
        path.write_text("{not valid json")
        assert sc.read_overlay(str(ws), SESSION_A, active_group="bgp") is None

    def test_version_mismatch_returns_none(self, tmp_path: Path):
        ws = _make_workspace(tmp_path)
        path = sc.overlay_path_for(str(ws), SESSION_A, "bgp")
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({"version": 999, "test_file": {"path": "x"}}))
        assert sc.read_overlay(str(ws), SESSION_A, active_group="bgp") is None


class TestOverlaySafety:
    def test_unsafe_session_id_dropped(self, tmp_path: Path):
        ws = _make_workspace(tmp_path)
        for unsafe in ["", "../escape", "a/b", "x:y", "  "]:
            sc.update_overlay(
                str(ws),
                unsafe,
                {"test_file": {"path": "x.ivy"}},
                active_group="bgp",
            )
        # No overlay file written for any unsafe session_id.
        sessions_dir = sc.overlay_path_for(str(ws), SESSION_A, "bgp").parent.parent
        if sessions_dir.exists():
            assert list(sessions_dir.iterdir()) == [], (
                "unsafe session_id values must not create overlay directories"
            )

    def test_unsafe_session_id_returns_none_on_read(self, tmp_path: Path):
        ws = _make_workspace(tmp_path)
        assert (
            sc.read_overlay(str(ws), "../escape", active_group="bgp") is None
        )

    def test_empty_workspace_root_returns_none(self):
        assert sc.read_overlay("", SESSION_A, active_group="bgp") is None

    def test_empty_sections_no_op(self, tmp_path: Path):
        ws = _make_workspace(tmp_path)
        sc.update_overlay(str(ws), SESSION_A, {}, active_group="bgp")
        assert not sc.overlay_path_for(str(ws), SESSION_A, "bgp").exists()


class TestOverlayFromHook:
    def test_from_hook_resolves_workspace_and_group(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        ws = _make_workspace(tmp_path)
        state = {
            "active_group": "bgp",
            "active_layers": ["bgp"],
            "active_tests": [],
            "granularity": "protocol",
            "set_by": "explicit",
        }
        (ws / ".ivy-workspace-state.json").write_text(json.dumps(state))
        monkeypatch.setenv("IVY_WORKSPACE_ROOT", str(ws))

        sc.update_overlay_from_hook(
            SESSION_A, {"test_file": {"path": "bgp_frame.ivy"}}
        )

        overlay = sc.read_overlay_from_hook(SESSION_A)
        assert overlay is not None
        assert overlay["test_file"]["path"] == "bgp_frame.ivy"
        # Confirm it landed under the bgp/ partition (not default/).
        bgp_overlay_path = sc.overlay_path_for(str(ws), SESSION_A, "bgp")
        assert bgp_overlay_path.exists()

    def test_from_hook_falls_through_when_no_workspace(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ):
        # No IVY_WORKSPACE_ROOT and tmp_path doesn't look like a panther_ivy tree.
        monkeypatch.delenv("IVY_WORKSPACE_ROOT", raising=False)
        monkeypatch.chdir(tmp_path)
        # Should silently no-op rather than crash.
        sc.update_overlay_from_hook(
            SESSION_A, {"test_file": {"path": "x.ivy"}}
        )
        assert sc.read_overlay_from_hook(SESSION_A) is None
