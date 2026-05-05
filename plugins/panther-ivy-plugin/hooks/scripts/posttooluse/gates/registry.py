#!/usr/bin/env python3
"""Declarative gate registry. Each Gate describes one G-gate dispatcher.

The registry is data-only — every entry is a record of references to
handler functions in `gate_handlers.py`. Runtime logic lives in
`run-gate.py` (the orchestrator) and `gate_handlers.py` (per-gate
parse, predicate, and dispatch).

Adding a new gate is two-step: append a `Gate(...)` literal here and
implement the three matching handlers (`parse_<id>`,
`predicate_<id>`, `dispatch_<id>`) in `gate_handlers.py`. The runner
needs no modification.
"""

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, FrozenSet, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from posttooluse.gates import gate_handlers


@dataclass(frozen=True)
class Gate:
    """Per-gate dispatch contract.

    Scalar fields (`id`, `name`, `watched_tools`, `workflow_required`)
    describe matchers and scope. The three callable fields describe
    the handler pipeline the runner threads `ctx` through:

      tool_name in watched_tools  →  parse_input(hook_input) → ctx
                                  →  predicate(ctx)
                                  →  workflow gate (if workflow_required)
                                  →  dispatch(ctx)  # appends journal + emits hook output

    `dispatch` consolidates payload-build, journal-append, message
    composition, and `emit_hook_output` into a single per-gate
    function. This shape lets the AST-discipline scanners
    (`test_hook_output_discipline.py`,
    `test_observability_write_discipline.py`) see the matching
    `journal_path(...)` call and the T2-template f-string
    `systemMessage` in the same file the journal write lives in.
    """

    id: str
    name: str
    watched_tools: FrozenSet[str]
    workflow_required: Optional[str]
    parse_input: Callable
    predicate: Callable
    dispatch: Callable


GATES: "dict[str, Gate]" = {
    "g2": Gate(
        id="g2",
        name="modeling-gate",
        watched_tools=frozenset({"Edit", "Write", "NotebookEdit"}),
        workflow_required="scaffold",
        parse_input=gate_handlers.parse_g2,
        predicate=gate_handlers.predicate_g2,
        dispatch=gate_handlers.dispatch_g2,
    ),
    "g3": Gate(
        id="g3",
        name="test-spec-gate",
        watched_tools=frozenset({"Edit", "Write", "NotebookEdit"}),
        workflow_required="scaffold",
        parse_input=gate_handlers.parse_g3,
        predicate=gate_handlers.predicate_g3,
        dispatch=gate_handlers.dispatch_g3,
    ),
    "g5": Gate(
        id="g5",
        name="trace-analysis-gate",
        watched_tools=frozenset({"ivy_iut_test"}),
        workflow_required=None,
        parse_input=gate_handlers.parse_g5,
        predicate=gate_handlers.predicate_g5,
        dispatch=gate_handlers.dispatch_g5,
    ),
    "g0b": Gate(
        id="g0b",
        name="plan-fidelity-gate",
        watched_tools=frozenset({"Edit", "Write", "Bash", "NotebookEdit"}),
        workflow_required=None,  # G0b is workflow-agnostic; fires whenever there is an unpaired plan_approved.
        parse_input=gate_handlers.parse_g0b,
        predicate=gate_handlers.predicate_g0b,
        dispatch=gate_handlers.dispatch_g0b,
    ),
}
