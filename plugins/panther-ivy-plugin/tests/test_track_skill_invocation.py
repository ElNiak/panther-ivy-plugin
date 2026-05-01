"""Tests for the PostToolUse:Skill hook ``track-skill-invocation.py``.

The hook tracks every ``Skill`` tool call:

  * Plugin skill inside an active workflow → emits ``[ivy-skill] <name> loaded
    (...)`` system message, optionally surfaces ``references/*.md`` as
    ``additionalContext``, AND appends a ``progress{kind: "skill_invoked"}``
    journal entry when the skill is one of the ops-skills.
  * Plugin skill OUTSIDE any workflow → emits the status line and (when a
    references directory exists) auto-loads it, but does not journal-write.
  * Non-plugin skill (e.g. ``superpowers:brainstorming``) → emits a minimal
    ``[ivy-skill] non-plugin skill: <name>`` line; nothing else.

These tests subprocess-invoke the hook so they exercise the end-to-end
JSON-on-stdin → JSON-on-stdout contract, not just the helper internals.
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
SCRIPT = PLUGIN_ROOT / "hooks" / "scripts" / "track-skill-invocation.py"


def _run(payload: dict, *, env: dict[str, str] | None = None) -> dict:
    """Run track-skill-invocation.py with a JSON payload and parse stdout.

    Returns the parsed JSON envelope, or an empty dict if the hook produced
    no output.
    """
    full_env = os.environ.copy()
    full_env["CLAUDE_PLUGIN_ROOT"] = str(PLUGIN_ROOT)
    if env:
        full_env.update(env)
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=10,
        env=full_env,
    )
    assert result.returncode == 0, (
        f"hook exited {result.returncode}: stderr={result.stderr!r}"
    )
    if not result.stdout.strip():
        return {}
    return json.loads(result.stdout)


# ---------------------------------------------------------------------------
# 1. Non-Skill tool → noop
# ---------------------------------------------------------------------------


class TestNonSkillTool:
    def test_non_skill_tool_emits_noop(self):
        out = _run({"tool_name": "Read", "tool_input": {"file_path": "/tmp/x"}})
        assert out.get("systemMessage", "").startswith("[ivy-noop]")
        assert "non-Skill" in out["systemMessage"]
        assert "additionalContext" not in out.get("hookSpecificOutput", {})


# ---------------------------------------------------------------------------
# 2. Non-plugin Skill → status line only
# ---------------------------------------------------------------------------


class TestNonPluginSkill:
    def test_emits_status_line_only(self):
        out = _run(
            {
                "tool_name": "Skill",
                "tool_input": {"skill": "superpowers:brainstorming"},
            }
        )
        assert "[ivy-skill] non-plugin skill" in out["systemMessage"]
        assert "superpowers:brainstorming" in out["systemMessage"]
        assert "additionalContext" not in out.get("hookSpecificOutput", {})

    def test_missing_skill_field_emits_noop(self):
        out = _run({"tool_name": "Skill", "tool_input": {}})
        assert out.get("systemMessage", "").startswith("[ivy-noop]")


# ---------------------------------------------------------------------------
# 3. Plugin Skill with references/ directory
# ---------------------------------------------------------------------------


class TestPluginSkill:
    @pytest.fixture
    def fake_plugin_root(self, tmp_path: Path) -> Path:
        """Build a minimal plugin tree with one plugin skill that has refs."""
        plugin_root = tmp_path / "plugin"
        skill_dir = plugin_root / "skills" / "verify-ops" / "references"
        skill_dir.mkdir(parents=True)
        (skill_dir / "first.md").write_text("# First reference\n\nbody one\n")
        (skill_dir / "second.md").write_text("# Second reference\n\nbody two\n")

        # Copy the script + its sibling library modules into the fake plugin
        # so subprocess imports resolve via CLAUDE_PLUGIN_ROOT pointing at
        # the fake tree.
        scripts_src = PLUGIN_ROOT / "hooks" / "scripts"
        scripts_dst = plugin_root / "hooks" / "scripts"
        scripts_dst.mkdir(parents=True)
        for name in (
            "track-skill-invocation.py",
            "hook_utils.py",
            "statusline_cache.py",
            "workflow_state.py",
            "style_utils.py",
        ):
            (scripts_dst / name).write_bytes(
                (scripts_src / name).read_bytes()
            )
        return plugin_root

    def test_loads_references_into_additional_context(
        self, fake_plugin_root: Path, tmp_path: Path
    ):
        out = _run_against_root(
            fake_plugin_root,
            {
                "tool_name": "Skill",
                "tool_input": {"skill": "panther-ivy-plugin:verify-ops"},
            },
            cwd=tmp_path,
        )
        assert "[ivy-skill] verify-ops loaded" in out["systemMessage"]
        ctx = out["hookSpecificOutput"]["additionalContext"]
        assert "references/first.md" in ctx
        assert "references/second.md" in ctx
        assert "body one" in ctx
        assert "body two" in ctx

    def test_no_references_dir_emits_status_line_only(
        self, tmp_path: Path
    ):
        # Build a plugin tree where the requested skill has NO references dir.
        plugin_root = tmp_path / "plugin"
        (plugin_root / "skills" / "ivy-syntax").mkdir(parents=True)
        scripts_src = PLUGIN_ROOT / "hooks" / "scripts"
        scripts_dst = plugin_root / "hooks" / "scripts"
        scripts_dst.mkdir(parents=True)
        for name in (
            "track-skill-invocation.py",
            "hook_utils.py",
            "statusline_cache.py",
            "workflow_state.py",
            "style_utils.py",
        ):
            (scripts_dst / name).write_bytes(
                (scripts_src / name).read_bytes()
            )

        out = _run_against_root(
            plugin_root,
            {
                "tool_name": "Skill",
                "tool_input": {"skill": "panther-ivy-plugin:ivy-syntax"},
            },
            cwd=tmp_path,
        )
        assert "[ivy-skill] ivy-syntax loaded" in out["systemMessage"]
        assert "(no references/)" in out["systemMessage"]
        assert "additionalContext" not in out.get("hookSpecificOutput", {})


def _run_against_root(plugin_root: Path, payload: dict, cwd: Path) -> dict:
    """Like ``_run`` but points CLAUDE_PLUGIN_ROOT at a constructed tree.

    Used by the references-loading tests that need a controlled
    ``skills/<name>/references/*.md`` directory layout instead of the real
    plugin's references.
    """
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = str(plugin_root)
    script = plugin_root / "hooks" / "scripts" / "track-skill-invocation.py"
    result = subprocess.run(
        [sys.executable, str(script)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=10,
        cwd=str(cwd),
        env=env,
    )
    assert result.returncode == 0, (
        f"hook exited {result.returncode}: stderr={result.stderr!r}"
    )
    if not result.stdout.strip():
        return {}
    return json.loads(result.stdout)
