"""Tests for the SessionStart self-test ``session/start/check-hook-paths.py``.

Three scenarios cover the hook's contract:

  * Real plugin tree → ``[ivy-noop] all hooks.json command paths verified``.
  * Constructed tree with one missing script → ``[ivy-meta] N hook script(s)
    missing`` system message + ``additionalContext`` listing the missing rels.
  * Missing or unparseable hooks.json → graceful ``[ivy-meta]`` error
    message, no crash.

The hook always exits 0 so a missing path never blocks a session.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = PLUGIN_ROOT / "hooks" / "scripts" / "session/start/check-hook-paths.py"


def test_clean_plugin_tree_emits_noop(run_hook):
    out = run_hook(SCRIPT, {}, env={"CLAUDE_PLUGIN_ROOT": str(PLUGIN_ROOT)})
    assert out.get("systemMessage", "").startswith("[ivy-noop]")
    assert "verified" in out["systemMessage"]


def test_missing_script_surfaces_meta_warning(run_hook, tmp_path: Path):
    """Build a fake plugin with a hooks.json pointing at a non-existent script."""
    fake_root = tmp_path / "fake-plugin"
    (fake_root / "hooks").mkdir(parents=True)
    (fake_root / "hooks" / "hooks.json").write_text(json.dumps({
        "hooks": {
            "SessionStart": [
                {"hooks": [{
                    "type": "command",
                    "command": "python3 ${CLAUDE_PLUGIN_ROOT}/hooks/scripts/missing.py",
                    "timeout": 5,
                }]},
            ],
        },
    }))
    out = run_hook(SCRIPT, {}, env={"CLAUDE_PLUGIN_ROOT": str(fake_root)})
    assert "missing" in out["systemMessage"]
    ctx = out["hookSpecificOutput"]["additionalContext"]
    assert "hooks/scripts/missing.py" in ctx


def test_unparseable_hooks_json_surfaces_meta_warning(run_hook, tmp_path: Path):
    fake_root = tmp_path / "fake-plugin"
    (fake_root / "hooks").mkdir(parents=True)
    (fake_root / "hooks" / "hooks.json").write_text("{ this is not valid json")
    out = run_hook(SCRIPT, {}, env={"CLAUDE_PLUGIN_ROOT": str(fake_root)})
    assert "[ivy-meta]" in out["systemMessage"]
    assert "unparseable" in out["systemMessage"]


def test_missing_hooks_json_surfaces_meta_warning(run_hook, tmp_path: Path):
    fake_root = tmp_path / "fake-plugin-no-hooks"
    fake_root.mkdir()
    out = run_hook(SCRIPT, {}, env={"CLAUDE_PLUGIN_ROOT": str(fake_root)})
    assert "[ivy-meta]" in out["systemMessage"]
    assert "not found" in out["systemMessage"]


def test_no_plugin_root_emits_noop(run_hook):
    """Run with CLAUDE_PLUGIN_ROOT empty — hook should not crash."""
    out = run_hook(SCRIPT, {}, env={"CLAUDE_PLUGIN_ROOT": ""})
    assert out.get("systemMessage", "").startswith("[ivy-noop]")
