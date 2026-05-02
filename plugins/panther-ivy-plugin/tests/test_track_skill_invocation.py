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

from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = PLUGIN_ROOT / "hooks" / "scripts" / "track-skill-invocation.py"

_SCRIPT_DEPS = (
    "track-skill-invocation.py",
    "hook_utils.py",
    "statusline_cache.py",
    "workflow_state.py",
    "style_utils.py",
)


def _materialise_scripts(plugin_root: Path) -> Path:
    """Copy the hook + its sibling library modules into ``<plugin_root>/hooks/scripts/``.

    The references-loading tests need a controlled
    ``skills/<name>/references/*.md`` directory layout, so they construct a
    plugin tree under ``tmp_path`` and point ``CLAUDE_PLUGIN_ROOT`` at it.
    The hook script imports its sibling modules via
    ``sys.path.insert(0, os.path.dirname(...))``, so those siblings have
    to be co-located with the script in the constructed tree.
    """
    scripts_src = PLUGIN_ROOT / "hooks" / "scripts"
    scripts_dst = plugin_root / "hooks" / "scripts"
    scripts_dst.mkdir(parents=True)
    for name in _SCRIPT_DEPS:
        (scripts_dst / name).write_bytes((scripts_src / name).read_bytes())
    return scripts_dst / "track-skill-invocation.py"


# ---------------------------------------------------------------------------
# 1. Non-Skill tool → noop
# ---------------------------------------------------------------------------


class TestNonSkillTool:
    def test_non_skill_tool_emits_noop(self, run_hook):
        out = run_hook(SCRIPT, {"tool_name": "Read", "tool_input": {"file_path": "/tmp/x"}})
        assert out.get("systemMessage", "").startswith("[ivy-noop]")
        assert "non-Skill" in out["systemMessage"]
        assert "additionalContext" not in out.get("hookSpecificOutput", {})


# ---------------------------------------------------------------------------
# 2. Non-plugin Skill → status line only
# ---------------------------------------------------------------------------


class TestNonPluginSkill:
    def test_emits_status_line_only(self, run_hook):
        out = run_hook(
            SCRIPT,
            {
                "tool_name": "Skill",
                "tool_input": {"skill": "superpowers:brainstorming"},
            },
        )
        assert "[ivy-skill] non-plugin skill" in out["systemMessage"]
        assert "superpowers:brainstorming" in out["systemMessage"]
        assert "additionalContext" not in out.get("hookSpecificOutput", {})

    def test_missing_skill_field_emits_noop(self, run_hook):
        out = run_hook(SCRIPT, {"tool_name": "Skill", "tool_input": {}})
        assert out.get("systemMessage", "").startswith("[ivy-noop]")


# ---------------------------------------------------------------------------
# 3. Plugin Skill with references/ directory
# ---------------------------------------------------------------------------


class TestPluginSkill:
    @pytest.fixture
    def fake_plugin_root(self, tmp_path: Path) -> tuple[Path, Path]:
        """Build a minimal plugin tree with one plugin skill that has refs.

        Returns ``(plugin_root, script_path)``; the script lives inside the
        constructed tree so ``sys.path``-relative imports resolve correctly.
        """
        plugin_root = tmp_path / "plugin"
        skill_dir = plugin_root / "skills" / "refine-ops" / "references"
        skill_dir.mkdir(parents=True)
        (skill_dir / "first.md").write_text("# First reference\n\nbody one\n")
        (skill_dir / "second.md").write_text("# Second reference\n\nbody two\n")
        script_path = _materialise_scripts(plugin_root)
        return plugin_root, script_path

    def test_loads_references_into_additional_context(
        self, run_hook, fake_plugin_root: tuple[Path, Path], tmp_path: Path
    ):
        plugin_root, script = fake_plugin_root
        out = run_hook(
            script,
            {
                "tool_name": "Skill",
                "tool_input": {"skill": "panther-ivy-plugin:refine-ops"},
            },
            env={"CLAUDE_PLUGIN_ROOT": str(plugin_root)},
            cwd=tmp_path,
        )
        assert "[ivy-skill] refine-ops loaded" in out["systemMessage"]
        ctx = out["hookSpecificOutput"]["additionalContext"]
        assert "references/first.md" in ctx
        assert "references/second.md" in ctx
        assert "body one" in ctx
        assert "body two" in ctx

    def test_no_references_dir_emits_status_line_only(
        self, run_hook, tmp_path: Path
    ):
        # Build a plugin tree where the requested skill has NO references dir.
        plugin_root = tmp_path / "plugin"
        (plugin_root / "skills" / "ivy-syntax").mkdir(parents=True)
        script = _materialise_scripts(plugin_root)
        out = run_hook(
            script,
            {
                "tool_name": "Skill",
                "tool_input": {"skill": "panther-ivy-plugin:ivy-syntax"},
            },
            env={"CLAUDE_PLUGIN_ROOT": str(plugin_root)},
            cwd=tmp_path,
        )
        assert "[ivy-skill] ivy-syntax loaded" in out["systemMessage"]
        assert "(no references/)" in out["systemMessage"]
        assert "additionalContext" not in out.get("hookSpecificOutput", {})


# ---------------------------------------------------------------------------
# 4. Activity flag is set for any plugin skill, not set for non-plugin skills
# ---------------------------------------------------------------------------


class TestActivityFlagOnSkillInvocation:
    def test_flag_set_for_plugin_skill(self, run_hook, tmp_path):
        """Any panther-ivy-plugin:* skill flips the session-activity flag."""
        import os
        session_id = "test-skill-flag-99"
        flag_path = tmp_path / "claude-ivy" / f"session-activity-{session_id}.flag"
        env = {
            "CLAUDE_PLUGIN_ROOT": str(PLUGIN_ROOT),
            "IVY_SESSION_ID": session_id,
            "TMPDIR": str(tmp_path),
        }
        run_hook(
            SCRIPT,
            {"tool_name": "Skill", "tool_input": {"skill": "panther-ivy-plugin:ivy-syntax"}},
            env=env,
            cwd=tmp_path,
        )
        assert flag_path.exists(), "Activity flag should be set for any panther-ivy-plugin skill"

    def test_flag_not_set_for_non_plugin_skill(self, run_hook, tmp_path):
        """Non-plugin skills must NOT flip the session-activity flag."""
        session_id = "test-skill-flag-98"
        flag_path = tmp_path / "claude-ivy" / f"session-activity-{session_id}.flag"
        env = {
            "CLAUDE_PLUGIN_ROOT": str(PLUGIN_ROOT),
            "IVY_SESSION_ID": session_id,
            "TMPDIR": str(tmp_path),
        }
        run_hook(
            SCRIPT,
            {"tool_name": "Skill", "tool_input": {"skill": "superpowers:brainstorming"}},
            env=env,
            cwd=tmp_path,
        )
        assert not flag_path.exists(), "Activity flag must NOT be set for non-plugin skill"

    def test_flag_set_for_knowledge_skill(self, run_hook, tmp_path):
        """Knowledge-only skills (ivy-syntax, methodology, etc.) also flip the flag."""
        session_id = "test-skill-flag-97"
        flag_path = tmp_path / "claude-ivy" / f"session-activity-{session_id}.flag"
        env = {
            "CLAUDE_PLUGIN_ROOT": str(PLUGIN_ROOT),
            "IVY_SESSION_ID": session_id,
            "TMPDIR": str(tmp_path),
        }
        run_hook(
            SCRIPT,
            {"tool_name": "Skill", "tool_input": {"skill": "panther-ivy-plugin:methodology"}},
            env=env,
            cwd=tmp_path,
        )
        assert flag_path.exists(), "Activity flag should be set even for knowledge-only plugin skills"
