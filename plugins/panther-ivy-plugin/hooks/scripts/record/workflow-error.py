#!/usr/bin/env python3
"""PostToolUse hook: record error events in workflow journal during active workflows.

Detects compilation failures, verification failures, and tool errors from
MCP tool results when a workflow is active. Additionally, after `ivy_verify`
returns (regardless of pass/fail), emits a G4 verification-gate dispatch
directive so Claude dispatches context-isolated critics before accepting the
verifier's verdict as conclusive.

Non-blocking -- always exits 0.
"""

import json
import os
import re
import sys

from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.hook_utils import emit_hook_output, emit_noop, read_stdin
from lib.workflow_state import (
    WorkflowContext,
    append_journal_event,
    get_scaffold_state_safe,
    journal_path,
)

_ERROR_PATTERNS = [
    (re.compile(r"compilation failed", re.IGNORECASE), "Ivy compilation failed"),
    (re.compile(r"FAIL\b.*isolate", re.IGNORECASE), "Verification failure"),
    (re.compile(r"error:.*\.ivy", re.IGNORECASE), "Ivy file error"),
    (re.compile(r'"success":\s*false', re.IGNORECASE), "MCP tool returned failure"),
    (re.compile(r"timed?\s*out|timeout\s+(?:exceeded|expired|killed)", re.IGNORECASE), "Operation timed out"),
]

_WATCHED_TOOLS = {
    "ivy_verify", "ivy_compile", "ivy_diagnostics",
    "ivy_coverage", "ivy_iut_test", "ivy_quality",
}


def _extract_error_summary(tool_result: str) -> str | None:
    """Check tool result for error patterns and return summary."""
    for pattern, summary in _ERROR_PATTERNS:
        if pattern.search(tool_result):
            return summary
    return None


def _build_g4_directive(tool_result: str, protocol: str, methodology: str | None) -> str:
    """Construct the G4 verification-gate dispatch directive."""
    methodology_line = f"- Methodology: {methodology}" if methodology else "- Methodology: unknown"
    status_hint = "OK" if '"status":"OK"' in tool_result.replace(" ", "") else "FAIL"
    return (
        f"[G4 verification gate] `ivy_verify` has returned ({status_hint}). "
        "Dispatch the G4 verification gate before treating the result as conclusive.\n\n"
        f"Protocol: {protocol}\n"
        f"{methodology_line}\n\n"
        "To dispatch:\n"
        "1. Read the G4 verbatim critic template at `skills/ivy/references/critic_prompts/g4_verification.md` (your preloaded `verification-failures` skill provides the catalog).\n"
        "2. Apply the Adversarial Quality Gates discipline-layer rules: verbatim spawn prompts, dual context isolation, asymmetric vote (Sonnet × 5 default: 4 SOUND / 2 UNSOUND / pigeonhole exit), calibrated abstention.\n"
        "3. Each critic loads the `verification-failures` skill to access the numbered catalog and applies only ID ranges #200-249 + #250-299 + #400-499.\n"
        "4. Critics treat `status: OK` as a hypothesis to falsify, not a conclusion. Check for #401 (unsound `assume`), #402 (trusted-isolate NativeAction leak), #403 (error whitelisted), #404 (solver wall claimed sound — duration_s near timeout), #405 (pre-fix research skipped), #406 (missing four-layer diagnostic cascade).\n"
        "5. Aggregate verdicts into VERDICT_SOUND / VERDICT_UNSOUND / VERDICT_ABSTAIN.\n"
        "6. On VERDICT_UNSOUND, write `[GAP: #NN <reason>]` markers at the cited file:line locations per `.claude/rules/gap-markers.md` (orchestrator only).\n"
        "7. Append a `gate_verdict` event to the workflow journal via `ivy_workflow_state(action=\"append_journal\", event_type=\"gate_verdict\", payload={...})`.\n"
        "8. Render the verdict block per `styles/tool-renderers/ivy_verdict.md` in the verify-overlay format.\n\n"
        "A false SOUND here is the exact failure mode this gate exists to prevent — when any catalog entry fires, lean against SOUND."
    )


def main() -> None:
    hook_input = read_stdin()
    tool_name = hook_input.get("tool_name", "")

    if tool_name not in _WATCHED_TOOLS:
        emit_noop("PostToolUse", f"tool '{tool_name}' not watched for errors")
        return

    ctx = WorkflowContext.current()
    if ctx is None:
        emit_noop("PostToolUse", "no active workflow")
        return

    tool_result = hook_input.get("tool_result", "")
    if isinstance(tool_result, dict):
        tool_result = json.dumps(tool_result)
    elif not isinstance(tool_result, str):
        tool_result = str(tool_result)

    error_summary = _extract_error_summary(tool_result)
    if error_summary:
        append_journal_event(
            ctx.protocol_dir,
            event_type="error",
            payload={
                "summary": error_summary,
                "tool": tool_name,
                "recoverable": True,
            },
            workflow=ctx.workflow,
            phase=ctx.phase,
        )

    if tool_name == "ivy_verify":
        scaffold_state = get_scaffold_state_safe(ctx.protocol_dir) or {}
        protocol = scaffold_state.get("protocol") or os.path.basename(ctx.protocol_dir.rstrip("/"))
        methodology = scaffold_state.get("methodology")

        append_journal_event(
            ctx.protocol_dir,
            event_type="gate_dispatched",
            payload={
                "gate": "g4",
                "trigger": "record-workflow-error.py",
                "tool": tool_name,
                "methodology": methodology,
            },
            workflow=ctx.workflow,
            phase=ctx.phase,
        )

        status_hint = "OK" if '"status":"OK"' in tool_result.replace(" ", "") else "FAIL"
        emit_hook_output(
            "PostToolUse",
            system_message=(
                f"[G4 verification gate] dispatched after ivy_verify "
                f"({status_hint}) on protocol={protocol}; "
                f"gate_dispatched appended to journal at {journal_path(ctx.protocol_dir)}"
            ),
            additional_context=_build_g4_directive(tool_result, protocol, methodology),
        )
    elif error_summary:
        emit_noop(
            "PostToolUse",
            f"recorded {tool_name} error to journal (no G4 dispatch)",
        )
    else:
        emit_noop(
            "PostToolUse",
            f"{tool_name} produced no error pattern; no journal write",
        )


if __name__ == "__main__":
    main()
