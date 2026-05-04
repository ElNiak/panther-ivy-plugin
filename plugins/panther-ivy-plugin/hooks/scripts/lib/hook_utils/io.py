#!/usr/bin/env python3
"""Hook I/O utilities: stdin parsing, emit_hook_output, emit_noop, emit_dedup."""

from __future__ import annotations

import json
import sys
from pathlib import Path


VALID_EVENT_NAMES = frozenset({
    "PreToolUse",
    "PostToolUse",
    "PostToolBatch",
    "PostToolUseFailure",
    "UserPromptSubmit",
    "SessionStart",
    "SessionEnd",
    "Stop",
    "SubagentStart",
    "SubagentStop",
    "Notification",
    "PreCompact",
    "PermissionRequest",
})


_EVENTS_WITH_HOOK_SPECIFIC_OUTPUT = frozenset({
    "PreToolUse",
    "PostToolUse",
    "PostToolBatch",
    "PostToolUseFailure",
    "UserPromptSubmit",
    "SessionStart",
    "SessionEnd",
    "SubagentStart",  # accepts additionalContext empirically (~2KB cap); see feedback_subagent_start_semantics
})

MAX_CONSECUTIVE_MCP_FAILURES = 3


def read_stdin() -> dict:
    """Read and parse JSON from stdin. Returns empty dict on failure."""
    try:
        data = json.load(sys.stdin)
        return data if isinstance(data, dict) else {}
    except (OSError, EOFError, ValueError, TypeError):
        return {}


def emit_hook_output(
    event_name: str,
    *,
    system_message: str,
    additional_context: str | None = None,
    deny_reason: str | None = None,
) -> None:
    """Print a Claude Code advanced-protocol hook JSON decision to stdout.

    Two envelope shapes per the runtime schema. For events in
    ``_EVENTS_WITH_HOOK_SPECIFIC_OUTPUT`` the helper emits::

        {"hookSpecificOutput": {"hookEventName": ..., ...}, "systemMessage": ...}

    For all other events (``Stop``, ``SubagentStop``, ``Notification``,
    ``PreCompact``) the runtime rejects ``hookSpecificOutput`` entirely;
    the helper emits only top-level fields. ``additional_context`` has no
    top-level home in that schema and is silently dropped — callers
    targeting those events should pass ``system_message`` only.

    The caller MUST return via a normal exit 0 after calling this function.
    Per the Claude Code hooks protocol (https://code.claude.com/docs/en/hooks),
    JSON output is only processed on exit 0; ``sys.exit(2)`` would cause the
    JSON payload to be ignored entirely and fall back to the legacy
    block-on-exit-2 contract, which discards ``deny_reason`` and
    ``additional_context``.

    For PreToolUse hooks, passing ``deny_reason`` sets
    ``permissionDecision: "deny"`` in the envelope and blocks the tool call.
    This is the authoritative blocking mechanism; do not combine it with
    ``sys.exit(2)``.

    Args:
        event_name: Hook event name, e.g. ``"PreToolUse"`` / ``"PostToolUse"``
            / ``"Stop"``. Determines which envelope shape is emitted.
        system_message: REQUIRED top-level ``systemMessage`` shown to the user
            in the Claude Code UI out-of-band from the model. Every hook
            surface must surface what it did, even on no-op paths
            (e.g. ``"[ivy-workspace-scope] no-op (non-.ivy file)"``). Pass
            ``""`` to suppress — empty string skips the JSON field via the
            ``if system_message:`` guard below. ``None`` raises ``TypeError``
            so accidental omission is loud.
        additional_context: Optional string surfaced to the model as
            ``hookSpecificOutput.additionalContext``. Meaningful only for
            events in ``_EVENTS_WITH_HOOK_SPECIFIC_OUTPUT``; ignored otherwise.
        deny_reason: Optional string that turns the envelope into a blocking
            deny decision. Sets ``hookSpecificOutput.permissionDecision`` to
            ``"deny"`` and ``permissionDecisionReason`` to this value. Valid
            only for PreToolUse hooks.

    Raises:
        TypeError: If ``system_message`` is not a ``str``. Empty string is
            allowed and suppresses the field.

    Returns:
        None. Output is printed to stdout as a single JSON line.
    """
    if not isinstance(system_message, str):
        raise TypeError(
            "emit_hook_output requires system_message: str (got "
            f"{type(system_message).__name__}). Pass an empty string to "
            "suppress the systemMessage field; None is not allowed because "
            "every hook surface must explicitly state whether it produces "
            "a status line."
        )

    if event_name not in VALID_EVENT_NAMES:
        raise ValueError(
            f"emit_hook_output got unknown event_name {event_name!r}; "
            f"expected one of {sorted(VALID_EVENT_NAMES)}. Typo guard: a "
            "misspelled event name silently falls outside the runtime's "
            "allow-list and the additionalContext field is dropped without "
            "warning, so we raise here instead."
        )

    output: dict = {}
    if event_name in _EVENTS_WITH_HOOK_SPECIFIC_OUTPUT:
        hook_output: dict = {"hookEventName": event_name}
        if deny_reason:
            hook_output["permissionDecision"] = "deny"
            hook_output["permissionDecisionReason"] = deny_reason
        if additional_context:
            hook_output["additionalContext"] = additional_context
        output["hookSpecificOutput"] = hook_output
    if system_message:
        output["systemMessage"] = system_message
    print(json.dumps(output))


def emit_noop(event_name: str, reason: str) -> None:
    """Emit a low-priority status line for hooks that ran but did nothing.

    Convention: status messages emitted via this helper carry the
    ``[ivy-noop]`` prefix so the user can visually filter them from
    action-bearing status lines.

    Args:
        event_name: Hook event name (passed through to :func:`emit_hook_output`).
        reason: Short human-readable description of why the hook took no
            action. Combined into a ``"[ivy-noop] <reason>"`` system message.
    """
    emit_hook_output(event_name, system_message=f"[ivy-noop] {reason}")


def _hook_dedup_cache_path(hook_input: dict | None = None) -> Path | None:
    """Return the per-session ``hook-dedup.json`` path or None on error.

    Uses the same workspace + session-id resolution as the MCP health
    state so the dedup cache lives next to the per-session circuit
    breaker. Returns ``None`` when the directory chain can't be
    resolved (degraded callers fall back to emitting unconditionally).
    """
    try:
        from .workspace import get_workspace_root
        from .session import resolve_session_id
        ws_root = get_workspace_root()
        sid = resolve_session_id(hook_input)
        return Path(ws_root) / ".observability" / "sessions" / sid / "hook-dedup.json"
    except (OSError, ValueError):
        return None


def emit_dedup(
    event_name: str,
    dedup_key: str,
    *,
    system_message: str,
    hook_input: dict | None = None,
    additional_context: str | None = None,
    deny_reason: str | None = None,
) -> None:
    """Emit ``system_message`` only when it differs from the previous emission for ``dedup_key`` in this session.

    Suppresses chatter when the same hook fires repeatedly with the
    same status line (the canonical case is the panther-ivy MCP
    PreToolUse hooks firing on every ``ivy_workflow_state`` call).
    State persists in ``.observability/sessions/<sid>/hook-dedup.json``
    so suppression survives across hook process boundaries — every hook
    invocation spawns a fresh Python process and would otherwise have
    no way to compare against the previous emission.

    Important: model-facing context (``additional_context``) and
    blocking decisions (``deny_reason``) are NEVER deduplicated. The
    model needs the context every call regardless of repetition, and a
    blocking decision must always reach the runtime. Only the
    ``system_message``-only path is suppressed.

    Args:
        event_name: Hook event name (passed through to :func:`emit_hook_output`).
        dedup_key: Stable per-call-site identifier (typically the bracket
            tag — ``"ivy-ready"`` / ``"ivy-health"``). Two emissions
            sharing this key are duplicates iff their ``system_message``
            is identical.
        system_message: User-visible status line. Compared verbatim
            against the cached value; any change re-fires the emission
            and updates the cache.
        hook_input: Threaded to :func:`_hook_dedup_cache_path` for
            session resolution.
        additional_context: Optional model-facing context. Forces
            emission regardless of cache state.
        deny_reason: Optional blocking reason. Forces emission and
            never deduplicates.
    """
    if deny_reason is not None or additional_context is not None:
        emit_hook_output(
            event_name,
            system_message=system_message,
            additional_context=additional_context,
            deny_reason=deny_reason,
        )
        return

    cache_path = _hook_dedup_cache_path(hook_input)
    cache: dict[str, str] = {}
    if cache_path is not None and cache_path.exists():
        try:
            data = json.loads(cache_path.read_text())
            if isinstance(data, dict):
                cache = data
        except (OSError, json.JSONDecodeError):
            pass

    if cache.get(dedup_key) == system_message:
        emit_noop(event_name, f"deduplicated ({dedup_key})")
        return

    cache[dedup_key] = system_message
    if cache_path is not None:
        try:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(json.dumps(cache))
        except OSError:
            pass

    emit_hook_output(event_name, system_message=system_message)
