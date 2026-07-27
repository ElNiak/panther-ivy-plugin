#!/usr/bin/env python3
"""Payload-shape regression guard for journaling-contract.md §3.

The existing parity test (`tests/test_event_types_parity.py`) only checks
that the `_VALID_EVENT_TYPES` allowlist is byte-identical between the hook
emitter and the MCP emitter. It does not check that the *payload shape*
written by each emit site matches what the contract declares as required.

That gap is what this test closes. F1 (gate_dispatched) and F2 (session_end)
in the 2026-05-05 journaling audit each surfaced a contract-vs-emitter
drift that escaped the allowlist test for months. These assertions catch
the same drift on re-introduction: every `gate_dispatched` payload MUST
include `artifact:str`, and every `session_end` payload MUST include
`reason:str`. Adding a new gate or re-shaping `session_end` will fail
these tests until the producer is contract-conformant.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

import pytest
import yaml

pytestmark = pytest.mark.unit

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = PLUGIN_ROOT / "hooks" / "scripts"
RUN_GATE = str(SCRIPTS / "posttooluse/gates/run-gate.py")
RECORD_WORKFLOW_ERROR = str(SCRIPTS / "record/workflow-error.py")
RECORD_SESSION_END = str(SCRIPTS / "record/session-end.py")


def _run(
    script: str,
    payload: dict,
    *,
    extra_argv: "list[str] | None" = None,
    env_overrides: "dict[str, str] | None" = None,
    stdin_payload: "dict | None" = None,
) -> "dict | None":
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = str(PLUGIN_ROOT)
    env.pop("IVY_WORKSPACE_ROOT", None)
    if env_overrides:
        env.update(env_overrides)
    cmd = [sys.executable, script]
    if extra_argv:
        cmd.extend(extra_argv)
    result = subprocess.run(
        cmd,
        input=json.dumps(stdin_payload if stdin_payload is not None else payload),
        capture_output=True,
        text=True,
        timeout=10,
        env=env,
    )
    assert result.returncode == 0, f"{script} exited {result.returncode}: {result.stderr}"
    return json.loads(result.stdout) if result.stdout.strip() else None


def _make_workspace(tmpdir: str, *, workflow: str, phase: str, methodology: str = "nct") -> "dict[str, str]":
    proto = Path(tmpdir) / "protocol-testing" / "bgp"
    state_dir = proto / ".panther-ivy"
    state_dir.mkdir(parents=True)
    (state_dir / "active-workflow").write_text(
        yaml.safe_dump(
            {"workflow": workflow, "phase": phase, "started": "2026-01-01T00:00:00+00:00"}
        )
    )
    (state_dir / "scaffold-state.yaml").write_text(
        yaml.safe_dump(
            {
                "workflow": workflow,
                "protocol": "bgp",
                "methodology": methodology,
                "started": "2026-01-01T00:00:00+00:00",
                "layers": {
                    "bgp_open": {"file": "bgp_stack/bgp_open.ivy", "status": "pending"}
                },
            }
        )
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


def _gate_dispatched_entries(events: "list[dict]") -> "list[dict]":
    return [e for e in events if e.get("type") == "gate_dispatched"]


# ---------------------------------------------------------------- F1


class TestGateDispatchedArtifactRequired:
    """Every `gate_dispatched` payload MUST include `artifact:str`."""

    def test_g2_writes_artifact_string(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ws = _make_workspace(tmpdir, workflow="scaffold", phase="write")
            _run(
                RUN_GATE,
                {"tool_name": "Edit", "tool_input": {"file_path": ws["layer_file"]}},
                extra_argv=["--id", "g2"],
                env_overrides={"IVY_WORKSPACE_ROOT": tmpdir},
            )
            entries = _gate_dispatched_entries(_read_journal(ws["journal"]))
            g2 = [e for e in entries if e["payload"]["gate"] == "g2"]
            assert g2, "G2 dispatch did not produce a journal entry"
            artifact = g2[0]["payload"].get("artifact")
            assert isinstance(artifact, str) and artifact, (
                f"G2 payload must have non-empty `artifact:str`; got {artifact!r}"
            )
            assert artifact == ws["layer_file"]

    def test_g3_writes_artifact_string(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ws = _make_workspace(tmpdir, workflow="scaffold", phase="write")
            _run(
                RUN_GATE,
                {"tool_name": "Edit", "tool_input": {"file_path": ws["test_file"]}},
                extra_argv=["--id", "g3"],
                env_overrides={"IVY_WORKSPACE_ROOT": tmpdir},
            )
            entries = _gate_dispatched_entries(_read_journal(ws["journal"]))
            g3 = [e for e in entries if e["payload"]["gate"] == "g3"]
            assert g3, "G3 dispatch did not produce a journal entry"
            artifact = g3[0]["payload"].get("artifact")
            assert isinstance(artifact, str) and artifact, (
                f"G3 payload must have non-empty `artifact:str`; got {artifact!r}"
            )
            assert artifact == ws["test_file"]

    def test_g4_writes_artifact_string(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ws = _make_workspace(tmpdir, workflow="refine", phase="executed")
            _run(
                RECORD_WORKFLOW_ERROR,
                {"tool_name": "ivy_verify", "tool_response": {"status": "OK"}},
                env_overrides={"IVY_WORKSPACE_ROOT": tmpdir},
            )
            entries = _gate_dispatched_entries(_read_journal(ws["journal"]))
            g4 = [e for e in entries if e["payload"]["gate"] == "g4"]
            assert g4, "G4 dispatch did not produce a journal entry"
            payload = g4[0]["payload"]
            artifact = payload.get("artifact")
            assert isinstance(artifact, str) and artifact, (
                f"G4 payload must have non-empty `artifact:str`; got {artifact!r}"
            )
            assert "tool" not in payload, (
                "G4 payload must use canonical `artifact` field, not legacy `tool`"
            )

    def test_g5_writes_artifact_string_and_keeps_artifacts_dict(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            ws = _make_workspace(tmpdir, workflow="refine", phase="iut-pass")
            trace_path = str(
                Path(tmpdir) / "outputs/run-001/logs/ivy_tester/ivy_tester.log"
            )
            tool_result = {
                "output_dir": str(Path(tmpdir) / "outputs/run-001"),
                "logs_path": str(Path(tmpdir) / "outputs/run-001/logs"),
                "pcap_path": str(Path(tmpdir) / "outputs/run-001/pcaps"),
                "ivy_trace_path": trace_path,
                "protocol": "bgp",
                "test": "bgp_server_test_session",
                "iut": "frr_bgp",
                "run_id": "run-001",
                "summary": {"test_passed": True},
            }
            _run(
                RUN_GATE,
                {"tool_name": "ivy_iut_test", "tool_response": tool_result},
                extra_argv=["--id", "g5"],
                env_overrides={"IVY_WORKSPACE_ROOT": tmpdir},
            )
            entries = _gate_dispatched_entries(_read_journal(ws["journal"]))
            g5 = [e for e in entries if e["payload"]["gate"] == "g5"]
            assert g5, "G5 dispatch did not produce a journal entry"
            payload = g5[0]["payload"]
            artifact = payload.get("artifact")
            assert isinstance(artifact, str) and artifact, (
                f"G5 payload must have non-empty `artifact:str`; got {artifact!r}"
            )
            assert artifact == trace_path, (
                f"G5 `artifact` should be the primary trace path; got {artifact!r}"
            )
            artifacts_dict = payload.get("artifacts")
            assert isinstance(artifacts_dict, dict), (
                f"G5 should still preserve full bundle as optional `artifacts:dict`; got {artifacts_dict!r}"
            )
            assert "ivy_trace_path" in artifacts_dict and "output_dir" in artifacts_dict


# ---------------------------------------------------------------- F2


class TestSessionEndReasonRequired:
    """Every `session_end` payload MUST include `reason:str`."""

    def _run_session_end(self, tmp_path: Path, *, session_id: str = "shape-test-1") -> None:
        env = os.environ.copy()
        env["CLAUDE_PLUGIN_ROOT"] = str(PLUGIN_ROOT)
        env["IVY_SESSION_ID"] = session_id
        env["TMPDIR"] = str(tmp_path)
        env["IVY_WORKSPACE_ROOT"] = str(tmp_path)

        flag_dir = tmp_path / "claude-ivy"
        flag_dir.mkdir(parents=True, exist_ok=True)
        (flag_dir / f"session-activity-{session_id}.flag").touch()

        proto_dir = tmp_path / "protocol-testing" / "bgp"
        panther_dir = proto_dir / ".panther-ivy"
        panther_dir.mkdir(parents=True, exist_ok=True)
        (panther_dir / "active-workflow").write_text(
            yaml.safe_dump({"workflow": "refine", "phase": "compile"})
        )

        result = subprocess.run(
            [sys.executable, RECORD_SESSION_END],
            input=json.dumps({}),
            capture_output=True,
            text=True,
            timeout=10,
            env=env,
            cwd=str(tmp_path),
        )
        assert result.returncode == 0, (
            f"session-end exited {result.returncode}: {result.stderr}"
        )

    def test_session_end_payload_has_reason_string(self, tmp_path):
        self._run_session_end(tmp_path)
        journal = tmp_path / "protocol-testing/bgp/.panther-ivy/workflow-journal.yaml"
        events = yaml.safe_load(journal.read_text()) or []
        session_ends = [e for e in events if e.get("type") == "session_end"]
        assert session_ends, "session_end event missing from journal"
        payload = session_ends[0].get("payload", {})
        reason = payload.get("reason")
        assert isinstance(reason, str) and reason, (
            f"session_end payload must have non-empty `reason:str`; got {reason!r}"
        )
        assert reason in {"clean_stop", "stale_workflow", "unknown"}, (
            f"session_end `reason` must be one of the documented enum values; got {reason!r}"
        )

    def test_session_end_payload_keeps_clean_and_phase_at_exit(self, tmp_path):
        self._run_session_end(tmp_path)
        journal = tmp_path / "protocol-testing/bgp/.panther-ivy/workflow-journal.yaml"
        events = yaml.safe_load(journal.read_text()) or []
        payload = next(e for e in events if e.get("type") == "session_end")["payload"]
        assert isinstance(payload.get("clean"), bool)
        assert isinstance(payload.get("phase_at_exit"), str)
