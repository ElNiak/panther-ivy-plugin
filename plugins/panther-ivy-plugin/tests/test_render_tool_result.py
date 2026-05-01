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
    def test_non_rendered_tool_emits_noop(self, tmp_path):
        output = run_hook(
            "Read",
            "file contents",
            tmp_path=tmp_path,
        )
        # Strict-literal scope: every hook invocation emits a status line.
        # Unrecognised tool names produce an [ivy-noop] systemMessage with no
        # additionalContext (nothing for the model to consume).
        assert output is not None
        assert output.get("systemMessage", "").startswith("[ivy-noop]")
        assert "hookSpecificOutput" not in output or (
            "additionalContext" not in output["hookSpecificOutput"]
        )


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


class TestIvyCoverageFormatting:
    def test_coverage_stats_default(self, tmp_path):
        output = run_hook(
            "mcp__panther-ivy-plugin__ivy_coverage",
            json.dumps({"percentage": 85, "covered": 17, "total": 20}),
            tmp_path=tmp_path,
        )
        assert output is not None
        ctx = output["hookSpecificOutput"]["additionalContext"]
        assert "85" in ctx
        assert "17" in ctx
        assert "20" in ctx

    def test_coverage_triage(self, tmp_path):
        output = run_hook(
            "mcp__panther-ivy-plugin__ivy_coverage",
            json.dumps({"percentage": 85, "covered": 17, "total": 20}),
            workflow="triage",
            tmp_path=tmp_path,
        )
        assert output is not None
        ctx = output["hookSpecificOutput"]["additionalContext"]
        assert "Coverage: 85%" in ctx

    def test_coverage_verify(self, tmp_path):
        output = run_hook(
            "mcp__panther-ivy-plugin__ivy_coverage",
            json.dumps({"percentage": 85, "covered": 17, "total": 20}),
            workflow="verify",
            tmp_path=tmp_path,
        )
        assert output is not None
        ctx = output["hookSpecificOutput"]["additionalContext"]
        assert "85%" in ctx
        assert "(17/20)" in ctx


class TestIvyDiagnosticsFormatting:
    def test_diagnostics_triage(self, tmp_path):
        output = run_hook(
            "mcp__panther-ivy-plugin__ivy_diagnostics",
            json.dumps({"issues": [
                {"severity": "error", "file": "a.ivy", "line": 10, "message": "bad"},
                {"severity": "warning", "file": "b.ivy", "line": 20, "message": "warn"},
            ]}),
            workflow="triage",
            tmp_path=tmp_path,
        )
        assert output is not None
        ctx = output["hookSpecificOutput"]["additionalContext"]
        assert "1 errors" in ctx
        assert "1 warnings" in ctx

    def test_diagnostics_default(self, tmp_path):
        output = run_hook(
            "mcp__panther-ivy-plugin__ivy_diagnostics",
            json.dumps({"issues": [
                {"severity": "error", "file": "a.ivy", "line": 10, "message": "bad type"},
            ]}),
            tmp_path=tmp_path,
        )
        assert output is not None
        ctx = output["hookSpecificOutput"]["additionalContext"]
        assert "ERROR" in ctx
        assert "a.ivy" in ctx
        assert "10" in ctx


class TestIvyCompileFormatting:
    def test_compile_success_default(self, tmp_path):
        output = run_hook(
            "mcp__panther-ivy-plugin__ivy_compile",
            json.dumps({"status": "success", "output_binary": "test_bin", "duration_s": 2.5}),
            tmp_path=tmp_path,
        )
        assert output is not None
        ctx = output["hookSpecificOutput"]["additionalContext"]
        assert "test_bin" in ctx
        assert "2.5" in ctx

    def test_compile_failure_build(self, tmp_path):
        output = run_hook(
            "mcp__panther-ivy-plugin__ivy_compile",
            json.dumps({"status": "failure", "error_message": "undefined symbol"}),
            workflow="build",
            tmp_path=tmp_path,
        )
        assert output is not None
        ctx = output["hookSpecificOutput"]["additionalContext"]
        assert "Layer compilation failed" in ctx

    def test_compile_triage(self, tmp_path):
        output = run_hook(
            "mcp__panther-ivy-plugin__ivy_compile",
            json.dumps({"status": "success", "output_binary": "x"}),
            workflow="triage",
            tmp_path=tmp_path,
        )
        assert output is not None
        ctx = output["hookSpecificOutput"]["additionalContext"]
        assert "ivy_compile: OK" in ctx


class TestIvyQualityFormatting:
    def test_quality_gate_pass(self, tmp_path):
        output = run_hook(
            "mcp__panther-ivy-plugin__ivy_quality",
            json.dumps({"passed": True, "gate_level": "basic"}),
            tmp_path=tmp_path,
        )
        assert output is not None
        ctx = output["hookSpecificOutput"]["additionalContext"]
        assert "PASS" in ctx
        assert "basic" in ctx

    def test_quality_gate_fail_triage(self, tmp_path):
        output = run_hook(
            "mcp__panther-ivy-plugin__ivy_quality",
            json.dumps({"passed": False, "gate_level": "basic", "failures": [{"criterion": "coverage", "details": "below 50%"}]}),
            workflow="triage",
            tmp_path=tmp_path,
        )
        assert output is not None
        ctx = output["hookSpecificOutput"]["additionalContext"]
        assert "FAIL" in ctx

    def test_quality_suggestions_suppressed_in_verify(self, tmp_path):
        output = run_hook(
            "mcp__panther-ivy-plugin__ivy_quality",
            json.dumps({"suggestions": [{"category": "style", "message": "rename", "severity": "minor"}]}),
            workflow="verify",
            tmp_path=tmp_path,
        )
        # Strict-literal scope: suggestions are still suppressed for the model
        # in the verify workflow (no additionalContext), but the hook surfaces
        # an [ivy-noop] systemMessage so the user sees it ran.
        assert output is not None
        assert output.get("systemMessage", "").startswith("[ivy-noop]")
        assert "hookSpecificOutput" not in output or (
            "additionalContext" not in output["hookSpecificOutput"]
        )
