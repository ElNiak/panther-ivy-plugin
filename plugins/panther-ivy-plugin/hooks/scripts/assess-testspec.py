#!/usr/bin/env python3
"""PostToolUse hook: trigger G3 test-spec gate on *_test_*.ivy writes.

Fires after Edit|Write on an Ivy test spec file (name contains `_test_`).
When the active workflow is `scaffold`, emits an additionalContext directive
instructing Claude to dispatch G3 test-spec critics (your preloaded
`verification-failures` skill provides the catalog).

The hook itself does NOT spawn critics — it is a subprocess and cannot invoke
the Agent tool. Claude reads the additionalContext on the next turn and runs
the gate dispatch (verbatim prompt, asymmetric vote, calibrated verdict, GAP
marker writing).

Non-blocking — always exits 0.

## Why scaffold-only?

G3 audits test-spec soundness during *construction* — coverage-matrix
gaps relative to the target RFC's MUST requirements, generator over-
constraint that silently skips test cases, and the structural pathologies
in ``*_test_*.ivy`` that matter most when a test spec is being written
for the first time. The filter line below (``if ctx is None or
ctx.workflow != "scaffold": return``) is intentional scoping.

Verify's Phase 7 fix loop and review's Phase 3 inline fixes, under the
cluster 1 design, either stay small or dispatch back to ``scaffold`` via
``pending_dispatch`` when the change warrants G3 re-run. That is the
re-engagement path — users write in ``scaffold``, G3 fires.

Users who want an adversarial audit of a test spec outside ``scaffold``
emit ``append_pending_dispatch(target_workflow="scaffold",
phase_hint="layer-check")`` and let navigate re-engage ``scaffold``.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from hook_utils import emit_hook_output, emit_noop, read_stdin

from workflow_state import (
    WorkflowContext,
    append_journal_event,
    get_scaffold_state_safe,
)

_WATCHED_TOOLS = {"Edit", "Write", "NotebookEdit"}


def _is_test_spec(file_path: str) -> bool:
    """True for .ivy files that are test specs (name contains `_test_` or ends `_test.ivy`)."""
    if not file_path.endswith(".ivy"):
        return False
    name = os.path.basename(file_path)
    return "_test_" in name or name.endswith("_test.ivy")


def _build_directive(*, file_path: str, protocol: str, methodology: str | None) -> str:
    methodology_line = f"- Methodology: {methodology}" if methodology else "- Methodology: unknown"
    nsct_note = ""
    if methodology == "nsct":
        nsct_note = "\n  - NSCT active: NSCT-specific test-spec patterns are limited; apply base catalog slice only."

    return (
        "[G3 test-spec gate] A `*_test_*.ivy` file has been written while the `scaffold` workflow is active. "
        "Dispatch the G3 test-spec gate before running `ivy_compile` / `ivy_verify`.\n\n"
        f"Artifact under audit: `{file_path}` (protocol: {protocol}).\n"
        f"{methodology_line}{nsct_note}\n\n"
        "To dispatch:\n"
        "1. Read the G3 verbatim critic template at `skills/ivy/references/critic_prompts/g3_testspec.md` (your preloaded `verification-failures` skill provides the catalog).\n"
        "2. Apply the Adversarial Quality Gates discipline-layer rules: verbatim spawn prompts, dual context isolation, asymmetric vote (Sonnet × 5 default: 4 SOUND / 2 UNSOUND / pigeonhole exit), calibrated abstention.\n"
        "3. Each critic loads the `verification-failures` skill to access the numbered catalog and applies only ID ranges #200-208 + #256-259 + #300-399.\n"
        "4. Before spawning critics, gather inputs the template expects: the test file contents, the RFC requirement manifest (typically `{protocol}_requirements.yaml`), and the output of `ivy_coverage(mode=\"matrix\", test_file=<file_path>)`.\n"
        "5. Aggregate verdicts into VERDICT_SOUND / VERDICT_UNSOUND / VERDICT_ABSTAIN.\n"
        "6. On VERDICT_UNSOUND, write `[GAP: #NN <reason>]` markers at the cited file:line locations per `.claude/rules/gap-markers.md` (orchestrator only).\n"
        "7. Append a `gate_verdict` event to the workflow journal via `ivy_workflow_state(action=\"append_journal\", event_type=\"gate_verdict\", payload={...})`.\n"
        "8. Render the verdict block per `styles/tool-renderers/ivy_verdict.md` in the scaffold-overlay format.\n\n"
        "A test spec that looks clean but silently fails to cover a MUST requirement or over-constrains the generator is the exact failure mode G3 exists to catch — read the coverage matrix carefully."
    )


def main() -> None:
    hook_input = read_stdin()
    if not hook_input:
        emit_noop("PostToolUse", "no hook input")
        return

    tool_name = hook_input.get("tool_name", "")
    if tool_name not in _WATCHED_TOOLS:
        emit_noop("PostToolUse", f"tool '{tool_name}' not watched by G3")
        return

    tool_input = hook_input.get("tool_input", {})
    file_path = tool_input.get("file_path", "")
    if not _is_test_spec(file_path):
        emit_noop("PostToolUse", "edit is not a test-spec file")
        return

    ctx = WorkflowContext.current()
    # G3 is scaffold-only by design — see "Why scaffold-only?" in the module
    # docstring for the rationale.
    if ctx is None or ctx.workflow != "scaffold":
        emit_noop("PostToolUse", "G3 is scaffold-workflow only")
        return

    scaffold_state = get_scaffold_state_safe(ctx.protocol_dir) or {}
    protocol = scaffold_state.get("protocol") or os.path.basename(ctx.protocol_dir.rstrip("/"))
    methodology = scaffold_state.get("methodology")

    append_journal_event(
        ctx.protocol_dir,
        event_type="gate_dispatched",
        payload={
            "gate": "g3",
            "trigger": "assess-testspec.py",
            "artifact": file_path,
            "methodology": methodology,
        },
        workflow="scaffold",
        phase=ctx.phase,
    )

    emit_hook_output(
        "PostToolUse",
        system_message=f"[G3 test-spec gate] dispatched on {os.path.basename(file_path)}",
        additional_context=_build_directive(
            file_path=file_path,
            protocol=protocol,
            methodology=methodology,
        ),
    )


if __name__ == "__main__":
    main()
