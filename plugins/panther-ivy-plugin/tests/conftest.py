"""Fixtures for panther-ivy-plugin integration tests."""

import shutil
from pathlib import Path

import pytest


# Root of the panther-ivy-plugin Claude Code plugin
PLUGIN_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def plugin_root() -> Path:
    """Path to the panther-ivy-plugin plugin root directory."""
    return PLUGIN_ROOT


@pytest.fixture
def ivy_lsp_root() -> Path:
    """Path to the sibling ivy-lsp plugin root directory."""
    lsp_root = PLUGIN_ROOT.parent / "ivy-lsp"
    assert lsp_root.is_dir(), f"ivy-lsp sibling directory not found at {lsp_root}"
    return lsp_root


@pytest.fixture
def hook_scripts_dir() -> Path:
    """Path to the hooks/scripts/ directory containing hook shell scripts."""
    scripts_dir = PLUGIN_ROOT / "hooks" / "scripts"
    assert scripts_dir.is_dir(), f"Hook scripts directory not found at {scripts_dir}"
    return scripts_dir


@pytest.fixture
def has_python3() -> bool:
    """Whether python3 is available on PATH (required by hook scripts)."""
    return shutil.which("python3") is not None


@pytest.fixture
def obs_scripts_dir(hook_scripts_dir) -> Path:
    """Path to the hooks/scripts/observability/ directory."""
    scripts_dir = hook_scripts_dir / "observability"
    assert scripts_dir.is_dir(), f"Observability scripts not found at {scripts_dir}"
    return scripts_dir
