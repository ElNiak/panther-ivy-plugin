#!/usr/bin/env python3
"""PostToolUse hook: run ``ruff check --fix`` on edited Python files.

Fires after Write/Edit on ``.py`` files, runs ``ruff check --fix --quiet``
against the file, and surfaces a status line indicating how many issues
were auto-fixed (or the file was already clean).

Scope: by default, only files under ``${CLAUDE_PLUGIN_ROOT}`` are linted —
this keeps the hook scoped to plugin source and avoids surprising users
who edit unrelated Python in the same session. Set
``IVY_RUFF_HOOK_GLOBAL=1`` to disable the prefix check and lint every
``.py`` file.

Graceful degradation:

  * ``ruff`` not installed → ``[ivy-noop] ruff binary not on PATH`` and
    return; the user can still benefit from every other hook on the chain.
  * file outside the plugin scope (when ``IVY_RUFF_HOOK_GLOBAL`` unset)
    → ``[ivy-noop] file outside plugin scope``.
  * file is not ``.py`` → ``[ivy-noop] non-Python file``.
  * ruff exits non-zero AND output is empty → ``[ivy-ruff] check failed``
    surfaced via stderr-derived system message; tool call is not blocked.

Always exits 0. The hook is informational; failing the tool call would
discard user edits.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib.hook_utils import emit_hook_output, emit_noop, read_stdin  # noqa: E402

_RUFF_TIMEOUT_S = 10


def _ruff_executable() -> str | None:
    """Return the ruff binary path, preferring the active virtualenv."""
    return shutil.which("ruff")


def _is_in_plugin_scope(file_path: Path) -> bool:
    """True iff ``file_path`` is under ``CLAUDE_PLUGIN_ROOT``.

    Uses ``Path.resolve()`` so symlinked worktrees and the canonical
    plugin source resolve to the same prefix. Falls back to a string
    comparison if either side fails to resolve (rare on macOS).
    """
    plugin_root = os.environ.get("CLAUDE_PLUGIN_ROOT", "").strip()
    if not plugin_root:
        return False
    try:
        return Path(plugin_root).resolve() in file_path.resolve().parents
    except OSError:
        return str(file_path).startswith(plugin_root.rstrip("/") + "/")


def _summarize_fix_count(stdout: str) -> int:
    """Count findings in ruff JSON output that have a non-null ``fix`` field.

    Ruff's JSON output is a list of finding objects on stdout; each finding
    has a ``fix`` field (``null`` if not auto-fixable, or an object with
    ``applicability`` indicating the fix kind). Empty stdout means no
    findings — return 0.
    """
    if not stdout.strip():
        return 0
    try:
        findings = json.loads(stdout)
    except (ValueError, TypeError):
        return 0
    if not isinstance(findings, list):
        return 0
    return sum(
        1 for f in findings
        if isinstance(f, dict) and f.get("fix") is not None
    )


def _run_ruff(ruff_bin: str, file_path: Path) -> tuple[int, int, str]:
    """Count fixable findings, then apply fixes. Return (rc, fixed_count, stderr).

    A single ``ruff check --fix`` returns the *remaining* findings after the
    fix pass (typically empty for auto-fixable issues), so counting from
    that output reports zero even when fixes were applied. The two-call
    approach below runs ``--no-fix`` first to enumerate fixable findings,
    then ``--fix`` to apply them, and returns the pre-pass count alongside
    the apply-pass return code and stderr.
    """
    pre = subprocess.run(
        [ruff_bin, "check", "--no-fix", "--output-format", "json", str(file_path)],
        capture_output=True,
        text=True,
        timeout=_RUFF_TIMEOUT_S,
    )
    fixable_count = _summarize_fix_count(pre.stdout)
    if fixable_count == 0:
        return pre.returncode, 0, pre.stderr

    apply = subprocess.run(
        [ruff_bin, "check", "--fix", "--quiet", str(file_path)],
        capture_output=True,
        text=True,
        timeout=_RUFF_TIMEOUT_S,
    )
    return apply.returncode, fixable_count, apply.stderr


def main() -> None:
    data = read_stdin()
    tool_input = data.get("tool_input", {}) or {}
    raw_path = tool_input.get("file_path", "")

    if not raw_path or not raw_path.endswith(".py"):
        emit_noop("PostToolUse", "non-Python file or empty path")
        return

    file_path = Path(raw_path)
    if not file_path.is_file():
        emit_noop("PostToolUse", f"file no longer exists: {file_path.name}")
        return

    if os.environ.get("IVY_RUFF_HOOK_GLOBAL", "").strip() != "1":
        if not _is_in_plugin_scope(file_path):
            emit_noop(
                "PostToolUse",
                "file outside plugin scope (set IVY_RUFF_HOOK_GLOBAL=1 to override)",
            )
            return

    ruff_bin = _ruff_executable()
    if ruff_bin is None:
        emit_noop("PostToolUse", "ruff binary not on PATH")
        return

    try:
        rc, fixed, stderr = _run_ruff(ruff_bin, file_path)
    except subprocess.TimeoutExpired:
        emit_hook_output(
            "PostToolUse",
            system_message=f"[ivy-ruff] check timed out after {_RUFF_TIMEOUT_S}s",
        )
        return

    if rc not in (0, 1):
        # rc=0: clean, rc=1: issues found (some may have been auto-fixed),
        # any other rc means ruff itself errored.
        emit_hook_output(
            "PostToolUse",
            system_message=f"[ivy-ruff] check failed (rc={rc}) on {file_path.name}",
            additional_context=stderr.strip()[:1500] or None,
        )
        return

    if fixed > 0:
        emit_hook_output(
            "PostToolUse",
            system_message=(
                f"[ivy-ruff] {fixed} issue{'s' if fixed != 1 else ''} "
                f"auto-fixed in {file_path.name}"
            ),
            additional_context=stderr.strip()[:1500] or None,
        )
        return

    emit_noop("PostToolUse", f"{file_path.name} clean (no ruff fixes)")


if __name__ == "__main__":
    main()
