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

sys.path.insert(
    0,
    os.path.join(
        os.environ.get("CLAUDE_PLUGIN_ROOT", "."), "hooks", "scripts"
    ),
)
from hook_utils import emit_hook_output, read_stdin
from workflow_state import (
    WorkflowContext,
    append_journal_event,
    get_build_state,
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
        "1. Load the `reflection-patterns` skill via the Skill tool.\n"
        "2. Read the G4 verbatim critic template at `critic_prompts/g4_verification.md` within that skill's references.\n"
        "3. Apply the Adversarial Quality Gates discipline-layer rules: verbatim spawn prompts, dual context isolation, asymmetric vote (Sonnet × 5 default: 4 SOUND / 2 UNSOUND / pigeonhole exit), calibrated abstention.\n"
        "4. Each critic must load the `ivy-error-patterns` skill to access the numbered catalog and apply only ID ranges #200-249 + #250-299 + #400-499.\n"
        "5. Critics treat `status: OK` as a hypothesis to falsify, not a conclusion. Check for #401 (unsound `assume`), #402 (trusted-isolate NativeAction leak), #403 (error whitelisted), #404 (solver wall claimed sound — duration_s near timeout), #405 (pre-fix research skipped), #406 (missing four-layer diagnostic cascade).\n"
        "6. Aggregate verdicts into VERDICT_SOUND / VERDICT_UNSOUND / VERDICT_ABSTAIN.\n"
        "7. On VERDICT_UNSOUND, write `[GAP: #NN <reason>]` markers at the cited file:line locations per `.claude/rules/gap-markers.md` (orchestrator only).\n"
        "8. Append a `gate_verdict` event to the workflow journal via `ivy_workflow_state(action=\"append_journal\", event_type=\"gate_verdict\", payload={...})`.\n"
        "9. Render the verdict block per `styles/tool-renderers/ivy_verdict.md` in the verify-overlay format.\n\n"
        "A false SOUND here is the exact failure mode this gate exists to prevent — when any catalog entry fires, lean against SOUND."
    )


def main() -> None:
    hook_input = read_stdin()
    tool_name = hook_input.get("tool_name", "")

    if tool_name not in _WATCHED_TOOLS:
        return

    ctx = WorkflowContext.current()
    if ctx is None:
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
        build_state = get_build_state(ctx.protocol_dir) or {}
        protocol = build_state.get("protocol") or os.path.basename(ctx.protocol_dir.rstrip("/"))
        methodology = build_state.get("methodology")

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

        emit_hook_output(
            "PostToolUse",
            additional_context=_build_g4_directive(tool_result, protocol, methodology),
        )


if __name__ == "__main__":
    main()
