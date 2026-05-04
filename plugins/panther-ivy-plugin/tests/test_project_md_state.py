"""Tests for hooks/scripts/project_md_state.py."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PLUGIN_ROOT / "hooks" / "scripts"))

from lib.project_md_state import (  # noqa: E402
    PROJECT_MD_KEYS,
    ProjectMdSchemaError,
    load_project_md,
    write_project_md,
)


def _idle_state(protocol: str = "bgp") -> dict:
    return {
        "protocol": protocol,
        "version": "rfc4271",
        "mode": "idle",
        "phase": 0,
        "journal_pointer": ".panther-ivy/workflow-journal.yaml#null",
        "last_verify": {"status": "NOT_RUN", "timestamp": None, "isolate": None},
        "rfc_sections_covered": [],
        "open_counterexamples": [],
        "last_iut_run": None,
        "deferred_layers": [],
    }


def test_schema_keys_locked():
    assert PROJECT_MD_KEYS == frozenset(
        {
            "protocol",
            "version",
            "mode",
            "phase",
            "journal_pointer",
            "last_verify",
            "rfc_sections_covered",
            "open_counterexamples",
            "last_iut_run",
            "deferred_layers",
        }
    )


def test_roundtrip_idle_state(tmp_path):
    target = tmp_path / "PROJECT.md"
    state = _idle_state()
    write_project_md(target, state)
    loaded = load_project_md(target)
    assert loaded == state


def test_load_rejects_unknown_mode(tmp_path):
    target = tmp_path / "PROJECT.md"
    state = _idle_state()
    state["mode"] = "refactor"
    target.write_text(
        "---\n"
        + "\n".join(f"{k}: {v!r}" for k, v in state.items())
        + "\n---\n"
    )
    with pytest.raises(ProjectMdSchemaError, match="mode"):
        load_project_md(target)


def test_load_rejects_phase_out_of_range(tmp_path):
    target = tmp_path / "PROJECT.md"
    state = _idle_state()
    state["phase"] = 11
    write_path = target
    write_path.write_text(
        "---\nprotocol: bgp\nversion: rfc4271\nmode: idle\nphase: 11\n"
        "journal_pointer: '.panther-ivy/workflow-journal.yaml#null'\n"
        "last_verify:\n  status: NOT_RUN\n  timestamp: null\n  isolate: null\n"
        "rfc_sections_covered: []\nopen_counterexamples: []\n"
        "last_iut_run: null\ndeferred_layers: []\n---\n"
    )
    with pytest.raises(ProjectMdSchemaError, match="phase"):
        load_project_md(target)


def test_load_rejects_missing_keys(tmp_path):
    target = tmp_path / "PROJECT.md"
    target.write_text(
        "---\nprotocol: bgp\nmode: idle\nphase: 0\n---\n"
    )
    with pytest.raises(ProjectMdSchemaError, match="missing keys"):
        load_project_md(target)


def test_load_rejects_unknown_keys(tmp_path):
    target = tmp_path / "PROJECT.md"
    state = _idle_state()
    state["bogus_field"] = "x"
    with pytest.raises(ProjectMdSchemaError, match="unknown keys"):
        write_project_md(target, state)


def test_load_rejects_no_frontmatter(tmp_path):
    target = tmp_path / "PROJECT.md"
    target.write_text("just a body, no frontmatter\n")
    with pytest.raises(ProjectMdSchemaError, match="frontmatter"):
        load_project_md(target)


def test_write_creates_parent_dir(tmp_path):
    target = tmp_path / "deep" / "nested" / "PROJECT.md"
    write_project_md(target, _idle_state())
    assert target.exists()


def test_last_iut_run_can_be_null(tmp_path):
    target = tmp_path / "PROJECT.md"
    state = _idle_state()
    state["last_iut_run"] = None
    write_project_md(target, state)
    loaded = load_project_md(target)
    assert loaded["last_iut_run"] is None


def test_last_iut_run_with_valid_verdict(tmp_path):
    target = tmp_path / "PROJECT.md"
    state = _idle_state()
    state["last_iut_run"] = {
        "iut": "frr",
        "verdict": "NO_VIOLATION_FOUND",
        "timestamp": "2026-05-02T10:00:00Z",
    }
    write_project_md(target, state)
    loaded = load_project_md(target)
    assert loaded["last_iut_run"]["verdict"] == "NO_VIOLATION_FOUND"


def test_mode_idle_with_nonzero_phase_rejected(tmp_path):
    target = tmp_path / "PROJECT.md"
    state = _idle_state()
    state["phase"] = 4
    with pytest.raises(ProjectMdSchemaError, match="mode=idle requires phase=0"):
        write_project_md(target, state)


def test_mode_nonidle_with_zero_phase_rejected(tmp_path):
    target = tmp_path / "PROJECT.md"
    state = _idle_state()
    state["mode"] = "scaffold"
    state["phase"] = 0
    with pytest.raises(ProjectMdSchemaError, match="requires phase in"):
        write_project_md(target, state)


def test_mode_scaffold_with_valid_phase_accepted(tmp_path):
    target = tmp_path / "PROJECT.md"
    state = _idle_state()
    state["mode"] = "scaffold"
    state["phase"] = 4
    write_project_md(target, state)
    loaded = load_project_md(target)
    assert loaded["mode"] == "scaffold"
    assert loaded["phase"] == 4


def test_last_iut_run_rejects_invalid_verdict(tmp_path):
    target = tmp_path / "PROJECT.md"
    state = _idle_state()
    state["last_iut_run"] = {"iut": "frr", "verdict": "BOGUS", "timestamp": None}
    with pytest.raises(ProjectMdSchemaError, match="last_iut_run.verdict"):
        write_project_md(target, state)
