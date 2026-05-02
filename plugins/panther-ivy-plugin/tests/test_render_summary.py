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


_DEFAULT_SESSION_ID = "test-render-summary-default"


def run_hook(
    tmp_path: Path,
    workflow: str | None = None,
    phase: str | None = None,
    ivy_files: dict[str, str] | None = None,
    events_jsonl: str | None = None,
    *,
    session_active: bool = True,
    session_id: str = _DEFAULT_SESSION_ID,
) -> dict | None:
    """Run the hook with given state, return parsed JSON or None."""
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = PLUGIN_ROOT
    env["IVY_WORKSPACE_ROOT"] = str(tmp_path)
    env["IVY_SESSION_ID"] = session_id
    env["TMPDIR"] = str(tmp_path)

    if session_active:
        flag_dir = tmp_path / "claude-ivy"
        flag_dir.mkdir(parents=True, exist_ok=True)
        (flag_dir / f"session-activity-{session_id}.flag").touch()

    proto_dir = tmp_path / "protocol-testing"
    proto_dir.mkdir(exist_ok=True)

    # Ensure a scope anchor so _is_under_protocol_testing() can resolve .ivy files.
    bgp_panther_dir = proto_dir / "bgp" / ".panther-ivy"
    bgp_panther_dir.mkdir(parents=True, exist_ok=True)

    if workflow:
        state = {"workflow": workflow}
        if phase:
            state["phase"] = phase
        (bgp_panther_dir / "active-workflow").write_text(yaml.safe_dump(state))

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
    def test_emits_noop(self, tmp_path):
        # Strict-literal scope: no .ivy files modified produces an
        # [ivy-noop] systemMessage rather than total silence so the user
        # sees the Stop hook ran.
        output = run_hook(tmp_path)
        assert output is not None
        assert output.get("systemMessage", "").startswith("[ivy-noop]")
        assert "hookSpecificOutput" not in output or (
            "additionalContext" not in output["hookSpecificOutput"]
        )


class TestLintDetection:
    def test_detects_missing_lang_header(self, tmp_path):
        output = run_hook(
            tmp_path,
            ivy_files={"protocol-testing/bgp/test.ivy": "include order\n# no lang header\n"},
        )
        assert output is not None, "Should produce output for modified .ivy files"
        ctx = output["systemMessage"]
        assert "SESSION SUMMARY" in ctx
        assert "lint" in ctx.lower() or "missing" in ctx.lower()


class TestClaimCounting:
    def test_counts_resolved_claims(self, tmp_path):
        output = run_hook(
            tmp_path,
            ivy_files={"protocol-testing/bgp/test.ivy": "#lang ivy1.7\n# RESOLVED(rfc9000:4.1) confirmed\n"},
        )
        assert output is not None
        ctx = output["systemMessage"]
        assert "CLAIM" in ctx
        assert "1 resolution" in ctx or "1 confirmed" in ctx


class TestWorkflowAwareSummary:
    def test_refine_summary_includes_workflow(self, tmp_path):
        output = run_hook(
            tmp_path,
            workflow="refine",
            phase="compile",
            ivy_files={"protocol-testing/bgp/test.ivy": "#lang ivy1.7\nrelation foo(X:t)\n"},
        )
        assert output is not None
        ctx = output["systemMessage"]
        assert "SESSION SUMMARY" in ctx
        assert "WORKFLOW" in ctx or "Refine" in ctx


class TestFallbackBehavior:
    def test_no_workflow_uses_generic(self, tmp_path):
        output = run_hook(
            tmp_path,
            ivy_files={"protocol-testing/bgp/test.ivy": "#lang ivy1.7\nrelation foo(X:t)\n"},
        )
        assert output is not None
        ctx = output["systemMessage"]
        assert "SESSION SUMMARY" in ctx


def _run_hook_with_activity(
    tmp_path: Path,
    *,
    session_active: bool = False,
    ivy_files: dict[str, str] | None = None,
    session_id: str = "test-render-summary-42",
) -> dict | None:
    """Variant of run_hook that controls the session-activity flag."""
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = PLUGIN_ROOT
    env["IVY_WORKSPACE_ROOT"] = str(tmp_path)
    env["IVY_SESSION_ID"] = session_id
    env["TMPDIR"] = str(tmp_path)

    flag_dir = tmp_path / "claude-ivy"
    if session_active:
        flag_dir.mkdir(parents=True, exist_ok=True)
        (flag_dir / f"session-activity-{session_id}.flag").touch()

    subprocess.run(["git", "init"], cwd=str(tmp_path), capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=str(tmp_path), capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=str(tmp_path), capture_output=True)
    (tmp_path / ".gitkeep").write_text("")
    subprocess.run(["git", "add", ".gitkeep"], cwd=str(tmp_path), capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=str(tmp_path), capture_output=True)

    if ivy_files:
        for name, content in ivy_files.items():
            f = tmp_path / name
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(content)
        subprocess.run(["git", "add", "-A"], cwd=str(tmp_path), capture_output=True)

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


class TestActivityGate:
    def test_emits_noop_when_flag_absent(self, tmp_path):
        """With no activity flag, hook is silent regardless of .ivy files."""
        output = _run_hook_with_activity(
            tmp_path,
            session_active=False,
            ivy_files={"protocol-testing/bgp/.panther-ivy/.keep": "",
                       "protocol-testing/bgp/test.ivy": "#lang ivy1.7\nrelation foo(X:t)\n"},
        )
        assert output is not None
        assert output.get("systemMessage", "").startswith("[ivy-noop]"), (
            "render-summary should be silent when session is inactive"
        )

    def test_emits_summary_when_flag_present(self, tmp_path):
        """With activity flag set and .ivy files under protocol-testing, emits summary."""
        panther_ivy_dir = tmp_path / "protocol-testing" / "bgp" / ".panther-ivy"
        panther_ivy_dir.mkdir(parents=True, exist_ok=True)
        output = _run_hook_with_activity(
            tmp_path,
            session_active=True,
            ivy_files={"protocol-testing/bgp/test.ivy": "#lang ivy1.7\nrelation foo(X:t)\n"},
        )
        assert output is not None
        assert "SESSION SUMMARY" in output.get("systemMessage", ""), (
            "render-summary should emit summary when session is active and .ivy files exist"
        )


class TestLintScopeFilter:
    def test_repo_root_ivy_files_excluded(self, tmp_path):
        """Scratch .ivy files at repo root are NOT included in the lint pass."""
        panther_ivy_dir = tmp_path / "protocol-testing" / "bgp" / ".panther-ivy"
        panther_ivy_dir.mkdir(parents=True, exist_ok=True)
        output = _run_hook_with_activity(
            tmp_path,
            session_active=True,
            # Only repo-root .ivy files; none under protocol-testing/
            ivy_files={"scratch.ivy": "# no lang header\n", "empty.ivy": ""},
        )
        msg = output.get("systemMessage", "") if output else ""
        # The hook should emit a noop because no scope-filtered files exist
        assert msg.startswith("[ivy-noop]"), (
            f"Repo-root .ivy files should be excluded from scope-filtered lint; got: {msg!r}"
        )
