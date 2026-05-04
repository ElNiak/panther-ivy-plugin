#!/usr/bin/env python3
"""PostToolUse hook: fast structural check after .ivy file writes.

Runs three quick checks (`#lang` header, balanced braces, non-empty file).
On findings, emits ``additionalContext`` with the bullet list and a one-line
``systemMessage`` summary. On no findings, emits ``[ivy-noop]``.

Always exits 0 — non-blocking.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from lib.hook_utils import emit_hook_output, emit_noop, mark_session_activity, read_stdin  # noqa: E402

_COMMENT = re.compile(r"#.*")
_STRING = re.compile(r'"[^"]*"')


def _check(file_path: Path) -> list[str]:
    """Return a list of finding strings (empty if file is structurally OK)."""
    findings: list[str] = []
    try:
        content = file_path.read_text()
    except OSError as exc:
        return [f"Could not read file: {exc}"]

    if not content:
        findings.append("File is empty")
        return findings

    first_line = content.splitlines()[0] if content.splitlines() else ""
    if "#lang ivy1.7" not in first_line:
        findings.append("Missing #lang ivy1.7 header on first line")

    stripped = _STRING.sub("", _COMMENT.sub("", content))
    opens = stripped.count("{")
    closes = stripped.count("}")
    if opens != closes:
        findings.append(f"Unbalanced braces: {opens} open vs {closes} close")

    return findings


def main() -> None:
    data = read_stdin()
    tool_input = data.get("tool_input", {})
    raw_path = tool_input.get("file_path", "")

    if not raw_path or not raw_path.endswith(".ivy"):
        emit_noop("PostToolUse", "non-.ivy file or empty path")
        return

    file_path = Path(raw_path)
    if not file_path.is_file():
        emit_noop("PostToolUse", f"file no longer exists: {file_path.name}")
        return

    mark_session_activity(f"file:{raw_path}")

    findings = _check(file_path)
    if not findings:
        emit_noop("PostToolUse", f"{file_path.name} structurally clean")
        return

    bullets = "\n".join(f"- {item}" for item in findings)
    emit_hook_output(
        "PostToolUse",
        system_message=f"[ivy-lint] {len(findings)} warning(s) in {file_path.name}",
        additional_context=(
            f"[IVY-LINT] Structural issues in {file_path.name}:\n"
            f"{bullets}\n"
            'Run ivy_diagnostics(mode="structural") MCP tool for full diagnostics.'
        ),
    )


if __name__ == "__main__":
    main()
