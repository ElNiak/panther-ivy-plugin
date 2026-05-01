"""Tests for WorkflowContext.current() helper."""

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
    if "workflow_state" in sys.modules:
        del sys.modules["workflow_state"]


def _import_module():
    if "workflow_state" in sys.modules:
        return importlib.reload(sys.modules["workflow_state"])
    return importlib.import_module("workflow_state")


class TestWorkflowContextCurrent:
    def test_returns_none_when_protocol_dir_missing(self, monkeypatch, tmp_path):
        # No protocol-testing/ subdir anywhere reachable.
        monkeypatch.setenv("IVY_WORKSPACE_ROOT", str(tmp_path))
        monkeypatch.chdir(tmp_path)
        mod = _import_module()
        assert mod.WorkflowContext.current() is None

    def test_returns_none_when_state_file_missing(self, monkeypatch, tmp_path):
        # Protocol dir resolves but no active-workflow file.
        (tmp_path / "protocol-testing" / "bgp").mkdir(parents=True)
        monkeypatch.setenv("IVY_WORKSPACE_ROOT", str(tmp_path))
        monkeypatch.chdir(tmp_path)
        mod = _import_module()
        assert mod.WorkflowContext.current() is None

    def test_returns_populated_context(self, monkeypatch, tmp_path):
        protocol_dir = tmp_path / "protocol-testing" / "bgp"
        protocol_dir.mkdir(parents=True)
        monkeypatch.setenv("IVY_WORKSPACE_ROOT", str(tmp_path))
        monkeypatch.chdir(tmp_path)
        mod = _import_module()
        mod.set_active_workflow(str(protocol_dir), "workflow-build", "modeling")
        ctx = mod.WorkflowContext.current(protocol="bgp")
        assert ctx is not None
        assert ctx.protocol_dir == str(protocol_dir)
        assert ctx.workflow == "workflow-build"
        assert ctx.phase == "modeling"
        assert ctx.started is not None  # Set by set_active_workflow
        # post-refactor: WorkflowContext exposes only 3 state fields + protocol_dir
        assert not hasattr(ctx, "invocation_depth")
        assert not hasattr(ctx, "caller")

    def test_warns_and_drops_unknown_yaml_keys(self, monkeypatch, tmp_path, capfd):
        """Schema drift: unknown keys (including legacy invocation_depth / caller
        from the pre-cluster-1 schema) are dropped, and a WARN is emitted once."""
        import yaml

        protocol_dir = tmp_path / "protocol-testing" / "bgp"
        state_dir = protocol_dir / ".panther-ivy"
        state_dir.mkdir(parents=True)
        with open(state_dir / "active-workflow", "w") as f:
            yaml.safe_dump(
                {
                    "workflow": "workflow-verify",
                    "phase": "exec",
                    "invocation_depth": 2,
                    "caller": "scaffold",
                    "rogue_field": "should-be-dropped",
                    "another_new_key": 42,
                },
                f,
            )
        monkeypatch.setenv("IVY_WORKSPACE_ROOT", str(tmp_path))
        monkeypatch.chdir(tmp_path)
        mod = _import_module()
        ctx = mod.WorkflowContext.current(protocol="bgp")
        assert ctx is not None
        assert ctx.workflow == "workflow-verify"
        assert ctx.phase == "exec"
        assert not hasattr(ctx, "invocation_depth")
        assert not hasattr(ctx, "caller")
        assert not hasattr(ctx, "rogue_field")
        assert not hasattr(ctx, "another_new_key")

        captured = capfd.readouterr()
        assert "WARN: WorkflowContext dropped unknown fields" in captured.err
        # Legacy fields from pre-cluster-1 schema are now unknown and reported.
        assert "invocation_depth" in captured.err
        assert "caller" in captured.err
        assert "rogue_field" in captured.err
        assert "another_new_key" in captured.err

        # Second call with the same unknown fields should NOT re-emit the WARN
        # (one-shot guard prevents hot-path spam).
        mod.WorkflowContext.current(protocol="bgp")
        captured2 = capfd.readouterr()
        assert captured2.err == ""

    def test_returns_none_when_workflow_key_missing(self, monkeypatch, tmp_path):
        """Guard: if active-workflow YAML lacks `workflow`, current() returns None."""
        import yaml

        protocol_dir = tmp_path / "protocol-testing" / "bgp"
        state_dir = protocol_dir / ".panther-ivy"
        state_dir.mkdir(parents=True)
        with open(state_dir / "active-workflow", "w") as f:
            yaml.safe_dump({"phase": "init"}, f)
        monkeypatch.setenv("IVY_WORKSPACE_ROOT", str(tmp_path))
        monkeypatch.chdir(tmp_path)
        mod = _import_module()
        assert mod.WorkflowContext.current(protocol="bgp") is None

    def test_allows_missing_phase(self, monkeypatch, tmp_path):
        """`phase` is Optional: current() returns a context with phase=None."""
        import yaml

        protocol_dir = tmp_path / "protocol-testing" / "bgp"
        state_dir = protocol_dir / ".panther-ivy"
        state_dir.mkdir(parents=True)
        with open(state_dir / "active-workflow", "w") as f:
            yaml.safe_dump({"workflow": "workflow-verify"}, f)
        monkeypatch.setenv("IVY_WORKSPACE_ROOT", str(tmp_path))
        monkeypatch.chdir(tmp_path)
        mod = _import_module()
        ctx = mod.WorkflowContext.current(protocol="bgp")
        assert ctx is not None
        assert ctx.workflow == "workflow-verify"
        assert ctx.phase is None
