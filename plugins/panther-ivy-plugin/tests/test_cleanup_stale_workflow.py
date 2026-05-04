"""Tests for cleanup/stale-workflow.py SessionStart hook.

Per plan Task 8: the idle path (no active workflow) should NOT write
session_start to the journal. Only stale-clear and real resume paths write.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.unit

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = PLUGIN_ROOT / "hooks" / "scripts" / "cleanup/stale-workflow.py"


def _run_hook(tmp_path: Path, *, workflow: str | None = None, phase: str | None = None) -> dict:
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = str(PLUGIN_ROOT)
    env["IVY_WORKSPACE_ROOT"] = str(tmp_path)

    if workflow:
        proto_dir = tmp_path / "protocol-testing" / "bgp"
        panther_dir = proto_dir / ".panther-ivy"
        panther_dir.mkdir(parents=True, exist_ok=True)
        state: dict = {
            "workflow": workflow,
            "started": datetime.now(timezone.utc).isoformat(),
        }
        if phase:
            state["phase"] = phase
        (panther_dir / "active-workflow").write_text(yaml.safe_dump(state))

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


class TestIdlePath:
    def test_emits_noop_when_no_workflow(self, tmp_path):
        (tmp_path / "protocol-testing" / "bgp" / ".panther-ivy").mkdir(parents=True, exist_ok=True)
        out = _run_hook(tmp_path, workflow=None)
        msg = out.get("systemMessage", "")
        assert msg.startswith("[ivy-noop]"), f"Expected [ivy-noop] for idle path, got: {msg!r}"

    def test_no_session_start_written_when_no_workflow(self, tmp_path):
        panther_dir = tmp_path / "protocol-testing" / "bgp" / ".panther-ivy"
        panther_dir.mkdir(parents=True, exist_ok=True)
        journal = panther_dir / "workflow-journal.yaml"
        _run_hook(tmp_path, workflow=None)
        if journal.exists():
            data = yaml.safe_load(journal.read_text())
            events = data.get("events", [])
            session_start_events = [e for e in events if e.get("type") == "session_start"]
            assert not session_start_events, (
                "session_start should NOT be written in idle (no-workflow) path"
            )


class TestResumePath:
    def test_emits_noop_for_fresh_active_workflow(self, tmp_path):
        """Fresh, non-stale active workflow: defers to orchestrator, emits noop."""
        out = _run_hook(tmp_path, workflow="refine", phase="compile")
        msg = out.get("systemMessage", "")
        assert msg.startswith("[ivy-noop]"), f"Expected [ivy-noop] for resume, got: {msg!r}"

    def test_session_start_written_for_fresh_active_workflow(self, tmp_path):
        """Fresh resume writes session_start (stale-clear and resume paths stay unchanged)."""
        _run_hook(tmp_path, workflow="refine", phase="compile")
        proto_dir = tmp_path / "protocol-testing" / "bgp"
        journal = proto_dir / ".panther-ivy" / "workflow-journal.yaml"
        assert journal.exists(), "Journal should be written when there is a fresh active workflow"
        data = yaml.safe_load(journal.read_text())
        events = data if isinstance(data, list) else data.get("events", [])
        session_start_events = [e for e in events if e.get("type") == "session_start"]
        assert session_start_events, "session_start should be written for fresh active workflow (resume path)"
