#!/usr/bin/env python3
"""Tests for workflow-aware hook scripts (post-write)."""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

POST_WRITE_SCRIPT = str(
    Path(__file__).resolve().parent.parent
    / "hooks"
    / "scripts"
    / "post-write-workflow-aware.py"
)


def _make_workflow_env(tmpdir: str) -> dict:
    """Create a tmp workspace with an active-workflow file and return env dict."""
    protocol_dir = os.path.join(tmpdir, "protocol-testing")
    state_dir = os.path.join(protocol_dir, ".panther-ivy")
    os.makedirs(state_dir)
    with open(os.path.join(state_dir, "active-workflow"), "w") as f:
        yaml.safe_dump(
            {
                "workflow": "review",
                "phase": "analyze",
                "invocation_depth": 0,
                "started": "2026-01-01T00:00:00+00:00",
            },
            f,
        )
    env = os.environ.copy()
    env["IVY_WORKSPACE_ROOT"] = tmpdir
    return env


def _run_post_write(file_path: str, env: dict | None = None) -> dict | None:
    input_data = json.dumps({"tool_input": {"file_path": file_path}})
    result = subprocess.run(
        [sys.executable, POST_WRITE_SCRIPT],
        input=input_data,
        capture_output=True,
        text=True,
        timeout=5,
        env=env or os.environ.copy(),
    )
    assert result.returncode == 0, f"Hook exited {result.returncode}: {result.stderr}"
    if result.stdout.strip():
        return json.loads(result.stdout)
    return None


def test_post_write_no_workflow_suggests_review():
    env = os.environ.copy()
    env.pop("IVY_WORKSPACE_ROOT", None)
    output = _run_post_write("/some/path/model.ivy", env=env)
    assert output is not None
    ctx = output["hookSpecificOutput"]["additionalContext"]
    assert "outside of a workflow" in ctx
    assert "review workflow" in ctx


def test_post_write_active_workflow_suppressed():
    with tempfile.TemporaryDirectory() as tmpdir:
        env = _make_workflow_env(tmpdir)
        output = _run_post_write("/some/path/model.ivy", env=env)
        # Strict-literal hook output discipline: every code path emits a
        # status line. The orientation suggestion must be suppressed when a
        # workflow is active, but a [ivy-noop] line is still emitted.
        assert output is not None
        assert output.get("systemMessage", "").startswith("[ivy-noop]")
        assert "hookSpecificOutput" not in output or (
            "additionalContext" not in output["hookSpecificOutput"]
        )


def test_post_write_non_ivy_file_silent():
    output = _run_post_write("/some/path/readme.md")
    # Strict-literal scope: no orientation context for non-.ivy files, but
    # the hook still surfaces a [ivy-noop] status line so the user sees it ran.
    assert output is not None
    assert output.get("systemMessage", "").startswith("[ivy-noop]")
    assert "hookSpecificOutput" not in output or (
        "additionalContext" not in output["hookSpecificOutput"]
    )


if __name__ == "__main__":
    tests = [
        test_post_write_no_workflow_suggests_review,
        test_post_write_active_workflow_suppressed,
        test_post_write_non_ivy_file_silent,
    ]
    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            print(f"  PASS: {test.__name__}")
            passed += 1
        except Exception as e:
            print(f"  FAIL: {test.__name__}: {e}")
            failed += 1
    print(f"\n{passed}/{passed + failed} tests passed")
    sys.exit(1 if failed else 0)
