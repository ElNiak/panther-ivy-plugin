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


class TestEmitDedup:
    """Regression tests for the per-session deduplicating hook emitter
    added 2026-05-02 to fix the [ivy-ready] / [ivy-health] chatter
    (Issue C of the hook fix pass).
    """

    def _make_dedup_env(self, tmp_path, monkeypatch):
        monkeypatch.setenv("IVY_WORKSPACE_ROOT", str(tmp_path))
        monkeypatch.delenv("IVY_SESSION_ID", raising=False)
        monkeypatch.delenv("CLAUDE_SESSION_ID", raising=False)
        monkeypatch.delenv("CLAUDE_CODE_SESSION_ID", raising=False)
        return _import_hook_utils()

    def test_first_emit_fires_then_repeated_suppressed(
        self, capsys, tmp_path, monkeypatch
    ):
        mod = self._make_dedup_env(tmp_path, monkeypatch)
        hi = {"session_id": "test-sid"}
        mod.emit_dedup(
            "PreToolUse", "ivy-ready",
            system_message="[ivy-ready] indexed", hook_input=hi,
        )
        first = json.loads(capsys.readouterr().out)
        assert first["systemMessage"] == "[ivy-ready] indexed"

        mod.emit_dedup(
            "PreToolUse", "ivy-ready",
            system_message="[ivy-ready] indexed", hook_input=hi,
        )
        second = json.loads(capsys.readouterr().out)
        assert second["systemMessage"].startswith("[ivy-noop] deduplicated")

    def test_changed_message_re_fires(self, capsys, tmp_path, monkeypatch):
        mod = self._make_dedup_env(tmp_path, monkeypatch)
        hi = {"session_id": "test-sid"}
        mod.emit_dedup(
            "PreToolUse", "ivy-health",
            system_message="[ivy-health] OK", hook_input=hi,
        )
        capsys.readouterr()
        mod.emit_dedup(
            "PreToolUse", "ivy-health",
            system_message="[ivy-health] 2 timeouts", hook_input=hi,
        )
        out = json.loads(capsys.readouterr().out)
        assert out["systemMessage"] == "[ivy-health] 2 timeouts"

    def test_additional_context_bypasses_dedup(
        self, capsys, tmp_path, monkeypatch
    ):
        mod = self._make_dedup_env(tmp_path, monkeypatch)
        hi = {"session_id": "test-sid"}
        for _ in range(2):
            mod.emit_dedup(
                "PreToolUse", "ivy-health",
                system_message="[ivy-health] OK",
                hook_input=hi,
                additional_context="hint for the model",
            )
        outputs = capsys.readouterr().out.strip().splitlines()
        assert len(outputs) == 2
        for line in outputs:
            payload = json.loads(line)
            assert payload["systemMessage"] == "[ivy-health] OK"
            assert payload["hookSpecificOutput"]["additionalContext"] == "hint for the model"


class TestCheckMcpHealthFiltering:
    """Regression test for the PID-start-time filter on error
    categorisation in check-mcp-health.py, added 2026-05-02 to fix
    Issue B (old log lines reported as 'recent' indefinitely).
    """

    def test_filter_drops_pre_floor_lines_keeps_post_floor(
        self, tmp_path, monkeypatch
    ):
        # Place a fake mcp-*.pid file inside a tmp PID dir; its mtime
        # becomes the live MCP start-time floor.
        pid_dir = tmp_path / "ivy-lsp-pids"
        pid_dir.mkdir()
        pid_file = pid_dir / "mcp-test-12345.pid"
        pid_file.write_text("12345")
        floor_ts = pid_file.stat().st_mtime

        # Load check-mcp-health and override its PID dir constant.
        import importlib.util
        from pathlib import Path

        spec = importlib.util.spec_from_file_location(
            "cmh", str(Path(_HOOK_SCRIPTS_DIR) / "check-mcp-health.py")
        )
        assert spec is not None and spec.loader is not None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        monkeypatch.setattr(mod, "_PID_DIR", str(pid_dir))

        from datetime import datetime
        pre = (
            datetime.fromtimestamp(floor_ts - 600).strftime("%Y-%m-%d %H:%M:%S,000")
            + " ivy ERROR pre-floor TimeoutError"
        )
        post = (
            datetime.fromtimestamp(floor_ts + 60).strftime("%Y-%m-%d %H:%M:%S,000")
            + " ivy ERROR post-floor TimeoutError"
        )
        no_ts = "    File 'x.py' line 5  ERROR continuation"

        filtered = mod._filter_to_current_process([pre, post, no_ts])
        # Pre-floor dropped; post-floor kept; no-timestamp kept (multi-line
        # tracebacks must not lose their continuation lines).
        assert pre not in filtered
        assert post in filtered
        assert no_ts in filtered

        buckets = mod._categorise_recent_errors([pre, post, no_ts])
        # The post-floor TimeoutError counts; the pre-floor one is dropped;
        # the no-timestamp continuation has ERROR but no timeout pattern, so
        # it's "other".
        assert buckets == {"crashes": 0, "timeouts": 1, "connection": 0, "other": 1}
