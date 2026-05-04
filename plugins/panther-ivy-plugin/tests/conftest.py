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


@pytest.fixture
def project_md_idle_state():
    """Return a callable producing a fresh PROJECT.md idle state dict.

    Consolidates the per-file ``_idle_state`` helpers across
    ``test_project_md_state.py``, ``test_render_mode_phase.py``, and the
    bootstrap migration tests. Each call returns a new dict so tests can
    mutate freely without bleeding into each other.
    """

    def _make(protocol: str = "bgp", version: str = "rfc4271") -> dict:
        return {
            "protocol": protocol,
            "version": version,
            "mode": "idle",
            "phase": 0,
            "journal_pointer": ".panther-ivy/workflow-journal.yaml#null",
            "last_verify": {"status": "NOT_RUN", "timestamp": None, "isolate": None},
            "rfc_sections_covered": [],
            "open_counterexamples": [],
            "last_iut_run": None,
            "deferred_layers": [],
        }

    return _make


@pytest.fixture
def seed_workspace_state():
    """Return a callable that writes ``.ivy-workspace-state.json`` under a root.

    Consolidates the per-file ``_seed_workspace_state`` helpers used by the
    PROJECT.md hook + statusline tests.
    """

    def _seed(root, active_group: str) -> None:
        from pathlib import Path

        state_path = Path(root) / ".ivy-workspace-state.json"
        state_path.write_text(json.dumps({"active_group": active_group}))

    return _seed


@pytest.fixture
def seed_journal():
    """Return a callable that writes ``.panther-ivy/workflow-journal.yaml``.

    Consolidates the per-file ``_seed_journal`` helpers used by the
    render-project-md and PROJECT.md hook tests.
    """
    import yaml

    def _seed(protocol_dir, events: list) -> None:
        from pathlib import Path

        panther_dir = Path(protocol_dir) / ".panther-ivy"
        panther_dir.mkdir(parents=True, exist_ok=True)
        (panther_dir / "workflow-journal.yaml").write_text(
            yaml.safe_dump({"events": events})
        )

    return _seed


@pytest.fixture(autouse=True)
def _isolate_statusline_cache_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Path:
    """Redirect the statusline cache root under ``tmp_path`` for every test.

    Consolidates the per-file ``_isolate_cache_root`` autouse fixture
    duplicated across ``test_statusline_cache_partitioning.py``,
    ``test_statusline_overlay.py``, and ``test_statusline_cache_migration.py``.
    Path overrides are cleared so each test gets the partition-aware
    layout (rather than the env-override short-circuit) by default.

    Tests that need the literal-path override can still set
    ``PANTHER_IVY_STATUSLINE_CACHE_PATH`` via their own ``monkeypatch``
    inside the test body — that takes precedence over this fixture's
    delenv because pytest's monkeypatch is LIFO at teardown.
    """
    monkeypatch.setenv("PANTHER_IVY_STATUSLINE_CACHE_ROOT", str(tmp_path / "cache"))
    monkeypatch.delenv("PANTHER_IVY_STATUSLINE_CACHE_PATH", raising=False)
    monkeypatch.delenv("PANTHER_IVY_STATUSLINE_OVERLAY_PATH", raising=False)
    return tmp_path
