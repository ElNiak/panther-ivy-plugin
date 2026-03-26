#!/usr/bin/env python3
"""Tests for interaction-checkpoint.py PostToolUse hook."""

import json
import subprocess
import sys
from pathlib import Path

SCRIPT = str(
    Path(__file__).resolve().parent.parent / "hooks" / "scripts" / "interaction-checkpoint.py"
)


def run_hook(tool_name: str, tool_output: str) -> dict | None:
    """Run the hook script with given input, return parsed JSON output or None."""
    input_data = json.dumps({"tool_name": tool_name, "tool_output": tool_output})
    result = subprocess.run(
        [sys.executable, SCRIPT],
        input=input_data,
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert result.returncode == 0, f"Hook exited with code {result.returncode}"
    if result.stdout.strip():
        return json.loads(result.stdout)
    return None


def test_ivy_verify_failure():
    output = run_hook("ivy_verify", '{"result": "FAIL", "error": "invariant violated"}')
    assert output is not None
    ctx = output["hookSpecificOutput"]["additionalContext"]
    assert "INTERACTION CHECKPOINT" in ctx
    assert "Verification Claim" in ctx


def test_ivy_verify_pass():
    output = run_hook("ivy_verify", '{"result": "OK", "status": "all checks pass"}')
    assert output is None, "Should not inject reminder for passing verification"


def test_ivy_coverage_gaps():
    output = run_hook("ivy_coverage", '{"gaps": [{"req": "rfc9000:4.1", "status": "uncovered"}]}')
    assert output is not None
    ctx = output["hookSpecificOutput"]["additionalContext"]
    assert "Coverage Gap" in ctx


def test_ivy_coverage_clean():
    output = run_hook("ivy_coverage", '{"coverage": "100%", "all_covered": true}')
    assert output is None, "Should not inject reminder for full coverage"


def test_ivy_extract_requirements():
    output = run_hook("ivy_extract_requirements", '{"requirements": [{"level": "MUST", "text": "test"}]}')
    assert output is not None
    ctx = output["hookSpecificOutput"]["additionalContext"]
    assert "RFC Mapping" in ctx


def test_ivy_quality_gate_failure():
    output = run_hook("ivy_quality", '{"gate_result": "fail", "score": 45}')
    assert output is not None
    ctx = output["hookSpecificOutput"]["additionalContext"]
    assert "quality" in ctx.lower()


def test_ivy_quality_gate_pass():
    output = run_hook("ivy_quality", '{"gate_result": "pass", "score": 95}')
    assert output is None, "Should not inject reminder for passing quality gate"


def test_unrelated_tool():
    output = run_hook("Read", '{"content": "some file content"}')
    assert output is None, "Should not inject reminder for unrelated tools"


def test_malformed_input():
    """Hook should handle malformed input gracefully."""
    result = subprocess.run(
        [sys.executable, SCRIPT],
        input="not json",
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert result.returncode == 0, "Hook should exit 0 even on bad input"


if __name__ == "__main__":
    tests = [
        test_ivy_verify_failure,
        test_ivy_verify_pass,
        test_ivy_coverage_gaps,
        test_ivy_coverage_clean,
        test_ivy_extract_requirements,
        test_ivy_quality_gate_failure,
        test_ivy_quality_gate_pass,
        test_unrelated_tool,
        test_malformed_input,
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
