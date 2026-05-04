#!/usr/bin/env python3
"""Registry-mechanism tests for `posttooluse/gates/registry.py`.

These tests check static properties of the `GATES` dict and `Gate`
dataclass — they do NOT subprocess into `run-gate.py` to verify
end-to-end dispatch. End-to-end coverage lives in
`tests/test_gate_hooks.py` (subprocess-driven against the runner with
`extra_argv=["--id", "g{2,3,5}"]`). The two test files are
intentionally non-overlapping: deleting either would leave a real
coverage gap.

What we cover here:

- `GATES` keys are exactly `{g2, g3, g5}` (catches accidental
  additions/removals).
- Each `Gate` entry has the expected scalar field types and
  callable handler fields (catches API drift between
  `registry.py` and `gate_handlers.py`).
- `workflow_required` is consistent with the gate's documented
  scope (G2/G3 scaffold-only, G5 unconstrained).
- The runner's argparse rejects an unknown `--id` (one
  subprocess call — testing the runner shell, not gate dispatch).
- Handler signatures match the runner's expectations (e.g.,
  `parse_input(hook_input)`, `message_builder(ctx, journal_p)`).
"""

import inspect
import subprocess
import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = PLUGIN_ROOT / "hooks" / "scripts"
RUN_GATE = SCRIPTS / "posttooluse" / "gates" / "run-gate.py"

sys.path.insert(0, str(SCRIPTS))
from posttooluse.gates import gate_handlers
from posttooluse.gates.registry import GATES, Gate


def test_GATES_dict_has_expected_ids():
    """GATES owns exactly g2, g3, g5 — no more, no fewer."""
    assert set(GATES.keys()) == {"g2", "g3", "g5"}


def test_Gate_field_types_are_correct():
    """Each Gate entry has the documented scalar + callable shape."""
    for gid, g in GATES.items():
        assert isinstance(g, Gate)
        assert g.id == gid, f"Gate.id ({g.id!r}) must match registry key ({gid!r})"
        assert isinstance(g.name, str) and g.name, f"{gid}: name must be a non-empty str"
        assert isinstance(g.watched_tools, frozenset), f"{gid}: watched_tools must be frozenset"
        assert g.watched_tools, f"{gid}: watched_tools must be non-empty"
        assert g.workflow_required is None or isinstance(g.workflow_required, str), (
            f"{gid}: workflow_required must be str|None"
        )
        for field_name in ("parse_input", "predicate", "dispatch"):
            handler = getattr(g, field_name)
            assert callable(handler), f"{gid}.{field_name} must be callable"


def test_workflow_required_consistency():
    """G2/G3 are scaffold-only by design; G5 is unconstrained."""
    assert GATES["g2"].workflow_required == "scaffold"
    assert GATES["g3"].workflow_required == "scaffold"
    assert GATES["g5"].workflow_required is None


def test_watched_tools_match_documented_matchers():
    """Watched-tools sets match the hooks.json matcher contract."""
    # G2 / G3: `Write|Edit` matcher in hooks.json (NotebookEdit included
    # as a forward-compatible synonym for Edit-class operations).
    assert GATES["g2"].watched_tools == frozenset({"Edit", "Write", "NotebookEdit"})
    assert GATES["g3"].watched_tools == frozenset({"Edit", "Write", "NotebookEdit"})
    # G5 fires on the ivy_iut_test MCP tool only.
    assert GATES["g5"].watched_tools == frozenset({"ivy_iut_test"})


def test_handler_signatures_match_runner_expectations():
    """Handlers expose the parameter shape the runner assumes."""
    for gid, g in GATES.items():
        # parse_input takes one positional arg (hook_input dict).
        params = inspect.signature(g.parse_input).parameters
        assert len(params) == 1, f"{gid}.parse_input must take 1 arg"

        # predicate takes one positional arg (ctx dict).
        params = inspect.signature(g.predicate).parameters
        assert len(params) == 1, f"{gid}.predicate must take 1 arg"

        # dispatch takes one positional arg (ctx dict); returns None
        # (side-effect via append_journal_event + emit_hook_output).
        params = inspect.signature(g.dispatch).parameters
        assert len(params) == 1, f"{gid}.dispatch must take 1 arg"


def test_run_gate_argparse_rejects_unknown_id():
    """The runner's argparse rejects an --id not in GATES.keys()."""
    result = subprocess.run(
        [sys.executable, str(RUN_GATE), "--id", "g99"],
        capture_output=True,
        text=True,
        timeout=5,
    )
    assert result.returncode != 0, "argparse should reject unknown gate id"
    # Argparse's error text mentions the invalid choice.
    assert "invalid choice" in result.stderr, (
        f"expected argparse 'invalid choice' diagnostic; got stderr={result.stderr!r}"
    )


def test_gate_handlers_module_exposes_per_gate_functions():
    """The flat module surface registry.py imports actually exists."""
    for prefix in ("parse", "predicate", "dispatch"):
        for gid in ("g2", "g3", "g5"):
            attr = f"{prefix}_{gid}"
            assert hasattr(gate_handlers, attr), (
                f"gate_handlers.{attr} missing — registry.py reference would break"
            )
            assert callable(getattr(gate_handlers, attr))


def test_g5_predicate_gates_missing_output_dir():
    """Missing output_dir: parse_g5 returns a ctx; predicate_g5 blocks dispatch.

    After F1 (parse_g5 no longer enforces non-empty output_dir), the gate
    condition is owned entirely by predicate_g5. A parseable tool_result
    with no output_dir must yield parse_g5(...) != None (parse succeeds)
    and predicate_g5(ctx) == False (gate blocks dispatch).
    """
    hook_input = {
        "tool_result": '{"protocol": "quic", "test": "t1", "iut": "picoquic", "run_id": "r1"}'
    }
    ctx = gate_handlers.parse_g5(hook_input)
    assert ctx is not None, "parse_g5 must succeed when tool_result is parseable"
    assert ctx.get("artifacts", {}).get("output_dir", "") == "", (
        "output_dir must be empty string when absent from tool_result"
    )
    assert gate_handlers.predicate_g5(ctx) is False, (
        "predicate_g5 must return False (block dispatch) when output_dir is empty"
    )
