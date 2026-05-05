"""Unit tests for hooks/scripts/lib/workflow_state/knowledge_capture.py."""

from __future__ import annotations

import importlib
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_HOOK_SCRIPTS_DIR = str(Path(__file__).resolve().parent.parent / "hooks" / "scripts")


@pytest.fixture(autouse=True)
def _patch_sys_path():
    sys.path.insert(0, _HOOK_SCRIPTS_DIR)
    yield
    sys.path.remove(_HOOK_SCRIPTS_DIR)
    for mod_name in list(sys.modules):
        if mod_name.startswith("lib.workflow_state"):
            del sys.modules[mod_name]


@pytest.fixture
def kc():
    """Import knowledge_capture module with hooks/scripts on sys.path."""
    if "lib.workflow_state.knowledge_capture" in sys.modules:
        return importlib.reload(sys.modules["lib.workflow_state.knowledge_capture"])
    return importlib.import_module("lib.workflow_state.knowledge_capture")


# ---------------------------------------------------------------- helpers


def _ts(offset_seconds: int = 0) -> str:
    """Return an ISO timestamp `offset_seconds` after a fixed reference."""
    base = datetime(2026, 5, 5, 12, 0, 0, tzinfo=timezone.utc)
    return (base + timedelta(seconds=offset_seconds)).isoformat()


@pytest.fixture
def journal_with_candidates() -> list[dict]:
    """Journal with fix_attempt, decision, error, and unsound gate_verdict entries."""
    return [
        {"ts": _ts(0), "type": "session_start", "payload": {}},
        {
            "ts": _ts(10),
            "type": "progress",
            "payload": {
                "kind": "fix_attempt",
                "key": "f.ivy",
                "attempt": 1,
                "text": "Catch deser_err",
            },
        },
        {
            "ts": _ts(20),
            "type": "decision",
            "payload": {"summary": "Use timestamps for correlation", "context": "F-C1"},
        },
        {
            "ts": _ts(30),
            "type": "error",
            "payload": {"pattern": "stale_pid", "file": "g.py", "line": 42},
        },
        {
            "ts": _ts(40),
            "type": "gate_verdict",
            "payload": {"gate": "g4", "verdict": "unsound", "patterns": ["#321"]},
        },
        {"ts": _ts(50), "type": "session_end", "payload": {"reason": "stop"}},
    ]


# ---------------------------------------------------------------- extract_candidates


def test_extract_candidates_returns_four_kinds(kc, journal_with_candidates):
    cands = kc.extract_candidates(
        journal_with_candidates, since_ts=_ts(0), until_ts=_ts(50)
    )
    kinds = {c["source_event_type"] for c in cands}
    assert kinds == {"progress", "decision", "error", "gate_verdict"}


def test_extract_candidates_skips_sound_gate_verdict(kc, journal_with_candidates):
    journal_with_candidates[4]["payload"]["verdict"] = "sound"
    cands = kc.extract_candidates(
        journal_with_candidates, since_ts=_ts(0), until_ts=_ts(50)
    )
    assert all(c["source_event_type"] != "gate_verdict" for c in cands)


def test_extract_candidates_includes_summary_and_evidence(kc, journal_with_candidates):
    cands = kc.extract_candidates(
        journal_with_candidates, since_ts=_ts(0), until_ts=_ts(50)
    )
    err_cand = next(c for c in cands if c["source_event_type"] == "error")
    assert err_cand["summary"] == "stale_pid"
    assert err_cand["evidence_paths"] == ["g.py:42"]


def test_extract_candidates_respects_window(kc, journal_with_candidates):
    cands = kc.extract_candidates(
        journal_with_candidates, since_ts=_ts(15), until_ts=_ts(35)
    )
    types = {c["source_event_type"] for c in cands}
    assert types == {"decision", "error"}


# ---------------------------------------------------------------- compute_candidate_id


def test_compute_candidate_id_is_deterministic(kc):
    cand = {
        "source_event_type": "error",
        "source_event_ts": _ts(30),
        "summary": "stale_pid",
        "evidence_paths": ["g.py:42"],
    }
    a = kc.compute_candidate_id(cand)
    b = kc.compute_candidate_id(cand)
    assert a == b
    assert len(a) == 12


def test_compute_candidate_id_collapses_whitespace_and_case(kc):
    cand_a = {
        "source_event_type": "decision",
        "source_event_ts": _ts(0),
        "summary": "Use Timestamps",
        "evidence_paths": [],
    }
    cand_b = {
        "source_event_type": "decision",
        "source_event_ts": _ts(99),
        "summary": "use   timestamps",
        "evidence_paths": [],
    }
    assert kc.compute_candidate_id(cand_a) == kc.compute_candidate_id(cand_b)


def test_compute_candidate_id_sorts_evidence_paths(kc):
    cand_a = {
        "source_event_type": "error",
        "source_event_ts": _ts(0),
        "summary": "x",
        "evidence_paths": ["b.py:2", "a.py:1"],
    }
    cand_b = {
        "source_event_type": "error",
        "source_event_ts": _ts(0),
        "summary": "x",
        "evidence_paths": ["a.py:1", "b.py:2"],
    }
    assert kc.compute_candidate_id(cand_a) == kc.compute_candidate_id(cand_b)


# ---------------------------------------------------------------- apply_dedup


def test_apply_dedup_drops_already_captured_candidates(kc):
    cand1 = {
        "source_event_type": "error",
        "source_event_ts": _ts(0),
        "summary": "x",
        "evidence_paths": ["a.py:1"],
    }
    cand2 = {
        "source_event_type": "error",
        "source_event_ts": _ts(0),
        "summary": "y",
        "evidence_paths": ["b.py:2"],
    }
    cand1_id = kc.compute_candidate_id(cand1)

    journal = [
        {
            "ts": _ts(0),
            "type": "knowledge_captured",
            "payload": {"candidate_id": cand1_id, "summary": "x"},
        },
    ]
    survivors = kc.apply_dedup([cand1, cand2], journal)
    survivor_ids = {kc.compute_candidate_id(c) for c in survivors}
    assert cand1_id not in survivor_ids
    assert kc.compute_candidate_id(cand2) in survivor_ids


def test_apply_dedup_returns_input_unchanged_when_no_prior_captures(kc):
    cands = [
        {
            "source_event_type": "decision",
            "source_event_ts": _ts(0),
            "summary": "z",
            "evidence_paths": [],
        }
    ]
    survivors = kc.apply_dedup(cands, journal=[])
    assert survivors == cands


# ---------------------------------------------------------------- aggregate votes


def test_aggregate_majority_keep(kc):
    votes = {"abc123def456": ["KEEP", "KEEP", "DROP"]}
    out = kc.aggregate_per_candidate_votes(votes)
    assert out["abc123def456"] == "KEEP"


def test_aggregate_majority_drop(kc):
    votes = {"abc": ["DROP", "DROP", "KEEP"]}
    assert kc.aggregate_per_candidate_votes(votes)["abc"] == "DROP"


def test_aggregate_one_one_one_resolves_to_defer(kc):
    votes = {"abc": ["KEEP", "DROP", "DEFER"]}
    assert kc.aggregate_per_candidate_votes(votes)["abc"] == "DEFER"


def test_aggregate_two_defer_resolves_to_defer(kc):
    votes = {"abc": ["DEFER", "DEFER", "KEEP"]}
    assert kc.aggregate_per_candidate_votes(votes)["abc"] == "DEFER"


def test_aggregate_rejects_invalid_vote_count(kc):
    with pytest.raises(ValueError, match="exactly 3"):
        kc.aggregate_per_candidate_votes({"abc": ["KEEP", "KEEP"]})
