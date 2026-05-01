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
