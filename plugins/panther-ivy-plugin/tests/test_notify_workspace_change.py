"""Tests for the mid-session workspace-change notifier.

The hook fires PostToolUse on the ``mcp__.*ivy_workspace`` matcher and
emits a T3 state-change banner when the workspace state file's
``active_group`` differs from the last value cached for the statusline.
Five scenarios cover the contract:

  * set with a change → banner cites new and was-prev.
  * clear (state file removed) → banner shows ``(none)`` for new.
  * set with same target / get / list → emit_noop.
  * state file missing AND no prev cache → emit_noop (cold call).
  * state file unreadable JSON → emit WARN, exit 0.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = PLUGIN_ROOT / "hooks" / "scripts" / "notify-workspace-change.py"
HOOK_SCRIPTS_DIR = PLUGIN_ROOT / "hooks" / "scripts"


def _write_state_file(panther_ivy: Path, group: str) -> None:
    """Build a panther_ivy root with the protocol-testing marker + state file."""
    panther_ivy.mkdir(parents=True, exist_ok=True)
    (panther_ivy / "protocol-testing").mkdir(exist_ok=True)
    (panther_ivy / ".ivy-workspace-state.json").write_text(
        json.dumps({"active_group": group, "set_by": "explicit"})
    )


def _build_panther_ivy_only(panther_ivy: Path) -> None:
    """Same as _write_state_file but without the state file (clear scenario)."""
    panther_ivy.mkdir(parents=True, exist_ok=True)
    (panther_ivy / "protocol-testing").mkdir(exist_ok=True)


def _seed_statusline_cache(
    panther_ivy: Path, prev_group: str, cache_root: Path
) -> None:
    """Write a cache entry so the hook can resolve a previous value."""
    sys.path.insert(0, str(HOOK_SCRIPTS_DIR))
    try:
        # Force a clean import each call so other tests' module state
        # doesn't leak across env-var changes.
        sys.modules.pop("statusline_cache", None)
        import os
        os.environ["PANTHER_IVY_STATUSLINE_CACHE_ROOT"] = str(cache_root)
        import statusline_cache
        statusline_cache.update_section(
            str(panther_ivy), "workspace", {"protocol": prev_group}
        )
    finally:
        if str(HOOK_SCRIPTS_DIR) in sys.path:
            sys.path.remove(str(HOOK_SCRIPTS_DIR))
        sys.modules.pop("statusline_cache", None)


def _hook_env(panther_ivy: Path, cache_root: Path) -> dict:
    return {
        "IVY_WORKSPACE_ROOT": str(panther_ivy),
        "CLAUDE_PLUGIN_ROOT": str(PLUGIN_ROOT),
        "PANTHER_IVY_STATUSLINE_CACHE_ROOT": str(cache_root),
    }


def test_emits_t3_banner_on_set_with_change(
    run_hook, tmp_path: Path, monkeypatch
):
    """ivy_workspace(set, target=quic) when prev was bgp → T3 banner."""
    panther_ivy = tmp_path / "panther_ivy"
    cache_root = tmp_path / "_cache"
    _write_state_file(panther_ivy, "quic")
    _seed_statusline_cache(panther_ivy, "bgp", cache_root)

    out = run_hook(
        SCRIPT, {}, env=_hook_env(panther_ivy, cache_root), cwd=tmp_path
    )
    msg = out.get("systemMessage", "")
    assert "[ivy-workspace] active workspace: quic (was: bgp)" in msg, msg


def test_emits_t3_banner_on_clear(
    run_hook, tmp_path: Path, monkeypatch
):
    """ivy_workspace(clear): state file removed → banner shows (none)."""
    panther_ivy = tmp_path / "panther_ivy"
    cache_root = tmp_path / "_cache"
    _build_panther_ivy_only(panther_ivy)
    _seed_statusline_cache(panther_ivy, "bgp", cache_root)

    out = run_hook(
        SCRIPT, {}, env=_hook_env(panther_ivy, cache_root), cwd=tmp_path
    )
    msg = out.get("systemMessage", "")
    assert "[ivy-workspace] active workspace: (none) (was: bgp)" in msg, msg


def test_noop_when_unchanged(
    run_hook, tmp_path: Path, monkeypatch
):
    """ivy_workspace(set, target=bgp) when prev was bgp → emit_noop."""
    panther_ivy = tmp_path / "panther_ivy"
    cache_root = tmp_path / "_cache"
    _write_state_file(panther_ivy, "bgp")
    _seed_statusline_cache(panther_ivy, "bgp", cache_root)

    out = run_hook(
        SCRIPT, {}, env=_hook_env(panther_ivy, cache_root), cwd=tmp_path
    )
    msg = out.get("systemMessage", "")
    assert msg.startswith("[ivy-noop]"), msg


def test_handles_missing_state_file_with_no_prev(
    run_hook, tmp_path: Path, monkeypatch
):
    """No state file, no prev cache → noop (cold ivy_workspace(get) call)."""
    panther_ivy = tmp_path / "panther_ivy"
    cache_root = tmp_path / "_cache"
    _build_panther_ivy_only(panther_ivy)
    # No cache seeded

    out = run_hook(
        SCRIPT, {}, env=_hook_env(panther_ivy, cache_root), cwd=tmp_path
    )
    msg = out.get("systemMessage", "")
    assert msg.startswith("[ivy-noop]"), msg


def test_handles_unreadable_state_file_emits_warn(
    run_hook, tmp_path: Path, monkeypatch
):
    """State file exists but is malformed JSON → emit WARN, exit 0."""
    panther_ivy = tmp_path / "panther_ivy"
    cache_root = tmp_path / "_cache"
    _build_panther_ivy_only(panther_ivy)
    (panther_ivy / ".ivy-workspace-state.json").write_text("{not valid json}")

    out = run_hook(
        SCRIPT, {}, env=_hook_env(panther_ivy, cache_root), cwd=tmp_path
    )
    msg = out.get("systemMessage", "")
    assert "[ivy-workspace] WARN" in msg, msg
    assert "unreadable" in msg, msg
