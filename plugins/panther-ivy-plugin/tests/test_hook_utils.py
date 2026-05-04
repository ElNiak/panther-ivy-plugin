"""Tests for shared hook utilities."""

import importlib
import importlib.util
import json
import sys
from datetime import datetime
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_HOOK_SCRIPTS_DIR = str(Path(__file__).resolve().parent.parent / "hooks" / "scripts")

# Minimal hook stdin payload used across the dedup tests. The session_id
# value is arbitrary — the dedup cache file path is keyed off it, so as
# long as every dedup test reuses the same value, repeated calls within
# one test see the same cache.
_DEDUP_HOOK_INPUT = {"session_id": "test-sid"}


@pytest.fixture(autouse=True)
def _patch_sys_path():
    """Temporarily add hooks/scripts/ to sys.path for imports."""
    sys.path.insert(0, _HOOK_SCRIPTS_DIR)
    yield
    sys.path.remove(_HOOK_SCRIPTS_DIR)
    for key in list(sys.modules):
        if key == "lib.hook_utils" or key.startswith("lib.hook_utils."):
            del sys.modules[key]


def _import_hook_utils():
    if "lib.hook_utils" in sys.modules:
        return importlib.reload(sys.modules["lib.hook_utils"])
    return importlib.import_module("lib.hook_utils")


def _import_hook_utils_session():
    _import_hook_utils()
    return importlib.import_module("lib.hook_utils.session")


class TestResolveSessionId:
    def test_env_var_priority(self, monkeypatch):
        session_mod = _import_hook_utils_session()
        monkeypatch.setattr(session_mod, "_canonical_resolve", None)
        monkeypatch.setenv("IVY_SESSION_ID", "from-ivy")
        monkeypatch.setenv("CLAUDE_SESSION_ID", "from-claude")
        assert session_mod.resolve_session_id() == "from-ivy"

    def test_fallback_to_unknown(self, monkeypatch):
        session_mod = _import_hook_utils_session()
        monkeypatch.setattr(session_mod, "_canonical_resolve", None)
        monkeypatch.delenv("IVY_SESSION_ID", raising=False)
        monkeypatch.delenv("CLAUDE_SESSION_ID", raising=False)
        monkeypatch.delenv("CLAUDE_CODE_SESSION_ID", raising=False)
        result = session_mod.resolve_session_id()
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
        # Pinning IVY_WORKSPACE_ROOT to a fresh tmp_path is the
        # load-bearing isolation step: _hook_dedup_cache_path derives the
        # cache file from the workspace root, so a per-test tmp_path
        # guarantees an empty hook-dedup.json. A future refactor that
        # decouples cache location from workspace root would break this
        # transitive isolation.
        monkeypatch.setenv("IVY_WORKSPACE_ROOT", str(tmp_path))
        monkeypatch.delenv("IVY_SESSION_ID", raising=False)
        monkeypatch.delenv("CLAUDE_SESSION_ID", raising=False)
        monkeypatch.delenv("CLAUDE_CODE_SESSION_ID", raising=False)
        return _import_hook_utils()

    def test_first_emit_fires_then_repeated_suppressed(
        self, capsys, tmp_path, monkeypatch
    ):
        mod = self._make_dedup_env(tmp_path, monkeypatch)
        hi = _DEDUP_HOOK_INPUT
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
        # Pin the dedup_key suffix so silently dropping the parenthesized
        # key from the noop message would fail this test.
        assert "[ivy-noop] deduplicated (ivy-ready)" in second["systemMessage"]

    def test_changed_message_re_fires(self, capsys, tmp_path, monkeypatch):
        mod = self._make_dedup_env(tmp_path, monkeypatch)
        hi = _DEDUP_HOOK_INPUT
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

    @pytest.mark.parametrize(
        "system_message, kwarg_name, kwarg_value, expected_hook_fields",
        [
            (
                "[ivy-health] OK",
                "additional_context",
                "hint for the model",
                {"additionalContext": "hint for the model"},
            ),
            (
                "[ivy-health] crashed",
                "deny_reason",
                "server crashed; run /mcp",
                {
                    "permissionDecision": "deny",
                    "permissionDecisionReason": "server crashed; run /mcp",
                },
            ),
        ],
        ids=["additional_context", "deny_reason"],
    )
    def test_kwarg_bypasses_dedup(
        self, capsys, tmp_path, monkeypatch,
        system_message, kwarg_name, kwarg_value, expected_hook_fields,
    ):
        # Both ``additional_context`` (model context) and ``deny_reason``
        # (blocking decision) must reach the runtime every call, never
        # replaced by ``[ivy-noop]``. Two invocations should produce two
        # full payloads.
        mod = self._make_dedup_env(tmp_path, monkeypatch)
        for _ in range(2):
            mod.emit_dedup(
                "PreToolUse", "ivy-health",
                system_message=system_message,
                hook_input=_DEDUP_HOOK_INPUT,
                **{kwarg_name: kwarg_value},
            )
        outputs = capsys.readouterr().out.strip().splitlines()
        assert len(outputs) == 2
        for line in outputs:
            payload = json.loads(line)
            assert payload["systemMessage"] == system_message
            hook_out = payload["hookSpecificOutput"]
            for field, expected in expected_hook_fields.items():
                assert hook_out[field] == expected

    def test_corrupt_cache_treated_as_empty(
        self, capsys, tmp_path, monkeypatch
    ):
        # A malformed cache file must not block emission. The defensive
        # OSError/JSONDecodeError swallow in emit_dedup falls through to
        # an empty cache, so the next emit fires unconditionally and
        # rewrites the cache as valid JSON.
        mod = self._make_dedup_env(tmp_path, monkeypatch)
        hi = _DEDUP_HOOK_INPUT
        cache_path = mod._hook_dedup_cache_path(hi)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text("{not valid json")

        mod.emit_dedup(
            "PreToolUse", "ivy-ready",
            system_message="[ivy-ready] indexed", hook_input=hi,
        )
        out = json.loads(capsys.readouterr().out)
        assert out["systemMessage"] == "[ivy-ready] indexed"
        rewritten = json.loads(cache_path.read_text())
        assert rewritten == {"ivy-ready": "[ivy-ready] indexed"}


class TestCheckMcpHealthFiltering:
    """Regression test for the PID-start-time filter on error
    categorisation in mcp/health.py, added 2026-05-02 to fix
    Issue B (old log lines reported as 'recent' indefinitely).
    """

    def test_filter_drops_pre_floor_lines_keeps_post_floor(
        self, tmp_path, monkeypatch, hook_scripts_dir
    ):
        # Place the fake mcp-*.pid file directly in tmp_path. Production's
        # _PID_DIR constant is monkeypatched below, so the directory name
        # is irrelevant.
        pid_file = tmp_path / "mcp-test-12345.pid"
        pid_file.write_text("12345")
        floor_ts = pid_file.stat().st_mtime

        # Load check-mcp-health fresh and override its PID dir constant.
        # Drop any prior cmh module so test isolation does not depend on
        # this being the only cmh test in the file (the autouse fixture
        # only cleans hook_utils).
        monkeypatch.delitem(sys.modules, "cmh", raising=False)
        spec = importlib.util.spec_from_file_location(
            "cmh", str(hook_scripts_dir / "mcp/health.py")
        )
        assert spec is not None and spec.loader is not None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        monkeypatch.setattr(mod, "_PID_DIR", str(tmp_path))

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


class TestSessionActivityHelpers:
    """Tests for mark_session_activity / is_session_active / _session_activity_path."""

    def _make_env(self, tmp_path, monkeypatch, session_id: str = "test-sa-42"):
        monkeypatch.setenv("TMPDIR", str(tmp_path))
        monkeypatch.setenv("IVY_SESSION_ID", session_id)
        monkeypatch.delenv("CLAUDE_SESSION_ID", raising=False)
        monkeypatch.delenv("CLAUDE_CODE_SESSION_ID", raising=False)
        return _import_hook_utils()

    def test_flag_created_on_first_call(self, tmp_path, monkeypatch):
        mod = self._make_env(tmp_path, monkeypatch)
        assert not mod.is_session_active()
        mod.mark_session_activity("test:signal")
        assert mod.is_session_active()

    def test_mark_idempotent(self, tmp_path, monkeypatch):
        mod = self._make_env(tmp_path, monkeypatch)
        mod.mark_session_activity("test:first")
        mod.mark_session_activity("test:second")
        assert mod.is_session_active()
        flag = mod._session_activity_path()
        # Should still be a single file, not duplicated
        assert flag.exists()

    def test_fail_closed_when_session_id_unknown(self, tmp_path, monkeypatch):
        monkeypatch.setenv("TMPDIR", str(tmp_path))
        mod = _import_hook_utils()
        # Patch resolve_session_id on the session sub-module where it is
        # called by is_session_active and mark_session_activity at runtime.
        session_mod = _import_hook_utils_session()
        monkeypatch.setattr(session_mod, "resolve_session_id", lambda *a, **kw: "unknown")
        # When session_id resolves to "unknown", is_session_active must return False
        # even if we have tried to mark activity.
        mod.mark_session_activity("test:unknown-session")
        # is_session_active fail-closes when sid == "unknown"
        assert mod.is_session_active() is False

    def test_flag_in_tmpdir_subdir(self, tmp_path, monkeypatch):
        mod = self._make_env(tmp_path, monkeypatch, session_id="sess-abc")
        mod.mark_session_activity("test:path-check")
        flag = tmp_path / "claude-ivy" / "session-activity-sess-abc.flag"
        assert flag.exists(), f"Expected flag at {flag}"

    def test_mark_suppresses_oserror(self, tmp_path, monkeypatch):
        """mark_session_activity must not raise even when the filesystem is unwritable."""
        monkeypatch.setenv("TMPDIR", "/dev/null/no-such-dir")
        monkeypatch.setenv("IVY_SESSION_ID", "test-sa-oserr")
        mod = _import_hook_utils()
        # Should not raise
        mod.mark_session_activity("test:oserror")

    def test_is_session_active_false_when_no_flag(self, tmp_path, monkeypatch):
        mod = self._make_env(tmp_path, monkeypatch, session_id="fresh-session")
        assert mod.is_session_active() is False
