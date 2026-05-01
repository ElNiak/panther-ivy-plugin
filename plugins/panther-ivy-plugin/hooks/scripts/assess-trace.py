#!/usr/bin/env python3
"""PostToolUse hook: trigger G5 trace-analysis gate on ivy_iut_test results.

Fires after the `ivy_iut_test` MCP tool returns. Emits an additionalContext
directive instructing Claude to dispatch G5 trace-analysis critics (your
preloaded `verification-failures` skill provides the catalog). Extracts
artifact paths from the tool result so the directive names them exactly.

The hook itself does NOT spawn critics — it is a subprocess and cannot invoke
the Agent tool. Critics must NOT invoke `ivy_iut_test` themselves; they analyze
the just-completed run's artifacts only.

Non-blocking — always exits 0.
"""

import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))
from hook_utils import emit_hook_output, emit_noop, read_stdin

from workflow_state import (
    append_journal_event,
    find_protocol_dir,
    get_active_workflow,
    get_build_state_safe,
)


def _parse_tool_result(raw: object) -> "dict[str, Any] | None":
    """Parse the tool result into a dict, whether it's already a dict or a JSON string."""
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else None
        except (ValueError, TypeError):
            return None
    return None


def _build_directive(*, artifacts: "dict[str, Any]", methodology: str | None) -> str:
    """Construct the G5 dispatch additionalContext directive."""
    output_dir = artifacts.get("output_dir", "<unknown>")
    logs_path = artifacts.get("logs_path", "<unknown>")
    pcap_path = artifacts.get("pcap_path", "<unknown>")
    ivy_trace_path = artifacts.get("ivy_trace_path", "<unknown>")
    protocol = artifacts.get("protocol", "<unknown>")
    test = artifacts.get("test", "<unknown>")
    iut = artifacts.get("iut", "<unknown>")
    run_id = artifacts.get("run_id", "<unknown>")
    test_passed = artifacts.get("summary", {}).get("test_passed", "<unknown>")

    methodology_line = f"- Methodology: {methodology}" if methodology else "- Methodology: unknown"
    nsct_note = ""
    if methodology == "nsct":
        nsct_note = "\n  - NSCT active: include catalog range #560-589 (replay/syscall) in the slice."

    return (
        f"[G5 trace-analysis gate] An `ivy_iut_test` run has completed ({protocol}/{test} against {iut}, run_id={run_id}, test_passed={test_passed}). "
        "Dispatch the G5 trace-analysis gate before accepting the run's verdict as ground truth.\n\n"
        "Artifact paths:\n"
        f"- `output_dir`: {output_dir}\n"
        f"- `logs_path`: {logs_path}\n"
        f"- `pcap_path`: {pcap_path}\n"
        f"- `ivy_trace_path`: {ivy_trace_path}\n"
        f"{methodology_line}{nsct_note}\n\n"
        "To dispatch:\n"
        "1. Read the G5 verbatim critic template at `skills/ivy/references/critic_prompts/g5_trace.md` (your preloaded `verification-failures` skill provides the catalog).\n"
        "2. Apply the Adversarial Quality Gates discipline-layer rules: verbatim spawn prompts, dual context isolation, asymmetric vote (Sonnet × 5 default: 4 SOUND / 2 UNSOUND / pigeonhole exit), calibrated abstention.\n"
        "3. Each critic loads the `verification-failures` skill to access the numbered catalog and applies only ID ranges #100-107 + #500-559 (+ #560-589 if NSCT).\n"
        "4. CRITICAL constraint: critics must read the run output directory in the mandatory order (analysis_results.json → compile log if compilation suspect → ivy_tester.log → IUT log → pcaps via tshark). They must NOT invoke `ivy_iut_test` themselves — spawning a new run is forbidden.\n"
        "5. Aggregate verdicts into VERDICT_SOUND / VERDICT_UNSOUND / VERDICT_ABSTAIN.\n"
        "6. On VERDICT_UNSOUND, write `[GAP: #NN <reason>]` markers at the cited spec file:line locations (not at artifact paths — the spec is the mutable target) per `.claude/rules/gap-markers.md`.\n"
        "7. Append a `gate_verdict` event to the workflow journal via `ivy_workflow_state(action=\"append_journal\", event_type=\"gate_verdict\", payload={...})`.\n"
        "8. Render the verdict block per `styles/tool-renderers/ivy_verdict.md` in the verify-overlay format.\n\n"
        "The hardest G5 call is distinguishing a real IUT bug from a model bug misattributed to the IUT. When in doubt about attribution, critics return UNSURE rather than bless an incorrect story."
    )


def main() -> None:
    hook_input = read_stdin()
    if not hook_input:
        emit_noop("PostToolUse", "no hook input")
        return

    tool_name = hook_input.get("tool_name", "")
    if tool_name != "ivy_iut_test":
        emit_noop("PostToolUse", f"tool '{tool_name}' is not ivy_iut_test")
        return

    tool_result = _parse_tool_result(hook_input.get("tool_result"))
    if not tool_result:
        emit_noop("PostToolUse", "ivy_iut_test produced no parseable tool_result")
        return

    artifacts = {
        "output_dir": tool_result.get("output_dir", ""),
        "logs_path": tool_result.get("logs_path", ""),
        "pcap_path": tool_result.get("pcap_path", ""),
        "ivy_trace_path": tool_result.get("ivy_trace_path", ""),
        "protocol": tool_result.get("protocol", ""),
        "test": tool_result.get("test", ""),
        "iut": tool_result.get("iut", ""),
        "run_id": tool_result.get("run_id", ""),
        "summary": tool_result.get("summary", {}),
    }
    if not artifacts["output_dir"]:
        emit_noop("PostToolUse", "ivy_iut_test result has no output_dir")
        return

    protocol_dir = find_protocol_dir()
    methodology = None
    if protocol_dir:
        build_state = get_build_state_safe(protocol_dir) or {}
        methodology = build_state.get("methodology")

        state = get_active_workflow(protocol_dir) or {}
        append_journal_event(
            protocol_dir,
            event_type="gate_dispatched",
            payload={
                "gate": "g5",
                "trigger": "assess-trace.py",
                "artifacts": {k: v for k, v in artifacts.items() if k != "summary"},
                "methodology": methodology,
            },
            workflow=state.get("workflow"),
            phase=state.get("phase"),
        )

    emit_hook_output(
        "PostToolUse",
        system_message=f"[G5 trace-analysis gate] dispatched on run_id={artifacts.get('run_id', '<unknown>')}",
        additional_context=_build_directive(
            artifacts=artifacts,
            methodology=methodology,
        ),
    )


if __name__ == "__main__":
    main()
