"""Unit tests for hook_utils.emit_hook_output.

`emit_hook_output` is the single point through which every blocking PreToolUse
hook emits its deny decision and every informational hook emits context to the
model. The function's contract (Claude Code advanced-protocol hook JSON, exit 0
required) is load-bearing for workspace edit isolation (check-workspace-scope.py)
and the MCP-CLI block hook (block-direct-ivy.sh). These tests pin the JSON
envelope shape so accidental changes surface immediately.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest

HOOKS_SCRIPTS = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HOOKS_SCRIPTS))


def _load_module() -> Any:
    spec = importlib.util.spec_from_file_location(
        "hook_utils", HOOKS_SCRIPTS / "hook_utils.py"
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _parse(raw: str) -> dict[str, Any]:
    return json.loads(raw.strip())


def test_emits_minimal_envelope_with_event_name_only(
    capsys: pytest.CaptureFixture[str],
) -> None:
    mod = _load_module()
    mod.emit_hook_output("PreToolUse")
    payload = _parse(capsys.readouterr().out)
    assert payload == {"hookSpecificOutput": {"hookEventName": "PreToolUse"}}


def test_deny_reason_sets_permission_decision(
    capsys: pytest.CaptureFixture[str],
) -> None:
    mod = _load_module()
    mod.emit_hook_output(
        "PreToolUse",
        deny_reason="BLOCKED: file outside active workspace",
    )
    payload = _parse(capsys.readouterr().out)
    hook = payload["hookSpecificOutput"]
    assert hook["hookEventName"] == "PreToolUse"
    assert hook["permissionDecision"] == "deny"
    assert (
        hook["permissionDecisionReason"]
        == "BLOCKED: file outside active workspace"
    )


def test_additional_context_appears_in_hook_specific_output(
    capsys: pytest.CaptureFixture[str],
) -> None:
    mod = _load_module()
    mod.emit_hook_output(
        "PreToolUse",
        additional_context="Consider /set-workspace bgp",
    )
    payload = _parse(capsys.readouterr().out)
    assert (
        payload["hookSpecificOutput"]["additionalContext"]
        == "Consider /set-workspace bgp"
    )
    assert "permissionDecision" not in payload["hookSpecificOutput"]


def test_system_message_sits_at_top_level_not_inside_hook_specific_output(
    capsys: pytest.CaptureFixture[str],
) -> None:
    mod = _load_module()
    mod.emit_hook_output("Notification", system_message="MCP reconnecting")
    payload = _parse(capsys.readouterr().out)
    assert payload["systemMessage"] == "MCP reconnecting"
    assert "systemMessage" not in payload["hookSpecificOutput"]


def test_deny_and_additional_context_combine(
    capsys: pytest.CaptureFixture[str],
) -> None:
    mod = _load_module()
    mod.emit_hook_output(
        "PreToolUse",
        deny_reason="BLOCKED",
        additional_context="Use /clear-workspace to remove restrictions",
    )
    payload = _parse(capsys.readouterr().out)
    hook = payload["hookSpecificOutput"]
    assert hook["permissionDecision"] == "deny"
    assert hook["permissionDecisionReason"] == "BLOCKED"
    assert (
        hook["additionalContext"]
        == "Use /clear-workspace to remove restrictions"
    )


def test_falsy_deny_reason_is_ignored(
    capsys: pytest.CaptureFixture[str],
) -> None:
    mod = _load_module()
    mod.emit_hook_output("PreToolUse", deny_reason="")
    payload = _parse(capsys.readouterr().out)
    assert "permissionDecision" not in payload["hookSpecificOutput"]


def test_output_is_single_json_line(
    capsys: pytest.CaptureFixture[str],
) -> None:
    mod = _load_module()
    mod.emit_hook_output(
        "PostToolUse",
        additional_context="line one\nline two",
    )
    raw = capsys.readouterr().out
    assert raw.count("\n") == 1 and raw.endswith("\n")
    payload = json.loads(raw)
    assert "\n" in payload["hookSpecificOutput"]["additionalContext"]
