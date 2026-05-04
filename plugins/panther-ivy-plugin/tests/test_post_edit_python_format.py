"""Tests for the PostToolUse:Write|Edit hook ``posttooluse/lint/python-format.py``.

The hook runs ``ruff check --fix --output-format json`` on edited Python
files and surfaces a status line indicating how many issues were auto-fixed.
Coverage areas:

  * Non-Python file → ``[ivy-noop] non-Python file or empty path``.
  * File outside ``CLAUDE_PLUGIN_ROOT`` (default scope) →
    ``[ivy-noop] file outside plugin scope``.
  * Ruff missing → graceful ``[ivy-noop] ruff binary not on PATH``.
  * Ruff fixes a known F811 redundant import → ``[ivy-ruff] N issue(s)
    auto-fixed`` and the file is rewritten in place.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = PLUGIN_ROOT / "hooks" / "scripts" / "posttooluse/lint/python-format.py"


class TestNonPythonFile:
    def test_md_file_emits_noop(self, run_hook, tmp_path: Path):
        md = tmp_path / "notes.md"
        md.write_text("# notes\n")
        out = run_hook(SCRIPT, {"tool_input": {"file_path": str(md)}})
        assert out.get("systemMessage", "").startswith("[ivy-noop]")
        assert "non-Python" in out["systemMessage"] or "outside plugin scope" in out["systemMessage"]

    def test_empty_file_path_emits_noop(self, run_hook):
        out = run_hook(SCRIPT, {"tool_input": {"file_path": ""}})
        assert out.get("systemMessage", "").startswith("[ivy-noop]")


class TestOutsidePluginScope:
    def test_python_file_outside_plugin_root_emits_noop(self, run_hook, tmp_path: Path):
        py = tmp_path / "outside.py"
        py.write_text("import os\n")
        out = run_hook(SCRIPT, {"tool_input": {"file_path": str(py)}})
        assert out.get("systemMessage", "").startswith("[ivy-noop]")
        assert "outside plugin scope" in out["systemMessage"]

    def test_global_override_disables_scope_check(self, run_hook, tmp_path: Path):
        """``IVY_RUFF_HOOK_GLOBAL=1`` should bypass the prefix check."""
        py = tmp_path / "outside.py"
        py.write_text("import os\n")
        out = run_hook(
            SCRIPT,
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
    def test_missing_file_emits_noop(self, run_hook):
        # File path inside plugin root that does not exist.
        ghost = PLUGIN_ROOT / "hooks" / "scripts" / "ghost-script-12345.py"
        out = run_hook(SCRIPT, {"tool_input": {"file_path": str(ghost)}})
        assert out.get("systemMessage", "").startswith("[ivy-noop]")
        assert "no longer exists" in out["systemMessage"]


@pytest.mark.skipif(
    shutil.which("ruff") is None,
    reason="ruff not on PATH; end-to-end auto-fix path cannot be exercised",
)
class TestAutoFixCount:
    """Exercise the ruff JSON parsing path with a known auto-fixable issue.

    The hook runs ``ruff check --fix --output-format json`` and counts
    findings whose ``fix`` field is non-null. A duplicate ``import os``
    triggers ``F811`` (redefined-while-unused) which ruff auto-fixes by
    removing the second import. The test confirms (a) the system message
    surfaces the fixed count, and (b) the file is rewritten in place.
    """

    def test_duplicate_import_is_auto_fixed(self, run_hook, tmp_path: Path):
        # The plugin's pyproject.toml at the repo root selects D rules
        # (pydocstyle) which fire D100 on test fixtures but are not
        # auto-fixable; that would shadow the F defaults we want to
        # exercise. Drop a ``ruff.toml`` in ``tmp_path`` to scope this
        # test to the F (pyflakes) rule family — ruff walks up from the
        # file's directory and uses the first config it finds.
        (tmp_path / "ruff.toml").write_text('[lint]\nselect = ["F"]\n')
        py = tmp_path / "fixable.py"
        # Two ``import os`` lines + a use of ``os`` so F811 fires (redefined-
        # while-unused) on the second import without F401 also firing on the
        # first (which would remove both lines and leave zero imports).
        py.write_text("import os\nimport os\nprint(os.path.exists('/'))\n")
        out = run_hook(
            SCRIPT,
            {"tool_input": {"file_path": str(py)}},
            env={"IVY_RUFF_HOOK_GLOBAL": "1"},
        )
        sm = out.get("systemMessage", "")
        assert sm.startswith("[ivy-ruff]"), f"unexpected system message: {sm!r}"
        assert "auto-fixed" in sm
        # The file should retain exactly one ``import os`` line.
        rewritten = py.read_text()
        assert rewritten.count("import os") == 1, (
            f"ruff did not remove the duplicate import; file is now: {rewritten!r}"
        )
