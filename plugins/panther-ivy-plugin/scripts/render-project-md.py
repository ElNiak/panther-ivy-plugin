#!/usr/bin/env python3
"""Derive PROJECT.md for one protocol from .panther-ivy/ journal + state.

Reads:
  <protocol-dir>/.panther-ivy/workflow-journal.yaml
Writes:
  <protocol-dir>/PROJECT.md

Usage:
  python3 render-project-md.py --protocol-dir protocol-testing/bgp
  python3 render-project-md.py --protocol bgp  # resolves under cwd/protocol-testing/
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PLUGIN_ROOT / "hooks" / "scripts"))

from project_md_state import write_project_md  # noqa: E402

_PHASE_TRANSITION_TYPES = {"phase_transition"}
_GATE_TYPES = {"gate_verdict"}
_MODE_FROM_WORKFLOW = {"scaffold", "refine", "experiment"}


def _load_journal(protocol_dir: Path) -> List[Dict[str, Any]]:
    journal = protocol_dir / ".panther-ivy" / "workflow-journal.yaml"
    if not journal.exists():
        return []
    data = yaml.safe_load(journal.read_text()) or {}
    return list(data.get("events", []))


def _latest_phase_transition(events: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    candidates = [e for e in events if e.get("type") in _PHASE_TRANSITION_TYPES]
    return candidates[-1] if candidates else None


def _latest_gate(events: List[Dict[str, Any]], gate_id: str) -> Optional[Dict[str, Any]]:
    candidates = [
        e
        for e in events
        if e.get("type") in _GATE_TYPES and e.get("gate_id") == gate_id
    ]
    return candidates[-1] if candidates else None


def _read_protocol_version(protocol_dir: Path) -> str:
    """Best-effort: read first RFC banner line from any .ivy file in the dir.

    Falls back to 'unknown'. Bootstrap path: migrate-bootstrap-project-md.py
    sets 'unknown' explicitly; subsequent renders may upgrade as files appear.
    """
    for candidate in protocol_dir.glob("*.ivy"):
        head = candidate.read_text(errors="ignore")[:1024]
        for line in head.splitlines():
            stripped = line.strip("# ").strip()
            if "rfc" in stripped.lower():
                return stripped
    return "unknown"


def _collect_decisions(events: List[Dict[str, Any]], decision_type: str) -> List[Any]:
    return [
        e.get("payload", {})
        for e in events
        if e.get("type") == "decision" and e.get("decision_type") == decision_type
    ]


def _collect_open_counterexamples(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    open_cxs: Dict[str, Dict[str, Any]] = {}
    for e in events:
        if e.get("type") != "gate_verdict" or e.get("gate_id") != "g4_verification":
            continue
        isolate = e.get("isolate")
        if not isolate:
            continue
        verdict = e.get("verdict")
        if verdict == "UNSAT":
            open_cxs[isolate] = {
                "phase": e.get("phase"),
                "isolate": isolate,
                "last_observed": e.get("timestamp"),
            }
        elif verdict == "SAT":
            open_cxs.pop(isolate, None)
    return list(open_cxs.values())


def derive_state(protocol_dir: Path) -> Dict[str, Any]:
    """Roll up journal events into a PROJECT.md state dict."""
    events = _load_journal(protocol_dir)
    transition = _latest_phase_transition(events)
    g4 = _latest_gate(events, "g4_verification")
    g5 = _latest_gate(events, "g5_trace")
    last_event_id = events[-1].get("event_id") if events else None

    if transition and transition.get("workflow") in _MODE_FROM_WORKFLOW:
        mode = transition["workflow"]
        phase = int(transition.get("phase", 0))
    else:
        mode = "idle"
        phase = 0

    last_verify = {
        "status": (g4 or {}).get("verdict", "NOT_RUN") if g4 else "NOT_RUN",
        "timestamp": (g4 or {}).get("timestamp"),
        "isolate": (g4 or {}).get("isolate"),
    }
    if last_verify["status"] not in {"SAT", "UNSAT", "NOT_RUN"}:
        last_verify["status"] = "NOT_RUN"

    last_iut_run: Optional[Dict[str, Any]] = None
    if g5:
        verdict = g5.get("verdict")
        if verdict in {"NO_VIOLATION_FOUND", "NON_COMPLIANT", "TESTER_CRASH", "IUT_CRASH"}:
            last_iut_run = {
                "iut": g5.get("iut"),
                "verdict": verdict,
                "timestamp": g5.get("timestamp"),
            }

    return {
        "protocol": protocol_dir.name,
        "version": _read_protocol_version(protocol_dir),
        "mode": mode,
        "phase": phase,
        "journal_pointer": (
            f".panther-ivy/workflow-journal.yaml#{last_event_id or 'null'}"
        ),
        "last_verify": last_verify,
        "rfc_sections_covered": _collect_decisions(events, "rfc_section_covered"),
        "open_counterexamples": _collect_open_counterexamples(events),
        "last_iut_run": last_iut_run,
        "deferred_layers": _collect_decisions(events, "defer_layer"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Derive PROJECT.md for one protocol.")
    parser.add_argument("--protocol-dir", type=Path, help="Path to protocol-testing/<protocol>/")
    parser.add_argument(
        "--protocol", type=str, help="Protocol name; resolved under cwd/protocol-testing/"
    )
    args = parser.parse_args()

    if args.protocol_dir:
        protocol_dir = args.protocol_dir
    elif args.protocol:
        protocol_dir = Path.cwd() / "protocol-testing" / args.protocol
    else:
        parser.error("--protocol-dir or --protocol required")
        return 2

    state = derive_state(protocol_dir)
    write_project_md(protocol_dir / "PROJECT.md", state)
    print(
        f"wrote {protocol_dir / 'PROJECT.md'} "
        f"(mode={state['mode']}, phase={state['phase']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
