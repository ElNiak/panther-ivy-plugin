"""Tests for hooks/scripts/render/project-md.py."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import yaml

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
HOOK = PLUGIN_ROOT / "hooks" / "scripts" / "render/project-md.py"


def _seed_workspace_state(root: Path, active_group: str) -> None:
    state_path = root / ".ivy-workspace-state.json"
    state_path.write_text(json.dumps({"active_group": active_group}))


def _seed_protocol(root: Path, protocol: str) -> Path:
    protocol_dir = root / "protocol-testing" / protocol
    panther_dir = protocol_dir / ".panther-ivy"
    panther_dir.mkdir(parents=True, exist_ok=True)
    (panther_dir / "workflow-journal.yaml").write_text(yaml.safe_dump({"events": []}))
    return protocol_dir


def _run_hook(payload: dict, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        check=False,
        cwd=str(cwd),
    )


def test_hook_invokes_render_for_set_action(tmp_path):
    _seed_workspace_state(tmp_path, "bgp")
    protocol_dir = _seed_protocol(tmp_path, "bgp")
    payload = {
        "tool_name": "mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_workflow_state",
        "tool_input": {"action": "set", "workflow": "scaffold", "phase": "1"},
    }
    proc = _run_hook(payload, tmp_path)
    assert proc.returncode == 0, proc.stderr
    assert (protocol_dir / "PROJECT.md").exists()


def test_hook_invokes_render_for_clear_action(tmp_path):
    _seed_workspace_state(tmp_path, "bgp")
    protocol_dir = _seed_protocol(tmp_path, "bgp")
    payload = {
        "tool_name": "mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_workflow_state",
        "tool_input": {"action": "clear", "protocol": "bgp"},
    }
    proc = _run_hook(payload, tmp_path)
    assert proc.returncode == 0, proc.stderr
    assert (protocol_dir / "PROJECT.md").exists()


def test_hook_skips_silently_for_get_action(tmp_path):
    _seed_workspace_state(tmp_path, "bgp")
    _seed_protocol(tmp_path, "bgp")
    payload = {
        "tool_name": "mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_workflow_state",
        "tool_input": {"action": "get"},
    }
    proc = _run_hook(payload, tmp_path)
    assert proc.returncode == 0
    # No PROJECT.md created and no systemMessage emitted
    assert not (tmp_path / "protocol-testing" / "bgp" / "PROJECT.md").exists()
    assert proc.stdout.strip() == ""


def test_hook_no_op_when_no_active_workspace(tmp_path):
    payload = {
        "tool_name": "mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_workflow_state",
        "tool_input": {"action": "set", "workflow": "scaffold"},
    }
    proc = _run_hook(payload, tmp_path)
    assert proc.returncode == 0
    output = json.loads(proc.stdout) if proc.stdout.strip() else {}
    assert "[ivy-project-md] no-op" in output.get("systemMessage", "")


def test_hook_no_op_when_protocol_dir_missing(tmp_path):
    _seed_workspace_state(tmp_path, "ghost")
    payload = {
        "tool_name": "mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_workflow_state",
        "tool_input": {"action": "set", "workflow": "scaffold"},
    }
    proc = _run_hook(payload, tmp_path)
    assert proc.returncode == 0
    output = json.loads(proc.stdout) if proc.stdout.strip() else {}
    assert "[ivy-project-md] no-op" in output.get("systemMessage", "")


def test_hook_emits_marker_on_success(tmp_path):
    _seed_workspace_state(tmp_path, "bgp")
    _seed_protocol(tmp_path, "bgp")
    payload = {
        "tool_name": "mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_workflow_state",
        "tool_input": {"action": "set", "workflow": "scaffold"},
    }
    proc = _run_hook(payload, tmp_path)
    assert proc.returncode == 0
    output = json.loads(proc.stdout)
    assert "[ivy-project-md]" in output.get("systemMessage", "")
    assert "PROJECT.md updated" in output.get("systemMessage", "")
