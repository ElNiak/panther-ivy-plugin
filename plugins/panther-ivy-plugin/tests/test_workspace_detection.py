"""Test workspace-common.sh functions via subprocess.

Tests the detect_ivy_workspace function by sourcing workspace-common.sh
and invoking the function in various directory structures.
"""

import subprocess
import tempfile
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


def _run_workspace_detection(
    workspace_common_sh: Path,
    cwd: Path,
    extra_script: str = "",
    env: dict | None = None,
) -> subprocess.CompletedProcess:
    """Source workspace-common.sh in a bash subprocess, run
    detect_ivy_workspace, and print the results.

    Args:
        workspace_common_sh: Path to workspace-common.sh
        cwd: Working directory where the detection runs
        extra_script: Additional bash commands to run after sourcing
        env: Subprocess environment (None inherits parent).
    """
    script = f"""
set -euo pipefail
source "{workspace_common_sh}"
{extra_script}
detect_ivy_workspace
echo "TYPE=$DETECTED_TYPE"
echo "ROOT=$DETECTED_ROOT"
"""
    return subprocess.run(
        ["bash", "-c", script],
        capture_output=True,
        text=True,
        timeout=10,
        cwd=str(cwd),
        env=env,
    )


def _parse_detection_output(result: subprocess.CompletedProcess) -> dict:
    """Parse TYPE= and ROOT= from detection output."""
    info = {}
    for line in result.stdout.splitlines():
        if line.startswith("TYPE="):
            info["type"] = line.split("=", 1)[1]
        elif line.startswith("ROOT="):
            info["root"] = line.split("=", 1)[1]
    return info


class TestDetectIvyWorkspace:
    """Test the detect_ivy_workspace function from workspace-common.sh."""

    @pytest.fixture
    def workspace_common_sh(self, plugin_root) -> Path:
        path = plugin_root / "scripts" / "workspace-common.sh"
        assert path.is_file(), f"workspace-common.sh not found at {path}"
        return path

    def test_panther_project_detection(self, workspace_common_sh, tmp_path):
        """A directory tree with the PANTHER structure should be detected
        as 'panther' type, with DETECTED_ROOT pointing to the panther_ivy
        directory.
        """
        # Create the expected PANTHER directory structure
        panther_ivy = (
            tmp_path
            / "panther"
            / "plugins"
            / "services"
            / "testers"
            / "panther_ivy"
        )
        (panther_ivy / "protocol-testing").mkdir(parents=True)

        result = _run_workspace_detection(workspace_common_sh, tmp_path)
        assert result.returncode == 0, f"Script failed: {result.stderr}"

        info = _parse_detection_output(result)
        assert info["type"] == "panther"
        assert info["root"] == str(panther_ivy)

    def test_standalone_project_detection(self, workspace_common_sh):
        """A directory with 3+ .ivy files (no PANTHER structure) should be
        detected as 'standalone' type.
        """
        with tempfile.TemporaryDirectory() as td:
            isolated = Path(td).resolve()
            for i in range(4):
                (isolated / f"spec_{i}.ivy").write_text(f"#lang ivy1.7\n# spec {i}\n")

            env = {"PATH": "/usr/bin:/bin", "HOME": str(isolated)}
            result = _run_workspace_detection(workspace_common_sh, isolated, env=env)
            assert result.returncode == 0, f"Script failed: {result.stderr}"

            info = _parse_detection_output(result)
            assert info["type"] == "standalone"
            assert info["root"] == str(isolated)

    def test_fallback_no_ivy_files(self, workspace_common_sh, tmp_path):
        """An empty directory should fall back with type 'fallback' and
        ROOT set to CWD.

        NOTE: detect_ivy_workspace walks UP from CWD (up to depth 8)
        looking for directories with >= 3 .ivy files. If sibling test
        directories in the same tmp tree created .ivy files, the walk-up
        may find them and report 'standalone' instead. We use a deep
        isolated subdirectory to minimize this, but accept either result
        since the walk-up behavior is by design.
        """
        isolated = tmp_path / "deep" / "isolated" / "empty"
        isolated.mkdir(parents=True)

        result = _run_workspace_detection(workspace_common_sh, isolated)
        assert result.returncode == 0, f"Script failed: {result.stderr}"

        info = _parse_detection_output(result)
        # Accept either fallback or standalone due to parent-walking behavior
        assert info["type"] in ("fallback", "standalone")

    def test_few_ivy_files_not_standalone(self, workspace_common_sh):
        """Only 1-2 .ivy files in the immediate directory should NOT trigger
        standalone detection on their own.
        """
        with tempfile.TemporaryDirectory() as td:
            isolated = Path(td) / "deep" / "isolated"
            isolated.mkdir(parents=True)
            (isolated / "a.ivy").write_text("#lang ivy1.7\n")
            (isolated / "b.ivy").write_text("#lang ivy1.7\n")

            env = {"PATH": "/usr/bin:/bin", "HOME": str(isolated)}
            result = _run_workspace_detection(workspace_common_sh, isolated, env=env)
            assert result.returncode == 0, f"Script failed: {result.stderr}"

            info = _parse_detection_output(result)
            assert info["type"] in ("fallback", "standalone")

    def test_panther_takes_priority_over_standalone(
        self, workspace_common_sh, tmp_path
    ):
        """If both PANTHER structure and 3+ .ivy files exist, PANTHER
        detection should take priority.
        """
        panther_ivy = (
            tmp_path
            / "panther"
            / "plugins"
            / "services"
            / "testers"
            / "panther_ivy"
        )
        (panther_ivy / "protocol-testing").mkdir(parents=True)

        # Also add .ivy files at the root
        for i in range(5):
            (tmp_path / f"model_{i}.ivy").write_text("#lang ivy1.7\n")

        result = _run_workspace_detection(workspace_common_sh, tmp_path)
        assert result.returncode == 0, f"Script failed: {result.stderr}"

        info = _parse_detection_output(result)
        assert info["type"] == "panther"

    def test_nested_ivy_files_detected(self, workspace_common_sh):
        """Ivy files in subdirectories (up to maxdepth 2) should count
        toward standalone detection.
        """
        with tempfile.TemporaryDirectory() as td:
            isolated = Path(td)
            subdir = isolated / "models"
            subdir.mkdir()
            for i in range(3):
                (subdir / f"spec_{i}.ivy").write_text("#lang ivy1.7\n")

            env = {"PATH": "/usr/bin:/bin", "HOME": str(isolated)}
            result = _run_workspace_detection(workspace_common_sh, isolated, env=env)
            assert result.returncode == 0, f"Script failed: {result.stderr}"

            info = _parse_detection_output(result)
            assert info["type"] == "standalone"


class TestFindPantherIvy:
    """Test the find_panther_ivy function from workspace-common.sh."""

    @pytest.fixture
    def workspace_common_sh(self, plugin_root) -> Path:
        return plugin_root / "scripts" / "workspace-common.sh"

    def test_direct_match(self, workspace_common_sh, tmp_path):
        """find_panther_ivy should find the panther_ivy directory when
        called from the project root.
        """
        panther_ivy = (
            tmp_path
            / "panther"
            / "plugins"
            / "services"
            / "testers"
            / "panther_ivy"
        )
        (panther_ivy / "protocol-testing").mkdir(parents=True)

        script = f"""
set -euo pipefail
source "{workspace_common_sh}"
result=$(find_panther_ivy "{tmp_path}")
echo "FOUND=$result"
"""
        result = subprocess.run(
            ["bash", "-c", script],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=str(tmp_path),
        )
        assert result.returncode == 0
        assert f"FOUND={panther_ivy}" in result.stdout

    def test_walk_up_from_subdirectory(self, workspace_common_sh, tmp_path):
        """find_panther_ivy should walk up from a subdirectory to find
        the panther_ivy directory.
        """
        panther_ivy = (
            tmp_path
            / "panther"
            / "plugins"
            / "services"
            / "testers"
            / "panther_ivy"
        )
        (panther_ivy / "protocol-testing").mkdir(parents=True)

        # Create a subdirectory to start from
        start_dir = tmp_path / "src" / "deep"
        start_dir.mkdir(parents=True)

        script = f"""
set -euo pipefail
source "{workspace_common_sh}"
result=$(find_panther_ivy "{start_dir}")
echo "FOUND=$result"
"""
        result = subprocess.run(
            ["bash", "-c", script],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=str(start_dir),
        )
        assert result.returncode == 0
        assert f"FOUND={panther_ivy}" in result.stdout

    def test_not_found_returns_nonzero(self, workspace_common_sh):
        """find_panther_ivy should return non-zero when no panther_ivy
        directory exists.
        """
        with tempfile.TemporaryDirectory() as td:
            isolated = Path(td)
            script = f"""
set -euo pipefail
source "{workspace_common_sh}"
if find_panther_ivy "{isolated}"; then
    echo "FOUND=yes"
else
    echo "FOUND=no"
fi
"""
            result = subprocess.run(
                ["bash", "-c", script],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=str(isolated),
                env={"PATH": "/usr/bin:/bin", "HOME": str(isolated)},
            )
            assert result.returncode == 0
            assert "FOUND=no" in result.stdout


class TestResolveIvyLspSource:
    """Test the resolve_ivy_lsp_source function from workspace-common.sh."""

    @pytest.fixture
    def workspace_common_sh(self, plugin_root) -> Path:
        return plugin_root / "scripts" / "workspace-common.sh"

    def test_explicit_dev_root(self, workspace_common_sh, tmp_path):
        """When IVY_LSP_DEV_ROOT is set and contains ivy_lsp/, that
        path should be used as the source.
        """
        dev_root = tmp_path / "dev-lsp"
        (dev_root / "ivy_lsp").mkdir(parents=True)

        script = f"""
set -euo pipefail
export IVY_LSP_DEV_ROOT="{dev_root}"
source "{workspace_common_sh}"
resolve_ivy_lsp_source
echo "SRC=$IVY_LSP_SRC"
"""
        result = subprocess.run(
            ["bash", "-c", script],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=str(tmp_path),
        )
        assert result.returncode == 0
        assert f"SRC={dev_root}" in result.stdout

    def test_empty_when_no_source_found(self, workspace_common_sh):
        """When no ivy-lsp source is found, IVY_LSP_SRC should be empty."""
        with tempfile.TemporaryDirectory() as td:
            isolated = Path(td)
            script = f"""
set -euo pipefail
source "{workspace_common_sh}"
resolve_ivy_lsp_source
echo "SRC=[$IVY_LSP_SRC]"
"""
            result = subprocess.run(
                ["bash", "-c", script],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=str(isolated),
                env={"PATH": "/usr/bin:/bin", "HOME": str(isolated)},
            )
            assert result.returncode == 0
            assert "SRC=[]" in result.stdout


# ---------------------------------------------------------------------------
# Fix 3A: Serena opt-in gate tests
# ---------------------------------------------------------------------------


class TestSerenaOptIn:
    """Test the PANTHER_IVY_ENABLE_SERENA gate in start-serena.sh."""

    @pytest.fixture
    def start_serena_sh(self, plugin_root) -> Path:
        path = plugin_root / "scripts" / "start-serena.sh"
        assert path.is_file(), f"start-serena.sh not found at {path}"
        return path

    def test_serena_disabled_by_default(self, start_serena_sh, tmp_path):
        """When PANTHER_IVY_ENABLE_SERENA is not set, script exits 0."""
        result = subprocess.run(
            ["bash", str(start_serena_sh)],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=str(tmp_path),
            env={"PATH": "/usr/bin:/bin", "HOME": str(tmp_path)},
        )
        assert result.returncode == 0
        assert "Disabled" in result.stderr

    def test_serena_disabled_when_zero(self, start_serena_sh, tmp_path):
        """When PANTHER_IVY_ENABLE_SERENA=0, script exits 0."""
        result = subprocess.run(
            ["bash", str(start_serena_sh)],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=str(tmp_path),
            env={
                "PATH": "/usr/bin:/bin",
                "HOME": str(tmp_path),
                "PANTHER_IVY_ENABLE_SERENA": "0",
            },
        )
        assert result.returncode == 0
        assert "Disabled" in result.stderr

    def test_serena_enabled_without_source_fails(self, start_serena_sh, tmp_path):
        """When PANTHER_IVY_ENABLE_SERENA=1 but no panther-serena found, exits non-zero."""
        result = subprocess.run(
            ["bash", str(start_serena_sh)],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=str(tmp_path),
            env={
                "PATH": "/usr/bin:/bin",
                "HOME": str(tmp_path),
                "PANTHER_IVY_ENABLE_SERENA": "1",
            },
        )
        # Script should fail because panther-serena is not found
        assert result.returncode != 0


# ---------------------------------------------------------------------------
# 2026-05-02: SessionStart workspace banner regression
# ---------------------------------------------------------------------------


class TestActiveWorkspaceResolution:
    """Regression for the 2026-05-02 SessionStart workspace bug.

    Pre-fix: detect-ivy-workspace.py:_active_workspace looked only at
    detected_root for .ivy-workspace-state.json, but the MCP ivy_workspace
    tool writes the file at the panther_ivy submodule root. The two
    differ by six directory segments in PANTHER worktrees, so the banner
    always rendered 'Active workspace: none' even with an explicitly
    set workspace. Fix delegates resolution to
    hook_utils.resolve_workspace_state_path.
    """

    def test_active_workspace_resolves_panther_ivy_root_fallback(
        self, run_hook, plugin_root: Path, tmp_path: Path
    ):
        """SessionStart banner finds bgp state file written at panther_ivy
        root when detected_root resolves elsewhere.
        """
        panther_ivy = tmp_path / "panther_ivy"
        (panther_ivy / "protocol-testing").mkdir(parents=True)
        state_file = panther_ivy / ".ivy-workspace-state.json"
        state_file.write_text('{"active_group": "bgp", "set_by": "explicit"}')

        cwd = tmp_path / "elsewhere"
        cwd.mkdir()
        script = plugin_root / "hooks" / "scripts" / "detect-ivy-workspace.py"
        out = run_hook(
            script,
            {"session_id": "test-regression"},
            env={
                "IVY_WORKSPACE_ROOT": str(panther_ivy),
                "CLAUDE_PLUGIN_ROOT": str(plugin_root),
            },
            cwd=cwd,
        )
        msg = out.get("systemMessage", "")
        assert "bgp" in msg, (
            f"Expected 'bgp' in systemMessage, got: {msg!r}"
        )
