"""Tests for shared hook utilities."""

import importlib
import json
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_HOOK_SCRIPTS_DIR = str(Path(__file__).resolve().parent.parent / "hooks" / "scripts")


@pytest.fixture(autouse=True)
def _patch_sys_path():
    """Temporarily add hooks/scripts/ to sys.path for imports."""
    sys.path.insert(0, _HOOK_SCRIPTS_DIR)
    yield
    sys.path.remove(_HOOK_SCRIPTS_DIR)
    if "hook_utils" in sys.modules:
        del sys.modules["hook_utils"]


def _import_hook_utils():
    if "hook_utils" in sys.modules:
        return importlib.reload(sys.modules["hook_utils"])
    return importlib.import_module("hook_utils")


class TestResolveSessionId:
    def test_env_var_priority(self, monkeypatch):
        mod = _import_hook_utils()
        monkeypatch.setattr(mod, "_canonical_resolve", None)
        monkeypatch.setenv("IVY_SESSION_ID", "from-ivy")
        monkeypatch.setenv("CLAUDE_SESSION_ID", "from-claude")
        assert mod.resolve_session_id() == "from-ivy"

    def test_fallback_to_unknown(self, monkeypatch):
        mod = _import_hook_utils()
        monkeypatch.setattr(mod, "_canonical_resolve", None)
        monkeypatch.delenv("IVY_SESSION_ID", raising=False)
        monkeypatch.delenv("CLAUDE_SESSION_ID", raising=False)
        monkeypatch.delenv("CLAUDE_CODE_SESSION_ID", raising=False)
        result = mod.resolve_session_id()
        assert isinstance(result, str)
        assert len(result) > 0


class TestGetStatePath:
    def test_returns_path_in_observability_dir(self, monkeypatch, tmp_path):
        monkeypatch.setenv("IVY_WORKSPACE_ROOT", str(tmp_path))
        monkeypatch.setenv("IVY_SESSION_ID", "test-sess")
        mod = _import_hook_utils()
        path = mod.get_mcp_health_state_path()
        assert "test-sess" in path
        assert "mcp-health-state.json" in path


class TestResolveWorkspaceStatePath:
    """Unit tests for the two-root resolver added 2026-05-02 to fix the
    SessionStart workspace banner always rendering 'Active workspace: none'
    when MCP writes state at the panther_ivy root but SessionStart detects
    the PANTHER root above it.
    """

    def test_returns_detected_root_when_present(self, tmp_path, monkeypatch):
        """Resolver picks detected_root candidate when its state file exists."""
        detected = tmp_path / "detected"
        detected.mkdir()
        state_file = detected / ".ivy-workspace-state.json"
        state_file.write_text('{"active_group": "bgp"}')
        # panther_ivy candidate exists but has no state file
        panther_ivy = tmp_path / "panther_ivy"
        panther_ivy.mkdir()
        monkeypatch.setenv("IVY_WORKSPACE_ROOT", str(panther_ivy))
        mod = _import_hook_utils()
        assert mod.resolve_workspace_state_path(str(detected)) == str(state_file)

    def test_falls_back_to_panther_ivy_root(self, tmp_path, monkeypatch):
        """Resolver falls back to panther_ivy root when detected_root has no
        state file. Regression for the 2026-05-02 SessionStart workspace bug.
        """
        detected = tmp_path / "detected"
        detected.mkdir()
        panther_ivy = tmp_path / "panther_ivy"
        panther_ivy.mkdir()
        state_file = panther_ivy / ".ivy-workspace-state.json"
        state_file.write_text('{"active_group": "quic"}')
        monkeypatch.setenv("IVY_WORKSPACE_ROOT", str(panther_ivy))
        mod = _import_hook_utils()
        assert mod.resolve_workspace_state_path(str(detected)) == str(state_file)

    def test_returns_none_when_neither_exists(self, tmp_path, monkeypatch):
        """Resolver returns None when no candidate root has the state file."""
        detected = tmp_path / "detected"
        detected.mkdir()
        panther_ivy = tmp_path / "panther_ivy"
        panther_ivy.mkdir()
        monkeypatch.setenv("IVY_WORKSPACE_ROOT", str(panther_ivy))
        mod = _import_hook_utils()
        assert mod.resolve_workspace_state_path(str(detected)) is None


class TestEmitHookOutput:
    def test_emit_additional_context(self, capsys):
        mod = _import_hook_utils()
        mod.emit_hook_output(
            "PreToolUse",
            system_message="",
            additional_context="test message",
        )
        output = json.loads(capsys.readouterr().out)
        assert output["hookSpecificOutput"]["additionalContext"] == "test message"

    def test_emit_deny(self, capsys):
        mod = _import_hook_utils()
        mod.emit_hook_output(
            "PreToolUse",
            system_message="",
            deny_reason="blocked",
        )
        output = json.loads(capsys.readouterr().out)
        assert output["hookSpecificOutput"]["permissionDecision"] == "deny"
