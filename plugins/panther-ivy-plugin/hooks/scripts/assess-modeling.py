#!/usr/bin/env python3
"""PostToolUse hook: trigger G2 modeling gate on .ivy layer writes.

Fires after Edit|Write on a .ivy file (excluding *_test_*.ivy). When the
active workflow is `build`, emits an additionalContext directive instructing
Claude to dispatch G2 modeling critics via the reflection-patterns skill.

The hook itself does NOT spawn critics — it is a subprocess and cannot invoke
the Agent tool. Claude reads the additionalContext on the next turn and runs
the gate dispatch (verbatim prompt, asymmetric vote, calibrated verdict, GAP
marker writing).

Non-blocking — always exits 0. Gate dispatch failures are non-fatal; the
verdict event is recorded in the workflow journal, not surfaced as an error.
"""

import os
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent))
from hook_utils import emit_hook_output, read_stdin

from workflow_state import (
    WorkflowContext,
    append_journal_event,
    get_build_state,
)

_WATCHED_TOOLS = {"Edit", "Write", "NotebookEdit"}


def _is_layer_file(file_path: str) -> bool:
    """True for .ivy files that are NOT test specs."""
    if not file_path.endswith(".ivy"):
        return False
    name = os.path.basename(file_path)
    return "_test_" not in name and not name.endswith("_test.ivy")


def _detect_layer(file_path: str, build_state: "dict[str, Any] | None") -> str | None:
    """Resolve layer name from build-state.yaml `layers` map, if available."""
    if not build_state:
        return None
    layers = build_state.get("layers") or {}
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
    layer_line = f"- Layer (from build-state.yaml): {layer_name}" if layer_name else "- Layer: unknown — not resolved from build-state.yaml"
    methodology_line = f"- Methodology: {methodology}" if methodology else "- Methodology: unknown (NACT/NSCT overlays not applied)"
    nsct_note = ""
    if methodology == "nsct":
        nsct_note = "\n  - NSCT active: include catalog range #260-289 in the slice."

    return (
        "[G2 modeling gate] An .ivy layer file has been written while the `build` workflow is active. "
        "Dispatch the G2 modeling gate before proceeding to the next layer.\n\n"
        f"Artifact under audit: `{file_path}` (protocol: {protocol}).\n"
        f"{layer_line}\n"
        f"{methodology_line}{nsct_note}\n\n"
        "To dispatch:\n"
        "1. Load the `reflection-patterns` skill via the Skill tool.\n"
        "2. Read the G2 verbatim critic template at `critic_prompts/g2_modeling.md` within that skill's references.\n"
        "3. Apply the Adversarial Quality Gates discipline-layer rules from `reflection-patterns`: verbatim spawn prompts, dual context isolation, asymmetric vote (Sonnet × 5 default: 4 SOUND / 2 UNSOUND / pigeonhole exit), calibrated abstention.\n"
        "4. Each critic must load the `ivy-error-patterns` skill to access the numbered catalog and apply only ID ranges #200-249 + #250-299 (+ #260-289 if NSCT).\n"
        "5. Aggregate verdicts into VERDICT_SOUND / VERDICT_UNSOUND / VERDICT_ABSTAIN.\n"
        "6. On VERDICT_UNSOUND, write `[GAP: #NN <reason>]` markers at the cited file:line locations per `.claude/rules/gap-markers.md` (orchestrator only — never let a critic edit the file).\n"
        "7. Append a `gate_verdict` event to the workflow journal via `ivy_workflow_state(action=\"append_journal\", event_type=\"gate_verdict\", payload={...})`.\n"
        "8. Render the verdict block per `styles/tool-renderers/ivy_verdict.md` in the build-overlay format.\n\n"
        "Do not proceed to the next layer until each `[GAP:]` is either resolved or deliberately promoted to `// DEFERRED YYYY-MM-DD: …`."
    )


def main() -> None:
    hook_input = read_stdin()
    if not hook_input:
        return

    tool_name = hook_input.get("tool_name", "")
    if tool_name not in _WATCHED_TOOLS:
        return

    tool_input = hook_input.get("tool_input", {})
    file_path = tool_input.get("file_path", "")
    if not _is_layer_file(file_path):
        return

    ctx = WorkflowContext.current()
    if ctx is None or ctx.workflow != "build":
        return

    build_state = get_build_state(ctx.protocol_dir) or {}
    protocol = build_state.get("protocol") or os.path.basename(ctx.protocol_dir.rstrip("/"))
    methodology = build_state.get("methodology")
    layer_name = _detect_layer(file_path, build_state)

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
        workflow="build",
        phase=ctx.phase,
    )

    emit_hook_output(
        "PostToolUse",
        additional_context=_build_directive(
            file_path=file_path,
            protocol=protocol,
            methodology=methodology,
            layer_name=layer_name,
        ),
    )


if __name__ == "__main__":
    main()
