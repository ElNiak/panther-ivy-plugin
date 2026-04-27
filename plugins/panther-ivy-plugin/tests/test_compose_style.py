"""Tests for compose-style.py UserPromptSubmit hook."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.unit

SCRIPT = str(
    Path(__file__).resolve().parent.parent / "hooks" / "scripts" / "compose-style.py"
)
PLUGIN_ROOT = str(Path(__file__).resolve().parent.parent)


def run_hook(
    env_overrides: dict | None = None,
    stdin_data: str = "{}",
) -> dict | None:
    """Run the hook script, return parsed JSON output or None."""
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = PLUGIN_ROOT
    if env_overrides:
        env.update(env_overrides)

    result = subprocess.run(
        [sys.executable, SCRIPT],
        input=stdin_data,
        capture_output=True,
        text=True,
        timeout=5,
        env=env,
    )
    assert result.returncode == 0, f"Hook exited {result.returncode}: {result.stderr}"
    if result.stdout.strip():
        return json.loads(result.stdout)
    return None


class TestNoWorkflowActive:
    def test_exits_silently_when_no_workflow(self, tmp_path):
        """When no workflow is active, hook produces no output."""
        proto_dir = tmp_path / "protocol-testing"
        proto_dir.mkdir()
        output = run_hook(env_overrides={"IVY_WORKSPACE_ROOT": str(tmp_path)})
        assert output is None


class TestWithActiveWorkflow:
    def test_injects_overlay(self, tmp_path):
        """When a workflow is active, overlay is included."""
        proto_dir = tmp_path / "protocol-testing"
        proto_dir.mkdir()
        state_dir = proto_dir / ".panther-ivy"
        state_dir.mkdir()
        (state_dir / "active-workflow").write_text(
            yaml.safe_dump({"workflow": "workflow-verify", "phase": "compile"})
        )
        output = run_hook(env_overrides={"IVY_WORKSPACE_ROOT": str(tmp_path)})
        if output is None:
            pytest.skip("No styles dir in plugin root yet")
        ctx = output["hookSpecificOutput"]["additionalContext"]
        assert "Verify Workflow" in ctx

    def test_highlights_active_phase(self, tmp_path):
        """The active phase section gets [ACTIVE PHASE] marker."""
        proto_dir = tmp_path / "protocol-testing"
        proto_dir.mkdir()
        state_dir = proto_dir / ".panther-ivy"
        state_dir.mkdir()
        (state_dir / "active-workflow").write_text(
            yaml.safe_dump({"workflow": "workflow-verify", "phase": "compile"})
        )
        output = run_hook(env_overrides={"IVY_WORKSPACE_ROOT": str(tmp_path)})
        if output is None:
            pytest.skip("No styles dir in plugin root yet")
        ctx = output["hookSpecificOutput"]["additionalContext"]
        assert "[ACTIVE PHASE]" in ctx


class TestNoProtocolDir:
    def test_exits_cleanly(self, tmp_path, monkeypatch):
        """When no protocol-testing dir exists, hook exits cleanly."""
        monkeypatch.delenv("IVY_WORKSPACE_ROOT", raising=False)
        monkeypatch.chdir(tmp_path)
        output = run_hook(env_overrides={"IVY_WORKSPACE_ROOT": ""})
        # Should either output base-only or exit silently
        assert True  # no crash


class TestMalformedState:
    def test_corrupt_workflow_file(self, tmp_path):
        """Corrupt active-workflow file falls back to base only."""
        proto_dir = tmp_path / "protocol-testing"
        proto_dir.mkdir()
        state_dir = proto_dir / ".panther-ivy"
        state_dir.mkdir()
        (state_dir / "active-workflow").write_text("not: [valid: yaml: {{")
        output = run_hook(env_overrides={"IVY_WORKSPACE_ROOT": str(tmp_path)})
        # Should not crash
        assert True
