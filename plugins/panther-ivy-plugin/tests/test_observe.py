"""Tests for the consolidated observe.py observability script."""

import json
import subprocess
import os
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

OBSERVE_SCRIPT = (
    Path(__file__).parent.parent
    / "hooks"
    / "scripts"
    / "observability"
    / "observe.py"
)


def _run_observe(event_type: str, json_input: dict, env: dict | None = None) -> subprocess.CompletedProcess:
    run_env = os.environ.copy()
    run_env["IVY_OBSERVABILITY_ENABLED"] = "1"
    if env:
        run_env.update(env)
    return subprocess.run(
        ["python3", str(OBSERVE_SCRIPT), "--event", event_type],
        input=json.dumps(json_input),
        capture_output=True,
        text=True,
        timeout=10,
        env=run_env,
    )


class TestObserveParametric:
    """Test that the parametric observer handles all event types."""

    @pytest.mark.parametrize("event_type", [
        "SessionStart", "SessionEnd", "Stop",
        "SubagentStart", "SubagentStop",
        "UserPromptSubmit", "Notification",
        "PermissionRequest", "PreCompact",
        "PreToolUse", "PostToolUse",
    ])
    def test_event_logged(self, event_type, tmp_path):
        """Each event type should produce a JSONL event in the log directory."""
        session_dir = tmp_path / "sessions" / "test-sess"
        result = _run_observe(
            event_type,
            {"session_id": "test-sess", "tool_name": "Bash", "command": "ls"},
            env={"IVY_OBSERVABILITY_DIR": str(tmp_path)},
        )
        assert result.returncode == 0
        events_file = session_dir / "events.jsonl"
        assert events_file.exists(), f"No events.jsonl for {event_type}"
        lines = events_file.read_text().strip().split("\n")
        assert len(lines) >= 1
        event = json.loads(lines[-1])
        assert event["event_type"] == event_type

    def test_pre_tool_use_skips_read_tools(self, tmp_path):
        """PreToolUse should skip Read/Grep/Glob unless IVY_OBSERVABILITY_ALL_TOOLS."""
        session_dir = tmp_path / "sessions" / "test-sess"
        result = _run_observe(
            "PreToolUse",
            {"session_id": "test-sess", "tool_name": "Read"},
            env={"IVY_OBSERVABILITY_DIR": str(tmp_path)},
        )
        assert result.returncode == 0
        events_file = session_dir / "events.jsonl"
        assert not events_file.exists()

    def test_session_end_includes_tool_summary(self, tmp_path):
        """SessionEnd should read back events and produce a tool summary."""
        session_dir = tmp_path / "sessions" / "test-sess"
        session_dir.mkdir(parents=True)
        events_file = session_dir / "events.jsonl"
        events_file.write_text(
            json.dumps({"event_type": "PreToolUse", "payload": {"tool_name": "Bash"}}) + "\n"
            + json.dumps({"event_type": "PreToolUse", "payload": {"tool_name": "Bash"}}) + "\n"
            + json.dumps({"event_type": "PreToolUse", "payload": {"tool_name": "Read"}}) + "\n"
        )
        result = _run_observe(
            "SessionEnd",
            {"session_id": "test-sess", "reason": "logout"},
            env={"IVY_OBSERVABILITY_DIR": str(tmp_path)},
        )
        assert result.returncode == 0
        lines = events_file.read_text().strip().split("\n")
        last = json.loads(lines[-1])
        assert last["event_type"] == "SessionEnd"
        assert "tool_summary" in last.get("payload", {})

    def test_invalid_json_graceful(self):
        """Invalid JSON on stdin should exit 0 silently."""
        result = subprocess.run(
            ["python3", str(OBSERVE_SCRIPT), "--event", "Stop"],
            input="not json",
            capture_output=True,
            text=True,
            timeout=10,
            env={**os.environ, "IVY_OBSERVABILITY_ENABLED": "1"},
        )
        assert result.returncode == 0

    def test_disabled_via_env(self, tmp_path):
        """IVY_OBSERVABILITY_ENABLED=0 should skip logging."""
        result = _run_observe(
            "SessionStart",
            {"session_id": "test-sess"},
            env={
                "IVY_OBSERVABILITY_DIR": str(tmp_path),
                "IVY_OBSERVABILITY_ENABLED": "0",
            },
        )
        assert result.returncode == 0
        session_dir = tmp_path / "sessions" / "test-sess"
        assert not session_dir.exists() or not (session_dir / "events.jsonl").exists()
