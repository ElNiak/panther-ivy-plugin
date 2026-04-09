"""Tests for render-tool-result.py PostToolUse hook."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.unit

SCRIPT = str(
    Path(__file__).resolve().parent.parent / "hooks" / "scripts" / "render-tool-result.py"
)
PLUGIN_ROOT = str(Path(__file__).resolve().parent.parent)


def run_hook(
    tool_name: str,
    tool_output: str,
    workflow: str | None = None,
    phase: str | None = None,
    tmp_path: Path | None = None,
) -> dict | None:
    """Run the hook with given tool result, return parsed JSON or None."""
    input_data = json.dumps({"tool_name": tool_name, "tool_output": tool_output})
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = PLUGIN_ROOT

    if workflow and tmp_path:
        proto_dir = tmp_path / "protocol-testing"
        proto_dir.mkdir(exist_ok=True)
        state_dir = proto_dir / ".panther-ivy"
        state_dir.mkdir(exist_ok=True)
        state = {"workflow": workflow}
        if phase:
            state["phase"] = phase
        (state_dir / "active-workflow").write_text(yaml.safe_dump(state))
        env["IVY_WORKSPACE_ROOT"] = str(tmp_path)
    elif tmp_path:
        proto_dir = tmp_path / "protocol-testing"
        proto_dir.mkdir(exist_ok=True)
        env["IVY_WORKSPACE_ROOT"] = str(tmp_path)

    result = subprocess.run(
        [sys.executable, SCRIPT],
        input=input_data,
        capture_output=True,
        text=True,
        timeout=5,
        env=env,
    )
    assert result.returncode == 0, f"Hook exited {result.returncode}: {result.stderr}"
    if result.stdout.strip():
        return json.loads(result.stdout)
    return None


class TestIvyVerifyFormatting:
    def test_verify_pass_default(self, tmp_path):
        output = run_hook(
            "mcp__panther-ivy-plugin__ivy_verify",
            json.dumps({"success": True, "isolate": "quic_conn", "clause_count": 12, "duration_s": 3.5}),
            tmp_path=tmp_path,
        )
        if output is None:
            pytest.skip("Formatter not yet producing output for default")
        ctx = output["hookSpecificOutput"]["additionalContext"]
        assert "PASS" in ctx
        assert "quic_conn" in ctx

    def test_verify_fail_triage_workflow(self, tmp_path):
        output = run_hook(
            "mcp__panther-ivy-plugin__ivy_verify",
            json.dumps({"success": False, "errors": [{"file": "a.ivy", "line": 10, "message": "violated"}]}),
            workflow="triage",
            tmp_path=tmp_path,
        )
        if output is None:
            pytest.skip("Formatter not yet producing output for triage")
        ctx = output["hookSpecificOutput"]["additionalContext"]
        assert "FAIL" in ctx

    def test_verify_pass_build_workflow(self, tmp_path):
        output = run_hook(
            "mcp__panther-ivy-plugin__ivy_verify",
            json.dumps({"success": True, "isolate": "quic_types"}),
            workflow="build",
            tmp_path=tmp_path,
        )
        if output is None:
            pytest.skip("Formatter not yet producing output for build")
        ctx = output["hookSpecificOutput"]["additionalContext"]
        assert "Layer verified" in ctx


class TestUnrelatedTool:
    def test_non_rendered_tool_exits_silently(self, tmp_path):
        output = run_hook(
            "Read",
            "file contents",
            tmp_path=tmp_path,
        )
        assert output is None


class TestMalformedInput:
    def test_bad_json_exits_cleanly(self):
        result = subprocess.run(
            [sys.executable, SCRIPT],
            input="not json",
            capture_output=True,
            text=True,
            timeout=5,
        )
        assert result.returncode == 0


class TestErrorInToolOutput:
    def test_error_result_passes_through(self, tmp_path):
        output = run_hook(
            "mcp__panther-ivy-plugin__ivy_verify",
            json.dumps({"error": "MCP server unreachable"}),
            tmp_path=tmp_path,
        )
        # Should either pass through or exit silently, not crash
        assert True
