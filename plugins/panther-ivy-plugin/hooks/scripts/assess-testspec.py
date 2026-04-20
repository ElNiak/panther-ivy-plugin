#!/usr/bin/env python3
"""PostToolUse hook: trigger G3 test-spec gate on *_test_*.ivy writes.

Fires after Edit|Write on an Ivy test spec file (name contains `_test_`).
When the active workflow is `build`, emits an additionalContext directive
instructing Claude to dispatch G3 test-spec critics via the reflection-patterns
skill.

The hook itself does NOT spawn critics — it is a subprocess and cannot invoke
the Agent tool. Claude reads the additionalContext on the next turn and runs
the gate dispatch (verbatim prompt, asymmetric vote, calibrated verdict, GAP
marker writing).

Non-blocking — always exits 0.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from hook_utils import emit_hook_output, read_stdin

from workflow_state import (
    append_journal_event,
    find_protocol_dir,
    get_active_workflow,
    get_build_state,
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
        "[G3 test-spec gate] A `*_test_*.ivy` file has been written while the `build` workflow is active. "
        "Dispatch the G3 test-spec gate before running `ivy_compile` / `ivy_verify`.\n\n"
        f"Artifact under audit: `{file_path}` (protocol: {protocol}).\n"
        f"{methodology_line}{nsct_note}\n\n"
        "To dispatch:\n"
        "1. Load the `reflection-patterns` skill via the Skill tool.\n"
        "2. Read the G3 verbatim critic template at `critic_prompts/g3_testspec.md` within that skill's references.\n"
        "3. Apply the Adversarial Quality Gates discipline-layer rules: verbatim spawn prompts, dual context isolation, asymmetric vote (Sonnet × 5 default: 4 SOUND / 2 UNSOUND / pigeonhole exit), calibrated abstention.\n"
        "4. Each critic must load the `ivy-error-patterns` skill to access the numbered catalog and apply only ID ranges #200-208 + #256-259 + #300-399.\n"
        "5. Before spawning critics, gather inputs the template expects: the test file contents, the RFC requirement manifest (typically `{protocol}_requirements.yaml`), and the output of `ivy_coverage(mode=\"matrix\", test_file=<file_path>)`.\n"
        "6. Aggregate verdicts into VERDICT_SOUND / VERDICT_UNSOUND / VERDICT_ABSTAIN.\n"
        "7. On VERDICT_UNSOUND, write `[GAP: #NN <reason>]` markers at the cited file:line locations per `.claude/rules/gap-markers.md` (orchestrator only).\n"
        "8. Append a `gate_verdict` event to the workflow journal via `ivy_workflow_state(action=\"append_journal\", event_type=\"gate_verdict\", payload={...})`.\n"
        "9. Render the verdict block per `styles/tool-renderers/ivy_verdict.md` in the build-overlay format.\n\n"
        "A test spec that looks clean but silently fails to cover a MUST requirement or over-constrains the generator is the exact failure mode G3 exists to catch — read the coverage matrix carefully."
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
    if not _is_test_spec(file_path):
        return

    protocol_dir = find_protocol_dir()
    if not protocol_dir:
        return

    active = get_active_workflow(protocol_dir)
    if not active or active.get("workflow") != "build":
        return

    build_state = get_build_state(protocol_dir) or {}
    protocol = build_state.get("protocol") or os.path.basename(protocol_dir.rstrip("/"))
    methodology = build_state.get("methodology")

    append_journal_event(
        protocol_dir,
        event_type="gate_dispatched",
        payload={
            "gate": "g3",
            "trigger": "assess-testspec.py",
            "artifact": file_path,
            "methodology": methodology,
        },
        workflow="build",
        phase=active.get("phase"),
    )

    emit_hook_output(
        "PostToolUse",
        additional_context=_build_directive(
            file_path=file_path,
            protocol=protocol,
            methodology=methodology,
        ),
    )


if __name__ == "__main__":
    main()
