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

from project_md_state import (  # noqa: E402
    VALID_IUT_VERDICT,
    VALID_MODES,
    VALID_VERIFY_STATUS,
    resolve_project_md_path,
    write_project_md,
)

_PHASE_TRANSITION_TYPES = {"phase_transition"}
_GATE_TYPES = {"gate_verdict"}
# Subset of VALID_MODES — excludes "idle" because idle is the fallback
# when no transition exists, not a workflow that gets recorded in the
# journal as a phase_transition.workflow value.
_MODE_FROM_WORKFLOW = VALID_MODES - {"idle"}


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
    """Read the protocol's RFC version, or fall back to 'unknown'.

    Honours an optional ``.panther-ivy/version`` file in the protocol
    directory if present (single line, e.g. ``rfc4271``). Falls back to
    'unknown' when the file is absent — the bootstrap migration sets
    'unknown' explicitly, and a future contributor can populate the
    version file when the protocol's RFC stabilises. Avoids a scan of
    every ``*.ivy`` file (which would be N syscalls per regen and a
    loose regex match).
    """
    candidate = protocol_dir / ".panther-ivy" / "version"
    if candidate.is_file():
        return candidate.read_text().strip() or "unknown"
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
        if phase == 0:
            mode = "idle"
    else:
        mode = "idle"
        phase = 0

    last_verify_status = (g4 or {}).get("verdict") if g4 else None
    if last_verify_status not in VALID_VERIFY_STATUS:
        last_verify_status = "NOT_RUN"
    last_verify = {
        "status": last_verify_status,
        "timestamp": (g4 or {}).get("timestamp"),
        "isolate": (g4 or {}).get("isolate"),
    }

    last_iut_run: Optional[Dict[str, Any]] = None
    if g5 and g5.get("verdict") in VALID_IUT_VERDICT:
        last_iut_run = {
            "iut": g5.get("iut"),
            "verdict": g5.get("verdict"),
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
    target = resolve_project_md_path(protocol_dir)
    write_project_md(target, state)
    print(f"wrote {target} (mode={state['mode']}, phase={state['phase']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
