#!/usr/bin/env python3
"""Tests for route-user-prompt.py UserPromptSubmit hook."""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

SCRIPT = str(
    Path(__file__).resolve().parent.parent / "hooks" / "scripts" / "route-user-prompt.py"
)
PLUGIN_ROOT = str(Path(__file__).resolve().parent.parent)


def run_hook(prompt: str, env_overrides: dict | None = None) -> dict | None:
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = PLUGIN_ROOT
    env.pop("IVY_WORKSPACE_ROOT", None)
    if env_overrides:
        env.update(env_overrides)
    input_data = json.dumps({"prompt": prompt})
    # Run from a tmp cwd unless a workspace was explicitly requested via
    # env_overrides; otherwise route-user-prompt.py's CWD-walk fallback
    # finds the test repo's protocol-testing/ tree and fires routing when
    # the test expects silence.
    cwd = env.get("IVY_WORKSPACE_ROOT") or tempfile.gettempdir()
    result = subprocess.run(
        [sys.executable, SCRIPT],
        input=input_data,
        capture_output=True,
        text=True,
        timeout=5,
        env=env,
        cwd=cwd,
    )
    assert result.returncode == 0, f"Hook exited {result.returncode}: {result.stderr}"
    if result.stdout.strip():
        return json.loads(result.stdout)
    return None


def _extract_context(output: dict) -> str:
    return output["hookSpecificOutput"]["additionalContext"]


def test_keyword_match():
    output = run_hook("check my spec")
    assert output is not None
    ctx = _extract_context(output)
    assert "[ROUTING]" in ctx
    assert "'workflow-verify'" in ctx


def test_intent_pattern_match():
    output = run_hook("why did it fail?")
    assert output is not None
    ctx = _extract_context(output)
    assert "'workflow-verify'" in ctx


def test_priority_resolution():
    output = run_hook("something is broken, check the spec")
    assert output is not None
    ctx = _extract_context(output)
    assert "'workflow-triage'" in ctx


def test_no_match_fallthrough():
    output = run_hook("hello world")
    assert output is None


def test_learning_injection():
    output = run_hook("how does NCT work?")
    assert output is not None
    ctx = _extract_context(output)
    assert "[ROUTING:KNOWLEDGE]" in ctx
    assert "methodology-reference" in ctx


def test_active_workflow_suppression():
    with tempfile.TemporaryDirectory() as tmpdir:
        protocol_dir = os.path.join(tmpdir, "protocol-testing")
        state_dir = os.path.join(protocol_dir, ".panther-ivy")
        os.makedirs(state_dir)
        with open(os.path.join(state_dir, "active-workflow"), "w") as f:
            yaml.safe_dump(
                {"workflow": "workflow-build", "phase": "scaffold", "invocation_depth": 0,
                 "started": "2026-01-01T00:00:00+00:00"},
                f,
            )
        output = run_hook(
            "check my spec",
            env_overrides={"IVY_WORKSPACE_ROOT": tmpdir},
        )
        # When the active workflow ("workflow-build") differs from the best-
        # matching intent ("workflow-verify" via "check.*spec"), routing emits
        # a switch suggestion rather than suppressing — the user gets explicit
        # guidance that intent has diverged. context_switch is journaled too.
        assert output is not None
        ctx = _extract_context(output)
        assert "'workflow-verify'" in ctx


def test_explicit_switch_override():
    with tempfile.TemporaryDirectory() as tmpdir:
        protocol_dir = os.path.join(tmpdir, "protocol-testing")
        state_dir = os.path.join(protocol_dir, ".panther-ivy")
        os.makedirs(state_dir)
        with open(os.path.join(state_dir, "active-workflow"), "w") as f:
            yaml.safe_dump(
                {"workflow": "workflow-build", "phase": "scaffold", "invocation_depth": 0,
                 "started": "2026-01-01T00:00:00+00:00"},
                f,
            )
        output = run_hook(
            "switch to review workflow",
            env_overrides={"IVY_WORKSPACE_ROOT": tmpdir},
        )
        assert output is not None, "Should route when prompt contains switch keyword"
        ctx = _extract_context(output)
        assert "'workflow-review'" in ctx


def test_file_trigger_matching():
    output = run_hook("open quic_frame.ivy and look at it")
    assert output is not None
    ctx = _extract_context(output)
    assert "'workflow-verify'" in ctx


def test_learning_suppresses_workflow():
    """Learning intent that also matches a workflow keyword should suppress workflow routing."""
    output = run_hook("how does NCT verify specs?")
    assert output is not None
    ctx = _extract_context(output)
    assert "[ROUTING:KNOWLEDGE]" in ctx
    assert "[ROUTING] Activate" not in ctx, "Learning should suppress workflow activation"


if __name__ == "__main__":
    tests = [
        test_keyword_match,
        test_intent_pattern_match,
        test_priority_resolution,
        test_no_match_fallthrough,
        test_learning_injection,
        test_active_workflow_suppression,
        test_explicit_switch_override,
        test_file_trigger_matching,
        test_learning_suppresses_workflow,
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
