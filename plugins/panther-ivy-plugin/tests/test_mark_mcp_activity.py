"""Tests for mcp/activity.py PostToolUse hook.

Verifies the flag flips on every mcp__plugin_panther-ivy-plugin_* tool call,
including ivy_workspace, ivy_workflow_state, and ivy_status (the three tools
the existing testing-tool matcher misses), and does NOT flip for non-plugin tools.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = PLUGIN_ROOT / "hooks" / "scripts" / "mcp/activity.py"


def _run_hook(tmp_path: Path, tool_name: str, *, session_id: str = "test-mcp-activity-42") -> dict:
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = str(PLUGIN_ROOT)
    env["IVY_SESSION_ID"] = session_id
    env["TMPDIR"] = str(tmp_path)

    proc = subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=json.dumps({"tool_name": tool_name, "tool_input": {}}),
        capture_output=True,
        text=True,
        timeout=10,
        env=env,
        cwd=str(tmp_path),
    )
    assert proc.returncode == 0, f"Hook exited {proc.returncode}: {proc.stderr}"
    return json.loads(proc.stdout) if proc.stdout.strip() else {}


def _flag_path(tmp_path: Path, session_id: str = "test-mcp-activity-42") -> Path:
    return tmp_path / "claude-ivy" / f"session-activity-{session_id}.flag"


class TestFlagOnPantherIvyMcpTools:
    @pytest.mark.parametrize("tool_name", [
        "mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_workspace",
        "mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_workflow_state",
        "mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_status",
        "mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_verify",
        "mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_compile",
        "mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_diagnostics",
        "mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_coverage",
        "mcp__plugin_panther-ivy-plugin_serena__find_symbol",
    ])
    def test_flag_set_for_panther_ivy_mcp_tool(self, tmp_path, tool_name):
        _run_hook(tmp_path, tool_name)
        assert _flag_path(tmp_path).exists(), (
            f"Activity flag should be created for panther-ivy MCP tool: {tool_name}"
        )

    def test_flag_uses_prefix_match_not_suffix(self, tmp_path):
        """Any tool starting with the plugin prefix flips the flag."""
        _run_hook(tmp_path, "mcp__plugin_panther-ivy-plugin_future-server__new_tool")
        assert _flag_path(tmp_path).exists(), "Broad prefix match should catch future tools"


class TestNoFlagForNonPantherTools:
    @pytest.mark.parametrize("tool_name", [
        "Read",
        "Write",
        "Bash",
        "mcp__plugin_other-plugin__some_tool",
        "ivy_verify",  # bare tool name without full MCP prefix
        "",
    ])
    def test_no_flag_for_non_panther_tool(self, tmp_path, tool_name):
        _run_hook(tmp_path, tool_name)
        assert not _flag_path(tmp_path).exists(), (
            f"Activity flag must NOT be created for non-panther tool: {tool_name!r}"
        )

    def test_emits_noop_for_non_panther_tool(self, tmp_path):
        out = _run_hook(tmp_path, "Read")
        msg = out.get("systemMessage", "")
        assert msg.startswith("[ivy-noop]"), f"Non-plugin tool should emit noop, got: {msg!r}"
