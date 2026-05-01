"""Fixtures for panther-ivy-plugin integration tests."""

import json
import os
import shutil
import subprocess
import sys
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
    """Path to the plugin root containing .lsp.json (unified plugin)."""
    return PLUGIN_ROOT


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


@pytest.fixture
def run_hook():
    """Subprocess-invoke a hook script with JSON stdin and return parsed stdout.

    Consolidates the per-file ``_run`` / ``_run_hook`` helpers across
    ``test_track_skill_invocation.py``, ``test_post_edit_python_format.py``,
    ``test_check_hook_paths.py``, and ``test_hooks.py``. New tests should
    prefer this fixture; the per-file helpers stay until a follow-up sweep.

    Args via the returned callable:
        script: Path to the hook script.
        payload: JSON-serializable dict piped to stdin (defaults to ``{}``).
        env: Optional dict merged into the subprocess environment;
            ``CLAUDE_PLUGIN_ROOT`` is set to ``PLUGIN_ROOT`` if unset.
        cwd: Optional working directory.
        timeout: Subprocess timeout in seconds (default 20).

    Returns:
        Parsed JSON envelope from stdout, or ``{}`` when the hook produced
        empty output.
    """
    def _run_hook(
        script,
        payload: dict | None = None,
        *,
        env: dict | None = None,
        cwd=None,
        timeout: int = 20,
    ) -> dict:
        full_env = os.environ.copy()
        full_env.setdefault("CLAUDE_PLUGIN_ROOT", str(PLUGIN_ROOT))
        if env:
            full_env.update(env)
        proc = subprocess.run(
            [sys.executable, str(script)],
            input=json.dumps(payload or {}),
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(cwd) if cwd else None,
            env=full_env,
        )
        assert proc.returncode == 0, (
            f"hook exited {proc.returncode}: stderr={proc.stderr!r}"
        )
        return json.loads(proc.stdout) if proc.stdout.strip() else {}

    return _run_hook
