"""AST lint: enforce the emit_hook_output discipline across all hook scripts.

Two checks:

  1. Every ``emit_hook_output`` call site passes ``system_message`` either
     as the second positional argument or as a keyword. This catches the
     accidental-omission failure mode that left ``additionalContext``
     surfaced to the model with no UI status line.

  2. No hook script constructs a ``hookSpecificOutput`` envelope by hand.
     This is the regression-prevention check for the
     ``journaling/contract-inject.py`` bug pattern, where a private
     ``emit()`` function nested ``systemMessage`` inside
     ``hookSpecificOutput`` (the runtime expects it top-level).

Run via ``pytest plugins/panther-ivy-plugin/tests/test_hook_output_discipline.py``.

Note on the ``parents[1]`` index: this test file lives at
``plugins/panther-ivy-plugin/tests/test_hook_output_discipline.py``.
``parents[0]`` is ``tests/``; ``parents[1]`` is the plugin root
(``panther-ivy-plugin/``); ``parents[2]`` would be ``plugins/`` and would
not contain ``hooks/scripts/``.
"""

from __future__ import annotations

import ast
import pathlib
from collections.abc import Iterable

import pytest

pytestmark = pytest.mark.unit

HOOKS_DIR = pathlib.Path(__file__).parents[1] / "hooks" / "scripts"

# Library modules co-located with the hook scripts but not invoked as hooks.
# Excluded from the discipline scan because they do not directly run as
# hook entry points.
_NON_HOOK_LIBS = frozenset({
    "hook_utils",
    "workflow_state",
    "statusline_cache",
    "style_utils",
})


def _all_hook_scripts() -> Iterable[pathlib.Path]:
    """Iterate every hook script under HOOKS_DIR (excluding library modules).

    Recurses into the ``observability/`` subdirectory so ``observe.py`` and
    ``log_event.py`` are scanned alongside the top-level scripts. Excludes
    the ``lib/`` package directory which contains utility modules, not hooks.
    """
    yield from (
        p
        for p in HOOKS_DIR.rglob("*.py")
        if p.stem not in _NON_HOOK_LIBS
        and "__pycache__" not in p.parts
        and "lib" not in p.parts
    )


def test_every_emit_call_passes_system_message() -> None:
    """Every emit_hook_output call site must pass system_message."""
    failures: list[str] = []
    for path in _all_hook_scripts():
        try:
            tree = ast.parse(path.read_text())
        except SyntaxError as exc:
            pytest.fail(f"{path.relative_to(HOOKS_DIR)}: {exc}")

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not (isinstance(func, ast.Name) and func.id == "emit_hook_output"):
                continue
            # system_message is positional[1] (after event_name) or keyword.
            has_pos = len(node.args) >= 2
            has_kw = any(kw.arg == "system_message" for kw in node.keywords)
            if not (has_pos or has_kw):
                failures.append(
                    f"{path.relative_to(HOOKS_DIR)}:{node.lineno}"
                )

    assert not failures, (
        "emit_hook_output calls missing system_message:\n  "
        + "\n  ".join(failures)
    )


def test_no_private_envelope_construction() -> None:
    """Catch regressions like journaling/contract-inject.py's old emit().

    A hook script that constructs the literal string ``hookSpecificOutput``
    is bypassing the canonical envelope helper and risks shape drift.
    Library modules and the helper itself are exempt; the helper module
    legitimately mentions the field name in its construction logic.
    """
    forbidden = ('"hookSpecificOutput"', "'hookSpecificOutput'")
    failures: list[str] = []
    for path in _all_hook_scripts():
        text = path.read_text()
        for pat in forbidden:
            if pat in text:
                failures.append(
                    f"{path.relative_to(HOOKS_DIR)}: contains {pat!r}"
                )
                break

    assert not failures, (
        "Hook scripts constructing hookSpecificOutput by hand "
        "(use emit_hook_output() from hook_utils instead):\n  "
        + "\n  ".join(failures)
    )


def test_no_hardcoded_workflow_journal_path_literals() -> None:
    """Enforce centralized workflow-journal path ownership.

    The workflow journal filename/path literal belongs in workflow_state.py,
    where journal_path(...) centralizes path construction. Hook scripts must
    not hardcode the path.
    """
    forbidden = ("workflow-journal.yaml", ".panther-ivy/workflow-journal")
    failures: list[str] = []
    for path in _all_hook_scripts():
        text = path.read_text()
        lines = text.splitlines()
        for idx, line in enumerate(lines, start=1):
            if any(token in line for token in forbidden):
                failures.append(f"{path.relative_to(HOOKS_DIR)}:{idx}: {line.strip()}")

    assert not failures, (
        "Hardcoded workflow journal path literals detected in hook scripts "
        "(use workflow_state.journal_path(...) or workflow_state.journal_path_template()):\n  "
        + "\n  ".join(failures)
    )


def test_appended_to_journal_messages_use_journal_path_helper() -> None:
    """Ensure T2-style appended-to-journal messages come from journal_path helpers."""
    failures: list[str] = []
    for path in _all_hook_scripts():
        text = path.read_text()
        if "appended to journal at" not in text:
            continue
        if "journal_path(" in text or "journal_path_template(" in text:
            continue
        failures.append(
            f"{path.relative_to(HOOKS_DIR)}: has 'appended to journal at' but no journal_path helper call"
        )

    assert not failures, (
        "T2 journal messages must use workflow_state helpers for path construction:\n  "
        + "\n  ".join(failures)
    )


def test_no_hardcoded_active_workflow_path_literals() -> None:
    """Enforce centralized active-workflow path ownership.

    The active-workflow filename/path literal belongs in workflow_state.py,
    where active_workflow_path(...) centralizes path construction. Hook scripts
    must not hardcode the path fragment '/.panther-ivy/active-workflow' in
    string expressions.
    """
    forbidden = ("/.panther-ivy/active-workflow",)
    failures: list[str] = []
    for path in _all_hook_scripts():
        text = path.read_text()
        lines = text.splitlines()
        for idx, line in enumerate(lines, start=1):
            if any(token in line for token in forbidden):
                failures.append(f"{path.relative_to(HOOKS_DIR)}:{idx}: {line.strip()}")

    assert not failures, (
        "Hardcoded active-workflow path literals detected in hook scripts "
        "(use workflow_state.active_workflow_path(...)):\n  "
        + "\n  ".join(failures)
    )
