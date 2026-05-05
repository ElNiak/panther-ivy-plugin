"""Unit tests for G0b handlers in posttooluse/gates/gate_handlers.py."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from hooks.scripts.posttooluse.gates import gate_handlers as gh


def _ts(offset: int = 0) -> str:
    base = datetime(2026, 5, 5, 12, 0, 0, tzinfo=timezone.utc)
    return (base + timedelta(seconds=offset)).isoformat()


# ---------------------------------------------------------------- parse_g0b


def test_parse_g0b_extracts_edit_artifact():
    hook_input = {
        "tool_name": "Edit",
        "tool_input": {"file_path": "protocol-testing/bgp/bgp.ivy"},
        "tool_response": {"success": True, "summary": "1 line changed"},
    }
    ctx = gh.parse_g0b(hook_input)
    assert ctx is not None  # narrow Optional[dict] for type-checkers
    assert ctx["tool_name"] == "Edit"
    assert ctx["artifact"] == "protocol-testing/bgp/bgp.ivy"
    assert "tool_input_digest" in ctx and len(ctx["tool_input_digest"]) > 0
    assert ctx["tool_result_excerpt"]  # non-empty


def test_parse_g0b_extracts_bash_artifact():
    hook_input = {
        "tool_name": "Bash",
        "tool_input": {"command": "pytest tests/", "description": "Run tests"},
        "tool_response": {"output": "5 passed"},
    }
    ctx = gh.parse_g0b(hook_input)
    assert ctx is not None  # narrow Optional[dict] for type-checkers
    assert ctx["tool_name"] == "Bash"
    assert ctx["artifact"] == "pytest tests/"


def test_parse_g0b_returns_none_on_missing_artifact():
    hook_input = {"tool_name": "Edit", "tool_input": {}, "tool_response": {}}
    assert gh.parse_g0b(hook_input) is None


# ---------------------------------------------------------------- predicate_g0b


def _pa(ts):
    return {"ts": ts, "type": "plan_approved", "payload": {}}


def _gd(ts):
    return {"ts": ts, "type": "gate_dispatched", "payload": {"gate": "g0b"}}


def _gv(ts):
    return {
        "ts": ts,
        "type": "gate_verdict",
        "payload": {"gate": "g0b", "verdict": "sound"},
    }


@pytest.fixture
def fixed_now():
    """Patch lib.workflow_state.knowledge_capture (or wherever predicate reads 'now') to a fixed value."""
    fixed = datetime(2026, 5, 5, 12, 0, 0, tzinfo=timezone.utc)
    with patch.object(gh, "_now_iso", return_value=fixed.isoformat()):
        yield fixed


def test_predicate_returns_false_when_no_plan_approved(fixed_now):
    journal = []
    ctx = {"protocol_dir": "/tmp/no-such-dir"}
    with patch.object(gh, "get_journal_entries", return_value=journal):
        assert gh.predicate_g0b(ctx) is False


def test_predicate_returns_true_when_plan_approved_unpaired(fixed_now):
    journal = [_pa(_ts(0))]
    ctx = {"protocol_dir": "/tmp/x"}
    with patch.object(gh, "get_journal_entries", return_value=journal):
        assert gh.predicate_g0b(ctx) is True


def test_predicate_returns_false_when_gate_verdict_after_plan_approved(fixed_now):
    journal = [_pa(_ts(0)), _gd(_ts(10)), _gv(_ts(20))]
    ctx = {"protocol_dir": "/tmp/x"}
    with patch.object(gh, "get_journal_entries", return_value=journal):
        assert gh.predicate_g0b(ctx) is False  # cycle closed


def test_predicate_returns_false_when_cycle_in_flight(fixed_now):
    # gate_dispatched at ts=-30 minutes; "now" is 12:00:00. Within 2h → cycle in flight.
    in_flight_ts = (fixed_now - timedelta(minutes=30)).isoformat()
    pa_ts = (fixed_now - timedelta(minutes=35)).isoformat()
    journal = [_pa(pa_ts), _gd(in_flight_ts)]
    ctx = {"protocol_dir": "/tmp/x"}
    with patch.object(gh, "get_journal_entries", return_value=journal):
        assert gh.predicate_g0b(ctx) is False


def test_predicate_returns_true_on_orphan_gate_dispatched(fixed_now):
    # gate_dispatched at ts=-3h with NO gate_verdict after → orphan, should re-fire.
    orphan_ts = (fixed_now - timedelta(hours=3)).isoformat()
    pa_ts = (fixed_now - timedelta(hours=3, minutes=5)).isoformat()
    journal = [_pa(pa_ts), _gd(orphan_ts)]
    ctx = {"protocol_dir": "/tmp/x"}
    with patch.object(gh, "get_journal_entries", return_value=journal):
        assert gh.predicate_g0b(ctx) is True


# ---------------------------------------------------------------- dispatch_g0b


def test_dispatch_g0b_appends_gate_dispatched_with_plan_approved_ts(
    fixed_now, tmp_path
):
    journal_dir = tmp_path / "proto"
    journal_dir.mkdir()
    journal = [_pa(_ts(0))]

    captured_appends = []
    captured_emits = []

    def fake_append(protocol_dir, event_type, payload, workflow=None, phase=None):
        captured_appends.append({"event_type": event_type, "payload": payload})
        return True

    def fake_emit(event, system_message, additional_context=None):
        captured_emits.append(
            {
                "event": event,
                "system_message": system_message,
                "additional_context": additional_context,
            }
        )

    ctx = {
        "protocol_dir": str(journal_dir),
        "tool_name": "Edit",
        "artifact": "protocol-testing/bgp/bgp.ivy",
        "tool_input_digest": "abc123",
        "tool_result_excerpt": "1 line changed",
        "workflow_ctx": None,
    }

    with patch.object(gh, "get_journal_entries", return_value=journal), patch.object(
        gh, "append_journal_event", side_effect=fake_append
    ), patch.object(gh, "emit_hook_output", side_effect=fake_emit):
        gh.dispatch_g0b(ctx)

    assert len(captured_appends) == 1
    payload = captured_appends[0]["payload"]
    assert payload["gate"] == "g0b"
    assert payload["trigger"] == "run-gate.py --id g0b"
    assert payload["plan_approved_ts"] == _ts(0)

    assert len(captured_emits) == 1
    assert "[G0b plan-fidelity gate]" in captured_emits[0]["system_message"]
    assert "appended to journal at" in captured_emits[0]["system_message"]
    assert "g-fidelity-critic" in captured_emits[0]["additional_context"]
