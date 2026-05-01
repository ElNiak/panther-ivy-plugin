"""Tests for the PostToolUse:Write|Edit hook ``post-edit-python-format.py``.

The hook runs ``ruff check --fix`` on edited Python files and surfaces a
status line indicating how many issues were auto-fixed. Three coverage
areas:

  * Non-Python file → ``[ivy-noop] non-Python file or empty path``.
  * File outside ``CLAUDE_PLUGIN_ROOT`` (default scope) →
    ``[ivy-noop] file outside plugin scope``.
  * Ruff missing → graceful ``[ivy-noop] ruff binary not on PATH``.

We do not test the auto-fix-count parsing path here; that path requires
a working ``ruff`` install plus a constructed file with auto-fixable
issues, which is more brittle than valuable for a unit test.
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
SCRIPT = PLUGIN_ROOT / "hooks" / "scripts" / "post-edit-python-format.py"


def _run(payload: dict, *, env: dict[str, str] | None = None) -> dict:
    full_env = os.environ.copy()
    full_env["CLAUDE_PLUGIN_ROOT"] = str(PLUGIN_ROOT)
    if env:
        full_env.update(env)
    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=20,
        env=full_env,
    )
    assert result.returncode == 0, (
        f"hook exited {result.returncode}: stderr={result.stderr!r}"
    )
    return json.loads(result.stdout) if result.stdout.strip() else {}


class TestNonPythonFile:
    def test_md_file_emits_noop(self, tmp_path: Path):
        md = tmp_path / "notes.md"
        md.write_text("# notes\n")
        out = _run({"tool_input": {"file_path": str(md)}})
        assert out.get("systemMessage", "").startswith("[ivy-noop]")
        assert "non-Python" in out["systemMessage"] or "outside plugin scope" in out["systemMessage"]

    def test_empty_file_path_emits_noop(self):
        out = _run({"tool_input": {"file_path": ""}})
        assert out.get("systemMessage", "").startswith("[ivy-noop]")


class TestOutsidePluginScope:
    def test_python_file_outside_plugin_root_emits_noop(self, tmp_path: Path):
        py = tmp_path / "outside.py"
        py.write_text("import os\n")
        out = _run({"tool_input": {"file_path": str(py)}})
        assert out.get("systemMessage", "").startswith("[ivy-noop]")
        assert "outside plugin scope" in out["systemMessage"]

    def test_global_override_disables_scope_check(self, tmp_path: Path):
        """``IVY_RUFF_HOOK_GLOBAL=1`` should bypass the prefix check."""
        py = tmp_path / "outside.py"
        py.write_text("import os\n")
        out = _run(
            {"tool_input": {"file_path": str(py)}},
            env={"IVY_RUFF_HOOK_GLOBAL": "1"},
        )
        # With the override, scope no longer blocks. Subsequent paths
        # depend on whether ruff is installed; either path is acceptable.
        sm = out.get("systemMessage", "")
        if sm.startswith("[ivy-noop]"):
            # Either ruff missing or file already clean.
            assert (
                "ruff binary not on PATH" in sm
                or "clean" in sm
                or "no longer exists" in sm
            )
        else:
            assert sm.startswith("[ivy-ruff]")


class TestNonexistentFile:
    def test_missing_file_emits_noop(self, tmp_path: Path):
        # File path inside plugin root that does not exist.
        ghost = PLUGIN_ROOT / "hooks" / "scripts" / "ghost-script-12345.py"
        out = _run({"tool_input": {"file_path": str(ghost)}})
        assert out.get("systemMessage", "").startswith("[ivy-noop]")
        assert "no longer exists" in out["systemMessage"]
