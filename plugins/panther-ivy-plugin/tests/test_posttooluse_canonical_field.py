"""Regression test pinning `tool_response` as the canonical PostToolUse stdin field.

Bug history: session 5611907a-131f-422f-a908-e07a141fc452 (2026-05-04) showed
ivy_workspace, ivy_status, ivy_coverage, ivy_manifest delivering empty {} to
PostToolUse hooks. Three hooks read non-canonical field names and fell back to
empty string. Fixed by aligning all PostToolUse hooks on `tool_response`,
matching record/askuserquestion.py:150 which works correctly.

This test pins the contract: every PostToolUse hook in this plugin reads
`tool_response` from stdin. The test will fail if any hook regresses to
`tool_output`, `tool_result`, or other non-canonical names.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

POSTUSE_DIR = Path(__file__).resolve().parent.parent / "hooks" / "scripts"
POSTUSE_HOOKS = [
    POSTUSE_DIR / "render" / "tool-result.py",
    POSTUSE_DIR / "record" / "workflow-error.py",
    POSTUSE_DIR / "record" / "askuserquestion.py",
    POSTUSE_DIR / "posttooluse" / "gates" / "gate_handlers.py",
]

_NON_CANONICAL = re.compile(r'get\("tool_(output|result|use_result)"')


@pytest.mark.parametrize("hook_path", POSTUSE_HOOKS, ids=lambda p: p.name)
def test_hook_reads_only_canonical_tool_response_field(hook_path: Path) -> None:
    """Every PostToolUse hook reads `tool_response`, never `tool_output` or `tool_result`."""
    assert hook_path.exists(), f"hook script missing: {hook_path}"
    src = hook_path.read_text(encoding="utf-8")
    bad = _NON_CANONICAL.findall(src)
    assert not bad, (
        f"{hook_path.name}: reads non-canonical field(s) {bad}. "
        "Use 'tool_response' (canonical Claude Code PostToolUse stdin field). "
        "See test docstring for the bug history."
    )
