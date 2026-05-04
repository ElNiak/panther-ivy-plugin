"""Tests for post-write-workflow-aware.py session-overlay routing.

The hook tracks the most-recently-edited ``.ivy`` file as a statusline
``test_file`` segment. Pre-Phase-2 it wrote to the workspace-shared cache,
which caused two Claude Code windows in the same workspace to overwrite
each other's segment. Phase 2 routes the write to the per-session overlay
file at ``cache/<wsHash>/<active_group>/sessions/<session_id>/overlay.json``
when ``session_id`` is present on the hook's stdin payload, and falls back
to the legacy shared-cache write when it is not (offline smoke tests, the
historical CLI invocation pattern).

Three scenarios:

1. Hook payload includes ``session_id`` and ``ivy_workspace`` is set to
   ``bgp`` → ``test_file`` lands in the bgp/ overlay; the shared cache
   stays free of it.
2. Hook payload omits ``session_id`` → ``test_file`` falls back to the
   shared-cache write at the active partition.
3. Two distinct ``session_id`` values produce two independent overlays
   for the same workspace+protocol — the per-session-isolation property
   the user actually asked for.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = PLUGIN_ROOT / "hooks" / "scripts" / "post-write-workflow-aware.py"
HOOK_SCRIPTS_DIR = PLUGIN_ROOT / "hooks" / "scripts"

# Constants copied from the hook so the tests are self-contained — if the
# hook's session-id-handling logic changes, these constants get reviewed too.
SESSION_A = "00893aaf-19fa-41d2-8238-13269b9b3ca0"
SESSION_B = "11111111-2222-3333-4444-555555555555"


def _make_panther_ivy_workspace(tmp_path: Path, active_group: str | None) -> Path:
    """Build a minimal panther_ivy/ tree with optional .ivy-workspace-state.json.

    Args:
        tmp_path: pytest tmp_path root.
        active_group: When non-None, write the state file with
            ``active_group=<value>``. When None, omit the file so the
            cache resolves to the ``default`` partition.

    Returns:
        Absolute path to the panther_ivy/ directory.
    """
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


def _run_hook(
    payload: dict,
    *,
    workspace_root: Path,
    cache_root: Path,
) -> dict:
    """Invoke the hook subprocess with stdin=payload and a hermetic cache root."""
    env = os.environ.copy()
    env.update({
        "CLAUDE_PLUGIN_ROOT": str(PLUGIN_ROOT),
        "IVY_WORKSPACE_ROOT": str(workspace_root),
        "PANTHER_IVY_STATUSLINE_CACHE_ROOT": str(cache_root),
    })
    # Override prevents the override-path short-circuit from masking partition tests.
    env.pop("PANTHER_IVY_STATUSLINE_CACHE_PATH", None)
    env.pop("PANTHER_IVY_STATUSLINE_OVERLAY_PATH", None)

    proc = subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=20,
        env=env,
    )
    assert proc.returncode == 0, (
        f"hook exited {proc.returncode}: stderr={proc.stderr!r}"
    )
    return json.loads(proc.stdout) if proc.stdout.strip() else {}


def _read_overlay(
    cache_root: Path, ws_root: Path, session_id: str, active_group: str
) -> dict | None:
    """Read the overlay JSON via the same path computation the hook uses."""
    sys.path.insert(0, str(HOOK_SCRIPTS_DIR))
    try:
        sys.modules.pop("lib.statusline_cache", None)
        os.environ["PANTHER_IVY_STATUSLINE_CACHE_ROOT"] = str(cache_root)
        import lib.statusline_cache as sc
        path = sc.overlay_path_for(str(ws_root), session_id, active_group)
        if not path.exists():
            return None
        return json.loads(path.read_text())
    finally:
        if str(HOOK_SCRIPTS_DIR) in sys.path:
            sys.path.remove(str(HOOK_SCRIPTS_DIR))
        sys.modules.pop("lib.statusline_cache", None)


def _read_shared(cache_root: Path, ws_root: Path, active_group: str) -> dict | None:
    """Read the shared cache JSON via the same path computation."""
    sys.path.insert(0, str(HOOK_SCRIPTS_DIR))
    try:
        sys.modules.pop("lib.statusline_cache", None)
        os.environ["PANTHER_IVY_STATUSLINE_CACHE_ROOT"] = str(cache_root)
        import lib.statusline_cache as sc
        path = sc.cache_path_for(str(ws_root), active_group)
        if not path.exists():
            return None
        return json.loads(path.read_text())
    finally:
        if str(HOOK_SCRIPTS_DIR) in sys.path:
            sys.path.remove(str(HOOK_SCRIPTS_DIR))
        sys.modules.pop("lib.statusline_cache", None)


class TestSessionOverlayRouting:
    def test_session_id_routes_to_overlay(self, tmp_path: Path):
        ws = _make_panther_ivy_workspace(tmp_path, active_group="bgp")
        cache_root = tmp_path / "_cache"
        ivy_file = ws / "protocol-testing" / "bgp_frame.ivy"
        ivy_file.write_text("# minimal\n")

        _run_hook(
            {
                "hook_event_name": "PostToolUse",
                "session_id": SESSION_A,
                "tool_name": "Write",
                "tool_input": {"file_path": str(ivy_file)},
            },
            workspace_root=ws,
            cache_root=cache_root,
        )

        overlay = _read_overlay(cache_root, ws, SESSION_A, "bgp")
        assert overlay is not None, "overlay file must exist when session_id present"
        assert overlay["test_file"]["basename"] == "bgp_frame.ivy"
        assert overlay["test_file"]["source"] == "last-edited"

        shared = _read_shared(cache_root, ws, "bgp")
        assert shared is None or "test_file" not in shared, (
            "shared cache must not receive test_file when session_id is present"
        )

    def test_missing_session_id_falls_back_to_shared(self, tmp_path: Path):
        ws = _make_panther_ivy_workspace(tmp_path, active_group="bgp")
        cache_root = tmp_path / "_cache"
        ivy_file = ws / "protocol-testing" / "bgp_route.ivy"
        ivy_file.write_text("# minimal\n")

        _run_hook(
            {
                "hook_event_name": "PostToolUse",
                "tool_name": "Edit",
                "tool_input": {"file_path": str(ivy_file)},
            },
            workspace_root=ws,
            cache_root=cache_root,
        )

        overlay = _read_overlay(cache_root, ws, SESSION_A, "bgp")
        assert overlay is None, "no overlay should be created without a session_id"

        shared = _read_shared(cache_root, ws, "bgp")
        assert shared is not None
        assert shared["test_file"]["basename"] == "bgp_route.ivy"
        assert shared["test_file"]["source"] == "last-edited"

    def test_two_sessions_produce_independent_overlays(self, tmp_path: Path):
        ws = _make_panther_ivy_workspace(tmp_path, active_group="bgp")
        cache_root = tmp_path / "_cache"

        ivy_a = ws / "protocol-testing" / "edit_by_a.ivy"
        ivy_b = ws / "protocol-testing" / "edit_by_b.ivy"
        ivy_a.write_text("# a\n")
        ivy_b.write_text("# b\n")

        _run_hook(
            {
                "hook_event_name": "PostToolUse",
                "session_id": SESSION_A,
                "tool_name": "Write",
                "tool_input": {"file_path": str(ivy_a)},
            },
            workspace_root=ws,
            cache_root=cache_root,
        )
        _run_hook(
            {
                "hook_event_name": "PostToolUse",
                "session_id": SESSION_B,
                "tool_name": "Write",
                "tool_input": {"file_path": str(ivy_b)},
            },
            workspace_root=ws,
            cache_root=cache_root,
        )

        overlay_a = _read_overlay(cache_root, ws, SESSION_A, "bgp")
        overlay_b = _read_overlay(cache_root, ws, SESSION_B, "bgp")
        assert overlay_a is not None
        assert overlay_b is not None
        assert overlay_a["test_file"]["basename"] == "edit_by_a.ivy"
        assert overlay_b["test_file"]["basename"] == "edit_by_b.ivy"

    def test_no_active_group_routes_to_default_partition(self, tmp_path: Path):
        """Sessions without ``ivy_workspace(set)`` write under default/."""
        ws = _make_panther_ivy_workspace(tmp_path, active_group=None)
        cache_root = tmp_path / "_cache"
        ivy_file = ws / "protocol-testing" / "anywhere.ivy"
        ivy_file.write_text("# any\n")

        _run_hook(
            {
                "hook_event_name": "PostToolUse",
                "session_id": SESSION_A,
                "tool_name": "Write",
                "tool_input": {"file_path": str(ivy_file)},
            },
            workspace_root=ws,
            cache_root=cache_root,
        )

        # Overlay lands under default/, not bgp/.
        overlay_default = _read_overlay(cache_root, ws, SESSION_A, "default")
        overlay_bgp = _read_overlay(cache_root, ws, SESSION_A, "bgp")
        assert overlay_default is not None
        assert overlay_default["test_file"]["basename"] == "anywhere.ivy"
        assert overlay_bgp is None
