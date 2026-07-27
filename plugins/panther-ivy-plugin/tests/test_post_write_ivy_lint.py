"""Tests for posttooluse/lint/ivy.py PostToolUse hook.

Verifies:
  - Activity flag is touched on .ivy file edits.
  - Activity flag is NOT touched for non-.ivy files.
  - Existing lint-output behavior is unchanged.
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
SCRIPT = PLUGIN_ROOT / "hooks" / "scripts" / "posttooluse/lint/ivy.py"


def _run_hook(tmp_path: Path, file_path: str, *, session_id: str = "test-ivy-lint-42") -> dict:
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = str(PLUGIN_ROOT)
    env["IVY_SESSION_ID"] = session_id
    env["TMPDIR"] = str(tmp_path)

    proc = subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=json.dumps({"tool_name": "Write", "tool_input": {"file_path": file_path}}),
        capture_output=True,
        text=True,
        timeout=10,
        env=env,
        cwd=str(tmp_path),
    )
    assert proc.returncode == 0, f"Hook exited {proc.returncode}: {proc.stderr}"
    return json.loads(proc.stdout) if proc.stdout.strip() else {}


def _flag_path(tmp_path: Path, session_id: str = "test-ivy-lint-42") -> Path:
    return tmp_path / "claude-ivy" / f"session-activity-{session_id}.flag"


class TestActivityFlagOnIvyEdit:
    def test_flag_created_for_ivy_file(self, tmp_path):
        ivy_file = tmp_path / "test.ivy"
        ivy_file.write_text("#lang ivy1.7\nrelation foo(X:t)\n")
        _run_hook(tmp_path, str(ivy_file))
        assert _flag_path(tmp_path).exists(), "Activity flag should be created for .ivy file edit"

    def test_flag_idempotent_on_repeated_edits(self, tmp_path):
        ivy_file = tmp_path / "test.ivy"
        ivy_file.write_text("#lang ivy1.7\nrelation foo(X:t)\n")
        _run_hook(tmp_path, str(ivy_file))
        mtime1 = _flag_path(tmp_path).stat().st_mtime
        _run_hook(tmp_path, str(ivy_file))
        # Flag should still exist (touch is idempotent)
        assert _flag_path(tmp_path).exists()

    def test_flag_not_created_for_py_file(self, tmp_path):
        py_file = tmp_path / "test.py"
        py_file.write_text("x = 1\n")
        _run_hook(tmp_path, str(py_file))
        assert not _flag_path(tmp_path).exists(), "Activity flag must NOT be created for .py file"

    def test_flag_not_created_for_empty_path(self, tmp_path):
        _run_hook(tmp_path, "")
        assert not _flag_path(tmp_path).exists(), "Activity flag must NOT be created for empty path"


class TestLintOutputUnchanged:
    def test_structurally_clean_file_emits_noop(self, tmp_path):
        ivy_file = tmp_path / "clean.ivy"
        ivy_file.write_text("#lang ivy1.7\nrelation foo(X:t)\n")
        out = _run_hook(tmp_path, str(ivy_file))
        msg = out.get("systemMessage", "")
        assert msg.startswith("[ivy-noop]"), f"Clean file should emit noop, got: {msg!r}"

    def test_missing_lang_header_emits_lint_warning(self, tmp_path):
        ivy_file = tmp_path / "bad.ivy"
        ivy_file.write_text("# no lang header\nrelation foo(X:t)\n")
        out = _run_hook(tmp_path, str(ivy_file))
        msg = out.get("systemMessage", "")
        assert "[ivy-lint]" in msg, f"Missing lang header should emit lint warning, got: {msg!r}"
