"""Tests for post-write-workflow-aware.py PostToolUse hook.

Activity-flag assertions per plan Task 5:
  - Specialist agent dispatch flips the flag.
  - Critic agent dispatch does NOT flip the flag.
  - Non-plugin agent dispatch does NOT flip the flag.
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
SCRIPT = PLUGIN_ROOT / "hooks" / "scripts" / "post-write-workflow-aware.py"

_SPECIALIST_AGENTS = [
    "panther-ivy-plugin:ivy-refiner-agent",
    "panther-ivy-plugin:ivy-experimenter-agent",
    "panther-ivy-plugin:ivy-builder-agent",
    "panther-ivy-plugin:ivy-reviewer-agent",
    "panther-ivy-plugin:ivy-triage-agent",
    "panther-ivy-plugin:ivy-meta-agent",
]

_CRITIC_AGENTS = [
    "panther-ivy-plugin:g-plan-critic",
    "panther-ivy-plugin:g-fidelity-critic",
    "panther-ivy-plugin:g-knowledge-critic",
]


def _run_hook(
    tmp_path: Path,
    tool_name: str,
    tool_input: dict,
    *,
    session_id: str = "test-workflow-aware-42",
) -> dict:
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = str(PLUGIN_ROOT)
    env["IVY_SESSION_ID"] = session_id
    env["TMPDIR"] = str(tmp_path)
    # No IVY_WORKSPACE_ROOT → WorkflowContext.current() returns None
    env.pop("IVY_WORKSPACE_ROOT", None)

    proc = subprocess.run(
        [sys.executable, str(SCRIPT)],
        input=json.dumps({"tool_name": tool_name, "tool_input": tool_input}),
        capture_output=True,
        text=True,
        timeout=10,
        env=env,
        cwd=str(tmp_path),
    )
    assert proc.returncode == 0, f"Hook exited {proc.returncode}: {proc.stderr}"
    return json.loads(proc.stdout) if proc.stdout.strip() else {}


def _flag_path(tmp_path: Path, session_id: str = "test-workflow-aware-42") -> Path:
    return tmp_path / "claude-ivy" / f"session-activity-{session_id}.flag"


class TestSpecialistAgentFlipsFlag:
    @pytest.mark.parametrize("subagent_type", _SPECIALIST_AGENTS)
    def test_specialist_agent_flips_flag(self, tmp_path, subagent_type):
        _run_hook(tmp_path, "Agent", {"subagent_type": subagent_type, "prompt": "fix bgp_connection.ivy"})
        assert _flag_path(tmp_path).exists(), (
            f"Activity flag should be set for specialist agent: {subagent_type}"
        )


class TestCriticAgentDoesNotFlipFlag:
    @pytest.mark.parametrize("subagent_type", _CRITIC_AGENTS)
    def test_critic_agent_does_not_flip_flag(self, tmp_path, subagent_type):
        _run_hook(tmp_path, "Agent", {"subagent_type": subagent_type, "prompt": "review this"})
        assert not _flag_path(tmp_path).exists(), (
            f"Activity flag must NOT be set for critic agent: {subagent_type}"
        )


class TestNonPluginAgentDoesNotFlipFlag:
    def test_explore_agent_no_flag(self, tmp_path):
        _run_hook(tmp_path, "Agent", {"subagent_type": "Explore", "prompt": "search for X"})
        assert not _flag_path(tmp_path).exists(), "Explore agent must NOT flip the activity flag"

    def test_non_plugin_agent_emits_noop(self, tmp_path):
        out = _run_hook(tmp_path, "Agent", {"subagent_type": "Explore", "prompt": "explore"})
        msg = out.get("systemMessage", "")
        assert msg.startswith("[ivy-noop]"), f"Non-plugin agent should emit noop, got: {msg!r}"
