"""AST + regex lint: hooks that persist state must cite a path in systemMessage.

Phase E of the workspace + observability-write discipline plan landed
2026-05-02. Catches future regressions where a new hook writes a file
(``json.dump`` / ``yaml.dump`` / ``write_text`` / ``open(... 'w'/'a' ...)``
/ ``append_journal_event`` / ``statusline_cache.update_*``) but does
not surface where it wrote in its ``systemMessage``.

The discipline is one of three canonical templates documented in
``.claude/rules/output-style.md`` § "State-persistence message templates":

* T1: ``[ivy-<surface>] recorded N <thing>(s) to <path>``
* T2: ``[ivy-<surface>] <event> appended to journal at <path>``
* T3: ``[ivy-<surface>] <thing>: <new> (was: <prev>)``

Two exemption groups:

* **Library modules** (``hook_utils``, ``workflow_state``,
  ``statusline_cache``, ``style_utils``) are not invoked as hooks.
* **High-frequency observers** (``observability/observe.py``,
  ``observability/log_event.py``) fire on every Claude tool event;
  citing the JSONL path each time would flood the scrollback. The path
  is documented in their docstrings instead.
* **Internal-state writers** (``check-indexing-ready.py``,
  ``check-workspace-scope.py``) maintain ephemeral session-scratch
  files (deny-state counter, inferred-scope tracker) that are not
  user-facing audit data. Their existing ``systemMessage`` payloads
  serve different purposes (scope decisions, indexing status).
"""

from __future__ import annotations

import ast
import pathlib
import re
from collections.abc import Iterable

import pytest

pytestmark = pytest.mark.unit

HOOKS_DIR = pathlib.Path(__file__).parents[1] / "hooks" / "scripts"

_NON_HOOK_LIBS = frozenset({
    "hook_utils",
    "workflow_state",
    "statusline_cache",
    "style_utils",
    "project_md_state",
})

_EXEMPT_HOOKS = frozenset({
    # High-frequency event observers — would flood scrollback.
    "observe",
    "log_event",
    # Internal-state writers — write ephemeral session scratch, not
    # user-facing audit trails. Their systemMessages serve unrelated
    # purposes (scope decisions, indexing readiness signals).
    "check-indexing-ready",
    "check-workspace-scope",
})

# Three canonical templates from output-style.md §"State-persistence
# message templates". A single matching emit_hook_output systemMessage
# satisfies the discipline for the whole hook.
_TEMPLATE_PATTERNS = (
    # T1: "recorded N <thing>(s) to <path>"
    re.compile(r"recorded\s+.+?\s+to\s+\S+", re.IGNORECASE),
    # T2: "<event> appended to journal at <path>"
    re.compile(r"appended\s+to\s+journal\s+at\s+\S+", re.IGNORECASE),
    # T3: "<thing>: <new> (was: <prev>)"
    re.compile(r":\s*\S+\s*\(was:\s*\S+\)", re.IGNORECASE),
    # T1-extended: "<descriptor>: <value>" — matches the SessionStart
    # banner shape "Env file: <path>" used by detect-ivy-workspace.py.
    # The descriptor word ("env file"/"wrote"/etc.) signals the intent
    # to cite a write target; the value after the colon is asserted at
    # runtime (the AST stringifier substitutes "<expr>" for f-string
    # placeholders, so a strict path-shape match would falsely fail).
    re.compile(
        r"\b(?:env\s+file|session\s+id|wrote|saved|file)\s*:\s*\S+",
        re.IGNORECASE,
    ),
)

# Method-name calls indicating a write. ``open`` is handled separately
# below because it needs argument inspection to distinguish read from
# write modes.
_WRITE_ATTR_NAMES = frozenset({
    "write_text",
    "append_journal_event",
    "update_from_hook",
    "update_section",
    "update_sections",
    "update_sections_from_hook",
})

_WRITE_BARE_NAMES = frozenset({
    "append_journal_event",
    "update_from_hook",
    "update_section",
    "update_sections",
    "update_sections_from_hook",
})


def _all_hook_scripts() -> Iterable[pathlib.Path]:
    """Yield every hook script under HOOKS_DIR (excluding libs and exempts).

    Recurses into ``observability/`` so the exempt names there are
    matched explicitly rather than being skipped by directory.
    """
    yield from (
        p
        for p in HOOKS_DIR.rglob("*.py")
        if p.stem not in _NON_HOOK_LIBS
        and p.stem not in _EXEMPT_HOOKS
        and "__pycache__" not in p.parts
        and "lib" not in p.parts
    )


def _open_arg_is_write_mode(node: ast.Call) -> bool:
    """Return True when ``open(...)`` has a ``'w'`` or ``'a'`` mode arg."""
    for arg in node.args:
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            if "w" in arg.value or "a" in arg.value:
                return True
    for kw in node.keywords:
        if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
            if isinstance(kw.value.value, str):
                if "w" in kw.value.value or "a" in kw.value.value:
                    return True
    return False


def _writes_state_lines(tree: ast.AST) -> list[int]:
    """Return line numbers where the AST persists state (any write marker)."""
    lines: list[int] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        # Attribute calls: x.write_text(), x.append_journal_event(), json.dump(), etc.
        if isinstance(func, ast.Attribute):
            attr = func.attr
            if attr in _WRITE_ATTR_NAMES:
                lines.append(node.lineno)
            elif attr == "dump" and isinstance(func.value, ast.Name) and func.value.id in ("json", "yaml"):
                lines.append(node.lineno)
            elif attr == "open" and _open_arg_is_write_mode(node):
                lines.append(node.lineno)
        # Bare names: append_journal_event(), update_from_hook(), open(... 'w' ...)
        elif isinstance(func, ast.Name):
            if func.id in _WRITE_BARE_NAMES:
                lines.append(node.lineno)
            elif func.id == "open" and _open_arg_is_write_mode(node):
                lines.append(node.lineno)
    return lines


def _collect_string_assignments(tree: ast.AST) -> dict[str, str]:
    """Map variable names to their stringified values for simple ``Assign`` nodes.

    Lets the lint follow patterns like::

        journal_suffix = (
            f"appended to journal at {path}" if ctx is not None else ""
        )
        emit_hook_output(..., system_message=f"... {journal_suffix}")

    which would otherwise miss because the literal ``appended to journal
    at`` lives in the variable definition, not in the emit call site.

    The map is module-level (last assignment wins). For ``IfExp`` values
    both branches' stringified text are concatenated — the lint only
    needs *one* branch to match a template, so a conditional assignment
    with the citation in the truthy branch satisfies the discipline.
    """
    assignments: dict[str, str] = {}
    # Walk Assigns in source order so a downstream assignment that
    # interpolates an earlier one (``status_line = f"...{env_suffix}..."``)
    # can resolve the dependency. Pass the in-progress map to
    # ``_stringify`` so each assignment sees the values bound above it.
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name):
                value = _stringify(node.value, assignments)
                if value is not None:
                    assignments[target.id] = value
    return assignments


def _stringify(
    node: ast.AST | None, names: dict[str, str] | None = None
) -> str | None:
    """Best-effort conversion of an AST string-ish node to literal-text.

    Handles plain string literals, f-strings (placeholders rendered as
    ``<expr>`` unless ``names`` resolves the referenced variable),
    string concatenation via ``+``, and ``IfExp`` (joins both branches
    so a conditional citation in either side satisfies the lint).
    Returns ``None`` when the value is not a recognisable static-text
    expression.
    """
    if node is None:
        return None
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        parts: list[str] = []
        for v in node.values:
            if isinstance(v, ast.Constant):
                parts.append(str(v.value))
            elif isinstance(v, ast.FormattedValue):
                inner = _stringify(v.value, names)
                parts.append(inner if inner is not None else "<expr>")
            else:
                parts.append("<expr>")
        return "".join(parts)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = _stringify(node.left, names) or ""
        right = _stringify(node.right, names) or ""
        return left + right
    if isinstance(node, ast.IfExp):
        body = _stringify(node.body, names) or ""
        orelse = _stringify(node.orelse, names) or ""
        return body + " " + orelse
    if isinstance(node, ast.Name) and names is not None:
        return names.get(node.id)
    return None


def _system_message_text(
    call: ast.Call, names: dict[str, str] | None = None
) -> str | None:
    """Return the systemMessage text passed to an emit_hook_output call."""
    for kw in call.keywords:
        if kw.arg == "system_message":
            return _stringify(kw.value, names)
    if len(call.args) >= 2:
        return _stringify(call.args[1], names)
    return None


def _matches_any_template(text: str) -> bool:
    return any(pat.search(text) for pat in _TEMPLATE_PATTERNS)


def test_writing_hooks_cite_path_in_system_message() -> None:
    """Every hook that persists state must emit at least one
    systemMessage following T1/T2/T3 from output-style.md.
    """
    failures: list[str] = []
    for path in _all_hook_scripts():
        try:
            tree = ast.parse(path.read_text())
        except SyntaxError as exc:
            pytest.fail(f"{path.relative_to(HOOKS_DIR)}: {exc}")

        write_lines = _writes_state_lines(tree)
        if not write_lines:
            continue

        names = _collect_string_assignments(tree)
        msg_values: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name) and func.id == "emit_hook_output":
                    msg = _system_message_text(node, names)
                    if msg is not None:
                        msg_values.append(msg)

        if not any(_matches_any_template(m) for m in msg_values):
            rel = path.relative_to(HOOKS_DIR)
            unique_lines = sorted(set(write_lines))
            failures.append(
                f"{rel}: writes state at line(s) "
                f"{','.join(str(n) for n in unique_lines)} but no "
                f"emit_hook_output systemMessage matches T1/T2/T3."
            )

    assert not failures, (
        "Hooks failing the observability-write discipline:\n  "
        + "\n  ".join(failures)
        + "\n\nApply one of the three templates from "
        + "'.claude/rules/output-style.md' § "
        + "'State-persistence message templates (T1 / T2 / T3)':"
        + "\n  T1: '[ivy-<surface>] recorded N <thing>(s) to <path>'"
        + "\n  T2: '[ivy-<surface>] <event> appended to journal at <path>'"
        + "\n  T3: '[ivy-<surface>] <thing>: <new> (was: <prev>)'"
        + "\n\nIf the hook persists internal session-scratch state that "
        + "is not user-relevant audit data, add it to _EXEMPT_HOOKS in "
        + "this lint with a comment explaining why."
    )
