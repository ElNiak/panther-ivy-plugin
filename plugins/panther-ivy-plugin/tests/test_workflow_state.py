"""Tests for workflow state utilities."""

import importlib
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml

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


class TestSetAndGetActiveWorkflow:
    def test_roundtrip(self, tmp_path):
        mod = _import_module()
        mod.set_active_workflow(
            str(tmp_path), "verify", "init", invocation_depth=1, caller="test-agent"
        )
        result = mod.get_active_workflow(str(tmp_path))
        assert result is not None
        assert result["workflow"] == "verify"
        assert result["phase"] == "init"
        assert result["invocation_depth"] == 1
        assert result["caller"] == "test-agent"
        assert "started" in result


class TestUpdatePhase:
    def test_only_phase_changes(self, tmp_path):
        mod = _import_module()
        mod.set_active_workflow(str(tmp_path), "build", "compile")
        original = mod.get_active_workflow(str(tmp_path))

        mod.update_workflow_phase(str(tmp_path), "link")
        updated = mod.get_active_workflow(str(tmp_path))

        assert updated["phase"] == "link"
        assert updated["workflow"] == original["workflow"]
        assert updated["started"] == original["started"]


class TestClearActiveWorkflow:
    def test_clear_removes_file(self, tmp_path):
        mod = _import_module()
        mod.set_active_workflow(str(tmp_path), "verify", "init")
        assert mod.get_active_workflow(str(tmp_path)) is not None

        mod.clear_active_workflow(str(tmp_path))
        assert mod.get_active_workflow(str(tmp_path)) is None

    def test_clear_nonexistent_is_noop(self, tmp_path):
        mod = _import_module()
        mod.clear_active_workflow(str(tmp_path))


class TestIsWorkflowStale:
    def test_stale_detection(self, tmp_path):
        mod = _import_module()
        mod.set_active_workflow(str(tmp_path), "verify", "init")

        state_file = tmp_path / ".panther-ivy" / "active-workflow"
        data = yaml.safe_load(state_file.read_text())
        data["started"] = (
            datetime.now(timezone.utc) - timedelta(hours=3)
        ).isoformat()
        state_file.write_text(yaml.safe_dump(data))

        assert mod.is_workflow_stale(str(tmp_path), max_age_hours=2) is True

    def test_fresh_workflow_is_not_stale(self, tmp_path):
        mod = _import_module()
        mod.set_active_workflow(str(tmp_path), "verify", "init")
        assert mod.is_workflow_stale(str(tmp_path), max_age_hours=2) is False

    def test_no_workflow_is_not_stale(self, tmp_path):
        mod = _import_module()
        assert mod.is_workflow_stale(str(tmp_path)) is False


class TestMissingDirReturnsNone:
    def test_get_returns_none(self, tmp_path):
        mod = _import_module()
        assert mod.get_active_workflow(str(tmp_path / "nonexistent")) is None

    def test_build_state_returns_none(self, tmp_path):
        mod = _import_module()
        assert mod.get_build_state(str(tmp_path / "nonexistent")) is None


class TestBuildStateRoundtrip:
    def test_write_and_read(self, tmp_path):
        mod = _import_module()
        state = {
            "phase": "compile",
            "targets": ["quic_server_test"],
            "completed": ["quic_types"],
        }
        mod.set_build_state(str(tmp_path), state)
        result = mod.get_build_state(str(tmp_path))
        assert result == state


class TestFindProtocolDir:
    def test_from_env_var(self, monkeypatch, tmp_path):
        proto_dir = tmp_path / "protocol-testing"
        proto_dir.mkdir()
        monkeypatch.setenv("IVY_WORKSPACE_ROOT", str(tmp_path))
        mod = _import_module()
        assert mod.find_protocol_dir() == str(proto_dir)

    def test_missing_env_and_no_dir(self, monkeypatch, tmp_path):
        monkeypatch.delenv("IVY_WORKSPACE_ROOT", raising=False)
        monkeypatch.chdir(tmp_path)
        mod = _import_module()
        assert mod.find_protocol_dir() is None

    def test_walk_up_from_cwd(self, monkeypatch, tmp_path):
        monkeypatch.delenv("IVY_WORKSPACE_ROOT", raising=False)
        proto_dir = tmp_path / "protocol-testing"
        proto_dir.mkdir()
        nested = tmp_path / "a" / "b" / "c"
        nested.mkdir(parents=True)
        monkeypatch.chdir(nested)
        mod = _import_module()
        assert mod.find_protocol_dir() == str(proto_dir)
