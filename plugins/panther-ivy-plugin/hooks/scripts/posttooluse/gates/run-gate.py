#!/usr/bin/env python3
"""Parametric G-gate runner — `--id g2|g3|g5` dispatches via the registry.

Replaces the per-gate dispatchers (`g2-modeling.py`, `g3-testspec.py`,
`g5-trace.py`). Threads a single `ctx` dict through the per-gate
handler pipeline declared in `registry.GATES`:

    tool_name watched?  →  parse_input → ctx
                        →  predicate
                        →  workflow gate (if workflow_required)
                        →  protocol_dir resolution
                        →  gate.dispatch(ctx)  # appends journal + emits hook

The journal-append and `emit_hook_output` calls live inside each
gate's `dispatch_<id>` function (in `gate_handlers.py`) so the
AST-discipline scanners can see the matching `journal_path(...)` and
T2-template `systemMessage` in the same source file.

Non-blocking — always exits 0 except when argparse rejects an unknown
`--id`. Any handler returning `None`/`False` triggers `emit_noop` and
clean exit, matching the original dispatcher semantics.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from lib.hook_utils import emit_noop, read_stdin
from lib.workflow_state import WorkflowContext, find_protocol_dir
from posttooluse.gates.registry import GATES


def main() -> None:
    parser = argparse.ArgumentParser(description="Parametric G-gate runner.")
    parser.add_argument("--id", required=True, choices=sorted(GATES.keys()),
                        help="Gate id to dispatch (one of: " + ", ".join(sorted(GATES.keys())) + ")")
    args = parser.parse_args()
    gate = GATES[args.id]

    hook_input = read_stdin()
    if not hook_input:
        emit_noop("PostToolUse", f"{gate.id} skipped: no hook input")
        return

    tool_name = hook_input.get("tool_name", "")
    if tool_name not in gate.watched_tools:
        emit_noop("PostToolUse", f"tool '{tool_name}' not watched by {gate.id}")
        return

    ctx = gate.parse_input(hook_input)
    if ctx is None:
        emit_noop("PostToolUse", f"{gate.id} skipped: parse_input returned None")
        return

    if not gate.predicate(ctx):
        emit_noop("PostToolUse", f"{gate.id} skipped: predicate returned False")
        return

    # Workflow gate (G2/G3 are scaffold-only; G5 has no workflow_required).
    if gate.workflow_required:
        workflow_ctx = WorkflowContext.current()
        if workflow_ctx is None or workflow_ctx.workflow != gate.workflow_required:
            emit_noop(
                "PostToolUse",
                f"{gate.id} is {gate.workflow_required}-workflow only",
            )
            return
        ctx["workflow_ctx"] = workflow_ctx
        ctx["protocol_dir"] = workflow_ctx.protocol_dir
    else:
        ctx["workflow_ctx"] = None
        ctx["protocol_dir"] = find_protocol_dir()

    gate.dispatch(ctx)


if __name__ == "__main__":
    main()
