#!/usr/bin/env python3
"""PostToolUse hook: trigger G2 modeling gate on .ivy layer writes.

Fires after Edit|Write on a .ivy file (excluding *_test_*.ivy). When the
active workflow is `scaffold`, emits an additionalContext directive instructing
Claude to dispatch G2 modeling critics (your preloaded `verification-failures`
skill provides the catalog).

The hook itself does NOT spawn critics — it is a subprocess and cannot invoke
the Agent tool. Claude reads the additionalContext on the next turn and runs
the gate dispatch (verbatim prompt, asymmetric vote, calibrated verdict, GAP
marker writing).

Non-blocking — always exits 0. Gate dispatch failures are non-fatal; the
verdict event is recorded in the workflow journal, not surfaced as an error.

## Why scaffold-only?

G2 audits layer modeling soundness during *construction* — ungrounded
quantifiers, missing invariants, actions without require guards, the
structural pathologies that matter most when a layer is being written for
the first time. The filter line below (``if ctx is None or ctx.workflow
!= "scaffold": return``) is intentional scoping, not inertia.

Verify's Phase 7 fix loop is expected to be narrow counterexample-driven
repairs bounded by cluster 7's journal-counted attempt cap (5 per test
file, cumulative across sessions, soft-reset via an
``override_attempt_cap`` decision). Broadening G2 to verify-phase .ivy
edits raises audit volume faster than it raises soundness confidence: the
fix cycle already carries attempt-counter accountability, and
counterexample-driven patches rarely introduce the structural pathologies
G2 is calibrated for.

Review's Phase 3 inline fixes either stay small (qualitative patches) or,
under cluster 1's design, dispatch back to ``scaffold`` via
``pending_dispatch(scaffold, phase_hint="<appropriate>")`` for structural
rethink. Either way, any .ivy write that warrants G2 re-runs G2 naturally
by re-entering ``scaffold``.

Users who want an adversarial audit outside scaffold emit
``append_pending_dispatch(target_workflow="scaffold",
phase_hint="layer-check")`` from the current workflow and let navigate
re-engage ``scaffold``.
"""

import os
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))
from hook_utils import emit_hook_output, emit_noop, read_stdin

from workflow_state import (
    WorkflowContext,
    append_journal_event,
    get_scaffold_state_safe,
)

_WATCHED_TOOLS = {"Edit", "Write", "NotebookEdit"}


def _is_layer_file(file_path: str) -> bool:
    """True for .ivy files that are NOT test specs."""
    if not file_path.endswith(".ivy"):
        return False
    name = os.path.basename(file_path)
    return "_test_" not in name and not name.endswith("_test.ivy")


def _detect_layer(file_path: str, scaffold_state: "dict[str, Any] | None") -> str | None:
    """Resolve layer name from scaffold-state.yaml `layers` map, if available."""
    if not scaffold_state:
        return None
    layers = scaffold_state.get("layers") or {}
    target = os.path.basename(file_path)
    for name, entry in layers.items():
        if isinstance(entry, dict) and os.path.basename(entry.get("file", "")) == target:
            return name
    return None


def _build_directive(
    *,
    file_path: str,
    protocol: str,
    methodology: str | None,
    layer_name: str | None,
) -> str:
    """Construct the G2 dispatch additionalContext directive."""
    layer_line = f"- Layer (from scaffold-state.yaml): {layer_name}" if layer_name else "- Layer: unknown — not resolved from scaffold-state.yaml"
    methodology_line = f"- Methodology: {methodology}" if methodology else "- Methodology: unknown (NACT/NSCT overlays not applied)"
    nsct_note = ""
    if methodology == "nsct":
        nsct_note = "\n  - NSCT active: include catalog range #260-289 in the slice."

    return (
        "[G2 modeling gate] An .ivy layer file has been written while the `scaffold` workflow is active. "
        "Dispatch the G2 modeling gate before proceeding to the next layer.\n\n"
        f"Artifact under audit: `{file_path}` (protocol: {protocol}).\n"
        f"{layer_line}\n"
        f"{methodology_line}{nsct_note}\n\n"
        "To dispatch:\n"
        "1. Read the G2 verbatim critic template at `skills/ivy/references/critic_prompts/g2_modeling.md` (your preloaded `verification-failures` skill provides the catalog).\n"
        "2. Apply the Adversarial Quality Gates discipline-layer rules: verbatim spawn prompts, dual context isolation, asymmetric vote (Sonnet × 5 default: 4 SOUND / 2 UNSOUND / pigeonhole exit), calibrated abstention.\n"
        "3. Each critic loads the `verification-failures` skill to access the numbered catalog and applies only ID ranges #200-249 + #250-299 (+ #260-289 if NSCT).\n"
        "4. Aggregate verdicts into VERDICT_SOUND / VERDICT_UNSOUND / VERDICT_ABSTAIN.\n"
        "5. On VERDICT_UNSOUND, write `[GAP: #NN <reason>]` markers at the cited file:line locations per `.claude/rules/gap-markers.md` (orchestrator only — never let a critic edit the file).\n"
        "6. Append a `gate_verdict` event to the workflow journal via `ivy_workflow_state(action=\"append_journal\", event_type=\"gate_verdict\", payload={...})`.\n"
        "7. Render the verdict block per `styles/tool-renderers/ivy_verdict.md` in the scaffold-overlay format.\n\n"
        "Do not proceed to the next layer until each `[GAP:]` is either resolved or deliberately promoted to `// DEFERRED YYYY-MM-DD: …`."
    )


def main() -> None:
    hook_input = read_stdin()
    if not hook_input:
        emit_noop("PostToolUse", "no hook input")
        return

    tool_name = hook_input.get("tool_name", "")
    if tool_name not in _WATCHED_TOOLS:
        emit_noop("PostToolUse", f"tool '{tool_name}' not watched by G2")
        return

    tool_input = hook_input.get("tool_input", {})
    file_path = tool_input.get("file_path", "")
    if not _is_layer_file(file_path):
        emit_noop("PostToolUse", "edit is not a layer file")
        return

    ctx = WorkflowContext.current()
    # G2 is scaffold-only by design — see "Why scaffold-only?" in the module
    # docstring for the rationale.
    if ctx is None or ctx.workflow != "scaffold":
        emit_noop("PostToolUse", "G2 is scaffold-workflow only")
        return

    scaffold_state = get_scaffold_state_safe(ctx.protocol_dir) or {}
    protocol = scaffold_state.get("protocol") or os.path.basename(ctx.protocol_dir.rstrip("/"))
    methodology = scaffold_state.get("methodology")
    layer_name = _detect_layer(file_path, scaffold_state)

    append_journal_event(
        ctx.protocol_dir,
        event_type="gate_dispatched",
        payload={
            "gate": "g2",
            "trigger": "assess-modeling.py",
            "artifact": file_path,
            "layer": layer_name,
            "methodology": methodology,
        },
        workflow="scaffold",
        phase=ctx.phase,
    )

    emit_hook_output(
        "PostToolUse",
        system_message=f"[G2 modeling gate] dispatched on {os.path.basename(file_path)}",
        additional_context=_build_directive(
            file_path=file_path,
            protocol=protocol,
            methodology=methodology,
            layer_name=layer_name,
        ),
    )


if __name__ == "__main__":
    main()
