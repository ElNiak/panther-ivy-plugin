"""Tests for record/session-end.py Stop hook.

Three scenarios per the plan's Decisions locked table:
  1. Activity flag absent → one-line confirmation noop, no journal write.
  2. Activity flag present, WorkflowContext None → activity noop, no journal write.
  3. Activity flag present, WorkflowContext populated → session_end appended to journal.
"""

from __future__ import annotations

import importlib
import json
import os
import sys
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.unit

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = PLUGIN_ROOT / "hooks" / "scripts" / "record/session-end.py"
HOOK_SCRIPTS_DIR = PLUGIN_ROOT / "hooks" / "scripts"


def _run_hook(
    tmp_path: Path,
    *,
    session_active: bool = False,
    workflow: str | None = None,
    phase: str | None = None,
    session_id: str = "test-session-42",
) -> dict:
    """Run record/session-end.py with controlled session-activity and workflow state."""
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = str(PLUGIN_ROOT)
    env["IVY_SESSION_ID"] = session_id

    flag_dir = tmp_path / "claude-ivy"
    env["TMPDIR"] = str(tmp_path)

    if session_active:
        flag_dir.mkdir(parents=True, exist_ok=True)
        (flag_dir / f"session-activity-{session_id}.flag").touch()

    if workflow:
        proto_dir = tmp_path / "protocol-testing" / "bgp"
        panther_dir = proto_dir / ".panther-ivy"
        panther_dir.mkdir(parents=True, exist_ok=True)
        state: dict = {"workflow": workflow}
        if phase:
            state["phase"] = phase
        (panther_dir / "active-workflow").write_text(yaml.safe_dump(state))
        env["IVY_WORKSPACE_ROOT"] = str(tmp_path)

    import subprocess
    proc = subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=json.dumps({}),
        capture_output=True,
        text=True,
        timeout=10,
        env=env,
        cwd=str(tmp_path),
    )
    assert proc.returncode == 0, f"Hook exited {proc.returncode}: {proc.stderr}"
    return json.loads(proc.stdout) if proc.stdout.strip() else {}


class TestFlagAbsent:
    def test_emits_noop_when_session_inactive(self, tmp_path):
        out = _run_hook(tmp_path, session_active=False)
        msg = out.get("systemMessage", "")
        assert msg.startswith("[ivy-noop]"), f"Expected [ivy-noop] prefix, got: {msg!r}"
        assert "no ivy activity" in msg

    def test_no_journal_written_when_session_inactive(self, tmp_path):
        _run_hook(tmp_path, session_active=False, workflow="refine", phase="compile")
        proto_dir = tmp_path / "protocol-testing" / "bgp"
        journal = proto_dir / ".panther-ivy" / "workflow-journal.yaml"
        if journal.exists():
            data = yaml.safe_load(journal.read_text())
            events = data if isinstance(data, list) else data.get("events", [])
            session_end_events = [e for e in events if e.get("type") == "session_end"]
            assert not session_end_events, "session_end should not be written when flag is absent"


class TestFlagPresentNoWorkflow:
    def test_emits_noop_when_no_workflow_context(self, tmp_path):
        out = _run_hook(tmp_path, session_active=True, workflow=None)
        msg = out.get("systemMessage", "")
        assert msg.startswith("[ivy-noop]"), f"Expected [ivy-noop] prefix, got: {msg!r}"
        assert "activity recorded" in msg or "no orchestrator workflow" in msg

    def test_no_journal_written_when_no_workflow(self, tmp_path):
        _run_hook(tmp_path, session_active=True, workflow=None)
        proto_dir = tmp_path / "protocol-testing" / "bgp"
        journal = proto_dir / ".panther-ivy" / "workflow-journal.yaml"
        assert not journal.exists(), "No journal should be written when no workflow context"


class TestFlagPresentWithWorkflow:
    def test_emits_journal_message_when_active(self, tmp_path):
        out = _run_hook(
            tmp_path, session_active=True, workflow="refine", phase="compile"
        )
        msg = out.get("systemMessage", "")
        assert "[ivy-session]" in msg, f"Expected [ivy-session] prefix, got: {msg!r}"
        assert "session_end" in msg
        assert "journal" in msg

    def test_journal_contains_session_end_event(self, tmp_path):
        _run_hook(
            tmp_path, session_active=True, workflow="refine", phase="compile"
        )
        proto_dir = tmp_path / "protocol-testing" / "bgp"
        journal = proto_dir / ".panther-ivy" / "workflow-journal.yaml"
        assert journal.exists(), "Journal should be written when flag is present and workflow is active"
        data = yaml.safe_load(journal.read_text())
        events = data if isinstance(data, list) else data.get("events", [])
        session_end_events = [e for e in events if e.get("type") == "session_end"]
        assert session_end_events, "session_end event should be in journal"
        assert session_end_events[0].get("payload", {}).get("clean") is True
