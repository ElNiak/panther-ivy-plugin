"""Cross-source parity test for journal event types.

The plugin's `journaling-contract.md` §3 declares the closed list of valid
``event_type`` values for the workflow journal. Three places must agree:

  1. ``hooks/scripts/workflow_state.py::_VALID_EVENT_TYPES`` (the
     hook-side validator that rejects unknown types in
     ``append_journal_event``).
  2. ``ivy-lsp/ivy_lsp/mcp/tools/workflow_state.py::_VALID_EVENT_TYPES``
     (the MCP-tool-side validator that rejects unknown types in
     ``ivy_workflow_state(action="append_journal", ...)``).
  3. The §3 markdown table in
     ``.claude/rules/journaling-contract.md`` (the canonical doc).

If they drift, the validator silently rejects (returns False) without
surfacing a contract gap. Drift was caught only by audit review until
this test landed.

This is the spot-check verification mandated by the harness audit
(finding H15) and the L9 fix in PR2.

The ivy-lsp surface is read via a relative path; if ivy-lsp is not
checked out as a sibling submodule, the test skips with a clear marker.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
PLUGIN_HOOK = PLUGIN_ROOT / "hooks" / "scripts" / "lib" / "workflow_state" / "context.py"
CONTRACT_MD = PLUGIN_ROOT / ".claude" / "rules" / "journaling-contract.md"
IVY_LSP_TOOL = (
    PLUGIN_ROOT.parent.parent.parent
    / "ivy-lsp"
    / "ivy_lsp"
    / "mcp"
    / "tools"
    / "workflow_state.py"
)


def _parse_event_set(py_file: Path) -> set[str]:
    """Extract the literal frozenset assigned to ``_VALID_EVENT_TYPES``.

    Uses ast so we don't have to import the module (which would pull in
    its dependency chain). Handles both ``frozenset({...})`` and
    ``frozenset({...,})`` syntaxes.
    """
    tree = ast.parse(py_file.read_text())
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if not (len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)):
            continue
        if node.targets[0].id != "_VALID_EVENT_TYPES":
            continue
        # Expect frozenset({...}). Walk into the call's argument.
        if not isinstance(node.value, ast.Call):
            continue
        if not (isinstance(node.value.func, ast.Name) and node.value.func.id == "frozenset"):
            continue
        if not node.value.args:
            continue
        arg = node.value.args[0]
        if isinstance(arg, ast.Set):
            return {
                str(elt.value)
                for elt in arg.elts
                if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
            }
    raise AssertionError(f"_VALID_EVENT_TYPES not found in {py_file}")


# Matches the §3 table rows. The first column is wrapped in backticks
# (`event_type` or `event_type{kind: foo}`); we extract the bare type.
_TABLE_ROW_RE = re.compile(
    r"^\|\s*`(?P<event>[a-z_]+)(?:\{[^}]*\})?`\s*\|", re.MULTILINE
)


def _parse_contract_event_set(md_file: Path) -> set[str]:
    """Extract event types from the §3 markdown table.

    Handles parameterized rows like ``progress{kind: fix_attempt}`` by
    keeping only the bare ``event_type`` part.
    """
    text = md_file.read_text()
    return {m.group("event") for m in _TABLE_ROW_RE.finditer(text)}


@pytest.fixture(scope="module")
def plugin_set() -> set[str]:
    return _parse_event_set(PLUGIN_HOOK)


@pytest.fixture(scope="module")
def contract_set() -> set[str]:
    return _parse_contract_event_set(CONTRACT_MD)


@pytest.fixture(scope="module")
def ivy_lsp_set() -> set[str]:
    if not IVY_LSP_TOOL.exists():
        pytest.skip(f"ivy-lsp sibling not checked out at {IVY_LSP_TOOL}")
    return _parse_event_set(IVY_LSP_TOOL)


def test_plugin_and_ivy_lsp_event_sets_agree(
    plugin_set: set[str], ivy_lsp_set: set[str]
) -> None:
    """Both validators must accept the same closed list of event types.

    A divergence means appends valid on one side will be silently
    rejected on the other (per ``journaling-contract.md §9``).
    """
    only_plugin = plugin_set - ivy_lsp_set
    only_ivy_lsp = ivy_lsp_set - plugin_set
    assert not only_plugin and not only_ivy_lsp, (
        f"Drift between plugin and ivy-lsp _VALID_EVENT_TYPES.\n"
        f"  Only in plugin: {sorted(only_plugin)}\n"
        f"  Only in ivy-lsp: {sorted(only_ivy_lsp)}"
    )


def test_validators_match_contract_table(
    plugin_set: set[str], contract_set: set[str]
) -> None:
    """Both validators must accept exactly the event types the contract documents."""
    only_validator = plugin_set - contract_set
    only_contract = contract_set - plugin_set
    assert not only_validator and not only_contract, (
        f"Drift between plugin _VALID_EVENT_TYPES and journaling-contract.md §3.\n"
        f"  Only in validator: {sorted(only_validator)}\n"
        f"  Only in contract:  {sorted(only_contract)}"
    )


def test_pending_dispatch_specifically_present(
    plugin_set: set[str], ivy_lsp_set: set[str], contract_set: set[str]
) -> None:
    """Regression for the original drift this test was added to catch.

    H15 of the harness audit observed ``pending_dispatch`` documented in
    the contract table but missing from the ivy-lsp validator set.
    """
    assert "pending_dispatch" in plugin_set
    assert "pending_dispatch" in ivy_lsp_set
    assert "pending_dispatch" in contract_set
