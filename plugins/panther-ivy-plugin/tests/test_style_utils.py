"""Tests for style_utils module."""

import importlib
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_HOOK_SCRIPTS_DIR = str(Path(__file__).resolve().parent.parent / "hooks" / "scripts")


@pytest.fixture(autouse=True)
def _patch_sys_path():
    sys.path.insert(0, _HOOK_SCRIPTS_DIR)
    yield
    sys.path.remove(_HOOK_SCRIPTS_DIR)
    if "style_utils" in sys.modules:
        del sys.modules["style_utils"]


def _import():
    if "style_utils" in sys.modules:
        return importlib.reload(sys.modules["style_utils"])
    return importlib.import_module("style_utils")


class TestFindSection:
    def test_finds_h2_section(self):
        mod = _import()
        content = "# Title\n\n## Foo\nfoo content\n\n## Bar\nbar content\n"
        assert mod.find_section(content, "Foo") == "foo content"

    def test_finds_h3_section(self):
        mod = _import()
        content = "## Parent\n\n### Child\nchild content\n\n### Other\nother\n"
        assert mod.find_section(content, "Child", level=3) == "child content"

    def test_returns_none_for_missing(self):
        mod = _import()
        assert mod.find_section("# Title\n## Foo\ncontent\n", "Missing") is None

    def test_includes_nested_headings(self):
        mod = _import()
        content = "## Outer\nouter text\n### Inner\ninner text\n\n## Next\n"
        result = mod.find_section(content, "Outer")
        assert "outer text" in result
        assert "### Inner" in result
        assert "inner text" in result


class TestLoadStyleFile:
    def test_loads_existing_file(self, tmp_path):
        mod = _import()
        styles_dir = tmp_path / "styles"
        styles_dir.mkdir()
        (styles_dir / "base.md").write_text("# Base\ncontent here\n")
        result = mod.load_style_file(str(tmp_path), "base.md")
        assert "content here" in result

    def test_returns_none_for_missing(self, tmp_path):
        mod = _import()
        assert mod.load_style_file(str(tmp_path), "nonexistent.md") is None


class TestComposeStyle:
    def test_base_only_when_no_workflow(self, tmp_path):
        mod = _import()
        styles_dir = tmp_path / "styles"
        styles_dir.mkdir()
        (styles_dir / "base.md").write_text("# Base\nbase rules\n")
        result = mod.compose_style(str(tmp_path), workflow=None, phase=None)
        assert "base rules" in result

    def test_base_plus_overlay(self, tmp_path):
        mod = _import()
        styles_dir = tmp_path / "styles"
        (styles_dir / "overlays").mkdir(parents=True)
        (styles_dir / "base.md").write_text("# Base\nbase rules\n")
        (styles_dir / "overlays" / "verify.md").write_text(
            "# Verify\nverify rules\n\n## Phase Modifiers\n\n"
            "### compile\ncompile stuff\n\n### diagnose\ndiagnose stuff\n"
        )
        result = mod.compose_style(str(tmp_path), workflow="verify", phase="compile")
        assert "base rules" in result
        assert "verify rules" in result
        assert "[ACTIVE PHASE]" in result
        assert "compile stuff" in result

    def test_missing_phase_still_includes_overlay(self, tmp_path):
        mod = _import()
        styles_dir = tmp_path / "styles"
        (styles_dir / "overlays").mkdir(parents=True)
        (styles_dir / "base.md").write_text("# Base\nbase rules\n")
        (styles_dir / "overlays" / "verify.md").write_text("# Verify\nverify rules\n")
        result = mod.compose_style(str(tmp_path), workflow="verify", phase="unknown")
        assert "base rules" in result
        assert "verify rules" in result
        assert "[ACTIVE PHASE]" not in result

    def test_missing_overlay_falls_back_to_base(self, tmp_path):
        mod = _import()
        styles_dir = tmp_path / "styles"
        styles_dir.mkdir()
        (styles_dir / "base.md").write_text("# Base\nbase rules\n")
        result = mod.compose_style(str(tmp_path), workflow="nonexistent", phase=None)
        assert "base rules" in result


