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

HOOKS_SCRIPTS = Path(__file__).resolve().parent.parent / "hooks" / "scripts"
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
    mod.emit_hook_output("PreToolUse", system_message="")
    payload = _parse(capsys.readouterr().out)
    assert payload == {"hookSpecificOutput": {"hookEventName": "PreToolUse"}}


def test_deny_reason_sets_permission_decision(
    capsys: pytest.CaptureFixture[str],
) -> None:
    mod = _load_module()
    mod.emit_hook_output(
        "PreToolUse",
        system_message="",
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
        system_message="",
        additional_context="Consider /set-workspace bgp",
    )
    payload = _parse(capsys.readouterr().out)
    assert (
        payload["hookSpecificOutput"]["additionalContext"]
        == "Consider /set-workspace bgp"
    )
    assert "permissionDecision" not in payload["hookSpecificOutput"]


def test_session_end_emits_hook_specific_output(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """SessionEnd is in the allow-list, so the nested envelope is emitted
    and ``systemMessage`` lives top-level alongside it."""
    mod = _load_module()
    mod.emit_hook_output("SessionEnd", system_message="MCP reconnecting")
    payload = _parse(capsys.readouterr().out)
    assert payload == {
        "hookSpecificOutput": {"hookEventName": "SessionEnd"},
        "systemMessage": "MCP reconnecting",
    }


def test_stop_envelope_is_top_level_only(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Stop is not in the allow-list. The runtime rejects
    ``hookSpecificOutput`` for Stop, so the helper must emit only top-level
    fields. Pins the fix for the original validator-rejected envelope."""
    mod = _load_module()
    mod.emit_hook_output("Stop", system_message="[ivy-session] recorded")
    payload = _parse(capsys.readouterr().out)
    assert payload == {"systemMessage": "[ivy-session] recorded"}
    assert "hookSpecificOutput" not in payload


def test_notification_envelope_is_top_level_only(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Notification is not in the allow-list either. Same top-level-only
    contract as Stop."""
    mod = _load_module()
    mod.emit_hook_output("Notification", system_message="MCP reconnecting")
    payload = _parse(capsys.readouterr().out)
    assert payload == {"systemMessage": "MCP reconnecting"}
    assert "hookSpecificOutput" not in payload


def test_stop_drops_additional_context(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """``additional_context`` has no top-level home in the Stop envelope, so
    the helper drops it. Callers are expected to pass ``system_message``
    instead."""
    mod = _load_module()
    mod.emit_hook_output(
        "Stop",
        system_message="",
        additional_context="ignored for Stop",
    )
    payload = _parse(capsys.readouterr().out)
    assert payload == {}


def test_deny_and_additional_context_combine(
    capsys: pytest.CaptureFixture[str],
) -> None:
    mod = _load_module()
    mod.emit_hook_output(
        "PreToolUse",
        system_message="",
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
    mod.emit_hook_output("PreToolUse", system_message="", deny_reason="")
    payload = _parse(capsys.readouterr().out)
    assert "permissionDecision" not in payload["hookSpecificOutput"]


def test_unknown_event_name_raises_value_error() -> None:
    """``emit_hook_output`` raises on a misspelled or unknown event name.

    A typo like ``"SessiontStart"`` would silently fall outside the runtime's
    allow-list and the additionalContext field would be dropped without
    warning. The raise here turns that silent-failure mode into a loud
    Python traceback that surfaces during test runs."""
    mod = _load_module()
    with pytest.raises(ValueError, match="unknown event_name"):
        mod.emit_hook_output("SessiontStart", system_message="")


def test_none_system_message_raises_type_error() -> None:
    """``emit_hook_output`` raises on a missing ``system_message``.

    Empty string is allowed (suppresses the field); ``None`` is not.
    Backs the AST lint test in ``test_hook_output_discipline.py``: a
    contributor who forgets the kwarg gets a loud Python traceback
    rather than a silently-broken hook."""
    mod = _load_module()
    with pytest.raises(TypeError, match="system_message"):
        mod.emit_hook_output("PreToolUse", system_message=None)


def test_output_is_single_json_line(
    capsys: pytest.CaptureFixture[str],
) -> None:
    mod = _load_module()
    mod.emit_hook_output(
        "PostToolUse",
        system_message="",
        additional_context="line one\nline two",
    )
    raw = capsys.readouterr().out
    assert raw.count("\n") == 1 and raw.endswith("\n")
    payload = json.loads(raw)
    assert "\n" in payload["hookSpecificOutput"]["additionalContext"]
