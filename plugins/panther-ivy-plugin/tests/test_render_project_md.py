"""Tests for scripts/render-project-md.py."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import yaml

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
RENDER_SCRIPT = PLUGIN_ROOT / "scripts" / "render-project-md.py"


def _seed_journal(protocol_dir: Path, events: list) -> None:
    panther_dir = protocol_dir / ".panther-ivy"
    panther_dir.mkdir(parents=True, exist_ok=True)
    (panther_dir / "workflow-journal.yaml").write_text(yaml.safe_dump({"events": events}))


def _read_state(project_md: Path) -> dict:
    text = project_md.read_text()
    fence = text.split("---\n", 2)
    return yaml.safe_load(fence[1])


def _run_render(protocol_dir: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(RENDER_SCRIPT), "--protocol-dir", str(protocol_dir)],
        capture_output=True,
        text=True,
        check=False,
    )


def test_derives_idle_when_no_events(tmp_path):
    protocol_dir = tmp_path / "bgp"
    _seed_journal(protocol_dir, [])
    result = _run_render(protocol_dir)
    assert result.returncode == 0, result.stderr
    state = _read_state(protocol_dir / "PROJECT.md")
    assert state["mode"] == "idle"
    assert state["phase"] == 0
    assert state["rfc_sections_covered"] == []
    assert state["last_verify"]["status"] == "NOT_RUN"
    assert state["last_iut_run"] is None


def test_derives_scaffold_phase_3_from_phase_transition_event(tmp_path):
    protocol_dir = tmp_path / "bgp"
    _seed_journal(
        protocol_dir,
        [
            {
                "type": "phase_transition",
                "workflow": "scaffold",
                "phase": 3,
                "timestamp": "2026-05-02T10:00:00Z",
                "event_id": "evt-001",
            }
        ],
    )
    result = _run_render(protocol_dir)
    assert result.returncode == 0, result.stderr
    state = _read_state(protocol_dir / "PROJECT.md")
    assert state["mode"] == "scaffold"
    assert state["phase"] == 3
    assert state["journal_pointer"].endswith("#evt-001")


def test_uses_latest_phase_transition_when_multiple(tmp_path):
    protocol_dir = tmp_path / "bgp"
    _seed_journal(
        protocol_dir,
        [
            {"type": "phase_transition", "workflow": "scaffold", "phase": 1, "event_id": "a"},
            {"type": "phase_transition", "workflow": "scaffold", "phase": 4, "event_id": "b"},
            {"type": "phase_transition", "workflow": "refine", "phase": 8, "event_id": "c"},
        ],
    )
    result = _run_render(protocol_dir)
    assert result.returncode == 0, result.stderr
    state = _read_state(protocol_dir / "PROJECT.md")
    assert state["mode"] == "refine"
    assert state["phase"] == 8


def test_last_verify_from_g4_gate(tmp_path):
    protocol_dir = tmp_path / "bgp"
    _seed_journal(
        protocol_dir,
        [
            {
                "type": "gate_verdict",
                "gate_id": "g4_verification",
                "verdict": "SAT",
                "isolate": "bgp_connection_test",
                "timestamp": "2026-05-02T11:00:00Z",
                "event_id": "g4-1",
            },
        ],
    )
    result = _run_render(protocol_dir)
    assert result.returncode == 0, result.stderr
    state = _read_state(protocol_dir / "PROJECT.md")
    assert state["last_verify"]["status"] == "SAT"
    assert state["last_verify"]["isolate"] == "bgp_connection_test"


def test_open_counterexamples_close_on_sat(tmp_path):
    protocol_dir = tmp_path / "bgp"
    _seed_journal(
        protocol_dir,
        [
            {
                "type": "gate_verdict",
                "gate_id": "g4_verification",
                "verdict": "UNSAT",
                "isolate": "bgp_connection_test",
                "phase": 8,
                "timestamp": "2026-05-02T10:00:00Z",
                "event_id": "1",
            },
            {
                "type": "gate_verdict",
                "gate_id": "g4_verification",
                "verdict": "UNSAT",
                "isolate": "bgp_speaker_test",
                "phase": 8,
                "timestamp": "2026-05-02T10:30:00Z",
                "event_id": "2",
            },
            {
                "type": "gate_verdict",
                "gate_id": "g4_verification",
                "verdict": "SAT",
                "isolate": "bgp_connection_test",
                "phase": 8,
                "timestamp": "2026-05-02T11:00:00Z",
                "event_id": "3",
            },
        ],
    )
    result = _run_render(protocol_dir)
    assert result.returncode == 0, result.stderr
    state = _read_state(protocol_dir / "PROJECT.md")
    isolates = {cx["isolate"] for cx in state["open_counterexamples"]}
    assert isolates == {"bgp_speaker_test"}


def test_last_iut_run_from_g5_gate(tmp_path):
    protocol_dir = tmp_path / "bgp"
    _seed_journal(
        protocol_dir,
        [
            {
                "type": "gate_verdict",
                "gate_id": "g5_trace",
                "verdict": "NON_COMPLIANT",
                "iut": "frr",
                "timestamp": "2026-05-02T12:00:00Z",
                "event_id": "g5-1",
            },
        ],
    )
    result = _run_render(protocol_dir)
    assert result.returncode == 0, result.stderr
    state = _read_state(protocol_dir / "PROJECT.md")
    assert state["last_iut_run"]["verdict"] == "NON_COMPLIANT"
    assert state["last_iut_run"]["iut"] == "frr"


def test_unknown_workflow_falls_back_to_idle(tmp_path):
    protocol_dir = tmp_path / "bgp"
    _seed_journal(
        protocol_dir,
        [{"type": "phase_transition", "workflow": "navigate", "phase": 1, "event_id": "n1"}],
    )
    result = _run_render(protocol_dir)
    assert result.returncode == 0, result.stderr
    state = _read_state(protocol_dir / "PROJECT.md")
    assert state["mode"] == "idle"


def test_protocol_arg_resolves_under_cwd(tmp_path, monkeypatch):
    (tmp_path / "protocol-testing" / "bgp").mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    result = subprocess.run(
        [sys.executable, str(RENDER_SCRIPT), "--protocol", "bgp"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "protocol-testing" / "bgp" / "PROJECT.md").exists()
