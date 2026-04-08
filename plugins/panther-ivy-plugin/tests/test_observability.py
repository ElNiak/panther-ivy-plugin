"""Tests for observability hook scripts and the log_event utility.

Unit tests import log_event directly.
Integration tests invoke each hook script via subprocess.
"""

import json
import os
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Resolve log_event.py so we can import it directly for unit tests
_OBS_DIR = (
    Path(__file__).resolve().parent.parent
    / "hooks"
    / "scripts"
    / "observability"
)


def _run_python_hook(
    script: Path,
    json_input: dict,
    env_extra: dict | None = None,
    event_type: str | None = None,
) -> subprocess.CompletedProcess:
    """Run a Python hook script with JSON piped to stdin."""
    run_env = os.environ.copy()
    if env_extra:
        run_env.update(env_extra)
    cmd = ["python3", str(script)]
    if event_type:
        cmd.extend(["--event", event_type])
    return subprocess.run(
        cmd,
        input=json.dumps(json_input),
        capture_output=True,
        text=True,
        timeout=10,
        env=run_env,
    )


def _read_last_event(events_file: Path) -> dict:
    """Read the last JSONL line from an events file."""
    lines = events_file.read_text().strip().splitlines()
    assert len(lines) > 0, "events.jsonl is empty"
    return json.loads(lines[-1])


# ---------------------------------------------------------------------------
# Unit tests: log_event.py
# ---------------------------------------------------------------------------

import sys

sys.path.insert(0, str(_OBS_DIR))
from log_event import _resolve_log_dir, log_event


class TestLogEvent:
    """Unit tests for the log_event utility."""

    def test_creates_directory_and_file(self, tmp_path):
        log_dir = tmp_path / "sessions" / "test-sess"
        result = log_event("TestEvent", "test-sess", log_dir_override=log_dir)
        assert result is not None
        assert result.exists()
        assert result.name == "events.jsonl"

    def test_appends_jsonl_lines(self, tmp_path):
        log_dir = tmp_path / "sessions" / "test-sess"
        for i in range(3):
            log_event("Event", "test-sess", {"i": i}, log_dir_override=log_dir)
        lines = (log_dir / "events.jsonl").read_text().strip().splitlines()
        assert len(lines) == 3
        for line in lines:
            parsed = json.loads(line)
            assert "timestamp" in parsed

    def test_event_fields(self, tmp_path):
        log_dir = tmp_path / "sessions" / "test-sess"
        log_event("PreToolUse", "sess-123", {"tool": "Bash"}, log_dir_override=log_dir)
        event = _read_last_event(log_dir / "events.jsonl")
        assert event["event_type"] == "PreToolUse"
        assert event["session_id"] == "sess-123"
        assert event["payload"]["tool"] == "Bash"
        assert "timestamp" in event
        assert "cwd" in event

    def test_empty_payload_omitted(self, tmp_path):
        log_dir = tmp_path / "sessions" / "test-sess"
        log_event("Stop", "sess-1", None, log_dir_override=log_dir)
        event = _read_last_event(log_dir / "events.jsonl")
        assert "payload" not in event

    def test_never_raises(self, tmp_path):
        # None session_id
        result = log_event("Bad", None, log_dir_override=tmp_path / "x")
        # Should return a path or None, but not raise
        assert result is None or isinstance(result, Path)

    def test_missing_session_id_normalized_to_unknown(self, tmp_path):
        log_dir = tmp_path / "sessions" / "unknown"
        log_event("Stop", "", log_dir_override=log_dir)
        event = _read_last_event(log_dir / "events.jsonl")
        assert event["session_id"] == "unknown"

    def test_extended_schema_fields(self, tmp_path):
        log_dir = tmp_path / "sessions" / "sess-42"
        log_event(
            "PostToolUse",
            "sess-42",
            {"tool": "Bash"},
            log_dir_override=log_dir,
            channel="mcp",
            name="ivy_verify",
            status="error",
            duration_ms=12.345,
            call_id="cid-42",
        )
        event = _read_last_event(log_dir / "events.jsonl")
        assert event["channel"] == "mcp"
        assert event["name"] == "ivy_verify"
        assert event["status"] == "error"
        assert event["call_id"] == "cid-42"
        assert event["duration_ms"] == 12.35

    def test_disabled_via_env(self, tmp_path, monkeypatch):
        monkeypatch.setenv("IVY_OBSERVABILITY_ENABLED", "0")
        log_dir = tmp_path / "sessions" / "test-sess"
        result = log_event("Event", "sess", log_dir_override=log_dir)
        assert result is None
        assert not (log_dir / "events.jsonl").exists()

    def test_resolve_log_dir_explicit(self, monkeypatch, tmp_path):
        monkeypatch.setenv("IVY_OBSERVABILITY_DIR", str(tmp_path / "obs"))
        path = _resolve_log_dir("sess-1")
        assert path == tmp_path / "obs" / "sessions" / "sess-1"

    def test_resolve_log_dir_workspace(self, monkeypatch, tmp_path):
        monkeypatch.delenv("IVY_OBSERVABILITY_DIR", raising=False)
        monkeypatch.setenv("IVY_WORKSPACE_ROOT", str(tmp_path / "ws"))
        path = _resolve_log_dir("sess-2")
        assert path == tmp_path / "ws" / ".observability" / "sessions" / "sess-2"

    def test_resolve_log_dir_fallback(self, monkeypatch):
        monkeypatch.delenv("IVY_OBSERVABILITY_DIR", raising=False)
        monkeypatch.delenv("IVY_WORKSPACE_ROOT", raising=False)
        path = _resolve_log_dir("sess-3")
        assert path == Path("/tmp/ivy-observability") / "sessions" / "sess-3"


# ---------------------------------------------------------------------------
# Integration tests: observability hook scripts
# ---------------------------------------------------------------------------

# Map of event_type -> (sample_input, expected_payload_keys)
# All events except PostToolUseFailure use observe.py --event <type>
_OBSERVE_SPECS = {
    "SessionStart": (
        {
            "session_id": "int-test",
            "source": "startup",
            "model": "claude-opus-4-6",
            "agent_type": "main",
            "permission_mode": "default",
        },
        ["source", "model", "agent_type", "permission_mode"],
    ),
    "PreToolUse": (
        {
            "session_id": "int-test",
            "tool_name": "Bash",
            "tool_use_id": "tu_1",
            "tool_input": {"command": "ls -la"},
        },
        ["tool_name", "tool_use_id", "tool_summary"],
    ),
    "PostToolUse": (
        {
            "session_id": "int-test",
            "tool_name": "Bash",
            "tool_use_id": "tu_2",
        },
        ["tool_name", "tool_use_id", "is_mcp_tool"],
    ),
    "Stop": (
        {
            "session_id": "int-test",
            "stop_hook_active": False,
            "last_assistant_message": "Done.",
        },
        ["stop_hook_active", "message_length"],
    ),
    "SubagentStart": (
        {
            "session_id": "int-test",
            "agent_id": "agent-42",
            "agent_type": "Explore",
        },
        ["agent_id", "agent_type"],
    ),
    "SubagentStop": (
        {
            "session_id": "int-test",
            "agent_id": "agent-42",
            "agent_type": "Explore",
            "stop_hook_active": False,
            "last_assistant_message": "Found it.",
        },
        ["agent_id", "agent_type", "stop_hook_active", "message_length"],
    ),
    "SessionEnd": (
        {
            "session_id": "int-test",
            "reason": "prompt_input_exit",
        },
        ["reason"],
    ),
    "PreCompact": (
        {
            "session_id": "int-test",
            "trigger": "auto",
            "custom_instructions": "keep context",
        },
        ["trigger", "has_custom_instructions"],
    ),
    "UserPromptSubmit": (
        {
            "session_id": "int-test",
            "prompt": "Fix the bug in auth module",
        },
        ["prompt_length", "prompt_preview"],
    ),
    "Notification": (
        {
            "session_id": "int-test",
            "notification_type": "permission_prompt",
            "title": "Permission needed",
            "message": "Allow Bash?",
        },
        ["notification_type", "title", "message_length"],
    ),
    "PermissionRequest": (
        {
            "session_id": "int-test",
            "tool_name": "Bash",
            "permission_suggestions": ["allow", "deny"],
        },
        ["tool_name", "suggestion_count"],
    ),
}

# obs_post_tool_use_failure.py is still a standalone script (has circuit breaker logic)
_STANDALONE_SPECS = {
    "obs_post_tool_use_failure.py": (
        "PostToolUseFailure",
        {
            "session_id": "int-test",
            "tool_name": "Bash",
            "tool_use_id": "tu_3",
            "error": "command not found",
            "is_interrupt": False,
        },
        ["tool_name", "tool_use_id", "error", "is_interrupt"],
    ),
}

_OBSERVE_SCRIPT = _OBS_DIR / "observe.py"


class TestObsHooksHappyPath:
    """Integration tests: observe.py --event produces correct JSONL output."""

    @pytest.fixture(params=list(_OBSERVE_SPECS.keys()))
    def event_type(self, request):
        return request.param

    def test_happy_path_observe(self, tmp_path, has_python3, event_type):
        if not has_python3:
            pytest.skip("python3 required")

        sample_input, expected_keys = _OBSERVE_SPECS[event_type]
        result = _run_python_hook(
            _OBSERVE_SCRIPT,
            sample_input,
            env_extra={"IVY_OBSERVABILITY_DIR": str(tmp_path)},
            event_type=event_type,
        )
        assert result.returncode == 0

        events_file = tmp_path / "sessions" / "int-test" / "events.jsonl"
        assert events_file.exists(), f"events.jsonl not created for {event_type}"

        event = _read_last_event(events_file)
        assert event["event_type"] == event_type
        assert event["session_id"] == "int-test"
        for key in expected_keys:
            assert key in event.get("payload", {}), (
                f"Missing payload key '{key}' in {event_type} output"
            )

    @pytest.fixture(params=list(_STANDALONE_SPECS.keys()))
    def standalone_spec(self, request):
        return request.param, _STANDALONE_SPECS[request.param]

    def test_happy_path_standalone(self, obs_scripts_dir, tmp_path, has_python3, standalone_spec):
        if not has_python3:
            pytest.skip("python3 required")

        script_name, (event_type, sample_input, expected_keys) = standalone_spec
        script = obs_scripts_dir / script_name
        result = _run_python_hook(
            script,
            sample_input,
            env_extra={"IVY_OBSERVABILITY_DIR": str(tmp_path)},
        )
        assert result.returncode == 0

        events_file = tmp_path / "sessions" / "int-test" / "events.jsonl"
        assert events_file.exists(), f"events.jsonl not created by {script_name}"

        event = _read_last_event(events_file)
        assert event["event_type"] == event_type


class TestObsHooksGracefulFailure:
    """Integration tests: hooks exit 0 on bad input."""

    @pytest.fixture(params=list(_OBSERVE_SPECS.keys()))
    def event_type(self, request):
        return request.param

    def test_invalid_json(self, has_python3, event_type):
        if not has_python3:
            pytest.skip("python3 required")

        result = subprocess.run(
            ["python3", str(_OBSERVE_SCRIPT), "--event", event_type],
            input="not valid json {{{",
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0

    def test_missing_session_id(self, tmp_path, has_python3, event_type):
        if not has_python3:
            pytest.skip("python3 required")

        result = _run_python_hook(
            _OBSERVE_SCRIPT,
            {"tool_name": "Bash"},
            env_extra={"IVY_OBSERVABILITY_DIR": str(tmp_path)},
            event_type=event_type,
        )
        assert result.returncode == 0


class TestObsPreToolUseSummarization:
    """Tests for tool input summarization in observe.py --event PreToolUse."""

    def _run(self, tmp_path, tool_name, tool_input):
        result = _run_python_hook(
            _OBSERVE_SCRIPT,
            {
                "session_id": "sum-test",
                "tool_name": tool_name,
                "tool_use_id": "tu_sum",
                "tool_input": tool_input,
            },
            env_extra={
                "IVY_OBSERVABILITY_DIR": str(tmp_path),
                "IVY_OBSERVABILITY_ALL_TOOLS": "1",
            },
            event_type="PreToolUse",
        )
        assert result.returncode == 0
        events_file = tmp_path / "sessions" / "sum-test" / "events.jsonl"
        return _read_last_event(events_file)

    def test_bash_command_truncated(self, tmp_path, has_python3):
        if not has_python3:
            pytest.skip("python3 required")
        event = self._run(tmp_path, "Bash", {"command": "x" * 500})
        summary = event["payload"]["tool_summary"]
        assert len(summary["command"]) == 200

    def test_write_shows_file_path_and_length(self, tmp_path, has_python3):
        if not has_python3:
            pytest.skip("python3 required")
        event = self._run(
            tmp_path, "Write",
            {"file_path": "/tmp/test.py", "content": "hello world"},
        )
        summary = event["payload"]["tool_summary"]
        assert summary["file_path"] == "/tmp/test.py"
        assert summary["content_length"] == 11

    def test_mcp_tool_parsed(self, tmp_path, has_python3):
        if not has_python3:
            pytest.skip("python3 required")
        event = self._run(
            tmp_path,
            "mcp__plugin_ivy__ivy_verify",
            {"file": "model.ivy"},
        )
        summary = event["payload"]["tool_summary"]
        assert summary["mcp_server"] == "plugin_ivy"
        assert summary["mcp_tool"] == "ivy_verify"

    def test_read_shows_file_path(self, tmp_path, has_python3):
        if not has_python3:
            pytest.skip("python3 required")
        event = self._run(
            tmp_path, "Read",
            {"file_path": "/tmp/data.txt"},
        )
        summary = event["payload"]["tool_summary"]
        assert summary["file_path"] == "/tmp/data.txt"

    def test_unknown_tool_shows_keys(self, tmp_path, has_python3):
        if not has_python3:
            pytest.skip("python3 required")
        event = self._run(
            tmp_path, "CustomTool",
            {"alpha": 1, "beta": 2},
        )
        summary = event["payload"]["tool_summary"]
        assert set(summary["keys"]) == {"alpha", "beta"}
