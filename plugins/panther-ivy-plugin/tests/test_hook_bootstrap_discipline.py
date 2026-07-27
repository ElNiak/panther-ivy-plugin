"""AST-scan: every hook script that imports ``from lib.<X>`` must declare the
canonical ``sys.path.insert`` prelude with depth-correct ``parents[N]``.

Every hook script in ``hooks/scripts/`` that needs the ``lib/`` package
prepends ``hooks/scripts/`` to ``sys.path`` before importing, using the
canonical form

    sys.path.insert(0, str(Path(__file__).resolve().parents[N]))
    from lib.X import Y  # noqa: E402

where ``N`` matches the file's nesting depth so ``parents[N]`` resolves to
``hooks/scripts/``. The exemplar is ``hooks/scripts/cleanup/stale-pids.py``.

This test scans every ``.py`` file under ``hooks/scripts/`` (excluding
``__init__.py`` and the ``lib/`` package internals) and asserts that any file
with a ``from lib.<X> import …`` import also declares the depth-correct
prelude. Both missing-prelude and wrong-depth bugs surface in a single
diagnostic naming the offending file.

If a future hook script legitimately needs a different prelude shape, add
its ``relative_to(SCRIPTS_DIR)`` string to ``_EXEMPT_PATHS`` with an inline
comment naming the reason. The current 56-file tree has no such file.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import List, Optional

import pytest

pytestmark = pytest.mark.unit

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "hooks" / "scripts"
LIB_DIR = SCRIPTS_DIR / "lib"

# One-line escape hatch for files that legitimately need a non-canonical
# prelude. Currently empty — the strict check holds on the 56-file tree.
_EXEMPT_PATHS: frozenset[str] = frozenset()


def _expected_depth(p: Path) -> int:
    """Return the ``parents[N]`` index that lands on ``SCRIPTS_DIR`` for ``p``."""
    return len(p.relative_to(SCRIPTS_DIR).parts) - 1


def _has_lib_import(tree: ast.Module) -> bool:
    return any(
        isinstance(n, ast.ImportFrom) and (n.module or "").split(".")[0] == "lib"
        for n in ast.walk(tree)
    )


def _is_path_file_resolve_chain(node: ast.AST) -> bool:
    """True iff ``node`` matches ``Path(__file__).resolve()``."""
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "resolve"
        and isinstance(node.func.value, ast.Call)
        and isinstance(node.func.value.func, ast.Name)
        and node.func.value.func.id == "Path"
        and len(node.func.value.args) == 1
        and isinstance(node.func.value.args[0], ast.Name)
        and node.func.value.args[0].id == "__file__"
    )


def _depth_from_inner(inner: ast.AST) -> Optional[int]:
    """If ``inner`` is a ``parents[N]`` subscript or a chained ``.parent``
    sequence on a ``Path(__file__).resolve()`` chain, return the depth.
    Otherwise return None.

    Both forms are accepted because both are present in the tree:
      - ``Path(__file__).resolve().parents[N]`` — preferred, used by 18+ scripts;
      - ``Path(__file__).resolve().parent[.parent ...]`` — equivalent chain form
        used by ``observability/observe.py`` and accepted by the handoff.
    """
    if isinstance(inner, ast.Subscript):
        if (
            isinstance(inner.value, ast.Attribute)
            and inner.value.attr == "parents"
            and _is_path_file_resolve_chain(inner.value.value)
            and isinstance(inner.slice, ast.Constant)
            and isinstance(inner.slice.value, int)
        ):
            return inner.slice.value
    # Chained .parent[.parent ...]: K hops correspond to parents[K-1].
    # Example: Path(__file__).resolve().parent.parent == parents[1].
    chain = 0
    node: ast.AST = inner
    while isinstance(node, ast.Attribute) and node.attr == "parent":
        chain += 1
        node = node.value
    if chain > 0 and _is_path_file_resolve_chain(node):
        return chain - 1
    return None


def _has_canonical_prelude(tree: ast.Module, expected_depth: int) -> bool:
    """True iff a top-level statement matches::

        sys.path.insert(0, str(Path(__file__).resolve().parents[N]))

    with N == ``expected_depth``. The equivalent chained form
    ``Path(__file__).resolve().parent[.parent ...]`` is also accepted (per
    ``_depth_from_inner``).
    """
    for stmt in tree.body:
        if not isinstance(stmt, ast.Expr) or not isinstance(stmt.value, ast.Call):
            continue
        call = stmt.value
        if not (
            isinstance(call.func, ast.Attribute)
            and call.func.attr == "insert"
            and isinstance(call.func.value, ast.Attribute)
            and call.func.value.attr == "path"
            and isinstance(call.func.value.value, ast.Name)
            and call.func.value.value.id == "sys"
        ):
            continue
        if len(call.args) < 2:
            continue
        first, second = call.args[0], call.args[1]
        if not (isinstance(first, ast.Constant) and first.value == 0):
            continue
        if not (
            isinstance(second, ast.Call)
            and isinstance(second.func, ast.Name)
            and second.func.id == "str"
            and len(second.args) == 1
        ):
            continue
        depth = _depth_from_inner(second.args[0])
        if depth == expected_depth:
            return True
    return False


def _violations() -> List[str]:
    issues: List[str] = []
    for path in sorted(SCRIPTS_DIR.rglob("*.py")):
        if path.name == "__init__.py":
            continue
        if path.is_relative_to(LIB_DIR):
            continue
        rel = str(path.relative_to(SCRIPTS_DIR))
        if rel in _EXEMPT_PATHS:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError as e:
            issues.append(f"{rel}: parse error {e}")
            continue
        if not _has_lib_import(tree):
            continue
        depth = _expected_depth(path)
        if not _has_canonical_prelude(tree, depth):
            prelude = f"sys.path.insert(0, str(Path(__file__).resolve().parents[{depth}]))"
            issues.append(
                f"{rel}: missing canonical {prelude} prelude before its `from lib.…` import"
            )
    return issues


def test_all_lib_importers_use_canonical_prelude() -> None:
    issues = _violations()
    assert issues == [], "\n".join(["bootstrap discipline violations:", *issues])
