"""Integration tests for panther-ivy-plugin hook scripts.

Each hook script reads JSON from stdin and produces stdout/stderr output.
Tests invoke the scripts via the shared ``run_hook`` fixture in
``conftest.py``, which subprocess-runs the script with the active Python
interpreter and parses stdout into a dict.
"""

import os
import tempfile
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


def _full_text(out: dict) -> str:
    """Concatenate ``systemMessage`` and ``additionalContext`` for substring checks.

    Several tests assert that a free-text marker (``"MCP"``,
    ``"IVY-LINT"``, etc.) appears anywhere in the hook's output. The hook
    envelope splits between a top-level ``systemMessage`` and a nested
    ``hookSpecificOutput.additionalContext``; rather than coupling each
    test to the exact field placement, this helper returns both joined.
    """
    sm = out.get("systemMessage", "") or ""
    ctx = (out.get("hookSpecificOutput") or {}).get("additionalContext", "") or ""
    return f"{sm}\n{ctx}"


# ===================================================================
# PreToolUse hook: block-direct-ivy.py
# ===================================================================


class TestBlockDirectIvyHook:
    """Tests for the PreToolUse hook that warns about direct Ivy CLI calls."""

    def _script(self, hook_scripts_dir: Path) -> Path:
        return hook_scripts_dir / "block-direct-ivy.py"

    def test_ivy_check_triggers_mcp_suggestion(self, run_hook, hook_scripts_dir):
        """Bash command containing 'ivy_check model.ivy' should produce a
        suggestion to use ivy_verify MCP tool instead.
        """
        out = run_hook(
            self._script(hook_scripts_dir),
            {"tool_input": {"command": "ivy_check model.ivy"}},
        )
        text = _full_text(out)
        assert "MCP" in text
        assert "ivy_verify" in text

    def test_non_ivy_command_produces_noop(self, run_hook, hook_scripts_dir):
        """A plain 'ls -la' command emits an [ivy-noop] line under
        strict-literal scope (replaces the bash predecessor's silent exit).
        """
        out = run_hook(
            self._script(hook_scripts_dir),
            {"tool_input": {"command": "ls -la"}},
        )
        assert out.get("systemMessage", "").startswith("[ivy-noop]")
        assert "additionalContext" not in out.get("hookSpecificOutput", {})

    def test_word_boundary_no_false_positive(self, run_hook, hook_scripts_dir):
        """A command like 'my_ivy_checker foo.ivy' should NOT match the
        word-boundary regex ``\\b(ivy_check|ivyc|ivy_show|ivy_to_cpp)\\b`` —
        the leading ``_`` is a word character, so ``\\b`` does not match
        before the embedded ``ivy_check``. Hook emits an [ivy-noop] envelope.
        """
        out = run_hook(
            self._script(hook_scripts_dir),
            {"tool_input": {"command": "my_ivy_checker foo.ivy"}},
        )
        assert out.get("systemMessage", "").startswith("[ivy-noop]")

    def test_ivyc_triggers_mcp_suggestion(self, run_hook, hook_scripts_dir):
        """Bash command with 'ivyc target=test foo.ivy' should produce a
        suggestion to use ivy_compile MCP tool.
        """
        out = run_hook(
            self._script(hook_scripts_dir),
            {"tool_input": {"command": "ivyc target=test foo.ivy"}},
        )
        text = _full_text(out)
        assert "MCP" in text
        assert "ivy_compile" in text

    def test_empty_command_field(self, run_hook, hook_scripts_dir):
        """Empty command field emits an [ivy-noop] line under strict-literal scope."""
        out = run_hook(
            self._script(hook_scripts_dir),
            {"tool_input": {"command": ""}},
        )
        assert out.get("systemMessage", "").startswith("[ivy-noop]")

    def test_missing_command_field(self, run_hook, hook_scripts_dir):
        """JSON without a 'command' field emits an [ivy-noop] line."""
        out = run_hook(
            self._script(hook_scripts_dir),
            {"tool_name": "Bash"},
        )
        assert out.get("systemMessage", "").startswith("[ivy-noop]")


# ===================================================================
# PostToolUse hook: post-write-ivy-lint.py
# ===================================================================


class TestPostWriteIvyLintHook:
    """Tests for the PostToolUse hook that checks .ivy files after writes."""

    def _script(self, hook_scripts_dir: Path) -> Path:
        return hook_scripts_dir / "post-write-ivy-lint.py"

    def test_valid_ivy_file_no_issues(self, run_hook, hook_scripts_dir, tmp_path):
        """Writing a valid .ivy file with #lang header and balanced braces
        should produce no lint output.
        """
        ivy_file = tmp_path / "valid.ivy"
        ivy_file.write_text("#lang ivy1.7\n\nobject foo = {\n    type t\n}\n")

        out = run_hook(
            self._script(hook_scripts_dir),
            {"tool_input": {"file_path": str(ivy_file)}},
            cwd=tmp_path,
        )
        # No issues means no [IVY-LINT] additionalContext (an [ivy-noop] line is OK).
        assert "IVY-LINT" not in _full_text(out)

    def test_missing_lang_header_warns(self, run_hook, hook_scripts_dir, tmp_path):
        """Writing an .ivy file without '#lang ivy1.7' on the first line
        should produce a warning about missing header.
        """
        ivy_file = tmp_path / "no_header.ivy"
        ivy_file.write_text("object foo = {\n    type t\n}\n")

        out = run_hook(
            self._script(hook_scripts_dir),
            {"tool_input": {"file_path": str(ivy_file)}},
            cwd=tmp_path,
        )
        text = _full_text(out)
        assert "IVY-LINT" in text
        assert "Missing #lang ivy1.7" in text

    def test_non_ivy_file_silent_exit(self, run_hook, hook_scripts_dir, tmp_path):
        """Writing a .py file should produce no output (not an .ivy file)."""
        py_file = tmp_path / "module.py"
        py_file.write_text("print('hello')\n")

        out = run_hook(
            self._script(hook_scripts_dir),
            {"tool_input": {"file_path": str(py_file)}},
            cwd=tmp_path,
        )
        # Strict-literal scope: silent-exit replaced with [ivy-noop] envelope.
        assert out.get("systemMessage", "").startswith("[ivy-noop]")
        assert "additionalContext" not in out.get("hookSpecificOutput", {})

    def test_unbalanced_braces_warns(self, run_hook, hook_scripts_dir, tmp_path):
        """Writing an .ivy file with unbalanced braces should produce a
        warning about the brace mismatch.
        """
        ivy_file = tmp_path / "unbalanced.ivy"
        # Has 2 open braces but only 1 close brace.
        ivy_file.write_text(
            "#lang ivy1.7\n\nobject foo = {\n    object bar = {\n    }\n"
        )

        out = run_hook(
            self._script(hook_scripts_dir),
            {"tool_input": {"file_path": str(ivy_file)}},
            cwd=tmp_path,
        )
        text = _full_text(out)
        assert "IVY-LINT" in text
        assert "Unbalanced braces" in text

    def test_empty_file_path_silent_exit(self, run_hook, hook_scripts_dir):
        """Empty file_path should produce no output."""
        out = run_hook(
            self._script(hook_scripts_dir),
            {"tool_input": {"file_path": ""}},
        )
        assert out.get("systemMessage", "").startswith("[ivy-noop]")

    def test_nonexistent_ivy_file_silent_exit(self, run_hook, hook_scripts_dir, tmp_path):
        """An .ivy file_path that does not exist should produce no output
        (the script checks file existence before linting).
        """
        out = run_hook(
            self._script(hook_scripts_dir),
            {"tool_input": {"file_path": str(tmp_path / "does_not_exist.ivy")}},
            cwd=tmp_path,
        )
        assert out.get("systemMessage", "").startswith("[ivy-noop]")

    def test_output_is_valid_json(self, run_hook, hook_scripts_dir, tmp_path):
        """When issues are found, the output should be valid JSON with the
        hookSpecificOutput structure.

        Uses a file with balanced braces but missing #lang header, so the
        only issue is the missing header.
        """
        ivy_file = tmp_path / "bad.ivy"
        ivy_file.write_text("object foo = {\n    type t\n}\n")

        out = run_hook(
            self._script(hook_scripts_dir),
            {"tool_input": {"file_path": str(ivy_file)}},
            cwd=tmp_path,
        )
        assert "hookSpecificOutput" in out
        assert out["hookSpecificOutput"]["hookEventName"] == "PostToolUse"
        assert "additionalContext" in out["hookSpecificOutput"]


# ===================================================================
# SessionStart hook: detect-ivy-workspace.py
# ===================================================================


class TestDetectIvyWorkspaceHook:
    """Tests for the SessionStart hook that detects Ivy workspace type."""

    def _script(self, hook_scripts_dir: Path) -> Path:
        return hook_scripts_dir / "detect-ivy-workspace.py"

    def test_panther_project_detected(self, run_hook, hook_scripts_dir, tmp_path):
        """A directory with panther/plugins/services/testers/panther_ivy/protocol-testing/
        should be detected as 'panther' type.
        """
        panther_dir = (
            tmp_path
            / "panther"
            / "plugins"
            / "services"
            / "testers"
            / "panther_ivy"
            / "protocol-testing"
        )
        panther_dir.mkdir(parents=True)

        out = run_hook(
            self._script(hook_scripts_dir),
            {},  # SessionStart hooks receive no meaningful input
            cwd=tmp_path,
        )
        sm = out.get("systemMessage", "")
        assert "[ivy-workspace] detected:" in sm
        assert "panther" in sm.lower()

    def test_standalone_project_detected(self, run_hook, hook_scripts_dir):
        """A directory with 3+ .ivy files (no PANTHER structure) should be
        detected as 'standalone' type.
        """
        with tempfile.TemporaryDirectory() as td:
            isolated = Path(td)
            for i in range(3):
                (isolated / f"model{i}.ivy").write_text(f"#lang ivy1.7\n# model {i}\n")

            out = run_hook(
                self._script(hook_scripts_dir),
                {},
                cwd=isolated,
                env={"PATH": "/usr/bin:/bin", "HOME": str(isolated)},
            )
            assert "[ivy-workspace] detected:" in out.get("systemMessage", "")

    def test_fallback_when_no_ivy_files(self, run_hook, hook_scripts_dir, tmp_path):
        """An empty directory still produces the slim status line.

        Phase E/F slimmed the script's output to a single ``systemMessage``
        line that no longer surfaces the project type word. The new
        contract is just the workspace prefix and a non-empty CWD-derived
        path.
        """
        # Use a deep subdirectory to reduce chance of parent .ivy file detection
        isolated = tmp_path / "deep" / "isolated" / "empty"
        isolated.mkdir(parents=True)

        out = run_hook(
            self._script(hook_scripts_dir),
            {},
            cwd=isolated,
        )
        assert "[ivy-workspace] detected:" in out.get("systemMessage", "")

    def test_output_is_valid_json_with_hook_event(self, run_hook, hook_scripts_dir, tmp_path):
        """Output should always be valid JSON with SessionStart event name."""
        out = run_hook(
            self._script(hook_scripts_dir),
            {},
            cwd=tmp_path,
        )
        assert out["hookSpecificOutput"]["hookEventName"] == "SessionStart"

    def test_env_file_written_when_set(self, run_hook, hook_scripts_dir, tmp_path):
        """When CLAUDE_ENV_FILE is set, the script should write
        IVY_WORKSPACE_ROOT to that file.
        """
        env_file = tmp_path / "claude_env"
        env = os.environ.copy()
        env["CLAUDE_ENV_FILE"] = str(env_file)

        run_hook(
            self._script(hook_scripts_dir),
            {},
            cwd=tmp_path,
            env=env,
        )
        assert env_file.exists()
        content = env_file.read_text()
        assert "IVY_WORKSPACE_ROOT=" in content
