"""Tests for scripts/statusline/render-mode-phase.py."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import yaml

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = PLUGIN_ROOT / "scripts" / "statusline" / "render-mode-phase.py"


def _seed_workspace_state(root: Path, active_group: str) -> None:
    state_path = root / ".ivy-workspace-state.json"
    state_path.write_text(json.dumps({"active_group": active_group}))


def _write_project_md(root: Path, protocol: str, mode: str, phase: int) -> None:
    state = {
        "protocol": protocol,
        "version": "rfc4271",
        "mode": mode,
        "phase": phase,
        "journal_pointer": ".panther-ivy/workflow-journal.yaml#null",
        "last_verify": {"status": "NOT_RUN", "timestamp": None, "isolate": None},
        "rfc_sections_covered": [],
        "open_counterexamples": [],
        "last_iut_run": None,
        "deferred_layers": [],
    }
    target = root / "protocol-testing" / protocol / "PROJECT.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    body = yaml.safe_dump(state, sort_keys=False)
    target.write_text(f"---\n{body}---\n")


def _run(root: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--root", str(root)],
        capture_output=True,
        text=True,
        check=False,
    )


def test_renders_mode_and_phase(tmp_path):
    _seed_workspace_state(tmp_path, "bgp")
    _write_project_md(tmp_path, "bgp", "scaffold", 4)
    proc = _run(tmp_path)
    assert proc.returncode == 0
    assert "Mode: SCAFFOLD" in proc.stdout
    assert "Phase: 4/10" in proc.stdout
    assert "core stack" in proc.stdout


def test_silent_when_no_active_workspace(tmp_path):
    proc = _run(tmp_path)
    assert proc.returncode == 0
    assert proc.stdout.strip() == ""


def test_silent_when_idle_mode(tmp_path):
    _seed_workspace_state(tmp_path, "bgp")
    _write_project_md(tmp_path, "bgp", "idle", 0)
    proc = _run(tmp_path)
    assert proc.returncode == 0
    assert proc.stdout.strip() == ""


def test_silent_when_project_md_absent(tmp_path):
    _seed_workspace_state(tmp_path, "bgp")
    proc = _run(tmp_path)
    assert proc.returncode == 0
    assert proc.stdout.strip() == ""


def test_phase_name_omitted_for_unknown_phase(tmp_path):
    _seed_workspace_state(tmp_path, "bgp")
    _write_project_md(tmp_path, "bgp", "scaffold", 0)
    # phase 0 is idle by definition; mode != idle with phase 0 is not in _PHASE_NAMES
    proc = _run(tmp_path)
    assert proc.returncode == 0
    # Mode != idle so we still print, but no phase name suffix
    assert "Mode: SCAFFOLD | Phase: 0/10" in proc.stdout
    # No parenthetical suffix
    assert "Phase: 0/10\n" in proc.stdout or "Phase: 0/10 \n" in proc.stdout


def test_silent_on_invalid_project_md(tmp_path):
    _seed_workspace_state(tmp_path, "bgp")
    target = tmp_path / "protocol-testing" / "bgp" / "PROJECT.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("not yaml frontmatter\n")
    proc = _run(tmp_path)
    assert proc.returncode == 0
    assert proc.stdout.strip() == ""
