"""Tests for render-summary.py Stop hook."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.unit

SCRIPT = str(
    Path(__file__).resolve().parent.parent / "hooks" / "scripts" / "render-summary.py"
)
PLUGIN_ROOT = str(Path(__file__).resolve().parent.parent)


def run_hook(
    tmp_path: Path,
    workflow: str | None = None,
    phase: str | None = None,
    ivy_files: dict[str, str] | None = None,
    events_jsonl: str | None = None,
) -> dict | None:
    """Run the hook with given state, return parsed JSON or None."""
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = PLUGIN_ROOT
    env["IVY_WORKSPACE_ROOT"] = str(tmp_path)

    proto_dir = tmp_path / "protocol-testing"
    proto_dir.mkdir(exist_ok=True)

    if workflow:
        state_dir = proto_dir / ".panther-ivy"
        state_dir.mkdir(exist_ok=True)
        state = {"workflow": workflow}
        if phase:
            state["phase"] = phase
        (state_dir / "active-workflow").write_text(yaml.safe_dump(state))

    # Initialize a real git repo so find_modified_ivy_files() works
    subprocess.run(["git", "init"], cwd=str(tmp_path), capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=str(tmp_path), capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=str(tmp_path), capture_output=True)
    # Create initial commit so HEAD exists
    (tmp_path / ".gitkeep").write_text("")
    subprocess.run(["git", "add", ".gitkeep"], cwd=str(tmp_path), capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=str(tmp_path), capture_output=True)

    if ivy_files:
        for name, content in ivy_files.items():
            f = tmp_path / name
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(content)
        # Stage the ivy files so git diff HEAD shows them
        subprocess.run(["git", "add", "-A"], cwd=str(tmp_path), capture_output=True)

    if events_jsonl:
        obs_dir = tmp_path / ".observability" / "sessions" / "test-session"
        obs_dir.mkdir(parents=True, exist_ok=True)
        (obs_dir / "events.jsonl").write_text(events_jsonl)
        env["IVY_OBSERVABILITY_DIR"] = str(tmp_path / ".observability" / "sessions")

    result = subprocess.run(
        [sys.executable, SCRIPT],
        input="{}",
        capture_output=True,
        text=True,
        timeout=10,
        env=env,
        cwd=str(tmp_path),
    )
    assert result.returncode == 0, f"Hook exited {result.returncode}: {result.stderr}"
    if result.stdout.strip():
        return json.loads(result.stdout)
    return None


class TestNoModifiedFiles:
    def test_exits_silently(self, tmp_path):
        output = run_hook(tmp_path)
        assert output is None


class TestLintDetection:
    def test_detects_missing_lang_header(self, tmp_path):
        output = run_hook(
            tmp_path,
            ivy_files={"test.ivy": "include order\n# no lang header\n"},
        )
        assert output is not None, "Should produce output for modified .ivy files"
        ctx = output["systemMessage"]
        assert "SESSION SUMMARY" in ctx
        assert "lint" in ctx.lower() or "missing" in ctx.lower()


class TestClaimCounting:
    def test_counts_resolved_claims(self, tmp_path):
        output = run_hook(
            tmp_path,
            ivy_files={"test.ivy": "#lang ivy1.7\n# RESOLVED(rfc9000:4.1) confirmed\n"},
        )
        assert output is not None
        ctx = output["systemMessage"]
        assert "CLAIM" in ctx
        assert "1 resolution" in ctx or "1 confirmed" in ctx


class TestWorkflowAwareSummary:
    def test_verify_summary_includes_workflow(self, tmp_path):
        output = run_hook(
            tmp_path,
            workflow="verify",
            phase="compile",
            ivy_files={"test.ivy": "#lang ivy1.7\nrelation foo(X:t)\n"},
        )
        assert output is not None
        ctx = output["systemMessage"]
        assert "SESSION SUMMARY" in ctx
        assert "WORKFLOW" in ctx or "Verify" in ctx


class TestFallbackBehavior:
    def test_no_workflow_uses_generic(self, tmp_path):
        output = run_hook(
            tmp_path,
            ivy_files={"test.ivy": "#lang ivy1.7\nrelation foo(X:t)\n"},
        )
        assert output is not None
        ctx = output["systemMessage"]
        assert "SESSION SUMMARY" in ctx
