#!/usr/bin/env python3
"""Tests for adversarial-gate dispatch hooks (G1-G5).

Verifies the trigger-detector hooks emit the expected `additionalContext`
directive when their conditions are met and stay silent otherwise. Also
verifies they write `gate_dispatched` breadcrumbs to the workflow journal.
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import yaml

PLUGIN_ROOT = str(Path(__file__).resolve().parent.parent)
SCRIPTS = Path(PLUGIN_ROOT) / "hooks" / "scripts"

ASSESS_MODELING = str(SCRIPTS / "assess-modeling.py")
ASSESS_TESTSPEC = str(SCRIPTS / "assess-testspec.py")
ASSESS_TRACE = str(SCRIPTS / "assess-trace.py")
ROUTE_USER_PROMPT = str(SCRIPTS / "route-user-prompt.py")
RECORD_WORKFLOW_ERROR = str(SCRIPTS / "record-workflow-error.py")


def _run(script: str, payload: dict, env_overrides: "dict[str, str] | None" = None) -> "dict | None":
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = PLUGIN_ROOT
    env.pop("IVY_WORKSPACE_ROOT", None)
    if env_overrides:
        env.update(env_overrides)
    result = subprocess.run(
        [sys.executable, script],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=5,
        env=env,
    )
    assert result.returncode == 0, f"{script} exited {result.returncode}: {result.stderr}"
    if result.stdout.strip():
        return json.loads(result.stdout)
    return None


def _make_workspace(tmpdir: str, *, workflow: str, phase: str, methodology: str = "nct", scaffold_state: bool = True) -> "dict[str, str]":
    """Create an Ivy-workspace skeleton inside tmpdir.

    Layout:
      tmpdir/
        protocol-testing/
          bgp/
            .panther-ivy/
              active-workflow      (yaml)
              scaffold-state.yaml     (yaml, if scaffold_state=True)
            bgp_stack/
              bgp_open.ivy         (placeholder layer file)
            bgp_tests/
              bgp_server_test_session.ivy  (placeholder test spec)
    """
    proto = Path(tmpdir) / "protocol-testing" / "bgp"
    state_dir = proto / ".panther-ivy"
    state_dir.mkdir(parents=True)
    with open(state_dir / "active-workflow", "w") as f:
        yaml.safe_dump(
            {"workflow": workflow, "phase": phase, "invocation_depth": 0,
             "started": "2026-01-01T00:00:00+00:00"},
            f,
        )
    if scaffold_state:
        with open(state_dir / "scaffold-state.yaml", "w") as f:
            yaml.safe_dump(
                {"workflow": workflow, "protocol": "bgp", "methodology": methodology,
                 "started": "2026-01-01T00:00:00+00:00",
                 "layers": {"bgp_open": {"file": "bgp_stack/bgp_open.ivy", "status": "pending"}}},
                f,
            )
    layer_dir = proto / "bgp_stack"
    layer_dir.mkdir()
    layer_file = layer_dir / "bgp_open.ivy"
    layer_file.write_text("#lang ivy1.7\n")
    test_dir = proto / "bgp_tests"
    test_dir.mkdir()
    test_file = test_dir / "bgp_server_test_session.ivy"
    test_file.write_text("#lang ivy1.7\n")
    return {
        "tmpdir": tmpdir,
        "protocol_dir": str(proto),
        "layer_file": str(layer_file),
        "test_file": str(test_file),
        "journal": str(state_dir / "workflow-journal.yaml"),
    }


def _read_journal(path: str) -> "list[dict[str, Any]]":
    if not os.path.exists(path):
        return []
    with open(path) as f:
        data = yaml.safe_load(f)
    return data or []


# ----- assess-modeling.py (G2) -----

def test_g2_emits_on_layer_edit_during_build():
    with tempfile.TemporaryDirectory() as tmpdir:
        ws = _make_workspace(tmpdir, workflow="workflow-build", phase="write")
        out = _run(
            ASSESS_MODELING,
            {"tool_name": "Edit", "tool_input": {"file_path": ws["layer_file"]}},
            env_overrides={"IVY_WORKSPACE_ROOT": tmpdir},
        )
        assert out is not None
        ctx = out["hookSpecificOutput"]["additionalContext"]
        assert "[G2 modeling gate]" in ctx
        assert "g2_modeling.md" in ctx
        events = _read_journal(ws["journal"])
        assert any(e["type"] == "gate_dispatched" and e["payload"]["gate"] == "g2" for e in events)


def _is_noop_envelope(out: "dict | None") -> bool:
    """True for the strict-literal `[ivy-noop]` envelope (no additionalContext)."""
    if out is None:
        return False
    sm = out.get("systemMessage", "")
    if not sm.startswith("[ivy-noop]"):
        return False
    hook = out.get("hookSpecificOutput") or {}
    return "additionalContext" not in hook


def test_g2_silent_on_test_spec_edit():
    with tempfile.TemporaryDirectory() as tmpdir:
        ws = _make_workspace(tmpdir, workflow="workflow-build", phase="write")
        out = _run(
            ASSESS_MODELING,
            {"tool_name": "Edit", "tool_input": {"file_path": ws["test_file"]}},
            env_overrides={"IVY_WORKSPACE_ROOT": tmpdir},
        )
        assert _is_noop_envelope(out)


def test_g2_silent_when_no_workflow():
    with tempfile.TemporaryDirectory() as tmpdir:
        proto = Path(tmpdir) / "protocol-testing" / "bgp"
        (proto / "bgp_stack").mkdir(parents=True)
        layer = proto / "bgp_stack" / "bgp_open.ivy"
        layer.write_text("#lang ivy1.7\n")
        out = _run(
            ASSESS_MODELING,
            {"tool_name": "Edit", "tool_input": {"file_path": str(layer)}},
            env_overrides={"IVY_WORKSPACE_ROOT": tmpdir},
        )
        assert _is_noop_envelope(out)


# ----- assess-testspec.py (G3) -----

def test_g3_emits_on_test_spec_edit_during_build():
    with tempfile.TemporaryDirectory() as tmpdir:
        ws = _make_workspace(tmpdir, workflow="workflow-build", phase="write")
        out = _run(
            ASSESS_TESTSPEC,
            {"tool_name": "Edit", "tool_input": {"file_path": ws["test_file"]}},
            env_overrides={"IVY_WORKSPACE_ROOT": tmpdir},
        )
        assert out is not None
        ctx = out["hookSpecificOutput"]["additionalContext"]
        assert "[G3 test-spec gate]" in ctx
        assert "g3_testspec.md" in ctx
        events = _read_journal(ws["journal"])
        assert any(e["type"] == "gate_dispatched" and e["payload"]["gate"] == "g3" for e in events)


def test_g3_silent_on_layer_edit():
    with tempfile.TemporaryDirectory() as tmpdir:
        ws = _make_workspace(tmpdir, workflow="workflow-build", phase="write")
        out = _run(
            ASSESS_TESTSPEC,
            {"tool_name": "Edit", "tool_input": {"file_path": ws["layer_file"]}},
            env_overrides={"IVY_WORKSPACE_ROOT": tmpdir},
        )
        assert _is_noop_envelope(out)


# ----- assess-trace.py (G5) -----

def test_g5_emits_on_iut_test_completion():
    with tempfile.TemporaryDirectory() as tmpdir:
        ws = _make_workspace(tmpdir, workflow="workflow-verify", phase="iut-pass")
        tool_result = {
            "output_dir": str(Path(tmpdir) / "outputs" / "run-001"),
            "logs_path": str(Path(tmpdir) / "outputs" / "run-001" / "logs"),
            "pcap_path": str(Path(tmpdir) / "outputs" / "run-001" / "pcaps"),
            "ivy_trace_path": str(Path(tmpdir) / "outputs" / "run-001" / "logs" / "ivy_tester" / "ivy_tester.log"),
            "protocol": "bgp",
            "test": "bgp_server_test_session",
            "iut": "frr_bgp",
            "run_id": "run-001",
            "summary": {"test_passed": True},
        }
        out = _run(
            ASSESS_TRACE,
            {"tool_name": "ivy_iut_test", "tool_result": tool_result},
            env_overrides={"IVY_WORKSPACE_ROOT": tmpdir},
        )
        assert out is not None
        ctx = out["hookSpecificOutput"]["additionalContext"]
        assert "[G5 trace-analysis gate]" in ctx
        assert "g5_trace.md" in ctx
        assert "must NOT invoke `ivy_iut_test`" in ctx
        events = _read_journal(ws["journal"])
        assert any(e["type"] == "gate_dispatched" and e["payload"]["gate"] == "g5" for e in events)


def test_g5_silent_on_other_tools():
    with tempfile.TemporaryDirectory() as tmpdir:
        out = _run(
            ASSESS_TRACE,
            {"tool_name": "ivy_verify", "tool_result": {"status": "OK"}},
            env_overrides={"IVY_WORKSPACE_ROOT": tmpdir},
        )
        assert _is_noop_envelope(out)


# ----- route-user-prompt.py G1 branch -----

def test_g1_emits_at_blueprint_done_phase():
    with tempfile.TemporaryDirectory() as tmpdir:
        ws = _make_workspace(tmpdir, workflow="workflow-build", phase="blueprint-done")
        out = _run(
            ROUTE_USER_PROMPT,
            {"prompt": "what's next?"},
            env_overrides={"IVY_WORKSPACE_ROOT": tmpdir},
        )
        assert out is not None
        ctx = out["hookSpecificOutput"]["additionalContext"]
        assert "[G1 exploration gate]" in ctx
        events = _read_journal(ws["journal"])
        assert any(e["type"] == "gate_dispatched" and e["payload"]["gate"] == "g1" for e in events)


def test_g1_silent_at_other_build_phases():
    with tempfile.TemporaryDirectory() as tmpdir:
        _make_workspace(tmpdir, workflow="workflow-build", phase="write")
        out = _run(
            ROUTE_USER_PROMPT,
            {"prompt": "continue building"},
            env_overrides={"IVY_WORKSPACE_ROOT": tmpdir},
        )
        # Output may or may not be present depending on routing match,
        # but it must NOT contain the G1 directive at this phase.
        if out is not None:
            ctx = out["hookSpecificOutput"].get("additionalContext", "")
            assert "[G1 exploration gate]" not in ctx


# ----- record-workflow-error.py G4 branch -----

def test_g4_emits_on_ivy_verify_completion_during_workflow():
    with tempfile.TemporaryDirectory() as tmpdir:
        ws = _make_workspace(tmpdir, workflow="workflow-verify", phase="executed")
        out = _run(
            RECORD_WORKFLOW_ERROR,
            {"tool_name": "ivy_verify",
             "tool_result": {"status": "OK", "duration_s": 12.5}},
            env_overrides={"IVY_WORKSPACE_ROOT": tmpdir},
        )
        assert out is not None
        ctx = out["hookSpecificOutput"]["additionalContext"]
        assert "[G4 verification gate]" in ctx
        assert "g4_verification.md" in ctx
        events = _read_journal(ws["journal"])
        assert any(e["type"] == "gate_dispatched" and e["payload"]["gate"] == "g4" for e in events)


def test_g4_silent_when_no_workflow():
    with tempfile.TemporaryDirectory() as tmpdir:
        proto = Path(tmpdir) / "protocol-testing" / "bgp"
        proto.mkdir(parents=True)
        out = _run(
            RECORD_WORKFLOW_ERROR,
            {"tool_name": "ivy_verify",
             "tool_result": {"status": "OK"}},
            env_overrides={"IVY_WORKSPACE_ROOT": tmpdir},
        )
        assert _is_noop_envelope(out)


def test_g4_silent_on_other_tools():
    with tempfile.TemporaryDirectory() as tmpdir:
        _make_workspace(tmpdir, workflow="workflow-verify", phase="compiled")
        out = _run(
            RECORD_WORKFLOW_ERROR,
            {"tool_name": "ivy_compile",
             "tool_result": {"status": "OK"}},
            env_overrides={"IVY_WORKSPACE_ROOT": tmpdir},
        )
        # ivy_compile is in WATCHED_TOOLS but G4 directive is gated on ivy_verify only.
        if out is not None:
            ctx = out["hookSpecificOutput"].get("additionalContext", "")
            assert "[G4 verification gate]" not in ctx
